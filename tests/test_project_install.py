import tempfile
import unittest
from pathlib import Path
from scripts import hub
from scripts.project_install import install

class InstallTests(unittest.TestCase):
    def test_install_and_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            install(hub.ROOT,p,fetch_external=False)
            self.assertTrue((p/".claude/agents/orchestrator.md").is_file())
            self.assertTrue((p/".agents/skills/token-budget/SKILL.md").is_file())
            self.assertTrue((p/".agent-hub/manifest.json").is_file())
            install(hub.ROOT,p,fetch_external=False)
    def test_preserves_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p/"CLAUDE.md").write_text("custom")
            with self.assertRaises(FileExistsError):
                install(hub.ROOT,p,fetch_external=False)
            self.assertEqual((p/"CLAUDE.md").read_text(),"custom")
            self.assertFalse((p/"MODEL_POLICY.json").exists())
    def test_new_has_agents(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=hub.new_project("demo","web",Path(tmp))
            self.assertTrue((p/".claude/agents/orchestrator.md").exists())
