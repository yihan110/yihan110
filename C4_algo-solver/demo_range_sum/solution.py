#!/usr/bin/env python3
"""solution.py — 区间和查询（前缀和，O(n+m)）
输入: n m / a[1..n] / m 行 l r (1-based 闭区间)
输出: 每行一个区间和
约束: 1<=n,m<=1e5, -1e9<=a[i]<=1e9
"""
import sys

def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    idx = 0
    n = int(data[idx]); idx += 1
    m = int(data[idx]); idx += 1
    a = [int(data[idx + i]) for i in range(n)]; idx += n

    # 前缀和
    pre = [0] * (n + 1)
    for i in range(1, n + 1):
        pre[i] = pre[i - 1] + a[i - 1]

    out = []
    for _ in range(m):
        l = int(data[idx]); r = int(data[idx + 1]); idx += 2
        out.append(str(pre[r] - pre[l - 1]))
    sys.stdout.write("\n".join(out))

if __name__ == "__main__":
    main()
