# 教学说明（C4C 作业自动求解与排版）

> 作者：阮依涵 ｜ 挑战：C4C ｜ 日期：2026-10-11

---

## 一、这是什么

一个**作业自动求解与排版流水线**：把你手上的数学作业文件（.md/.pdf/.docx/图片）
一键变成**可提交的 PDF**。内置国产大模型 DeepSeek 推理引擎 + SymPy 符号计算引擎。

## 二、环境要求

| 依赖 | 说明 |
|------|------|
| Python 3.10+ | 运行环境 |
| `sympy` `pyyaml` `pdfplumber` `python-docx` `requests` | Python 库 |
| LaTeX（推荐 xelatex） | 编译 PDF（支持中文） |
| `DEEPSEEK_API_KEY` | DeepSeek 开放平台 key（证明/文字题推理用） |

```bash
pip install sympy pyyaml pdfplumber python-docx requests
# Windows/国内源：pip install -i https://mirrors.huaweicloud.com/repository/pypi/simple ...
```

## 三、安装

1. 下载/复制 `homework-solver/` 整个目录；
2. 安装上述依赖；
3. 设置环境变量 `DEEPSEEK_API_KEY=<你的 key>`。

## 四、使用方法

```bash
# 一键跑通（Markdown 作业）
python scripts/pipeline.py 作业.md output/ --compile \
    --course "Advanced Mathematics" --student "阮依涵" --title "高等数学作业"

# 分步执行（便于调试）
python scripts/ingest.py 作业.md output/1_ingested.json
python scripts/parse_problems.py output/1_ingested.json output/2_parsed.json
python scripts/solve.py output/2_parsed.json output/3_solutions.json
python scripts/render_latex.py output/3_solutions.json output/homework.tex --compile
```

输出：`output/homework.pdf`（可直接提交）+ `homework.tex` + 各阶段 JSON。

## 五、作业文件格式

支持 `Problem N` / `题 N` / `N.` / `Q.N` 题号，`(a)(b)` 子题，`$...$`/`$$...$$` 公式。

示例：
```markdown
## 多元函数微分学

1. 求函数 $f(x,y)=x^3+y^3-3xy$ 的偏导数。

2. 计算二重积分 $\iint_D (x^2+y)\,dA$，其中 $D=[0,1]\times[0,1]$。
```

## 六、支持哪些课程

| 领域 | 题型 | 引擎 |
|------|------|------|
| 微积分极限 | 极限、切线、ε-δ | SymPy（继承 starter） |
| **高等数学·多元微分** | 偏导数、全微分、拉格朗日乘数法 | SymPy |
| **高等数学·重积分** | 二重、三重积分 | SymPy |
| **高等数学·级数** | p-级数、比值判别、幂级数、泰勒展开 | SymPy |
| **证明/文字题** | 证明、概念、复杂推理 | DeepSeek |

## 七、常见问题

**Q：不设置 DEEPSEEK_API_KEY 能跑吗？**
能。计算题（题 1-10 类）不依赖 LLM，照常求解；证明/文字题会降级为"未求解"并提示。

**Q：PDF 中文乱码？**
需用 xelatex 编译（本模板已内置 ctex 宏包）。若用 pdflatex 编译中文会失败，请改用 xelatex。

**Q：想支持新的题型？**
按"领域覆盖度"思路：在 `domain_skills/` 加领域 YAML，在 `solve_advanced.py` 加对应求解函数即可。
