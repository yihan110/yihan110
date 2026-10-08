---
name: algo-solver
description: >
  Take any algorithm/competitive-programming problem (problem text, image, or copied statement)
  and produce a complete, runnable ACM-mode solution: problem restatement, algorithm design with
  complexity analysis, ready-to-submit C++ or Python code, and an automated verification pass that
  compiles and runs the solution against sample and custom test cases via scripts/judge.py.
  Use whenever the user says "solve this problem", "解这道题", "帮我写这道题的代码", "ACM题解",
  "algorithm solution", "写个acm模式代码", "帮我AC", or provides a problem statement, LeetCode/PAT/
  牛客/力扣 problem, or an algorithm question and wants code plus a correctness check.
  Also trigger when the user wants a full workflow: problem analysis → code → test-case verification.
  Works for any difficulty; especially useful when the user must submit to an online judge and wants
  code that is verified before submission. Does NOT require a working C++ compiler to produce the
  answer, but verification (Step 4) needs g++ and Python 3 available.
---

# Algo-Solver — Algorithm Problem → Verified Solution

## Purpose

Every computer-science student repeatedly does the same loop: read a problem → figure out the
algorithm → write ACM-mode code → submit to an online judge (PAT / 牛客 / LeetCode / 力扣 / Codeforces)
→ find out whether it passes. Most of the time is wasted on the last two steps: subtle bugs, wrong
output format, integer overflow, missing edge cases.

This skill turns that loop into a repeatable, verifiable workflow. Given **one algorithm problem**,
it returns **a solution you can trust**: explained, complexity-analyzed, and automatically tested
against the official samples plus your own edge cases **before you submit**. Think of it as a
personal coach that not only solves the problem but proves the solution works.

**Input** → a problem statement (text / pasted statement / image of a problem / screenshot)
**Output** → `problem.md` + `solution.cpp` (or `.py`) + `verdict_report.txt` (pass/fail per test)

## Prerequisites

### Runtime (only needed for the verification step)
- Python 3 (any recent version)
- A C++ compiler `g++` (for C++ solutions). Check: `g++ --version`.
  If `g++` is missing, fall back to Python solutions, or output code without running verification
  and clearly note "未验证（无编译器）".

### Nothing else is required
The skill works for any problem. The user does NOT need an account on any online judge.

## Workflow

### Step 1 — Capture and restate the problem

1. Get the problem from the user. Accept any of these inputs:
   - Pasted problem text (best).
   - An image/screenshot of the problem (read it; if a picture, describe what you see then proceed).
   - A link to a problem (only if you can read it; otherwise ask the user to paste the statement).
2. Restate the problem **in your own words** in `problem.md`, capturing the four essentials:
   - **Task** — what the program must compute.
   - **Input format** — first line(s) meaning, constraints of each variable, delimiters, EOF handling.
   - **Output format** — exact formatting (spacing, decimals, trailing newline) — this is the #1 cause
     of Wrong Answer on real judges.
   - **Constraints** — `n ≤ 10^5` vs `n ≤ 20` completely changes the intended algorithm.
3. Write the explicit bounds at the top: e.g. `1 ≤ n ≤ 2×10^5`. If the user did not state them, ask.

### Step 2 — Design the algorithm

Before writing any code, choose the approach and **justify it with the constraints**:

| Constraint magnitude | Typical viable complexity | Example algorithms |
|----------------------|---------------------------|--------------------|
| `n ≤ 20` | `O(2^n)`, `O(n!)` | brute force, bitmask DP, backtracking |
| `n ≤ 10^3` | `O(n^2)` | nested loops, simple DP, Floyd-Warshall |
| `n ≤ 10^5` | `O(n log n)` | sort, binary search, two pointers, heap, DSU, segment tree |
| `n ≤ 10^6` | `O(n)` | prefix sum, sliding window, hashing, linear sieve |
| `n ≤ 10^9` | `O(log n)` / math | fast exponentiation, matrix fast power, number theory |

- Pick the algorithm, state time and space complexity in Big-O, and note **why** an obvious simpler
  approach would TLE (time-limit-exceeded) — this is the reasoning the user will learn from.
- Check the reference `references/complexity-cheatsheet.md` and `references/algo-templates.md`
  for ready-made patterns (fast IO, prefix sums, binary search, two pointers, etc.).

### Step 3 — Generate the solution code

Write ACM-mode (plain stdin/stdout) code. Follow these hard rules:

1. **C++ default; Python if the user asks or if big-integer/memory convenience is needed.**
2. **Fast IO** for C++ (`ios::sync_with_stdio(false); cin.tie(nullptr);`) — always add it.
3. **Use 64-bit types** (`long long`) whenever any sum/product can exceed `2^31-1`.
4. **Exact output formatting** — match the spec byte-for-byte (spaces, newline, `fixed`/`setprecision`
   for decimals). Use `cout << fixed << setprecision(k)` for floats.
5. **Handle multiple test cases** if the spec says `T` or "input until EOF".
6. Keep the code clean: no debug prints, no extra prompts. A single `main()` / top-level flow.
7. Save as `solution.cpp` or `solution.py` **in the current working directory**.

### Step 4 — Verify automatically with judge.py

This is what makes the skill trustworthy. Run the bundled verifier:

```bash
python3 scripts/judge.py solution.cpp --tests ./tests   # C++
python3 scripts/judge.py solution.py  --tests ./tests   # Python
```

`judge.py` expects a test directory containing pairs of files named like `1.in` / `1.out`,
`2.in` / `2.out`, … It will:

1. Compile the C++ solution (or pick the Python interpreter).
2. Run the solution against every `.in` file with a time limit (default 2s per case).
3. Compare the program's stdout against the matching `.out` file (whitespace-insensitive on
   trailing newlines, per OJ convention).
4. Print a `PASS` / `FAIL` verdict per case plus a summary.

Seed `./tests` with the **official sample cases** first, then add at least 2–3 of your own
**edge cases**: minimum values (`n=1`), maximum values, boundary of the constraint, empty input
(if legal), and any tricky format case. If any case fails, debug, fix `solution.cpp`, and re-run
until all PASS. Write the final output to `verdict_report.txt`:

```
Test 1: PASS
Test 2: PASS
Test 3: PASS
Edge n=1: PASS
Summary: 5/5 PASS
```

### Step 5 — Deliver the result

Present to the user:
- `problem.md` — restatement + constraints + chosen algorithm + complexity.
- `solution.cpp` / `solution.py` — the verified, submission-ready code.
- `verdict_report.txt` — the verification evidence.
- A short plain-language explanation of *how* the algorithm works and *why* it is correct
  (loop invariant / induction argument, 2–4 sentences).

## Edge Cases

- **Problem statement is an image only** — read the image and transcribe the statement; if any
  constraint is unreadable, ask the user rather than guessing.
- **Missing constraints** — the algorithm choice depends on them. Ask. Never silently pick a
  brute-force when the intended solution is logarithmic.
- **No compiler available** — output the code and note "未验证（无 g++）"; still provide the
  algorithm and complexity. Do not fake a PASS.
- **Judge.py cannot find tests** — create `./tests`, put the official samples in it, re-run.
- **Time-limit fail in judge** — your algorithm is too slow for the constraint; go back to Step 2
  and pick a faster approach (e.g., replace `O(n^2)` with `O(n log n)`).
- **Whitespace-only difference** — judge.py ignores trailing whitespace by design (OJ behavior).
  If the judge is stricter, note it and trim output exactly.
- **Huge inputs (`n=10^6`+)** — the program must use fast IO and avoid O(n) memory copies;
  remind the user in the explanation.
- **Multiple valid outputs** (e.g., "any valid permutation") — judge.py compares to expected;
  use the official sample as the reference for verification, and note that other valid outputs exist.

## Examples

### Example 1 — Two Sum → verified
> User: "给定数组和目标值，找两个数的下标使和等于目标。n≤10^5"

The skill restates constraints, chooses a hash map (`O(n)`), writes `solution.cpp` with fast IO,
seeds `tests/` with `3.in/3.out` etc., runs judge.py → all PASS, returns the code + verdict.

### Example 2 — PAT 打印沙漏 / 牛客 prefix-sum problem
> User pastes a full PAT statement with sample I/O.

The skill parses the input format exactly (note the trailing newline and exact spacing), writes the
code, verifies against the provided sample, and returns submission-ready code.

### Example 3 — Python big-integer
> User: "算 2^1000，用 Python。"

The skill writes a Python solution, verifies with judge.py, returns code.

## Extensibility

- **More languages**: extend `scripts/judge.py` with a new compiler block (e.g. Java) — the
  run/compare logic is language-agnostic.
- **New test formats**: judge.py supports any naming via glob; point it at a new test directory.
- **Templates**: add more patterns to `references/algo-templates.md`; the workflow automatically
  benefits without code changes.

## Quick Reference

- Verify: `python3 scripts/judge.py <solution> --tests <dir>`
- Time limit flag: `--tl 3` (seconds, default 2)
- List test files: the script prints the matched `.in` count.
