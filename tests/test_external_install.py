"""External capability install, catalog helper, backup and rollback (fake hub, fake repos)."""
import hashlib
import json
import os
import stat
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import hub
from scripts.bootstrap import verify_project
from scripts.project_install import install, rollback
from tests.support import Isolated

REAL = hub.ROOT
AGENT_OK = "---\nname: helper\ndescription: Helps\nmodel: haiku\n---\nbody\n"
AGENT_BIG = "---\nname: big\ndescription: Big\nmodel: opus\n---\nbody\n"
OWN_AGENT = "---\nname: %s\ndescription: d\nmodel: %s\neffort: medium\nskills:\n  - a\n---\nbody\n"


def rm_git(path):
    def onerror(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onerror=onerror)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


def make_repo(path, files):
    path.mkdir(parents=True)
    git(path, "init", "-q")
    for rel, text in files.items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_bytes(text.encode())
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "x")
    return git(path, "rev-parse", "HEAD")


def skill_item(repo, repo_dir, name, tier, files, **extra):
    base = "skills/" + name
    item = {"id": f"{repo}--{name}", "name": name, "repo": repo, "path": base, "files": sorted(files),
            "sha256": {f: sha((repo_dir / base / f).read_bytes()) for f in files}, "license": "MIT",
            "domains": ["testing"], "tier": tier, "description": f"{name} does {name} things"}
    item.update(extra)
    return item


def build_hub(tmp):
    root = Path(tmp) / "hub"
    for rel in ("AGENTS.md", "CLAUDE.md", "MODEL_POLICY.json", ".claude/settings.json",
                ".claude/hooks/model_guard.py", "registry/integrations.json",
                "templates/agent-hub/catalog.py"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REAL / rel, root / rel)
    for name, model in (("orchestrator", "opus"), ("worker", "sonnet")):
        (root / ".claude/agents").mkdir(parents=True, exist_ok=True)
        text = OWN_AGENT % (name, model)
        (root / f".claude/agents/{name}.md").write_bytes((text).encode())
    (root / "skills/own-skill").mkdir(parents=True)
    (root / "skills/own-skill/SKILL.md").write_bytes(("---\nname: own-skill\ndescription: d\n---\nown\n").encode())
    repo_dir = root / "external/repoa"
    commit = make_repo(repo_dir, {
        "LICENSE": "MIT license text\n", "skills/alpha/SKILL.md": "# alpha\n", "skills/alpha/ref.md": "ref\n",
        "skills/beta/SKILL.md": "# beta\n", "skills/own-skill/SKILL.md": "# clash\n",
        "agents/helper.md": AGENT_OK, "agents/big.md": AGENT_BIG})
    bad_dir = root / "external/repob"
    bad_commit = make_repo(bad_dir, {"LICENSE": "GPL", "skills/zed/SKILL.md": "# zed\n"})
    registry = {
        "schema": 1, "generated_by": "scripts/external_scan.py",
        "repositories": {
            "repoa": {"commit": commit, "license": "MIT", "license_files": ["LICENSE"],
                      "redistribution": "allowed", "reason": "MIT"},
            "repob": {"commit": bad_commit, "license": "GPL", "license_files": ["LICENSE"],
                      "redistribution": "forbidden", "reason": "no redistribution"}},
        "skills": [skill_item("repoa", repo_dir, "alpha", "active", ["SKILL.md", "ref.md"]),
                   skill_item("repoa", repo_dir, "beta", "catalog", ["SKILL.md"]),
                   skill_item("repoa", repo_dir, "own-skill", "active", ["SKILL.md"]),
                   skill_item("repob", bad_dir, "zed", "active", ["SKILL.md"])],
        "agents": [
            {"id": "repoa--helper", "name": "helper", "repo": "repoa", "path": "agents/helper.md",
             "sha256": sha(AGENT_OK.encode()), "license": "MIT", "model": "haiku", "domains": ["testing"],
             "tier": "catalog", "description": "A helper agent"},
            {"id": "repoa--big", "name": "big", "repo": "repoa", "path": "agents/big.md",
             "sha256": sha(AGENT_BIG.encode()), "license": "MIT", "model": "haiku", "domains": ["testing"],
             "tier": "catalog", "description": "A big agent"}]}
    write_registry(root, registry)
    return root, registry


def write_registry(root, registry):
    path = root / "registry/external_capabilities.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(registry, indent=2)).encode())


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in Path(root).rglob("*") if p.is_file()}


class ExternalBase(Isolated, unittest.TestCase):
    real_external = True

    def setUp(self):
        super().setUp()
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.root, self.registry = build_hub(self._t.name)
        self.p = Path(self._t.name) / "proj"
        self.p.mkdir()

    def go(self, **kw):
        kw.setdefault("home", self._home.name)
        kw.setdefault("runtime_scan", False)
        return install(self.root, self.p, fetch_external=False, **kw)

    def catalog(self, *args):
        proc = subprocess.run([sys.executable, str(self.p / ".agent-hub/bin/catalog.py"), *args],
                              capture_output=True, text=True, encoding="utf-8", timeout=60)
        return proc.returncode, proc.stdout, proc.stderr

    def manifest(self):
        return json.loads((self.p / ".agent-hub/manifest.json").read_text(encoding="utf-8"))


class PlacementTests(ExternalBase):
    def test_placement_index_licenses_provenance(self):
        result = self.go()["external"]
        self.assertEqual("ok", result["status"])
        self.assertEqual((1, 1, 2), (result["active_skills"], result["catalog_skills"], result["catalog_agents"]))
        for runtime in (".claude/skills", ".agents/skills"):
            self.assertEqual(b"# alpha\n", (self.p / runtime / "alpha/SKILL.md").read_bytes())
            self.assertEqual(b"ref\n", (self.p / runtime / "alpha/ref.md").read_bytes())
            self.assertEqual(b"own\n".strip(), (self.p / runtime / "own-skill/SKILL.md").read_text(encoding="utf-8").splitlines()[-1].encode())
        self.assertFalse((self.p / ".claude/skills/beta").exists())
        self.assertTrue((self.p / ".agent-hub/catalog/skills/repoa--beta/SKILL.md").is_file())
        self.assertTrue((self.p / ".agent-hub/catalog/agents/repoa--helper.md").is_file())
        self.assertFalse((self.p / ".claude/agents/helper.md").exists())
        self.assertTrue((self.p / ".agent-hub/catalog/licenses/repoa/LICENSE").is_file())
        self.assertFalse((self.p / ".agent-hub/catalog/licenses/repob").exists())
        lines = (self.p / ".agent-hub/catalog/index.jsonl").read_text(encoding="utf-8").splitlines()
        entries = [json.loads(x) for x in lines]
        self.assertEqual(sorted(e["id"] for e in entries), [e["id"] for e in entries])
        self.assertEqual({"repoa--alpha", "repoa--beta", "repoa--big", "repoa--helper"}, {e["id"] for e in entries})
        alpha = next(e for e in entries if e["name"] == "alpha")
        self.assertEqual(["id", "kind", "name", "tier", "domains", "license", "repo", "commit", "path", "description"],
                         list(alpha))
        self.assertEqual(".claude/skills/alpha", alpha["path"])
        self.assertNotIn(" ", lines[0].split('"id":')[0])
        meta = self.manifest()["external"][".claude/skills/alpha/SKILL.md"]
        self.assertEqual(self.registry["repositories"]["repoa"]["commit"], meta["commit"])
        self.assertEqual({"repo", "commit", "source", "sha256", "license", "id"}, set(meta))
        self.assertEqual([], verify_project(self.p))

    def test_forbidden_tamper_and_mismatch_skipped(self):
        self.registry["skills"][1]["sha256"]["SKILL.md"] = "0" * 64
        write_registry(self.root, self.registry)
        skipped = self.go()["external"]["skipped"]
        self.assertIn("redistribution forbidden", skipped["repob--zed"])
        self.assertFalse((self.p / ".claude/skills/zed").exists())
        self.assertIn("collision", skipped["repoa--own-skill"])
        self.assertIn("sha256 mismatch", skipped["repoa--beta"])
        self.assertFalse((self.p / ".agent-hub/catalog/skills/repoa--beta").exists())
        self.assertTrue((self.p / ".claude/skills/alpha/SKILL.md").is_file())

    def test_commit_mismatch_and_dirty_checkout_skip_repo(self):
        good = self.registry["repositories"]["repoa"]["commit"]
        self.registry["repositories"]["repoa"]["commit"] = "1" * 40
        write_registry(self.root, self.registry)
        result = self.go()["external"]
        self.assertEqual(0, result["active_skills"])
        self.assertIn("differs from registry", result["skipped"]["repoa--alpha"])
        self.assertFalse((self.p / ".claude/skills/alpha").exists())
        self.registry["repositories"]["repoa"]["commit"] = good
        write_registry(self.root, self.registry)
        self.assertEqual(1, self.go()["external"]["active_skills"])
        (self.root / "external/repoa/skills/alpha/SKILL.md").write_bytes(b"# tampered\n")
        result = self.go()["external"]
        self.assertIn("not clean", result["skipped"]["repoa--alpha"])
        self.assertEqual(b"# alpha\n", (self.p / ".claude/skills/alpha/SKILL.md").read_bytes())

    def test_registry_missing_and_submodules_uninitialized(self):
        (self.root / "registry/external_capabilities.json").unlink()
        result = self.go()["external"]
        self.assertEqual("unavailable: registry missing", result["status"])
        self.assertTrue((self.p / ".claude/agents/orchestrator.md").is_file())
        write_registry(self.root, self.registry)
        rm_git(self.root / "external/repoa/.git")
        rm_git(self.root / "external/repob/.git")
        result = self.go()["external"]
        self.assertEqual("unavailable: submodules not initialized", result["status"])
        self.assertTrue((self.p / ".agent-hub/manifest.json").is_file())

    def test_unavailable_keeps_previously_installed_external_files(self):
        self.go()
        rm_git(self.root / "external/repoa/.git")
        rm_git(self.root / "external/repob/.git")
        before = tree(self.p)
        again = self.go()
        self.assertTrue(again["external"]["status"].startswith("unavailable"))
        self.assertEqual({k for k in before if k != ".agent-hub/manifest.json"},
                         {k for k in tree(self.p) if k != ".agent-hub/manifest.json"})
        self.assertIn(".claude/skills/alpha/SKILL.md", self.manifest()["files"])
        self.assertIn(".claude/skills/alpha/SKILL.md", self.manifest()["external"])

    def test_no_duplicate_names_and_project_skill_preserved(self):
        (self.p / ".claude/skills/alpha").mkdir(parents=True)
        (self.p / ".claude/skills/alpha/SKILL.md").write_bytes(b"mine\n")
        result = self.go()
        self.assertEqual(b"mine\n", (self.p / ".claude/skills/alpha/SKILL.md").read_bytes())
        self.assertFalse((self.p / ".claude/skills/alpha/ref.md").exists())
        self.assertIn(".claude/skills/alpha/SKILL.md", result["conflicts"])
        self.assertIn(".claude/skills/alpha/ref.md", result["conflicts"])
        self.assertTrue((self.p / ".agent-hub/incoming/.claude/skills/alpha/ref.md").is_file())
        self.assertTrue((self.p / ".agents/skills/alpha/SKILL.md").is_file())
        names = [d.name for d in (self.p / ".claude/skills").iterdir() if d.is_dir()]
        self.assertEqual(len(names), len(set(names)))


class CatalogHelperTests(ExternalBase):
    def setUp(self):
        super().setUp()
        self.go()

    def test_search_and_show(self):
        code, out, _ = self.catalog("search", "beta")
        self.assertEqual(0, code)
        lines = out.strip().splitlines()
        self.assertTrue(lines[0].startswith("repoa--beta | skill | testing | beta does beta things"))
        _, out, _ = self.catalog("search", "things", "--kind", "agent")
        self.assertEqual("", out.strip())
        _, out, _ = self.catalog("search", "helper", "--kind", "agent", "--domain", "testing", "--limit", "1")
        self.assertEqual(1, len(out.strip().splitlines()))
        code, out, _ = self.catalog("show", "repoa--beta")
        self.assertIn(".agent-hub/catalog/skills/repoa--beta", out)
        self.assertIn("license: MIT", out)
        self.assertNotIn("# beta", out)
        self.assertEqual(1, self.catalog("show", "nope")[0])

    def test_enable_disable_skill_and_agent(self):
        code, out, _ = self.catalog("enable", "repoa--beta")
        self.assertEqual(0, code)
        self.assertIn("new Claude Code session", out)
        for runtime in (".claude/skills", ".agents/skills"):
            self.assertTrue((self.p / runtime / "beta/SKILL.md").is_file())
        self.assertEqual(0, self.catalog("disable", "repoa--beta")[0])
        self.assertFalse((self.p / ".claude/skills/beta").exists())
        self.assertEqual(0, self.catalog("enable", "repoa--helper")[0])
        text = (self.p / ".claude/agents/helper.md").read_text(encoding="utf-8")
        self.assertIn("effort: medium", text)
        self.assertEqual([], verify_project(self.p))
        (self.p / ".claude/agents/helper.md").write_bytes((text + "edited\n").encode())
        code, _, err = self.catalog("disable", "repoa--helper")
        self.assertEqual(1, code)
        self.assertIn("modified", err)
        self.assertTrue((self.p / ".claude/agents/helper.md").is_file())

    def test_enable_refusals(self):
        code, _, err = self.catalog("enable", "repoa--big")
        self.assertEqual(1, code)
        self.assertIn("MODEL_POLICY.json", err)
        self.assertFalse((self.p / ".claude/agents/big.md").exists())
        (self.p / ".claude/agents/helper.md").write_bytes(("own\n").encode())
        self.assertEqual(1, self.catalog("enable", "repoa--helper")[0])
        (self.p / ".claude/skills/beta").mkdir(parents=True)
        self.assertEqual(1, self.catalog("enable", "repoa--beta")[0])
        self.assertFalse((self.p / ".agents/skills/beta").exists())

    def test_enabled_items_survive_and_update_on_reinstall(self):
        self.catalog("enable", "repoa--beta")
        self.assertEqual([], self.go()["conflicts"])
        self.assertIn(".claude/skills/beta/SKILL.md", self.manifest()["external"])
        repo = self.root / "external/repoa"
        (repo / "skills/beta/SKILL.md").write_bytes(("# beta v2\n").encode())
        git(repo, "commit", "-aqm", "v2")
        self.registry["repositories"]["repoa"]["commit"] = git(repo, "rev-parse", "HEAD")
        self.registry["skills"][1]["sha256"]["SKILL.md"] = sha(b"# beta v2\n")
        write_registry(self.root, self.registry)
        result = self.go()
        self.assertEqual([], result["conflicts"])
        self.assertEqual(b"# beta v2\n", (self.p / ".claude/skills/beta/SKILL.md").read_bytes())
        self.assertTrue(result["backup"])
        self.assertEqual(0, self.catalog("disable", "repoa--beta")[0])
        self.assertFalse((self.p / ".claude/skills/beta").exists())


class BackupTests(ExternalBase):
    def test_reinstall_is_idempotent(self):
        self.go()
        snapshot = tree(self.p)
        backups = self.p / ".agent-hub/backups"
        self.assertFalse(backups.exists())
        again = self.go()
        self.assertEqual([], again["conflicts"])
        self.assertIsNone(again["backup"])
        self.assertEqual(snapshot, tree(self.p))
        self.assertFalse(backups.exists())

    def test_backup_and_rollback_restore_unmodified_and_refuse_modified(self):
        self.go()
        (self.root / "AGENTS.md").write_bytes(("changed hub rules\n").encode())
        (self.root / "skills/own-skill/SKILL.md").write_bytes(("---\nname: own-skill\ndescription: d\n---\nv2\n").encode())
        original = (self.p / "AGENTS.md").read_bytes()
        result = self.go()
        self.assertTrue(result["backup"])
        self.assertEqual(b"changed hub rules\n", (self.p / "AGENTS.md").read_bytes())
        # the user edits one of the updated files afterwards
        (self.p / ".claude/skills/own-skill/SKILL.md").write_bytes(b"user edit\n")
        report = rollback(self.p)
        self.assertEqual(result["backup"], report["backup"])
        self.assertIn("AGENTS.md", report["restored"])
        self.assertEqual(original, (self.p / "AGENTS.md").read_bytes())
        self.assertEqual(b"user edit\n", (self.p / ".claude/skills/own-skill/SKILL.md").read_bytes())
        self.assertIn(".claude/skills/own-skill/SKILL.md", report["conflicts"])
        self.assertIn(".agents/skills/own-skill/SKILL.md", report["restored"])

    def test_rollback_removes_created_files_and_prunes_old_backups(self):
        self.go()
        (self.root / "skills/new-skill").mkdir()
        (self.root / "skills/new-skill/SKILL.md").write_bytes(("---\nname: new-skill\ndescription: d\n---\nn\n").encode())
        result = self.go()
        self.assertTrue((self.p / ".claude/skills/new-skill/SKILL.md").is_file())
        report = rollback(self.p, result["backup"])
        self.assertFalse((self.p / ".claude/skills/new-skill/SKILL.md").exists())
        self.assertIn(".claude/skills/new-skill/SKILL.md", report["removed"])
        self.assertNotIn(".claude/skills/new-skill/SKILL.md", self.manifest()["files"])
        base = self.p / ".agent-hub/backups"
        for n in range(7):
            (self.root / "AGENTS.md").write_bytes((f"rules {n}\n").encode())
            self.go()
        self.assertLessEqual(len(list(base.iterdir())), 5)
        with self.assertRaises(ValueError):
            rollback(self.p, "nope")


class ValidateRegistryTests(ExternalBase):
    def check(self):
        notes = []
        return hub.check_external_registry(self.root, notes), notes

    def test_good_and_bad_registry(self):
        errors, _ = self.check()
        # own-skill collision and the forbidden repo are expected to be flagged only for the collision
        self.assertTrue(any("collides" in e for e in errors), errors)
        self.registry["skills"] = [s for s in self.registry["skills"] if s["name"] not in ("own-skill", "zed")]
        write_registry(self.root, self.registry)
        self.assertEqual([], self.check()[0])
        self.registry["agents"][0]["model"] = "opus"
        write_registry(self.root, self.registry)
        self.assertTrue(any("not in executors" in e for e in self.check()[0]))
        self.registry["agents"][0]["model"] = "haiku"
        self.registry["skills"][0]["sha256"]["SKILL.md"] = "f" * 64
        write_registry(self.root, self.registry)
        self.assertTrue(any("sha256" in e for e in self.check()[0]))
        del self.registry["skills"]
        write_registry(self.root, self.registry)
        self.assertTrue(any("missing key" in e for e in self.check()[0]))

    def test_uninitialized_submodules_only_notes(self):
        self.registry["skills"] = [s for s in self.registry["skills"] if s["name"] not in ("own-skill", "zed")]
        write_registry(self.root, self.registry)
        for name in ("repoa", "repob"):
            rm_git(self.root / "external" / name / ".git")
        errors, notes = self.check()
        self.assertEqual([], errors)
        self.assertTrue(any("skipped" in n for n in notes))


if __name__ == "__main__":
    unittest.main()


class CatalogPathSafetyTests(unittest.TestCase):
    def test_enable_targets_rejects_unsafe_names_and_paths(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "catalog_helper", Path(__file__).resolve().parents[1] / "templates/agent-hub/catalog.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ok = mod.enable_targets({"name": "safe-skill", "kind": "skill"}, {"SKILL.md": b"x"})
        self.assertTrue(all("safe-skill" in k for k in ok))
        for name in ("../escape", "a/b", "C:evil", ""):
            with self.assertRaises(ValueError):
                mod.enable_targets({"name": name, "kind": "skill"}, {"SKILL.md": b"x"})
        for rel in ("../x.md", "/abs.md", "C:/x.md", "refs/../../x.md"):
            with self.assertRaises(ValueError):
                mod.enable_targets({"name": "safe-skill", "kind": "skill"}, {rel: b"x"})
