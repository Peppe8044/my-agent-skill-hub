"""Project-local installation; never execute upstream code automatically."""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit

try:
    from .integrations import approved_files, mcp_config, plan_external
    from . import model_policy as mp
    from . import hooks_manager as hm
except ImportError:
    import hooks_manager as hm
    from integrations import approved_files, mcp_config, plan_external
    import model_policy as mp

MERGED = (".mcp.json", ".claude/settings.json", "MODEL_POLICY.json")
POLICY_REL = "MODEL_POLICY.json"
INCOMING = ".agent-hub/incoming"
BACKUPS = ".agent-hub/backups"
ENABLED_REL = ".agent-hub/enabled.json"
CATALOG_TEMPLATE = "templates/agent-hub/catalog.py"


class PolicyConflictError(ValueError):
    """Project configuration conflicts with the model policy; nothing was written."""


def lp(path):
    """Extended-length path on Windows so deep catalog paths do not hit MAX_PATH."""
    path = Path(path)
    prefix = '\\\\?\\'
    if os.name == "nt" and path.is_absolute() and not str(path).startswith(prefix):
        return Path(prefix + str(path))
    return path


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


def merge_policy(existing_bytes, hub_bytes, previous_digest, previous_overrides):
    """Central MODEL_POLICY.json plus the project's own values for tunable keys only.

    Returns (bytes, report, overrides). Central keys (models, efforts, concurrency caps,
    mandatory skills) always come from the hub; invalid project values are dropped."""
    hub = json.loads(hub_bytes.decode("utf-8"))
    overrides = dict(previous_overrides) if isinstance(previous_overrides, dict) else {}
    reset = []
    if existing_bytes is not None and digest(existing_bytes) != previous_digest:
        try:
            current = json.loads(existing_bytes.decode("utf-8"))
        except ValueError as exc:
            raise PolicyConflictError(f"Install stopped, nothing written: invalid JSON in MODEL_POLICY.json: {exc}")
        if not isinstance(current, dict):
            raise PolicyConflictError("Install stopped, nothing written: MODEL_POLICY.json must be a JSON object")
        overrides = {k: current[k] for k in mp.TUNABLE_KEYS if k in current and current[k] != hub.get(k)}
        reset = sorted(k for k in current if k not in mp.TUNABLE_KEYS and current[k] != hub.get(k))
    merged, rejected = dict(hub), []
    for key in sorted(overrides):
        trial = dict(merged, **{key: overrides[key]})
        if mp.validate_policy(trial):
            rejected.append(key)
        else:
            merged = trial
    overrides = {k: v for k, v in overrides.items() if k not in rejected}
    data = hub_bytes if not overrides else (json.dumps(merged, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    return data, {"preserved": sorted(overrides), "rejected": rejected, "reset_to_central": reset}, overrides


def load_catalog_module(root):
    """Load the project-side helper template (shared enable transform)."""
    path = Path(root) / CATALOG_TEMPLATE
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("agent_hub_catalog_template", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_enabled(target):
    data = _read_json(Path(target) / ENABLED_REL)
    return data if data is not None else {}


def _prune_backups(base, keep=5):
    if not base.is_dir():
        return
    for old in sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True)[keep:]:
        shutil.rmtree(old, ignore_errors=True)


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
        try:
            subprocess.run(["git", "-C", str(root), "submodule", "update", "--init"], check=True)
        except (subprocess.CalledProcessError, OSError):
            pass  # reported below as external: unavailable (submodules not initialized)
    files = {}
    def add(rel, data):
        files[str(rel).replace("\\", "/")] = data
    for rel in ("AGENTS.md", "CLAUDE.md", mp.HOOK_REL):
        add(rel, (root / rel).read_bytes())
    for src in sorted((root / ".claude/agents").glob("*.md")):
        add(src.relative_to(root), src.read_bytes())
    own_skills = set()
    for folder in ("skills",):
        for src in sorted((root / folder).glob("*/SKILL.md")):
            own_skills.add(src.parent.name)
            for runtime in (".claude/skills", ".agents/skills"):
                add(f"{runtime}/{src.parent.name}/SKILL.md", src.read_bytes())
    if profile == "full":
        for rel, data in approved_files(root).items():
            if rel in files:
                raise ValueError("External skill conflicts with hub skill: " + rel)
            add(rel, data)
            parts = rel.split("/")
            own_skills.add(parts[2])
    catalog = []
    legacy = profile == "full" and not (root / "registry/external_capabilities.json").is_file()
    if legacy:  # superseded by the approved registry when present (also avoids a slow tree scan)
        for repo in sorted((root / "external").iterdir()) if (root / "external").exists() else []:
            if not repo.is_dir() or repo.is_symlink():
                continue
            for src in sorted(repo.rglob("SKILL.md")):
                if src.is_symlink() or not src.is_file() or ".git" in src.relative_to(repo).parts:
                    continue
                catalog.append({"source": repo.name, "path": src.relative_to(repo).as_posix(), "status": "review-required"})
    if legacy or profile != "full":
        add(".agent-hub/external-catalog.json", (json.dumps(catalog, indent=2)+"\n").encode())
    add(".agent-hub/README.md", b"# Agent Hub\nOwn agents and skills are installed. Approved external skills are active or searchable via .agent-hub/bin/catalog.py; MCP services need their own setup. Start Claude with: claude --agent orchestrator --model opus\n")
    ltarget = lp(target)
    manifest_path = ltarget / ".agent-hub/manifest.json"
    def safe_path(rel):
        p = target / rel
        if not p.resolve().is_relative_to(target) or any(q.is_symlink() for q in [p, *p.parents] if q != target and target in q.parents):
            raise ValueError(f"Unsafe path: {rel}")
        return lp(p)
    safe_path(".agent-hub/manifest.json")
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": {}}
    prev_files = previous.get("files", {})
    prev_ext = previous.get("external", {}) if isinstance(previous.get("external"), dict) else {}
    policy_path = safe_path(POLICY_REL)
    if policy_path.exists() and not policy_path.is_file():
        raise ValueError("Unsafe path: " + POLICY_REL)
    policy_bytes, policy_report, policy_overrides = merge_policy(
        policy_path.read_bytes() if policy_path.exists() else None, (root / POLICY_REL).read_bytes(),
        prev_files.get(POLICY_REL), previous.get("policy_overrides"))
    add(POLICY_REL, policy_bytes)

    # --- external capabilities (verified against registry hashes and pinned commits)
    ext_meta, groups, enabled_targets = {}, {}, {}
    ext = {"active_skills": 0, "catalog_skills": 0, "catalog_agents": 0, "skipped": {},
           "status": "skipped: profile core"}
    plan = None
    if profile == "full":
        try:
            executors = mp.load_json(root / "MODEL_POLICY.json").get("executors", ["sonnet", "haiku"])
        except (OSError, ValueError):
            executors = ["sonnet", "haiku"]
        plan = plan_external(root, own_skills, executors)
        ext.update({k: plan[k] for k in ("active_skills", "catalog_skills", "catalog_agents", "skipped", "status")})
    carry = set()
    if plan is not None and plan["status"] == "ok":
        for rel, data in plan["files"].items():
            if rel not in files:
                add(rel, data)
                ext_meta[rel] = plan["meta"][rel]
        index = "".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n" for e in plan["index"])
        add(".agent-hub/catalog/index.jsonl", index.encode("utf-8"))
        carry = {rel for rel, m in prev_ext.items() if m.get("id") in plan["skipped"]}
        helper = load_catalog_module(root)
        if helper is not None:
            add(".agent-hub/bin/catalog.py", (root / CATALOG_TEMPLATE).read_bytes())
            _, default_effort = helper.policy(root)
            skills = helper.mandatory_skills(root)
            for iid in sorted(_read_enabled(target)):
                item = plan["catalog"].get(iid)
                if not item:
                    continue
                targets = helper.enable_targets({"kind": item["kind"], "name": item["name"]},
                                                item["files"], default_effort, skills)
                enabled_targets[iid] = targets
                for rel, data in targets.items():
                    add(rel, data)
                    fname = "agent.md" if item["kind"] == "agent" else rel.split("/", 3)[3]
                    ext_meta[rel] = item["meta"][fname]
    elif profile == "full" or previous.get("external"):
        carry = set(prev_ext) | {r for r in prev_files if r.startswith(".agent-hub/catalog/")
                                 or r == ".agent-hub/bin/catalog.py"}
        if (ltarget / ".agent-hub/bin/catalog.py").is_file() and (root / CATALOG_TEMPLATE).is_file():
            carry.discard(".agent-hub/bin/catalog.py")
            add(".agent-hub/bin/catalog.py", (root / CATALOG_TEMPLATE).read_bytes())
    # --- hooks (registry-driven; ECC files verified against pinned commit and sha256)
    hplan = hm.plan_hooks(root, target, profile, prev_files, home)
    for rel, data in hplan["files"].items():
        add(rel, data)
        if rel in hplan["meta"]:
            ext_meta[rel] = hplan["meta"][rel]
    carry = set(carry) | hplan["carry"]
    for rel, dest in (("scripts/phase_report.py", ".agent-hub/bin/phase_report.py"),
                      ("templates/PHASE_REPORT.md", "docs/reports/PHASE_REPORT_TEMPLATE.md")):
        if (root / rel).is_file():
            add(dest, (root / rel).read_bytes())
    if plan is not None:
        for rel in ext_meta:
            if rel.startswith((".claude/skills/", ".agents/skills/")):
                groups.setdefault("/".join(rel.split("/")[:3]), []).append(rel)

    # --- preflight: settings and MCP (nothing is written if this fails)
    settings_path = safe_path(".claude/settings.json")
    if settings_path.exists() and not settings_path.is_file():
        raise ValueError("Unsafe path: .claude/settings.json")
    existing_settings = settings_path.read_bytes() if settings_path.exists() else None
    new_settings, settings_status, problems = merge_settings(
        existing_settings, (root / ".claude/settings.json").read_bytes(), prev_files.get(".claude/settings.json"))
    if problems:
        raise PolicyConflictError("Install stopped, nothing written: " + "; ".join(problems))
    new_settings = hm.finalize_settings(existing_settings, new_settings, hplan)
    if new_settings is not None and settings_status == "unchanged":
        settings_status = "merged"
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
        if (rel != POLICY_REL and p.exists() and p.read_bytes() != data
                and prev_files.get(rel) != digest(p.read_bytes())):
            conflicts.append(rel)
    # A skill directory is staged as a whole: never mix hub files into a foreign directory.
    for prefix, rels in groups.items():
        folder = ltarget / prefix
        owned = any(r.startswith(prefix + "/") for r in prev_files)
        extra = False
        if folder.is_dir() and not owned:
            present = {q.relative_to(ltarget).as_posix() for q in folder.rglob("*") if q.is_file()}
            extra = bool(present - set(rels))
        if extra or any(r in conflicts for r in rels):
            conflicts += [r for r in rels if r not in conflicts]
    for rel in conflicts:
        safe_path(f"{INCOMING}/{rel}")

    # --- classify changes (for backup and rollback)
    overwritten = [r for r, d in files.items() if r not in conflicts and (ltarget / r).is_file()
                   and (ltarget / r).read_bytes() != d]
    created = [r for r in files if r not in conflicts and not (ltarget / r).exists()]
    stale = [r for r, want in prev_files.items()
             if r not in files and r not in carry and r not in MERGED and (ltarget / r).is_file()
             and digest((ltarget / r).read_bytes()) == want]
    for rel in stale:
        safe_path(rel)
    backup_id = None
    settings_backup = new_settings is not None and existing_settings is not None
    if overwritten or stale or settings_backup or (created and manifest_path.exists()):
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        backup_id, n = stamp, 1
        while (ltarget / BACKUPS / backup_id).exists():
            backup_id, n = f"{stamp}-{n}", n + 1
        base = safe_path(f"{BACKUPS}/{backup_id}")
        base.mkdir(parents=True, exist_ok=True)
        for rel in sorted(set(overwritten) | set(stale)):
            dest = base / "files" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ltarget / rel).read_bytes())
        if manifest_path.exists():
            (base / "manifest.json").write_bytes(manifest_path.read_bytes())
        meta = {"restored": sorted(set(overwritten) | set(stale)), "created": sorted(created)}
        if settings_backup:
            (base / "settings.json").write_bytes(existing_settings)
            meta["settings_after"] = digest(new_settings)
        (base / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

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
    for rel in stale:
        p = ltarget / rel
        p.unlink()
        for parent in p.parents:
            if parent == ltarget or any(parent.iterdir()):
                break
            parent.rmdir()
    if new_settings is not None:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_bytes(new_settings)
    if new_mcp is not None:
        mcp_path.write_text(json.dumps(new_mcp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    incoming_root = ltarget / INCOMING
    if incoming_root.is_dir():
        for stale_file in sorted(incoming_root.rglob("*"), reverse=True):
            rel = stale_file.relative_to(incoming_root).as_posix()
            if stale_file.is_file() and not stale_file.is_symlink() and rel not in conflicts:
                stale_file.unlink()
            elif stale_file.is_dir() and not any(stale_file.iterdir()):
                stale_file.rmdir()
    merged = [rel for rel in MERGED if (ltarget / rel).is_file()]
    manifest_files = {k: digest(v) for k, v in files.items() if k not in conflicts}
    manifest_ext = {k: v for k, v in ext_meta.items() if k not in conflicts}
    for rel in carry:
        if rel in prev_files and rel not in manifest_files:
            manifest_files[rel] = prev_files[rel]
            if rel in prev_ext:
                manifest_ext[rel] = prev_ext[rel]
    if enabled_targets:
        enabled = _read_enabled(target)
        for iid, targets in enabled_targets.items():
            record = enabled.get(iid)
            if isinstance(record, dict):
                record["files"] = {r: digest(d) for r, d in targets.items()
                                   if r not in conflicts} | {r: h for r, h in record.get("files", {}).items()
                                                            if r in conflicts}
        (ltarget / ENABLED_REL).write_text(json.dumps(enabled, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"profile": profile, "files": manifest_files, "merged": merged,
                                         "external": manifest_ext, "policy_overrides": policy_overrides},
                                        indent=2)+"\n", encoding="utf-8")
    if backup_id:
        _prune_backups(ltarget / BACKUPS)
    return {"installed_files": len(manifest_files), "external_candidates": len(catalog),
            "external_activation": "review-required", "target": str(target),
            "conflicts": sorted(conflicts), "settings": settings_status, "policy": policy_report,
            "mcp": mcp_report,
            "external": ext, "backup": backup_id, "hooks": hplan["report"]}


def rollback(target, backup_id=None):
    """Restore a backup made by install; user-modified files are reported and left alone."""
    target = Path(target).resolve()
    ltarget = lp(target)
    base = ltarget / BACKUPS
    available = sorted((p.name for p in base.iterdir() if p.is_dir()), reverse=True) if base.is_dir() else []
    if not available:
        raise ValueError("No backups found in " + str(base))
    if backup_id is None:
        backup_id = available[0]
    elif backup_id not in available:
        raise ValueError(f"Unknown backup {backup_id}; available: {available}")
    folder = base / backup_id
    manifest_path = ltarget / ".agent-hub/manifest.json"
    current = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": {}}
    cur_files = current.get("files", {})
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    restored, removed, conflicts = [], [], []

    def unmodified(rel):
        p = ltarget / rel
        return not p.exists() or (p.is_file() and digest(p.read_bytes()) == cur_files.get(rel))

    for rel in meta.get("restored", []):
        if not (target / rel).resolve().is_relative_to(target):
            raise ValueError("Unsafe path in backup: " + rel)
        if unmodified(rel):
            p = ltarget / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((folder / "files" / rel).read_bytes())
            restored.append(rel)
        else:
            conflicts.append(rel)
    for rel in meta.get("created", []):
        p = ltarget / rel
        if not (target / rel).resolve().is_relative_to(target):
            raise ValueError("Unsafe path in backup: " + rel)
        if not p.exists():
            continue
        if p.is_file() and digest(p.read_bytes()) == cur_files.get(rel):
            p.unlink()
            removed.append(rel)
        else:
            conflicts.append(rel)
    if meta.get("settings_after") and (folder / "settings.json").is_file():
        sp = ltarget / ".claude/settings.json"
        if sp.is_file() and digest(sp.read_bytes()) == meta["settings_after"]:
            sp.write_bytes((folder / "settings.json").read_bytes())
            restored.append(".claude/settings.json")
            state_backup, state = folder / "hooks_state.json", ltarget / ".agent-hub/hooks.json"
            if state_backup.is_file():
                state.write_bytes(state_backup.read_bytes())
            elif meta.get("reason") == "hooks toggle" and state.is_file():
                state.unlink()
            restored.append(".agent-hub/hooks.json") if state_backup.is_file() else None
        else:
            conflicts.append(".claude/settings.json")
    prev_manifest_file = folder / "manifest.json"
    if prev_manifest_file.is_file():
        restored_manifest = json.loads(prev_manifest_file.read_text(encoding="utf-8"))
        files = dict(restored_manifest.get("files", {}))
        ext = dict(restored_manifest.get("external", {}))
        for rel in conflicts:
            if rel in cur_files:
                files[rel] = cur_files[rel]
            else:
                files.pop(rel, None)
            if rel in current.get("external", {}):
                ext[rel] = current["external"][rel]
        restored_manifest["files"], restored_manifest["external"] = files, ext
        manifest_path.write_text(json.dumps(restored_manifest, indent=2) + "\n", encoding="utf-8")
    return {"backup": backup_id, "restored": sorted(restored), "removed": sorted(removed),
            "conflicts": sorted(conflicts)}
