import importlib.util
import json
import os
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


class GuardTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = Path(self._tmp.name)
        (self.project / ".claude/agents").mkdir(parents=True)
        (self.project / ".claude/agents/scout.md").write_text(
            "---\nname: scout\nmodel: haiku\n---\nx\n", encoding="utf-8")
        (self.project / ".claude/agents/big.md").write_text(
            "---\nname: big\nmodel: opus\n---\nx\n", encoding="utf-8")

    def run_hook(self, payload, raw=False):
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
            self.assertAllowed(self.run_hook(agent_call(subagent_type="general-purpose", model=model)))
        self.assertAllowed(self.run_hook({"tool_name": "Task", "tool_input": {"model": "haiku"}}))

    def test_no_model(self):
        self.assertAllowed(self.run_hook(agent_call(subagent_type="scout")))
        proc = self.run_hook(agent_call(subagent_type="general-purpose"))
        self.assertDenied(proc)
        self.assertIn("pass model: sonnet or haiku explicitly", proc.stderr)
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
        for name in ("researcher", "code-reviewer"):
            proc = call(hub.ROOT, agent_call(subagent_type=name))
            self.assertEqual(0, proc.returncode, proc.stderr)


if __name__ == "__main__":
    unittest.main()


class BudgetTests(unittest.TestCase):
    def _session(self, tmp, per_message, messages):
        project = Path(tmp) / "p"
        (project / ".claude/agents").mkdir(parents=True)
        (project / "MODEL_POLICY.json").write_text(json.dumps(
            {"executors": ["sonnet", "haiku"], "max_executor_tokens_per_session": 1000}), encoding="utf-8")
        transcript = Path(tmp) / "s.jsonl"
        transcript.write_text("{}\n", encoding="utf-8")
        sub = Path(tmp) / "s" / "subagents"
        sub.mkdir(parents=True)
        lines = []
        for i in range(messages):
            line = json.dumps({"type": "assistant", "message": {"id": "m%d" % i, "usage": {
                "input_tokens": per_message, "output_tokens": 0, "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 99999}}})
            lines += [line, line]  # same message id twice: counted once
        (sub / "agent-a.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return project, str(transcript)

    def run_guard(self, project, transcript):
        payload = {"tool_name": "Agent", "transcript_path": transcript,
                   "tool_input": {"subagent_type": "general-purpose", "model": "haiku"}}
        return call(project, payload)

    def test_budget_blocks_new_delegations_when_exhausted(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, transcript = self._session(tmp, 600, 2)  # 1200 >= 1000 (cache reads ignored)
            proc = self.run_guard(project, transcript)
            self.assertEqual(2, proc.returncode)
            self.assertIn("budget", proc.stderr)

    def test_budget_allows_under_limit_and_dedupes(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, transcript = self._session(tmp, 400, 2)  # 800 < 1000 although lines are duplicated
            self.assertEqual(0, self.run_guard(project, transcript).returncode)

    def test_budget_not_measurable_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = self._session(tmp, 600, 2)
            self.assertEqual(0, self.run_guard(project, str(Path(tmp) / "missing.jsonl")).returncode)

