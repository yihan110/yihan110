"""completeness.py —— Level 2：提交完整性检查。

对照 c4_rubric.yaml 的 required_deliverables，对每个作者的提交检查
C4 要求的五个必需文件是否齐全，并给出具体缺失项。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import load_rubric, normalize_text


@dataclass
class CompletenessItem:
    key: str
    label: str
    present: bool = False
    matched_files: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    fuzzy: bool = False   # True = 仅在内容层命中（文件名未命中），需人工复核


@dataclass
class CompletenessResult:
    author: str
    items: dict[str, CompletenessItem] = field(default_factory=dict)
    present_count: int = 0
    total: int = 5

    @property
    def status(self) -> str:
        """✅ 齐全(5/5) / ⚠️ 部分缺失(3-4/5) / ❌ 严重缺失(<3/5)"""
        if self.present_count >= self.total:
            return "齐全"
        if self.present_count >= 3:
            return "部分缺失"
        return "严重缺失"

    @property
    def score(self) -> float:
        return self.present_count / self.total


def _file_matches_filename(name_lower: str, patterns: list[str]) -> bool:
    return any(p.lower() in name_lower for p in patterns)


def _text_hits(text: str, signals: list[str]) -> list[str]:
    """返回命中的内容信号（归一化后做包含匹配）。"""
    norm = normalize_text(text)
    hits = []
    for s in signals:
        if s.lower() in norm:
            hits.append(s)
    return hits


def check_completeness(
    author: str,
    files: list,
    rubric: dict | None = None,
) -> CompletenessResult:
    """对单个作者的全部文件做五必需文件完整性检查。

    两遍检测以降低误判率：
      第一遍（权威）：按文件名模式匹配 → 命中即计为「已提供」。
      第二遍（回退）：仅对仍未命中的必需文件，扫描其余文件内容层信号，
                     用于拯救命名不规范但内容确实存在的提交；内容命中标记
                     为「⚠️ 需人工复核」，避免误判。

    files: scanner 输出的 FileInfo 列表（含可选 `_content`）。
    """
    rubric = rubric or load_rubric()
    req = rubric.get("required_deliverables", {})
    result = CompletenessResult(author=author)

    for key, spec in req.items():
        label = spec.get("label_cn", key)
        item = CompletenessItem(key=key, label=label)
        # c4_rubric.yaml 中检测信号统一嵌套在 detection 下（单一事实来源）
        det = spec.get("detection", {})
        filename_patterns = det.get("filename_patterns", [])
        content_signals = det.get("content_signals", [])
        preferred_ext = det.get("preferred_extensions", [])

        # 第一遍：文件名命中（权威信号）
        for fi in files:
            if _file_matches_filename(fi.name.lower(), filename_patterns):
                item.present = True
                item.matched_files.append(fi.name)
                item.evidence.append(f"文件名命中: {fi.name}")
        if item.present:
            result.items[key] = item
            continue

        # 第二遍：内容回退（仅当文件名层未命中该必需文件时）
        for fi in files:
            if fi.ext not in preferred_ext:
                continue
            if fi.name in item.matched_files:
                continue
            content = getattr(fi, "_content", None)
            if content and _text_hits(content, content_signals):
                item.present = True
                item.fuzzy = True
                item.matched_files.append(fi.name)
                item.evidence.append(f"内容命中: {fi.name}")
        result.items[key] = item

    result.present_count = sum(1 for it in result.items.values() if it.present)
    return result
