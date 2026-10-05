"""
校准曲线可视化（纯 Python 生成 SVG，零第三方依赖）
==================================================
把“确信度 vs 实际准确率”的分箱点与 45° 对角线绘制为 SVG，
评审可一眼看出模型是否过自信（点在对角线下方 = 高确信但低准确）。
"""

import os


def calibration_svg(bins, title="校准曲线", width=520, height=420):
    """bins: [(conf, acc, count), ...] 返回 SVG 字符串。"""
    margin = 50
    plot_w = width - 2 * margin
    plot_h = height - 2 * margin

    def sx(v):  # 确信度 0-1 -> x
        return margin + v * plot_w

    def sy(v):  # 准确率 0-1 -> y（上方为高）
        return margin + (1 - v) * plot_h

    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
                 f'viewBox="0 0 {width} {height}" font-family="Arial, sans-serif">')
    parts.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    parts.append(f'<text x="{width/2}" y="24" text-anchor="middle" font-size="16" '
                 f'font-weight="bold" fill="#333">{title}</text>')

    # 网格 + 坐标轴
    for i in range(11):
        v = i / 10
        gx, gy = sx(v), sy(v)
        parts.append(f'<line x1="{gx:.0f}" y1="{margin:.0f}" x2="{gx:.0f}" '
                     f'y2="{margin+plot_h:.0f}" stroke="#eef0f3" stroke-width="1"/>')
        parts.append(f'<line x1="{margin:.0f}" y1="{gy:.0f}" x2="{margin+plot_w:.0f}" '
                     f'y2="{gy:.0f}" stroke="#eef0f3" stroke-width="1"/>')
        parts.append(f'<text x="{gx:.0f}" y="{margin+plot_h+16:.0f}" text-anchor="middle" '
                     f'font-size="10" fill="#999">{v:.1f}</text>')
        parts.append(f'<text x="{margin-8:.0f}" y="{gy+3:.0f}" text-anchor="end" '
                     f'font-size="10" fill="#999">{(1-v):.1f}</text>')

    # 45° 完美校准参考线（y=x）
    parts.append(f'<line x1="{sx(0):.0f}" y1="{sy(0):.0f}" x2="{sx(1):.0f}" '
                 f'y2="{sy(1):.0f}" stroke="#b0b7c3" stroke-width="2" stroke-dasharray="6,4"/>')
    parts.append(f'<text x="{sx(0.98):.0f}" y="{sy(0.96):.0f}" font-size="11" '
                 f'fill="#9aa2ad">完美校准</text>')

    # 分箱点 + 折线
    pts = [(sx(c), sy(a)) for c, a, _ in bins]
    if pts:
        poly = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
        parts.append(f'<polyline points="{poly}" fill="none" stroke="#4c78ff" '
                     f'stroke-width="2" stroke-linejoin="round"/>')
    for (c, a, cnt), (x, y) in zip(bins, pts):
        r = 4 + min(3, cnt / 5)
        parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="#4c78ff" '
                     f'opacity="0.85"/>')
        parts.append(f'<text x="{x:.0f}" y="{y-8:.0f}" text-anchor="middle" font-size="9" '
                     f'fill="#4c78ff">n={cnt}</text>')

    # 轴标签
    parts.append(f'<text x="{margin+plot_w/2:.0f}" y="{height-6}" text-anchor="middle" '
                 f'font-size="12" fill="#333">确信度（reported confidence）</text>')
    parts.append(f'<text x="14" y="{height/2:.0f}" text-anchor="middle" font-size="12" '
                 f'fill="#333" transform="rotate(-90 14 {height/2:.0f})">准确率（accuracy）</text>')
    parts.append('</svg>')
    return "\n".join(parts)


def save_calibration_svg(bins, out_path, title="校准曲线"):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(calibration_svg(bins, title=title))
    return out_path
