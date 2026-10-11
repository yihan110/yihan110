#!/usr/bin/env python3
"""gpa_calc.py —— 加权绩点计算器。"""


def calc_gpa(scores, credits):
    total_credit = sum(credits)
    if total_credit == 0:
        return 0.0
    return sum(s * c for s, c in zip(scores, credits)) / total_credit


if __name__ == "__main__":
    scores = [float(x) for x in input("各科成绩(空格分隔): ").split()]
    credits = [float(x) for x in input("各科学分(空格分隔): ").split()]
    print("加权平均分:", round(calc_gpa(scores, credits), 2))
