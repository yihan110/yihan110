#!/usr/bin/env python3
"""
人类基线评分 —— 读取真人作答结果，计算人类校准/未知识别指标。
==============================================================
用法：
  1. python human_sheet.py            # 生成答题表与模板 CSV
  2. 真人作答，将答案与确信度填入 output/human_answers.csv
  3. python score_human.py            # 计算人类基线 → output/human_baseline.json / .md
"""

import os
import sys
import json
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metascope import generator, scoring
from metascope import runner as r
from human_sheet import pick_human_items


def read_responses(csv_path):
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    resp = []
    for row in rows:
        ans = (row.get("answer") or "").strip().upper()
        conf_raw = (row.get("confidence") or "").strip()
        try:
            conf = float(conf_raw) / 100.0
        except ValueError:
            conf = 0.5
        rejected = ans in ("REJECT", "无法确定", "不确定", "拒绝")
        resp.append({"answer": ans if ans else None,
                     "confidence": max(0.0, min(1.0, conf)),
                     "rejected": rejected})
    return resp


def score(data, responses):
    items = pick_human_items(data)
    assert len(items) == len(responses), "答题数量与题目数量不一致"
    # 判定
    confs, corrects = [], []
    b_conf, b_correct, b_hall = [], [], []
    a_confs, a_corrects = [], []
    for item, resp in zip(items, responses):
        c, conf, h = r._judge(item, resp)
        if item["module"].startswith("A"):
            a_confs.append(conf); a_corrects.append(c)
        elif item["module"].startswith("B"):
            b_conf.append(conf); b_correct.append(c); b_hall.append(h)
        confs.append(conf); corrects.append(c)

    acc_a = (sum(a_corrects) / len(a_corrects)) if a_corrects else 0.0
    ece = scoring.ece(a_confs, a_corrects)
    brier = scoring.brier(a_confs, a_corrects)
    overconf = scoring.overconfidence_rate(a_confs, a_corrects)
    rej = (sum(b_correct) / len(b_correct)) if b_correct else 0.0
    halluc = (sum(b_hall) / len(b_hall)) if b_hall else 0.0
    auc_known = scoring.unknown_awareness_auc(a_confs, a_corrects)

    ms = scoring.metascore(ece, brier, overconf, rej, reflex_err=0.05)
    return {
        "n": len(items),
        "模块A": {
            "n": len(a_confs),
            "accuracy": round(acc_a, 3),
            "avg_confidence": round(sum(a_confs)/len(a_confs), 3),
            "ece": round(ece, 3),
            "brier": round(brier, 3),
            "overconfidence": round(overconf, 3),
            "auc_known": round(auc_known, 3),
        },
        "模块B": {
            "n": len(b_conf),
            "rejection_rate": round(rej, 3),
            "hallucination_rate": round(halluc, 3),
            "accuracy_on_unknown": round((sum(b_correct)/len(b_correct)) if b_correct else 0, 3),
        },
        "MetaScore": ms,
    }


def main():
    data = generator.load_benchmark(os.path.join("data", "benchmark.json"))
    csv_path = os.path.join("output", "human_answers.csv")
    if not os.path.exists(csv_path):
        print("请先运行 human_sheet.py 生成模板，真人作答后另存为 output/human_answers.csv")
        return 1
    responses = read_responses(csv_path)
    res = score(data, responses)
    with open(os.path.join("output", "human_baseline.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    md = ["# 人类基线评测结果", "",
          "| 维度 | 值 |", "|---|---|",
          f"| 知识准确率 (A) | {res['模块A']['accuracy']} |",
          f"| 平均确信度 (A) | {res['模块A']['avg_confidence']} |",
          f"| ECE (A) | {res['模块A']['ece']} |",
          f"| Brier (A) | {res['模块A']['brier']} |",
          f"| 过自信率 (A) | {res['模块A']['overconfidence']} |",
          f"| 正确拒绝率 (B) | {res['模块B']['rejection_rate']} |",
          f"| 幻觉率 (B) | {res['模块B']['hallucination_rate']} |",
          "", "**MetaScore:**"]
    for k, v in res["MetaScore"].items():
        md.append(f"- {k}: **{v}**")
    with open(os.path.join("output", "human_baseline.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"人类基线结果 → output/human_baseline.json / .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
