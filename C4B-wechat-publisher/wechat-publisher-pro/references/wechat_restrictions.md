# 微信公众号 HTML 限制规则（wechat_restrictions.md）

公众号编辑器不是浏览器，而是一台规则严格的「打印机」。本技能在转换过程中
**强制执行**以下规则；`--validate` 命令会逐条检查输出是否合规。

## 允许的标签

```
p, h2, h3, ul, ol, li, span, img, a, table, tr, th, td, br
```

## 禁止的标签及处理方式

| 标签 | 为什么禁止 | 本技能的处理 |
|------|-----------|-------------|
| `<h1>` | 公众号保留给文章标题 | 降级为 `<h2>` |
| `<div>` | 渲染不可靠 | 转换为 `<p>` / `<span>` |
| `<script>` | 安全原因，必被剥离 | 整块删除 |
| `<style>` | CSS 必须行内 | 删除，样式改为 `style=""` |
| `<iframe>` / `<video>` / `<audio>` | 必须使用公众号自身的嵌入组件 | 删除（可手动改为链接） |
| `<svg>` / `<canvas>` | 保存时消失 | 删除（请改用 PNG） |
| `<form>` / `<input>` / `<button>` | 交互组件被禁用 | 删除 |
| `<hr>` | 不在白名单，会被静默丢弃 | 转为居中圆点分隔符 `· · ·` |
| `<pre>` / `<blockquote>` | 语义标签不被支持 | 转为带行内样式的 `<p>` |
| `<h4>`–`<h6>` | 层级不被支持 | 统一下沉为 `<h3>` |

> **注意**：`<hr>` 和 `<pre>` 这类标签的危险之处在于**被静默丢弃、不报错**。
> starter kit 就存在这个问题：Markdown 里的 `---` 在输出里凭空消失，只能靠肉眼发现。

## 禁止的属性

| 属性 | 处理 |
|------|------|
| `class` | 删除 |
| `id` | 删除（同时意味着**内部锚点跳转不可用**，目录只能做成纯文字列表） |
| `on*`（`onclick` 等） | 删除 |
| `data-*` | 删除 |

## CSS 规则

### 必须行内化

```html
<!-- ✅ 正确 -->
<p style="font-size:16px; color:#333;">正文</p>

<!-- ❌ 公众号会剥离 -->
<style>p { font-size:16px; }</style>
<p class="body">正文</p>
```

### 白名单属性（`ALLOWED_CSS`）

```
color, background-color, font-size, font-weight, font-style, font-family,
line-height, text-align, text-indent, text-decoration, letter-spacing,
word-break, overflow-wrap, white-space,
margin / margin-top / margin-bottom / margin-left / margin-right,
padding / padding-top / padding-bottom / padding-left / padding-right,
border, border-top, border-bottom, border-left, border-right, border-radius,
border-collapse, display, vertical-align, max-width, width, height,
list-style-type, list-style-position
```

### 禁止的 CSS

- 布局类：`position`、`float`、`flex`、`grid`
- 动效类：`animation`、`transition`
- `@media` 媒体查询
- `@font-face` 自定义字体

> starter kit 里定义了 `ALLOWED_CSS` 常量却**从未使用**（死代码）。本技能把它
> 真正接进了清洗流程：任何越界的 CSS 属性都会被剔除。

## 图片规则

| 方式 | 是否可用 | 说明 |
|------|---------|------|
| `<img src="https://...">` | ⚠️ | 可显示，但建议上传到素材库 |
| `<img src="data:image/png;base64,...">` | ✅ | 粘贴时公众号会自动转存到素材库 |
| `<img src="data:image/svg+xml;base64,...">` | ❌ | 保存时消失 |
| 内联 `<svg>` | ❌ | 直接被剥离 |

**最佳实践**：自包含图形用 PNG base64；照片走公众号素材库 + CDN 链接。
本技能对**本地图片**自动做 base64 内嵌，对外链图片与 SVG 给出警告。

## 数学公式

公众号编辑器不支持 MathJax / KaTeX，也不接受 SVG。唯一稳定可行的方案是
**把公式离线渲染成透明底 PNG，再以 base64 内嵌**。本技能使用 matplotlib 的
mathtext 引擎完成渲染（无需安装完整 LaTeX 环境）：

- `$$公式$$` → 块级公式图片
- `$公式$` → 行内公式图片（`vertical-align: middle`）

## 文章长度与图片限制

| 限制项 | 数值 |
|--------|------|
| 单篇正文上限 | 约 20,000 中文字符 |
| 单篇图片数 | ≤ 100 张 |
| 单图体积 | ≤ 10 MB |
| 支持格式 | PNG / JPG / GIF |
| GIF 体积 | ≤ 2 MB |

## 常见坑（含真实踩坑记录）

1. **保存后样式丢失** —— 通常用了 `<style>`、`class` 或禁用的标签。
2. **图片消失** —— SVG data URI 或失效的外链。
3. **排版错乱** —— 公众号对 margin 的合并规则与浏览器不同，故本技能统一用
   `margin: 0 0 16px 0` 这种单向边距，避免塌陷。
4. **代码块显示为一坨** —— 必须用 `<p>` + `<br>`，不能用 `<pre>`（浏览器依赖
   `white-space: pre`，公众号不保证）。
5. **表格超出屏宽** —— 没有横向滚动，过宽的表格需手动拆分。
6. **Windows 控制台 GBK 报错** —— `print()` 输出 emoji 会抛
   `UnicodeEncodeError`。本技能启动即把 stdout 切到 UTF-8。
