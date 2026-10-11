# 🧠 algo-solver — 算法题解生成器（Algorithm Problem → Verified Solution）

> **C4 技能分享与传播 ｜ 提交人：阮依涵**
>
> 输入一道算法题，输出**已本地评测过、全过才给你**的 ACM 模式代码 + 讲解 + 评测凭证。

---

## 📌 一句话

**输入** 一道算法题（文字/截图/粘贴题面） → **输出** `solution.cpp/.py`（可直接提交）+ `problem.md`（算法与复杂度）+ `verdict_report.txt`（自动评测的 PASS/FAIL 凭证）。

> 不再"写完就盲交、WA 了再改"——它在把代码交给你之前，已经用随附的 `judge.py` 帮你测过了。

---

## ✨ 为什么值得用

| 收益 | 说明 |
|------|------|
| 🕐 省时间 | 写完先在本地跑评测，全过再提交，减少 OJ 上 WA/TLE/RE 的挫败 |
| 🛡️ 避免 WA | 输出格式、边界、int 溢出这些最常见的坑，评测器替你盯住 |
| 🎓 学得会 | 每个答案都带"为什么是这个算法 + 复杂度"，不只是给代码 |
| 🐍 零门槛 | 不需要 g++，用 Python 题解即可跑通全部流程 |

---

## 🗂 仓库结构

```
C4_algo-solver/
├── README.md                      ← 本文件
├── algo-solver/                   ← 技能源码（可直接安装/阅读）
│   ├── SKILL.md                   ← 主指令（触发描述 + 5 步工作流 + 边界情况）
│   ├── scripts/judge.py           ← 评测器：编译/运行/比对输出
│   ├── references/                ← 复杂度速查表 + 算法模板
│   └── assets/sample-problem.md   ← 示例题目（两数之和）
├── 阮依涵_C4_algo-solver.skill    ← 打包好的可安装技能包 (tar.gz)
├── 阮依涵_C4_skill说明.md          ← 技能说明（问题/场景/IO/步骤/真实案例）
├── 阮依涵_C4_教学说明.md           ← 教学说明（上手/常见坑/优化技巧）
├── 阮依涵_C4_AI日志.md             ← AI 使用日志 + 复盘（4 轮迭代）
├── 阮依涵_C4_demo.png             ← Demo 截图（真实运行输出）
├── demo_workspace/                ← 可直接复现的演示（题解 + 测试 + 评测报告）
├── demo_range_sum/                ← 真题演示①：区间和查询（前缀和）
└── demo_pat1009/                  ← 真题演示②：PAT 乙级 1009 说反话
```

---

## 🚀 快速开始（2 分钟）

### 方式 A：安装 .skill 包（推荐给会用 Claude/豆包技能的人）
1. 下载 `阮依涵_C4_algo-solver.skill`。
2. 解压得到 `algo-solver/` 目录，放入技能目录。
3. 对它说："解这道题：<题目文字>"。

### 方式 B：直接用脚本（不装技能也能验证）
```bash
cd demo_workspace
python ../algo-solver/scripts/judge.py solution.py --tests ./tests
# 期望输出：Summary: 4/4 PASS
```

### 自己造测试
在 `tests/` 里放 `N.in` / `N.out` 配对（官方样例 + 自造边界），然后：
```bash
python algo-solver/scripts/judge.py solution.cpp --tests ./tests   # C++
python algo-solver/scripts/judge.py solution.py  --tests ./tests   # Python
```

---

## 🧪 真实运行证据（本仓库可复现）

`demo_workspace/` 内已含完整测试集与结果：

**正确题解 `solution.py`**（4 组测试：样例 / 负数 / 大整数边界 / 非相邻答案）
```
Test 1: PASS   Test 2: PASS   Test 3: PASS   Test 4: PASS
Summary: 4/4 PASS
```

**故意写错的 `buggy.py`**（只检查相邻两数）—— 同一测试集被自动抓出：
```
Test 4: FAIL (output mismatch)
Summary: 3/4 PASS
```

> 说明：第 4 组"非相邻答案"用例专门用于暴露此类逻辑 bug，证明评测器不是摆设。

---

## ✅ 真实真题验证（更新于 2026-10-10）

技能不只对示例题有效——**对网上找的真实 OJ 真题同样当场跑通**：

### 演示②：PAT 乙级 1009「说反话」（浙江大学 PTA 真题）
- 输入：`Hello World Here I Come`
- 输出：`Come I Here World Hello`
- 评测：**3/3 PASS，可直接提交** ✅（含官方样例 / 单单词 / 多单词边界）
- 复现：`demo_pat1009/`

### 演示①：区间和查询（前缀和，`n,m ≤ 10^5`）
- 用前缀和 `O(n+m)` 取代暴力 `O(n·m)`，评测 **3/3 PASS** ✅
- 复现：`demo_range_sum/`

> 每次都是"写代码 → judge.py 自动评测 → 全过才交付"，不是直接甩答案。

---

## 📋 技能四条件

| 条件 | 满足方式 |
|------|----------|
| ✅ 可复用 | 不依赖个人环境；Python 3 即可跑通；任意题目可用 |
| ✅ 可执行 | `judge.py` 真实编译、运行、比对输出 |
| ✅ 可验证 | 给定测试输入 → 稳定输出 PASS/FAIL 判定 |
| ✅ IO 明确 | 输入题目 → 输出代码 + 讲解 + 评测凭证 |

---

## 🔭 Roadmap（v2 计划）

- 支持 Java / Go 评测
- HTML 高亮评测报告
- 扩充 DP / 图论 / 字符串模板
- 内置冒烟自检（`--tl 1` 跑示例题）

## 💬 反馈

用一次，告诉我哪里难用 —— 你的反馈会直接进入 v2 迭代。**被用得越多，它就越好用。**
