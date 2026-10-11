"""evaluator.py —— 编排器：把 Level 1→4 串成一条完整流水线。

流水线：
  WeChat 群文件夹/任意本地文件夹
      → ① scan_folder        （采集与作者识别，Level 1）
      → ② check_completeness （五必需文件完整性，Level 2）
      → ③ evaluate_quality   （四条件质量评审，Level 3）
      → ④ generate_*         （Markdown + Excel + HTML 报告，Level 4）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .completeness import CompletenessResult, check_completeness
from .config import load_rubric
from .quality import LLMReviewer, QualityResult, evaluate_quality
from .report import (
    composite_score,
    generate_excel,
    generate_html,
    generate_markdown,
)
from .scanner import FileInfo, ScanResult, scan_folder


@dataclass
class EvalOutput:
    """一次完整评审的输出。"""

    scan: ScanResult
    completeness: dict[str, CompletenessResult] = field(default_factory=dict)
    quality: dict[str, QualityResult] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    versions: dict[str, list[str]] = field(default_factory=dict)
    markdown: str = ""
    excel_path: str = ""
    html_path: str = ""


def _group_latest(files: list[FileInfo]) -> dict[str, FileInfo]:
    """按（作者, 内容描述去掉版本）分组，保留最新版本文件。"""
    latest: dict[str, FileInfo] = {}
    for fi in files:
        key = _strip_version(fi.name)
        if key not in latest or _ver_num(fi.version or "0") > _ver_num(latest[key].version or "0"):
            latest[key] = fi
    return latest


def _strip_version(name: str) -> str:
    import re
    return re.sub(r"(_v?\d+(?:\.\d+)?|\(\d+\))\s*$", "", name, flags=re.IGNORECASE)


def _ver_num(v: str) -> float:
    try:
        return float(v)
    except ValueError:
        return 0.0


def run_evaluation(
    folder: str,
    rubric_path: str | None = None,
    llm_reviewer: LLMReviewer | None = None,
    weights: dict | None = None,
    out_dir: str | None = None,
) -> EvalOutput:
    """运行完整评审流水线，返回结构化结果，并（可选）写出报告文件。

    out_dir: 指定时写出 评审报告.md / 评审数据.xlsx / 评审仪表板.html。
    """
    rubric = load_rubric(rubric_path)
    scan = scan_folder(folder)

    out = EvalOutput(scan=scan)

    # 版本轨迹：按作者收集其带版本标记（_v1/_v2）的文件，展示迭代历史
    for author, files in scan.authors.items():
        vers = []
        for fi in files:
            if fi.version:
                vers.append(f"v{fi.version} ({fi.name})")
        if vers:
            out.versions[author] = vers

    for author, files in scan.authors.items():
        # 完整性检查针对该作者全部文件
        out.completeness[author] = check_completeness(author, files, rubric)
        # 质量评审针对该作者全部文件
        out.quality[author] = evaluate_quality(author, files, rubric, llm_reviewer)
        out.scores[author] = composite_score(
            out.completeness[author], out.quality[author], weights)

    if out_dir:
        od = Path(out_dir)
        od.mkdir(parents=True, exist_ok=True)
        out.markdown = generate_markdown(
            folder, out.completeness, out.quality, out.scores, scan.non_c4_files,
            versions=out.versions)
        (od / "评审报告.md").write_text(out.markdown, encoding="utf-8")
        out.excel_path = generate_excel(out.completeness, out.quality, out.scores,
                                        od / "评审数据.xlsx")
        out.html_path = generate_html(folder, out.completeness, out.quality, out.scores,
                                      od / "评审仪表板.html")

    return out
