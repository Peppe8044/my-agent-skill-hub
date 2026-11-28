import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import hub, model_policy as mp

HOOK = hub.ROOT / ".claude/hooks/model_guard.py"


def load_hook_module():
    spec = importlib.util.spec_from_file_location("model_guard", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def call(project, payload, raw=False):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
    data = payload if raw else json.dumps(payload)
    return subprocess.run([sys.executable, str(HOOK)], input=data, capture_output=True,
                          text=True, env=env, timeout=30)


def agent_call(**tool_input):
    return {"tool_name": "Agent", "tool_input": tool_input}


def with_skill(project, name="token-budget"):
    path = Path(project) / ".claude/skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nname: %s\n---\nx\n" % name, encoding="utf-8")


class GuardTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = Path(self._tmp.name)
        (self.project / ".claude/agents").mkdir(parents=True)
        (self.project / ".claude/agents/scout.md").write_text(
            "---\nname: scout\nmodel: haiku\nskills:\n  - token-budget\n---\nx\n", encoding="utf-8")
        (self.project / ".claude/agents/big.md").write_text(
            "---\nname: big\nmodel: opus\nskills:\n  - token-budget\n---\nx\n", encoding="utf-8")
        (self.project / ".claude/agents/plain.md").write_text(
            "---\nname: plain\nmodel: haiku\n---\nx\n", encoding="utf-8")
        with_skill(self.project)
        self.transcript = Path(self._tmp.name) / "s.jsonl"
        self.transcript.write_text("{}\n", encoding="utf-8")

    def run_hook(self, payload, raw=False):
        if isinstance(payload, dict) and payload.get("tool_name") in ("Agent", "Task"):
            payload = dict(payload, session_id="s", transcript_path=str(self.transcript))
        return call(self.project, payload, raw)

    def assertDenied(self, proc):
        self.assertEqual(2, proc.returncode, proc.stderr)
        self.assertIn("MODEL_POLICY.json", proc.stderr)

    def assertAllowed(self, proc):
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual("", proc.stdout)

    def test_denied_models(self):
        for model in ("opus", "fable", "inherit", "claude-sonnet-5-5"):
            with self.subTest(model=model):
                self.assertDenied(self.run_hook(agent_call(subagent_type="scout", model=model)))

    def test_policy_file_cannot_widen_executors(self):
        (self.project / "MODEL_POLICY.json").write_text(
            json.dumps({"executors": ["sonnet", "haiku", "opus"]}), encoding="utf-8")
        self.assertDenied(self.run_hook(agent_call(subagent_type="scout", model="opus")))
        self.assertAllowed(self.run_hook(agent_call(subagent_type="scout", model="haiku")))
        (self.project / "MODEL_POLICY.json").write_text(
            json.dumps({"executors": ["opus"]}), encoding="utf-8")
        self.assertDenied(self.run_hook(agent_call(subagent_type="scout", model="haiku")))

    def test_effort_denied_for_xhigh_and_max(self):
        for effort in ("xhigh", "max"):
            with self.subTest(effort=effort):
                self.assertDenied(self.run_hook(agent_call(subagent_type="scout", model="haiku", effort=effort)))
        for effort in ("low", "medium", "high"):
            self.assertAllowed(self.run_hook(agent_call(subagent_type="scout", model="haiku", effort=effort)))

    def test_allowed_models(self):
        for model in ("sonnet", "haiku"):
            self.assertAllowed(self.run_hook(agent_call(subagent_type="scout", model=model)))
        self.assertAllowed(self.run_hook({"tool_name": "Task", "tool_input": {"subagent_type": "scout"}}))

    def test_builtins_denied_even_with_model(self):
        for name in ("general-purpose", "Explore", "Plan"):
            proc = self.run_hook(agent_call(subagent_type=name, model="haiku"))
            self.assertDenied(proc)
            self.assertIn("not a project agent", proc.stderr)
        self.assertDenied(self.run_hook({"tool_name": "Task", "tool_input": {"model": "haiku"}}))

    def test_mandatory_skills_required(self):
        proc = self.run_hook(agent_call(subagent_type="plain"))
        self.assertDenied(proc)
        self.assertIn("mandatory skills token-budget", proc.stderr)
        (self.project / "MODEL_POLICY.json").write_text(
            json.dumps({"mandatory_agent_skills": ["documentation-ledger"]}), encoding="utf-8")
        self.assertDenied(self.run_hook(agent_call(subagent_type="scout")))  # needs both skills
        (self.project / "MODEL_POLICY.json").write_text(json.dumps({"mandatory_agent_skills": []}), encoding="utf-8")
        self.assertAllowed(self.run_hook(agent_call(subagent_type="scout")))
        (self.project / ".claude/skills/token-budget/SKILL.md").unlink()  # declared but not installed
        self.assertDenied(self.run_hook(agent_call(subagent_type="scout")))

    def test_no_model(self):
        self.assertAllowed(self.run_hook(agent_call(subagent_type="scout")))
        proc = self.run_hook(agent_call(subagent_type="general-purpose"))
        self.assertDenied(proc)
        self.assertIn("not a project agent", proc.stderr)
        self.assertDenied(self.run_hook(agent_call(subagent_type="big")))
        self.assertDenied(self.run_hook(agent_call(subagent_type="../x")))
        self.assertDenied(self.run_hook(agent_call(prompt="x")))

    def test_fork_denied(self):
        self.assertDenied(self.run_hook(agent_call(subagent_type="fork", model="sonnet")))
        self.assertDenied(self.run_hook(agent_call(subagent_type="fork")))

    def test_malformed_denied(self):
        self.assertDenied(self.run_hook("{not json", raw=True))
        self.assertDenied(self.run_hook("[]", raw=True))
        self.assertDenied(self.run_hook({"tool_name": "Agent", "tool_input": "x"}))

    def test_other_tools_allowed(self):
        self.assertAllowed(self.run_hook({"tool_name": "Bash", "tool_input": {"command": "ls"}}))

    def test_regex_parity_over_real_agents(self):
        mod = load_hook_module()
        self.assertEqual(mp.MODEL_RE.pattern, mod.MODEL_RE.pattern)
        for path in sorted((hub.ROOT / ".claude/agents").glob("*.md")):
            with self.subTest(agent=path.stem):
                self.assertEqual(mp.parse_model(path.read_text(encoding="utf-8")), mod.agent_model(str(path)))

    def test_real_agents_via_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "p"
            shutil.copytree(hub.ROOT / ".claude/agents", project / ".claude/agents")
            shutil.copytree(hub.ROOT / ".claude/skills", project / ".claude/skills")
            shutil.copy(hub.ROOT / "MODEL_POLICY.json", project / "MODEL_POLICY.json")
            transcript = Path(tmp) / "s.jsonl"
            transcript.write_text("{}\n", encoding="utf-8")
            for name in ("researcher", "code-reviewer"):
                payload = {"tool_name": "Agent", "session_id": "s", "transcript_path": str(transcript),
                           "tool_input": {"subagent_type": name}}
                proc = call(project, payload)
                self.assertEqual(0, proc.returncode, proc.stderr)


if __name__ == "__main__":
    unittest.main()



class BudgetTests(unittest.TestCase):
    POLICY = {"executors": ["sonnet", "haiku"], "max_parallel_agents": 2,
              "executor_budget_per_phase": 1000, "executor_budget_per_session": 1000,
              "executor_budget_reserve_per_active": 100,
              "budget_weights": {"input": 1, "output": 1, "cache_creation": 1, "cache_read": 0.1}}

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.project = self.root / "p"
        (self.project / ".claude/agents").mkdir(parents=True)
        (self.project / "MODEL_POLICY.json").write_text(json.dumps(self.POLICY), encoding="utf-8")
        (self.project / ".claude/agents/worker.md").write_text(
            "---\nname: worker\nmodel: haiku\nskills:\n  - token-budget\n---\nx\n", encoding="utf-8")
        with_skill(self.project)

    def session(self, sid, per_message=0, messages=0, cache_read=0, running=0):
        transcript = self.root / (sid + ".jsonl")
        transcript.write_text("{}\n", encoding="utf-8")
        sub = self.root / sid / "subagents"
        sub.mkdir(parents=True, exist_ok=True)
        lines = []
        for i in range(messages):
            line = json.dumps({"type": "assistant", "message": {"id": "m%d" % i, "usage": {
                "input_tokens": per_message, "output_tokens": 0, "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": cache_read}}})
            lines += [line, line]  # the same message on two lines is counted once
        (sub / "agent-a.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (sub / "agent-a.meta.json").write_text(json.dumps({"finished": True}), encoding="utf-8")
        for r in range(running):
            (sub / ("agent-r%d.meta.json" % r)).write_text("{}", encoding="utf-8")
        return str(transcript)

    def delegate(self, transcript, sid):
        return call(self.project, {"tool_name": "Agent", "session_id": sid, "transcript_path": transcript,
                                   "tool_input": {"subagent_type": "worker", "model": "haiku"}})

    def budget(self, *args):
        return subprocess.run([sys.executable, str(HOOK), "--budget", *args, "--project", str(self.project)],
                              capture_output=True, text=True, timeout=30)

    def status(self):
        return json.loads(self.budget("status").stdout)

    def test_weighted_categories_counted_once(self):
        t = self.session("s1", per_message=200, messages=2, cache_read=1000)  # 2 x (200 + 0.1 x 1000)
        self.assertEqual(0, self.delegate(t, "s1").returncode)
        record = self.status()["sessions"]["s1"]
        self.assertEqual(600, record["weighted"])
        self.assertEqual({"input": 400, "output": 0, "cache_creation": 0, "cache_read": 2000}, record["usage"])

    def test_session_budget_with_reserve(self):
        self.assertEqual(0, self.delegate(self.session("s1", per_message=450, messages=2), "s1").returncode)
        proc = self.delegate(self.session("s2", per_message=460, messages=2), "s2")  # 920 + 100 > 1000
        self.assertEqual(2, proc.returncode)
        self.assertIn("budget", proc.stderr)

    def test_phase_budget_survives_a_new_session(self):
        t1 = self.session("s1")
        self.assertEqual(0, self.delegate(t1, "s1").returncode)
        self.session("s1", per_message=475, messages=2)  # the executor of s1 then used 950
        proc = self.delegate(self.session("s2"), "s2")
        self.assertEqual(2, proc.returncode)
        self.assertIn("phase", proc.stderr)

    def test_running_executors_reserve_and_max_parallel(self):
        self.assertEqual(0, self.delegate(self.session("s1", per_message=300, messages=2, running=1), "s1").returncode)
        proc = self.delegate(self.session("s3", running=2), "s3")
        self.assertEqual(2, proc.returncode)
        self.assertIn("max_parallel_agents", proc.stderr)

    def test_unmeasurable_blocks_until_recovery(self):
        missing = str(self.root / "missing.jsonl")
        proc = self.delegate(missing, "sx")
        self.assertEqual(2, proc.returncode)
        self.assertIn("authorize-recovery", proc.stderr)
        self.assertEqual(0, self.budget("authorize-recovery", "1").returncode)
        self.assertEqual(0, self.delegate(missing, "sx").returncode)
        self.assertEqual(2, self.delegate(missing, "sx").returncode)

    def test_missing_budget_keys_use_central_defaults(self):
        (self.project / "MODEL_POLICY.json").write_text(json.dumps({"executors": ["haiku"]}), encoding="utf-8")
        self.assertEqual(0, self.delegate(self.session("s1", per_message=20000, messages=2), "s1").returncode)
        proc = self.delegate(self.session("s2", per_message=21000, messages=2), "s2")  # 42000 + 10000 > 50000
        self.assertEqual(2, proc.returncode)
        self.assertEqual(50000, self.status()["phase_budget"])

    def test_start_phase_and_keep_if_same(self):
        t = self.session("s1", per_message=100, messages=1)
        self.delegate(t, "s1")
        self.budget("start-phase", "5")
        self.assertEqual(("5", {}), (self.status()["phase"], self.status()["sessions"]))
        self.delegate(t, "s1")
        self.budget("start-phase", "5", "--keep-if-same")
        self.assertIn("s1", self.status()["sessions"])
