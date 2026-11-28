#!/usr/bin/env python3
"""Per-project Agent Memory (rohitg00/agentmemory) config and local service management.

Local only: 127.0.0.1, no LLM/embedding provider keys, no capture hooks, no global state.
The engine home (~/.agentmemory/bin) is redirected into <project>/.agent-hub/memory/home.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request
import zlib
from pathlib import Path

HOST = "127.0.0.1"
MEM_REL = ".agent-hub/memory"
GITIGNORE_LINES = (".agent-hub/memory/",)
SERVER_NAME = "agentmemory"
PORT_BASE, PORT_SLOTS, PORT_STEP = 3200, 100, 10   # REST N, viewer N+2, engine ws N+46023
SECRET_ENV = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY",
              "VOYAGE_API_KEY", "COHERE_API_KEY", "MINIMAX_API_KEY", "AGENTMEMORY_SECRET",
              "AGENTMEMORY_LLM_PROVIDER", "EMBEDDING_PROVIDER")


def mem_dir(target):
    return Path(target).resolve() / MEM_REL


def checkout(root):
    return Path(root).resolve() / "external" / "agentmemory"


def _port_free(port):
    for p in (port, port + 2, port + 46023):
        with socket.socket() as s:
            try:
                s.bind((HOST, p))
            except OSError:
                return False
    return True


def pick_port(target, taken=(), free=_port_free):
    """Deterministic per-project port (hash of the path), skipping ports in use or already taken."""
    start = zlib.crc32(str(Path(target).resolve()).lower().encode()) % PORT_SLOTS
    for i in range(PORT_SLOTS):
        port = PORT_BASE + ((start + i) % PORT_SLOTS) * PORT_STEP
        if port not in taken and free(port):
            return port
    raise RuntimeError("no free port for agentmemory")


def read_config(target):
    path = mem_dir(target) / "config.json"
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
        return cfg if isinstance(cfg, dict) and isinstance(cfg.get("port"), int) else None
    except (OSError, ValueError):
        return None


def mcp_entry(root, target, port):
    return {"command": "node",
            "args": [str(checkout(root) / "dist" / "cli.mjs"), "mcp"],
            "env": {"AGENTMEMORY_URL": f"http://{HOST}:{port}",
                    "AGENTMEMORY_DATA_DIR": str(mem_dir(target) / "data"),
                    "AGENTMEMORY_TOOLS": "core"}}


def _merge_mcp(path, entry):
    cfg = {}
    if path.exists():
        cfg = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(cfg, dict) or not isinstance(cfg.get("mcpServers", {}), dict):
            raise ValueError("Existing .mcp.json must be an object with an mcpServers object")
    servers = cfg.setdefault("mcpServers", {})
    if servers.get(SERVER_NAME) == entry:
        return False
    servers[SERVER_NAME] = entry
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def _merge_gitignore(path):
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    missing = [x for x in GITIGNORE_LINES if x not in lines]
    if missing:
        path.write_text("\n".join(lines + missing) + "\n", encoding="utf-8")
    return bool(missing)


def configure(root, target, port=None, taken=()):
    """Idempotent: config.json (port kept once chosen), .mcp.json entry, .gitignore lines. Never starts the service."""
    target = Path(target).resolve()
    md = mem_dir(target)
    for sub in ("data", "home"):
        (md / sub).mkdir(parents=True, exist_ok=True)
    old = read_config(target)
    port = port or (old or {}).get("port") or pick_port(target, taken)
    if not 1024 <= int(port) <= 19000:
        raise ValueError("port must be between 1024 and 19000")
    new = {"host": HOST, "port": int(port), "data_dir": "data", "home_dir": "home", "tools": "core",
           "llm_provider": None, "embeddings": "off", "capture_hooks": False}
    if old != new:
        (md / "config.json").write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
    mcp = _merge_mcp(target / ".mcp.json", mcp_entry(root, target, new["port"]))
    gi = _merge_gitignore(target / ".gitignore")
    return {"port": new["port"], "mcp_changed": mcp, "gitignore_changed": gi, "config_changed": old != new}


# ---- service management ----
def _pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out.split()
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def health(port, timeout=2):
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://{HOST}:{port}/agentmemory/livez", timeout=timeout) as r:
            return r.status == 200
    except (OSError, ValueError):
        return False


def listener_pids(port, run=subprocess.run):
    """PIDs listening on the REST, viewer and engine ports (the CLI daemonizes, so the launcher pid is not enough)."""
    ports = {port, port + 2, port + 46023}
    found = set()
    try:
        if os.name == "nt":
            out = run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True).stdout
            for line in out.splitlines():
                f = line.split()
                if len(f) >= 5 and f[3] == "LISTENING" and f[1].startswith(HOST + ":") and f[1].rsplit(":", 1)[1].isdigit()                         and int(f[1].rsplit(":", 1)[1]) in ports and f[4].isdigit():
                    found.add(int(f[4]))
        else:
            for p in ports:
                out = run(["lsof", "-t", f"-iTCP@{HOST}:{p}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout
                found.update(int(x) for x in out.split() if x.isdigit())
    except OSError:
        pass
    return sorted(found)


def _read_pids(target):
    try:
        d = json.loads((mem_dir(target) / "memory.pid").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    pids = d.get("pids") or [d.get("pid")]
    return [x for x in pids if isinstance(x, int)]


def status(target, alive=_pid_alive, probe=health):
    cfg = read_config(target)
    if not cfg:
        return {"state": "unconfigured", "port": None, "pid": None}
    pids = _read_pids(target)
    pid = pids[0] if pids else None
    up = probe(cfg["port"])
    if any(alive(x) for x in pids):
        state = "running" if up else "starting-or-unhealthy"
    else:
        state = "running-untracked" if up else ("stale-pid" if pid is not None else "stopped")
    return {"state": state, "port": cfg["port"], "pid": pid, "pids": pids, "healthy": up, "url": f"http://{HOST}:{cfg['port']}"}


def service_env(target, cfg, environ=None):
    env = {k: v for k, v in (environ or os.environ).items() if k not in SECRET_ENV}
    md = mem_dir(target)
    home = str(md / cfg.get("home_dir", "home"))
    env.update({"USERPROFILE": home, "HOME": home, "AGENTMEMORY_DATA_DIR": str(md / cfg.get("data_dir", "data")),
                "AGENTMEMORY_ENV_FILE": str(md / "home" / ".env"), "AGENTMEMORY_TOOLS": "core",
                "AGENTMEMORY_AUTO_COMPRESS": "false", "AGENTMEMORY_INJECT_CONTEXT": "false",
                "AGENTMEMORY_URL": f"http://{HOST}:{cfg['port']}"})
    return env


def start(root, target, popen=subprocess.Popen, wait=60, sleep=time.sleep):
    cfg = read_config(target)
    if not cfg:
        raise ValueError("memory not configured; run bootstrap/update or `memory configure`")
    st = status(target)
    if st["state"] in ("running", "running-untracked"):
        return {**st, "action": "already-running"}
    cli = checkout(root) / "dist" / "cli.mjs"
    node = shutil.which("node")
    if not cli.is_file() or not node:
        raise RuntimeError(f"missing {'node' if not node else cli}; build with: "
                           "cd external/agentmemory && npm install --ignore-scripts && npm run build")
    md = mem_dir(target)
    cmd = [node, str(cli), "--port", str(cfg["port"]), "--data-dir", str(md / cfg["data_dir"]), "--tools", "core"]
    kw = {"cwd": str(md), "env": service_env(target, cfg), "stdin": subprocess.DEVNULL}
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    with open(md / "memory.log", "ab") as log:
        proc = popen(cmd, stdout=log, stderr=log, **kw)
    (md / "memory.pid").write_text(json.dumps({"pid": proc.pid, "port": cfg["port"], "started": time.time()}),
                                   encoding="utf-8")
    for _ in range(wait):
        if health(cfg["port"]):
            pids = sorted({proc.pid, *listener_pids(cfg["port"])})
            (md / "memory.pid").write_text(json.dumps({"pid": proc.pid, "pids": pids, "port": cfg["port"],
                                                       "started": time.time()}), encoding="utf-8")
            return {**status(target), "action": "started"}
        sleep(1)
    return {**status(target), "action": "started-not-healthy-yet"}


def _kill_tree(pid):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        import signal
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass


def _cli_stop(root, target, run=subprocess.run):
    """Official `agentmemory stop` (reaps the Worker Compose daemon, which is not a listener); best effort."""
    cfg, node = read_config(target), shutil.which("node")
    cli = checkout(root) / "dist" / "cli.mjs"
    if not (cfg and node and cli.is_file()):
        return False
    try:
        cmd = [node, str(cli), "stop", "--port", str(cfg["port"]), "--data-dir", str(mem_dir(target) / cfg["data_dir"])]
        return run(cmd, env=service_env(target, cfg), cwd=str(mem_dir(target)), capture_output=True, timeout=90,
                   stdin=subprocess.DEVNULL).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def stop(root, target, alive=_pid_alive, kill=_kill_tree, sleep=time.sleep, cli_stop=_cli_stop,
         listeners=listener_pids):
    pids = _read_pids(target)
    cli_stop(root, target)
    # A stale pid file (e.g. after a reboot) may name a reused pid: only kill pids that still
    # listen on this project's ports.
    cfg = read_config(target)
    owned = set(listeners(cfg["port"])) if cfg else set()
    pids = [p for p in pids if p in owned]
    for pid in pids:
        if alive(pid):
            kill(pid)
    for _ in range(10):
        if not any(alive(x) for x in pids):
            break
        sleep(0.5)
    (mem_dir(target) / "memory.pid").unlink(missing_ok=True)
    return {"state": "stopped", "pids": pids}


def recover(root, target, **kw):
    """Stop (kills a live tree), remove stale pid/lock files, then start again."""
    stop(root, target)
    md = mem_dir(target)
    removed = []
    for name in ("memory.pid", "data/compose/worker-compose.lock", "data/.lock", "data/lock", "data/LOCK"):
        p = md / name
        if p.is_file():
            p.unlink()
            removed.append(name)
    return {**start(root, target, **kw), "removed": removed}


def run(root, target, action):
    if action == "configure":
        return configure(root, target)
    if action == "status":
        return status(target)
    if action == "start":
        return start(root, target)
    if action == "stop":
        return stop(root, target)
    if action == "recover":
        return recover(root, target)
    raise ValueError(f"unknown action {action}")
