import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import hooks_manager as hm
from scripts import hub
from scripts.project_install import install, rollback
from tests.support import Isolated

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
ENTRY = "scripts/hooks/guard.js"
LIB = "scripts/lib/hooks/helper.js"


def make_fake_hub(tmp):
    hub_root = Path(tmp)
    (hub_root / "registry").mkdir()
    (hub_root / "docs").mkdir()
    (hub_root / ".claude/hooks").mkdir(parents=True)
    (hub_root / ".claude/hooks/model_guard.py").write_text("import sys\n", encoding="utf-8")
    decisions = {"schema": 1, "own": [{"id": "own:model-guard", "script": ".claude/hooks/model_guard.py",
                                        "runtime": "python", "events": [{"event": "PreToolUse", "matcher": "Agent|Task"}],
                                        "mandatory": True, "default_enabled": True, "risk": "low", "areas": [], "notes": "n"}],
                 "ecc": {"repo": "ECC", "decisions": {
                     "pre:guard": {"status": "approved", "default_enabled": True, "risk": "low", "runtime": "node",
                                   "files": [ENTRY, LIB], "entry": ENTRY, "reason": "reviewed"}}}}
    (hub_root / "registry/hook_decisions.json").write_text(json.dumps(decisions), encoding="utf-8")
    ecc = hub_root / "external/ECC"
    (ecc / "hooks").mkdir(parents=True)
    (ecc / "scripts/hooks").mkdir(parents=True)
    (ecc / "scripts/lib/hooks").mkdir(parents=True)
    entries = [{"matcher": "Write", "hooks": [{"type": "command", "command": "node -e \"x\" node " + ENTRY}]},
               {"hooks": [{"type": "command", "command": "node -e \"y\" node scripts/hooks/other.js"}]}]
    meta = [{"id": "pre:guard", "description": "d", "fingerprint": "f"},
            {"id": "pre:unknown", "description": "d", "fingerprint": "g"}]
    (ecc / "hooks/hooks.json").write_text(json.dumps({"hooks": {"PreToolUse": entries}}), encoding="utf-8")
    (ecc / "hooks/hooks.metadata.json").write_text(json.dumps({"entries": {"PreToolUse": meta}}), encoding="utf-8")
    (ecc / ENTRY).write_text("const h = require('../lib/hooks/helper');\n", encoding="utf-8")
    (ecc / LIB).write_text("module.exports = 1;\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(ecc)], check=True)
    subprocess.run([*GIT, "-C", str(ecc), "add", "-A"], check=True)
    subprocess.run([*GIT, "-C", str(ecc), "commit", "-qm", "x"], check=True)
    return hub_root


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.hub = make_fake_hub(self._t.name)

    def test_deterministic_and_merged(self):
        a, b = hm.build_registry(self.hub), hm.build_registry(self.hub)
        self.assertEqual(a, b)
        ids = [h["id"] for h in a["hooks"]]
        self.assertEqual(sorted(ids), ids)
        guard = next(h for h in a["hooks"] if h["id"] == "pre:guard")
        self.assertEqual("approved", guard["status"])
        self.assertEqual(hm.ECC_DEST + ENTRY, guard["install_paths"][0])
        self.assertIn("scripts/lib/hooks/helper", guard["dependencies"])
        self.assertEqual([{"event": "PreToolUse", "matcher": "Write"}], guard["events"])
        self.assertTrue(guard["command"].startswith('node "$CLAUDE_PROJECT_DIR/.claude/hooks/ecc/'))
        self.assertEqual(40, len(guard["provenance"]["commit"]))

    def test_unknown_ecc_id_is_inventory_only(self):
        unknown = next(h for h in hm.build_registry(self.hub)["hooks"] if h["id"] == "pre:unknown")
        self.assertEqual("inventory-only", unknown["status"])
        self.assertEqual("no decision recorded", unknown["reason"])
        self.assertFalse(unknown["default_enabled"])

    def test_report_and_check(self):
        hm.write_outputs(self.hub)
        self.assertEqual([], hm.check_outputs(self.hub))
        self.assertIn("Hooks aprobados", (self.hub / hm.REPORT_REL).read_text(encoding="utf-8"))

    def test_tampered_ecc_file_is_skipped(self):
        hm.write_outputs(self.hub)
        proj = Path(self._t.name) / "proj"
        plan = hm.plan_hooks(self.hub, proj, "full", {}, None)
        self.assertIn("pre:guard", plan["report"]["installed"])
        (self.hub / "external/ECC" / ENTRY).write_text("evil();\n", encoding="utf-8")
        subprocess.run([*GIT, "-C", str(self.hub / "external/ECC"), "commit", "-qam", "t"], check=True)
        plan = hm.plan_hooks(self.hub, proj, "full", {}, None)
        self.assertIn("pre:guard", plan["report"]["skipped"])
        self.assertFalse([k for k in plan["files"] if k.startswith(hm.ECC_DEST)])


class HooksInstallTests(Isolated, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._p = tempfile.TemporaryDirectory()
        self.addCleanup(self._p.cleanup)
        self.p = Path(self._p.name)

    def go(self, profile="full"):
        return install(hub.ROOT, self.p, profile=profile, fetch_external=False, home=self._home.name,
                       runtime_scan=False)

    def commands(self):
        return hm._settings_commands(json.loads((self.p / ".claude/settings.json").read_text(encoding="utf-8")))

    def write_settings(self, data):
        (self.p / ".claude").mkdir(exist_ok=True)
        (self.p / ".claude/settings.json").write_text(json.dumps(data), encoding="utf-8")

    def test_registers_each_approved_once(self):
        first = self.go()
        self.go()
        cmds = self.commands()
        for h in hm.load_registry(hub.ROOT)["hooks"]:
            if h["status"] == "approved" and h["default_enabled"] and h["id"] not in first["hooks"]["skipped"]:
                self.assertEqual(len(h["events"]), cmds.count(h["command"]), h["id"])
        self.assertIn("own:model-guard", first["hooks"]["installed"])
        self.assertIsNone(self.go()["backup"])

    def test_core_profile_only_mandatory(self):
        result = self.go("core")
        self.assertEqual(["own:model-guard", "own:usage-tracker"], result["hooks"]["installed"])
        self.assertEqual(3, len(self.commands()))  # guard + tracker on Stop and SubagentStop

    def test_disable_removes_only_hub_entry(self):
        self.write_settings({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo mine"}]}]}})
        self.go()
        hm.set_enabled(hub.ROOT, self.p, "own:command-guard", False)
        cmds = self.commands()
        self.assertIn("echo mine", cmds)
        self.assertFalse(any("command_guard" in c for c in cmds))
        self.assertTrue(any("file_guard" in c for c in cmds))
        self.assertEqual(["own:command-guard"], self.go()["hooks"]["disabled"])
        self.assertFalse(any("command_guard" in c for c in self.commands()))
        hm.set_enabled(hub.ROOT, self.p, "own:command-guard", True)
        self.assertEqual(1, sum("command_guard" in c for c in self.commands()))

    def test_model_guard_cannot_be_disabled(self):
        self.go()
        with self.assertRaises(ValueError):
            hm.set_enabled(hub.ROOT, self.p, "own:model-guard", False)
        self.assertEqual(2, hm.main(["disable", "--target", str(self.p), "own:model-guard"]))

    def test_conflict_with_same_named_project_hook(self):
        self.write_settings({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": "python tools/command_guard.py"}]}]}})
        result = self.go()
        self.assertEqual(["own:command-guard"], [c["id"] for c in result["hooks"]["conflicts"]])
        self.assertEqual(["python tools/command_guard.py"], [c for c in self.commands() if "command_guard" in c])

    def test_global_duplicate_reported(self):
        home = Path(self._home.name)
        (home / ".claude").mkdir()
        cmd = next(h["command"] for h in hm.load_registry(hub.ROOT)["hooks"] if h["id"] == "own:file-guard")
        (home / ".claude/settings.json").write_text(json.dumps(
            {"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": cmd}]}]}}), encoding="utf-8")
        result = self.go()
        self.assertEqual("global", result["hooks"]["conflicts"][0]["where"])
        self.assertNotIn(cmd, self.commands())

    def test_rollback_restores_settings(self):
        original = json.dumps({"permissions": {"allow": ["Bash(ls)"]}}, indent=2)
        (self.p / ".claude").mkdir()
        (self.p / ".claude/settings.json").write_text(original, encoding="utf-8")
        result = self.go()
        self.assertTrue(result["backup"])
        self.assertTrue(any("model_guard" in c for c in self.commands()))
        out = rollback(self.p, result["backup"])
        self.assertIn(".claude/settings.json", out["restored"])
        self.assertEqual(original, (self.p / ".claude/settings.json").read_text(encoding="utf-8"))

    def test_verify_guards(self):
        self.go()
        out = hm.verify(hub.ROOT, self.p)
        for hid in ("own:model-guard", "own:command-guard", "own:file-guard", "own:usage-tracker"):
            self.assertEqual("pass", out["results"][hid]["status"], out["results"][hid])
        self.assertTrue(out["ok"])


if __name__ == "__main__":
    unittest.main()


class ToggleRollbackTests(unittest.TestCase):
    def test_disable_then_rollback_restores_hook_and_state(self):
        import json as _json
        from scripts import hooks_manager as hm, project_install as pi, hub as _hub
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
            target = Path(tmp)
            pi.install(_hub.ROOT, target, profile="core", fetch_external=False, runtime_scan=False, home=home)
            hm.set_enabled(_hub.ROOT, target, "own:command-guard", True)
            settings = target / ".claude/settings.json"
            self.assertIn("command_guard", settings.read_text(encoding="utf-8"))
            result = hm.set_enabled(_hub.ROOT, target, "own:command-guard", False)
            self.assertIsNotNone(result["backup"])
            self.assertNotIn("command_guard", settings.read_text(encoding="utf-8"))
            pi.rollback(target)
            self.assertIn("command_guard", settings.read_text(encoding="utf-8"))
            state = target / ".agent-hub/hooks.json"
            disabled = _json.loads(state.read_text(encoding="utf-8")).get("disabled", []) if state.is_file() else []
            self.assertNotIn("own:command-guard", disabled)


class RegistryWithoutEccTests(unittest.TestCase):
    def test_registry_equal_ignores_ecc_entries_without_checkout(self):
        from scripts import hooks_manager as hm
        stored = {"schema": 1, "hooks": [{"id": "own:x", "source": "own", "files": []},
                                         {"id": "ecc:y", "source": "ECC", "files": [{"path": "a", "sha256": "1"}]}]}
        built = {"schema": 1, "hooks": [{"id": "own:x", "source": "own", "files": []}]}
        self.assertTrue(hm.registry_equal(stored, built, ignore_ecc_sha=True))
        self.assertFalse(hm.registry_equal(stored, built, ignore_ecc_sha=False))
        changed = {"schema": 1, "hooks": [{"id": "own:x", "source": "own", "files": [{"path": "b"}]}]}
        self.assertFalse(hm.registry_equal(stored, changed, ignore_ecc_sha=True))
