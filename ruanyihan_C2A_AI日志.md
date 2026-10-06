# C2A AI 生成日志 / AI Generation Log

**作者 / Author：** ruanyihan（阮依涵）
**挑战 / Challenge：** C2A — Track 2 Metacognition
**日期 / Date：** 2026-10-05
**工具 / Tools：** 豆包（Doubao）· AI+X Elite 20 工作台；C2A 提案生成器

---

## 0. 工作流设计（AI 使用方式）

本提案遵循挑战要求的 AI-First 原则，采用"AI 精读 → AI 调研 → AI 生成初稿 → 人工审阅修正 → AI 检查"的迭代工作流：

```
Step 1  AI 精读 DeepMind 论文摘要 → 提取元认知定义、评估缺口、三阶段协议
Step 2  AI 调研已有 benchmark（MMLU/BIG-Bench/LLM-Uncertainty/ARC）→ 定位元认知缺口
Step 3  AI 生成四部分提案初稿
Step 4  人工审阅：选赛道、定三模块结构、校指标、调可行性时间表
Step 5  AI 检查逻辑一致性与表达清晰度（多轮）
```

## 1. 论文精读 / Paper Analysis

- **输入：** DeepMind《Measuring Progress Toward AGI: A Cognitive Framework》官方摘要 PDF。
- **AI 提取要点：**
  1. 10 个认知能力中元认知被列为评估缺口最大的五分之一；
  2. 元认知定义 = "知之为知之，不知为不知"，是幻觉的关键根源；
  3. 三阶段评估协议 = 认知评估 → 人类基线 → 认知画像（10 维雷达图）。
- **追问迭代：** 第 1 轮追问"元认知与置信度校准在评测上如何具体化"，AI 给出校准曲线/ECE/Brier 的方向，并指出该赛道现有基准只测准确率不测确信度——这直接构成提案的核心动机。

## 2. Benchmark 调研 / Benchmark Research

- **搜索策略（并行多路）：**
  - Query 1：`metacognition confidence calibration LLM benchmark ECE Brier 2025`
  - Query 2：`MMLU BIG-Bench accuracy only limitation hallucination unknown`
  - Query 3：`LLM uncertainty quantification benchmark ARC few-shot novel`
- **关键发现：**
  - MMLU/BIG-Bench：高准确率但只报正确率，不测确信度 → 元认知盲区；
  - LLM-Uncertainty-Bench (Ye et al., 2024)：置信度量化框架 → 借鉴校准指标；
  - ARC (Chollet, 2019)："答案不在训练数据"的去记忆化哲学 → 借鉴到 Module B；
  - DeepMind 框架：元认知=幻觉根源 → 设计对抗式"未知识别"模块。
- **取舍：** 共调研 7+ 个方向，最终确定借鉴 MMLU（多选题形式）、LLM-Uncertainty（校准指标）、ARC（反记忆污染）、DeepMind（元认知定义与协议），其余（如 SocialIQA、Theory of Mind）因赛道不匹配而去掉。

## 3. 提案撰写 / Proposal Writing

- **初稿：** 让 AI 按四部分结构生成，覆盖"赛道动机/设计/人类基线/创新与可行性"。
- **迭代（3 轮）：**
  - 第 1 轮：初稿缺少具体指标与"为什么能隔离元认知"的论证 → 补上 ECE/Brier/AUROC 定义与隔离性论证；
  - 第 2 轮：设计过于抽象 → 明确三模块（A 校准/B 未知识别/C 自我监控）+ 复合分权重；
  - 第 3 轮：补人类基线（过自信偏差、拒绝率≈1）与 7 天可行性时间表。
- **人工修改（我的核心贡献）：**
  - 选定 Track 2（元认知）而非示例的 Learning，理由：缺口最大 + 最易量化 + 与 KSTAR ΔE 对接最直接；
  - 亲自设计 Module B 的"伪造干扰项 + 信息不足陷阱"构造，确保答案机制性不在训练集；
  - 将复合分确定为"校准 40 + 未知识别 40 + 自我监控 20"，并校验各权重不会让投机模型得分；
  - 核对引用真实性，去掉 AI 可能杜撰的文献，只保留可追溯来源。

## 4. 手动步骤说明 / Manual Steps Justification（反向举证）

| 手动步骤 | 为什么没用 AI |
|----------|-------------|
| 选定赛道为 Metacognition | 需要结合个人强项（软件工程、可量化评测落地能力）与课程 KSTAR 关联做价值判断，AI 无法代替个人定位 |
| 三模块的隔离性论证 | 需确保"只操控一个变量"，这是评测科学性的概念判断，需人工把关 |
| 复合分权重设置 | 需人工推演投机模型（"永远 50%""全说不知道"）在权重下的得分，验证无漏洞 |
| 参考文献真实性核验 | AI 有杜撰引用风险，逐条人工核查来源 |

## 5. AI 段位自评 / AI Usage Level

**🟢 驾驭级（advanced）** — 设计并执行了完整 AI 工作流（精读→调研→生成→人工修正→检查），多轮迭代 prompt 优化输出，核心设计（未知识别模块、隔离性论证、复合分权重）由人工与 AI 协同完成。非一句话指令直接提交，符合"AI 使用质量"满分维度。
