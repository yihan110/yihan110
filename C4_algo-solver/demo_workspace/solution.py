#!/usr/bin/env python3
"""solution.py — 两数之和（哈希表，O(n)）· 用于 judge.py 验证演示"""
import sys

def main():
    data = sys.stdin.read().split()
    if not data:
        return
    n = int(data[0])
    nums = list(map(int, data[1:1 + n]))
    target = int(data[1 + n])

    seen = {}
    for i, val in enumerate(nums):
        need = target - val
        if need in seen:
            a, b = seen[need], i
            print(a, b)
            return
        seen[val] = i

if __name__ == "__main__":
    main()
