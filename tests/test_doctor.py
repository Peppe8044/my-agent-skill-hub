import json
import unittest
from unittest.mock import patch

from scripts import doctor, hub
from scripts.doctor import _Result


class Recorder:
    def __init__(self, docker_ok=False):
        self.calls, self.docker_ok = [], docker_ok

    def __call__(self, args, timeout=15):
        self.calls.append(list(args))
        if args[0] == "docker" and not self.docker_ok:
            return _Result(1, "", "cannot connect")
        if args[:2] == ["git", "config"]:
            return _Result(0, "true\n")
        if args[0] == "gh":
            return _Result(1, "secret output", "")
        if args[:2] == ["git", "-C"] and args[3] == "submodule":
            return _Result(0, "-abc external/a\n abc external/b\n")
        return _Result(0, "ok 1.0\n")


def run(runner, environ=None):
    return doctor.doctor(hub.ROOT, lambda notes: [], runner=runner, environ=environ or {},
                         which=lambda n: None, http_get=lambda url, t: json.dumps({"version": "0.1"}),
                         godot_finder=lambda: (None, "not found"))


def status(checks, name):
    return next(c for c in checks if c["name"] == name)["status"]


class DoctorTests(unittest.TestCase):
    def test_docker_down_warns_and_gh_output_hidden(self):
        runner = Recorder()
        checks = run(runner)
        self.assertEqual("WARN", status(checks, "docker-engine"))
        self.assertEqual("WARN", status(checks, "submodules"))
        self.assertEqual("WARN", status(checks, "godot"))
        self.assertNotIn("secret", json.dumps(checks))
        self.assertFalse(any(c["status"] == "FAIL" for c in checks))
        self.assertFalse(any("ollama" in call[0] for call in runner.calls))
        self.assertTrue(all(isinstance(a, str) for call in runner.calls for a in call))
        self.assertEqual("OK", status(checks, "ollama"))

    def test_forbidden_env_fails(self):
        self.assertEqual("FAIL", status(run(Recorder(True), {"ANTHROPIC_MODEL": "x"}), "model-env"))
        self.assertEqual("OK", status(run(Recorder(True)), "docker-engine"))

    def test_missing_binaries(self):
        def missing(args, timeout=15):
            raise FileNotFoundError(args[0])
        checks = run(missing)
        self.assertEqual("WARN", status(checks, "claude"))
        self.assertEqual("FAIL", status(checks, "git"))

    def test_cli_exit_codes(self):
        with patch("scripts.doctor.doctor", return_value=[{"name": "x", "status": "FAIL", "detail": "d"}]):
            self.assertEqual(1, hub.main(["doctor"]))
        with patch("scripts.doctor.doctor", return_value=[{"name": "x", "status": "WARN", "detail": "d"}]):
            self.assertEqual(0, hub.main(["doctor", "--json"]))

    def test_godot_lookup(self):
        self.assertEqual((None, "GODOT_BIN points to a missing path: /nope"),
                         doctor.find_godot({"GODOT_BIN": "/nope"}, lambda n: None))
        self.assertEqual(("/bin/godot", "PATH"), doctor.find_godot({}, lambda n: "/bin/godot"))


if __name__ == "__main__":
    unittest.main()
