#!/usr/bin/env python3
"""
judge.py — Algo-Solver test runner / verifier.

Given a solution file (.cpp / .py) and a directory of test cases (N.in / N.out pairs),
compile & run the solution against each input, compare its stdout with the expected
output, and print a PASS/FAIL verdict per case plus a summary.

Usage:
    python3 judge.py solution.cpp --tests ./tests
    python3 judge.py solution.py  --tests ./tests --tl 3

Test directory layout (all files in one folder):
    tests/1.in   tests/1.out
    tests/2.in   tests/2.out
    tests/3.in   tests/3.out
    ...

Exit code:
    0  -> all tests PASS
    1  -> at least one FAIL, or a runtime/compile/usage error

Output comparison is whitespace-tolerant on trailing newlines (online-judge convention):
program output and expected output are compared line by line after stripping
trailing whitespace from each line and dropping trailing blank lines.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_TIME_LIMIT = 2.0  # seconds per test case


def find_compiler():
    """Locate a usable C++ compiler. Prefer g++ on PATH, else try common names."""
    for name in ("g++", "gcc", "clang++", "clang", "c++", "CC"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _skip_windowsapps(path):
    """Windows Store 'alias' stubs (WindowsApps\\*.exe) are 0-byte placeholders that
    fail with exit code 9009 when executed. Treat them as absent."""
    if not path:
        return True
    p = Path(path).resolve()
    return "WindowsApps" in str(p).replace("/", "\\")


def find_python():
    """Return a working Python interpreter: prefer the one running this script
    (guaranteed real), then a real 'python'/'python3' on PATH (skipping WindowsApps
    stubs). Returns None if none found."""
    if sys.executable and not _skip_windowsapps(sys.executable):
        return sys.executable
    for name in ("python", "python3"):
        p = shutil.which(name)
        if p and not _skip_windowsapps(p):
            return p
    return None


def has_python():
    """Whether a Python interpreter is available."""
    return find_python() is not None


def discover_tests(test_dir: Path):
    """Return a sorted list of (case_number, input_path, output_path) tuples."""
    if not test_dir.is_dir():
        return []
    in_files = sorted(test_dir.glob("*.in"))
    tests = []
    for in_file in in_files:
        out_file = in_file.with_suffix(".out")
        if out_file.exists():
            m = re.search(r"(\d+)", in_file.stem)
            num = int(m.group(1)) if m else len(tests)
            tests.append((num, in_file, out_file))
    # stable sort by numeric part when present
    tests.sort(key=lambda t: t[0])
    return tests


def norm_output(text: str) -> str:
    """Normalize for comparison: strip trailing whitespace per line, drop trailing blank lines."""
    lines = text.splitlines()
    stripped = [ln.rstrip() for ln in lines]
    while stripped and stripped[-1] == "":
        stripped.pop()
    return stripped


def run_case(cmd, stdin_data: str, tl: float):
    """Run a command with given stdin; return (returncode, stdout, stderr, timed_out)."""
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=tl,
        )
        return proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return -1, out, err, True


def build_command(solution: Path, workdir: Path, lang: str):
    """Build the command list that runs the solution for one test case."""
    if lang == "cpp":
        exe = workdir / (solution.stem + ".exe")
        return [str(exe)]
    elif lang == "py":
        interpreter = find_python()
        return [interpreter, str(solution)]
    else:
        raise ValueError(f"Unsupported language: {lang}")


def detect_language(solution: Path):
    if solution.suffix.lower() in (".cpp", ".cc", ".cxx", ".c"):
        return "cpp"
    if solution.suffix.lower() == ".py":
        return "py"
    return None


def main():
    ap = argparse.ArgumentParser(description="Algo-Solver test runner / verifier")
    ap.add_argument("solution", help="path to solution file (.cpp or .py)")
    ap.add_argument("--tests", default="./tests", help="directory containing N.in / N.out pairs")
    ap.add_argument("--tl", type=float, default=DEFAULT_TIME_LIMIT,
                    help=f"per-test time limit in seconds (default {DEFAULT_TIME_LIMIT})")
    ap.add_argument("--compiler", default=None, help="explicit C++ compiler path (optional)")
    args = ap.parse_args()

    solution = Path(args.solution).expanduser().resolve()
    if not solution.is_file():
        print(f"[ERROR] Solution file not found: {solution}")
        sys.exit(1)

    lang = detect_language(solution)
    if lang is None:
        print(f"[ERROR] Unsupported file type: {solution.suffix}. Use .cpp or .py")
        sys.exit(1)

    test_dir = Path(args.tests).expanduser().resolve()
    tests = discover_tests(test_dir)
    if not tests:
        print(f"[ERROR] No 'N.in'/'N.out' pairs found in {test_dir}")
        sys.exit(1)

    # ---- Prepare run command ----
    run_cmd = None
    tmp = None
    if lang == "cpp":
        compiler = args.compiler or find_compiler()
        if compiler is None:
            print("[ERROR] No C++ compiler found on PATH (tried g++, clang++, c++, ...).")
            print("        Install g++ or use a .py solution instead.")
            sys.exit(1)
        tmp = Path(tempfile.mkdtemp(prefix="algosolver_"))
        exe = tmp / (solution.stem + ".exe")
        comp = subprocess.run([compiler, str(solution), "-O2", "-o", str(exe), "-std=c++17"],
                              capture_output=True, text=True)
        if comp.returncode != 0:
            print("[COMPILE FAILED]")
            print(comp.stderr)
            sys.exit(1)
        run_cmd = [str(exe)]
    elif lang == "py":
        interpreter = find_python()
        if interpreter is None:
            print("[ERROR] No working Python interpreter found.")
            sys.exit(1)
        run_cmd = [interpreter, str(solution)]

    # ---- Run all test cases ----
    total = len(tests)
    passed = 0
    print(f"Running {total} test case(s) with time limit {args.tl}s ...\n")
    failures = []

    for num, in_file, out_file in tests:
        stdin_data = in_file.read_text(encoding="utf-8", errors="replace")
        expected = norm_output(out_file.read_text(encoding="utf-8", errors="replace"))
        rc, stdout, stderr, timed_out = run_case(run_cmd, stdin_data, args.tl)

        if timed_out:
            print(f"  Test {num}: FAIL (time limit {args.tl}s exceeded)")
            failures.append((num, "timeout"))
            continue
        if rc != 0:
            print(f"  Test {num}: FAIL (runtime error, exit code {rc})")
            if stderr:
                print("       stderr:", stderr.strip().splitlines()[-1][:200])
            failures.append((num, f"runtime error {rc}"))
            continue

        got = norm_output(stdout)
        if got == expected:
            print(f"  Test {num}: PASS")
            passed += 1
        else:
            print(f"  Test {num}: FAIL (output mismatch)")
            failures.append((num, "wrong answer"))
            # show a short diff hint
            for i in range(max(len(got), len(expected))):
                a = got[i] if i < len(got) else "<missing>"
                b = expected[i] if i < len(expected) else "<missing>"
                if a != b:
                    print(f"       line {i+1}: got {a[:80]!r}  expected {b[:80]!r}")
                    break

    # ---- Summary ----
    print(f"\nSummary: {passed}/{total} PASS")
    if failures:
        print("Failed:", ", ".join(f"#{n}({why})" for n, why in failures))
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
        sys.exit(1)
    else:
        print("All tests passed. The solution is ready to submit.")
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
