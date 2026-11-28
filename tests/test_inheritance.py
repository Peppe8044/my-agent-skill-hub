"""The central model and token rules reach new and existing projects (isolated temp projects).

Checks the files and, more importantly, the behaviour: the installed model_guard hook is run
against each project to prove delegation, mandatory skills and the budget are enforced.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import hub, model_policy as mp
from scripts.bootstrap import launch, update, verify_project
from scripts.project_install import digest, install
from tests.support import Isolated

GUARD = ".claude/hooks/model_guard.py"


def load_catalog():
    spec = importlib.util.spec_from_file_location("catalog_under_test", hub.ROOT / "templates/agent-hub/catalog.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InheritanceTests(Isolated, unittest.TestCase):
    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def delegate(self, project, agent, sid="s1", used=0, running=0, **tool_input):
        transcript = self.tmp / (sid + ".jsonl")
        transcript.write_text("{}\n", encoding="utf-8")
        sub = self.tmp / sid / "subagents"
        sub.mkdir(parents=True, exist_ok=True)
        if used:
            row = {"message": {"id": "m", "usage": {"input_tokens": used}}}
            (sub / "agent-a.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            (sub / "agent-a.meta.json").write_text('{"finished": true}', encoding="utf-8")
        for r in range(running):
            (sub / ("agent-r%d.meta.json" % r)).write_text("{}", encoding="utf-8")
        payload = {"tool_name": "Agent", "session_id": sid, "transcript_path": str(transcript),
                   "tool_input": dict(subagent_type=agent, **tool_input)}
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
        return subprocess.run([sys.executable, str(project / GUARD)], input=json.dumps(payload),
                              capture_output=True, text=True, env=env, timeout=30)

    def assert_inherited(self, project):
        self.assertEqual((hub.ROOT / GUARD).read_bytes(), (project / GUARD).read_bytes())
        policy = json.loads((project / "MODEL_POLICY.json").read_text(encoding="utf-8"))
        self.assertEqual([], mp.validate_policy(policy))
        self.assertIn("token-budget", policy["mandatory_agent_skills"])
        settings = json.loads((project / ".claude/settings.json").read_text(encoding="utf-8"))
        self.assertTrue(mp.has_model_guard(settings))
        self.assertIn("SubagentStop", settings.get("hooks", {}))  # usage measured per executor
        for runtime in (".claude/skills", ".agents/skills"):
            self.assertEqual((hub.ROOT / "skills/token-budget/SKILL.md").read_bytes(),
                             (project / runtime / "token-budget/SKILL.md").read_bytes())
        present = {p.parent.name for p in (project / ".claude/skills").glob("*/SKILL.md")}
        for agent in sorted((project / ".claude/agents").glob("*.md")):
            self.assertEqual([], hub.check_agent_skills(agent, present, set(policy["mandatory_agent_skills"])))
        orchestrator = (project / ".claude/agents/orchestrator.md").read_text(encoding="utf-8")
        self.assertEqual("medium", mp.parse_effort(orchestrator))
        self.assertTrue((project / ".agent-hub/bin/phase_report.py").is_file())
        self.assertEqual([], verify_project(project))

    def assert_enforced(self, project):
        self.assertEqual(0, self.delegate(project, "researcher").returncode)
        self.assertEqual(2, self.delegate(project, "general-purpose", model="haiku").returncode)
        self.assertEqual(2, self.delegate(project, "researcher", model="opus").returncode)
        spent = self.delegate(project, "researcher", sid="s2", used=45000)
        self.assertEqual(2, spent.returncode)
        self.assertIn("budget", spent.stderr)

    def test_new_projects_of_every_kind_inherit_and_enforce(self):
        for kind in hub.PROJECT_KINDS:
            with self.subTest(kind=kind):
                project = hub.new_project("demo-" + kind, kind, directory=self.tmp / "new")
                self.assert_inherited(project)
                self.assert_enforced(project)

    def test_game_project_install_inherits_and_phase_survives_new_session(self):
        project = self.tmp / "game"
        project.mkdir()
        (project / "project.godot").write_text("config_version=5\n", encoding="utf-8")
        install(hub.ROOT, project, "core", fetch_external=False)
        self.assert_inherited(project)
        self.assertEqual(0, self.delegate(project, "researcher", sid="a").returncode)
        row = {"message": {"id": "m", "usage": {"input_tokens": 42000}}}  # that executor then spent 42000
        (self.tmp / "a/subagents/agent-a.jsonl").write_text(json.dumps(row) + chr(10), encoding="utf-8")
        (self.tmp / "a/subagents/agent-a.meta.json").write_text('{"finished": true}', encoding="utf-8")
        blocked = self.delegate(project, "researcher", sid="b")  # new session, same phase
        self.assertEqual(2, blocked.returncode)
        self.assertIn("phase", blocked.stderr)

    def test_existing_project_update_preserves_tunables_and_restores_central_rules(self):
        project = self.tmp / "existing"
        project.mkdir()
        install(hub.ROOT, project, "core", fetch_external=False)
        # An outdated agent written by an older hub (manifest digest matches) lacks token-budget.
        agent = project / ".claude/agents/researcher.md"
        old = agent.read_text(encoding="utf-8").replace("  - token-budget\n", "").encode("utf-8")
        agent.write_bytes(old)
        manifest_path = project / ".agent-hub/manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"][".claude/agents/researcher.md"] = digest(old)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        denied = self.delegate(project, "researcher")
        self.assertEqual(2, denied.returncode)
        self.assertIn("mandatory skills", denied.stderr)
        # The project customised its policy: a tunable value and some central keys.
        policy = json.loads((project / "MODEL_POLICY.json").read_text(encoding="utf-8"))
        policy.update(executor_budget_per_phase=20000, executors=["sonnet", "haiku", "opus"], max_parallel_agents=3)
        del policy["mandatory_agent_skills"]
        (project / "MODEL_POLICY.json").write_text(json.dumps(policy), encoding="utf-8")
        report = update(hub.ROOT, project)
        self.assertEqual([], report["static_errors"])
        self.assertEqual(["executor_budget_per_phase"], report["installation"]["policy"]["preserved"])
        self.assertEqual(["executors", "max_parallel_agents"], report["installation"]["policy"]["reset_to_central"])
        merged = json.loads((project / "MODEL_POLICY.json").read_text(encoding="utf-8"))
        self.assertEqual(20000, merged["executor_budget_per_phase"])
        self.assertEqual(["sonnet", "haiku"], merged["executors"])
        self.assertEqual(2, merged["max_parallel_agents"])
        self.assert_inherited(project)
        self.assertEqual(0, self.delegate(project, "researcher").returncode)
        blocked = self.delegate(project, "researcher", sid="s3", used=15000)  # 15000 + 10000 > 20000
        self.assertEqual(2, blocked.returncode)
        update(hub.ROOT, project)  # a second update keeps the project's value
        self.assertEqual(20000, json.loads((project / "MODEL_POLICY.json").read_text(encoding="utf-8"))
                         ["executor_budget_per_phase"])

    def test_external_agents_get_mandatory_skills_when_enabled(self):
        catalog = load_catalog()
        skills = ["token-budget", "documentation-ledger"]
        samples = {
            "none": b"---\nname: ext-a\nmodel: haiku\n---\nbody\n",
            "block": b"---\nname: ext-a\nmodel: haiku\nskills:\n  - own-skill\n---\nbody\n",
            "inline": b"---\nname: ext-a\nmodel: haiku\nskills: [own-skill]\n---\nbody\n",
        }
        project = self.tmp / "ext"
        project.mkdir()
        install(hub.ROOT, project, "core", fetch_external=False)
        self.assertEqual(skills, catalog.mandatory_skills(project))
        for label, data in samples.items():
            with self.subTest(form=label):
                targets = catalog.enable_targets({"kind": "agent", "name": "ext-a"}, {"agent.md": data}, "medium", skills)
                text = targets[".claude/agents/ext-a.md"].decode("utf-8")
                for name in skills + (["own-skill"] if label != "none" else []):
                    self.assertIn("  - %s\n" % name, text)
                (project / ".claude/agents/ext-a.md").write_text(text, encoding="utf-8")
                self.assertEqual(0, self.delegate(project, "ext-a").returncode)
        (project / ".claude/agents/ext-a.md").write_bytes(samples["none"])  # bypassing enable
        self.assertEqual(2, self.delegate(project, "ext-a").returncode)

    def test_project_policy_cannot_widen_central_limits(self):
        project = self.tmp / "widen"
        project.mkdir()
        install(hub.ROOT, project, "core", fetch_external=False)
        (project / "MODEL_POLICY.json").write_text(json.dumps(
            {"executors": ["opus", "sonnet", "haiku"], "max_parallel_agents": 9, "mandatory_agent_skills": []}),
            encoding="utf-8")
        self.assertEqual(2, self.delegate(project, "researcher", model="opus").returncode)
        self.assertEqual(2, self.delegate(project, "researcher", sid="p2", running=2).returncode)  # capped at 2
        self.assertEqual(0, self.delegate(project, "researcher", sid="p1", running=1).returncode)
        spent = self.delegate(project, "researcher", sid="s9", used=45000)  # default budget applies
        self.assertEqual(2, spent.returncode)
        (project / ".claude/skills/token-budget/SKILL.md").unlink()  # token-budget is always required
        self.assertEqual(2, self.delegate(project, "researcher", sid="s10").returncode)

    @patch("scripts.bootstrap.subprocess.call", return_value=0)
    @patch("scripts.bootstrap.shutil.which", return_value="claude")
    def test_launch_applies_central_rules_first(self, which, call):
        project = self.tmp / "launch"
        project.mkdir()
        install(hub.ROOT, project, "core", fetch_external=False)
        policy = json.loads((project / "MODEL_POLICY.json").read_text(encoding="utf-8"))
        del policy["mandatory_agent_skills"]
        (project / "MODEL_POLICY.json").write_text(json.dumps(policy), encoding="utf-8")
        self.assertEqual(0, launch(project, {"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"}))
        self.assertIn("mandatory_agent_skills", json.loads((project / "MODEL_POLICY.json").read_text(encoding="utf-8")))
        self.assertIn("--effort", call.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
