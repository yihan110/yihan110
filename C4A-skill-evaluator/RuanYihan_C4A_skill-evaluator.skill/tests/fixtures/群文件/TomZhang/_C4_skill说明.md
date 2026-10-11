# TomZhang — 技能说明：flashcard-maker

> 提交人：TomZhang ｜ 版本：v2（当前为最新版）

**输入**一组知识点文本，**输出**一组可导入 Anki 的问答卡片（CSV）。

## 解决什么问题
背单词、背知识点效率低，本技能把「知识点 → 复习卡片」自动化。

## 环境要求
- Python 3，`pip install -r requirements.txt`
- 平台：Windows / macOS / Linux

## 使用步骤
1. 准备知识点文本文件。
2. 运行 `python make_cards.py input.txt`。
3. 得到 `cards.csv`，导入 Anki 即可。

## 四条件
- 可复用：有安装与环境要求，无硬编码路径
- 可执行：`_C4_技能包_v2.skill` 内含可运行脚本
- 可验证：附 demo 录屏（mp4）
- IO 明确：输入知识点文本，输出 CSV 卡片
