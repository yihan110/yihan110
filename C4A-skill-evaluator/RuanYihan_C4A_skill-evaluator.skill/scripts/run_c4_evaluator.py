#!/usr/bin/env python3
"""run_c4_evaluator.py —— C4A 技能提交自动评审器 · 命令行入口。

用法：
  python run_c4_evaluator.py <文件夹路径> [--out 输出目录] [--rubric 规则文件] [--llm 启用LLM层]

示例：
  python run_c4_evaluator.py "C:/微信群文件" --out ./结果
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许从任意工作目录运行：把 src 加入模块搜索路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="c4-evaluator",
        description="C4A 技能提交自动评审器：扫描→完整性→质量评审→报告（Markdown/Excel/HTML）。")
    ap.add_argument("folder", help="要扫描的本地文件夹路径（WeChat 同步目录或任意包含 C4 提交的目录）")
    ap.add_argument("--out", default=None, help="报告输出目录（默认与扫描目录同级）")
    ap.add_argument("--rubric", default=None, help="自定义 c4_rubric.yaml 路径")
    ap.add_argument("--llm", action="store_true", help="启用 LLM 深度评审层（需自行实现 LLMReviewer）")
    args = ap.parse_args(argv)

    from src.evaluator import run_evaluation

    out_dir = args.out or str(Path(args.folder).parent)
    llm = None
    if args.llm:
        # 提供一个占位 reviewer 提示（默认不启用，保持确定性）
        print("[提示] 未配置 LLMReviewer 实现，继续使用规则引擎。", file=sys.stderr)

    print(f"① 扫描文件夹：{args.folder}")
    result = run_evaluation(args.folder, rubric_path=args.rubric,
                            llm_reviewer=llm, out_dir=out_dir)

    n = len(result.scores)
    n_complete = sum(1 for c in result.completeness.values() if c.present_count >= 5)
    ranked = sorted(result.scores, key=result.scores.get, reverse=True)
    print(f"② 识别提交：{n} 位作者，完整 5/5：{n_complete}")
    print("③ 综合分排名：")
    for i, a in enumerate(ranked, 1):
        print(f"   {i:>2}. {a:<16} 完整性 {result.completeness[a].present_count}/5  "
              f"质量 {result.quality[a].score * 4:.2f}/4.0  "
              f"综合 {result.scores[a]:.1f}/100")
    print("④ 报告已写出：")
    print(f"   - 评审报告.md : {out_dir}")
    print(f"   - 评审数据.xlsx : {result.excel_path}")
    print(f"   - 评审仪表板.html : {result.html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
