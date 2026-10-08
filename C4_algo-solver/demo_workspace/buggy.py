#!/usr/bin/env python3
"""buggy.py — 故意有 bug 的题解（暴力但只比较相邻两数），用于证明 judge.py 能抓错"""
import sys

def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    nums = list(map(int, data[1:1 + n]))
    target = int(data[1 + n])
    for i in range(n - 1):           # 只检查相邻对 —— 会漏掉 0 和 2 这种不相邻答案
        if nums[i] + nums[i + 1] == target:
            print(i, i + 1)
            return

if __name__ == "__main__":
    main()
