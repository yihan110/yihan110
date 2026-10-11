# 拿来说明 — 我从 starter kit 拿了什么、改了什么、为什么

> 挑战：C4B 公众号文章生成技能 ｜ 提交人：阮依涵 ｜ 日期：2026-10-11
> 基座：`c4b-wechat-publisher-starter.zip`（15426 字节，SHA-256 `6d42f43bfee8f90c…`）
> 产出：`wechat-publisher-pro`（可直接安装的技能包）

---

## 一、starter kit 有什么

解压后共 5 个文件：

```
c4b-wechat-publisher-starter/
├── SKILL.md                        ← 主指令
├── scripts/convert_to_wechat.py    ← 转换脚本（383 行）
├── references/wechat_styles.md     ← 样式参考
├── references/wechat_restrictions.md ← 限制规则
└── examples/sample_article.md / sample_output.html
```

它的核心是 4 个函数，我逐个读过并实际跑通：

| 函数 | 做什么 | 我的评价 |
|------|--------|---------|
| `read_markdown()` | 用 `markdown` 库 + `extra/fenced_code/nl2br/sane_lists` 转 HTML | 可用，但 `nl2br` 会把软换行变成 `<br>`，段落语义被噪声污染 |
| `read_docx()` | 用 `python-docx` 抽段落与加粗/斜体 | 可用，但**不支持表格**、不支持列表 |
| `sanitize()` | 删 script/style/iframe，h1→h2，div→p，pre/blockquote→p | 思路对，但**用 `get_text()` 提取内容，会把嵌套格式拍平** |
| `apply_styles()` | 给各标签套默认 inline CSS | 可用，但只有一套样式，无主题概念 |
| `clean_attributes()` | 删 class/id，unwrap 非白名单标签 | 可用，但定义的 `ALLOWED_CSS` **从未被使用（死代码）** |

**结论：这是一份合格的「能跑」的基座，但离「好用、好看、有个性」还差得远。**

---

## 二、我实际跑了一遍，拿证据说话

我没有只读代码，而是先跑通它，再逐项验收：

```bash
pip install markdown beautifulsoup4 python-docx lxml
python scripts/convert_to_wechat.py examples/sample_article.md output.html
```

### ❌ 第一个问题：脚本在中文 Windows 上直接崩溃

```
UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f4d6'
  in position 0: illegal multibyte sequence
```

`convert_to_wechat.py` 第 300 行 `print("📖 Reading ...")` —— 一个 emoji，让整条流水线
在中文 Windows 的 GBK 控制台上直接死掉。

> 这暴露了 starter kit 的一个盲区：**它是为 Mac/Linux 写的，没有考虑中文 Windows 环境。**
> 而这份挑战的参与者大量使用 Windows。

### ❌ 第二个问题：`<hr>` 被静默丢弃

样例文章里有 `---` 分隔线。在输出 HTML 里，它**完全消失了**，而且没有任何警告。

原因：`markdown` 把 `---` 生成 `<hr>`，而 `<hr>` 不在 `ALLOWED_TAGS` 里，
`clean_attributes()` 里的 `tag.unwrap()` 会把它拆掉 —— 内容为空，所以等于删除。

### ❌ 第三个问题：加粗里的嵌套内容被拍平

`sanitize()` 处理 `<strong>` 时用的是：

```python
span.string = tag.get_text()      # ← 只取纯文本
```

如果加粗内容里还有 `<code>` 或 `<a>`，**里面的格式会一起被拍平**，变成一个不可区分的纯文本 span。

### ❌ 第四个问题：引用块的内部结构被压成一坨

`<blockquote>` 同样用 `get_text()` 提取，多段引用被合并，段内格式全丢。

### ⚠️ 第五个问题：`h4`/`h5`/`h6` 未处理

只映射了 h1/h2/h3。更深层级的标题会走 `unwrap()`，**标题语义彻底消失**，退化成普通文字。

### ✅ 一个正面发现：`ALLOWED_CSS` 是死代码

脚本里认真定义了 14 个 CSS 白名单属性，但全文搜索无任何引用。**作者的意图是过滤
非法 CSS，但功能从未接上。** 这意味着输出里可能出现公众号不支持的 CSS 属性。

---

## 三、我改了什么（拿来主义的清单）

### 3.1 保留的部分（拿来）

| 保留 | 说明 |
|------|------|
| 整体四段式流水线 | 读取 → 清洗 → 应用样式 → 清理属性，这个骨架是对的 |
| `markdown` + `BeautifulSoup` 技术选型 | 成熟稳定，不折腾 |
| `python-docx` 支持 | Word 输入是刚需 |
| 自动安装依赖的思路 | 降低使用门槛，保留 |
| 白名单 / 黑名单的数据结构 | `ALLOWED_TAGS` / `DROP_TAGS` / `ALLOWED_CSS` 三张表直接继承 |
| 命令行「输入 → 输出」的极简接口 | 保持 `input output` 位置参数兼容 |

### 3.2 修掉的部分（改造）

| 问题 | 修法 |
|------|------|
| emoji 在 GBK 控制台崩溃 | 启动时把 stdout/stderr `reconfigure(encoding="utf-8")`，并保留兜底 |
| `get_text()` 拍平嵌套 | 改为**搬运子节点**（`child.extract()` + `append`），保留全部嵌套格式 |
| `<hr>` 静默丢弃 | 主动转成居中圆点分隔符 `· · ·`，视觉上更像公众号 |
| `h4`–`h6` 语义丢失 | 统一下沉为 `<h3>`，保住标题层级 |
| `ALLOWED_CSS` 死代码 | 真正接入 `clean_attributes()`，逐条过滤非法 CSS 属性 |
| `nl2br` 污染段落 | 关闭 `nl2br`，改用 `sane_lists` + `smarty`（智能引号/破折号） |
| `read_docx()` 不支持表格/列表 | 补充 Word 表格提取与列表聚合 |
| 代码块换行不可靠 | 用 `<p>` + `<br>` 保留换行（公众号对 `white-space: pre` 不保证） |
| 输出夹带 `<html><body>` | 只提取 `<body>` 的子节点（`str(soup)` 会带出 lxml 自动补全的外壳） |

### 3.3 新增的部分（超越）

| 新增能力 | 怎么实现的 | 为什么值得做 |
|---------|-----------|-------------|
| **主题系统（5 套）** | `THEMES` 字典驱动整套色板，`--theme` 切换 | 让文章有视觉标识；新增主题只需加一项字典 |
| **Callout 高亮框（10 种）** | 在 Markdown 解析**之前**逐行扫描 `> [!TYPE]`，改写为占位段落 | 公众号最核心的排版元素；且必须先于解析，否则标记与正文被合并 |
| **自动目录** | 收集 h2/h3 生成带底色圆角框（纯文字，不用锚点 —— 公众号会删 `id`） | 长文可读性 |
| **文章元数据** | YAML frontmatter → 副标题 / 作者行 / 虚线摘要框 | 文章结构完整 |
| **页脚版权** | `--footer` 自定义，默认自动署名 | 实际发布必需 |
| **中文排版优化** | 「盘古之白」：汉字与拉丁字母/数字之间插细空格；**排除全角标点** | 专业感提升；排除标点是关键细节 |
| **数学公式** | matplotlib mathtext 渲染 → 透明底 PNG → base64 内嵌 | 公众号不支持 MathJax/SVG，这是唯一稳定方案 |
| **图片处理** | 本地图片自动 base64 内嵌；外链与 SVG 给出告警 | 粘贴时不掉图 |
| **批量转换** | `--batch <dir>` 遍历目录 | 一次处理多篇 |
| **多格式输出** | `--formats wechat,zhihu,plain` | 一次写作，多平台分发 |
| **模板系统** | `--template tutorial\|notes\|product\|post` | 预设组合，降低选择成本 |
| **校验命令** | `--validate` 逐条检查公众号规则 | 把「可验证」做成一条命令 |
| **自检 eval** | `--selftest` 22 项断言 + 自动校验 | 交付前自证可用 |

---

## 四、改造后的效果对比

| 维度 | starter kit | wechat-publisher-pro |
|------|-------------|----------------------|
| 代码行数 | 383 行 | 约 1050 行 |
| 主题 | 1 套（硬编码） | 5 套 + 可扩展 |
| 排版元素 | 标题/正文/列表/表格/代码 | 上述 + Callout×10 + 目录 + 摘要 + 页脚 |
| 数学公式 | ❌ | ✅ PNG base64 |
| 本地图片 | ❌ 原样保留（会掉图） | ✅ 自动 base64 内嵌 |
| 中文排版 | ❌ | ✅ 中英间距 + 标点保护 |
| 批量 | ❌ | ✅ |
| 多格式 | ❌ | ✅ 公众号/知乎/纯文本 |
| 自检 | ❌ | ✅ 22 项断言 |
| Windows 兼容 | ❌ emoji 崩溃 | ✅ UTF-8 强制 |
| 嵌套格式 | ❌ 被拍平 | ✅ 完整保留 |

---

## 五、为什么这么改（设计取舍）

1. **先在解析前动手，不要在后处理里挣扎。**
   Callout 的教训最深：如果先让 Markdown 解析，标记行和正文会被合并进同一个 `<p>`，
   之后无论怎么写正则都拆不干净。**把处理提前到数据还没变形的时候**，是最省力的解法。

2. **静默失败比报错更危险。**
   `<hr>` 被丢弃、CSS 属性被忽略，这些都不会报错。所以我加了 `--validate`，
   把「看不见的失败」变成「看得见的清单」。

3. **主题做成数据，不做成代码分支。**
   5 套主题全部是字典数据，没有任何 `if theme == "xxx"` 的分支。所以新增一套主题
   只需要往字典里加一项，不需要动逻辑 —— 这是可复用性的关键。

4. **保留 CLI 兼容。**
   `python script.py input.md output.html` 这种最简用法在改造后**依然可用**，
   老用户不需要改习惯。

---

## 六、诚实的边界声明

- 公众号的**封面图、图片素材库、发布动作**无法通过脚本完成，仍需人工在
  `mp.weixin.qq.com` 操作。技能解决的是「排版」，不是「发布」。
- 数学公式依赖 matplotlib。**未安装时不会崩溃**，会降级为带样式的原始 LaTeX 文本并给出告警。
- 目录是纯文字列表，**不含锚点跳转** —— 因为公众号会删除 `id` 属性，内部锚点不可用。
  这是平台限制，不是实现缺陷，已在 `references/wechat_restrictions.md` 中说明。
