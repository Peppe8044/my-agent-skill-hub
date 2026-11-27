import tempfile
import unittest
from pathlib import Path
from scripts import hub
from scripts.integrations import approved_files, mcp_config, status

class IntegrationTests(unittest.TestCase):
    def test_default_mcp(self):
        config=mcp_config(hub.ROOT)
        self.assertEqual(set(config["mcpServers"]), {"github","clickup"})
    def test_no_unreviewed_skills(self):
        self.assertEqual(approved_files(hub.ROOT, []), {})
    def test_status_does_not_claim_runtime(self):
        with tempfile.TemporaryDirectory() as p:
            self.assertIn("not verified",status(hub.ROOT,Path(p))["runtime_status"])
