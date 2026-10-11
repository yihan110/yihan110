# 教学说明 — 怎么安装、怎么用 `wechat-publisher-pro`

> 挑战：C4B 公众号文章生成技能 ｜ 提交人：阮依涵
> 一句话：**一行命令，把 Markdown 变成能直接粘贴进公众号的 HTML。**

---

## 一、这个技能解决什么问题

微信公众号编辑器有一套严格规则：只接受行内 CSS、禁用 `<h1>`/`<div>`/`<script>`、
SVG 会消失、外链图片会掉。从 Markdown 或 Word 到「排版精美的公众号文章」，
中间全是坑。

这个技能把规则固化成代码：**你只管写内容，排版交给它。**

---

## 二、安装（3 步）

### 第 1 步：装依赖

```bash
pip install markdown beautifulsoup4 python-docx lxml
# 可选：只有文章含数学公式时才需要
pip install matplotlib
```

> Windows 用户如果 `pip` 报权限错误，加 `--break-system-packages` 或改用虚拟环境。
> 脚本本身也内置了「缺依赖自动安装」的兜底逻辑。

### 第 2 步：放置技能

把 `wechat-publisher-pro/` 整个目录放到以下任一位置：

| 作用域 | 路径 | 说明 |
|--------|------|------|
| 用户级（推荐） | `~/.workbuddy/skills/wechat-publisher-pro/` | 所有项目都能用 |
| 项目级 | `<项目>/.workbuddy/skills/wechat-publisher-pro/` | 只在当前项目生效 |

或者安装打包好的技能包：

```bash
# 把 ruanyihan_C4B_wechat-publisher.skill 解压到技能目录即可
unzip ruanyihan_C4B_wechat-publisher.skill -d ~/.workbuddy/skills/
```

### 第 3 步：验证安装

```bash
cd wechat-publisher-pro
python scripts/convert_to_wechat_pro.py --selftest
```

看到 `结果：22/22 通过` 就说明环境正常。

---

## 三、四种典型用法

### 用法 1：最简转换（一条命令）

```bash
python scripts/convert_to_wechat_pro.py 我的文章.md 输出.html
```

浏览器打开 `输出.html` → 点「复制正文」→ 粘贴到公众号编辑器。

### 用法 2：用模板一键出稿（推荐）

```bash
python scripts/convert_to_wechat_pro.py 我的文章.md --outdir dist --template tutorial
```

会生成 4 个文件：

| 文件 | 用途 |
|------|------|
| `dist/我的文章.html` | 浏览器**预览页**（手机外框 + 复制按钮） |
| `dist/我的文章_body.html` | **纯正文片段**，直接粘贴用 |
| `dist/我的文章.zhihu.md` | 知乎友好版 Markdown |
| `dist/我的文章.txt` | 纯文本版 |

`--template` 可选：`tutorial`（技术教程）/ `notes`（学习笔记）/
`product`（产品介绍）/ `post`（通用随笔）。

### 用法 3：换主题、加目录

```bash
# 查看所有主题
python scripts/convert_to_wechat_pro.py --list-themes

# 换主题 + 自动目录 + 自定义页脚
python scripts/convert_to_wechat_pro.py 我的文章.md --outdir dist \
  --theme warm --toc --footer "本文首发于我的公众号，转载请注明出处"
```

5 套主题：`default`（经典蓝）、`accent`（科技蓝）、`warm`（暖橙）、
`green`（微信绿）、`minimal`（极简灰）。

### 用法 4：批量转换整个目录

```bash
python scripts/convert_to_wechat_pro.py --batch ./文章目录 --outdir dist --template notes
```

目录下所有 `.md` / `.docx` 会一次性转换完成。

---

## 四、文章怎么写（Markdown 约定）

### 4.1 开头加元数据

```markdown
---
title: 我的文章标题
subtitle: 一句话副标题
author: 阮依涵
date: 2026-10-11
digest: 这里写摘要，会渲染成虚线摘要框
---
```

### 4.2 用 Callout 高亮框突出重点

```markdown
> [!NOTE] 知识点
> 这里写正文，支持 **加粗** 和 `行内代码`。

> [!WARNING] 注意
> 警告内容。
```

10 种类型任选：`NOTE` `TIP` `IMPORTANT` `WARNING` `DANGER` `PRACTICE`
`SUCCESS` `QUOTE` `INFO` `QUESTION`。
中文写法也认：`[!知识]` `[!注意]` `[!实践]` `【提示】`…

### 4.3 数学公式

```markdown
行内：$E = mc^2$
块级：

$$\int_0^1 x^2\,dx = \frac{1}{3}$$
```

### 4.4 分隔线

```markdown
---
```

会渲染成居中的 `· · ·`（因为 `<hr>` 在公众号里会被丢弃）。

> 完整语法速查见 `references/markdown_syntax.md`。

---

## 五、发布流程（从 Markdown 到上线，5 分钟）

```
1. 写好 Markdown（元数据 + 正文 + Callout）
        ↓
2. python scripts/convert_to_wechat_pro.py 文章.md --outdir dist --template tutorial
        ↓
3. 浏览器打开 dist/文章.html，逐屏检查排版
        ↓
4. 点「复制正文」
        ↓
5. 打开 mp.weixin.qq.com → 新建图文消息 → Ctrl+V 粘贴
        ↓
6. 手动补充：封面图、作者、原文链接（这三项公众平台不允许脚本代填）
        ↓
7. 手机预览 → 微调 → 发布
```

### 粘贴后需要人工确认的 3 件事

| 项目 | 为什么要手动 |
|------|-------------|
| 封面图 | 必须在公众号后台上传，脚本无法代传 |
| 图片素材 | base64 会在粘贴时被自动转存到素材库，粘完扫一眼有没有缺图 |
| 原文链接 / 话题标签 | 属于平台侧设置，不在 HTML 里 |

---

## 六、验证输出是否合规

```bash
python scripts/convert_to_wechat_pro.py --validate dist/文章_body.html
```

输出 `✓ 通过公众号 HTML 规则校验` 即为合规；若有问题会逐条列出
（违规标签、`class`/`id`、事件属性、越界 CSS 属性）。退出码 1 表示有问题的，
方便接进 CI。

---

## 七、常见问题

| 问题 | 原因与解法 |
|------|-----------|
| 粘贴后样式全没了 | 你复制的是预览页而不是正文。用预览页的「复制正文」按钮，或直接打开 `_body.html` |
| 公式显示不出来 | 没装 matplotlib。装一下，或接受降级为原始 LaTeX 文本 |
| 图片粘贴后不见了 | 外部链图片。请上传到公众号素材库后替换，或用本地图片让技能自动内嵌 |
| 标题显示不全 | 公众号标题在后台单独填写，正文里的 H1 会被降级为 H2 |
| 提示「本地图片未找到」 | Markdown 里的图片路径是相对路径，相对的是 **md 文件所在目录** |
| 脚本报 GBK 编码错误 | 老版本 starter kit 的问题；本技能已在启动时强制 UTF-8，不会出现 |
| 表格在手机上溢出 | 公众号没有横向滚动。把宽表拆成两张，或精简列 |

---

## 八、扩展技能

### 加一套新主题

在 `scripts/convert_to_wechat_pro.py` 的 `THEMES` 字典里追加一项（照抄任意一套改色值），
`--theme 新名字` 立刻可用。**不需要改任何逻辑代码。**

### 加一种新 Callout

在 `CALLOUTS` 里加一项 `{icon, label, color, bg}`，并在 `CALLOUT_ALIAS` 里登记别名即可。

具体字段说明见 `references/themes.md`。

---

## 九、文件清单

```
wechat-publisher-pro/
├── SKILL.md                          # 技能主指令（给 AI 读）
├── scripts/
│   └── convert_to_wechat_pro.py      # 转换脚本（核心）
├── references/
│   ├── wechat_restrictions.md        # 公众号 HTML 限制规则（含真实踩坑）
│   ├── themes.md                     # 主题系统参考
│   └── markdown_syntax.md            # Markdown 扩展语法速查
└── examples/
    ├── sample_article.md             # 示例输入
    ├── sample_article.html           # 示例输出（预览页）
    └── sample_article_body.html      # 示例输出（正文片段）
```

**欢迎使用，反馈越多，下一版越好。**
