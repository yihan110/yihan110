"""report.py —— Level 4：评审报告生成。

输出三件套：
  1. Markdown 评审报告（班级总览 + 作者详情 + 排名 + 改进建议）
  2. Excel 详表（openpyxl，适合老师批量看/排序）
  3. HTML 可视化仪表板（自包含单文件，可双击打开，含排名条形图）
额外能力：
  * 版本追踪：检测 `_v2/_v3`，展示作者迭代轨迹
  * 排名：按四条件加权综合分排序（权重可配置）
"""

from __future__ import annotations

import html as _html
from datetime import datetime
from pathlib import Path

from .completeness import CompletenessResult
from .quality import QualityResult


# ---------------------------------------------------------------------------
# 综合分（对齐 c4_rubric.yaml scoring）
# ---------------------------------------------------------------------------
def composite_score(completeness: CompletenessResult, quality: QualityResult,
                    weights: dict | None = None) -> float:
    """completeness*0.4 + quality*0.6，映射到 0~100。"""
    w = weights or {"completeness": 0.4, "quality": 0.6}
    return (completeness.score * w["completeness"] + quality.score * w["quality"]) * 100


def _fmt_score(x: float) -> str:
    return f"{x:.1f}"


# ---------------------------------------------------------------------------
# Markdown 报告
# ---------------------------------------------------------------------------
def generate_markdown(
    folder: str,
    completeness_map: dict[str, CompletenessResult],
    quality_map: dict[str, QualityResult],
    scores: dict[str, float],
    non_c4: list,
    versions: dict[str, list] | None = None,
    generated_at: str | None = None,
) -> str:
    """生成完整 Markdown 评审报告（对应 C4A 报告模板，并增强班级总览与版本轨迹）。"""
    generated_at = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    authors = list(completeness_map.keys())
    ranked = sorted(authors, key=lambda a: scores.get(a, 0), reverse=True)

    n = len(authors)
    n_complete = sum(1 for a in authors if completeness_map[a].present_count >= 5)
    n_partial = sum(1 for a in authors if 3 <= completeness_map[a].present_count < 5)
    n_insufficient = n - n_complete - n_partial
    avg_quality = (sum(quality_map[a].score for a in authors) / n) if n else 0.0
    avg_composite = (sum(scores.get(a, 0) for a in authors) / n) if n else 0.0

    # 最常见缺失 & 最弱维度
    missing_counter: dict[str, int] = {}
    for a in authors:
        for item in completeness_map[a].items.values():
            if not item.present:
                missing_counter[item.label] = missing_counter.get(item.label, 0) + 1
    most_missing = max(missing_counter, key=missing_counter.get) if missing_counter else "无"
    weakest = min(
        ("可复用", "可执行", "可验证", "IO 明确"),
        key=lambda k: sum(quality_map[a].criteria[_key_of(k)].value for a in authors)
        if authors else 0)

    L = []
    L.append("# C4 提交自动评审报告")
    L.append("")
    L.append(f"生成时间：{generated_at}")
    L.append(f"扫描路径：`{folder}`")
    L.append(f"识别提交：{n} 位作者")
    L.append("")
    L.append("## 一、班级总览")
    L.append("")
    L.append("| 指标 | 数值 |")
    L.append("|------|------|")
    L.append(f"| 总提交人数 | {n} |")
    L.append(f"| 完整提交（5/5） | {n_complete} |")
    L.append(f"| 部分提交（3-4/5） | {n_partial} |")
    L.append(f"| 严重缺失（<3/5） | {n_insufficient} |")
    L.append(f"| 平均质量分 | {_fmt_score(avg_quality * 4)}/4.0 |")
    L.append(f"| 平均综合分 | {_fmt_score(avg_composite)}/100 |")
    L.append("")
    if non_c4:
        L.append(f"> 另有 {len(non_c4)} 个非 C4 文件被过滤（已在报告末尾列出）。")
        L.append("")

    # 作者详情
    L.append("## 二、作者详情")
    L.append("")
    for a in ranked:
        comp = completeness_map[a]
        qual = quality_map[a]
        L.append(f"### {a}")
        L.append("")
        L.append("**完整性检查：**")
        L.append("")
        L.append("| 必需文件 | 状态 | 匹配文件 |")
        L.append("|----------|------|----------|")
        for item in comp.items.values():
            flag = "✅" if item.present else ("⚠️" if item.fuzzy else "❌")
            matched = "、".join(item.matched_files) if item.matched_files else "—"
            if item.present and item.fuzzy:
                flag = "⚠️(内容命中)"
            L.append(f"| {item.label} | {flag} | {matched} |")
        L.append(f"| **合计** | **{comp.present_count}/5 {comp.status}** | |")
        L.append("")
        L.append("**质量评审（四条件）：**")
        L.append("")
        L.append("| 条件 | 评级 | 依据 |")
        L.append("|------|------|------|")
        for key, c in qual.criteria.items():
            evidence = "；".join(c.evidence[:3]) if c.evidence else "—"
            L.append(f"| {c.label} | {c.mark} | {evidence} |")
        L.append("")
        L.append(f"**综合评分：** 完整性 {comp.present_count}/5 · 质量 {_fmt_score(qual.score * 4)}/4.0 · **综合 {_fmt_score(scores.get(a, 0))}/100**")
        L.append("")
        # 版本轨迹
        if versions and versions.get(a):
            hist = ", ".join(versions[a])
            L.append(f"**版本轨迹：** {hist}")
            L.append("")
        L.append("**改进建议：**")
        L.append("")
        sug = []
        for item in comp.items.values():
            if not item.present:
                sug.append(f"补齐缺失文件：{item.label}")
        for c in qual.criteria.values():
            if c.suggestions:
                sug.extend(c.suggestions[:2])
        if not sug:
            sug.append("已满足基本要求，建议进一步补充负向测试与真实运行截图。")
        for i, s in enumerate(sug[:6], 1):
            L.append(f"{i}. {s}")
        L.append("")
        L.append("---")
        L.append("")

    # 排名
    L.append("## 三、排名（按综合分）")
    L.append("")
    L.append("| 排名 | 作者 | 完整性 | 质量分 | 综合分 | 评级 |")
    L.append("|------|------|--------|--------|--------|------|")
    for i, a in enumerate(ranked, 1):
        comp = completeness_map[a]
        qual = quality_map[a]
        L.append(f"| {i} | {a} | {comp.present_count}/5 | {_fmt_score(qual.score * 4)}/4.0 | {_fmt_score(scores.get(a, 0))}/100 | {qual.mark} |")
    L.append("")

    # 全班改进建议
    L.append("## 四、全班改进建议")
    L.append("")
    L.append(f"- 最常见缺失文件：**{most_missing}**")
    L.append(f"- 最弱评审维度：**{weakest}**")
    L.append("- 建议：所有同学在提交前用本评审技能（`c4_evaluator`）自检一遍，补齐缺失、强化最弱维度。")
    L.append("")

    if non_c4:
        L.append("## 附：被过滤的非 C4 文件")
        L.append("")
        L.append("| 文件 |")
        L.append("|------|")
        for f in non_c4:
            L.append(f"| {f.name} |")
        L.append("")
    return "\n".join(L)


def _key_of(cn_label: str) -> str:
    """中文条件标签 -> key（用于最弱维度统计）。"""
    return {"可复用": "reusable", "可执行": "executable",
            "可验证": "verifiable", "IO 明确": "clear_io"}.get(cn_label, cn_label)


# ---------------------------------------------------------------------------
# Excel 详表
# ---------------------------------------------------------------------------
def generate_excel(
    completeness_map: dict[str, CompletenessResult],
    quality_map: dict[str, QualityResult],
    scores: dict[str, float],
    out_path: str | Path,
) -> str:
    """生成 Excel 详表（每个作者一行，含五文件状态、四条件评级、综合分）。"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("缺少依赖 openpyxl，请先 `pip install openpyxl`") from e

    wb = Workbook()
    ws = wb.active
    ws.title = "C4A评审汇总"

    headers = ["排名", "作者", "完整性", "状态"] + [
        "Skill说明", "可执行", "Demo", "教学说明", "AI日志"] + [
        "可复用", "可执行(质量)", "可验证", "IO明确", "质量分/4.0", "综合分/100"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    ranked = sorted(completeness_map, key=lambda a: scores.get(a, 0), reverse=True)
    green = PatternFill("solid", fgColor="C6EFCE")
    yellow = PatternFill("solid", fgColor="FFEB9C")
    red = PatternFill("solid", fgColor="FFC7CE")

    for i, a in enumerate(ranked, 1):
        comp = completeness_map[a]
        qual = quality_map[a]
        row = [i, a, f"{comp.present_count}/5", comp.status]
        for key in ("skill_doc", "executable_content", "demo", "teaching_doc", "ai_log"):
            it = comp.items.get(key)
            row.append("✅" if it and it.present else "❌")
        for key in ("reusable", "executable", "verifiable", "clear_io"):
            c = qual.criteria.get(key)
            row.append(c.mark if c else "—")
        row.append(f"{qual.score * 4:.2f}")
        row.append(f"{scores.get(a, 0):.1f}")
        ws.append(row)
        fill = green if comp.present_count >= 5 else (yellow if comp.present_count >= 3 else red)
        for cell in ws[ws.max_row]:
            cell.fill = fill

    width_map = {"A": 6, "B": 16, "C": 10, "D": 10, "E": 10, "F": 10, "G": 10,
                 "H": 10, "I": 10, "J": 10, "K": 12, "L": 14, "M": 12, "N": 12,
                 "O": 12, "P": 12}
    for col, w in width_map.items():
        ws.column_dimensions[col].width = w

    wb.save(str(out_path))
    return str(out_path)


# ---------------------------------------------------------------------------
# HTML 可视化仪表板（自包含单文件）
# ---------------------------------------------------------------------------
def generate_html(
    folder: str,
    completeness_map: dict[str, CompletenessResult],
    quality_map: dict[str, QualityResult],
    scores: dict[str, float],
    out_path: str | Path,
    generated_at: str | None = None,
) -> str:
    """生成自包含 HTML 仪表板（含排名条形图，用内联 CSS 绘制，无需联网）。"""
    generated_at = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    ranked = sorted(completeness_map, key=lambda a: scores.get(a, 0), reverse=True)
    n = len(ranked)

    rows_html = []
    max_score = max(scores.values()) if scores else 1
    for i, a in enumerate(ranked, 1):
        comp = completeness_map[a]
        qual = quality_map[a]
        s = scores.get(a, 0)
        pct = (s / max_score * 100) if max_score else 0
        comp_items = "".join(
            f'<span class="chip {"ok" if it.present else "no"}">{it.label[:2]}</span>'
            for it in comp.items.values())
        qual_items = "".join(
            f'<span class="chip q">{c.mark}</span>' for c in qual.criteria.values())
        rows_html.append(
            f'<tr><td>{i}</td><td><b>{_html.escape(a)}</b></td>'
            f'<td>{comp.present_count}/5</td><td>{comp_items}</td>'
            f'<td>{qual_items}</td><td>{qual.score * 4:.2f}</td>'
            f'<td><div class="bar"><div class="fill" style="width:{pct:.1f}%"></div></div>'
            f'<span class="score">{s:.1f}</span></td></tr>')
    table = "\n".join(rows_html)

    n_complete = sum(1 for a in ranked if completeness_map[a].present_count >= 5)
    n_partial = sum(1 for a in ranked if 3 <= completeness_map[a].present_count < 5)
    avg_q = (sum(quality_map[a].score for a in ranked) / n) if n else 0

    page = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>C4 技能提交自动评审 · 班级仪表板</title>
<style>
  :root {{ --blue:#2563eb; --green:#16a34a; --red:#dc2626; --amber:#d97706; }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:-apple-system,'Segoe UI',Roboto,'Microsoft YaHei',sans-serif;
         margin:0; background:#f1f5f9; color:#0f172a; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:28px 20px 60px; }}
  header {{ background:linear-gradient(135deg,#1e3a8a,#2563eb); color:#fff;
            border-radius:14px; padding:26px 28px; margin-bottom:22px; }}
  header h1 {{ margin:0 0 6px; font-size:26px; }}
  header p {{ margin:2px 0; opacity:.9; font-size:13px; }}
  .cards {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:22px; }}
  .card {{ background:#fff; border-radius:12px; padding:18px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  .card .num {{ font-size:30px; font-weight:700; color:var(--blue); }}
  .card .lbl {{ font-size:13px; color:#64748b; margin-top:4px; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:12px;
           overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  th {{ background:#0f172a; color:#fff; padding:11px 12px; font-size:13px; text-align:left; }}
  td {{ padding:10px 12px; border-bottom:1px solid #e2e8f0; font-size:13px; }}
  tr:hover td {{ background:#f8fafc; }}
  .chip {{ display:inline-block; min-width:26px; text-align:center; padding:2px 5px;
          border-radius:6px; margin-right:3px; font-size:11px; }}
  .chip.ok {{ background:#dcfce7; color:#166534; }}
  .chip.no {{ background:#fee2e2; color:#991b1b; }}
  .chip.q {{ background:#e0e7ff; color:#3730a3; }}
  .bar {{ display:inline-block; width:90px; height:8px; background:#e2e8f0;
          border-radius:6px; vertical-align:middle; overflow:hidden; }}
  .fill {{ height:100%; background:linear-gradient(90deg,#3b82f6,#2563eb); }}
  .score {{ margin-left:8px; font-weight:700; }}
  .foot {{ color:#64748b; font-size:12px; margin-top:16px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>📊 C4 技能提交自动评审 · 班级仪表板</h1>
    <p>生成时间：{_html.escape(generated_at)} ｜ 扫描路径：<code>{_html.escape(folder)}</code></p>
    <p>识别提交：{n} 位作者 ｜ 完整 5/5：{n_complete} ｜ 部分：{n_partial} ｜ 平均质量分：{avg_q * 4:.2f}/4.0</p>
  </header>
  <div class="cards">
    <div class="card"><div class="num">{n}</div><div class="lbl">提交作者</div></div>
    <div class="card"><div class="num" style="color:var(--green)">{n_complete}</div><div class="lbl">完整提交 (5/5)</div></div>
    <div class="card"><div class="num" style="color:var(--amber)">{n_partial}</div><div class="lbl">部分提交</div></div>
    <div class="card"><div class="num" style="color:var(--blue)">{avg_q * 4:.2f}</div><div class="lbl">平均质量分 / 4</div></div>
  </div>
  <table>
    <thead><tr><th>排名</th><th>作者</th><th>完整性</th><th>必需文件</th>
      <th>四条件</th><th>质量分</th><th>综合分</th></tr></thead>
    <tbody>
{table}
    </tbody>
  </table>
  <p class="foot">图例：必需文件 = Skill说明 / 可执行 / Demo / 教学 / AI日志；四条件 = 可复用 / 可执行 / 可验证 / IO明确。</p>
</div>
</body>
</html>"""
    Path(out_path).write_text(page, encoding="utf-8")
    return str(out_path)
