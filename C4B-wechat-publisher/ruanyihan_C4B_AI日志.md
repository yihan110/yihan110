# AI 日志 — C4B 公众号文章生成技能开发全过程

> 挑战：C4B 公众号文章生成技能 ｜ 提交人：阮依涵 ｜ 日期：2026-10-11
> 本文件记录：**用了什么 AI、怎么指挥、迭代了几轮、我做了什么、失败在哪**。
> 所有命令输出均为真实运行结果，可复现（脚本与文章源文件均在交付包内）。

---

## 一、用到的 AI 工具与技能

| 工具 / 技能 | 在本次任务中的角色 |
|------------|------------------|
| **WorkBuddy AI Agent** | 主体：解读挑战、读 starter kit、写转换脚本、跑测试、写全部文档 |
| **`skill-creator` 技能（强制要求）** | 元技能：提供「创建技能」的标准流程与官方脚本 |
| `init_skill.py` | skill-creator 附带：生成符合规范的技能骨架 |
| `package_skill.py` | skill-creator 附带：校验并打包 `.skill` |
| `quick_validate.py` | skill-creator 附带：结构合法性校验 |
| Python 3.13 + venv | 隔离运行环境（不污染系统环境） |

---

## 二、我如何指挥 AI（工作流设计）

我没有用一句话把任务甩给 AI。我采用的是**「先定框架 → 再要证据 → 逐轮加压」**
的三段式指挥法。

### 第 0 轮 · 定框架（我给方向与硬约束）

> "读完 CHALLENGE.md、rubric.json 和 starter kit 的全部源码。先不要写代码。
> 我的硬约束有四条：
> 1. 必须真的用 skill-creator 的流程和官方脚本（这是评分项，不能假装）；
> 2. 新增能力不能少于 2 项，但要覆盖 rubric 的「技能定制深度」；
> 3. 输出必须能被 `--validate` 自证合规（对应「可验证」）；
> 4. 命名严格按 `姓名拼音_C4B_内容.扩展名`。
> 先给我一份「starter kit 缺陷清单 + 改造方案」，我确认后再动手。"

**我为什么要先说这句？** 因为 C4B 的最大陷阱是「让 AI 从头写一个新脚本」——
那样就丢掉了「拿来主义」这个评分维度。我先要求 AI **先读懂再动手**。

### 第 1 轮 · 要结构（我给标准）

> "按 skill-creator 的标准结构落地：`SKILL.md`（YAML frontmatter + 工作流 +
> 边界情况）+ `scripts/` + `references/`。SKILL.md 要用祈使句，
> description 要写清「什么时候触发」，并加中英双语触发短语。"

### 第 2 轮起 · 要证据（我反复加压）

> "不要只给我代码。**实际跑给我看。** 每一项能力都要有一条断言证明它生效。"

> "跑完先别急着说成功 —— 用 `--validate` 校验输出，再把失败项报给我。"

> "自检 22 项全过了吗？没过就把每一项的失败原因写出来。"

这一步是整份日志最有价值的部分 —— 因为**加压之后，AI 真的连续暴露了 6 个问题**。

---

## 三、skill-creator 使用记录（评分要求，逐条可查）

| 步骤 | skill-creator 要求的动作 | 我的实际操作 |
|------|------------------------|-------------|
| Step 1 理解 | 用具体例子明确技能的用法 | 跑通 starter kit，整理出 10 项缺失能力清单 |
| Step 2 规划 | 分析需要哪些 scripts/references/assets | 确定：1 个转换脚本 + 3 份 references + examples；**删除 assets**（不需要） |
| Step 3 初始化 | 运行 `init_skill.py` | `init_skill.py wechat-publisher-pro --path <workspace>` ✅ |
| Step 4 编辑 | 写 SKILL.md + 填充 resources | 重写 SKILL.md（含 `agent_created: true`），删除示例文件，写入脚本与 references |
| Step 5 打包 | 运行 `package_skill.py` 校验并打包 | `package_skill.py wechat-publisher-pro` ✅ |
| Step 6 迭代 | 用真实任务检验并改进 | 6 轮迭代，见下节 |

初始化命令的真实输出：

```
🚀 Initializing skill: wechat-publisher-pro
✅ Created skill directory: ...\wechat-publisher-pro
✅ Created SKILL.md
✅ Created scripts/example.py
✅ Created references/api_reference.md
✅ Created assets/example_asset.txt
```

> **我做的关键决策**：删掉了 `assets/` 目录。skill-creator 的骨架默认生成
> `assets/`，但这个技能不需要往输出里放模板文件或字体，**留着空目录只会让结构变脏**。
> 这是「理解标准后做裁剪」，而不是机械照搬。

---

## 四、迭代过程（6 轮，每轮都真实改了代码）

### 轮次 1 · 跑通 starter kit，撞上第一个真实崩溃 ❌

- **我做了什么**：创建 venv、装依赖、跑官方示例。
- **失败现象**：脚本直接崩溃：

  ```
  UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f4d6'
    in position 0: illegal multibyte sequence
  ```
- **根因定位**：`print("📖 Reading ...")` —— 中文 Windows 控制台是 GBK 编码，
  输出 emoji 直接抛异常。
- **修复**：在脚本启动时把 `sys.stdout/stderr` 强制 `reconfigure(encoding="utf-8")`。
- **教训**：**跨平台脚本的「本地化盲区」比逻辑 bug 更容易致命。**
  一个表情符号就能让整条流水线跑不起来，而作者在 Mac 上永远遇不到。

### 轮次 2 · 逐项验收 starter kit，整理出缺陷清单

- **我做了什么**：让 AI 逐段读源码 + 用真实输出反推行为，列出缺陷并**要求给出证据**。
- **AI 提交的缺陷清单**（我逐条复核过）：

  | # | 缺陷 | 证据 |
  |---|------|------|
  | 1 | `<hr>` 被静默丢弃 | 示例里的 `---` 在输出 HTML 中完全消失 |
  | 2 | `<strong>` 用 `get_text()` 拍平嵌套 | 加粗内的 `<code>`/`<a>` 格式丢失 |
  | 3 | `<blockquote>` 同样被压平 | 多段引用合并成一段纯文本 |
  | 4 | `ALLOWED_CSS` 是死代码 | 定义但全文件零引用 |
  | 5 | `h4`–`h6` 未处理 | 走了 `unwrap()`，标题语义消失 |
  | 6 | `read_docx()` 不支持表格 | Word 表格完全丢失 |
  | 7 | `nl2br` 污染段落语义 | 软换行变 `<br>` |

- **我的复核动作**：我要求 AI 把每条缺陷都写成 `--selftest` 里的一条断言 ——
  **能被测试的缺陷才是被理解的缺陷。** 这直接催生了后面的 22 项自检。

### 轮次 3 · 第一版 Callout 实现失败 ❌（最有价值的一轮）

- **我做了什么**：要求实现 `> [!NOTE] 标题` 语法的 Callout 框。
- **失败现象**：自检报错：

  ```
  [FAIL] callout NOTE 渲染
  [FAIL] callout WARNING 渲染
  ```
- **根因定位**（AI 排查后给我的结论）：第一版是「先让 Markdown 解析，再从
  `<blockquote>` 里识别标记」。但 Markdown 会把

  ```markdown
  > [!NOTE] 关键知识点
  > Callout 框应被正确识别。
  ```

  合并成**同一个 `<p>`**：`<p>[!NOTE] 关键知识点\nCallout 框…</p>`。
  标题和正文粘成一坨，正则怎么都拆不干净。
- **修复**：把识别动作**提前到 Markdown 解析之前** —— 逐行扫描原始文本，
  天然保留「标记行 / 正文行」的边界。
- **教训**：**处理要尽量前置到数据还没变形的时候。** 后处理阶段的挣扎，
  往往是因为上游把信息揉成一团了。这条经验我已经写进了 `markdown_syntax.md`。

### 轮次 4 · 拼接 HTML 时套出了「页面里的页面」❌

- **失败现象**：高亮框 HTML 里出现了嵌套的 `<html><body>`：

  ```html
  <p style="...">
    <html><body><p>[!NOTE] ...</p></body></html>
  </p>
  ```
- **根因**：我用 `soup.append(BeautifulSoup(fragment, "lxml"))` 把字符串片段塞进节点 ——
  而 `BeautifulSoup(...)` 会**自动补全整个文档结构**，于是塞进去一整个页面。
- **修复**：不再用字符串当中间层，改成**直接搬运 DOM 节点**（`child.extract()` + `append`）。
- **教训**：用解析器构造 HTML 时，**字符串和节点是两种东西**，混用会得到结构错乱的产物。

### 轮次 5 · 「盘古之白」插错了位置 ❌

- **我做了什么**：要求实现中英文之间自动加细间距。
- **失败现象**：输出里出现 `⚠️ 坑 1 ： emoji`、`改成 1.75 、给引用`
  —— **数字和全角标点之间被插了空格**。
- **根因**：我最初把 CJK 字符集定义成了「汉字 + CJK 标点 + 全角标点」，
  于是 `1` 后面紧跟的全角冒号 `：` 也被当成需要加空格的边界。
- **修复**：把字符集**收窄到只包含汉字**（`\u4e00-\u9fff` 等），
  明确排除全角标点。
- **教训**：**范围定义过宽，比功能缺失更伤人。** 一个字符集写宽了，
  满篇都是错位的空格，比不加还难看。

### 轮次 6 · 自检用例本身是错的 ❌（我自己的锅）

- **失败现象**：`[FAIL] 中英文间距（盘古之白）`。
- **根因定位**：**不是技能错了，是我的测试样例写错了。** 我用来测「中英文间距」
  的句子是「包含 English words 与 123 数字」—— 中英文之间**本来就有空格**，
  根本没有触发条件，用例自然永远失败。
- **修复**：改成真正的无空格混排样例「还混排了Python3代码与Windows GBK编码」，
  测试立刻通过。
- **教训**：**测试用例也是要被验证的对象。** 「有个测试」不等于「测到了」。
  这和我在 C4（algo-solver）里踩过的坑是同一个：验证的充分性取决于用例的质量。

### 收尾 · 打包与验收

- 跑 `--selftest`：**22/22 通过**
- 跑 `--validate`：**✓ 通过公众号 HTML 规则校验**
- 生成正式文章 HTML（预览页 48 KB / 正文片段 44 KB，含 8 张内嵌公式图）
- 用 skill-creator 的 `package_skill.py` 打包为 `.skill`

---

## 五、迭代成效对照

| 维度 | 第 1 版 | 最终版 |
|------|--------|--------|
| 自检通过率 | 16/19 | **22/22** |
| 已知失败项 | 3 项（Callout×2、间距×1） | 0 项 |
| 微博客规则校验 | 未接入 | ✓ 通过 |
| Windows 兼容 | ❌ emoji 崩溃 | ✅ |
| 输出结构 | 夹带 `<html><body>` | ✅ 纯净 |
| 标点错位 | ❌ `1 ：` / `1.75 、` | ✅ 已修正 |

---

## 六、prompt 优化的三条实操心得

1. **先要「缺陷清单」，再要「代码」。**
   如果第一步就要代码，AI 会直接写一个「新脚本」而忽略 starter kit；
   先要清单，才会被迫先读懂。

2. **把「证据」写进指令里。**
   「跑给我看」这四个字，让 AI 从「声称完成」转向「给出断言结果」。
   改造前后最关键的一句指令就是：**「每一项能力都要有一条断言证明它生效。」**

3. **要求 AI 记录自己的失败。**
   我在第 3 轮之后加了一条固定指令：**「每次修复都要写清：现象 → 根因 → 修法 → 教训。」**
   这直接产出了本文件第四节的全部内容 —— 也让复盘（AAR）有了真实素材，
   而不是事后编一段「一切顺利」。

---

## 七、AAR 复盘

见同目录 `ruanyihan_C4B_复盘AAR.md`。

---

## 八、可复现证据索引

| 证据 | 位置 |
|------|------|
| 自检 22 项通过 | `python scripts/convert_to_wechat_pro.py --selftest` |
| 公众号规则校验通过 | `python scripts/convert_to_wechat_pro.py --validate ruanyihan_C4B_output_body.html` |
| starter kit 原始崩溃 | 本文第四节 轮次 1 |
| 生成的文章 HTML | `ruanyihan_C4B_output.html` / `ruanyihan_C4B_output_body.html` |
| 文章 Markdown 源文件 | `ruanyihan_C4B_文章源文件.md` |
| 改造清单（拿了什么 / 改了什么） | `ruanyihan_C4B_拿来说明.md` |
