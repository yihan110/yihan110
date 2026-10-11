# RuanYihan_C4A_skill-evaluator.skill

C4A 挑战「技能提交自动评审」的可安装技能包：把一个本地文件夹里的 C4 提交
扫描 → 作者识别 → 完整性检查 → 四条件质量评审 → 生成报告（Markdown / Excel / HTML）。

## 结构

```
RuanYihan_C4A_skill-evaluator.skill/
├── SKILL.md                 # 主技能文档（触发描述 + 四步流水线 + 边界情况）
├── requirements.txt         # Python 依赖
├── README.md                # 本文件
├── references/
│   ├── c4_rubric.yaml       # 机器可读评审规则（单一事实来源，改它即改评审）
│   └── wechat_doc_mapper_notes.md  # 拿来主义分析（对 wechat-doc-mapper 的改造说明）
├── src/
│   ├── config.py            # 常量/命名规范/信号加载
│   ├── scanner.py           # L1 扫描与作者识别
│   ├── completeness.py      # L2 完整性检查
│   ├── quality.py           # L3 四条件质量评审（规则+可选LLM）
│   ├── report.py            # L4 报告生成（MD/Excel/HTML）
│   └── evaluator.py         # 编排器
├── scripts/
│   └── run_c4_evaluator.py  # 命令行入口
└── tests/
    ├── test_c4_evaluator.py # 单元测试（含误判率回归）
    └── fixtures/            # 样例 C4 提交语料（同时作为测试用例）
```

## 快速开始

```bash
pip install -r requirements.txt
python scripts/run_c4_evaluator.py "C:/path/to/群文件" --out ./report
```

产物：`评审报告.md`、`评审数据.xlsx`、`评审仪表板.html`。

## 复用与扩展
- 改评审规则：编辑 `references/c4_rubric.yaml`，无需改代码。
- 接 LLM 深审：继承 `src/quality.LLMReviewer`。
- 改排名权重：`run_evaluation(weights=...)`。
