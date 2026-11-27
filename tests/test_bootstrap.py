import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import hub
from scripts.bootstrap import bootstrap, verify_project

class BootstrapTests(unittest.TestCase):
    @patch("scripts.bootstrap.probe_memory",return_value={"state":"unreachable"})
    def test_bootstrap_and_tamper_detection(self,probe):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            report=bootstrap(hub.ROOT,target,fetch_external=False)
            self.assertEqual(report["static_errors"],[])
            self.assertFalse(report["ready"])
            self.assertTrue((target/".agent-hub/bootstrap-report.json").exists())
            (target/".claude/agents/orchestrator.md").write_text("changed")
            self.assertTrue(verify_project(target))
