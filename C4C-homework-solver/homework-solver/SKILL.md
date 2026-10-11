# Homework Auto-Solver & Formatter（国产模型迁移版）

> 从作业文件到可提交 PDF，一条命令搞定。
> 基于 starter kit（Claude 基线）迁移到**国产大模型 DeepSeek**，并扩展新学科。

## 概述

C4C 作业自动求解与排版流水线。将"拿到作业 → 手动解题 → 手动排版 → 提交 PDF"
压缩为一条命令。本版本做了两件核心事：

1. **迁移引擎**：把 starter kit 的 LLM 推理能力从 Claude 迁移到国产模型 **DeepSeek**（`deepseek-chat`）。
2. **扩展学科**：在 starter 的微积分极限基础上，新增**高等数学（多元微积分 + 无穷级数）**领域。

## Skill Invocation

**触发词**：用户提供数学作业文件（.md/.pdf/.docx/.png）并请求"求解作业 / 自动解题 / auto-solve homework / solve this homework"。

**用法：**
```bash
python scripts/pipeline.py <input_file> <output_dir> [--compile] \
    [--course "Advanced Mathematics"] [--student "阮依涵"] [--title "高等数学作业"]
```

**参数：**
| 参数 | 默认 | 说明 |
|------|------|------|
| `input` | 必填 | 作业文件（md/pdf/docx/图片） |
| `output_dir` | 必填 | 输出目录 |
| `--compile` | 关 | 编译 LaTeX → PDF（xelatex，支持中文） |
| `--course` / `--student` / `--title` | — | 文档页眉信息 |
| `--verbose` | 关 | 详细输出 |

**输出文件：**
| 文件 | 内容 |
|------|------|
| `1_ingested.json` | 文本抽取（含分段边界） |
| `2_parsed.json` | 结构化题目（题号/类型/子题） |
| `3_solutions.json` | 解答（步骤/答案/求解状态） |
| `homework.tex` | 排版的 LaTeX 文档 |
| `homework.pdf` | 编译后的 PDF（--compile） |

**环境变量：** `DEEPSEEK_API_KEY`（DeepSeek 开放平台 key，用于证明/文字题的 LLM 推理）

## 双引擎混合架构

```
输入 → 摄入 → 解析+分类 → 求解 → LaTeX 排版 → PDF 编译
                            │
              ┌─────────────┴─────────────┐
              │ 层1  SymPy 符号计算        │  确定性精确计算
              │ 层2  DeepSeek LLM 推理     │  证明/文字/复杂多步
              └───────────────────────────┘
```

`solve_advanced.py` 是本次迁移+扩展的核心：优先用 SymPy 精确计算（偏导、重积分、级数），
SymPy 无法精确求解的证明/文字题交给 DeepSeek（`llm_solver.py`）推理。
无法处理的题目回退到原 solver，保持向后兼容。

## 领域覆盖

| 领域 | 能力 | 求解器 |
|------|------|--------|
| 微积分极限（继承 starter） | 切线、ε-δ、极限 | `solve_limit` / `solve_tangent` 等 |
| **高等数学·多元微分**（扩展） | 偏导数、全微分、拉格朗日乘数法 | `solve_advanced.py` |
| **高等数学·重积分**（扩展） | 二重积分、三重积分 | `solve_advanced.py` |
| **高等数学·级数**（扩展） | p-级数、比值判别、幂级数、泰勒展开 | `solve_advanced.py` |
| **证明/文字题**（扩展） | 证明、概念、复杂推理 | `llm_solver.py`（DeepSeek） |

领域知识定义在 `domain_skills/advanced_math.yaml`（ontology-grounded，遵循
starter 的"求解率 = 领域覆盖度"思想）。

## 迁移说明（Claude → DeepSeek）

| 层面 | Claude 基线（starter） | 本版本（DeepSeek） |
|------|----------------------|-------------------|
| LLM 引擎 | Claude（闭源） | **DeepSeek `deepseek-chat`**（国产，API 国内直连） |
| 求解机制 | 规则 + SymPy | 规则 + SymPy + **DeepSeek 混合** |
| 学科覆盖 | 仅微积分极限（94.4%） | 极限 + **高等数学（多元/级数）** |
| 领域知识 | `calculus_limits.yaml` | + **`advanced_math.yaml`** |
| 中文化 | 英文为主 | 中文题目 + 中文解题步骤 + ctex 排版 |

## 测试结果（本版本实测）

| 测试集 | 领域 | 正确数 | 准确率 |
|--------|------|--------|--------|
| starter 极限域（Berkeley W3/W4） | 微积分极限 | 17/18 | 94.4% |
| **C4C 扩展（本次作业）** | **高等数学（多元+级数）** | **11/11** | **100%** |

详细对比见 `ruanyihan_C4C_验证报告.md`。

## 文件结构

```
homework-solver/
├── SKILL.md                      ← 本文件（迁移版）
├── scripts/
│   ├── ingest.py                 ← Stage 1 文档摄入
│   ├── parse_problems.py         ← Stage 2 题目解析
│   ├── classify.py / retrieve.py ← 分类与检索
│   ├── solve.py                  ← Stage 3 求解（集成高级求解器）
│   ├── solve_advanced.py         ← ★ 高等数学求解器（SymPy 多元/级数）
│   ├── llm_solver.py             ← ★ DeepSeek 推理引擎（国产模型迁移）
│   ├── render_latex.py           ← Stage 4 LaTeX（ctex 中文支持）
│   └── pipeline.py               ← 一键流水线
├── domain_skills/
│   ├── calculus_limits.yaml      ← 继承 starter
│   └── advanced_math.yaml        ← ★ 新增高等数学领域
├── references/                   ← LaTeX 模板、SymPy 速查
├── examples/                     ← 示例作业
└── test_cases/                   ← Berkeley 测试用例
```

## 依赖

```bash
pip install sympy pyyaml pdfplumber python-docx requests
# PDF 编译需要 LaTeX（推荐 xelatex，支持中文）
# LLM 推理需要设置环境变量 DEEPSEEK_API_KEY
```
