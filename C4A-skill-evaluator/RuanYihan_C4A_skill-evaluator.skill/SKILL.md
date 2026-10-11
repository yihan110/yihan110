---
name: c4-skill-evaluator
description: >
  Scan a local folder containing C4/C4A skill submissions (typically from a WeChat
  group), identify each submission's author, check deliverable completeness against
  the 5 required files (skill doc, executable content, demo, teaching doc, AI log),
  evaluate skill quality against the C4 four-criteria rubric (Reusable, Executable,
  Verifiable, Clear I/O), and generate a structured evaluation report with per-author
  scores, gap analysis, ranking, improvement suggestions and version tracking.
  Output formats: Markdown report + Excel detail sheet + self-contained HTML dashboard.
  Use whenever the user says "evaluate C4 submissions", "check C4 completeness",
  "review skill submissions", "评审C4提交", "检查技能提交", "C4评审报告",
  "自动阅卷", "技能自动评审", or provides a folder path and asks to evaluate/review
  the skill files inside.
---

# C4 Skill Submission Evaluator (技能提交自动评审器)

把 `wechat-doc-mapper` 的“分类盘点”能力升级为“自动评审”能力：不仅扫描→分类→查缺口，
还能对每个 C4 提交给出完整性判定、四条件质量评分、排名与个性化改进建议。

## Purpose

给定一个本地文件夹路径（WeChat 群同步目录 / 手动下载目录 / 任意包含 C4 提交的目录），
本技能自动完成四级流水线：

```
WeChat 群文件夹
    ↓
① 文件采集与作者识别（scanner）        —— Level 1
    ↓
② 提交完整性检查（completeness）       —— Level 2：五必需文件
    ↓
③ 技能质量评审（quality）              —— Level 3：四条件（规则 + 可选 LLM）
    ↓
④ 评审报告生成（report）              —— Level 4：Markdown + Excel + HTML
```

## Prerequisites

### Runtime
- Python 3.10+
- 依赖：`openpyxl`（Excel）、`pyyaml`（规则解析）。安装：
  ```bash
  pip install -r requirements.txt
  ```
- （可选，Level 3 增强）一个 `LLMReviewer` 实现用于深度语义评审；默认关闭，纯离线规则可跑。

### Input
- 一个本地文件夹路径，内含 C4 提交文件，命名遵循规范：`姓名拼音_C4_内容描述.扩展名`
  或 `姓名拼音_C4A_内容描述.扩展名`（如 `RuanYihan_C4_skill说明.md`）。

## Quick Start

```bash
# 1) 安装依赖
pip install -r requirements.txt

# 2) 运行评审（输入 = 一个文件夹路径）
python scripts/run_c4_evaluator.py "C:/path/to/wechat-group-folder" --out ./report

# 3) 产物
#    report/评审报告.md       —— Markdown 完整报告
#    report/评审数据.xlsx     —— Excel 详表
#    report/评审仪表板.html   —— HTML 可视化仪表板（双击打开）
```

若作为豆包/Claude 技能使用：安装本 `.skill` 包后，直接把群文件夹路径发给技能，
说“评审这个文件夹里的 C4 提交”，技能即按四步流水线执行并交付报告。

## Architecture & Design Decisions

模块（`src/`）与 C4A 四级任务一一对应，每个模块单一职责、可单测：

| 模块 | 负责 | 对应 Level |
|------|------|-----------|
| `config.py` | 路径/命名规范/信号加载（单一事实来源） | — |
| `scanner.py` | 扫描、作者识别链、版本追踪 | L1 |
| `completeness.py` | 五必需文件完整性检查 | L2 |
| `quality.py` | 四条件质量评审（规则+可选LLM） | L3 |
| `report.py` | Markdown/Excel/HTML 生成、排名、建议 | L4 |
| `evaluator.py` | 编排 1→4 级流水线 | — |

**评审方案（关键设计决策）**：采用 **规则 + 可选 LLM 混合**。
- 规则引擎：依据 `references/c4_rubric.yaml` 的正/负向信号做确定性计分——
  快、零成本、可复现、可测试（对应评审器质量“有测试用例 / 误判率低”）。
- 可选 LLM 层：`quality.LLMReviewer` 可插拔接口，规则先快筛，LLM 再做语义复核与
  补充建议，兼顾确定性与理解力。默认关闭，保证离线可运行。
- 为什么不是纯规则：关键词覆盖率低、易误判；为什么不是纯 LLM：慢、贵、不确定。
  混合式让两者分工（方案文档有完整取舍分析）。

**评分公式**（对齐 `c4_rubric.yaml`）：
- 完整性分 = 已提交必需文件数 / 5
- 质量分 = 四条件（✅=1.0 / ⚠️=0.5 / ❌=0.0）均值
- 综合分 = 完整性×0.4 + 质量×0.6，映射到 0–100

## Step-by-step Workflow

### Step 1 — Scan & Identify Authors (L1)
- 递归扫描目标文件夹，过滤 `.git/__pycache__` 等。
- 识别文件名 `_C4_` / `_C4A_` 标记；`_v2`、`_v3` 版本追踪。
- **作者识别链**：文件名前缀 → 子文件夹名 → 文档内容（`提交人：`）→ 标记 `Unknown` 待人工。
- 二进制/超大文件（>50MB）跳过内容分析，仅做文件名匹配。

### Step 2 — Completeness Check (L2)
对照 5 个必需文件（skill_doc / executable_content / demo / teaching_doc / ai_log），
文件名层 + 内容信号层双重判定；内容层命中标记“需人工复核”。状态：✅齐全 / ⚠️部分缺失 / ❌严重缺失。

### Step 3 — Quality Evaluation (L3)
对四条件（可复用 / 可执行 / 可验证 / IO 明确），按正/负信号统计满足的 check items：
满足 ≥2 项 → ✅；1 项 → ⚠️；0 项 → ❌。附评审依据与改进建议。

### Step 4 — Generate Report (L4)
Markdown（班级总览 + 作者详情 + 排名 + 全班建议 + 非C4文件清单）+
Excel（按作者一行，含状态与评级，可排序）+ HTML（自包含仪表板，含排名条形图）。

## Edge Cases

| 情况 | 处理 |
|------|------|
| 空文件夹 / 无 C4 文件 | 报告“未找到 C4 相关文件”，列出扫描路径与匹配规则 |
| 文件名不规范 | 回退到子文件夹名/内容识别，标记“需人工确认” |
| 超大文件（>50MB） | 跳过内容分析，仅文件名/类型匹配 |
| 二进制文件（.mp4/.png 等） | 仅文件名匹配（demo 判定依赖扩展名） |
| 非 C4 文件混入 | 过滤后单列“非 C4 文件” |
| 同一作者多版本（_v2/_v3） | 版本追踪，报告迭代轨迹，排名用最新版 |
| 中文/编码问题 | UTF-8 优先，GBK 回退 |

## Customization
- 想调整评审维度/信号：改 `references/c4_rubric.yaml`（代码自动读取，无需改代码）。
- 想接入 LLM 深度评审：继承 `quality.LLMReviewer` 实现 `review()`，传入 `run_evaluation(llm_reviewer=...)`。
- 想改排名权重：`run_evaluation(weights={"completeness":0.4,"quality":0.6})`。
