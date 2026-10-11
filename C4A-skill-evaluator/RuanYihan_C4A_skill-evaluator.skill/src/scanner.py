"""scanner.py —— Level 1：文件采集与作者识别。

能力：
  * 递归扫描本地文件夹，识别文件名中的 `_C4_` / `_C4A_` 标记；
  * 按命名规范提取作者名；
  * 处理不规范命名（回退到子文件夹名 / 文件内容特征）；
  * 支持混合格式（.md / .docx / .pdf / .skill / .py / .mp4 / .png 等）；
  * 版本追踪：检测 `_v2`、`_v3`，报告最新版本并保留迭代历史。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import (
    EXCLUDED_DIRS,
    MAX_CONTENT_SCAN_BYTES,
    decode_bytes,
    extract_author_from_filename,
    is_valid_c4_filename,
    strip_version_tag,
)


@dataclass
class FileInfo:
    """单个被识别为 C4 提交的文件信息。"""

    path: Path
    name: str                      # 文件名（含扩展名）
    ext: str                       # 小写扩展名
    author: str                    # 归属作者（可能是 "Unknown"）
    version: str | None = None     # 版本标记（如 "2"），无则 None
    size: int = 0
    kind: str = "file"             # "file" / "binary"
    is_c4: bool = True
    source: str = "filename"       # 作者来源：filename / subfolder / metadata / content

    @property
    def rel_path(self) -> str:
        return str(self.path)


@dataclass
class ScanResult:
    """一次扫描的汇总结果。"""

    folder: str
    files: list[FileInfo] = field(default_factory=list)      # 全部 C4 相关文件
    non_c4_files: list[FileInfo] = field(default_factory=list)  # 混入的非 C4 文件
    authors: dict[str, list[FileInfo]] = field(default_factory=dict)  # 按作者分组
    skipped_binary: int = 0      # 因超大/二进制跳过内容分析的文件数
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 文本内容读取（仅对可读小文件执行，二进制只做文件名匹配）
# ---------------------------------------------------------------------------
def _read_text_safe(path: Path, max_bytes: int = MAX_CONTENT_SCAN_BYTES) -> str | None:
    """读取文本内容；超大文件或二进制返回 None（跳过内容分析）。"""
    try:
        size = path.stat().st_size
        if size > max_bytes:
            return None
        raw = path.read_bytes()
        text = decode_bytes(raw)
        if "\x00" in text[:4096]:
            return None  # 含 NUL 字节，判为二进制
        return text
    except OSError:
        return None


# 常见二进制扩展名（不做内容分析）
BINARY_EXTS = {
    ".mp4", ".mov", ".webm", ".avi", ".mkv", ".png", ".jpg", ".jpeg", ".gif",
    ".bmp", ".ico", ".zip", ".tar", ".gz", ".skill", ".exe", ".bin", ".pdf",
}


# ---------------------------------------------------------------------------
# 作者识别链
# ---------------------------------------------------------------------------
def _author_from_subfolder(path: Path) -> str | None:
    """子文件夹名兜底：若文件位于以作者命名的子目录下，取该目录名。"""
    parent = path.parent
    if parent.name and parent.name not in EXCLUDED_DIRS:
        name = parent.name.strip("_ -")
        if name and not name.lower().startswith(("c4", "wechat", "群", "提交")):
            return name
    return None


def _author_from_content_heuristic(text: str | None, name: str) -> str | None:
    """内容兜底：从文档头部提取作者特征（如 `提交人：X` / `作者：X`）。"""
    if not text:
        return None
    import re

    for pat in [
        re.compile(r"(?:提交人|作者|姓名)\s*[：:]\s*([\u4e00-\u9fa5A-Za-z]{2,20})"),
        re.compile(r"^#\s*([\u4e00-\u9fa5A-Za-z]{2,20})\s*[—\-—–]"),
    ]:
        m = pat.search(text[:2000])
        if m:
            return m.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# 扫描主入口
# ---------------------------------------------------------------------------
def scan_folder(folder: str) -> ScanResult:
    """递归扫描文件夹，返回按作者分组的 C4 文件清单。"""
    root = Path(folder)
    if not root.exists():
        raise FileNotFoundError(f"文件夹不存在：{folder}")
    if not root.is_dir():
        raise NotADirectoryError(f"不是文件夹：{folder}")

    result = ScanResult(folder=str(root))

    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        name = path.name
        ext = path.suffix.lower()

        if not is_valid_c4_filename(name):
            # 非 C4 文件，记录但不参与评审（便于报告“非 C4 文件”）
            result.non_c4_files.append(
                FileInfo(path=path, name=name, ext=ext, author="—",
                         size=path.stat().st_size,
                         kind="binary" if ext in BINARY_EXTS else "file",
                         is_c4=False)
            )
            continue

        # 版本追踪
        base_name, version = strip_version_tag(name)

        # 读取文本内容：无论作者识别是否成功都要读，
        # 因为 Level 3 质量评审需要基于文件内容（单一扫描，一次读取）。
        text = None
        if ext not in BINARY_EXTS:
            text = _read_text_safe(path)

        # 作者识别链：文件名 → 子文件夹 → 内容
        author = extract_author_from_filename(name)
        source = "filename"
        if author is None:
            author = _author_from_subfolder(path)
            source = "subfolder"
        if author is None and text:
            cand = _author_from_content_heuristic(text, name)
            if cand:
                author = cand
                source = "content"
        if author is None:
            author = "Unknown"
            source = "unknown"

        info = FileInfo(
            path=path, name=name, ext=ext, author=author, version=version,
            size=path.stat().st_size,
            kind="binary" if (ext in BINARY_EXTS or text is None) else "file",
            is_c4=True, source=source,
        )
        if text is not None:
            info._content = text  # type: ignore[attr-defined]
        result.files.append(info)
        result.authors.setdefault(author, []).append(info)

    return result
