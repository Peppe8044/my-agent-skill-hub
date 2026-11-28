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
        self.assertEqual(["claude", "--agent", "orchestrator", "--model", "opus", "--effort", "medium"],
                         call.call_args[0][0])

    @patch("scripts.bootstrap.subprocess.call", return_value=0)
    @patch("scripts.bootstrap.shutil.which", return_value="claude")
    def test_launch_central_hub_uses_hub_validation(self, which, call):
        manifest = hub.ROOT / ".agent-hub/manifest.json"
        self.assertFalse(manifest.exists())
        env = {"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"}
        self.assertEqual(0, launch(hub.ROOT, env, phase="5", root=hub.ROOT))
        self.assertFalse(manifest.exists())
        self.assertIn("start-phase", call.call_args_list[0][0][0])
        self.assertEqual("claude", call.call_args_list[1][0][0][0])
        # Hub validation still guards the launch.
        call.reset_mock()
        with patch("scripts.hub.validate", return_value=["broken"]):
            with self.assertRaises(ValueError):
                launch(hub.ROOT, env, phase="5", root=hub.ROOT)
        call.assert_not_called()

    @patch("scripts.bootstrap.subprocess.call", return_value=2)
    @patch("scripts.bootstrap.shutil.which", return_value="claude")
    def test_launch_stops_when_start_phase_fails(self, which, call):
        env = {"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"}
        self.assertEqual(4, launch(hub.ROOT, env, phase="5", root=hub.ROOT))
        self.assertEqual(1, call.call_count)
        self.assertIn("start-phase", call.call_args[0][0])

    @patch("scripts.bootstrap.check_target_settings", return_value=[])
    @patch("scripts.bootstrap.subprocess.call", return_value=0)
    @patch("scripts.bootstrap.shutil.which", return_value="claude")
    def test_launch_project_without_manifest_still_fails(self, which, call, settings):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                launch(tmp, {"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"}, root=hub.ROOT)
        call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
