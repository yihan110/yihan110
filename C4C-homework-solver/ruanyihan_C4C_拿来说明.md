# 拿来说明（C4C 作业自动求解与排版）

> 作者：阮依涵 ｜ 挑战：C4C ｜ 日期：2026-10-11

---

## 一、从 starter kit 拿了什么

| 模块 | 拿取内容 | 处理方式 |
|------|----------|----------|
| **5 阶段流水线架构** | 摄入 → 解析 → 求解 → LaTeX → PDF | 完整继承框架 |
| `ingest.py` | 文档摄入（Markdown/PDF/Word） | 原样保留 |
| `parse_problems.py` | 题号/子题/公式解析、题型分类 | 原样保留 |
| `classify.py` / `retrieve.py` | 分类与检索机制 | 原样保留 |
| `solve.py` | 微积分极限求解器（极限/切线/ε-δ）+ `SOLVERS` 路由 | 保留，并新增高级求解器入口 |
| `render_latex.py` | LaTeX 作业模板、题目+解答排版、PDF 编译 | 保留，新增中文支持 |
| `pipeline.py` | 一键串联 | 保留 |
| `domain_skills/calculus_limits.yaml` | 极限领域知识（ontology-grounded 范式） | 保留，作为新领域的范式参照 |
| `references/`（homework_template.tex、sympy_cheatsheet.md） | 排版模板与 SymPy 速查 | 保留 |
| 核心思想 | **"求解率 = 领域覆盖度"** | 吸收并沿用 |

## 二、我改了什么（相对 starter）

| 改动 | 说明 |
|------|------|
| **新增 `llm_solver.py`** | DeepSeek 国产模型客户端，把 starter 的 Claude 推理迁移到国产模型 |
| **新增 `solve_advanced.py`** | 高等数学求解器：偏导、全微分、拉格朗日、二重/三重积分、p-级数、比值判别、幂级数、泰勒展开（全 SymPy） |
| **新增 `domain_skills/advanced_math.yaml`** | 高等数学领域知识定义（概念、解法、分类规则） |
| **修改 `solve.py`** | 在 `solve_problem` 开头优先调用高级求解器，失败回退原 solver（向后兼容） |
| **修改 `render_latex.py`** | 加 `ctex` 宏包支持中文，编译优先 xelatex |
| **重写 `SKILL.md`** | 更新为迁移版说明 |

## 三、用了哪些外部库

| 库 | 用途 | 为什么 |
|----|------|--------|
| **SymPy** | 符号计算引擎（求导、积分、级数、极限、方程） | 确定性精确，是"拿来"的计算引擎 |
| **PyYAML** | 读取领域知识 YAML | starter 依赖 |
| **pdfplumber** | PDF 文本提取（摄入层） | 支持 PDF 输入 |
| **python-docx** | Word 文本提取 | 支持 docx 输入 |
| **requests** | 可选的 LLM 调用 | 备用（当前用标准库 urllib，减少依赖） |
| **DeepSeek API** | 国产模型推理 | 迁移核心 |
| **ctex / xelatex** | 中文 LaTeX 排版 | 支持中文作业 |

## 四、Claude 版本 vs 国产模型版本（关键差异）

| 维度 | Claude 基线（starter） | 本版本（DeepSeek） |
|------|----------------------|-------------------|
| **LLM 引擎** | Claude（闭源，国外） | **DeepSeek `deepseek-chat`**（国产，国内直连） |
| **推理调用** | 内嵌于求解器 | 抽象为 `llm_solver.py` 单点，可切换 Qwen/Kimi/DeepSeek |
| **学科覆盖** | 仅微积分极限（94.4%） | 极限 + **高等数学（多元/级数），100%** |
| **证明题** | ❌ 失败（无 LLM 求解器） | ✅ DeepSeek 反证法完整推导 |
| **领域知识** | `calculus_limits.yaml` | + `advanced_math.yaml` |
| **中文能力** | 英文为主 | 中文题目/解答 + ctex 中文排版 |
| **求解策略** | 规则 + SymPy | **规则 + SymPy + DeepSeek 三层混合** |

**核心增量**：把 starter 的"单引擎（规则+SymPy）"升级为"双引擎（SymPy 计算 + DeepSeek 推理）"，
并将领域从极限扩展到高等数学，域外求解率从 **40% → 100%**。

## 五、拿来主义反思

- **吸收而非照搬**：保留 starter 的架构骨架和极限能力（向后兼容），把扩展集中在新增领域和迁移引擎上，避免重写带来的风险。
- **理解后再迁移**：先吃透"领域覆盖度"设计哲学，再决定新领域如何接入（YAML + 求解函数 + 路由），而非写死正则。
- **迁移的本质**：LLM 调用点单一化后，换平台只需改 API 端点——这正体现了"在不同平台复现"的工程能力。
