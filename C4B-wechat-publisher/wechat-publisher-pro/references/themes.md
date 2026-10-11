# 主题系统参考（themes.md）

`wechat-publisher-pro` 内置 5 套主题。用 `--theme <name>` 切换，或通过
`--template` 间接选择。所有主题都只输出 **inline CSS**，符合公众号编辑器要求。

## 主题一览

| 名称 | 标签 | 主色 | 适合场景 |
|------|------|------|----------|
| `default` | 经典蓝 | `#2b6cb0` | 通用、稳妥，适合大多数文章 |
| `accent` | 科技蓝 | `#1a73e8` | 技术文章、教程、产品说明 |
| `warm` | 暖橙 | `#e8710a` | 学习笔记、随笔、生活类 |
| `green` | 微信绿 | `#07c160` | 与微信生态一致的品牌感 |
| `minimal` | 极简灰 | `#3d4451` | 观点长文、严肃内容 |

查看当前可用主题：

```bash
python scripts/convert_to_wechat_pro.py --list-themes
```

## 主题色板结构

每套主题在脚本的 `THEMES` 字典里定义以下色值键：

| 键 | 作用 |
|----|------|
| `primary` | 品牌主色（目录标题、摘要前缀、预览页强调色） |
| `h2` / `h2_rule` | 二级标题文字色 / 左侧竖线色 |
| `h3` | 三级标题文字色 |
| `body` | 正文文字色（不用纯黑，减轻眼睛负担） |
| `muted` | 次要文字（作者行、日期、页脚） |
| `link` | 链接色 |
| `quote_bg` / `quote_border` / `quote_text` | 普通引用块底色 / 竖线 / 文字 |
| `code_bg` / `code_fg` | 代码块底色 / 文字 |
| `ci_bg` / `ci_fg` | 行内代码底色 / 文字 |
| `th_bg` / `th_fg` / `td_border` | 表头底色 / 表头文字 / 单元格边框 |
| `box_bg` / `box_border` | 目录框、摘要框的底色 / 边框 |
| `hr` | 分隔符与页脚上边线颜色 |

## 排版基线（所有主题共用）

| 元素 | 参数 | 原因 |
|------|------|------|
| 正文 | 16px / 行高 1.85 / 段间距 16px | 手机阅读的舒适区 |
| 二级标题 | 20px 粗体 + 左侧 4px 竖线 | 公众号最常见的章节标识 |
| 正文对齐 | `justify` + `letter-spacing: 0.4px` | 中文两端对齐更整齐 |
| 代码 | 13.5px 等宽 + 圆角 8px | 与正文形成清晰的视觉分区 |
| 表格 | `border-collapse` + 100% 宽 | 避免超出手机屏宽 |
| 图片 | `max-width: 100%` | 防止溢出 |

## 新增自定义主题

在 `scripts/convert_to_wechat_pro.py` 的 `THEMES` 字典里追加一项即可，例如：

```python
"purple": {
    "label": "紫罗兰",
    "primary": "#6d28d9",
    "h2": "#4c1d95",
    "h2_rule": "#8b5cf6",
    "h3": "#6d28d9",
    "body": "#2f2a3d",
    "muted": "#8b8598",
    "link": "#6d28d9",
    "quote_bg": "#f7f4ff",
    "quote_border": "#8b5cf6",
    "quote_text": "#4a4460",
    "code_bg": "#f7f5fb",
    "code_fg": "#2b2438",
    "ci_bg": "#efe9fe",
    "ci_fg": "#5b21b6",
    "th_bg": "#efe9fe",
    "th_fg": "#4c1d95",
    "td_border": "#e0d8f5",
    "box_bg": "#f7f4ff",
    "box_border": "#e0d8f5",
    "hr": "#e4ddf2",
},
```

无需改动其它代码 —— `--theme purple` 立即可用。

## Callout 色板

Callout 颜色与主题解耦（保证语义一致性：警告永远是橙色系）：

| 类型 | 图标 | 主色 | 底色 |
|------|------|------|------|
| note | 📘 | `#1a73e8` | `#f0f7ff` |
| tip | 💡 | `#0f9d58` | `#f0fbf4` |
| important | ❗ | `#d93025` | `#fdecea` |
| warning | ⚠️ | `#e8710a` | `#fff8e1` |
| danger | 🚫 | `#c5221f` | `#fdecea` |
| practice | 🔧 | `#7b1fa2` | `#f7f0fd` |
| success | ✅ | `#0f9d58` | `#f0fbf4` |
| quote | 💬 | `#5f6368` | `#f8f9fa` |
| info | ℹ️ | `#1a73e8` | `#f0f7ff` |
| question | ❓ | `#e8710a` | `#fff8e1` |
