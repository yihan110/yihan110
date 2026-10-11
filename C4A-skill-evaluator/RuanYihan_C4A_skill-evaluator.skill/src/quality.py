"""quality.py —— Level 3：技能质量评审（C4 四条件）。

方案选择（混合式，本模块是核心创新点）：
  * 主引擎 = 规则 + 信号计数（确定性、可复现、零成本、可测试），
    依据 c4_rubric.yaml 的 positive/negative signals 与 check_items 计分；
  * 可选增强 = 可插拔 LLM 深度评审接口（`LLMReviewer`），当用户在命令行传入
    --llm-reviewer 时启用，对规则结果做语义复核与补充建议；
  * 为什么选混合式：纯规则快但覆盖率低、易误判；纯 LLM 灵活但慢、贵、不确定。
    混合式让「规则快筛 + LLM 深审」分工，兼顾确定性与理解力（方案文档有详述）。

评级规则（对齐 c4_rubric.yaml）：
  ✅ = 满足 ≥2 个 check items；⚠️ = 满足 1 个；❌ = 满足 0 个。

为降低误判率，检测信号刻意采用「成组关键词」而非单个泛词：
  例如「示例」用 示例/example/样例/demo 判定，而不是把「输入」也算成示例证据，
  避免把正常描述误判为“有示例”。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import load_rubric, normalize_text

GRADE_MAP = {"pass": "✅", "partial": "⚠️", "fail": "❌"}
VALUE_MAP = {"pass": 1.0, "partial": 0.5, "fail": 0.0}


@dataclass
class CriterionScore:
    key: str
    label: str
    grade: str = "fail"              # pass / partial / fail
    satisfied: int = 0
    total: int = 0
    evidence: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def mark(self) -> str:
        return GRADE_MAP[self.grade]

    @property
    def value(self) -> float:
        return VALUE_MAP[self.grade]


@dataclass
class QualityResult:
    author: str
    criteria: dict[str, CriterionScore] = field(default_factory=dict)

    @property
    def score(self) -> float:          # 0.0 ~ 1.0
        if not self.criteria:
            return 0.0
        return sum(c.value for c in self.criteria.values()) / len(self.criteria)

    @property
    def mark(self) -> str:
        s = self.score
        if s >= 0.75:
            return "优秀"
        if s >= 0.5:
            return "良好"
        if s > 0:
            return "待改进"
        return "不合格"


# ---------------------------------------------------------------------------
# 检测辅助
# ---------------------------------------------------------------------------
# 否定词：用于避免把“无安装说明 / 无需配置 / 不依赖”误判为“有安装/有配置”。
_NEGATION = ("无", "没有", "未", "不", "无需", "缺少", "缺", "免", "非", "without", "not ")


def _has(text: str, *terms: str) -> bool:
    """否定感知的包含检测：命中关键词但前文带否定词（如“无/没有/不”）时不算命中。"""
    norm = normalize_text(text)
    for t in terms:
        t = t.lower()
        if not t:
            continue
        for m in re.finditer(re.escape(t), norm):
            ctx = norm[max(0, m.start() - 4): m.start()]
            if any(n in ctx for n in _NEGATION):
                continue  # 该处被否定，跳过
            return True
    return False


# 硬编码绝对路径 / 密钥检测（负向信号）
# - Windows 盘符：C:\ / C:/，但排除 URL 协议（https:/ 前的 s: 不是盘符）
_WIN_DRIVE_RE = re.compile(r"(?<![a-zA-Z])[a-zA-Z]:[\\/]", re.IGNORECASE)
_POSIX_HOME_RE = re.compile(r"[/\\](users|home|Users)\b", re.IGNORECASE)
# 硬编码凭据：仅当把字面量（带引号字符串）赋给密钥名时才算硬编码；
# `export API_KEY=xxx` 或 `os.environ["API_KEY"]` 这类环境变量用法不算。
_CRED_RE = re.compile(
    r"(api_key|apikey|password|passwd|secret|access_token)\s*[:=]\s*['\"][^'\"]{2,}['\"]",
    re.IGNORECASE)


def _has_hardcoded_path(text: str) -> bool:
    """检测是否含硬编码绝对路径或凭据（跨 Windows/POSIX，大小写不敏感）。"""
    if _WIN_DRIVE_RE.search(text):
        return True
    if _POSIX_HOME_RE.search(text):
        return True
    if _CRED_RE.search(text):
        return True
    if "我的电脑" in text:
        return True
    return False


def _merge_author_texts(files) -> str:
    """把作者全部文件的可读文本拼接起来，供规则评审使用。"""
    parts = []
    for fi in files:
        content = getattr(fi, "_content", None)
        if content:
            parts.append(f"{fi.name}\n{content}")
    return "\n\n".join(parts)


def _mk(key: str, label: str, items: list[tuple[bool, str]], total: int) -> CriterionScore:
    """按 check items 命中数定级，并生成“缺什么补什么”的针对性建议。"""
    satisfied = sum(1 for ok, _ in items if ok)
    evidence = [desc for ok, desc in items if ok]
    c = CriterionScore(key=key, label=label, satisfied=satisfied, total=total, evidence=evidence)
    c.grade = "pass" if satisfied >= 2 else ("partial" if satisfied >= 1 else "fail")
    # 针对性建议：只针对未命中的 check items
    c.suggestions = [f"缺失「{desc}」" for ok, desc in items if not ok]
    return c


# ---------------------------------------------------------------------------
# 四个条件的评审函数
# ---------------------------------------------------------------------------
def _eval_reusable(text: str, spec: dict) -> CriterionScore:
    total = len(spec.get("check_items", [])) or 4
    items = [
        (_has(text, "安装", "install", "pip install", "npm install", "requirements.txt",
              "setup.py"), "安装/依赖说明"),
        (_has(text, "环境要求", "requirements", "dependencies", "python 3", "python3",
              "环境", "平台"), "环境/平台要求"),
        (not _has_hardcoded_path(text), "无硬编码路径/密钥"),
        (_has(text, "参数", "相对路径", "通用", "兼容", "跨平台", "platform", "任意"),
         "参数化/通用性说明"),
    ]
    return _mk("reusable", spec.get("label_cn", "可复用"), items, total)


def _eval_executable(text: str, files, spec: dict) -> CriterionScore:
    total = len(spec.get("check_items", [])) or 4
    items = [
        (_has(text, "```", "def ", "class ", "import ", "from ", "return "),
         "包含代码/函数/类定义"),
        (any(fi.ext == ".skill" for fi in files) or _has(text, "---\nname:", "yaml frontmatter"),
         ".skill 包或 YAML frontmatter"),
        (_has(text, "workflow", "pipeline", "步骤", "流程", "step"), "可执行 workflow/步骤"),
        (_has(text, "运行", "执行", "python ", "python3", "run ", "npm run", "bash"),
         "含可运行入口/命令"),
    ]
    return _mk("executable", spec.get("label_cn", "可执行"), items, total)


def _eval_verifiable(text: str, files, spec: dict) -> CriterionScore:
    total = len(spec.get("check_items", [])) or 4
    demo_file = any(fi.ext in (".mp4", ".mov", ".webm", ".png", ".jpg", ".gif", ".jpeg")
                    for fi in files)
    items = [
        (_has(text, "测试", "test", "pytest", "测试用例", "tests/"), "测试/测试用例"),
        (_has(text, "示例", "example", "样例", "demo", "演示"), "示例/演示"),
        (_has(text, "预期", "expected", "期望", "结果", "result", "pass", "fail", "判据"),
         "预期结果/判据"),
        (demo_file, "附 demo 视频/截图"),
    ]
    return _mk("verifiable", spec.get("label_cn", "可验证"), items, total)


def _eval_clear_io(text: str, spec: dict) -> CriterionScore:
    total = len(spec.get("check_items", [])) or 4
    io_pattern = spec.get("io_pattern", r"输入.*输出|input.*output|接受.*返回|给定.*得到")
    items = [
        (bool(re.search(io_pattern, text, flags=re.IGNORECASE)), "“输入X，输出Y”一句话"),
        (_has(text, "输入", "input"), "明确输入"),
        (_has(text, "输出", "output", "返回", "return", "生成"), "明确输出"),
        (_has(text, "类型", "格式", "format", "type", "扩展名", "str", "csv", "json", "md"),
         "输入/输出类型或格式"),
    ]
    return _mk("clear_io", spec.get("label_cn", "IO 明确"), items, total)


# ---------------------------------------------------------------------------
# 可插拔 LLM 深度评审接口（可选增强）
# ---------------------------------------------------------------------------
class LLMReviewer:
    """规则层的可选语义增强。

    默认不启用（保持确定性、可离线运行）。如需启用，子类实现 review()，
    将规则结果与提交内容一起交给大模型做语义复核并返回补充建议。
    """

    name = "abstract"

    def review(self, author: str, text: str, rule_result: QualityResult) -> dict:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 质量评审入口
# ---------------------------------------------------------------------------
def evaluate_quality(
    author: str,
    files: list,
    rubric: dict | None = None,
    llm_reviewer: LLMReviewer | None = None,
) -> QualityResult:
    rubric = rubric or load_rubric()
    qspec = rubric.get("quality_criteria", {})
    text = _merge_author_texts(files)

    result = QualityResult(author=author)
    evals = {
        "reusable": lambda s: _eval_reusable(text, s),
        "executable": lambda s: _eval_executable(text, files, s),
        "verifiable": lambda s: _eval_verifiable(text, files, s),
        "clear_io": lambda s: _eval_clear_io(text, s),
    }
    for key, spec in qspec.items():
        if key in evals:
            result.criteria[key] = evals[key](spec)

    # LLM 增强层：仅在有 reviewer 且提交内容非空时启用
    if llm_reviewer is not None and text.strip():
        llm_feedback = llm_reviewer.review(author, text, result)
        if llm_feedback.get("suggestions"):
            for key, sug in llm_feedback["suggestions"].items():
                if key in result.criteria:
                    result.criteria[key].suggestions.extend(sug[:2])
    return result
