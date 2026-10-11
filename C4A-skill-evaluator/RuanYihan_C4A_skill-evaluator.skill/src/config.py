"""config.py —— 常量、路径解析与评审信号加载。

设计原则：
  1. 单一事实来源：评审所需的「检测信号」全部从 references/c4_rubric.yaml 读取，
     不在此处硬编码关键词，避免代码与规则分叉。
  2. 命名规范：所有交付文件名遵循 Elite20 规范 `姓名拼音_C4A_内容描述.扩展名`。
  3. 路径无关：本技能只接受「一个本地文件夹路径」作为输入，不依赖任何绝对路径。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PACKAGE_ROOT / "references"
DEFAULT_RUBRIC = REFERENCES_DIR / "c4_rubric.yaml"

# 输入文件大小上限（字节）：超过则跳过内容分析，仅做文件名/类型匹配
MAX_CONTENT_SCAN_BYTES = 50 * 1024 * 1024  # 50 MB


# ---------------------------------------------------------------------------
# 命名规范
# ---------------------------------------------------------------------------
# 目标形态：姓名拼音_C4A_内容描述.扩展名（如 RuanYihan_C4A_方案设计.md）
# 兼容 C4 的 `_C4_` 标记，以及常见的 `_C4A_` 变体。
C4A_TAG_PATTERNS = [
    re.compile(r"_C4A?_", re.IGNORECASE),   # _C4_ / _C4A_
    re.compile(r"[-_]c4[-_]", re.IGNORECASE),  # -c4- / _c4_
]

# 版本追踪：_v2 / _V2 / _v2.1 / (2) 等（位于扩展名前，如 `_v2.skill`）
VERSION_PATTERN = re.compile(r"(_v?\d+(?:\.\d+)?|\(\d+\))\s*$", re.IGNORECASE)

# 非 C4 文件（混入文件夹）也会被报告，但会被标记为非 C4
EXCLUDED_DIRS = {".git", "__pycache__", ".idea", ".vscode", "node_modules"}


# ---------------------------------------------------------------------------
# 合规输入校验
# ---------------------------------------------------------------------------
def is_valid_c4_filename(filename: str) -> bool:
    """判断文件名是否带有 C4 提交标记。"""
    return any(p.search(filename) for p in C4A_TAG_PATTERNS)


def strip_version_tag(filename: str) -> tuple[str, str | None]:
    """拆出版本标记（如 _v2 / (2)），返回 (去版本名, 版本号或 None)。

    版本标记位于扩展名之前（`skill_v2.skill` -> `skill.skill` + "2"），
    与扩展名无关，避免把 `v2` 误判到 `.md` 上。
    """
    stem, dot, ext = filename.rpartition(".")
    m = VERSION_PATTERN.search(stem)
    if not m:
        return filename, None
    # 提取纯数字版本号（_v1 -> "1"，(2) -> "2"，_v2.1 -> "2.1"）
    version = re.sub(r"[^\d.]", "", m.group(1)) or None
    new_stem = stem[: m.start()] + stem[m.end():]
    return new_stem + dot + ext, version


def extract_author_from_filename(filename: str) -> str | None:
    """按命名规范从文件名提取作者（`_C4_` 或 `_C4A_` 之前的部分）。

    例：`RuanYihan_C4A_方案设计.md` -> `RuanYihan`；
        `ZhangSan_C4_skill说明.md`   -> `ZhangSan`。
    返回 None 表示无法从文件名判定（交由内容/元数据回退）。
    """
    for pat in C4A_TAG_PATTERNS:
        m = pat.search(filename)
        if m:
            author = filename[: m.start()].strip("_ -")
            if author:
                return author
    return None


# ---------------------------------------------------------------------------
# 信号加载
# ---------------------------------------------------------------------------
def load_rubric(rubric_path: str | os.PathLike | None = None) -> dict:
    """加载机器可读的评审规则（c4_rubric.yaml）。"""
    path = Path(rubric_path) if rubric_path else DEFAULT_RUBRIC
    if yaml is None:
        raise RuntimeError("缺少依赖 PyYAML，请先 `pip install pyyaml`")
    if not path.exists():
        raise FileNotFoundError(f"评审规则文件不存在：{path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# 文本工具
# ---------------------------------------------------------------------------
def decode_bytes(raw: bytes) -> str:
    """对文件内容做鲁棒解码：优先 UTF-8，失败回退 GBK。"""
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def normalize_text(text: str) -> str:
    """归一化文本：去空白、转小写，便于信号匹配。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\s+", " ", text).lower()
