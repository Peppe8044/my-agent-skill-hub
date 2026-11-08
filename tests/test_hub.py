"""Self-contained checks for the deterministic hub CLI."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts import hub


class HubTests(unittest.TestCase):
    def test_repository_validation(self):
        self.assertEqual([], hub.validate(), "Hub registry, agents and skills must be consistent")

    def test_required_policy(self):
        self.assertTrue(hub.MANDATORY_SKILLS.issubset(
            {p.parent.name for p in (hub.ROOT/"skills").glob("*/SKILL.md")}
        ))

    def test_name_validation(self):
        self.assertEqual("valid-name", hub.slug("valid-name"))
        for invalid in ("../bad", "bad name", ".hidden", "", "a/" + "b" * 80):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    hub.slug(invalid)

    def test_project_creation_is_safe_and_has_doc_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = hub.new_project("test-project", "data-science", Path(tmp))
            self.assertEqual(json.loads((p/"project.json").read_text())["kind"],
                             "data-science")
            for filename in ("PROJECT_BRIEF.md", "STACK_DECISION.md",
                             "WORK_LOG.md", "QUALITY_REPORT.md", "HANDOFF.md",
                             "EXCEPTIONS.md"):
                self.assertTrue((p/filename).is_file(), filename)
            with self.assertRaises(FileExistsError):
                hub.new_project("test-project", "data-science", Path(tmp))

    def test_recommendation_is_conditional(self):
        candidates = hub.recommend({"kind": "data-science", "requirements": {
            "has_ml": True, "team_prefers_python": True
        }})
        self.assertEqual(candidates[0]["id"], "data-ml")
        self.assertTrue(candidates[0]["score"] > candidates[-1]["score"])
        candidates = hub.recommend({"kind": "sre", "requirements": {
            "needs_automation": True, "team_prefers_python": True
        }})
        self.assertIn(candidates[0]["id"], ("sre-tool", "automation"))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            hub.recommend({"kind": "quantum", "requirements": {}})

    def test_readme_describes_limits(self):
        text = (hub.ROOT/"README.md").read_text(encoding="utf-8")
        self.assertIn("no", text.lower())
        self.assertIn("stack", text.lower())


if __name__ == "__main__":
    unittest.main()
