"""
MetaScope — Metacognitive Calibration & Unknown-Awareness Benchmark
====================================================================
衡量 AGI 元认知能力（Track 2 · Metacognition）的基准评测包。

赛道对应 DeepMind《Measuring Progress Toward AGI: A Cognitive Framework》
中评估缺口最大的五个认知能力之一——元认知（Metacognition）：
  “知之为知之，不知为不知”——模型是否知道自己知道什么、不知道什么，
  能否校准自身的确信度。

MetaScope 通过三个任务模块隔离测量元认知的两个子能力：
  Module A  Knowledge Calibration  知识校准   —— 知道时，确信度是否与正确率一致
  Module B  Unknown Awareness      未知识别   —— 不知道时，能否识别并拒绝，而非幻觉
  Module C  Confidence Reflexivity 自信反思   —— 能否预测自己的正确率（自我监控）

主要指标：ECE / Brier / MCE / 校准曲线 / 未知识别 AUROC / 过自信率 / 幻觉率 /
          自我预测误差（MetaScore 复合分）。

作者：ruanyihan（阮依涵）· 郑州西亚斯学院 · AI+X Elite 20 课程
课程：C2A / C9 — 衡量 AGI 的认知能力
"""

__version__ = "1.0.0"
__track__ = "Track 2 — Metacognition（元认知）"
