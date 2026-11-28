"""Hook registry, security report, per-project enable/disable and verification (stdlib only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_REL = "registry/HOOK_REGISTRY.json"
REPORT_REL = "docs/HOOK_SECURITY_REPORT.md"
DECISIONS_REL = "registry/hook_decisions.json"
STATE_REL = ".agent-hub/hooks.json"
ECC_DEST = ".claude/hooks/ecc/"
MANAGED_MARK = "/.claude/hooks/"
MODEL_GUARD = "own:model-guard"
SCRIPT_RE = re.compile(r"scripts/hooks/[\w./-]+\.js")
REQUIRE_RE = re.compile(r"""require\(\s*['"](\.{1,2}/[^'"]+)['"]\s*\)""")


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha(data):
    # Content hash independent of line endings (git autocrlf checks out CRLF on Windows, LF elsewhere).
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60)


def ecc_commit(hub_root):
    """Pinned commit: gitlink of external/ECC, else the checkout HEAD, else None."""
    r = _git(hub_root, "ls-files", "-s", "external/ECC")
    parts = r.stdout.split() if r.returncode == 0 else []
    if len(parts) >= 2 and parts[0] == "160000":
        return parts[1]
    return ecc_head(hub_root)


def ecc_head(hub_root):
    repo = Path(hub_root) / "external/ECC"
    if not repo.is_dir():
        return None
    r = _git(repo, "rev-parse", "HEAD")
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def _own_command(script):
    return 'python "$CLAUDE_PROJECT_DIR/' + script + '"'


def _ecc_command(entry):
    return 'node "$CLAUDE_PROJECT_DIR/' + ECC_DEST + entry + '"'


def _ecc_events(ecc_root):
    """[(id, description, event, matcher, scripts)] in hooks.json order merged with metadata."""
    cfg = _json(ecc_root / "hooks/hooks.json")["hooks"]
    meta = _json(ecc_root / "hooks/hooks.metadata.json")["entries"]
    out = []
    for event, entries in cfg.items():
        ids = meta.get(event, [])
        for i, entry in enumerate(entries):
            m = ids[i] if i < len(ids) else {"id": f"{event}:{i}", "description": ""}
            command = " ".join(h.get("command", "") for h in entry.get("hooks", []))
            scripts = SCRIPT_RE.findall(command)
            out.append((m["id"], m.get("description", ""), event, entry.get("matcher", ""), scripts))
    return out


def _deps(ecc_root, files):
    found = set()
    for rel in files:
        p = ecc_root / rel
        if p.is_file():
            for target in REQUIRE_RE.findall(p.read_text(encoding="utf-8", errors="replace")):
                found.add((Path(rel).parent / target).as_posix().replace("/./", "/"))
    norm = set()
    for item in found:
        parts = []
        for seg in item.split("/"):
            if seg == "..":
                if parts:
                    parts.pop()
            elif seg != ".":
                parts.append(seg)
        norm.add("/".join(parts))
    return sorted(norm)


def build_registry(hub_root=ROOT):
    hub_root = Path(hub_root)
    decisions = _json(hub_root / DECISIONS_REL)
    hooks = []
    for d in decisions["own"]:
        path = hub_root / d["script"]
        entry = {
            "id": d["id"], "source": "own", "status": "approved", "mandatory": bool(d.get("mandatory")),
            "default_enabled": bool(d.get("default_enabled")), "runtime": d["runtime"],
            "events": d["events"],
            "files": [{"path": d["script"], "sha256": _sha(path.read_bytes()) if path.is_file() else None}],
            "install_paths": [d["script"]], "command": _own_command(d["script"]),
            "dependencies": [d["runtime"]], "risk": d.get("risk", "low"), "areas": d.get("areas", []),
            "reason": d.get("notes", ""),
        }
        if not path.is_file():
            entry["notes"] = "hub file not present yet; sha256 unknown"
        hooks.append(entry)
    ecc_cfg = decisions.get("ecc", {})
    ecc_root = hub_root / "external" / ecc_cfg.get("repo", "ECC")
    inventory = hub_root / "registry/EXTERNAL_SKILLS_INVENTORY.json"
    inv = _json(inventory)["repos"] if inventory.is_file() else {}
    commit = ecc_commit(hub_root)
    license_ = (inv.get("ECC") or {}).get("license")
    decided = ecc_cfg.get("decisions", {})
    if (ecc_root / "hooks/hooks.json").is_file():
        for hid, description, event, matcher, scripts in _ecc_events(ecc_root):
            dec = decided.get(hid)
            status = dec["status"] if dec else "inventory-only"
            entry_script = (dec or {}).get("entry") or (scripts[-1] if scripts else None)
            files = (dec or {}).get("files") if status == "approved" else None
            if files is None:
                files = [entry_script] if entry_script else []
            hooks.append({
                "id": hid, "source": "ECC", "status": status, "mandatory": False,
                "default_enabled": bool((dec or {}).get("default_enabled")) and status == "approved",
                "runtime": (dec or {}).get("runtime", "node"),
                "events": (dec or {}).get("events") or [{"event": event, "matcher": matcher}],
                "files": [{"path": f, "sha256": _sha((ecc_root / f).read_bytes()) if (ecc_root / f).is_file() else None}
                          for f in files],
                "install_paths": [ECC_DEST + f for f in files],
                "command": _ecc_command(entry_script) if status == "approved" and entry_script else None,
                "dependencies": ["node"] + _deps(ecc_root, files), "risk": (dec or {}).get("risk", "unreviewed"),
                "areas": (dec or {}).get("areas", []),
                "reason": (dec or {}).get("reason", "no decision recorded") if dec else "no decision recorded",
                "description": description,
                "provenance": {"repo": "ECC", "commit": commit, "license": license_},
            })
    for repo, info in sorted(inv.items()):
        if repo == "ECC":
            continue
        seen = set()
        for item in info.get("hooks", []):
            hid = f"{repo}:{item['path']}"
            if hid in seen:
                continue
            seen.add(hid)
            hooks.append({
                "id": hid, "source": repo, "status": "inventory-only", "mandatory": False,
                "default_enabled": False, "runtime": "unknown", "events": [], "files": [],
                "install_paths": [], "command": None, "dependencies": [], "risk": "unreviewed", "areas": [],
                "reason": "out of phase-4 scope; service not installed", "kind": item.get("kind"),
                "provenance": {"repo": repo, "commit": info.get("commit"), "license": info.get("license")},
            })
    hooks.sort(key=lambda h: h["id"])
    return {"schema": 1, "hooks": hooks}


def _strip_ecc_sha(registry):
    data = json.loads(json.dumps(registry))
    for h in data["hooks"]:
        if h["source"] == "ECC":
            for f in h["files"]:
                f["sha256"] = None
            h["dependencies"] = [d for d in h["dependencies"] if d in ("node", "python")]
    return data


def registry_equal(a, b, ignore_ecc_sha=False):
    """Compare registries. Without an ECC checkout (e.g. CI) the ECC entries cannot be rebuilt,
    so only the non-ECC entries are compared; ECC entries are verified where ECC is present."""
    if ignore_ecc_sha:
        def non_ecc(reg):
            return {**reg, "hooks": [h for h in reg.get("hooks", []) if h.get("source") != "ECC"]}
        return _strip_ecc_sha(non_ecc(a)) == _strip_ecc_sha(non_ecc(b))
    return a == b


def render_registry(registry):
    return json.dumps(registry, indent=2, ensure_ascii=False) + "\n"


def _short(h):
    return (h or "n/a")[:12]


def security_report(registry):
    hooks = registry["hooks"]
    by_status, by_source = {}, {}
    for h in hooks:
        by_status[h["status"]] = by_status.get(h["status"], 0) + 1
        by_source[h["source"]] = by_source.get(h["source"], 0) + 1
    L = ["# Informe de seguridad de hooks", "",
         "Generado por `python scripts/hooks_manager.py registry` desde `registry/hook_decisions.json`. No editar a mano.", "",
         "## Totales", "", "| Estado | Cantidad |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(by_status.items())]
    L += ["", "| Origen | Cantidad |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(by_source.items())]
    L += ["", "## Hooks aprobados", "",
          "| id | evento / matcher | runtime | riesgo | archivos (sha256) | hechos revisados |", "|---|---|---|---|---|---|"]
    for h in (x for x in hooks if x["status"] == "approved"):
        ev = "; ".join(f"{e['event']} / {e['matcher'] or '*'}" for e in h["events"])
        fl = "<br>".join(f"`{f['path']}` {_short(f['sha256'])}" for f in h["files"])
        flag = " (obligatorio)" if h["mandatory"] else ""
        L.append(f"| {h['id']}{flag} | {ev} | {h['runtime']} | {h['risk']} | {fl} | {h['reason']} |")
    L += ["", "## Hooks rechazados", "", "| id | motivo |", "|---|---|"]
    L += [f"| {h['id']} | {h['reason']} |" for h in hooks if h["status"] == "rejected"]
    inv = [h for h in hooks if h["status"] == "inventory-only"]
    L += ["", "## Solo inventario", "", f"Total: {len(inv)}.", "", "| Repo | Cantidad |", "|---|---|"]
    counts = {}
    for h in inv:
        counts[h["source"]] = counts.get(h["source"], 0) + 1
    L += [f"| {k} | {v} |" for k, v in sorted(counts.items())]
    L += ["", "Hooks de ECC en solo inventario:", "", "| id | motivo |", "|---|---|"]
    L += [f"| {h['id']} | {h['reason']} |" for h in inv if h["source"] == "ECC"]
    L += ["", "## Comportamientos prohibidos y como se evitan", "",
          "| Prohibido | Control |", "|---|---|",
          "| Exfiltracion de datos | Solo se aprueban hooks revisados sin red ni procesos hijos; `command_guard` bloquea ejecucion remota (curl/wget a shell). |",
          "| Captura global de conversaciones | Rechazados los hooks de observacion, sesion y aprendizaje; `usage_tracker` guarda solo conteos de tokens en el proyecto. |",
          "| Scripts remotos sin revisar | El instalador copia solo archivos cuyo sha256 y commit coinciden con el registro; si no coinciden se omiten. |",
          "| Acceso a credenciales | `file_guard` bloquea contenido con patrones de credenciales; ningun hook aprobado lee credenciales. |",
          "| Comandos destructivos automaticos | `command_guard` deniega o pide confirmacion; ningun hook ejecuta comandos. |",
          "| Escritura fuera del proyecto | Rutas de instalacion relativas al proyecto; `file_guard` pregunta por rutas externas; rechazados los hooks que escriben en `~/.claude` o temp. |",
          "| Desactivar model_guard | `own:model-guard` es obligatorio: `hooks disable` lo rechaza, el instalador lo registra siempre y `validate` lo exige. |",
          "| Cambiar el modelo | `model_guard` deniega modelos fuera de sonnet/haiku; `file_guard` protege `MODEL_POLICY.json` y los scripts de hooks. |", ""]
    return "\n".join(L)


def write_outputs(hub_root=ROOT):
    hub_root = Path(hub_root)
    registry = build_registry(hub_root)
    (hub_root / REGISTRY_REL).write_text(render_registry(registry), encoding="utf-8")
    (hub_root / REPORT_REL).parent.mkdir(parents=True, exist_ok=True)
    (hub_root / REPORT_REL).write_text(security_report(registry), encoding="utf-8")
    return registry


def check_outputs(hub_root=ROOT):
    hub_root = Path(hub_root)
    registry = build_registry(hub_root)
    problems = []
    for rel, want in ((REGISTRY_REL, render_registry(registry)), (REPORT_REL, security_report(registry))):
        p = hub_root / rel
        if not p.is_file() or p.read_text(encoding="utf-8") != want:
            problems.append(f"{rel} is out of date (run: python scripts/hooks_manager.py registry)")
    return problems


# ------------------------------------------------------------ project install
def load_registry(hub_root):
    return _json(Path(hub_root) / REGISTRY_REL)


def read_state(target):
    p = Path(target) / STATE_REL
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return sorted(set(str(i) for i in data.get("disabled", [])))
    except (OSError, ValueError, AttributeError):
        return []


def write_state(target, disabled):
    p = Path(target) / STATE_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"disabled": sorted(set(disabled))}, indent=2) + "\n", encoding="utf-8")


def _settings_commands(settings):
    out = []
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    for groups in (hooks or {}).values() if isinstance(hooks, dict) else []:
        for g in groups if isinstance(groups, list) else []:
            for h in (g.get("hooks", []) if isinstance(g, dict) else []):
                if isinstance(h, dict) and h.get("command"):
                    out.append(h["command"])
    return out


def _read_settings(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _script_name(h):
    return Path(h["install_paths"][-1] if h["source"] == "own" else h["install_paths"][0]).name if h["install_paths"] else None


def ecc_hook_files(hub_root, hook, registry_commit=None):
    """({rel: bytes}, None) when every file is verified, else ({}, reason)."""
    hub_root = Path(hub_root)
    repo = hub_root / "external/ECC"
    want = (hook.get("provenance") or {}).get("commit")
    if not repo.is_dir():
        return {}, "external/ECC not available"
    if want is None or ecc_head(hub_root) != want:
        return {}, "external/ECC HEAD does not match the pinned commit"
    out = {}
    for f, dest in zip(hook["files"], hook["install_paths"]):
        p = repo / f["path"]
        if not p.is_file() or p.is_symlink():
            return {}, f"missing file {f['path']}"
        data = p.read_bytes()
        if f["sha256"] is None or _sha(data) != f["sha256"]:
            return {}, f"sha256 mismatch for {f['path']}"
        out[dest] = data
    return out, None


def plan_hooks(hub_root, target, profile, prev_files, home):
    """Compute hook files, settings registrations and the report for an install."""
    hub_root, target = Path(hub_root), Path(target)
    report = {"installed": [], "disabled": [], "skipped": {}, "conflicts": []}
    result = {"files": {}, "meta": {}, "carry": set(), "register": [], "keep_commands": set(),
              "managed_commands": set(), "report": report}
    reg_path = hub_root / REGISTRY_REL
    if not reg_path.is_file():
        report["skipped"]["registry"] = "HOOK_REGISTRY.json missing"
        return result
    registry = load_registry(hub_root)
    disabled = set(read_state(target)) - {MODEL_GUARD}
    existing = _read_settings(target / ".claude/settings.json")
    existing_cmds = _settings_commands(existing)
    global_cmds = _settings_commands(_read_settings(Path(home) / ".claude/settings.json")) if home else []
    for h in registry["hooks"]:
        if h["status"] != "approved" or not h["command"]:
            continue
        result["managed_commands"].add(h["command"])
        wanted = h["mandatory"] or (profile == "full" and h["default_enabled"])
        if not wanted:
            continue
        if h["id"] in disabled and not h["mandatory"]:
            report["disabled"].append(h["id"])
            continue
        if h["source"] == "own":
            f = hub_root / h["files"][0]["path"]
            if not f.is_file():
                report["skipped"][h["id"]] = "hub file not present"
                continue
            files = {h["install_paths"][0]: f.read_bytes()}
        else:
            files, reason = ecc_hook_files(hub_root, h)
            if reason:
                report["skipped"][h["id"]] = reason
                prev = [d for d in h["install_paths"] if d in prev_files]
                if prev:
                    result["carry"].update(prev)
                    result["keep_commands"].add(h["command"])
                continue
        name = _script_name(h)
        clash = None
        if h["id"] != MODEL_GUARD:
            for where, cmds in (("project", existing_cmds), ("global", global_cmds)):
                for c in cmds:
                    if name and name in c and c != h["command"]:
                        clash = {"id": h["id"], "where": where, "command": c}
                    elif c == h["command"] and where == "global":
                        clash = {"id": h["id"], "where": where, "command": c}
        if clash:
            report["conflicts"].append(clash)
            report["skipped"][h["id"]] = f"conflict with {clash['where']} hook"
            continue
        for rel, data in files.items():
            result["files"][rel] = data
            if h["source"] == "ECC":
                src = rel[len(ECC_DEST):]
                result["meta"][rel] = {"repo": "ECC", "commit": h["provenance"]["commit"], "path": src,
                                       "sha256": _sha(data), "license": h["provenance"]["license"],
                                       "id": "hook:" + h["id"]}
        result["register"].append(h)
        result["keep_commands"].add(h["command"])
        report["installed"].append(h["id"])
    report["installed"].sort()
    report["disabled"].sort()
    report["conflicts"].sort(key=lambda c: c["id"])
    return result


def apply_settings(settings, register, remove_commands):
    """Mutate settings: drop hub-managed entries in remove_commands, add missing registrations."""
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        return settings
    for event in list(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        kept = []
        for g in groups:
            inner = g.get("hooks") if isinstance(g, dict) else None
            if isinstance(inner, list):
                new_inner = [x for x in inner if not (isinstance(x, dict) and x.get("command") in remove_commands
                                                      and MANAGED_MARK in x["command"])]
                if len(new_inner) != len(inner):
                    if not new_inner:
                        continue
                    g = dict(g, hooks=new_inner)
            kept.append(g)
        hooks[event] = kept
    # Registered per (event, command): a hook that gained an event (usage tracker: Stop and
    # SubagentStop) is added to the new event in projects that already have the old one.
    present = {(event, x.get("command")) for event, groups in hooks.items() if isinstance(groups, list)
               for g in groups if isinstance(g, dict) and isinstance(g.get("hooks"), list)
               for x in g["hooks"] if isinstance(x, dict)}
    for h in register:
        for ev in h["events"]:
            if (ev["event"], h["command"]) in present:
                continue
            group = {"hooks": [{"type": "command", "command": h["command"]}]}
            if ev.get("matcher"):
                group = {"matcher": ev["matcher"], **group}
            if not isinstance(hooks.setdefault(ev["event"], []), list):
                continue
            hooks[ev["event"]].append(group)
            present.add((ev["event"], h["command"]))
    for event in [e for e, g in hooks.items() if g == []]:
        del hooks[event]
    if not hooks:
        settings.pop("hooks", None)
    return settings


def finalize_settings(existing_bytes, new_bytes, plan):
    """Return bytes to write (or None when nothing changes) after hook reconciliation."""
    base = new_bytes if new_bytes is not None else existing_bytes
    if base is None:
        return None
    settings = json.loads(base.decode("utf-8"))
    remove = plan["managed_commands"] - plan["keep_commands"]
    apply_settings(settings, plan["register"], remove)
    if existing_bytes is not None:
        try:
            if json.loads(existing_bytes.decode("utf-8")) == settings:
                return None
        except ValueError:
            pass
    return (json.dumps(settings, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


# ------------------------------------------------------------------ CLI helpers
def _status_rows(hub_root, target):
    registry = load_registry(hub_root)
    disabled = set(read_state(target))
    cmds = set(_settings_commands(_read_settings(Path(target) / ".claude/settings.json")))
    rows = []
    for h in registry["hooks"]:
        if h["status"] != "approved":
            continue
        rows.append({"id": h["id"], "mandatory": h["mandatory"], "runtime": h["runtime"],
                     "registered": h["command"] in cmds, "disabled": h["id"] in disabled,
                     "installed": all((Path(target) / p).is_file() for p in h["install_paths"])})
    return rows


def set_enabled(hub_root, target, hook_id, enable):
    hub_root, target = Path(hub_root), Path(target)
    registry = load_registry(hub_root)
    hook = next((h for h in registry["hooks"] if h["id"] == hook_id), None)
    if hook is None or hook["status"] != "approved":
        raise ValueError(f"Unknown or unapproved hook: {hook_id}")
    if not enable and (hook["mandatory"] or hook_id == MODEL_GUARD):
        raise ValueError(f"{hook_id} is mandatory and cannot be disabled")
    disabled = set(read_state(target))
    settings_path = target / ".claude/settings.json"
    settings = _read_settings(settings_path)
    if enable:
        if hook["source"] == "own":
            src = hub_root / hook["files"][0]["path"]
            if not src.is_file():
                raise ValueError("hub file not present: " + hook["files"][0]["path"])
            files = {hook["install_paths"][0]: src.read_bytes()}
        else:
            files, reason = ecc_hook_files(hub_root, hook)
            if reason:
                raise ValueError(reason)
        for rel, data in files.items():
            p = target / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        disabled.discard(hook_id)
        apply_settings(settings, [hook], set())
    else:
        disabled.add(hook_id)
        apply_settings(settings, [], {hook["command"]})
    new_bytes = (json.dumps(settings, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    backup_id = _backup_toggle(target, settings_path, new_bytes)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_bytes(new_bytes)
    write_state(target, disabled)
    return {"id": hook_id, "enabled": enable, "backup": backup_id}


def _backup_toggle(target, settings_path, new_bytes):
    """Back up settings and hook state in the installer's format so `hub.py rollback` undoes a toggle."""
    import time
    if not settings_path.is_file():
        return None
    base_dir = target / ".agent-hub/backups"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup_id, n = stamp, 1
    while (base_dir / backup_id).exists():
        backup_id, n = f"{stamp}-{n}", n + 1
    folder = base_dir / backup_id
    folder.mkdir(parents=True)
    (folder / "settings.json").write_bytes(settings_path.read_bytes())
    state = target / STATE_REL
    if state.is_file():
        (folder / "hooks_state.json").write_bytes(state.read_bytes())
    manifest = target / ".agent-hub/manifest.json"
    if manifest.is_file():
        (folder / "manifest.json").write_bytes(manifest.read_bytes())
    meta = {"restored": [], "created": [], "settings_after": hashlib.sha256(new_bytes).hexdigest(),
            "reason": "hooks toggle"}
    (folder / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return backup_id


def _run_hook(hook, target, payload, project_dir=None):
    script = Path(target) / hook["install_paths"][-1 if hook["source"] == "own" else 0]
    exe = sys.executable if hook["runtime"] == "python" else "node"
    import os
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project_dir or target))
    r = subprocess.run([exe, str(script)], input=json.dumps(payload), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=30)
    return r.returncode


def verify(hub_root, target, which=shutil.which):
    hub_root, target = Path(hub_root), Path(target)
    registry = load_registry(hub_root)
    cmds = set(_settings_commands(_read_settings(target / ".claude/settings.json")))
    disabled = set(read_state(target))
    results = {}
    tmp = tempfile.mkdtemp(prefix="hookverify-")
    try:
        eslint = Path(tmp) / ".eslintrc.json"
        eslint.write_text("{}\n", encoding="utf-8")
        tproj = str(target)
        # Empty session transcript: measurable (0 executor tokens), so the budget check can pass.
        transcript = Path(tmp) / "hooks-verify.jsonl"
        transcript.write_text("{}\n", encoding="utf-8")
        cases = {
            "own:model-guard": ({"tool_name": "Agent", "session_id": "hooks-verify", "transcript_path": str(transcript),
                                 "tool_input": {"subagent_type": "researcher", "model": "haiku"}},
                                {"tool_name": "Agent", "tool_input": {"subagent_type": "scout", "model": "opus"}}),
            "own:command-guard": ({"tool_name": "Bash", "tool_input": {"command": "echo hello"}},
                                  {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}),
            "own:file-guard": ({"tool_name": "Write", "tool_input": {"file_path": str(target / "notes.txt"), "content": "hello"}},
                               {"tool_name": "Write", "tool_input": {"file_path": str(target / ".claude/hooks/model_guard.py"),
                                                                     "content": "x = 1\n"}}),
            "own:usage-tracker": ({"hook_event_name": "Stop", "transcript_path": str(Path(tmp) / "missing.jsonl")}, None),
            "pre:config-protection": ({"tool_name": "Edit", "tool_input": {"file_path": str(Path(tmp) / "main.py"),
                                                                           "old_string": "a", "new_string": "b"}},
                                      {"tool_name": "Edit", "tool_input": {"file_path": str(eslint),
                                                                           "old_string": "{}", "new_string": "{\"rules\":{}}"}}),
        }
        for h in registry["hooks"]:
            if h["status"] != "approved" or h["command"] not in cmds or h["id"] in disabled:
                continue
            if h["runtime"] == "node" and which("node") is None:
                results[h["id"]] = {"status": "skipped: node not found"}
                continue
            if h["id"] not in cases:
                results[h["id"]] = {"status": "skipped: no synthetic payload defined"}
                continue
            script = target / h["install_paths"][-1 if h["source"] == "own" else 0]
            if not script.is_file():
                results[h["id"]] = {"status": "fail", "detail": "script missing in target"}
                continue
            benign, deny = cases[h["id"]]
            try:
                ok_code = _run_hook(h, target, benign, tproj)
                deny_code = _run_hook(h, target, deny, tproj) if deny else None
            except (OSError, subprocess.SubprocessError) as exc:
                results[h["id"]] = {"status": "fail", "detail": str(exc)}
                continue
            passed = ok_code == 0 and (deny is None or deny_code == 2)
            results[h["id"]] = {"status": "pass" if passed else "fail", "benign_exit": ok_code, "deny_exit": deny_code}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"ok": all(r["status"] == "pass" or r["status"].startswith("skipped") for r in results.values()),
            "results": results}


def main(argv=None, hub_root=ROOT):
    parser = argparse.ArgumentParser(prog="hooks")
    sub = parser.add_subparsers(dest="cmd", required=True)
    reg = sub.add_parser("registry")
    reg.add_argument("--check", action="store_true")
    for name in ("list", "verify"):
        sub.add_parser(name).add_argument("--target", required=True)
    for name in ("enable", "disable"):
        p = sub.add_parser(name)
        p.add_argument("--target", required=True)
        p.add_argument("id")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "registry":
            if args.check:
                problems = check_outputs(hub_root)
                for p in problems:
                    print(p, file=sys.stderr)
                return 1 if problems else 0
            registry = write_outputs(hub_root)
            print(f"Wrote {REGISTRY_REL} ({len(registry['hooks'])} hooks) and {REPORT_REL}")
            return 0
        if args.cmd == "list":
            print(json.dumps(_status_rows(hub_root, args.target), indent=2))
            return 0
        if args.cmd in ("enable", "disable"):
            print(json.dumps(set_enabled(hub_root, args.target, args.id, args.cmd == "enable")))
            return 0
        out = verify(hub_root, args.target)
        print(json.dumps(out, indent=2))
        return 0 if out["ok"] else 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
