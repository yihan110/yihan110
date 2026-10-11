# 方案设计文档（C4C 作业自动求解与排版）

> 作者：阮依涵 ｜ 挑战：C4C ｜ 日期：2026-10-11

---

## 一、挑战理解

C4C 的核心不是做一个单点工具，而是构建一条**端到端自动化流水线**，把"收到作业 → 手动解题 → 手动排版 → 提交 PDF"压缩为一条命令。starter kit 已在 Claude Code 上跑通微积分极限（94.4%），我的任务有两件：

1. **迁移引擎**：把流水线从 Claude 迁移到**国产大模型**。
2. **扩展学科**：从微积分极限扩展到新领域（我不能选极限）。

我选用的国产模型是 **DeepSeek**，扩展学科是**高等数学（多元微积分 + 无穷级数）**。

---

## 二、总体架构

沿用 starter kit 的 5 阶段流水线，并在求解层引入**双引擎混合**：

```
输入(作业) → Stage1 摄入 → Stage2 解析+分类 → Stage3 求解 → Stage4 LaTeX → Stage5 PDF
                                                  │
                                    ┌─────────────┴─────────────┐
                                    │ 层1 SymPy 符号计算         │  确定性精确
                                    │ 层2 DeepSeek LLM 推理     │  证明/文字
                                    └───────────────────────────┘
```

- **Stage 1 摄入（ingest.py）**：读取 .md/.pdf/.docx/图片，抽取出结构化文本与分段边界。
- **Stage 2 解析（parse_problems.py）**：识别题号（`Problem N` / `N.` / `题 N`）、子题、LaTeX 公式，并分类题型。
- **Stage 3 求解（solve.py + solve_advanced.py + llm_solver.py）**：
  - 保留 starter 的极限/切线求解器（向后兼容）；
  - 新增 `solve_advanced.py` 处理高等数学（偏导、全微分、拉格朗日、重积分、级数、幂级数、泰勒）——全部用 SymPy 精确计算；
  - 证明/文字题走 `llm_solver.py` 调用 **DeepSeek** 推理。
- **Stage 4 排版（render_latex.py）**：套用作业模板，题目+解答交替，答案方框标注；新增 `ctex` 支持中文（xelatex 编译）。
- **Stage 5 编译**：xelatex 编译 3 遍生成 PDF。

---

## 三、国产模型选型：为什么用 DeepSeek

CHALLENGE 推荐 Qwen 3.6 / Kimi 2.5，但也明确"DeepSeek 也可尝试"。我选择 **DeepSeek**，理由：

| 维度 | 评估 |
|------|------|
| **可获取性** | 已有可用 API key，无需额外注册；开放平台国内直连，符合"不翻墙、只用国内源"的约束 |
| **数学推理** | `deepseek-chat` 在高等数学证明（如调和级数发散的反证法）上表现优秀，实测能给出完整严谨的分步推导 |
| **成本与延迟** | 国内 API 延迟低、成本可控，适合高频批量求解 |
| **可复现性** | 与 Qwen/Kimi 同为国产模型，满足"迁移到国产大模型"的挑战要求 |

> 迁移的本质是"理解架构后在不同平台复现"。我把 Claude 版流水线的 LLM 调用点抽象成 `llm_solver.py` 一个模块，只改 API 端点与鉴权即可切换到 Qwen/Kimi/DeepSeek 任意一家——这正是跨平台工程能力的体现。

---

## 四、目标课程与求解策略

**目标课程**：高等数学（Advanced Mathematics）——选它作为"非微积分极限"的真实作业学科。

**求解策略（何时用 SymPy、何时用 DeepSeek）**：

| 题型 | 引擎 | 理由 |
|------|------|------|
| 偏导数、全微分 | SymPy `diff` | 确定性、精确 |
| 拉格朗日乘数法 | SymPy `solve`（梯度方程组） | 精确求解驻点 |
| 二重/三重积分 | SymPy `integrate`（嵌套） | 精确数值/符号结果 |
| p-级数、比值判别 | SymPy `limit`（比值极限） | 精确判定 ρ 与 p |
| 幂级数收敛半径、泰勒展开 | SymPy `limit` / `series` | 精确公式 |
| **证明题（如调和级数发散）** | **DeepSeek** | 需要多步逻辑推理，SymPy 无法证明 |

**核心创新**：不盲信单一引擎。计算题用 SymPy 保证正确率（可核验），推理题用 DeepSeek 补足 starter 的短板（Claude 版证明题会失败）。`solve_advanced.py` 先尝试 SymPy，失败再回退，保持鲁棒。

---

## 五、Level 达成目标

- **Level 1（Bronze）**：国产模型（DeepSeek）跑通微积分极限 → 继承 starter 能力 ✅
- **Level 2（Silver）**：输入格式扩展 + 新增高等数学领域（多元/级数）✅
- **Level 3（Gold）**：用真实作业（高等数学，非极限）生成正确 PDF ✅
- **Level 4（Platinum，部分）**：SymPy+DeepSeek 混合、答案核验、领域知识文件

实测：本作业 **11/11（100%）** 求解正确，PDF 编译成功，详见《验证报告》。

---

## 六、文件交付清单

| 文件 | 说明 |
|------|------|
| `ruanyihan_C4C_方案设计.md` | 本文件 |
| `homework-solver/` | 可运行技能包（源码） |
| `ruanyihan_C4C_作业原件.md` | 真实作业（高等数学，11 题） |
| `ruanyihan_C4C_output.pdf` / `.tex` | 生成的答案 PDF / LaTeX |
| `ruanyihan_C4C_验证报告.md` | 正确性验证 + 与 Claude 基线对比 |
| `ruanyihan_C4C_教学说明.md` | 安装、使用、支持课程 |
| `ruanyihan_C4C_AI日志.md` | 开发全过程 AI 使用记录 |
| `ruanyihan_C4C_拿来说明.md` | 拿来主义说明 + 国产模型差异 |
