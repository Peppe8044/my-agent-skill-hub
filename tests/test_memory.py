import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import memory as m  # noqa: E402


class Proc:
    pid = 4242


class MemoryConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.p1, self.p2 = self.tmp / "p1", self.tmp / "p2"
        self.p1.mkdir()
        self.p2.mkdir()
        self.free = mock.patch.object(m, "_port_free", return_value=True)
        self.free.start()
        self.addCleanup(self.free.stop)

    def test_configure_idempotent_and_preserves_servers(self):
        (self.p1 / ".mcp.json").write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}))
        (self.p1 / ".gitignore").write_text("node_modules/\n")
        first = m.configure(ROOT, self.p1)
        second = m.configure(ROOT, self.p1)
        self.assertTrue(first["mcp_changed"] and first["gitignore_changed"])
        self.assertFalse(second["mcp_changed"] or second["gitignore_changed"] or second["config_changed"])
        servers = json.loads((self.p1 / ".mcp.json").read_text())["mcpServers"]
        self.assertEqual(set(servers), {"other", "agentmemory"})
        self.assertEqual(servers["agentmemory"]["env"]["AGENTMEMORY_URL"], f"http://127.0.0.1:{first['port']}")
        lines = (self.p1 / ".gitignore").read_text().splitlines()
        self.assertEqual(lines.count(".agent-hub/memory/"), 1)
        self.assertIn("node_modules/", lines)

    def test_no_secrets_or_provider_in_config(self):
        m.configure(ROOT, self.p1)
        text = (self.p1 / ".mcp.json").read_text() + (self.p1 / ".agent-hub/memory/config.json").read_text()
        self.assertNotIn("SECRET", text.upper().replace("AGENTMEMORY_DATA_DIR", ""))
        cfg = m.read_config(self.p1)
        self.assertEqual((cfg["host"], cfg["embeddings"], cfg["llm_provider"], cfg["capture_hooks"]),
                         ("127.0.0.1", "off", None, False))

    def test_isolation_distinct_dirs_and_ports(self):
        a = m.configure(ROOT, self.p1)
        b = m.configure(ROOT, self.p2, taken=(a["port"],))
        self.assertNotEqual(a["port"], b["port"])
        self.assertNotEqual(m.mem_dir(self.p1), m.mem_dir(self.p2))
        e1 = json.loads((self.p1 / ".mcp.json").read_text())["mcpServers"]["agentmemory"]["env"]
        e2 = json.loads((self.p2 / ".mcp.json").read_text())["mcpServers"]["agentmemory"]["env"]
        self.assertNotEqual(e1["AGENTMEMORY_DATA_DIR"], e2["AGENTMEMORY_DATA_DIR"])

    def test_port_kept_across_reconfigure_and_validated(self):
        port = m.configure(ROOT, self.p1)["port"]
        self.assertEqual(m.configure(ROOT, self.p1)["port"], port)
        with self.assertRaises(ValueError):
            m.configure(ROOT, self.p2, port=80)

    def test_invalid_mcp_json_is_not_overwritten(self):
        (self.p1 / ".mcp.json").write_text("{bad")
        with self.assertRaises(ValueError):
            m.configure(ROOT, self.p1)
        self.assertEqual((self.p1 / ".mcp.json").read_text(), "{bad")

    def test_service_env_strips_keys_and_redirects_home(self):
        m.configure(ROOT, self.p1)
        cfg = m.read_config(self.p1)
        env = m.service_env(self.p1, cfg, {"ANTHROPIC_API_KEY": "k", "OPENAI_API_KEY": "k", "PATH": "p"})
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertEqual(env["AGENTMEMORY_AUTO_COMPRESS"], "false")
        self.assertTrue(env["USERPROFILE"].startswith(str(m.mem_dir(self.p1))))
        self.assertTrue(env["HOME"].startswith(str(m.mem_dir(self.p1))))


class MemoryServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.p = Path(self._tmp.name) / "p"
        self.p.mkdir()
        with mock.patch.object(m, "_port_free", return_value=True):
            m.configure(ROOT, self.p)
        self.md = m.mem_dir(self.p)

    def test_status_states(self):
        self.assertEqual(m.status(self.p, alive=lambda p: False, probe=lambda p: False)["state"], "stopped")
        (self.md / "memory.pid").write_text(json.dumps({"pid": 7}))
        self.assertEqual(m.status(self.p, alive=lambda p: False, probe=lambda p: False)["state"], "stale-pid")
        self.assertEqual(m.status(self.p, alive=lambda p: True, probe=lambda p: True)["state"], "running")
        self.assertEqual(m.status(self.p, alive=lambda p: True, probe=lambda p: False)["state"], "starting-or-unhealthy")
        self.assertEqual(m.status(Path(self._tmp.name) / "none", probe=lambda p: True)["state"], "unconfigured")

    def test_start_spawns_node_with_port_datadir_and_records_pid(self):
        popen = mock.Mock(return_value=Proc())
        with mock.patch.object(m, "health", return_value=True), \
                mock.patch.object(m.shutil, "which", return_value="node"), \
                mock.patch.object(m, "listener_pids", return_value=[4243]), \
                mock.patch.object(m, "checkout", return_value=ROOT / "scripts"), \
                mock.patch.object(Path, "is_file", return_value=True):
            with mock.patch.object(m, "_pid_alive", return_value=False):
                res = m.start(ROOT, self.p, popen=popen, wait=1, sleep=lambda s: None)
        cmd = popen.call_args[0][0]
        port = m.read_config(self.p)["port"]
        self.assertIn(str(port), cmd)
        self.assertIn("--data-dir", cmd)
        self.assertEqual(popen.call_args[1]["env"]["AGENTMEMORY_DATA_DIR"], str(self.md / "data"))
        self.assertEqual(json.loads((self.md / "memory.pid").read_text())["pids"], [4242, 4243])
        self.assertEqual(res["action"], "started")

    def test_start_requires_configuration_and_build(self):
        with self.assertRaises(ValueError):
            m.start(ROOT, Path(self._tmp.name) / "unconfigured")
        with mock.patch.object(m, "checkout", return_value=Path(self._tmp.name) / "nope"):
            with self.assertRaises(RuntimeError):
                m.start(ROOT, self.p, popen=mock.Mock())

    def test_stop_kills_all_pids_and_removes_pidfile(self):
        (self.md / "memory.pid").write_text(json.dumps({"pid": 1, "pids": [1, 2]}))
        kill = mock.Mock()
        state = {"n": 0}

        def alive(pid):
            state["n"] += 1
            return state["n"] <= 2
        res = m.stop(ROOT, self.p, alive=alive, kill=kill, sleep=lambda s: None, cli_stop=mock.Mock(),
                     listeners=lambda port: [1, 2])
        self.assertEqual(kill.call_count, 2)
        self.assertEqual(res["state"], "stopped")
        self.assertFalse((self.md / "memory.pid").exists())

    def test_stop_never_kills_reused_pid(self):
        (self.md / "memory.pid").write_text(json.dumps({"pids": [4242]}))
        kill = mock.Mock()
        m.stop(ROOT, self.p, alive=lambda pid: True, kill=kill, sleep=lambda s: None, cli_stop=mock.Mock(),
               listeners=lambda port: [])
        kill.assert_not_called()
        self.assertFalse((self.md / "memory.pid").exists())

    def test_recover_removes_stale_pid_and_lock_then_starts(self):
        (self.md / "memory.pid").write_text(json.dumps({"pid": 9}))
        lock = self.md / "data/compose/worker-compose.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("x")
        with mock.patch.object(m, "stop"), mock.patch.object(m, "_pid_alive", return_value=False), \
                mock.patch.object(m, "start", return_value={"action": "started"}) as st:
            res = m.recover(ROOT, self.p)
        self.assertFalse(lock.exists())
        self.assertIn("data/compose/worker-compose.lock", res["removed"])
        st.assert_called_once()

    def test_listener_pids_parses_netstat_for_loopback_ports_only(self):
        out = ("  TCP    127.0.0.1:3430         0.0.0.0:0              LISTENING       11\n"
               "  TCP    0.0.0.0:3432           0.0.0.0:0              LISTENING       12\n"
               "  TCP    127.0.0.1:49453        0.0.0.0:0              LISTENING       13\n"
               "  TCP    127.0.0.1:9999         0.0.0.0:0              LISTENING       14\n")
        fake = mock.Mock(return_value=mock.Mock(stdout=out))
        with mock.patch.object(m.os, "name", "nt"):
            self.assertEqual(m.listener_pids(3430, run=fake), [11, 13])


if __name__ == "__main__":
    unittest.main()
