#!/usr/bin/env python3
"""
Stage 3 扩展：高等数学求解器（Advanced Math Solver）
=====================================================
在 starter kit（微积分极限）基础上扩展的新领域：
  - 多元函数微分学：偏导数、全微分、拉格朗日乘数法
  - 重积分：二重积分、三重积分
  - 无穷级数：级数收敛性、比值判别法、幂级数、泰勒/麦克劳林展开
  - 证明/文字题：SymPy 无法精确求解的，交给国产模型 DeepSeek 推理

设计原则：双层引擎混合
  层1  SymPy 符号计算 -> 确定性精确答案（计算题）
  层2  DeepSeek LLM   -> 推理/证明/文字/复杂多步（无法精确计算的）
既保证正确率，又扩展了 starter 不具备的推理能力。

用法：由 solve.py 的 solve_problem 优先调用本模块；本模块无法处理时返回 None，
     由原 solver 兜底（保持向后兼容）。
"""

import re

from sympy import (
    symbols, Symbol, diff, integrate, limit, series, summation,
    solve, simplify, factor, expand, latex, oo, E, factorial, Rational, sqrt,
    sin, cos, tan, exp, log, ln, Abs, Piecewise, pi,
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor,
)
from sympy.abc import x, y, z, n, k

try:
    from llm_solver import solve_with_llm
except ImportError:
    from scripts.llm_solver import solve_with_llm

dx, dy = Symbol("dx"), Symbol("dy")
lam = Symbol("lambda")

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

_LOCAL = {
    "x": x, "y": y, "z": z, "n": n, "k": k,
    "pi": pi, "e": E, "oo": oo, "E": E,
    "sin": sin, "cos": cos, "tan": tan, "exp": exp,
    "log": log, "ln": ln, "sqrt": sqrt, "Abs": Abs,
    "factorial": factorial,
}


def _find_matching_brace(s, pos):
    if pos >= len(s) or s[pos] != "{":
        return -1
    depth = 1
    i = pos + 1
    while i < len(s) and depth > 0:
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
        i += 1
    return i - 1 if depth == 0 else -1


def _replace_frac(s):
    while "\\frac{" in s:
        idx = s.index("\\frac{")
        num_start = idx + 6
        num_end = _find_matching_brace(s, num_start - 1)
        if num_end < 0 or num_end + 1 >= len(s) or s[num_end + 1] != "{":
            break
        den_start = num_end + 2
        den_end = _find_matching_brace(s, num_end + 1)
        if den_end < 0:
            break
        num = s[num_start:num_end]
        den = s[den_start:den_end]
        s = s[:idx] + f"(({num})/({den}))" + s[den_end + 1:]
    return s


def _clean_expr(s):
    s = s.strip()
    s = re.sub(r"\\iint", "", s)
    s = re.sub(r"\\iiint", "", s)
    s = re.sub(r"\\oint", "", s)
    s = re.sub(r"\\int", "", s)
    s = re.sub(r"\\sum_[^{}]*\{[^{}]*\}[^{}]*\{[^{}]*\}", "", s)
    s = re.sub(r"\\sum", "", s)
    s = re.sub(r"\\,?d[A-Z]", "", s)
    s = re.sub(r"\,d", " ", s)
    s = re.sub(r"[DE]=\[[^\]]*\]", "", s)
    s = re.sub(r"^[a-zA-Z]\([^)]*\)\s*=", "", s)
    s = re.sub(r"^[a-zA-Z]\s*=", "", s)
    s = re.sub(r"e\^\{([^}]+)\}", r"E**(\1)", s)
    s = re.sub(r"e\^(\w)", r"E**\1", s)
    s = _replace_frac(s)
    s = re.sub(r"(\w)!", r"factorial(\1)", s)
    s = s.replace("!", "factorial")
    for fn in ["sin", "cos", "tan", "ln", "log", "exp", "sqrt", "arcsin", "arccos", "arctan"]:
        s = s.replace(f"\\{fn}", fn)
    s = re.sub(r"\\left[(\[{|]?", "(", s)
    s = re.sub(r"\\right[)\]}|]?", ")", s)
    s = re.sub(r"\\[,;!]", " ", s)
    s = re.sub(r"\\(?:quad|qquad)", " ", s)
    s = re.sub(r"\\mathrm\{([^}]+)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+", "", s)
    s = s.replace("\\cdot", "*").replace("\\times", "*").replace("\\div", "/")
    s = s.replace("\\pi", "pi").replace("\\infty", "oo")
    s = re.sub(r"\^\{([^}]+)\}", r"**(\1)", s)
    s = re.sub(r"\^(\w)", r"**\1", s)
    s = re.sub(r"_\{[^}]+\}", "", s)
    s = re.sub(r"_\w", "", s)
    s = s.replace("{", "(").replace("}", ")")
    s = re.sub(r"\|([^|]+)\|", r"Abs(\1)", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def latex_to_expr(s):
    clean = _clean_expr(s)
    if not clean or clean in ("", "="):
        return None
    try:
        return parse_expr(clean, local_dict=_LOCAL, transformations=TRANSFORMATIONS)
    except Exception:
        return None


def _make(problem, steps, answer, answer_latex=None, solver="advanced_sympy"):
    return {
        "problem_id": problem["id"],
        "problem_text": problem["text"],
        "solved": True,
        "steps": steps,
        "answer": str(answer),
        "answer_latex": answer_latex if answer_latex is not None else latex(answer),
        "solver": solver,
        "sub_solutions": [],
    }


def _find_expr(exprs, contains=None, exclude=None):
    for e in exprs:
        s = e.get("latex", "")
        if contains and all(kw not in s for kw in contains):
            continue
        if exclude and any(kw in s for kw in exclude):
            continue
        ex = latex_to_expr(s)
        if ex is not None:
            return ex
    return None


# ---------- 多元函数微分学 ----------

def solve_partial_derivative(problem, exprs):
    expr = None
    for e in exprs:
        s = e.get("latex", "")
        if ("f(" in s or "f\\left" in s) or ("^" in s and "," not in s):
            ex = latex_to_expr(s)
            if ex is not None and ex.free_symbols & {x, y}:
                expr = ex
                break
    if expr is None:
        expr = _find_expr(exprs)
    if expr is None:
        return None
    fx, fy = diff(expr, x), diff(expr, y)
    steps = [
        f"对 $x$ 求偏导（$y$ 视为常数）：$f_x=\\frac{{\\partial f}}{{\\partial x}}={latex(fx)}$",
        f"对 $y$ 求偏导（$x$ 视为常数）：$f_y=\\frac{{\\partial f}}{{\\partial y}}={latex(fy)}$",
    ]
    return _make(problem, steps, (fx, fy), f"f_x={latex(fx)},\\; f_y={latex(fy)}")


def solve_total_differential(problem, exprs):
    expr = _find_expr(exprs)
    if expr is None:
        return None
    dz = diff(expr, x) * dx + diff(expr, y) * dy
    point = None
    for e in exprs:
        s = e.get("latex", "")
        m = re.search(r"\((-?\d+)\s*,\s*(-?\d+)\)", s)
        if m:
            point = (int(m.group(1)), int(m.group(2)))
            break
    fx_l, fy_l = latex(diff(expr, x)), latex(diff(expr, y))
    answer_latex = f"dz = {fx_l}\\,dx + {fy_l}\\,dy"
    steps = [f"全微分：$dz = f_x\\,dx + f_y\\,dy = {fx_l}\\,dx + {fy_l}\\,dy$"]
    if point:
        val = dz.subs({x: point[0], y: point[1]})
        answer_latex = f"dz({point}) = {latex(val)}"
        steps.append(f"在点 ${point}$ 处：${answer_latex}$")
    return _make(problem, steps, answer_latex, answer_latex)


def solve_lagrange(problem, exprs):
    f_expr = None
    g_expr = None
    for e in exprs:
        s = e.get("latex", "")
        if "=" in s and g_expr is None and "f" not in s[:3]:
            g_latex = s.split("=")[0]
            const = s.split("=")[1].strip() if len(s.split("=")) > 1 else ""
            g_expr = latex_to_expr(g_latex)
            if g_expr is not None and const and const not in ("0", ""):
                c = latex_to_expr(const)
                if c is not None:
                    g_expr = g_expr - c
        elif "^" in s and "," in s and f_expr is None:
            f_expr = latex_to_expr(s)
    if f_expr is None:
        f_expr = _find_expr(exprs)
    if f_expr is None or g_expr is None:
        return None
    fx, fy = diff(f_expr, x), diff(f_expr, y)
    gx, gy = diff(g_expr, x), diff(g_expr, y)
    try:
        sols = solve([fx - lam * gx, fy - lam * gy, g_expr], [x, y, lam], dict=True)
    except Exception:
        return None
    if not sols:
        return None
    steps = [f"构造拉格朗日函数 $L=f-\\lambda g$，其中 $f={latex(f_expr)}$，约束 $g={latex(g_expr)}=0$"]
    val_latex = []
    for s in sols:
        pt_x, pt_y = s.get(x), s.get(y)
        fv = f_expr.subs({x: pt_x, y: pt_y})
        val_latex.append(f"({latex(pt_x)},{latex(pt_y)}) 处 f={latex(fv)}")
        steps.append(f"解梯度方程组得驻点 $({latex(pt_x)},{latex(pt_y)})$，$f={latex(fv)}$")
    return _make(problem, steps, "; ".join(val_latex), "; ".join(val_latex))


# ---------- 重积分 ----------

def solve_double_integral(problem, exprs):
    integrand = None
    bounds = None
    for e in exprs:
        s = e.get("latex", "")
        if "iint" in s:
            m = re.search(r"\\iint_?[A-Za-z]?\s*(.+?)(?:\\,?d[A-Z]|$)", s)
            if m:
                integrand = latex_to_expr(m.group(1))
        m2 = re.search(r"\[(-?\d+),(-?\d+)\]\\times\[(-?\d+),(-?\d+)\]", s)
        if m2:
            bounds = [int(v) for v in m2.groups()]
    if integrand is None:
        integrand = _find_expr(exprs)
    if integrand is None:
        return None
    if bounds:
        x0, x1, y0, y1 = bounds
        val = integrate(integrate(integrand, (y, y0, y1)), (x, x0, x1))
        steps = [
            f"直角坐标化：$\\iint_D {latex(integrand)}\\,dA=\\int_{{{x0}}}^{{{x1}}}\\int_{{{y0}}}^{{{y1}}}{latex(integrand)}\\,dy\\,dx$",
            f"逐层积分得 $={latex(val)}$",
        ]
        return _make(problem, steps, val)
    txt = problem["text"]
    if "三角形" in txt or ("x+y" in txt):
        inner = simplify(integrate(integrand, (y, 0, 1 - x)))
        val = integrate(inner, (x, 0, 1))
        steps = [
            f"区域 $D=\\{{(x,y):0\\le x\\le 1,\\;0\\le y\\le 1-x\\}}$",
            f"积分化为 $\\int_0^1\\int_0^{{1-x}}{latex(integrand)}\\,dy\\,dx$",
            f"先对 $y$ 积分：$\\int_0^1 {latex(inner)}\\,dx$",
            f"对 $x$ 积分得 $={latex(simplify(val))}$",
        ]
        return _make(problem, steps, simplify(val))
    return None


def solve_triple_integral(problem, exprs):
    integrand = None
    bounds = None
    for e in exprs:
        s = e.get("latex", "")
        if "iiint" in s:
            m = re.search(r"\\iiint_?[A-Za-z]?\s*(.+?)(?:\\,?d[A-Z]|$)", s)
            if m:
                integrand = latex_to_expr(m.group(1))
        m2 = re.search(r"\[(-?\d+),(-?\d+)\]\\times\[(-?\d+),(-?\d+)\]\\times\[(-?\d+),(-?\d+)\]", s)
        if m2:
            bounds = [int(v) for v in m2.groups()]
    if integrand is None:
        integrand = _find_expr(exprs)
    if integrand is None:
        return None
    if bounds:
        x0, x1, y0, y1, z0, z1 = bounds
        val = integrate(integrate(integrate(integrand, (z, z0, z1)), (y, y0, y1)), (x, x0, x1))
        steps = [
            f"化为三次积分：$\\iiint_E {latex(integrand)}\\,dV=\\int_{{{x0}}}^{{{x1}}}\\int_{{{y0}}}^{{{y1}}}\\int_{{{z0}}}^{{{z1}}}{latex(integrand)}\\,dz\\,dy\\,dx$",
            f"逐层积分得 $={latex(val)}$",
        ]
        return _make(problem, steps, val)
    return None


# ---------- 无穷级数 ----------

def _extract_series_term(exprs):
    for e in exprs:
        s = e.get("latex", "")
        if "\\sum" in s:
            m = re.search(r"\\sum_[^{}]*\{[^{}]*\}[^{}]*\{[^{}]*\}\s*(.+)", s)
            body = m.group(1).strip() if m else s.replace("\\sum", "").strip()
            ex = latex_to_expr(body)
            if ex is not None and n in ex.free_symbols:
                return ex
    return None


def solve_ratio_test(problem, exprs):
    a_n = _extract_series_term(exprs)
    if a_n is None:
        return None
    try:
        ratio = simplify((a_n.subs(n, n + 1)) / a_n)
        rho = limit(ratio, n, oo)
    except Exception:
        return None
    if rho is None or not rho.is_number:
        return None
    verdict = "收敛" if rho < 1 else ("发散" if rho > 1 else "需进一步判断")
    steps = [
        f"设一般项 $a_n={latex(a_n)}$",
        f"比值判别法：$\\rho=\\lim_{{n\\to\\infty}}\\frac{{a_{{n+1}}}}{{a_n}}=\\lim_{{n\\to\\infty}}{latex(simplify(a_n.subs(n,n+1)/a_n))}={latex(rho)}$",
        f"因 $\\rho{'<' if rho<1 else '>'}1$，由比值判别法级数\\textbf{{{verdict}}}。",
    ]
    return _make(problem, steps, verdict, verdict)


def solve_p_series(problem, exprs):
    a_n = _extract_series_term(exprs)
    if a_n is None:
        return None
    p_val = None
    try:
        if a_n.is_Pow and a_n.base == n and a_n.exp.is_number:
            e = a_n.exp
            p_val = -e if e < 0 else e  # 1/n^p = n^{-p}，p = -exp
        elif a_n == 1 / n:
            p_val = 1
        elif a_n == n ** Rational(-1, 2):
            p_val = Rational(1, 2)
    except Exception:
        pass
    if p_val is None:
        return None
    verdict = "收敛" if p_val > 1 else "发散"
    steps = [
        f"该级数为 $p$-级数 $\\sum\\frac{{1}}{{n^{{{p_val}}}}}$",
        f"由 $p$-级数判别法：$p={p_val}{'>' if p_val>1 else '\\le'}1$，故级数\\textbf{{{verdict}}}。",
    ]
    return _make(problem, steps, verdict, verdict)


def solve_power_series(problem, exprs):
    a_n = _extract_series_term(exprs)
    if a_n is None or x not in a_n.free_symbols:
        return None
    a_coef = None
    try:
        if a_n == x ** n:
            a_coef = 1
        elif a_n.is_Mul:
            a_coef = 1
            for f_ in a_n.args:
                if x not in f_.free_symbols:
                    a_coef = a_coef * f_
        else:
            a_coef = a_n / (x ** n)
        if a_coef is None:
            return None
        ratio = simplify(a_coef.subs(n, n + 1) / a_coef)
        rho = limit(abs(ratio), n, oo)
        R = 1 / rho if rho.is_number and rho != 0 else (oo if rho == 0 else None)
    except Exception:
        return None
    if R is None:
        return None
    steps = [
        f"幂级数一般项系数 $a_n={latex(a_coef)}$",
        f"收敛半径：$R=\\lim_{{n\\to\\infty}}\\left|\\frac{{a_n}}{{a_{{n+1}}}}\\right|={latex(R)}$",
        f"故收敛半径 $R={latex(R)}$，收敛区间 $(-{latex(R)},{latex(R)})$（端点需单独检验）。",
    ]
    return _make(problem, steps, f"R={latex(R)}", f"R={latex(R)}")


def solve_taylor(problem, exprs):
    expr = None
    for e in exprs:
        s = e.get("latex", "")
        if ("f(" in s or "e^" in s) and "=" in s:
            expr = latex_to_expr(s)
    if expr is None:
        expr = _find_expr(exprs)
    if expr is None:
        return None
    point = 0
    for e in exprs:
        m = re.search(r"x=(-?\d+)", e.get("latex", ""))
        if m:
            point = int(m.group(1))
            break
    try:
        ser = series(expr, x, point, 4).removeO()
    except Exception:
        return None
    steps = [
        f"在 $x={point}$ 处作展开，截取到 $o(x^{{3}})$：",
        f"${latex(ser)}+\\cdots$",
    ]
    return _make(problem, steps, latex(ser), latex(ser))


def solve_proof(problem):
    res = solve_with_llm(problem["text"], "证明题")
    if not res:
        return None
    return {
        "problem_id": problem["id"],
        "problem_text": problem["text"],
        "solved": True,
        "steps": res["steps"],
        "answer": res["answer"],
        "answer_latex": res["answer_latex"],
        "solver": "deepseek",
        "sub_solutions": [],
    }


# ---------- 主入口 ----------

def solve_advanced(problem):
    text = problem["text"].lower()
    exprs = problem.get("math_expressions", [])

    try:
        if any(kw in text for kw in ["证明", "prove", "证明题"]):
            return solve_proof(problem)

        if any(kw in text for kw in ["拉格朗日", "约束条件", "条件极值", "条件下的极值"]):
            r = solve_lagrange(problem, exprs)
            if r:
                return r

        if any(kw in text for kw in ["全微分"]):
            r = solve_total_differential(problem, exprs)
            if r:
                return r

        if any(kw in text for kw in ["偏导数", "偏导", "\\partial", "partial", "多元函数"]):
            r = solve_partial_derivative(problem, exprs)
            if r:
                return r

        if any(kw in text for kw in ["三重积分", "iiint"]):
            r = solve_triple_integral(problem, exprs)
            if r:
                return r
        if any(kw in text for kw in ["二重积分", "iint", "重积分"]):
            r = solve_double_integral(problem, exprs)
            if r:
                return r

        if any(kw in text for kw in ["幂级数", "收敛半径", "收敛区间"]):
            r = solve_power_series(problem, exprs)
            if r:
                return r
        if any(kw in text for kw in ["比值判别", "达朗贝尔", "d'alembert"]):
            r = solve_ratio_test(problem, exprs)
            if r:
                return r
        if any(kw in text for kw in ["级数", "收敛", "收敛性"]):
            r = solve_p_series(problem, exprs)
            if r:
                return r
            r = solve_ratio_test(problem, exprs)
            if r:
                return r

        if any(kw in text for kw in ["泰勒", "麦克劳林", "展开式"]):
            r = solve_taylor(problem, exprs)
            if r:
                return r

    except Exception:
        return None

    return None


if __name__ == "__main__":
    import json, sys
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        problems = json.load(f)
    for p in problems:
        sol = solve_advanced(p)
        tag = (sol["solver"] + " ✅") if sol and sol["solved"] else "未处理"
        print(f"{p['id']}: {tag} | {p['text'][:40]}")
