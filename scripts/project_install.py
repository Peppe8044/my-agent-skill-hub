"""Project-local installation; never execute upstream code automatically."""
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

try:
    from .integrations import approved_files, mcp_config
    from . import model_policy as mp
except ImportError:
    from integrations import approved_files, mcp_config
    import model_policy as mp

MERGED = (".mcp.json", ".claude/settings.json")
INCOMING = ".agent-hub/incoming"


class PolicyConflictError(ValueError):
    """Project configuration conflicts with the model policy; nothing was written."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def default_home():
    return Path.home()


def default_runner(args, cwd=None, env=None, timeout=120):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


# ---------------------------------------------------------------- MCP helpers
def norm_name(name):
    name = str(name).lower().strip()
    if name.startswith("claude.ai "):
        name = name[len("claude.ai "):]
    return re.sub(r"[^a-z0-9]", "", name)


def norm_url(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not re.match(r"(?i)^https?://", value):
        return None
    parts = urlsplit(value)
    return f"{parts.scheme.lower()}://{(parts.netloc or '').lower()}{parts.path.rstrip('/')}"


def parse_mcp_list(text):
    """Parse `claude mcp list` lines `name: target - status` into {name: target}."""
    found = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("checking mcp"):
            continue
        name, sep, rest = line.partition(": ")
        if not sep:
            continue
        target = rest.rpartition(" - ")[0] if " - " in rest else rest
        found[name.strip()] = target.strip()
    return found


def _read_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _entry(config):
    if isinstance(config, dict):
        return norm_url(config.get("url"))
    return None


def existing_servers(target, home, runtime_scan, runner, which):
    """Return ({scope: {name: normalized_url|None}}, runtime_scan_status)."""
    scopes = {"project": {}, "local": {}, "user": {}, "runtime": {}}
    claude_json = _read_json(Path(home) / ".claude.json") or {}
    user = claude_json.get("mcpServers")
    for name, cfg in (user.items() if isinstance(user, dict) else []):
        scopes["user"][name] = _entry(cfg)
    projects = claude_json.get("projects")
    if isinstance(projects, dict):
        for spelling in {str(target), str(target).replace("\\", "/"), str(target).replace("/", "\\")}:
            local = (projects.get(spelling) or {}).get("mcpServers") if isinstance(projects.get(spelling), dict) else None
            for name, cfg in (local.items() if isinstance(local, dict) else []):
                scopes["local"][name] = _entry(cfg)
    status = "skipped"
    if runtime_scan and which("claude"):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        try:
            proc = runner([which("claude"), "mcp", "list"], cwd=str(target) if Path(target).is_dir() else None,
                          env=env, timeout=120)
            if proc.returncode != 0:
                status = f"unavailable: claude mcp list exited {proc.returncode}"
            else:
                for name, tgt in parse_mcp_list(proc.stdout or "").items():
                    scopes["runtime"][name] = norm_url(tgt.split()[0]) if tgt else None
                status = "ok"
        except subprocess.TimeoutExpired:
            status = "unavailable: timeout"
        except (OSError, subprocess.SubprocessError) as exc:
            status = f"unavailable: {type(exc).__name__}"
    return scopes, status


def plan_mcp(target, desired, home, runtime_scan, runner, which):
    mcp_path = Path(target) / ".mcp.json"
    project_cfg, project_servers = {}, {}
    if mcp_path.exists():
        try:
            project_cfg = json.loads(mcp_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ValueError(f"Invalid JSON in existing .mcp.json: {exc}")
        project_servers = project_cfg.get("mcpServers", {}) if isinstance(project_cfg, dict) else None
        if not isinstance(project_cfg, dict) or not isinstance(project_servers, dict):
            raise ValueError("Existing .mcp.json must be an object with an mcpServers object")
    scopes, scan = existing_servers(target, home, runtime_scan, runner, which)
    scopes["project"] = {n: _entry(c) for n, c in project_servers.items()}
    report = {"added": [], "skipped": {}, "preserved": sorted(project_servers), "conflicts": [],
              "runtime_scan": scan}
    for name, cfg in desired.items():
        if name in project_servers:
            if project_servers[name] != cfg:
                report["conflicts"].append(f"{name}: project config differs from hub config; kept project config")
            continue
        url, hit = _entry(cfg), None
        for scope in ("project", "local", "user", "runtime"):
            for other, other_url in scopes[scope].items():
                if norm_name(other) == norm_name(name) or (url and other_url == url):
                    hit = f"{scope}:{other}"
                    break
            if hit:
                break
        if hit:
            report["skipped"][name] = f"duplicate of {hit}"
        else:
            report["added"].append(name)
    new_cfg = None
    if report["added"]:
        new_cfg = dict(project_cfg)
        servers = dict(project_servers)
        for name in report["added"]:
            servers[name] = desired[name]
        new_cfg["mcpServers"] = servers
    return report, new_cfg


# ------------------------------------------------------------ settings merge
def merge_settings(existing_bytes, hub_bytes, previous_digest):
    """Return (new_bytes_or_None, status, problems)."""
    if existing_bytes is None:
        return hub_bytes, "created", []
    if previous_digest is not None and digest(existing_bytes) == previous_digest:
        return (None if existing_bytes == hub_bytes else hub_bytes), "unchanged" if existing_bytes == hub_bytes else "updated", []
    try:
        settings = json.loads(existing_bytes.decode("utf-8"))
    except ValueError as exc:
        return None, "invalid", [f"Invalid JSON in .claude/settings.json: {exc}"]
    if not isinstance(settings, dict):
        return None, "invalid", [".claude/settings.json must be a JSON object"]
    problems = []
    original = json.dumps(settings, sort_keys=True)
    if "model" not in settings:
        settings["model"] = "opus"
    elif settings["model"] != "opus":
        problems.append(f"Policy conflict: project settings model is {settings['model']!r}, policy requires opus")
    env = settings.get("env")
    if env is None:
        env = settings["env"] = {}
    if not isinstance(env, dict):
        problems.append("Policy conflict: settings env is not an object")
    else:
        for key in mp.FORBIDDEN_ENV:
            if key in env:
                problems.append(f"Policy conflict: project settings env sets forbidden {key}")
        if mp.SUBAGENT_ENV not in env:
            env[mp.SUBAGENT_ENV] = "sonnet"
        elif env[mp.SUBAGENT_ENV] not in mp.EXECUTORS:
            problems.append(f"Policy conflict: project settings env.{mp.SUBAGENT_ENV} is {env[mp.SUBAGENT_ENV]!r}, policy allows only sonnet or haiku")
    if not mp.has_model_guard(settings):
        hooks = settings.setdefault("hooks", {})
        if not isinstance(hooks, dict) or not isinstance(hooks.setdefault("PreToolUse", []), list):
            problems.append("Policy conflict: settings hooks.PreToolUse is not a list")
        else:
            hooks["PreToolUse"].append(json.loads(json.dumps(mp.GUARD_ENTRY)))
    if problems:
        return None, "conflict", problems
    if json.dumps(settings, sort_keys=True) == original:
        return None, "unchanged", []
    return (json.dumps(settings, indent=2, ensure_ascii=False) + "\n").encode("utf-8"), "merged", []


def install(root, target, profile="full", fetch_external=True, *, home=None,
            runtime_scan=True, runner=None, which=None):
    root, target = Path(root).resolve(), Path(target).resolve()
    if target == root or root in target.parents and target.parent != root / "workspaces":
        # Nested workspaces are supported, but never overwrite the hub itself.
        if target == root or root / "external" in target.parents:
            raise ValueError("Unsafe installation target")
    if profile not in {"full", "core"}:
        raise ValueError("Unknown installation profile")
    home = default_home() if home is None else home
    runner = runner or default_runner
    which = which or shutil.which
    if fetch_external and profile == "full":
        subprocess.run(["git", "-C", str(root), "submodule", "update", "--init"], check=True)
    files = {}
    def add(rel, data):
        files[str(rel).replace("\\", "/")] = data
    for rel in ("AGENTS.md", "CLAUDE.md", "MODEL_POLICY.json", mp.HOOK_REL):
        add(rel, (root / rel).read_bytes())
    for src in sorted((root / ".claude/agents").glob("*.md")):
        add(src.relative_to(root), src.read_bytes())
    for folder in ("skills",):
        for src in sorted((root / folder).glob("*/SKILL.md")):
            for runtime in (".claude/skills", ".agents/skills"):
                add(f"{runtime}/{src.parent.name}/SKILL.md", src.read_bytes())
    if profile == "full":
        for rel, data in approved_files(root).items():
            if rel in files:
                raise ValueError("External skill conflicts with hub skill: " + rel)
            add(rel, data)
    catalog = []
    if profile == "full":
        for repo in sorted((root / "external").iterdir()) if (root / "external").exists() else []:
            if not repo.is_dir() or repo.is_symlink():
                continue
            for src in sorted(repo.rglob("SKILL.md")):
                if src.is_symlink() or not src.is_file() or ".git" in src.relative_to(repo).parts:
                    continue
                catalog.append({"source": repo.name, "path": src.relative_to(repo).as_posix(), "status": "review-required"})
    add(".agent-hub/external-catalog.json", (json.dumps(catalog, indent=2)+"\n").encode())
    add(".agent-hub/README.md", b"# Agent Hub\nOwn agents and skills are installed. External catalog entries require review before activation; MCP services need their own setup. Start Claude with: claude --agent orchestrator --model opus\n")
    manifest_path = target / ".agent-hub/manifest.json"
    def safe_path(rel):
        p = target / rel
        if not p.resolve().is_relative_to(target) or any(q.is_symlink() for q in [p, *p.parents] if q != target and target in q.parents):
            raise ValueError(f"Unsafe path: {rel}")
        return p
    safe_path(".agent-hub/manifest.json")
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": {}}
    prev_files = previous.get("files", {})

    # --- preflight: settings and MCP (nothing is written if this fails)
    settings_path = safe_path(".claude/settings.json")
    if settings_path.exists() and not settings_path.is_file():
        raise ValueError("Unsafe path: .claude/settings.json")
    existing_settings = settings_path.read_bytes() if settings_path.exists() else None
    new_settings, settings_status, problems = merge_settings(
        existing_settings, (root / ".claude/settings.json").read_bytes(), prev_files.get(".claude/settings.json"))
    if problems:
        raise PolicyConflictError("Install stopped, nothing written: " + "; ".join(problems))
    mcp_report = {"added": [], "skipped": {}, "preserved": [], "conflicts": [], "runtime_scan": "skipped"}
    new_mcp = None
    mcp_path = safe_path(".mcp.json")
    if mcp_path.exists() and not mcp_path.is_file():
        raise ValueError("Unsafe path: .mcp.json")
    if profile == "full":
        mcp_report, new_mcp = plan_mcp(target, mcp_config(root)["mcpServers"], home, runtime_scan, runner, which)
    conflicts = []
    for rel, data in files.items():
        p = safe_path(rel)
        if p.exists() and not p.is_file():
            raise ValueError(f"Unsafe path: {rel}")
        if p.exists() and p.read_bytes() != data and prev_files.get(rel) != digest(p.read_bytes()):
            conflicts.append(rel)
    for rel in conflicts:
        safe_path(f"{INCOMING}/{rel}")

    # --- write
    for rel, data in files.items():
        if rel in conflicts:
            inc = safe_path(f"{INCOMING}/{rel}")
            inc.parent.mkdir(parents=True, exist_ok=True)
            inc.write_bytes(data)
            continue
        p = safe_path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists() or p.read_bytes() != data:
            p.write_bytes(data)
    if new_settings is not None:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_bytes(new_settings)
    if new_mcp is not None:
        mcp_path.write_text(json.dumps(new_mcp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    incoming_root = target / INCOMING
    if incoming_root.is_dir():
        for stale in sorted(incoming_root.rglob("*"), reverse=True):
            rel = stale.relative_to(incoming_root).as_posix()
            if stale.is_file() and not stale.is_symlink() and rel not in conflicts:
                stale.unlink()
            elif stale.is_dir() and not any(stale.iterdir()):
                stale.rmdir()
    merged = [rel for rel in MERGED if (target / rel).is_file()]
    manifest_files = {k: digest(v) for k, v in files.items() if k not in conflicts}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"profile": profile, "files": manifest_files, "merged": merged}, indent=2)+"\n", encoding="utf-8")
    return {"installed_files": len(manifest_files), "external_candidates": len(catalog),
            "external_activation": "review-required", "target": str(target),
            "conflicts": sorted(conflicts), "settings": settings_status, "mcp": mcp_report}
