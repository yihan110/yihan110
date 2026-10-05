#!/usr/bin/env python3
"""
MetaScope 评测入口
==================
用法：
  python run_benchmark.py                    # 生成题目 + 跑两个离线演示模型（无需 API）
  python run_benchmark.py --api              # 用环境变量配置的真实模型跑评测
  python run_benchmark.py --model <name>     # 只跑单个演示模型

真实模型配置（国内可直连，无需翻墙）：
  set METASCOPE_BASE_URL=https://api.deepseek.com
  set METASCOPE_API_KEY=你的key
  set METASCOPE_MODEL=deepseek-chat
  （也可换用 Qwen / Kimi / 智谱 GLM 等任何 OpenAI 兼容端点）
"""

import argparse
import os
import sys

# 保证可以以“包外运行”方式 import metascope
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from metascope import generator
from metascope import runner
from metascope import visualize
from metascope.clients import DemoModel, APIModel


def build_report(model_results, calib_data, svg_files):
    """生成人类可读的 Markdown 报告。"""
    lines = ["# MetaScope 评测报告（Markdown）", ""]
    for r in model_results:
        s = r["summary"]
        a, b, c = s["模块A_知识校准"], s["模块B_未知识别"], s["模块C_自信反思"]
        lines.append(f"## {r['label']}（{r['name']}）")
        lines.append("")
        lines.append("| 维度 | 值 |")
        lines.append("|---|---|")
        lines.append(f"| 知识准确率 (A) | {a['accuracy']:.3f} |")
        lines.append(f"| 平均确信度 (A) | {a['avg_confidence']:.3f} |")
        lines.append(f"| ECE 期望校准误差 (A) | {a['ece']:.3f} |")
        lines.append(f"| MCE 最大校准误差 (A) | {a['mce']:.3f} |")
        lines.append(f"| Brier 分数 (A) | {a['brier']:.3f} |")
        lines.append(f"| 过自信率 (A) | {a['overconfidence']:.3f} |")
        lines.append(f"| 已知项 AUROC (A) | {a['auc_known']:.3f} |")
        lines.append(f"| 未知项 AUROC (B) | {b['unknown_auc']:.3f} |")
        lines.append(f"| 幻觉率 (B) | {b['hallucination_rate']:.3f} |")
        lines.append(f"| 正确拒绝率 (B) | {b['rejection_rate']:.3f} |")
        lines.append(f"| 自我预测误差 (C) | {c['reflexivity_error']:.3f} |")
        lines.append("")
        lines.append("**MetaScore：**")
        lines.append("")
        for k, v in r["MetaScore"].items():
            lines.append(f"- {k}: **{v}**")
        lines.append("")
        lines.append("### 校准曲线（A 模块，分箱 置信度 vs 准确率）")
        lines.append("")
        img = svg_files.get(r["name"])
        if img:
            name = r["name"]
            lines.append(f"![校准曲线 {name}]({img})")
            lines.append("")
        lines.append("| 分箱 | 置信度 | 准确率 | 样本数 |")
        lines.append("|---|---|---|---|")
        for conf, acc, cnt in calib_data[r["name"]]:
            lines.append(f"| - | {conf:.2f} | {acc:.2f} | {cnt} |")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="MetaScope 元认知基准评测")
    ap.add_argument("--api", action="store_true", help="使用真实 API 模型（需环境变量）")
    ap.add_argument("--model", default="all",
                    choices=["all", "well_calibrated", "overconfident_hallucinator"],
                    help="演示模型：all=两个都跑")
    ap.add_argument("--out", default=os.path.join("output", "results.json"))
    ap.add_argument("--report", default=os.path.join("output", "report.md"))
    ap.add_argument("--data", default=os.path.join("data", "benchmark.json"))
    args = ap.parse_args()

    print(">> 生成/加载题目数据 ...")
    if not os.path.exists(args.data):
        data = generator.save_benchmark(args.data)
    else:
        data = generator.load_benchmark(args.data)
    print(f"   题目数: {generator.module_counts(data)}")

    results = []

    if args.api:
        print(">> 使用真实 API 模型（OpenAI 兼容端点）...")
        api = APIModel()
        print(f"   endpoint={api.base_url} model={api.model}")
        res = runner.run_benchmark(api, data, name=api.model, label="真实模型(API)")
        results.append(res)
        runner.save_result(res, "output", f"api_{api.model.replace('/', '_')}.json")
    else:
        print(">> 运行离线演示模型（无需 API Key）...")
        if args.model in ("all", "well_calibrated"):
            m = DemoModel("well_calibrated", seed=0)
            res = runner.run_benchmark(m, data, name="well_calibrated",
                                       label="演示模型①：校准良好（知道才自信，不知道会拒绝）")
            results.append(res)
            runner.save_result(res, "output", "demo_well_calibrated.json")
            print(f"   [well_calibrated] MetaScore={res['MetaScore']['MetaScore']}")
        if args.model in ("all", "overconfident_hallucinator"):
            m = DemoModel("overconfident_hallucinator", seed=1)
            res = runner.run_benchmark(m, data, name="overconfident_hallucinator",
                                       label="演示模型②：过自信+幻觉（不知道也强行猜）")
            results.append(res)
            runner.save_result(res, "output", "demo_overconfident.json")
            print(f"   [overconfident_hallucinator] MetaScore={res['MetaScore']['MetaScore']}")

    # 校准曲线数据 + SVG 可视化
    calib = {}
    svg_files = {}
    for r in results:
        cc = r["summary"]["模块A_知识校准"].get("calibration_curve")
        calib[r["name"]] = cc if cc is not None else []
        if cc:
            fname = f"calibration_curve_{r['name'].replace('/', '_')}.svg"
            visualize.save_calibration_svg(cc, os.path.join("output", fname),
                                           title=f"校准曲线 · {r['label']}")
            svg_files[r["name"]] = fname

    # 汇总报告
    report_md = build_report(results, calib, svg_files)
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(report_md)

    # 汇总 JSON
    summary = {"model_results": [r for r in results]}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n>> 完成。结果: {args.out}")
    print(f">> 人类可读报告: {args.report}")
    return 0


if __name__ == "__main__":
    import json
    sys.exit(main())
