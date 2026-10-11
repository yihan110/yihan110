#!/usr/bin/env python3
"""
国产大模型求解引擎（LLM Solver）
=================================
本模块将 starter kit 的 Claude 推理能力迁移到国产大模型 **DeepSeek**。
用于处理 SymPy 无法精确求解的题目类型：证明题、文字题、概念题、复杂多步推理，
并为所有题目补充"人话"解题步骤。

特性：
  - API Key 从环境变量 DEEPSEEK_API_KEY 读取（不硬编码、不泄露）
  - 支持 stream=False 的普通对话补全
  - 解析模型输出为 (steps, answer) 结构，兼容 pipeline 渲染
  - Key 缺失时优雅降级（返回 None，由上层 fallback），不崩溃
"""

import json
import os
import re
import urllib.request

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

SYSTEM_PROMPT = (
    "你是一位严谨、耐心的大学高等数学助教。你的任务是为学生讲解数学题的完整求解过程。"
    "要求：步骤清晰、逻辑严谨、结论正确；数学公式一律用 LaTeX 行内符号 $...$ 表达。"
)


def get_key() -> str:
    """从环境变量读取 DeepSeek API Key。"""
    return os.environ.get("DEEPSEEK_API_KEY", "").strip()


def chat(prompt: str, max_tokens: int = 1500, temperature: float = 0.3) -> str:
    """调用 DeepSeek 对话补全。失败或 Key 缺失时返回 None。"""
    key = get_key()
    if not key:
        return None
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def solve_with_llm(problem_text: str, domain: str = "高等数学") -> dict:
    """
    用 DeepSeek 求解题目。

    返回: {"steps": [...], "answer": str, "answer_latex": str} 或 None。
    """
    prompt = (
        f"请用简体中文求解下面这道{domain}题，并满足：\n"
        "1. 给出完整、清晰的分步推导过程，每行一步，用序号（1. 2. 3. …）标注；\n"
        "2. 最后一行以“答案：”开头，给出明确的最终答案；\n"
        "3. 所有数学公式用 LaTeX 行内符号 $...$ 表示，例如 $\\sum_{n=1}^{\\infty}\\frac{1}{n}$。\n\n"
        f"题目：\n{problem_text}"
    )
    content = chat(prompt)
    if not content:
        return None

    lines = [ln.strip() for ln in content.split("\n") if ln.strip()]
    steps = []
    answer = ""
    for ln in lines:
        if ln.startswith("答案"):
            answer = ln[3:].strip()
        else:
            steps.append(ln)

    # 去掉步骤里的序号前缀（保留可读性）
    steps = [re.sub(r"^\d+[.、)）]\s*", "", s) for s in steps]
    if not answer and steps:
        answer = steps[-1]

    # 合并多行 $$...$$ 显示公式为单行 $...$（便于 LaTeX 排版）
    merged = []
    i = 0
    while i < len(steps):
        s = steps[i]
        if s.strip() == "$$":
            block = []
            i += 1
            while i < len(steps) and steps[i].strip() != "$$":
                block.append(steps[i].strip())
                i += 1
            if block:
                merged.append("$" + " ".join(block) + "$")
        else:
            merged.append(s)
        i += 1
    steps = merged

    return {
        "steps": steps,
        "answer": answer,
        "answer_latex": _extract_latex(answer),
    }


def _extract_latex(answer: str) -> str:
    """从答案文本中提取第一个 $...$ 公式作为 answer_latex，无则用原文。"""
    m = re.search(r"\$(.+?)\$", answer)
    if m:
        return m.group(1).strip()
    return answer


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        res = solve_with_llm(sys.argv[1], "高等数学")
        if res:
            print("STEPS:")
            for s in res["steps"]:
                print(" -", s)
            print("ANSWER:", res["answer"])
        else:
            print("LLM 求解失败（Key 缺失或 API 错误）")
