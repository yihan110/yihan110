#!/usr/bin/env python3
"""solution.py — PAT乙级1009 说反话（单词倒序）
输入: 一行字符串（总长<=80，单词用1个空格分隔，句末无多余空格）
输出: 倒序后的句子，占一行
"""
import sys

def main():
    s = sys.stdin.readline().strip()
    words = s.split()
    sys.stdout.write(" ".join(reversed(words)))

if __name__ == "__main__":
    main()
