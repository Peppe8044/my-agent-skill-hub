"""Environment diagnostics: read-only, no shell=True, injectable runner."""
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

try:
    from . import model_policy as mp
except ImportError:
    import model_policy as mp


class _Result:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def default_runner(args, timeout=15):
    """Run a command (list args). Raises FileNotFoundError/TimeoutExpired to the caller."""
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)
    return _Result(proc.returncode, proc.stdout or "", proc.stderr or "")


def default_http_get(url, timeout=3):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def steam_godot_candidates():
    """Godot executables inside Steam libraries (Windows only)."""
    if sys.platform != "win32":
        return []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            steam = Path(winreg.QueryValueEx(key, "SteamPath")[0])
    except (ImportError, OSError):
        return []
    libraries = [steam]
    vdf = steam / "steamapps" / "libraryfolders.vdf"
    try:
        libraries += [Path(p.replace("\\\\", "\\")) for p in
                      re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="replace"))]
    except OSError:
        pass
    found = []
    for lib in libraries:
        found += sorted((lib / "steamapps" / "common" / "Godot Engine").glob("*.exe"))
    return found


def find_godot(environ, which, steam=steam_godot_candidates):
    configured = environ.get("GODOT_BIN")
    if configured:
        return (configured, "GODOT_BIN") if Path(configured).exists() else (None, f"GODOT_BIN points to a missing path: {configured}")
    for name in ("godot", "godot4", "godot.exe"):
        hit = which(name)
        if hit:
            return hit, "PATH"
    hits = steam()
    if hits:
        return str(hits[0]), "Steam library"
    return None, "not found (set GODOT_BIN, add to PATH, or install via Steam)"


def doctor(root, validate_fn, runner=None, environ=None, which=None, http_get=None,
           platform=None, godot_finder=None):
    runner = runner or default_runner
    environ = os.environ if environ is None else environ
    which = which or shutil.which
    http_get = http_get or default_http_get
    platform = platform or sys.platform
    checks = []

    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail})

    def run(args, timeout=15):
        try:
            return runner(args, timeout=timeout)
        except FileNotFoundError:
            return None
        except (subprocess.SubprocessError, OSError):
            return None

    notes = []
    errors = validate_fn(notes)
    add("validate", "FAIL" if errors else "OK",
        f"{len(errors)} error(s): " + "; ".join(errors[:3]) if errors else "library structure and policies pass"
        + (" (" + "; ".join(notes) + ")" if notes else ""))
    v = sys.version_info
    add("python", "OK" if v >= (3, 10) else "FAIL", f"{v.major}.{v.minor}.{v.micro}")
    r = run(["git", "--version"])
    add("git", "OK" if r and r.returncode == 0 else "FAIL", (r.stdout.strip() if r and r.returncode == 0 else "git not available"))
    r = run(["git", "-C", str(root), "submodule", "status"], 30)
    if r is None or r.returncode != 0:
        add("submodules", "WARN", "git submodule status unavailable")
    else:
        lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
        bad = [ln[1:].split()[1] for ln in lines if ln[0] in "+U" and len(ln[1:].split()) > 1]
        uninit = [ln[1:].split()[1] for ln in lines if ln[0] == "-" and len(ln[1:].split()) > 1]
        if bad:
            add("submodules", "FAIL", "modified or conflicted: " + ", ".join(bad))
        elif uninit:
            add("submodules", "WARN", f"{len(uninit)} not initialized (run install with fetch to init)")
        else:
            add("submodules", "OK", f"{len(lines)} initialized at pinned commits")
    r = run(["claude", "--version"])
    add("claude", "OK" if r and r.returncode == 0 else "WARN",
        r.stdout.strip() if r and r.returncode == 0 else "claude CLI not available")
    r = run(["gh", "auth", "status"])
    if r is None:
        add("gh", "WARN", "gh not available")
    else:
        add("gh", "OK" if r.returncode == 0 else "WARN", "authenticated: " + ("yes" if r.returncode == 0 else "no"))
    r = run(["docker", "info", "--format", "{{.ServerVersion}}"], 20)
    if r and r.returncode == 0 and r.stdout.strip():
        add("docker-engine", "OK", "server " + r.stdout.strip())
    else:
        add("docker-engine", "WARN", "docker engine unreachable")
    r = run(["docker", "compose", "version", "--short"], 20)
    add("docker-compose", "OK" if r and r.returncode == 0 else "WARN",
        r.stdout.strip() if r and r.returncode == 0 else "docker compose not available")
    try:
        version = json.loads(http_get("http://127.0.0.1:11434/api/version", 3)).get("version", "unknown")
        add("ollama", "OK", f"HTTP API reachable, version {version}")
    except (OSError, ValueError, AttributeError):
        add("ollama", "WARN", "HTTP API not reachable at 127.0.0.1:11434 (CLI is never invoked)")
    finder = godot_finder or (lambda: find_godot(environ, which))
    path, how = finder()
    add("godot", "OK" if path else "WARN", f"{path} ({how})" if path else how)
    problems = mp.check_runtime_env(environ)
    add("model-env", "FAIL" if problems else "OK", "; ".join(problems) if problems else "no overriding model variables")
    if platform == "win32":
        r = run(["git", "config", "core.longpaths"])
        longpaths = bool(r and r.returncode == 0 and r.stdout.strip().lower() == "true")
        add("git-longpaths", "OK" if longpaths else "WARN",
            "core.longpaths=true" if longpaths else "core.longpaths is not true (git config core.longpaths true)")
    if "onedrive" in str(root).lower():
        add("repo-path", "WARN", "repository is inside OneDrive; sync can corrupt git state or lock files")
    else:
        add("repo-path", "OK", str(root))
    return checks


def format_checks(checks):
    return "\n".join(f"[{c['status']}] {c['name']}: {c['detail']}" for c in checks)
