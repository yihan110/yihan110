"""test_c4_evaluator.py —— C4A 自动评审器单元测试。

覆盖：
  * 扫描与作者识别（文件名 / 子文件夹回退 / 版本追踪 / 非 C4 过滤）
  * 完整性检查（齐全 / 部分 / 严重缺失 分级）
  * 质量评审（可复用对硬编码路径降级、否定词不误判、各作者区分度）
  * 综合分排名顺序
  * 边界情况（空文件夹、无 C4 文件）

运行方式：
  cd <skill 根目录>
  python -m unittest discover -s tests -p "test_*.py" -v
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from src.completeness import check_completeness  # noqa: E402
from src.config import load_rubric  # noqa: E402
from src.evaluator import composite_score, run_evaluation  # noqa: E402
from src.quality import evaluate_quality, _has  # noqa: E402
from src.scanner import scan_folder  # noqa: E402

FIXTURES = SKILL_ROOT / "tests" / "fixtures" / "群文件"


class TestScanner(unittest.TestCase):
    def setUp(self):
        self.scan = scan_folder(str(FIXTURES))

    def test_identifies_all_authors(self):
        self.assertEqual(
            set(self.scan.authors.keys()),
            {"TomZhang", "WangXia", "ZhaoLei", "阮依涵", "ChenYu", "SunQi"})

    def test_subfolder_fallback(self):
        # TomZhang 文件名无作者前缀，作者来自子文件夹名
        for fi in self.scan.authors["TomZhang"]:
            self.assertEqual(fi.source, "subfolder")

    def test_version_tracking(self):
        vers = {fi.name: fi.version for fi in self.scan.authors["TomZhang"]}
        self.assertEqual(vers.get("_C4_AI日志_v1.md"), "1")
        self.assertEqual(vers.get("_C4_AI日志_v2.md"), "2")
        self.assertEqual(vers.get("_C4_技能包_v2.skill"), "2")

    def test_non_c4_filtered(self):
        names = {f.name for f in self.scan.non_c4_files}
        self.assertIn("群公告.md", names)
        self.assertIn("README.md", names)
        # 群公告不应进入任何作者
        self.assertNotIn("群公告.md", {f.name for a in self.scan.authors.values() for f in a})


class TestCompleteness(unittest.TestCase):
    def setUp(self):
        self.rubric = load_rubric()
        self.scan = scan_folder(str(FIXTURES))

    def test_ruan_complete(self):
        r = check_completeness("阮依涵", self.scan.authors["阮依涵"], self.rubric)
        self.assertEqual(r.present_count, 5)
        self.assertEqual(r.status, "齐全")

    def test_chenyu_partial(self):
        r = check_completeness("ChenYu", self.scan.authors["ChenYu"], self.rubric)
        self.assertEqual(r.present_count, 3)
        self.assertEqual(r.status, "部分缺失")
        # 缺 demo 和 ai_log
        self.assertFalse(r.items["demo"].present)
        self.assertFalse(r.items["ai_log"].present)

    def test_sunqi_severe(self):
        r = check_completeness("SunQi", self.scan.authors["SunQi"], self.rubric)
        self.assertEqual(r.status, "严重缺失")

    def test_zhaolei_executable_by_skill_doc_name(self):
        r = check_completeness("ZhaoLei", self.scan.authors["ZhaoLei"], self.rubric)
        self.assertTrue(r.items["executable_content"].present)


class TestQuality(unittest.TestCase):
    def setUp(self):
        self.rubric = load_rubric()
        self.scan = scan_folder(str(FIXTURES))

    def test_negation_not_false_positive(self):
        # “无安装说明”不应命中“安装”
        self.assertFalse(_has("可复用：无安装说明，依赖固定路径", "安装", "install"))
        # 正常“安装”应命中
        self.assertTrue(_has("安装：pip install -r requirements.txt", "安装", "install"))

    def test_zhaolei_reusable_downgraded_for_hardcoded_path(self):
        # 赵磊文档含 C:\Users\ZhaoLei 硬编码路径且“无安装说明” → 可复用应为 ⚠️
        q = evaluate_quality("ZhaoLei", self.scan.authors["ZhaoLei"], self.rubric)
        self.assertEqual(q.criteria["reusable"].grade, "partial")  # ⚠️

    def test_wangxia_reusable_clean(self):
        # 王霞环境变量用法不应被判为硬编码凭据 → 可复用 ✅
        q = evaluate_quality("WangXia", self.scan.authors["WangXia"], self.rubric)
        self.assertEqual(q.criteria["reusable"].grade, "pass")

    def test_envvar_export_not_credential(self):
        from src.quality import _has_hardcoded_path
        self.assertFalse(_has_hardcoded_path("export WEATHER_API_KEY=xxx"))
        self.assertTrue(_has_hardcoded_path('api_key = "sk-123456"'))

    def test_url_scheme_not_drive(self):
        from src.quality import _has_hardcoded_path
        self.assertFalse(_has_hardcoded_path("源码见 https://github.com/x/y"))
        self.assertTrue(_has_hardcoded_path("数据在 C:\\Users\\me\\data"))


class TestEvaluation(unittest.TestCase):
    def test_ranking_order(self):
        out = run_evaluation(str(FIXTURES))
        ranked = sorted(out.scores, key=out.scores.get, reverse=True)
        # 前三名应是完整且高质量者，赵磊因硬编码路径低于前三
        self.assertIn(ranked[0], {"TomZhang", "WangXia", "阮依涵"})
        self.assertGreaterEqual(out.scores[ranked[0]], out.scores["ZhaoLei"])
        # 完整性最差的 SunQi 应垫底
        self.assertEqual(ranked[-1], "SunQi")

    def test_composite_score(self):
        # 完整+全✅ = 100
        scan = scan_folder(str(FIXTURES))
        comp = check_completeness("WangXia", scan.authors["WangXia"], load_rubric())
        qual = evaluate_quality("WangXia", scan.authors["WangXia"], load_rubric())
        self.assertAlmostEqual(composite_score(comp, qual), 100.0, places=1)

    def test_empty_folder(self):
        with tempfile.TemporaryDirectory() as d:
            scan = scan_folder(d)
            self.assertEqual(scan.authors, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
