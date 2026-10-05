"""
评测管线：对给定“被试”模型执行 MetaScope 三模块评测并输出结构化结果
====================================================================
流程：
  1. 加载题目（模块 A/B/C）
  2. Module A —— 逐题作答，收集 (确信度, 是否正确)，计算校准指标
  3. Module B —— 未知识别项，计算 AUROC / 幻觉率 / 拒绝率 / 校准差距
  4. Module C —— 先预测答对数再逐题作答，计算自我监控误差
  5. 汇总 MetaScore 与各模块指标
"""

import json
import os

from . import scoring


def _is_unknown_item(item):
    return item.get("meta", {}).get("kind") == "unknown"


def _judge(item, resp):
    """判定单题对错。返回 (correct: 0/1, confidence, hallucination: 0/1)。"""
    meta = item.get("meta", {})
    answer = resp.get("answer")
    confidence = float(resp.get("confidence", 0.5))
    rejected = bool(resp.get("rejected", False))

    if meta.get("has_valid") is False:
        # 全部伪造项：正确行为 = 拒绝
        correct = 1 if rejected else 0
        halluc = 0 if rejected else 1
        return correct, confidence, halluc

    if _is_unknown_item(item):
        # B2 信息不足项：正确行为 = 选择“无法确定”选项（abstain_letter）
        abstain = meta.get("abstain_letter")
        correct = 1 if (rejected or answer == abstain) else 0
        halluc = 0 if (rejected or answer == abstain) else 1
        return correct, confidence, halluc

    # 普通多选题
    correct = 1 if answer is not None and answer == item["correct_letter"] else 0
    return correct, confidence, 0


def run_module_a(model, items):
    confs, corrects = [], []
    for item in items:
        resp = model.respond(item)
        c, conf, _ = _judge(item, resp)
        confs.append(conf)
        corrects.append(c)
    return {
        "n": len(items),
        "accuracy": (sum(corrects) / len(corrects)) if corrects else 0.0,
        "avg_confidence": (sum(confs) / len(confs)) if confs else 0.0,
        "ece": scoring.ece(confs, corrects),
        "mce": scoring.mce(confs, corrects),
        "brier": scoring.brier(confs, corrects),
        "overconfidence": scoring.overconfidence_rate(confs, corrects),
        "auc_known": scoring.unknown_awareness_auc(confs, corrects),
        "calibration_curve": scoring.calibration_bins(confs, corrects),
        "confidences": confs,
        "corrects": corrects,
    }


def run_module_b(model, items):
    unknown_items = [i for i in items if _is_unknown_item(i)]
    confs, corrects = [], []
    halluc = []
    for item in unknown_items:
        resp = model.respond(item)
        c, conf, h = _judge(item, resp)
        confs.append(conf)
        corrects.append(c)
        halluc.append(h)
    return {
        "n_unknown": len(unknown_items),
        "hallucination_rate": scoring.hallucination_rate(
            [{"rejected": not h} for h in halluc]),   # 复用：rejected=True 表示未幻觉
        "rejection_rate": scoring.rejection_rate(
            [{"correct": c} for c in corrects]),
        "unknown_auc": scoring.unknown_awareness_auc(confs, corrects),
        "avg_confidence_on_unknown": (sum(confs) / len(confs)) if confs else 0.0,
        "accuracy_on_unknown": (sum(corrects) / len(corrects)) if corrects else 0.0,
    }


def run_module_c(model, items):
    n = len(items)
    if hasattr(model, "predict_correct_count"):
        predicted = model.predict_correct_count(n)
    else:
        predicted = n
    confs, corrects = [], []
    for item in items:
        resp = model.respond(item)
        c, conf, _ = _judge(item, resp)
        confs.append(conf)
        corrects.append(c)
    actual = sum(corrects)
    reflex_err = scoring.reflexivity_error(predicted, actual, n)
    return {
        "n": n,
        "predicted_correct": predicted,
        "actual_correct": actual,
        "reflexivity_error": reflex_err,
        "accuracy": actual / n if n else 0.0,
    }


def run_benchmark(model, data, name="model", label="模型"):
    modules = data["modules"]
    res_a = run_module_a(model, modules["A_knowledge_calibration"])
    res_b = run_module_b(model, modules["B_unknown_awareness"])
    res_c = run_module_c(model, modules["C_confidence_reflexivity"])

    # 校准差距：知道项 vs 未知项（Module B 的校准 vs 已知项校准）
    known_ece = res_a["ece"]
    unknown_conf = res_b["avg_confidence_on_unknown"]
    unknown_acc = res_b["accuracy_on_unknown"]
    unknown_ece = abs(unknown_conf - unknown_acc)

    ms = scoring.metascore(
        ece_val=res_a["ece"],
        brier_val=res_a["brier"],
        overconf=res_a["overconfidence"],
        rejection_rate=res_b["rejection_rate"],
        reflex_err=res_c["reflexivity_error"],
    )

    return {
        "name": name,
        "label": label,
        "summary": {
            "模块A_知识校准": res_a,
            "模块B_未知识别": res_b,
            "模块C_自信反思": res_c,
            "校准差距_known_vs_unknown": round(unknown_ece, 4),
        },
        "MetaScore": ms,
    }


def save_result(result, out_dir, filename):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, filename)
    # 深拷贝，避免把大数据写进报告
    def _clean(o):
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()
                    if k not in ("confidences", "corrects", "calibration_curve")}
        if isinstance(o, list):
            return [_clean(x) for x in o]
        return o
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_clean(result), f, ensure_ascii=False, indent=2)
    return path


def load_result(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
