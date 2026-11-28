import copy
import tempfile
import unittest
from pathlib import Path

from scripts import hub, model_policy as mp

GOOD_SETTINGS = {
    "model": "opus",
    "env": {"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"},
    "hooks": {"PreToolUse": [mp.GUARD_ENTRY]},
}


def agent(model, effort="medium"):
    head = "model: %s\n" % model if model else ""
    head += "effort: %s\n" % effort if effort else ""
    return "---\nname: x\ndescription: d\n%sskills:\n  - a\n---\nbody\n" % head


class AgentTests(unittest.TestCase):
    def check(self, agents):
        with tempfile.TemporaryDirectory() as tmp:
            for name, model in agents.items():
                (Path(tmp) / (name + ".md")).write_text(agent(model), encoding="utf-8")
            return mp.validate_agents(tmp)

    def check_eff(self, orch, **efforts):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "orchestrator.md").write_text(agent("opus", orch), encoding="utf-8")
            for name, effort in efforts.items():
                (Path(tmp) / (name + ".md")).write_text(agent("haiku", effort), encoding="utf-8")
            return mp.validate_agents(tmp)

    def test_effort_rules(self):
        self.assertEqual([], self.check_eff("high", a="low", b="medium", c="high"))
        self.assertEqual([], self.check_eff("medium", a="low"))
        for bad in (None, "xhigh", "max", "ultra"):
            with self.subTest(executor=bad):
                self.assertTrue(self.check_eff("high", a=bad))
        for bad in (None, "low", "xhigh", "max"):
            with self.subTest(orchestrator=bad):
                self.assertTrue(self.check_eff(bad, a="low"))

    def test_policy_effort_keys(self):
        policy = mp.load_json(hub.ROOT / "MODEL_POLICY.json")
        self.assertEqual("medium", policy["default_executor_effort"])
        for key, value in (("executor_efforts", ["low", "xhigh"]), ("executor_efforts", ["low", "low"]),
                           ("executor_efforts", []), ("default_executor_effort", "high-ish"),
                           ("executor_efforts", ["low"]), ("default_executor_effort", 1)):
            with self.subTest(key=key, value=value):
                self.assertTrue(mp.validate_policy(dict(policy, **{key: value})))

    def test_valid_including_haiku(self):
        self.assertEqual([], self.check({"orchestrator": "opus", "a": "sonnet", "b": "haiku"}))

    def test_rejections(self):
        for bad in ("opus", "inherit", None, "claude-sonnet-5-5", "fable", "Sonnet"):
            with self.subTest(model=bad):
                self.assertTrue(self.check({"orchestrator": "opus", "a": bad}))

    def test_second_opus_and_non_opus_orchestrator(self):
        self.assertTrue(self.check({"orchestrator": "opus", "a": "opus"}))
        self.assertTrue(self.check({"orchestrator": "sonnet", "a": "sonnet"}))

    def test_real_agents(self):
        self.assertEqual([], mp.validate_agents(hub.ROOT / ".claude/agents"))
        haiku = {p.stem for p in (hub.ROOT / ".claude/agents").glob("*.md")
                 if mp.parse_model(p.read_text(encoding="utf-8")) == "haiku"}
        self.assertEqual(haiku, {"asset-validator", "documentation-keeper", "localization-agent",
                                 "memory-curator", "researcher"})


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = mp.load_json(hub.ROOT / "MODEL_POLICY.json")

    def test_real_policy_valid(self):
        self.assertEqual([], mp.validate_policy(self.policy))

    def test_bad_policies(self):
        cases = [("max_parallel_agents", 4), ("max_parallel_agents", True), ("allow_inherit", 0),
                 ("allow_executor_opus", True), ("max_retries", 3), ("default_parallel_agents", 0),
                 ("orchestrator", "sonnet"), ("executors", ["sonnet", "sonnet"]),
                 ("executors", ["sonnet", "haiku", "opus"]), ("max_retries", "2")]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                self.assertTrue(mp.validate_policy(dict(self.policy, **{key: value})))
        self.assertTrue(mp.validate_policy(dict(self.policy, extra=1)))
        missing = dict(self.policy)
        del missing["max_retries"]
        self.assertTrue(mp.validate_policy(missing))
        self.assertTrue(mp.validate_policy(dict(self.policy, default_parallel_agents=3, max_parallel_agents=2)))


class SettingsTests(unittest.TestCase):
    def test_good(self):
        self.assertEqual([], mp.validate_settings(GOOD_SETTINGS, hub.ROOT))
        self.assertEqual([], mp.validate_settings(mp.load_json(hub.ROOT / ".claude/settings.json"), hub.ROOT))
        self.assertEqual([], mp.validate_settings(dict(GOOD_SETTINGS, env={"CLAUDE_CODE_SUBAGENT_MODEL": "haiku"})))

    def test_subagent_env(self):
        for env in ({}, {"CLAUDE_CODE_SUBAGENT_MODEL": "opus"}, {"CLAUDE_CODE_SUBAGENT_MODEL": "claude-sonnet-5-5"}):
            with self.subTest(env=env):
                self.assertTrue(mp.validate_settings(dict(GOOD_SETTINGS, env=env)))
        self.assertTrue(mp.validate_settings({k: v for k, v in GOOD_SETTINGS.items() if k != "env"}))

    def test_forbidden_env_model_and_hook(self):
        for key in mp.FORBIDDEN_ENV:
            env = dict(GOOD_SETTINGS["env"], **{key: "x"})
            self.assertTrue(mp.validate_settings(dict(GOOD_SETTINGS, env=env)), key)
        self.assertTrue(mp.validate_settings(dict(GOOD_SETTINGS, model="sonnet")))
        self.assertTrue(mp.validate_settings({k: v for k, v in GOOD_SETTINGS.items() if k != "hooks"}))
        narrow = copy.deepcopy(GOOD_SETTINGS)
        narrow["hooks"]["PreToolUse"][0]["matcher"] = "Agent"
        self.assertTrue(mp.validate_settings(narrow))

    def test_missing_hook_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(any("Missing hook file" in e for e in mp.validate_settings(GOOD_SETTINGS, tmp)))

    def test_runtime_env(self):
        self.assertEqual([], mp.check_runtime_env({}))
        self.assertEqual([], mp.check_runtime_env({"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"}))
        self.assertTrue(mp.check_runtime_env({"CLAUDE_CODE_SUBAGENT_MODEL": "opus"}))
        self.assertTrue(mp.check_runtime_env({"ANTHROPIC_MODEL": "x"}))


class PinTests(unittest.TestCase):
    def test_real_repo_pins(self):
        self.assertEqual([], hub.check_external_pins(hub.ROOT, []))


if __name__ == "__main__":
    unittest.main()
