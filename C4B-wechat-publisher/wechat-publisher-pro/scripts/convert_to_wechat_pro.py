#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wechat-publisher-pro — Markdown / Word → 微信公众号 HTML（增强版）

在 starter kit (c4b-wechat-publisher-starter) 的基础上做了以下增强：

  1. 主题系统           --theme default|accent|warm|green|minimal
  2. Callout 高亮框      > [!NOTE] / [!TIP] / [!WARNING] / [!DANGER] / [!IMPORTANT] / [!PRACTICE]
  3. 自动目录           --toc
  4. 文章元数据          YAML frontmatter（title / author / date / digest / cover）
  5. 页脚版权声明        --footer / --no-footer
  6. 中文排版优化        --pangu（中英文自动加细间距）+ 标点规范化 + 段落样式
  7. 数学公式            $...$ 与 $$...$$ → PNG base64（matplotlib mathtext）
  8. 图片处理            本地图片自动转 base64 内嵌；外链图片给出告警
  9. 批量转换            --batch <dir>
 10. 多格式输出          --formats wechat,zhihu,plain
 11. 模板系统            --template tutorial|notes|product|post
 12. 自检 / 校验         --selftest  与  --validate <file.html>

用法举例：
    python convert_to_wechat_pro.py article.md out.html --theme accent --toc
    python convert_to_wechat_pro.py article.md --outdir dist --formats wechat,zhihu,plain
    python convert_to_wechat_pro.py --batch articles/ --outdir dist --template tutorial
    python convert_to_wechat_pro.py --selftest
    python convert_to_wechat_pro.py --validate out.html

然后：浏览器打开 out.html → 「复制正文」按钮 → 粘贴到 mp.weixin.qq.com 编辑器。
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import sys
import tempfile
from pathlib import Path

# ------------------------------------------------------------------
# Windows 控制台兼容：把 stdout/stderr 切到 UTF-8，避免 emoji 触发
# UnicodeEncodeError: 'gbk' codec can't encode character ...
# （这是 starter kit 在中文 Windows 上的真实崩溃点，见 AI日志）
# ------------------------------------------------------------------
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    try:
        if _stream is not None and hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover - 环境差异兜底
        pass

# matplotlib 默认会把字体缓存写进用户 AppData，在受限环境下会被拒绝；
# 显式指到临时目录，保证公式渲染在任何环境都能跑。
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "wxp_mpl_cache"))


# ============================================================
# 依赖
# ============================================================

REQUIRED = {
    "markdown": "markdown",
    "bs4": "beautifulsoup4",
    "docx": "python-docx",
    "lxml": "lxml",
}


def ensure_dependencies() -> None:
    """缺失依赖时自动安装（沿用 starter 的做法，但打印信息全部 ASCII 安全）。"""
    missing = []
    for module, pkg in REQUIRED.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("[deps] installing: " + ", ".join(missing))
        import subprocess

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *missing, "-q"]
        )
        print("[deps] done")


ensure_dependencies()

import markdown  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

try:  # python-docx 只在处理 .docx 时才真正需要
    from docx import Document  # noqa: E402
except Exception:  # pragma: no cover
    Document = None  # type: ignore


# ============================================================
# 主题系统（新增能力 #1）
# ============================================================

THEMES: dict[str, dict[str, str]] = {
    "default": {
        "label": "经典蓝",
        "primary": "#2b6cb0",
        "h2": "#1a365d",
        "h2_rule": "#2b6cb0",
        "h3": "#2b6cb0",
        "body": "#333333",
        "muted": "#8a94a6",
        "link": "#2b6cb0",
        "quote_bg": "#f7f9fc",
        "quote_border": "#2b6cb0",
        "quote_text": "#4a5568",
        "code_bg": "#f6f8fa",
        "code_fg": "#24292e",
        "ci_bg": "#eef2f7",
        "ci_fg": "#b02a37",
        "th_bg": "#eef2f7",
        "th_fg": "#1a365d",
        "td_border": "#dfe6ee",
        "box_bg": "#f7f9fc",
        "box_border": "#dfe6ee",
        "hr": "#d8e0ea",
    },
    "accent": {
        "label": "科技蓝",
        "primary": "#1a73e8",
        "h2": "#0b3d91",
        "h2_rule": "#1a73e8",
        "h3": "#1a73e8",
        "body": "#2f3640",
        "muted": "#7b8794",
        "link": "#1a73e8",
        "quote_bg": "#f0f7ff",
        "quote_border": "#1a73e8",
        "quote_text": "#3c4858",
        "code_bg": "#f3f6fb",
        "code_fg": "#1f2933",
        "ci_bg": "#e8f0fe",
        "ci_fg": "#1967d2",
        "th_bg": "#e8f0fe",
        "th_fg": "#0b3d91",
        "td_border": "#d7e3f4",
        "box_bg": "#f0f7ff",
        "box_border": "#cfe0f7",
        "hr": "#d3e0f2",
    },
    "warm": {
        "label": "暖橙",
        "primary": "#e8710a",
        "h2": "#8a3b00",
        "h2_rule": "#e8710a",
        "h3": "#c2560a",
        "body": "#3a3a3a",
        "muted": "#9a8c7d",
        "link": "#c2560a",
        "quote_bg": "#fff8ee",
        "quote_border": "#f2a54a",
        "quote_text": "#5a4a3a",
        "code_bg": "#fbf6ef",
        "code_fg": "#4a3f33",
        "ci_bg": "#fdeedd",
        "ci_fg": "#b35309",
        "th_bg": "#fdeedd",
        "th_fg": "#8a3b00",
        "td_border": "#f0e0cc",
        "box_bg": "#fff8ee",
        "box_border": "#f3ddc0",
        "hr": "#eddfcc",
    },
    "green": {
        "label": "微信绿",
        "primary": "#07c160",
        "h2": "#0b6b39",
        "h2_rule": "#07c160",
        "h3": "#07914a",
        "body": "#333a35",
        "muted": "#82948a",
        "link": "#07914a",
        "quote_bg": "#f2fbf6",
        "quote_border": "#07c160",
        "quote_text": "#3f5047",
        "code_bg": "#f4f8f6",
        "code_fg": "#26332c",
        "ci_bg": "#e6f7ee",
        "ci_fg": "#0b6b39",
        "th_bg": "#e6f7ee",
        "th_fg": "#0b6b39",
        "td_border": "#d6eadf",
        "box_bg": "#f2fbf6",
        "box_border": "#cdeadb",
        "hr": "#d8e9e0",
    },
    "minimal": {
        "label": "极简灰",
        "primary": "#3d4451",
        "h2": "#1f2328",
        "h2_rule": "#c9ced6",
        "h3": "#3d4451",
        "body": "#3d4451",
        "muted": "#9aa1ab",
        "link": "#3d4451",
        "quote_bg": "#fafafa",
        "quote_border": "#c9ced6",
        "quote_text": "#6b7280",
        "code_bg": "#f7f7f8",
        "code_fg": "#2f3640",
        "ci_bg": "#f0f1f3",
        "ci_fg": "#5b616b",
        "th_bg": "#f4f5f7",
        "th_fg": "#1f2328",
        "td_border": "#e3e5e8",
        "box_bg": "#fafafa",
        "box_border": "#e3e5e8",
        "hr": "#e3e5e8",
    },
}

DEFAULT_THEME = "default"


# ============================================================
# 模板系统（新增能力 #11）
# ============================================================

TEMPLATES: dict[str, dict[str, object]] = {
    "tutorial": {"theme": "accent", "toc": True, "footer": True, "digest": True},
    "notes": {"theme": "warm", "toc": True, "footer": True, "digest": True},
    "product": {"theme": "green", "toc": False, "footer": True, "digest": True},
    "post": {"theme": "default", "toc": False, "footer": True, "digest": False},
}


# ============================================================
# Callout 类型表（新增能力 #2）
# ============================================================

CALLOUTS: dict[str, dict[str, str]] = {
    "note": {"icon": "📘", "label": "知识点", "color": "#1a73e8", "bg": "#f0f7ff"},
    "tip": {"icon": "💡", "label": "小技巧", "color": "#0f9d58", "bg": "#f0fbf4"},
    "important": {"icon": "❗", "label": "重点", "color": "#d93025", "bg": "#fdecea"},
    "warning": {"icon": "⚠️", "label": "注意", "color": "#e8710a", "bg": "#fff8e1"},
    "danger": {"icon": "🚫", "label": "避坑", "color": "#c5221f", "bg": "#fdecea"},
    "practice": {"icon": "🔧", "label": "动手实践", "color": "#7b1fa2", "bg": "#f7f0fd"},
    "success": {"icon": "✅", "label": "完成", "color": "#0f9d58", "bg": "#f0fbf4"},
    "quote": {"icon": "💬", "label": "引言", "color": "#5f6368", "bg": "#f8f9fa"},
    "info": {"icon": "ℹ️", "label": "说明", "color": "#1a73e8", "bg": "#f0f7ff"},
    "question": {"icon": "❓", "label": "思考", "color": "#e8710a", "bg": "#fff8e1"},
}

# 中文别名 → 规范类型
CALLOUT_ALIAS: dict[str, str] = {
    "知识": "note", "知识点": "note", "note": "note",
    "提示": "tip", "技巧": "tip", "tip": "tip",
    "重点": "important", "重要": "important", "important": "important",
    "注意": "warning", "警告": "warning", "warning": "warning",
    "避坑": "danger", "危险": "danger", "danger": "danger",
    "实践": "practice", "动手": "practice", "practice": "practice",
    "完成": "success", "成功": "success", "success": "success",
    "引言": "quote", "引用": "quote", "quote": "quote",
    "说明": "info", "info": "info",
    "思考": "question", "问题": "question", "question": "question",
}


# ============================================================
# HTML / CSS 白名单（WeChat 规则）
# ============================================================

ALLOWED_TAGS = {
    "p", "h2", "h3", "ul", "ol", "li", "span", "img", "a",
    "table", "tr", "th", "td", "br", "strong", "b", "em", "i",
}

# 会被整体删除（不是 unwrap）的标签
DROP_TAGS = {"script", "style", "iframe", "video", "audio", "svg", "canvas", "form", "input", "button", "object", "embed", "link", "meta"}

# 允许出现在 inline style 里的 CSS 属性（starter 里定义了 ALLOWED_CSS 却从未使用 —— 这里真正生效）
ALLOWED_CSS = {
    "color", "background-color", "font-size", "font-weight", "font-style",
    "font-family", "line-height", "text-align", "text-indent", "text-decoration",
    "letter-spacing", "word-break", "overflow-wrap", "white-space",
    "margin", "margin-top", "margin-bottom", "margin-left", "margin-right",
    "padding", "padding-top", "padding-bottom", "padding-left", "padding-right",
    "border", "border-top", "border-bottom", "border-left", "border-right",
    "border-radius", "border-collapse", "display", "vertical-align",
    "max-width", "width", "height", "list-style-type", "list-style-position",
}

# 段落分隔符：starter 里 `---` 生成的 <hr> 不在白名单里被直接丢掉（真实缺陷），这里改为居中圆点
HR_HTML = (
    '<p style="margin:24px 0; text-align:center; color:{hr}; '
    'letter-spacing:8px; font-size:14px; line-height:1;">· · ·</p>'
)


# ============================================================
# 工具函数
# ============================================================

# 只对「汉字」加间距，绝不把全角标点（：、。！？等）当成需要加空格的边界，
# 否则会出现「坑 1 ： emoji」「1.75 、给引用」这类错位。
_CJK = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_RE_CJK_LATIN = re.compile(rf"([{_CJK}])([A-Za-z0-9])")
_RE_LATIN_CJK = re.compile(rf"([A-Za-z0-9])([{_CJK}])")

THIN_SPACE = "\u2009"


def pangu(text: str) -> str:
    """在中文与英文/数字之间插入细间距（盘古之白），提升中文排版观感。"""
    if not text:
        return text
    text = _RE_CJK_LATIN.sub(lambda m: m.group(1) + THIN_SPACE + m.group(2), text)
    text = _RE_LATIN_CJK.sub(lambda m: m.group(1) + THIN_SPACE + m.group(2), text)
    return text


def sanitize_css(style: str) -> str:
    """只保留白名单内的 CSS 属性。"""
    if not style:
        return ""
    kept = []
    for decl in style.split(";"):
        if ":" not in decl:
            continue
        prop, _, value = decl.partition(":")
        prop = prop.strip().lower()
        if prop in ALLOWED_CSS:
            kept.append(f"{prop}: {value.strip()}")
    return "; ".join(kept)


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ============================================================
# 元数据（新增能力 #4）：解析 YAML frontmatter
# ============================================================

def split_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """解析文件头部的 --- key: value --- 元数据块。"""
    meta: dict[str, str] = {}
    if not raw.lstrip().startswith("---"):
        return meta, raw
    lines = raw.splitlines()
    # 找到起始 ---
    start = next(i for i, l in enumerate(lines) if l.strip() == "---")
    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return meta, raw
    for line in lines[start + 1:end]:
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        meta[k.strip().lower()] = v.strip().strip('"').strip("'")
    body = "\n".join(lines[end + 1:])
    return meta, body


# ============================================================
# 数学公式（新增能力 #7）：LaTeX → PNG base64
# ============================================================

_MATH_TOKEN = "@@WXMATH{}@@"


def _render_math_png(latex: str, fontsize: int = 20, color: str = "#24292e") -> str | None:
    """用 matplotlib mathtext 把 LaTeX 渲染成透明底 PNG，返回 data URI。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    try:
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, f"${latex}$", fontsize=fontsize, color=color)
        buf = __import__("io").BytesIO()
        fig.savefig(
            buf, format="png", dpi=200, transparent=True,
            bbox_inches="tight", pad_inches=0.05,
        )
        plt.close(fig)
        data = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{data}"
    except Exception:
        try:
            plt.close("all")
        except Exception:
            pass
        return None


def extract_math(text: str, warnings: list[str]) -> tuple[str, dict[str, str]]:
    """
    把 Markdown 里的 $$...$$ / $...$ 替换为占位 token，并返回 token → <img> 映射。
    先处理块级 $$...$$，再处理行内 $...$。
    """
    store: dict[str, str] = {}
    counter = [0]

    def _make(latex: str, block: bool) -> str:
        idx = counter[0]
        counter[0] += 1
        token = _MATH_TOKEN.format(idx)
        uri = _render_math_png(latex)
        if uri is None:
            warnings.append(f"数学公式渲染失败，已保留原始 LaTeX：{latex[:40]}")
            store[token] = (
                f'<span style="font-family: monospace; color:#b02a37;">${esc(latex)}$</span>'
            )
        else:
            width = "max-width:100%;" if block else "vertical-align:middle;max-width:100%;"
            store[token] = (
                f'<img src="{uri}" alt="{esc(latex)}" style="{width}height:auto;" />'
            )
        return token

    def _block(m: re.Match) -> str:
        return "\n\n" + _make(m.group(1).strip(), True) + "\n\n"

    def _inline(m: re.Match) -> str:
        return _make(m.group(1).strip(), False)

    text = re.sub(r"\$\$(.+?)\$\$", _block, text, flags=re.S)
    text = re.sub(r"(?<!\$)\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\$)", _inline, text)
    return text, store


# ============================================================
# 输入读取
# ============================================================

MARKDOWN_EXTENSIONS = ["extra", "sane_lists", "smarty"]

# 在 Markdown 解析前先把 > [!TYPE] 引用块改写成可识别的占位段落。
# 为什么必须在解析前做？因为 python-markdown 会把
#     > [!NOTE] 标题
#     > 正文
# 合并成 *同一个* <p>，标题与正文混在一条文本里，无法稳定拆分。
# 预处理器逐行扫描，天然保留"标记行 / 正文行"的边界。
_CALLOUT_MARK = re.compile(
    r"^\s*>\s*(?:\[!\s*([A-Za-z\u4e00-\u9fff]+)\s*\]|【\s*([A-Za-z\u4e00-\u9fff]+)\s*】)\s*(.*)$"
)
_QUOTE_LINE = re.compile(r"^\s*>")


def preprocess_callouts(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        m = _CALLOUT_MARK.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue

        key = (m.group(1) or m.group(2) or "note").lower()
        title = (m.group(3) or "").strip().strip("`")
        i += 1
        body_lines: list[str] = []
        while i < len(lines) and _QUOTE_LINE.match(lines[i]):
            body_lines.append(re.sub(r"^\s*>\s?", "", lines[i]))
            i += 1
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()

        inner_md = "\n".join(body_lines)
        inner_html = ""
        if inner_md.strip():
            rendered = markdown.markdown(inner_md, extensions=MARKDOWN_EXTENSIONS)
            frag = BeautifulSoup(rendered, "lxml")
            blocks = [p.decode_contents() for p in frag.find_all("p")]
            if not blocks:
                blocks = [inner_md]
            inner_html = "<br>".join(b.replace("\n", " ") for b in blocks)

        safe_title = title.replace('"', "&quot;")
        out.append(
            f'<p data-wxcallout="{key}" data-wx-title="{safe_title}">{inner_html}</p>'
        )
        out.append("")
    return "\n".join(out)


def _remove_leading_nodes(el, count: int) -> None:
    """从元素开头删除前 count 个字符（用于剥掉 blockquote 里的 [!TYPE] 标记）。"""
    remaining = count
    for node in list(el.find_all(string=True)):
        if remaining <= 0:
            break
        s = str(node)
        if len(s) <= remaining:
            remaining -= len(s)
            node.extract()
        else:
            node.replace_with(s[remaining:])
            remaining = 0


def read_markdown(filepath: str) -> tuple[str, dict[str, str], dict[str, str], list[str]]:
    """读取 Markdown，返回 (html, meta, math_store, warnings)。"""
    raw = None
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            raw = Path(filepath).read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if raw is None:
        raise ValueError(f"无法解码文件（尝试 utf-8 / gbk 均失败）：{filepath}")

    meta, body = split_frontmatter(raw)
    warnings: list[str] = []
    body = preprocess_callouts(body)
    body, math_store = extract_math(body, warnings)
    html = markdown.markdown(body, extensions=MARKDOWN_EXTENSIONS)
    return html, meta, math_store, warnings


def _docx_para_html(para) -> str:
    """把 Word 段落转成 HTML（保留标题层级与行内加粗/斜体，且保留嵌套文本）。"""
    text = para.text.strip()
    if not text:
        return ""
    style_name = (para.style.name if para.style else "") or ""
    m = re.match(r"Heading\s*([1-6])", style_name)
    if m:
        level = int(m.group(1))
        tag = "h2" if level <= 2 else "h3"
        return f"<{tag}>{esc(text)}</{tag}>"
    if style_name.startswith("List"):
        return f"<li>{esc(text)}</li>"

    parts = ["<p>"]
    for run in para.runs:
        t = run.text
        if not t:
            continue
        t = esc(t)
        if run.bold and run.italic:
            parts.append(f"<strong><em>{t}</em></strong>")
        elif run.bold:
            parts.append(f"<strong>{t}</strong>")
        elif run.italic:
            parts.append(f"<em>{t}</em>")
        else:
            parts.append(t)
    parts.append("</p>")
    return "".join(parts)


def read_docx(filepath: str) -> tuple[str, dict[str, str], dict[str, str], list[str]]:
    if Document is None:
        raise RuntimeError("未安装 python-docx，无法读取 .docx")
    doc = Document(filepath)
    chunks: list[str] = []
    list_open = False
    for para in doc.paragraphs:
        style_name = (para.style.name if para.style else "") or ""
        is_list = style_name.startswith("List")
        if is_list and not list_open:
            chunks.append("<ul>")
            list_open = True
        elif not is_list and list_open:
            chunks.append("</ul>")
            list_open = False
        chunks.append(_docx_para_html(para))
    if list_open:
        chunks.append("</ul>")

    # Word 表格
    for table in doc.tables:
        rows = []
        for r_i, row in enumerate(table.rows):
            cells = "".join(
                f"<{'th' if r_i == 0 else 'td'}>{esc(c.text.strip())}</{'th' if r_i == 0 else 'td'}>"
                for c in row.cells
            )
            rows.append(f"<tr>{cells}</tr>")
        chunks.append("<table>" + "".join(rows) + "</table>")

    meta: dict[str, str] = {}
    props = getattr(doc, "core_properties", None)
    if props is not None:
        if props.title:
            meta["title"] = props.title
        if props.author:
            meta["author"] = props.author
    return "\n".join(chunks), meta, {}, []


# ============================================================
# HTML 清洗与结构改写
# ============================================================

def _wrap_preserving(el, soup, style: str):
    """用带样式的 <span> 包裹元素，同时保留其内部的嵌套结构（修掉 starter 用 get_text() 丢格式的 bug）。"""
    span = soup.new_tag("span")
    span["style"] = style
    for child in list(el.contents):
        span.append(child.extract())
    el.replace_with(span)


def sanitize(html: str, theme: dict[str, str]) -> BeautifulSoup:
    soup = BeautifulSoup(html, "lxml")

    # 1) 彻底删除危险/不被支持的标签
    for name in DROP_TAGS:
        for el in soup.find_all(name):
            el.decompose()

    # 2) <pre><code> → 代码块段落（带语言标签）
    for pre in soup.find_all("pre"):
        code = pre.find("code")
        code_text = (code.get_text() if code else pre.get_text()).rstrip("\n")
        lang = ""
        if code is not None:
            for cls in code.get("class", []) or []:
                if cls.startswith("language-"):
                    lang = cls[len("language-"):]
        block = soup.new_tag("p")
        block["style"] = (
            f"background-color: {theme['code_bg']}; color: {theme['code_fg']}; "
            "font-size: 13.5px; line-height: 1.7; padding: 14px 16px; margin: 14px 0; "
            "border-radius: 8px; font-family: Consolas, Menlo, Monaco, monospace; "
            "white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere;"
        )
        if lang:
            label = soup.new_tag("span")
            label["style"] = (
                f"display: block; font-size: 11px; letter-spacing: 1px; "
                f"color: {theme['muted']}; margin-bottom: 6px; text-transform: uppercase;"
            )
            label.string = lang
            block.append(label)
        # 用 <br> 保留换行（WeChat 不支持 white-space:pre 的可靠渲染）
        lines = code_text.split("\n")
        for i, line in enumerate(lines):
            if i:
                block.append(soup.new_tag("br"))
            block.append(line)
        pre.replace_with(block)

    # 3) 行内 <code> → 带样式的 <span>
    for code in soup.find_all("code"):
        span = soup.new_tag("span")
        span["style"] = (
            f"background-color: {theme['ci_bg']}; color: {theme['ci_fg']}; "
            "font-size: 14px; padding: 2px 6px; border-radius: 4px; "
            "font-family: Consolas, Menlo, Monaco, monospace;"
        )
        for child in list(code.contents):
            span.append(child.extract())
        code.replace_with(span)

    # 4) strong / em → span（保留内部结构）
    for tag in soup.find_all(["strong", "b"]):
        _wrap_preserving(tag, soup, f"font-weight: bold; color: {theme['h2']};")
    for tag in soup.find_all(["em", "i"]):
        _wrap_preserving(tag, soup, "font-style: italic;")

    # 5) h1 → 文章标题块（WeChat 不允许 h1）；h4~h6 → h3
    for h1 in soup.find_all("h1"):
        h1.name = "h2"
    for h in soup.find_all(["h4", "h5", "h6"]):
        h.name = "h3"

    # 6) <hr> → 居中圆点分隔（starter 里 <hr> 被静默丢弃）
    for hr in soup.find_all("hr"):
        p = soup.new_tag("p")
        p["style"] = (
            f"margin: 24px 0; text-align: center; color: {theme['hr']}; "
            "letter-spacing: 8px; font-size: 14px; line-height: 1;"
        )
        p.string = "· · ·"
        hr.replace_with(p)

    # 7a) 预处理阶段写入的 callout 段落 → 主题化高亮框
    for holder in soup.find_all("p", attrs={"data-wxcallout": True}):
        ctype = CALLOUT_ALIAS.get(str(holder["data-wxcallout"]).lower(), "note")
        spec = CALLOUTS[ctype]
        title = holder.get("data-wx-title") or spec["label"]
        box = soup.new_tag("p")
        box["style"] = (
            f"background-color: {spec['bg']}; border-left: 4px solid {spec['color']}; "
            "border-radius: 6px; padding: 12px 15px; margin: 16px 0; "
            f"font-size: 15px; line-height: 1.8; color: {theme['body']};"
        )
        head = soup.new_tag("span")
        head["style"] = (
            f"display: block; font-weight: bold; color: {spec['color']}; "
            "font-size: 15px; margin-bottom: 4px;"
        )
        head.string = f"{spec['icon']} {title}"
        box.append(head)
        for child in list(holder.contents):
            box.append(child.extract())
        holder.replace_with(box)

    # 7b) 剩余 blockquote → callout（兜底）或普通引用块
    quote_style = (
        f"background-color: {theme['quote_bg']}; color: {theme['quote_text']}; "
        f"border-left: 4px solid {theme['quote_border']}; border-radius: 0 6px 6px 0; "
        "padding: 12px 16px; margin: 16px 0; font-size: 15px; line-height: 1.8;"
    )
    for bq in soup.find_all("blockquote"):
        paras = bq.find_all("p")
        if not paras:
            text = bq.get_text().strip()
            if not text:
                bq.decompose()
                continue
            p = soup.new_tag("p")
            p["style"] = quote_style
            p.string = text
            bq.replace_with(p)
            continue

        m = _CALLOUT_MARK.match(paras[0].get_text())
        if m:
            key = (m.group(1) or m.group(2) or "note").lower()
            spec = CALLOUTS[CALLOUT_ALIAS.get(key, "note")]
            _remove_leading_nodes(paras[0], m.end())
            box = soup.new_tag("p")
            box["style"] = (
                f"background-color: {spec['bg']}; border-left: 4px solid {spec['color']}; "
                "border-radius: 6px; padding: 12px 15px; margin: 16px 0; "
                f"font-size: 15px; line-height: 1.8; color: {theme['body']};"
            )
            head = soup.new_tag("span")
            head["style"] = (
                f"display: block; font-weight: bold; color: {spec['color']}; "
                "font-size: 15px; margin-bottom: 4px;"
            )
            head.string = f"{spec['icon']} {spec['label']}"
            box.append(head)
            for idx, para in enumerate(paras):
                if idx:
                    box.append(soup.new_tag("br"))
                for child in list(para.contents):
                    box.append(child.extract())
            bq.replace_with(box)
        else:
            p = soup.new_tag("p")
            p["style"] = quote_style
            for idx, para in enumerate(paras):
                if idx:
                    p.append(soup.new_tag("br"))
                for child in list(para.contents):
                    p.append(child.extract())
            bq.replace_with(p)

    return soup


def apply_styles(soup: BeautifulSoup, theme: dict[str, str]) -> BeautifulSoup:
    """给未设置样式的元素套上主题 inline 样式。"""
    style_map = {
        "h2": (
            f"font-size: 20px; font-weight: bold; line-height: 1.5; color: {theme['h2']}; "
            f"margin: 30px 0 14px 0; padding-left: 12px; "
            f"border-left: 4px solid {theme['h2_rule']};"
        ),
        "h3": (
            f"font-size: 17px; font-weight: bold; line-height: 1.5; color: {theme['h3']}; "
            "margin: 22px 0 10px 0;"
        ),
        "p": (
            f"font-size: 16px; line-height: 1.85; color: {theme['body']}; "
            "margin: 0 0 16px 0; letter-spacing: 0.4px; text-align: justify; "
            "word-break: break-word;"
        ),
        "li": (
            f"font-size: 16px; line-height: 1.85; color: {theme['body']}; "
            "margin: 6px 0; letter-spacing: 0.4px;"
        ),
        "ul": "margin: 12px 0 16px 0; padding-left: 22px; list-style-type: disc;",
        "ol": "margin: 12px 0 16px 0; padding-left: 22px; list-style-type: decimal;",
        "table": (
            "border-collapse: collapse; width: 100%; margin: 16px 0; "
            "font-size: 14px; line-height: 1.6;"
        ),
        "th": (
            f"background-color: {theme['th_bg']}; color: {theme['th_fg']}; font-weight: bold; "
            f"padding: 9px 10px; text-align: left; border: 1px solid {theme['td_border']};"
        ),
        "td": (
            f"padding: 9px 10px; border: 1px solid {theme['td_border']}; "
            f"color: {theme['body']}; vertical-align: top;"
        ),
        "a": f"color: {theme['link']}; text-decoration: underline; word-break: break-all;",
        "img": "max-width: 100%; height: auto; border-radius: 6px;",
    }

    for tag_name, style in style_map.items():
        for el in soup.find_all(tag_name):
            if el.get("style"):
                continue  # 不覆盖已经手工设置过的样式
            el["style"] = style
    return soup


def clean_attributes(soup: BeautifulSoup) -> BeautifulSoup:
    """移除 class / id / data-* / on*，过滤非法 CSS，unwrap 不支持的标签。"""
    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if attr in ("class", "id") or attr.startswith(("on", "data-")):
                del tag.attrs[attr]
        if tag.has_attr("style"):
            cleaned = sanitize_css(tag["style"])
            if cleaned:
                tag["style"] = cleaned
            else:
                del tag["style"]
        if tag.name not in ALLOWED_TAGS and tag.name not in (
            "html", "head", "body", "[document]",
        ):
            tag.unwrap()
    return soup


# ============================================================
# 中文排版 / 图片处理
# ============================================================

def apply_typography(soup: BeautifulSoup, enable_pangu: bool, indent: bool) -> BeautifulSoup:
    if enable_pangu:
        for text_node in list(soup.find_all(string=True)):
            parent = text_node.parent
            if parent is None or parent.name in ("code", "pre", "img"):
                continue
            s = str(text_node)
            if "://" in s or not s.strip():
                continue
            new = pangu(s)
            if new != s:
                text_node.replace_with(new)

    if indent:
        for p in soup.find_all("p"):
            existing = p.get("style", "")
            if "text-indent" not in existing:
                p["style"] = (existing + "; text-indent: 2em;").strip("; ")
    return soup


def embed_local_images(soup: BeautifulSoup, base_dir: Path, warnings: list[str]) -> BeautifulSoup:
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src.startswith("data:"):
            continue
        if re.match(r"^https?://", src):
            warnings.append(f"外链图片需上传到公众号素材库后替换：{src}")
            continue
        candidate = (base_dir / src.lstrip("/\\")).resolve()
        if candidate.exists():
            ext = candidate.suffix.lower().lstrip(".")
            mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}.get(ext, "png")
            if ext == "svg":
                warnings.append(f"SVG 在公众号保存时会丢失，请改导出 PNG：{src}")
                continue
            data = base64.b64encode(candidate.read_bytes()).decode("ascii")
            img["src"] = f"data:image/{mime};base64,{data}"
        else:
            warnings.append(f"本地图片未找到，已跳过：{src}")
    return soup


# ============================================================
# 目录 / 元数据 / 页脚
# ============================================================

def build_toc(soup: BeautifulSoup, theme: dict[str, str]) -> str:
    headings = soup.find_all(["h2", "h3"])
    if not headings:
        return ""
    items = []
    for h in headings:
        title = h.get_text().strip()
        if not title:
            continue
        if h.name == "h2":
            items.append(f'<span style="font-weight:bold;">{esc(title)}</span>')
        else:
            items.append(f'<span style="padding-left:16px;">{esc(title)}</span>')
    if not items:
        return ""
    body = "<br>".join(items)
    return (
        f'<p style="background-color:{theme["box_bg"]}; border:1px solid {theme["box_border"]}; '
        f'border-radius:10px; padding:14px 18px; margin:18px 0 26px 0; font-size:15px; '
        f'line-height:2; color:{theme["body"]};">'
        f'<span style="display:block; font-weight:bold; color:{theme["primary"]}; '
        f'font-size:15px; margin-bottom:6px;">📑 本文目录</span>{body}</p>'
    )


def build_meta_block(meta: dict[str, str], theme: dict[str, str], opt: dict) -> str:
    pieces = []
    author = meta.get("author") or opt.get("author")
    date = meta.get("date") or opt.get("date")
    subtitle = meta.get("subtitle") or meta.get("sub_title")
    digest = meta.get("digest") or meta.get("abstract") or meta.get("summary")

    if subtitle:
        pieces.append(
            f'<p style="text-align:center; font-size:16px; color:{theme["muted"]}; '
            f'line-height:1.7; margin:0 0 10px 0;">{esc(subtitle)}</p>'
        )
    info = " · ".join(x for x in (author, date) if x)
    if info:
        pieces.append(
            f'<p style="text-align:center; font-size:13px; color:{theme["muted"]}; '
            f'margin:0 0 18px 0; letter-spacing:0.5px;">{esc(info)}</p>'
        )
    if digest and opt.get("digest", True):
        pieces.append(
            f'<p style="background-color:{theme["box_bg"]}; border:1px dashed {theme["box_border"]}; '
            f'border-radius:8px; padding:12px 15px; margin:0 0 24px 0; font-size:14.5px; '
            f'line-height:1.8; color:{theme["quote_text"]};">'
            f'<span style="font-weight:bold; color:{theme["primary"]};">摘要｜</span>{esc(digest)}</p>'
        )
    return "".join(pieces)


def build_footer(opt: dict, theme: dict[str, str]) -> str:
    if not opt.get("footer", True):
        return ""
    text = opt.get("footer_text")
    if not text:
        author = opt.get("author", "")
        text = f'本文由「{author}」原创，使用 wechat-publisher-pro 技能一键排版。'
    return (
        f'<p style="margin:34px 0 0 0; padding-top:14px; border-top:1px solid {theme["hr"]}; '
        f'font-size:13px; color:{theme["muted"]}; line-height:1.8; text-align:center;">'
        f'{esc(text)}<br>欢迎转发分享 · 转载请注明出处</p>'
    )


# ============================================================
# 主流水线
# ============================================================

def resolve_options(args) -> dict:
    opt: dict = {
        "theme": args.theme or DEFAULT_THEME,
        "toc": bool(args.toc),
        "footer": not args.no_footer,
        "digest": True,
        "pangu": not args.no_pangu,
        "indent": bool(args.indent),
        "author": args.author,
        "date": args.date,
        "footer_text": args.footer,
        "formats": [f.strip() for f in (args.formats or "wechat").split(",") if f.strip()],
        "outdir": args.outdir,
    }
    if args.template:
        tpl = TEMPLATES.get(args.template, {})
        if not args.theme and tpl.get("theme"):
            opt["theme"] = str(tpl["theme"])
        if not args.toc and tpl.get("toc"):
            opt["toc"] = True
        if tpl.get("digest") is False:
            opt["digest"] = False
    if opt["theme"] not in THEMES:
        print(f"[warn] 未知主题 '{opt['theme']}'，回退到 {DEFAULT_THEME}")
        opt["theme"] = DEFAULT_THEME
    return opt


def convert_to_html(source: str, opt: dict) -> tuple[str, str, dict[str, str], list[str]]:
    """返回 (body_html, meta_title, meta, warnings)"""
    path = Path(source)
    if path.suffix.lower() == ".docx":
        raw_html, meta, math_store, warnings = read_docx(source)
    else:
        raw_html, meta, math_store, warnings = read_markdown(source)

    theme = THEMES[opt["theme"]]
    soup = sanitize(raw_html, theme)
    soup = apply_styles(soup, theme)
    soup = clean_attributes(soup)
    soup = apply_typography(soup, opt["pangu"], opt["indent"])
    soup = embed_local_images(soup, path.parent, warnings)

    # 回填数学公式图片，并只取 <body> 内的子节点
    # （直接 str(soup) 会带出 lxml 自动补全的 <html><body> 外壳 —— 这也是 starter 踩过的坑）
    body_node = soup.find("body")
    body_html = (
        "".join(str(c) for c in body_node.children)
        if body_node is not None else str(soup)
    )
    for token, img_html in math_store.items():
        body_html = body_html.replace(token, img_html)
        body_html = body_html.replace(esc(token), img_html)

    parts = []
    meta_html = build_meta_block(meta, theme, opt)
    if meta_html:
        parts.append(meta_html)
    if opt["toc"]:
        # 目录需要基于清洗后的结构，单独解析一次
        toc_soup = BeautifulSoup(body_html, "lxml")
        toc = build_toc(toc_soup, theme)
        if toc:
            parts.append(toc)
    parts.append(body_html)
    parts.append(build_footer(opt, theme))

    final_body = "\n".join(p for p in parts if p and p.strip())
    return final_body, meta.get("title", ""), meta, warnings


PREVIEW_SHELL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>公众号文章预览 · {title}</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#eef1f5; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif; }}
  .topbar {{ position:sticky; top:0; z-index:9; display:flex; align-items:center; gap:12px;
    padding:12px 20px; background:#ffffff; border-bottom:1px solid #e3e7ee; }}
  .topbar h1 {{ margin:0; font-size:15px; font-weight:600; color:#2b3445; flex:1;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .badge {{ font-size:12px; color:#fff; background:{accent}; padding:3px 10px; border-radius:20px; }}
  button {{ font-size:13px; padding:8px 16px; border-radius:8px; border:1px solid #d3dae5;
    background:#fff; color:#2b3445; cursor:pointer; }}
  button.primary {{ background:{accent}; border-color:{accent}; color:#fff; font-weight:600; }}
  button:active {{ transform:translateY(1px); }}
  .stage {{ padding:26px 16px 60px; }}
  .phone {{ max-width:414px; margin:0 auto; background:#fff; border-radius:14px;
    box-shadow:0 8px 30px rgba(20,35,60,.10); padding:22px 20px 34px; }}
  .hint {{ max-width:414px; margin:14px auto 0; font-size:12.5px; color:#7d889b; text-align:center; line-height:1.7; }}
  .toast {{ position:fixed; left:50%; bottom:34px; transform:translateX(-50%) translateY(20px);
    background:#1f2937; color:#fff; padding:10px 20px; border-radius:22px; font-size:13px;
    opacity:0; transition:.25s; pointer-events:none; }}
  .toast.show {{ opacity:1; transform:translateX(-50%) translateY(0); }}
</style>
</head>
<body>
  <div class="topbar">
    <span class="badge">{theme_label}</span>
    <h1>{title}</h1>
    <button id="copyBtn" class="primary">复制正文</button>
    <button id="copyAllBtn">复制整页 HTML</button>
  </div>
  <div class="stage">
    <div class="phone" id="article">
{body}
    </div>
  </div>
  <p class="hint">点击「复制正文」→ 打开 mp.weixin.qq.com 新建图文 → Ctrl+V 粘贴。<br>
  图片/公式已内嵌为 base64，粘贴时会被公众号自动转存到素材库。</p>
  <div class="toast" id="toast">已复制到剪贴板 ✅</div>
<script>
  function toast(msg) {{
    var t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('show');
    setTimeout(function(){{ t.classList.remove('show'); }}, 1600);
  }}
  function copyNode(node, label) {{
    var range = document.createRange(); range.selectNodeContents(node);
    var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(range);
    var ok = false;
    try {{ ok = document.execCommand('copy'); }} catch (e) {{ ok = false; }}
    sel.removeAllRanges();
    if (ok) {{ toast(label + ' 已复制 ✅'); }}
    else {{ toast('请手动 Ctrl+C 复制选中的内容'); }}
  }}
  document.getElementById('copyBtn').addEventListener('click', function() {{
    copyNode(document.getElementById('article'), '正文');
  }});
  document.getElementById('copyAllBtn').addEventListener('click', function() {{
    copyNode(document.documentElement, '整页 HTML');
  }});
</script>
</body>
</html>
"""


def to_zhihu_markdown(source: str) -> str:
    """同一份内容 → 知乎友好的 Markdown（保留标题/表格/代码，callout 降级为引用）。"""
    raw = Path(source).read_text(encoding="utf-8")
    _meta, body = split_frontmatter(raw)
    body = re.sub(r"^\[!(\w+)\]\s*(.*)$", r"> **\2**", body, flags=re.M)
    body = re.sub(r"^\[!([\u4e00-\u9fff]+)\]\s*(.*)$", r"> **\2**", body, flags=re.M)
    return body.strip() + "\n"


def to_plain_text(source: str) -> str:
    """纯文本版本（去掉 Markdown 标记，便于粘贴到不支持富文本的地方）。"""
    raw = Path(source).read_text(encoding="utf-8")
    _meta, body = split_frontmatter(raw)
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    body = re.sub(r"`([^`]*)`", r"\1", body)
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    body = re.sub(r"^\s{0,3}#{1,6}\s*", "", body, flags=re.M)
    body = re.sub(r"^\s*>\s?", "", body, flags=re.M)
    body = re.sub(r"^\s*[-*+]\s+", "· ", body, flags=re.M)
    body = re.sub(r"\*\*([^*]*)\*\*", r"\1", body)
    body = re.sub(r"\*([^*]*)\*", r"\1", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip() + "\n"


# ============================================================
# 校验（--validate）：把"可验证"做成命令
# ============================================================

def validate_html(filepath: str) -> int:
    html = Path(filepath).read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")
    problems: list[str] = []

    for name in DROP_TAGS | {"div", "h1", "h4", "h5", "h6", "pre", "blockquote", "hr"}:
        found = soup.find_all(name)
        if found:
            problems.append(f"发现违规标签 <{name}> × {len(found)}")
    for tag in soup.find_all(True):
        if tag.has_attr("class"):
            problems.append("发现 class 属性")
        if tag.has_attr("id"):
            problems.append("发现 id 属性")
        for attr in tag.attrs:
            if attr.startswith("on"):
                problems.append(f"发现事件属性 {attr}")
        if tag.has_attr("style"):
            for decl in tag["style"].split(";"):
                if ":" in decl:
                    prop = decl.split(":")[0].strip().lower()
                    if prop and prop not in ALLOWED_CSS:
                        problems.append(f"发现非白名单 CSS 属性：{prop}")

    if problems:
        seen = sorted(set(problems))
        print(f"[validate] ✗ {filepath} 发现 {len(seen)} 类问题：")
        for p in seen:
            print("   - " + p)
        return 1
    print(f"[validate] ✓ {filepath} 通过公众号 HTML 规则校验")
    return 0


# ============================================================
# 自检 / eval（--selftest）
# ============================================================

SELFTEST_ARTICLE = """---
title: 自检样例
author: ruanyihan
date: 2026-10-11
digest: 用于验证技能的 12 项能力是否全部生效。
---

# 一级标题应降级为 h2

这是正文段落，包含 English words 与 123 数字，还混排了Python3代码与Windows GBK编码。
第1步：安装依赖，版本v1.0。

## 二级标题

> [!NOTE] 关键知识点
> Callout 框应被正确识别并渲染为带底色的框。
> 支持多行正文与**加粗**。

> [!WARNING] 注意
> 这是一个警告框。

> 这是一段普通引用。

### 三级标题

- 列表项一
- 列表项二

1. 有序一
2. 有序二

| 能力 | 状态 |
|------|------|
| 主题 | ✅ |
| 目录 | ✅ |

```python
print("hello wechat")
```

行内 `code` 测试，**加粗** 与 *斜体*。

---

公式测试：$E = mc^2$

![本地图片](missing.png)
"""


def run_selftest() -> int:
    import tempfile

    print("=" * 56)
    print("wechat-publisher-pro 自检 (selftest)")
    print("=" * 56)
    checks: list[tuple[str, bool, str]] = []

    tmp = Path(tempfile.mkdtemp(prefix="wxp_selftest_"))
    src = tmp / "selftest.md"
    src.write_text(SELFTEST_ARTICLE, encoding="utf-8")

    opt = {
        "theme": "accent", "toc": True, "footer": True, "digest": True,
        "pangu": True, "indent": False, "author": "ruanyihan", "date": "2026-10-11",
        "footer_text": None, "outdir": None,
    }
    body, title, meta, warnings = convert_to_html(str(src), opt)
    out = tmp / "selftest.html"
    out.write_text(body, encoding="utf-8")

    def check(name: str, cond: bool, detail: str = ""):
        checks.append((name, bool(cond), detail))
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    check("元数据解析 title/author/date/digest", meta.get("title") == "自检样例" and meta.get("author") == "ruanyihan")
    check("h1 已降级（无 <h1>）", "<h1" not in body)
    check("h2 应用主题色 #1a73e8", "#1a73e8" in body or "1a73e8" in body)
    check("callout NOTE 渲染", "📘" in body and "知识点" in body)
    check("callout WARNING 渲染", "⚠️" in body)
    check("普通引用保留", "border-left: 4px solid #1a73e8" in body)
    check("自动目录生成", "本文目录" in body)
    check("表格保留", "<table" in body and "<th" in body)
    check("代码块转段落（无 <pre>）", "<pre" not in body and "print" in body)
    check("行内 code 保留", "font-family: Consolas" in body)
    check("加粗转 span（无 <strong>）", "<strong" not in body and "font-weight: bold" in body)
    check("斜体转 span（无 <em>）", "<em>" not in body and "font-style: italic" in body)
    check("hr 转分隔圆点（无 <hr>）", "<hr" not in body and "· · ·" in body)
    check("中英文间距（盘古之白）", "\u2009" in body)
    check("数学公式转 PNG base64", "data:image/png;base64," in body)
    check("页脚版权追加", "wechat-publisher-pro" in body)
    check("外链/缺失图片告警", any("missing.png" in w for w in warnings))
    check("无 class / id 属性", 'class="' not in body and ' id="' not in body)
    check("输出不含 <html>/<body> 外壳", "<html" not in body and "<body" not in body)
    check("全角标点前不插细空格", "1\u2009：" not in body and "\u2009，" not in body)
    check("callout 标题不含 Markdown 反引号", "`" not in body)

    rc = validate_html(str(out))
    check("输出通过公众号规则校验", rc == 0)

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    print("-" * 56)
    print(f"结果：{passed}/{total} 通过")
    if passed != total:
        print("未通过项：")
        for name, ok, detail in checks:
            if not ok:
                print(f"   - {name} {detail}")
    print("=" * 56)
    return 0 if passed == total else 1


# ============================================================
# CLI
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="convert_to_wechat_pro.py",
        description="Markdown/Word → 微信公众号 HTML（增强版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", nargs="?", help="输入文件（.md / .docx / .html）")
    p.add_argument("output", nargs="?", help="输出 HTML 路径（单文件模式）")
    p.add_argument("--theme", choices=sorted(THEMES.keys()), help="主题（默认 default）")
    p.add_argument("--template", choices=sorted(TEMPLATES.keys()), help="模板预设")
    p.add_argument("--toc", action="store_true", help="自动生成目录")
    p.add_argument("--no-footer", action="store_true", help="不追加页脚")
    p.add_argument("--footer", metavar="TEXT", help="自定义页脚文案")
    p.add_argument("--no-pangu", action="store_true", help="关闭中英文自动加空格")
    p.add_argument("--indent", action="store_true", help="段落首行缩进 2em")
    p.add_argument("--author", help="作者（覆盖 frontmatter）")
    p.add_argument("--date", help="日期（覆盖 frontmatter）")
    p.add_argument("--outdir", default="dist", help="批量/多格式模式的输出目录")
    p.add_argument("--formats", default="wechat",
                   help="输出格式，逗号分隔：wechat,zhihu,plain（默认 wechat）")
    p.add_argument("--batch", metavar="DIR", help="批量转换目录下所有 .md/.docx")
    p.add_argument("--fragment", action="store_true", help="只输出可直接粘贴的正文片段（不含预览外壳）")
    p.add_argument("--selftest", action="store_true", help="运行内置自检用例")
    p.add_argument("--validate", metavar="FILE", help="校验一个 HTML 是否符合公众号规则")
    p.add_argument("--list-themes", action="store_true", help="列出所有主题")
    return p


def _write_outputs(source: str, opt: dict, outdir: Path, base: str) -> tuple[str, str]:
    """写出 HTML（预览壳 + 正文片段）以及可选的其他格式，返回 (预览路径, 正文路径)。"""
    body, title, meta, warnings = convert_to_html(source, opt)
    theme = THEMES[opt["theme"]]

    outdir.mkdir(parents=True, exist_ok=True)
    preview_path = outdir / f"{base}.html"
    fragment_path = outdir / f"{base}_body.html"

    title_text = title or Path(source).stem
    shell = PREVIEW_SHELL.format(
        title=esc(title_text), body=body,
        accent=theme["primary"], theme_label=f"{opt['theme']} · {theme['label']}",
    )
    preview_path.write_text(shell, encoding="utf-8")
    fragment_path.write_text(body, encoding="utf-8")

    if "zhihu" in opt["formats"]:
        (outdir / f"{base}.zhihu.md").write_text(to_zhihu_markdown(source), encoding="utf-8")
    if "plain" in opt["formats"]:
        (outdir / f"{base}.txt").write_text(to_plain_text(source), encoding="utf-8")

    print(f"[ok] 预览：{preview_path}")
    print(f"[ok] 正文（可直接粘贴）：{fragment_path}")
    if warnings:
        print(f"[warn] {len(warnings)} 条提示：")
        for w in dict.fromkeys(warnings):
            print("   - " + w)
    return str(preview_path), str(fragment_path)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_themes:
        for key, spec in THEMES.items():
            print(f"  {key:<9} {spec['label']}  主色 {spec['primary']}")
        return 0

    if args.selftest:
        return run_selftest()

    if args.validate:
        return validate_html(args.validate)

    opt = resolve_options(args)

    # 批量模式
    if args.batch:
        src_dir = Path(args.batch)
        files = sorted(
            [f for f in src_dir.iterdir() if f.suffix.lower() in (".md", ".docx", ".html")]
        )
        if not files:
            print(f"[error] 目录中没有可转换文件：{src_dir}")
            return 1
        print(f"[batch] 共 {len(files)} 个文件 → {args.outdir}")
        for f in files:
            print(f"\n→ {f.name}")
            _write_outputs(str(f), opt, Path(args.outdir), f.stem)
        return 0

    if not args.input:
        build_parser().print_help()
        return 1

    src = Path(args.input)
    if not src.exists():
        print(f"[error] 找不到文件：{src}")
        return 1

    # 多格式 / 指定 outdir → 输出到目录
    if args.outdir and (args.outdir != "dist" or len(opt["formats"]) > 1 or not args.output):
        base = args.output and Path(args.output).stem or src.stem
        _write_outputs(str(src), opt, Path(args.outdir), base)
        preview = Path(args.outdir) / f"{base}.html"
        print("\n下一步：浏览器打开预览 → 点「复制正文」→ 粘贴到 mp.weixin.qq.com 编辑器")
        print(f"完成后可校验：python scripts/convert_to_wechat_pro.py --validate {preview}")
        return 0

    # 单文件模式（与 starter 用法保持一致）
    body, title, meta, warnings = convert_to_html(str(src), opt)
    theme = THEMES[opt["theme"]]
    out = Path(args.output)
    out.write_text(
        body if args.fragment
        else PREVIEW_SHELL.format(
            title=esc(title or src.stem), body=body,
            accent=theme["primary"], theme_label=f"{opt['theme']} · {theme['label']}",
        ),
        encoding="utf-8",
    )
    size_kb = out.stat().st_size / 1024
    print(f"[ok] {out} ({size_kb:.1f} KB)  主题={opt['theme']}")
    if warnings:
        print(f"[warn] {len(warnings)} 条提示：")
        for w in dict.fromkeys(warnings):
            print("   - " + w)
    print("\n下一步：浏览器打开 → 点「复制正文」→ 粘贴到 mp.weixin.qq.com → 预览 → 发布")
    return 0


if __name__ == "__main__":
    sys.exit(main())
