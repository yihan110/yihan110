---
name: wechat-publisher-pro
description: Convert Markdown or Word documents (.md / .docx) into WeChat Official Account (微信公众号) ready-to-paste HTML, with themes, callout boxes, auto table of contents, article metadata, footer, Chinese typography optimization, LaTeX math rendered to PNG base64, local image embedding, batch conversion and multi-format export (WeChat HTML / Zhihu Markdown / plain text). This skill should be used when the user says "转换成公众号", "公众号排版", "生成公众号文章", "公众号 HTML", "wechat html", "convert to wechat", "publish to WeChat Official Account", "排版成公众号格式", or provides a .md/.docx file and wants it formatted for WeChat publishing. Also use it when the user asks to restyle, re-theme, or batch-convert existing articles for WeChat, or asks to validate that an HTML file complies with WeChat editor rules.
agent_created: true
---

# WeChat Publisher Pro — Markdown/Word → 公众号 HTML

## Purpose

Turn a Markdown (.md) or Word (.docx) document into **copy-paste-ready HTML for
the WeChat Official Account editor**, plus a browser preview page. Think of it
as a "print driver for WeChat": you supply content, it supplies HTML that
survives WeChat's strict editor rules — with themes, callout boxes, a table of
contents, metadata, math formulas and embedded images.

This skill is a hardened, extended version of the `c4b-wechat-publisher-starter`
kit. See the project's `拿来说明.md` for the full list of what changed and why.

## Quick Start

```bash
# one-command conversion (tutorial preset = accent theme + TOC + digest + footer)
python scripts/convert_to_wechat_pro.py article.md --outdir dist --template tutorial
```

Outputs:

| File | Purpose |
|------|---------|
| `dist/article.html` | Browser **preview page** (phone frame + 「复制正文」button) |
| `dist/article_body.html` | **Paste-ready body fragment** — this is what goes into WeChat |
| `dist/article.zhihu.md` | Optional: Zhihu-friendly Markdown |
| `dist/article.txt` | Optional: plain-text version |

Then: open the preview page → click 「复制正文」 → `mp.weixin.qq.com` → new article → `Ctrl+V`.

## Workflow

### Step 1 — Read source

Read `.md`, `.docx` or `.html`. Markdown is parsed with `extra`, `sane_lists`
and `smarty` extensions (tables, fenced code, footnotes, smart quotes).

### Step 2 — Pre-process

- Parse YAML frontmatter (`title`, `subtitle`, `author`, `date`, `digest`, `cover`).
- Rewrite `> [!TYPE] title` callout blocks into placeholders **before** Markdown
  parsing — this is required because Markdown merges the marker line and the body
  line into a single `<p>`, making them impossible to split afterwards.
- Extract `$...$` / `$$...$$` math and render each to a transparent PNG, inlined
  as a `data:image/png;base64,` URI (WeChat drops inline SVG but re-hosts base64 PNG).

### Step 3 — Sanitize

- Delete `script / style / iframe / video / audio / svg / canvas / form / ...`.
- `<pre><code>` → styled `<p>` with `<br>` line breaks and an optional language label.
- `<strong>/<em>` → styled `<span>`, **preserving nested children** (not `get_text()`).
- `<h1>` → `<h2>`; `<h4>–<h6>` → `<h3>`.
- `<hr>` → centred dot separator (`· · ·`), because `<hr>` is not whitelisted and
  would otherwise be silently dropped.
- `<blockquote>` → callout box (if a `[!TYPE]` marker is present) or styled quote.

### Step 4 — Style

Apply theme inline CSS from `references/themes.md`. Never overwrite an element
that already carries a `style` attribute.

### Step 5 — Clean & typography

- Strip `class`, `id`, `on*`, `data-*`; filter CSS declarations against a whitelist.
- Optional "盘古之白": insert a thin space between **Han characters** and Latin
  letters/digits. Full-width punctuation is deliberately excluded so you never get
  `坑 1 ：` or `1.75 、`.
- Embed local images as base64; warn about remote URLs and SVG.
- Emit only the `<body>` children — never the lxml-generated `<html><body>` shell.

### Step 6 — Validate (optional but recommended)

```bash
python scripts/convert_to_wechat_pro.py --validate dist/article_body.html
```

Reports any forbidden tag, `class`/`id`, event attribute or non-whitelisted CSS
property. Exit code 1 if anything is found.

## Command Reference

```bash
python scripts/convert_to_wechat_pro.py <input> [output] [options]

  --theme default|accent|warm|green|minimal   # colour scheme
  --template tutorial|notes|product|post      # preset bundles
  --toc                                       # auto table of contents
  --no-footer / --footer "TEXT"               # footer control
  --no-pangu                                  # disable CJK/Latin spacing
  --indent                                    # first-line indent 2em
  --author / --date                           # override frontmatter
  --outdir dist                               # output directory
  --formats wechat,zhihu,plain                # multi-format export
  --batch <dir>                               # convert every .md/.docx in a folder
  --fragment                                  # body fragment only, no preview shell
  --validate <file.html>                      # check WeChat rule compliance
  --selftest                                  # run the 22-case built-in eval
  --list-themes                               # print available themes
```

## Supported Markdown Syntax

See `references/markdown_syntax.md`. Highlights:

```markdown
---
title: 文章标题
author: 作者名
date: 2026-10-11
digest: 一句话摘要
---

## 二级标题

> [!NOTE] 知识点
> 正文，支持 **加粗** 与 `行内代码`。

> [!WARNING] 注意
> 警告内容。

公式：$E = mc^2$ 或 $$\int_0^1 x^2 dx$$
```

Available callout types: `NOTE` `TIP` `IMPORTANT` `WARNING` `DANGER` `PRACTICE`
`SUCCESS` `QUOTE` `INFO` `QUESTION` — Chinese aliases work too
(`[!知识]` `[!注意]` `[!实践]` …).

## Edge Cases

| Situation | Handling |
|-----------|----------|
| Empty file | Reports error, refuses to emit empty HTML |
| Non-UTF-8 file | Tries `utf-8`, `utf-8-sig`, then `gbk` |
| Windows console | Forces stdout/stderr to UTF-8 so emoji logs don't crash on GBK |
| Missing dependencies | Auto-installs `markdown / beautifulsoup4 / python-docx / lxml` |
| matplotlib absent | Math degrades to styled raw LaTeX + a warning (never crashes) |
| Remote image URL | Kept as-is + warning to upload to the WeChat media library |
| Local image missing | Skipped + warning |
| SVG image | Warned (WeChat drops SVG) and left alone |
| Very long articles | Works; WeChat caps at ~20,000 Chinese characters |
| Wide tables | Contained by `width: 100%`; split manually if wider than phone |

## Dependencies

```bash
pip install markdown beautifulsoup4 python-docx lxml
pip install matplotlib   # optional, only needed for $math$
```
