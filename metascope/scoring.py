"""
评分函数与元认知指标（纯 Python 实现，无第三方依赖）
======================================================
指标对应 DeepMind 认知框架中的元认知（Metacognition）定义：

  * 校准类（Module A）
      - ECE  Expected Calibration Error   期望校准误差
      - MCE  Maximum Calibration Error    最大校准误差
      - Brier Score                       布莱尔分数（正确评分规则，惩罚投机取巧）
      - Overconfidence Rate               过自信率
      - Calibration Curve                 校准曲线（分箱 置信度 vs 实际准确率）

  * 未知识别类（Module B）
      - AUROC（用“确信度”作为分数，预测“作答是否正确”）—— 模型越自信越正确 ⇒ 高 AUROC
      - Hallucination Rate                幻觉率（对无有效答案项仍强行作答）
      - Rejection / Abstain Rate          拒绝率（正确识别“不知道”的比例）
      - Known vs Unknown Calibration Gap  知道与不知道项的校准差异

  * 自我监控类（Module C）
      - Reflexivity Error                 自我预测误差 |预测正确数 - 实际正确数|
      - Predicted-Actual Correlation      预测与实际的相关性

  * 复合分
      - MetaScore = 满分 100 的加权汇总（校准 40 + 未知识别 40 + 自我监控 20）
"""

import math


# ---------------------------------------------------------------------------
# 校准指标
# ---------------------------------------------------------------------------
def calibration_bins(confidences, corrects, n_bins=10):
    """按确信度分箱，返回 (bin_conf, bin_acc, bin_count) 列表。"""
    assert len(confidences) == len(corrects)
    if not confidences:
        return []
    bins = [[] for _ in range(n_bins)]
    for conf, corr in zip(confidences, corrects):
        idx = min(n_bins - 1, int(conf * n_bins))
        bins[idx].append((conf, int(corr)))
    result = []
    for b in bins:
        if not b:
            continue
        avg_conf = sum(c for c, _ in b) / len(b)
        avg_acc = sum(y for _, y in b) / len(b)
        result.append((avg_conf, avg_acc, len(b)))
    return result


def ece(confidences, corrects, n_bins=10):
    """期望校准误差：加权平均的 |准确率 - 确信度| 绝对偏差。"""
    bins = calibration_bins(confidences, corrects, n_bins)
    n = len(confidences)
    if n == 0:
        return 0.0
    return sum(abs(acc - conf) * cnt / n for conf, acc, cnt in bins)


def mce(confidences, corrects, n_bins=10):
    """最大校准误差：各分箱中 |准确率-确信度| 的最大值。"""
    bins = calibration_bins(confidences, corrects, n_bins)
    if not bins:
        return 0.0
    return max(abs(acc - conf) for conf, acc, cnt in bins)


def brier(confidences, corrects):
    """布莱尔分数：mean((1 - conf_selected)^2) —— 对选中的答案项。
    越小越好（0 = 完美校准且全对）。"""
    if not confidences:
        return 0.0
    return sum((c - int(y)) ** 2 for c, y in zip(confidences, corrects)) / len(confidences)


def overconfidence_rate(confidences, corrects, n_bins=10):
    """过自信率：仅在“准确率 < 确信度”的分箱上，加权平均偏差。
    反映了模型系统性高估自己。"""
    bins = calibration_bins(confidences, corrects, n_bins)
    n = len(confidences)
    if n == 0:
        return 0.0
    total = 0.0
    for conf, acc, cnt in bins:
        if acc < conf:
            total += (conf - acc) * cnt / n
    return total


# ---------------------------------------------------------------------------
# 未知识别（AUROC，Mann-Whitney 秩和法，纯 Python）
# ---------------------------------------------------------------------------
def _rank_auc(scores_pos, scores_neg):
    """用“确信度”作分数：正例=作答正确，负例=作答错误。AUROC=随机抽一对，正例分更高的概率。"""
    if not scores_pos or not scores_neg:
        return 0.5
    pos = sorted(scores_pos)
    neg = sorted(scores_neg)
    n_pos, n_neg = len(pos), len(neg)
    total = 0.0
    i = 0
    for p in pos:
        # neg 中严格小于 p 的数量 + 0.5 * 等于 p 的数量
        while i < n_neg and neg[i] < p:
            i += 1
        j = i
        while j < n_neg and neg[j] == p:
            j += 1
        total += i + 0.5 * (j - i)
    auc = total / (n_pos * n_neg)
    return auc


def unknown_awareness_auc(confidences, corrects):
    """以确信度作为不确定性分数，预测“作答是否正确”。
    AUROC 越接近 1，说明模型越“自信即正确”——校准良好的未知识别。"""
    pos = [c for c, y in zip(confidences, corrects) if y == 1]
    neg = [c for c, y in zip(confidences, corrects) if y == 0]
    return _rank_auc(pos, neg)


def hallucination_rate(items_results):
    """幻觉率：对“无有效答案”或“信息不足”的题目，模型仍给出具体答案（非拒绝）的比例。"""
    if not items_results:
        return 0.0
    halluc = sum(1 for r in items_results if not r["rejected"])
    return halluc / len(items_results)


def rejection_rate(items_results):
    """正确拒绝率：本应拒绝（无有效答案/信息不足）的题目中被模型正确拒绝的比例。"""
    if not items_results:
        return 0.0
    # 对这些题目，正确答案就是“拒绝”，correct 字段标记为 1 表示正确拒绝
    ok = sum(1 for r in items_results if r["correct"] == 1)
    return ok / len(items_results)


def calibration_gap(known_errors, unknown_errors):
    """知道与不知道场景的校准误差之差 —— 衡量“有知时有把握、无知时也自信”的病态偏差。"""
    return unknown_errors - known_errors


# ---------------------------------------------------------------------------
# 自我监控（Module C）
# ---------------------------------------------------------------------------
def reflexivity_error(predicted_correct, actual_correct, n_total):
    """自我预测误差：|预测答对个数 - 实际答对个数|。越小，自我认知越准确。"""
    return abs(predicted_correct - actual_correct) / n_total


# ---------------------------------------------------------------------------
# 复合分 MetaScore（0-100）
# ---------------------------------------------------------------------------
def metascore(ece_val, brier_val, overconf, rejection_rate, reflex_err):
    """加权汇总：校准 40 + 未知识别 40 + 自我监控 20。
    设计取向：
      - 校准：惩罚 ECE（校准误差）、Brier（正确评分规则）、过自信率——校准良好得高分
      - 未知识别：核心是“正确拒绝/不幻觉”（知道不知道）——以正确拒绝率为主
      - 自我监控：预测正确数与实际一致（知道自己几斤几两）
    """
    calib_score = max(0.0, 40 * (1 - (ece_val + brier_val) / 2 - overconf))
    unk_score = max(0.0, 40 * min(1.0, rejection_rate))
    refl_score = max(0.0, 20 * (1 - reflex_err))
    total = calib_score + unk_score + refl_score
    return {
        "MetaScore": round(total, 1),
        "校准得分": round(calib_score, 1),
        "未知识别得分": round(unk_score, 1),
        "自我监控得分": round(refl_score, 1),
    }
