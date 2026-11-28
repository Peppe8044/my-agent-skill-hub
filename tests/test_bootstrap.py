import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import hub
from scripts.bootstrap import bootstrap, launch, verify_project
from tests.support import Isolated


class BootstrapTests(Isolated, unittest.TestCase):
    @patch("scripts.bootstrap.probe_memory", return_value={"state": "unreachable"})
    def test_bootstrap_and_tamper_detection(self, probe):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            report = bootstrap(hub.ROOT, target, fetch_external=False, runtime_scan=False, home=self._home.name)
            self.assertEqual(report["static_errors"], [])
            self.assertFalse(report["ready"])
            self.assertEqual([], report["pending_reconciliation"])
            self.assertTrue((target / ".agent-hub/bootstrap-report.json").exists())
            (target / ".claude/agents/orchestrator.md").write_text("changed")
            self.assertTrue(verify_project(target))

    @patch("scripts.bootstrap.probe_memory", return_value={"state": "unreachable"})
    def test_verify_detects_missing_hook(self, probe):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            bootstrap(hub.ROOT, target, fetch_external=False, runtime_scan=False, home=self._home.name)
            (target / ".claude/hooks/model_guard.py").unlink()
            self.assertTrue(any("model_guard" in e for e in verify_project(target)))

    @patch("scripts.bootstrap.subprocess.call")
    @patch("scripts.bootstrap.shutil.which", return_value="claude")
    def test_launch_blocked_by_forbidden_env(self, which, call):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(3, launch(tmp, {"ANTHROPIC_MODEL": "x"}))
            self.assertEqual(3, launch(tmp, {"CLAUDE_CODE_SUBAGENT_MODEL": "opus"}))
        call.assert_not_called()

    @patch("scripts.bootstrap.probe_memory", return_value={"state": "unreachable"})
    @patch("scripts.bootstrap.subprocess.call", return_value=0)
    @patch("scripts.bootstrap.shutil.which", return_value="claude")
    def test_launch_command(self, which, call, probe):
        with tempfile.TemporaryDirectory() as tmp:
            bootstrap(hub.ROOT, Path(tmp), fetch_external=False, runtime_scan=False, home=self._home.name)
            self.assertEqual(0, launch(tmp, {"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"}))
        self.assertEqual(["claude", "--agent", "orchestrator", "--model", "opus"], call.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
