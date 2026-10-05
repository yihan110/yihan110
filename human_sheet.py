#!/usr/bin/env python3
"""
生成“人类答题表” —— 供真人作答，用于采集实测人类基线。
==========================================================
用法：
  python human_sheet.py            # 生成 output/human_answer_sheet.md 与答题模板 CSV

说明：
  选出的题量控制在 24 题左右（人类可负担），含 Module A 知识校准与 Module B 未知识别。
  真人作答后，将答案填入模板 CSV，再运行 score_human.py 计算人类基线。
"""

import os
import sys
import csv
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metascope import generator


def pick_human_items(data, a_knowledge=12, a_arithmetic=4, b_fake=4, b_trap=2, seed=2026):
    rng = random.Random(seed)
    a = data["modules"]["A_knowledge_calibration"]
    b = data["modules"]["B_unknown_awareness"]
    a_k = [i for i in a if i["module"] == "A_knowledge"]
    a_r = [i for i in a if i["module"] == "A_arithmetic"]
    b1 = [i for i in b if i["module"] == "B1_fake_distractor"]
    b1f = [i for i in b if i["module"] == "B1_all_fake"]
    b2 = [i for i in b if i["module"] == "B2_underspecified"]
    items = []
    items += rng.sample(a_k, min(a_knowledge, len(a_k)))
    items += rng.sample(a_r, min(a_arithmetic, len(a_r)))
    items += rng.sample(b1, min(b_fake, len(b1)))
    items += rng.sample(b1f, min(1, len(b1f)))
    items += rng.sample(b2, min(b_trap, len(b2)))
    return items


def generate_human_sheet(data, out_md, out_csv):
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    items = pick_human_items(data)
    lines = ["# MetaScope 人类基线 · 答题表", "",
             "请逐题作答：写出选项（A/B/C/D）；若你认为**没有任何选项成立 / 信息不足**，写 `REJECT`。",
             "每题再给出你的**确信度**（0-100，100=非常确定）。", ""]
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "answer", "confidence"])
        for i, it in enumerate(items, 1):
            lines.append(f"### 第 {i} 题 (id={it['module']}-{i})")
            lines.append(f"**{it['question']}**")
            lines.append("")
            for letter, opt in zip(it["letters"], it["options"]):
                lines.append(f"- {letter}. {opt}")
            if it.get("meta", {}).get("has_valid") is False:
                lines.append("_（本题所有选项均为编造，正确答案为 REJECT）_")
            lines.append("")
            lines.append("> 我的答案：____  　确信度：____ %")
            lines.append("")
            w.writerow([f"{it['module']}-{i}", "", ""])
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"人类答题表: {out_md}")
    print(f"答题模板CSV: {out_csv}  （共 {len(items)} 题）")


if __name__ == "__main__":
    data_path = os.path.join("data", "benchmark.json")
    if not os.path.exists(data_path):
        generator.save_benchmark(data_path)
    data = generator.load_benchmark(data_path)
    generate_human_sheet(data,
                         os.path.join("output", "human_answer_sheet.md"),
                         os.path.join("output", "human_answers_template.csv"))
