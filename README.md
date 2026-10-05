# MetaScope — Metacognitive Calibration & Unknown-Awareness Benchmark

> 衡量 AGI **元认知能力**的基准评测包（Track 2 · Metacognition）
> 作者：ruanyihan（阮依涵）· 郑州西亚斯学院 · AI+X Elite 20 课程
> 对应 Kaggle 黑客松：*Measuring Progress Toward AGI: Cognitive Abilities*
> 框架依据：Google DeepMind《Measuring Progress Toward AGI: A Cognitive Framework》(2026-03-16)

---

## 一、这是什么？

DeepMind 把 AGI 拆成 10 个认知能力，其中**元认知（Metacognition）**是评估缺口最大的五个之一，定义是
**“知之为知之，不知为不知”**——模型是否知道自己知道什么、不知道什么，能否校准自身确信度。
它正是 LLM 产生**幻觉**的关键根源。

MetaScope 把元认知拆成三个可隔离测量的子能力，用可量化、可复现、可反作弊的指标去测：

| 模块 | 测什么 | 对应元认知子能力 |
|------|--------|------------------|
| **A 知识校准** Knowledge Calibration | 模型知道答案时，它的自信度是否与真实正确率一致 | 确信度校准（confidence calibration） |
| **B 未知识别** Unknown Awareness | 模型不知道答案时，能否识别出来并**拒绝/不幻觉** | 认知边界 / 未知识别（knowing-unknowing） |
| **C 自信反思** Confidence Reflexivity | 模型能否预测自己会答对几题（自我监控） | 前瞻式元认知 / 自我监控 |

**一句话**：不只看“答对没有”，更看“该自信时是否自信、该认怂时是否认怂、是否知道自己几斤几两”。

---

## 二、为什么能有效测量元认知（而非别的能力）

1. **隔离性**：三个模块分别只操控“校准 / 未知识别 / 自我监控”一个变量，其他条件（题目难度、作答协议）保持一致，避免把推理、知识、注意力等能力混进来。
2. **正确评分规则（Proper Scoring）**：用 **Brier 分数**而非准确率——一个永远报“50% 对 50%”的模型无法靠打太极刷分；过自信会被 ECE 与过自信率显式惩罚。
3. **反记忆污染**：Module B 的题目全部**程序化生成**（伪造概念、非存在实体、信息不足陷阱），答案不可能存在于任何训练数据中，从机制上排除“背答案”。
4. **防作弊**：同时测量校准曲线、Brier、AUROC、幻觉率等多个相互制约的指标，单点投机（如“全都说不知道”）会在校准维度暴跌。

---

## 三、指标定义

| 指标 | 公式/含义 | 好模型 | 坏模型 |
|------|-----------|--------|--------|
| **ECE** 期望校准误差 | 按确信度分 10 箱，Σ\|箱内准确率−箱内确信度\|·权重 | ≈0 | 高 |
| **MCE** 最大校准误差 | 各箱 \|准确率−确信度\| 的最大值 | ≈0 | 高 |
| **Brier 分数** | mean((p−y)²)，p=选定项确信度，y=1 对/0 错 | ≈0 | 高 |
| **过自信率** | 仅当“准确率<确信度”时加权偏差 | ≈0 | 高 |
| **正确拒绝率** | 对“无有效答案/信息不足”项正确拒绝的比例 | ≈1 | 低 |
| **幻觉率** | 无有效答案项仍强行作答的比例 | ≈0 | 高 |
| **AUROC（已知项）** | 以确信度为分数预测“作答正确”，考察自信-正确一致性 | 高 | ≈0.5 |
| **自我预测误差** | \|预测答对数−实际答对数\| / 总题数 | 低 | 高 |

**复合分 MetaScore（0–100）** = 校准 40 + 未知识别 40 + 自我监控 20。

---

## 四、快速开始

**环境**：仅需 Python 3.8+，**无任何第三方依赖**（纯标准库），离线即可运行。

```bash
# 1) 生成题目 + 跑两个离线演示模型（无需 API Key，验证管线）
python run_benchmark.py

# 2) 产物
#    data/benchmark.json       题目数据
#    output/results.json       结构化指标结果
#    output/report.md          人类可读报告（含校准曲线）
#    output/demo_well_calibrated.json / demo_overconfident.json
```

运行后你会看到两个“性格”截然不同的模型被清晰区分：

```
演示模型①：校准良好（知道才自信，不知道会拒绝）  →  MetaScore ≈ 94
演示模型②：过自信+幻觉（不知道也强行猜）        →  MetaScore ≈ 32
```

这说明基准对**元认知水平**有真实区分度，而非测“谁知识更广”。

---

## 五、对真实前沿模型评测（国内可直连）

MetaScope 提供 OpenAI 兼容的 API 客户端，**无需翻墙**，默认指向 DeepSeek，
也可切换 Qwen（DashScope）、Kimi（Moonshot）、智谱 GLM 等任何兼容端点。

```bash
# 配置环境变量（以 DeepSeek 为例）
set METASCOPE_BASE_URL=https://api.deepseek.com
set METASCOPE_API_KEY=你的APIKey
set METASCOPE_MODEL=deepseek-chat

# 运行真实模型评测
python run_benchmark.py --api
```

结果会写入 `output/api_<model>.json`，可与演示模型、人类基线放在同一张雷达/表格里对比。

---

## 六、目录结构

```
metascope/                    # 核心 Python 包
  __init__.py                 # 包说明与版本
  generator.py                # 题目生成（Module A/B/C）
  scoring.py                  # 指标：ECE/Brier/MCE/校准/AUROC/幻觉/自我预测
  clients.py                  # API 客户端（OpenAI 兼容）+ 离线演示模型
  runner.py                   # 评测管线：加载→作答→判定→汇总
run_benchmark.py              # 命令行入口
data/benchmark.json           # 生成的题目数据
output/                       # 评测结果（json + markdown 报告）
```

---

## 七、参考与拿来主义（Attribution）

本基准站在已有工作肩膀上，核心借鉴与取舍：

| 来源 | 拿了什么 | 改了什么 / 为什么 |
|------|---------|------------------|
| **MMLU / BIG-Bench** | 多选题+知识广度 | 不只看准确率，增加“确信度校准 + 未知识别”，直指元认知而非知识量 |
| **LLM-Uncertainty-Bench (Ye et al., 2024)** | 置信度量化评估框架 | 补上“伪造干扰项 + 信息不足陷阱”对抗式未知识别模块 |
| **ARC (Chollet, 2019)** | “任务答案不在训练数据中”的设计哲学 | 用程序化生成替代手工视觉网格，聚焦元认知维度 |
| **DeepMind AGI 认知框架 (2026)** | 元认知定义 + 三阶段评估协议（认知→人类基线→画像） | 落实为可自动打分的三模块基准 |
| **KSTAR 课程框架** | ΔE（认知偏差）+ 置信度校准 → 元认知 | Module B 直接测量“模型是否知道自己不知道”（ΔE 最小化） |

---

## 八、人类基线（设计预期）

人类在“知识校准”上通常校准良好（ECE 约 5–10%），但在困难领域存在经典**过自信偏差**；
对“无有效答案/信息不足”项，成年人普遍能正确拒绝（拒绝率接近 1，幻觉率≈0）——
这正是 MetaScope 想同时测的两个方向。基准难度可调（题目库扩展、陷阱强度），
可避免地板/天花板效应。

---

## 九、作者与版权

- 作者：ruanyihan（阮依涵）· 郑州西亚斯学院软件工程专业
- 用途：AI+X Elite 20 课程 C2A/C9 挑战 · Kaggle Community Benchmarks 参赛作品
- 欢迎 fork / 提 issue，可在 `generator.py` 中扩展题目库后直接复用。
