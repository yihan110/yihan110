"""c4-evaluator: 可复用、可执行、可验证的 C4 技能提交自动评审器。

模块划分（对应 C4A 四级任务）：
  config       —— 常量、路径、信号加载（复用 c4_rubric.yaml，单一事实来源）
  scanner      —— Level 1：文件夹扫描、作者识别、版本追踪
  completeness —— Level 2：五必需文件完整性检查
  quality      —— Level 3：四条件质量评审（规则 + 可选 LLM 的混合方案）
  report       —— Level 4：Markdown / Excel / HTML 报告生成 + 排名 + 改进建议
  evaluator    —— 编排器：把 1→4 级串成一条流水线
"""

__version__ = "1.2.0"
