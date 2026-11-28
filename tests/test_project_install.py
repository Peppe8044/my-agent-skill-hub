import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts import hub, model_policy as mp
from scripts.bootstrap import bootstrap, verify_project
from scripts.project_install import PolicyConflictError, install, norm_name, norm_url, parse_mcp_list
from tests.support import Isolated

CLICKUP = {"type": "http", "url": "https://mcp.clickup.com/mcp"}
RUNTIME_OUT = ("Checking MCP server health…\n"
               "claude.ai ClickUp: https://mcp.clickup.com/mcp - ✔ Connected\n"
               "other: npx -y thing - ✔ Connected\n")


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in Path(root).rglob("*") if p.is_file()}


class InstallTests(Isolated, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.p = Path(self._t.name)

    def go(self, **kw):
        kw.setdefault("home", self._home.name)
        kw.setdefault("runtime_scan", False)
        return install(hub.ROOT, self.p, fetch_external=False, **kw)

    def mcp(self):
        return json.loads((self.p / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]

    def test_install_and_repeat(self):
        first = self.go()
        self.assertTrue((self.p / ".claude/agents/orchestrator.md").is_file())
        self.assertTrue((self.p / ".agents/skills/token-budget/SKILL.md").is_file())
        self.assertTrue((self.p / ".claude/hooks/model_guard.py").is_file())
        self.assertEqual(["clickup", "github"], sorted(first["mcp"]["added"]))
        self.assertEqual("created", first["settings"])
        snapshot = tree(self.p)
        second = self.go()
        self.assertEqual(snapshot, tree(self.p))
        self.assertEqual([], second["conflicts"])
        self.assertEqual([], second["mcp"]["added"])
        self.assertEqual(["clickup", "github"], second["mcp"]["preserved"])
        self.assertEqual([], verify_project(self.p))

    def test_core_has_hook_and_no_mcp(self):
        self.go(profile="core")
        self.assertTrue((self.p / ".claude/hooks/model_guard.py").is_file())
        self.assertFalse((self.p / ".mcp.json").exists())

    def test_preserves_existing_and_stages_incoming(self):
        (self.p / "CLAUDE.md").write_bytes(b"custom\r\nline")
        result = self.go()
        self.assertEqual(b"custom\r\nline", (self.p / "CLAUDE.md").read_bytes())
        self.assertEqual(["CLAUDE.md"], result["conflicts"])
        self.assertEqual((hub.ROOT / "CLAUDE.md").read_bytes(), (self.p / ".agent-hub/incoming/CLAUDE.md").read_bytes())
        self.assertTrue((self.p / "MODEL_POLICY.json").exists())
        again = self.go()
        self.assertEqual(["CLAUDE.md"], again["conflicts"])
        (self.p / "CLAUDE.md").write_bytes((hub.ROOT / "CLAUDE.md").read_bytes())
        done = self.go()
        self.assertEqual([], done["conflicts"])
        self.assertFalse((self.p / ".agent-hub/incoming/CLAUDE.md").exists())

    def test_hub_updated_file_is_overwritten_when_unchanged_by_user(self):
        self.go()
        (self.p / "AGENTS.md").write_bytes(b"old hub version")
        manifest = json.loads((self.p / ".agent-hub/manifest.json").read_text())
        from scripts.project_install import digest
        manifest["files"]["AGENTS.md"] = digest(b"old hub version")
        (self.p / ".agent-hub/manifest.json").write_text(json.dumps(manifest))
        self.assertEqual([], self.go()["conflicts"])
        self.assertEqual((hub.ROOT / "AGENTS.md").read_bytes(), (self.p / "AGENTS.md").read_bytes())

    def test_duplicate_via_project_mcp(self):
        (self.p / ".mcp.json").write_text(json.dumps({"mcpServers": {"my-gh": {
            "type": "http", "url": "https://API.githubcopilot.com/mcp"}}}))
        result = self.go()
        self.assertEqual({"github": "duplicate of project:my-gh"}, {k: v for k, v in result["mcp"]["skipped"].items() if k == "github"})
        self.assertEqual(["clickup"], result["mcp"]["added"])
        self.assertNotIn("github", self.mcp())

    def test_duplicate_via_user_and_local_scope(self):
        (Path(self._home.name) / ".claude.json").write_text(json.dumps({
            "mcpServers": {"ClickUp": {"type": "http", "url": "https://x.example/other"}},
            "projects": {str(self.p).replace("\\", "/"): {"mcpServers": {"gh": {"url": "https://api.githubcopilot.com/mcp/"}}}}}))
        result = self.go()
        self.assertEqual("duplicate of user:ClickUp", result["mcp"]["skipped"]["clickup"])
        self.assertEqual("duplicate of local:gh", result["mcp"]["skipped"]["github"])
        self.assertFalse((self.p / ".mcp.json").exists())

    def test_duplicate_via_runtime_scan(self):
        calls = []
        def runner(args, cwd=None, env=None, timeout=None):
            calls.append((args, env, timeout))
            return SimpleNamespace(returncode=0, stdout=RUNTIME_OUT, stderr="")
        result = self.go(runtime_scan=True, runner=runner, which=lambda n: "claude")
        self.assertEqual("ok", result["mcp"]["runtime_scan"])
        self.assertEqual("duplicate of runtime:claude.ai ClickUp", result["mcp"]["skipped"]["clickup"])
        self.assertEqual(["github"], result["mcp"]["added"])
        self.assertEqual(["github"], list(self.mcp()))
        self.assertEqual(["claude", "mcp", "list"], calls[0][0])
        self.assertNotIn("CLAUDECODE", calls[0][1])
        self.assertEqual(120, calls[0][2])

    def test_runtime_scan_failure_and_skip(self):
        def boom(*a, **k):
            raise OSError("x")
        self.assertTrue(self.go(runtime_scan=True, runner=boom, which=lambda n: "claude")
                        ["mcp"]["runtime_scan"].startswith("unavailable"))
        self.assertEqual("skipped", self.go(runtime_scan=True, which=lambda n: None)["mcp"]["runtime_scan"])

    def test_existing_servers_preserved_verbatim_and_conflict(self):
        existing = {"theme": 1, "mcpServers": {"clickup": {"type": "http", "url": "https://mine.example/mcp", "headers": {"A": "secret"}},
                                               "db": {"command": "x", "env": {"T": "tok"}}}}
        (self.p / ".mcp.json").write_text(json.dumps(existing))
        result = self.go()
        servers = self.mcp()
        self.assertEqual(existing["mcpServers"]["clickup"], servers["clickup"])
        self.assertEqual(existing["mcpServers"]["db"], servers["db"])
        self.assertIn("github", servers)
        self.assertEqual(1, json.loads((self.p / ".mcp.json").read_text())["theme"])
        self.assertEqual(1, len(result["mcp"]["conflicts"]))
        self.assertNotIn("secret", json.dumps(result))
        self.assertNotIn("tok", json.dumps(result))

    def test_no_mcp_file_when_all_duplicates_and_existing_untouched(self):
        raw = json.dumps({"mcpServers": {"clickup": CLICKUP, "github": {"type": "http", "url": "https://api.githubcopilot.com/mcp/"}}}, indent=4)
        (self.p / ".mcp.json").write_text(raw)
        self.go()
        self.assertEqual(raw, (self.p / ".mcp.json").read_text())

    def test_settings_merge_preserves_project_keys_and_hooks(self):
        project = {"permissions": {"allow": ["Bash(ls)"]}, "env": {"FOO": "1"},
                   "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo"}]}],
                             "Stop": [{"hooks": []}]}}
        (self.p / ".claude").mkdir()
        (self.p / ".claude/settings.json").write_text(json.dumps(project))
        result = self.go()
        merged = json.loads((self.p / ".claude/settings.json").read_text())
        self.assertEqual("merged", result["settings"])
        self.assertEqual(project["permissions"], merged["permissions"])
        self.assertEqual("1", merged["env"]["FOO"])
        self.assertEqual("sonnet", merged["env"]["CLAUDE_CODE_SUBAGENT_MODEL"])
        self.assertEqual("opus", merged["model"])
        self.assertEqual(project["hooks"]["PreToolUse"][0], merged["hooks"]["PreToolUse"][0])
        self.assertEqual(project["hooks"]["Stop"][0], merged["hooks"]["Stop"][0])
        self.assertTrue(mp.has_model_guard(merged))
        self.assertEqual([], mp.validate_settings(merged, self.p))
        self.assertEqual([], verify_project(self.p))
        before = (self.p / ".claude/settings.json").read_bytes()
        self.assertEqual("unchanged", self.go()["settings"])
        self.assertEqual(before, (self.p / ".claude/settings.json").read_bytes())

    def test_policy_conflicts_stop_without_writing(self):
        bad = [{"env": {"ANTHROPIC_MODEL": "x"}}, {"model": "sonnet"}, {"env": {"CLAUDE_CODE_SUBAGENT_MODEL": "opus"}}]
        for settings in bad:
            with self.subTest(settings=settings):
                (self.p / ".claude").mkdir(exist_ok=True)
                (self.p / ".claude/settings.json").write_text(json.dumps(settings))
                with self.assertRaises(PolicyConflictError):
                    self.go()
                self.assertEqual({".claude/settings.json"}, set(tree(self.p)))
        (self.p / ".claude/settings.json").write_text("{nope")
        with self.assertRaises(ValueError):
            self.go()
        self.assertEqual({".claude/settings.json"}, set(tree(self.p)))

    def test_normalizers(self):
        self.assertEqual(norm_name("claude.ai Click-Up"), norm_name("clickup"))
        self.assertEqual("https://a.com/x", norm_url("HTTPS://A.com/x/?q=1#f"))
        self.assertEqual({"a": "u", "claude.ai B": "cmd x"},
                         parse_mcp_list("Checking MCP server health…\na: u - ok\nclaude.ai B: cmd x - bad\n"))

    def test_bootstrap_reports_pending(self):
        (self.p / "AGENTS.md").write_text("mine")
        report = bootstrap(hub.ROOT, self.p, fetch_external=False, runtime_scan=False, home=self._home.name)
        self.assertEqual(["AGENTS.md"], [x for x in report["pending_reconciliation"] if x == "AGENTS.md"])
        self.assertFalse(report["ready"])
        self.assertEqual([], report["static_errors"])

    def test_new_has_agents(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = hub.new_project("demo", "web", Path(tmp))
            self.assertTrue((p / ".claude/agents/orchestrator.md").exists())


if __name__ == "__main__":
    unittest.main()
