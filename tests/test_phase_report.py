import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase_report as pr  # noqa: E402

FAKE_TOKEN = "gh" + "p_" + "A" * 36


def sample(**extra):
    data = {
        "phase": 4, "title": "Ganchos", "objective": "Probar", "executive_summary": ["ok"],
        "initial_state": ["a"], "final_state": ["b"], "components": ["c"],
        "files": {"created": ["x.py"], "modified": []}, "versions": ["python 3.13"],
        "commands": [{"cmd": "python -m unittest", "result": "OK"}],
        "tests": [{"name": "t1", "status": "passed", "evidence": "OK"}],
        "evidence": ["e"], "risks": ["r"], "decisions": [{"decision": "d", "why": "w"}],
        "tokens": [
            {"agent": "E2", "model": "haiku", "tokens": 100, "tool_uses": 3, "duration_s": 12.5, "source": "measured"},
            {"agent": "E1", "model": "sonnet", "tokens": 50, "tool_uses": 1, "duration_s": 2, "source": "x"},
        ],
        "costs": [{"item": "api", "usd": 0.5, "source": "x"}], "duration": "10 min",
        "problems": [{"problem": "p", "solution": "s"}], "pending": ["p"], "authorizations": ["a"],
        "github": {"commits": [], "prs": [], "links": []}, "next_phase": "5",
    }
    data.update(extra)
    return data


class PhaseReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.no_usage = str(self.tmp / "no-usage")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_data(self, data, name="PHASE_04.json", folder="data"):
        path = self.tmp / folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_nineteen_sections_in_order(self):
        text = pr.render(sample(), self.no_usage, ".")
        positions = []
        for number, name in enumerate(pr.SECTIONS, 1):
            heading = f"## {number}. {name}"
            self.assertEqual(text.count(heading), 1, heading)
            positions.append(text.index(heading))
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(pr.SECTIONS), 19)
        self.assertEqual(text.count("\n## "), 19)

    def test_empty_sections_message(self):
        text = pr.render({"phase": 1, "title": "t"}, self.no_usage, ".")
        self.assertIn(pr.EMPTY, text)
        self.assertIn("## 19. Recomendación para la siguiente fase", text)

    def test_status_rendering(self):
        tests = [{"name": "a", "status": "passed"}, {"name": "b", "status": "failed"},
                 {"name": "c", "status": "pending"}, {"name": "d", "status": "not-measured"}]
        text = pr.render(sample(tests=tests), self.no_usage, ".")
        for label in ("✅ pasó", "❌ falló", "⏳ pendiente", "➖ no medido"):
            self.assertIn(label, text)

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            pr.render(sample(tests=[{"name": "a", "status": "maybe"}]), self.no_usage, ".")

    def test_token_total_row(self):
        text = pr.render(sample(), self.no_usage, ".")
        self.assertIn("**Total**", text)
        self.assertIn("| 150 |", text)

    def test_privacy_refuses_token(self):
        data_path = self.write_data(sample(commands=[{"cmd": "x", "result": FAKE_TOKEN}]))
        rc = pr.main(["render", "--data", str(data_path), "--usage-dir", self.no_usage])
        self.assertEqual(rc, 2)
        self.assertFalse((self.tmp / "PHASE_04_REPORT.md").exists())
        with self.assertRaises(pr.PrivacyError) as ctx:
            pr.render(sample(commands=[{"cmd": "x", "result": FAKE_TOKEN}]), self.no_usage, ".")
        self.assertNotIn(FAKE_TOKEN, "\n".join(ctx.exception.findings))

    def test_privacy_refuses_personal_path(self):
        data_path = self.write_data(sample(risks=["ruta C:\\Users\\someone\\proj"]))
        self.assertEqual(pr.main(["render", "--data", str(data_path), "--usage-dir", self.no_usage]), 2)

    def test_determinism(self):
        self.assertEqual(pr.render(sample(), self.no_usage, "."), pr.render(sample(), self.no_usage, "."))

    def test_usage_table_appended(self):
        usage = self.tmp / "usage"
        usage.mkdir()
        (usage / "s1.json").write_text(json.dumps({"totals_by_model": {"haiku": {
            "input_tokens": 7, "output_tokens": 2, "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 1, "messages": 1}}}), encoding="utf-8")
        text = pr.render(sample(), str(usage), ".")
        self.assertIn("Consumo medido por usage_tracker", text)
        self.assertIn("| total | haiku | 7 | 2 | 0 | 1 | 1 |", text)
        (usage / "s2.json").write_text(json.dumps({
            "main": {"opus": {"input_tokens": 5, "output_tokens": 1, "messages": 1}},
            "subagents": [{"models": {"sonnet": {"input_tokens": 3, "output_tokens": 4, "messages": 2}}}]}),
            encoding="utf-8")
        text = pr.render(sample(), str(usage), ".")
        self.assertIn("| orquestador | opus | 5 | 1 | 0 | 0 | 1 |", text)
        self.assertIn("| ejecutores | sonnet | 3 | 4 | 0 | 0 | 2 |", text)

    def test_latest_copies_newest_with_note(self):
        d = self.tmp / "reports"
        d.mkdir()
        (d / "PHASE_02_REPORT.md").write_text("old\n", encoding="utf-8")
        (d / "PHASE_04_REPORT.md").write_text("new\n", encoding="utf-8")
        self.assertEqual(pr.main(["latest", "--dir", str(d)]), 0)
        self.assertEqual((d / "LATEST_REPORT.md").read_text(encoding="utf-8"),
                         "Copia de PHASE_04_REPORT.md\n\nnew\n")

    def test_sub_phase_labels_and_latest(self):
        self.assertEqual(("04", "04_1", "04.1"), (pr.phase_label(4), pr.phase_label("4.1"), pr.phase_label("4.1", ".")))
        d = self.tmp / "sub"
        d.mkdir()
        for name in ("PHASE_04_REPORT.md", "PHASE_04_1_REPORT.md", "PHASE_03_REPORT.md"):
            (d / name).write_text(name + chr(10), encoding="utf-8")
        self.assertEqual(pr.main(["latest", "--dir", str(d)]), 0)
        self.assertIn("Copia de PHASE_04_1_REPORT.md", (d / "LATEST_REPORT.md").read_text(encoding="utf-8"))

    def test_check_detects_drift(self):
        d = self.tmp / "docs"
        self.write_data(sample(), folder="docs/data")
        data_path = d / "data" / "PHASE_04.json"
        self.assertEqual(pr.main(["render", "--data", str(data_path), "--usage-dir", self.no_usage]), 0)
        self.assertEqual(pr.main(["latest", "--dir", str(d)]), 0)
        check = ["check", "--dir", str(d), "--usage-dir", self.no_usage]
        self.assertEqual(pr.main(check), 0)
        report = d / "PHASE_04_REPORT.md"
        report.write_text(report.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
        self.assertEqual(pr.main(check), 1)


if __name__ == "__main__":
    unittest.main()
