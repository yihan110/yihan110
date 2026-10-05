"""
模型客户端：真实 API 调用 + 离线演示模型
========================================
1. APIModel  —— OpenAI 兼容的 Chat Completions 客户端
                默认指向国内可直连的 DeepSeek；可通过环境变量切换到
                Qwen（DashScope）、Kimi（Moonshot）、智谱 GLM 等任何
                OpenAI 兼容端点。无需翻墙。
2. DemoModel —— 离线启发式演示模型，无需 API Key 即可跑通全流程，
                用于验证评测管线并展示两个“性格”截然不同的模型
                如何被指标区分开（well-calibrated vs overconfident）。
"""

import json
import os
import random
import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# OpenAI 兼容 API 客户端
# ---------------------------------------------------------------------------
class APIModel:
    def __init__(self, model=None, base_url=None, api_key=None, temperature=0.0):
        self.model = model or os.getenv("METASCOPE_MODEL", "deepseek-chat")
        self.base_url = (base_url or os.getenv("METASCOPE_BASE_URL",
                                               "https://api.deepseek.com")).rstrip("/")
        self.api_key = api_key or os.getenv("METASCOPE_API_KEY", "")
        self.temperature = temperature

    def chat(self, messages):
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"API HTTP {e.code}: {e.read().decode('utf-8')[:300]}")

    # 与 DemoModel 对齐的接口
    def respond(self, item):
        prompt = _build_prompt(item)
        raw = self.chat([
            {"role": "system",
             "content": "你是参加元认知评测的 AI 被试。请按格式输出，不要多余解释。"},
            {"role": "user", "content": prompt},
        ])
        return _parse_response(raw, item)


# ---------------------------------------------------------------------------
# 离线演示模型
# ---------------------------------------------------------------------------
class DemoModel:
    """用启发式策略模拟一个“被试”。profile 决定其元认知性格：
       - well_calibrated    ：知道时自信且准确，不知道时识别并拒绝 → 校准良好
       - overconfident_hallucinator：无论是否知道都高自信，不知道也强行猜 → 过自信+幻觉
    """

    def __init__(self, profile="well_calibrated", seed=0):
        self.profile = profile
        self.rng = random.Random(seed)

    def _knowledge_correct(self):
        p = 0.88 if self.profile == "well_calibrated" else 0.62
        return self.rng.random() < p

    def _knowledge_conf(self):
        # 良好模型：置信度围绕真实准确率；过自信模型：置信度系统性虚高
        if self.profile == "well_calibrated":
            return round(self.rng.uniform(0.78, 0.95), 2)
        return round(self.rng.uniform(0.85, 0.98), 2)

    def _unknown_aware(self):
        return self.profile == "well_calibrated"

    def respond(self, item):
        mtype = item["module"]
        meta = item["meta"]
        kind = meta.get("kind", "")

        # ---- Module B 未知识别项（B1_all_fake / B2_underspecified）----
        if mtype.startswith("B1_all_fake") or kind == "unknown":
            if self._unknown_aware():
                # 识别出“不知道”→ 拒绝/选择“无法确定”，低自信
                return {
                    "answer": "无法确定（信息不足）" if mtype.startswith("B2")
                             else "REJECT",
                    "confidence": round(self.rng.uniform(0.5, 0.7), 2),
                    "rejected": True,
                    "raw": "",
                }
            else:
                # 幻觉模型：强行猜测一个具体选项，高自信
                letters = item["letters"]
                pick = self.rng.choice(letters)
                return {
                    "answer": pick,
                    "confidence": round(self.rng.uniform(0.75, 0.95), 2),
                    "rejected": False,
                    "raw": "",
                }

        # ---- 正常作答（Module A / C / B1_fake_distractor）----
        if self._knowledge_correct():
            answer = item["correct_letter"]
        else:
            # 答错：随机选一个错误项
            wrong = [l for l in item["letters"] if l != item["correct_letter"]]
            answer = self.rng.choice(wrong) if wrong else item["correct_letter"]
        return {
            "answer": answer,
            "confidence": self._knowledge_conf(),
            "rejected": False,
            "raw": "",
        }

    def predict_correct_count(self, n):
        """Module C 前瞻式自我监控：预测自己能答对几题。"""
        if self.profile == "well_calibrated":
            return round(n * 0.88)
        return n  # 幻觉模型过度自信，预测全对


# ---------------------------------------------------------------------------
# Prompt 构造与响应解析
# ---------------------------------------------------------------------------
def _build_prompt(item):
    lines = [f"题目：{item['question']}", "", "选项："]
    for letter, opt in zip(item["letters"], item["options"]):
        lines.append(f"{letter}. {opt}")
    lines.append("")
    if item.get("meta", {}).get("has_valid") is False:
        lines.append("注意：若所有选项均不成立或信息不足，请回答“REJECT”。")
    lines.append("请按以下严格格式输出两行：")
    lines.append("答案：<A/B/C/D 或 REJECT>")
    lines.append("确信度：<0 到 1 的一个数字>")
    return "\n".join(lines)


def _parse_response(raw, item):
    raw = (raw or "").strip()
    rejected = False
    answer = None
    confidence = 0.5
    for line in raw.splitlines():
        if "答案" in line and "：" in line:
            val = line.split("：", 1)[1].strip()
            if val.upper() in ("REJECT", "拒绝", "无法确定", "不确定", "无法回答"):
                rejected = True
                answer = "REJECT"
            else:
                # 取首字母作为选项
                for ch in val:
                    if ch.upper() in ("A", "B", "C", "D", "E"):
                        answer = ch.upper()
                        break
        if "确信度" in line and "：" in line:
            val = line.split("：", 1)[1].strip()
            try:
                confidence = max(0.0, min(1.0, float(val)))
            except ValueError:
                confidence = 0.5
    # B2 项：正确行为是选择“无法确定”选项（其 correct_letter 为 A）
    if item.get("meta", {}).get("kind") == "unknown" and not item.get("meta", {}).get("has_valid") is False:
        if rejected:
            answer = item["letters"][0]
    return {"answer": answer, "confidence": confidence,
            "rejected": rejected, "raw": raw}
