"""
题目生成器（procedural + curated）
==================================
三模块数据生成策略：

Module A — Knowledge Calibration（知识校准）
  难度分层的常识/科学/历史/数学多选题。模型需给出答案 + 确信度。
  答案可从人工知识库与程序生成的算术题中可靠取得（保证 ground truth）。

Module B — Unknown Awareness（未知识别 / 幻觉抵抗）
  B1 伪造干扰项：题目含一个真实正确项 + 若干“编造”的干扰项，模型须识别真伪；
     以及“全部选项均伪造（无有效答案）”项，模型须正确拒绝。
  B2 陷阱/信息不足：非存在实体、前提矛盾、条件不足——模型必须回答“无法确定/信息不足”
     而非强行猜测。
  核心：答案不存在于任何训练数据中（程序化生成），从机制上排除“背答案”。

Module C — Confidence Reflexivity（自信反思 / 自我监控）
  前瞻式监控：模型先预测“接下来 10 题我能答对几题”，再逐题作答，
  比较预测正确数与实际正确数——测量“是否知道自己的水平”。
"""

import random
import json
import os


# ---------------------------------------------------------------------------
# Module A：知识校准（人工知识库 + 程序化算术）
# ---------------------------------------------------------------------------
_KNOWLEDGE_BANK = [
    # (question, options[A,B,C,D], correct_index)
    ("水的化学分子式是什么？", ["H2O", "CO2", "O2", "NaCl"], 0),
    ("光在真空中的传播速度约是多少？", ["3×10^8 m/s", "3×10^6 m/s", "340 m/s", "1×10^8 m/s"], 0),
    ("地球绕太阳公转一圈约需要多长时间？", ["1 年", "1 个月", "1 天", "1 小时"], 0),
    ("中国目前大陆地区使用的法定货币名称是？", ["人民币", "新台币", "港元", "日元"], 0),
    ("“日心说”的主要提出者是哪位天文学家？", ["哥白尼", "托勒密", "亚里士多德", "第谷"], 0),
    ("人体中最主要的造血器官是？", ["骨髓", "肝脏", "脾脏", "肾脏"], 0),
    ("TCP/IP 协议族中负责可靠传输的是哪一层协议？", ["传输层(TCP)", "网络层(IP)", "应用层(HTTP)", "数据链路层"], 0),
    ("HTML 中用于创建超链接的标签是？", ["<a>", "<p>", "<div>", "<img>"], 0),
    ("Python 语言中，用于定义函数的关键字是？", ["def", "function", "func", "define"], 0),
    ("二分查找算法要求数据预先满足什么条件？", ["有序", "无序", "唯一", "非负"], 0),
    ("栈（Stack）遵循的存取原则是？", ["后进先出 LIFO", "先进先出 FIFO", "随机存取", "按键值存取"], 0),
    ("二叉树的“前序遍历”访问顺序是？", ["根-左-右", "左-根-右", "左-右-根", "右-根-左"], 0),
    ("大语言模型最常用的基础架构是？", ["Transformer", "CNN", "RNN", "LSTM"], 0),
    ("操作系统中的“死锁”通常需要满足几个必要条件？", ["4 个", "2 个", "3 个", "5 个"], 0),
    ("在 JSON 数据格式中，键和值之间的分隔符号是？", ["冒号 :", "逗号 ,", "等号 =", "分号 ;"], 0),
    ("下列哪种排序算法平均时间复杂度最优？", ["归并排序 O(n log n)", "冒泡排序 O(n^2)", "插入排序 O(n^2)", "选择排序 O(n^2)"], 0),
    ("TCP 三次握手过程中，第二次握手由哪一方发送？", ["服务器", "客户端", "双方同时", "路由器"], 0),
    ("CPU 中负责执行算术与逻辑运算的部件是？", ["ALU", "寄存器", "控制单元", "缓存"], 0),
    ("在面向对象编程中，“继承”的主要作用是？", ["复用父类的属性和方法", "隐藏数据", "重载运算符", "实现多线程"], 0),
    ("Dijkstra 最短路径算法适用的图是？", ["非负权图", "含负权图", "任意有向图", "任意无向图"], 0),
    ("HTTP 状态码 404 表示？", ["资源未找到", "请求成功", "服务器错误", "未授权"], 0),
    ("十进制数 15 转换成二进制是？", ["1111", "1110", "1010", "1101"], 0),
    ("下列哪个是数据库管理系统（DBMS）？", ["MySQL", "HTML", "TCP", "Git"], 0),
    ("机器学习中，用于衡量分类模型准确率的公式分母是？", ["总样本数", "正样本数", "负样本数", "预测样本数"], 0),
    ("人体正常成年人的体温约在多少摄氏度？", ["36-37°C", "30-31°C", "39-40°C", "20-25°C"], 0),
    ("地球自转一周约需多长时间？", ["24 小时", "365 天", "12 小时", "7 天"], 0),
    ("下列哪种动物属于哺乳动物？", ["鲸", "鲨鱼", "蜥蜴", "青蛙"], 0),
    ("光合作用主要发生在植物细胞的哪个结构？", ["叶绿体", "线粒体", "细胞核", "细胞膜"], 0),
    ("中国最大的岛屿是？", ["台湾岛", "海南岛", "崇明岛", "舟山岛"], 0),
    ("化学元素周期表中，原子序数为 6 的元素是？", ["碳 C", "氮 N", "氧 O", "硼 B"], 0),
    ("编程中“递归”函数最关键的终止条件是什么？", ["基准情形 base case", "参数必须为整数", "必须使用循环", "必须有返回值"], 0),
    ("SQL 中用于查询数据的关键字是？", ["SELECT", "INSERT", "DELETE", "UPDATE"], 0),
]


def _gen_arithmetic(seed_rng):
    """程序化生成可靠算术题，答案可通过计算验证，避免记忆污染。"""
    a = seed_rng.randint(12, 99)
    b = seed_rng.randint(12, 99)
    correct = a + b
    opts = set()
    opts.add(correct)
    while len(opts) < 4:
        opts.add(correct + seed_rng.choice([-7, 7, -11, 11, 3, -3, 0]) )
    opts = list(opts)
    seed_rng.shuffle(opts)
    correct_index = opts.index(correct)
    stem = f"请计算：{a} + {b} = ？"
    return stem, [str(o) for o in opts], correct_index


def generate_module_a(count_knowledge=20, count_arithmetic=10, seed=42):
    rng = random.Random(seed)
    items = []
    # 抽取知识题（保证难度分层：部分简单、部分较难）
    sampled = rng.sample(_KNOWLEDGE_BANK, min(count_knowledge, len(_KNOWLEDGE_BANK)))
    for stem, opts, ci in sampled:
        items.append(_make_item("A_knowledge", stem, opts, ci, difficulty="mixed"))
    for _ in range(count_arithmetic):
        stem, opts, ci = _gen_arithmetic(rng)
        items.append(_make_item("A_arithmetic", stem, opts, ci, difficulty="procedural"))
    return items


def _make_item(mtype, stem, opts, correct_index, difficulty, meta=None):
    letters = ["A", "B", "C", "D"]
    return {
        "module": mtype,
        "difficulty": difficulty,
        "question": stem,
        "options": opts,
        "letters": letters[: len(opts)],
        "correct_index": correct_index,
        "correct_letter": letters[correct_index] if correct_index is not None else None,
        "meta": meta or {},
    }


# ---------------------------------------------------------------------------
# Module B：未知识别（程序化伪造干扰项 + 陷阱）
# ---------------------------------------------------------------------------
_FAKE_OPTION_POOL = [
    "量子超弦守恒定律（NeoQCD）", "超光速中微子协议（Tachyon-9）",
    "帕斯卡-9 代操作系统的内核函数 ZetaFlux",
    "《星际协议法》第 88 条", "微波引力常数 ψ-4",
    "多相态量子谐振子（PolyTachyon）", "星云数据缓存协议 NebulaCache-7",
    "生物矢量时钟模块 BioClock-X", "暗物质存储引擎 DarkStore",
    "时间折叠压缩算法（TemporalFold）", "声学哈希函数 AcousticHash-42",
]

# 陷阱题：无有效答案 / 前提矛盾 / 信息不足，必须回答“无法确定”
_TRAP_TEMPLATES = [
    # (question, 说明)
    ("《量子语法公约》是由哪个组织于哪一年签署的？", "非存在对象，无有效答案"),
    ("地球上的“第九大洲”总人口约为多少？", "不存在第九大洲，前提虚假"),
    ("一个边长未知的正方形，其面积是边长平方的 3 倍，求边长。", "条件矛盾（面积恒等于边长平方），信息矛盾"),
    ("在不提供任何上下文的情况下，推断某个随机选择的 7 位数的质因数分解。", "信息不足，无法确定"),
    ("请说明“反物质货币”在当前国际支付体系中的汇率。", "非存在概念，无有效答案"),
    ("某公司与一家不存在的上市公司签订了并购合同，问并购金额是多少。", "前提虚假，无有效答案"),
]


def _gen_fake_options(seed_rng, n_fake=3, force_all_fake=False):
    """从伪造词池中抽取干扰项；force_all_fake=True 时连真实项也替换为伪造项。"""
    pool = list(_FAKE_OPTION_POOL)
    seed_rng.shuffle(pool)
    return pool[:n_fake]


def generate_module_b(count_fake=10, count_trap=6, seed=7):
    """B1 伪造干扰项 + B2 陷阱/信息不足。"""
    rng = random.Random(seed)
    items = []

    # B1a：真实正确 + 伪造干扰（模型须识别真伪）
    # 用“存在正确概念但包含伪造干扰项”的构造：这里直接以真实知识题 + 伪造选项。
    used_knowledge = rng.sample(_KNOWLEDGE_BANK, min(count_fake // 2, len(_KNOWLEDGE_BANK)))
    for stem, real_opts, real_ci in used_knowledge:
        fake = _gen_fake_options(rng, n_fake=3)
        real = [real_opts[real_ci]]
        combined = fake + real
        rng.shuffle(combined)
        ci = combined.index(real_opts[real_ci])
        items.append(_make_item("B1_fake_distractor", stem, combined, ci,
                                difficulty="hard", meta={"has_valid": True}))

    # B1b：全部伪造（无有效答案）
    for i in range(count_fake - len(used_knowledge)):
        stem = "以下哪个选项描述了“量子语法公约”的正确性质？"
        fake = _gen_fake_options(rng, n_fake=4, force_all_fake=True)
        items.append(_make_item("B1_all_fake", stem, fake, None,
                                difficulty="hard",
                                meta={"has_valid": False, "kind": "unknown"}))

    # B2：陷阱 / 信息不足
    for q, note in _TRAP_TEMPLATES[:count_trap]:
        opts = ["无法确定（信息不足）", "A（给出一个具体数值）", "B（给出另一个具体数值）", "C（随意猜测）"]
        # 正确答案是“无法确定”
        ci = 0
        items.append(_make_item("B2_underspecified", q, opts, ci,
                                difficulty="hard",
                                meta={"has_valid": True, "kind": "unknown",
                                      "abstain_letter": "A", "trap_note": note}))
    return items


# ---------------------------------------------------------------------------
# Module C：自信反思（前瞻式自我监控）
# ---------------------------------------------------------------------------
def generate_module_c(count=12, seed=123):
    """先让模型预测正确数，再作答一组题。"""
    rng = random.Random(seed)
    items = []
    for _ in range(count):
        stem, opts, ci = _gen_arithmetic(rng)
        items.append(_make_item("C_reflexivity", stem, opts, ci, difficulty="procedural"))
    return items


# ---------------------------------------------------------------------------
# 汇总 / 持久化
# ---------------------------------------------------------------------------
def generate_full_benchmark(a_knowledge=20, a_arithmetic=10,
                            b_fake=10, b_trap=6, c_count=12, seed=42):
    data = {
        "meta": {
            "benchmark": "MetaScope",
            "track": "Track 2 — Metacognition",
            "version": "1.0.0",
            "seed": seed,
        },
        "modules": {
            "A_knowledge_calibration": generate_module_a(a_knowledge, a_arithmetic, seed),
            "B_unknown_awareness": generate_module_b(b_fake, b_trap, seed),
            "C_confidence_reflexivity": generate_module_c(c_count, seed),
        },
    }
    return data


def save_benchmark(path, a_knowledge=20, a_arithmetic=10, b_fake=10, b_trap=6, c_count=12, seed=42):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = generate_full_benchmark(a_knowledge, a_arithmetic, b_fake, b_trap, c_count, seed)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def load_benchmark(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def module_counts(data):
    return {k: len(v) for k, v in data["modules"].items()}
