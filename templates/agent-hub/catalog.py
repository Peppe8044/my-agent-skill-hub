#!/usr/bin/env python3
"""Project-side helper for the on-demand skill/agent catalog (stdlib only).

Installed to .agent-hub/bin/catalog.py. Commands:
  search <terms...> [--domain D] [--kind skill|agent] [--limit 10]
  show <id>      installed path, license and provenance (never file content)
  enable <id>    copy a catalog skill/agent into the active directories
  disable <id>   remove an enabled item if it was not modified since enabling
A new Claude Code session is needed to detect newly enabled or disabled items.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

NOTE = "Note: start a new Claude Code session to detect newly enabled or disabled items."
DEFAULT_EXECUTORS = ("sonnet", "haiku")
EFFORTS = ("low", "medium", "high")
MODEL_RE = re.compile(r"(?m)^model:[ \t]*(\S+)[ \t]*$")
EFFORT_RE = re.compile(r"(?m)^effort:[ \t]*(\S+)[ \t]*$")
SKILL_DIRS = (".claude/skills", ".agents/skills")


def lp(path):
    """Extended-length path on Windows (deep catalog paths exceed MAX_PATH)."""
    path = Path(path)
    prefix = chr(92) * 2 + "?" + chr(92)
    if os.name == "nt" and path.is_absolute() and not str(path).startswith(prefix):
        return Path(prefix + str(path))
    return path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def project_root(override=None):
    if override:
        return Path(override).resolve()
    if os.environ.get("CATALOG_PROJECT"):
        return Path(os.environ["CATALOG_PROJECT"]).resolve()
    return Path(__file__).resolve().parents[2]


def load_index(project):
    path = project / ".agent-hub/catalog/index.jsonl"
    entries = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                entries[entry["id"]] = entry
    return entries


def read_json(path, default):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else default
    except (OSError, ValueError):
        return default


def policy(project):
    data = read_json(project / "MODEL_POLICY.json", {})
    executors = data.get("executors")
    if not (isinstance(executors, list) and executors and all(isinstance(x, str) for x in executors)):
        executors = list(DEFAULT_EXECUTORS)
    default_effort = data.get("default_executor_effort")
    return ([x for x in executors if x in DEFAULT_EXECUTORS],
            default_effort if default_effort in EFFORTS else "medium")


def frontmatter_split(text):
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None, text
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return None, text
    return parts[1], parts[2]


def agent_model(data):
    front, _ = frontmatter_split(data.decode("utf-8", "replace"))
    match = MODEL_RE.search(front or "")
    return match.group(1) if match else None


def agent_for_enable(data, default_effort="medium"):
    """Return agent bytes carrying a valid `effort:` line (deterministic transform)."""
    text = data.decode("utf-8", "replace").replace("\r\n", "\n")
    front, body = frontmatter_split(text)
    if front is None:
        return data
    match = EFFORT_RE.search(front)
    if match and match.group(1) in EFFORTS:
        return text.encode("utf-8")
    if match:
        front = EFFORT_RE.sub("effort: " + default_effort, front, count=1)
    else:
        model = MODEL_RE.search(front)
        line = "effort: " + default_effort
        front = (front[:model.end()] + "\n" + line + front[model.end():]) if model else front + line + "\n"
    return ("---\n" + front + "---\n" + body).encode("utf-8")


def source_files(project, entry):
    base = lp(project / entry["path"])
    if entry["kind"] == "agent":
        return {"agent.md": base.read_bytes()} if base.is_file() else {}
    files = {}
    if base.is_dir():
        for src in sorted(base.rglob("*")):
            if src.is_file() and not src.is_symlink():
                files[src.relative_to(base).as_posix()] = src.read_bytes()
    return files


def enable_targets(entry, files, default_effort="medium"):
    """Map destination rel path -> bytes for enabling a catalog entry."""
    name = entry["name"]
    # Defence in depth: index entries must not be able to write outside the project.
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", str(name)):
        raise ValueError("refusing catalog entry with unsafe name %r" % (name,))
    for f in files:
        parts = f.replace("\\", "/").split("/")
        if f.startswith(("/", "\\")) or ":" in f or ".." in parts:
            raise ValueError("refusing catalog file with unsafe path %r" % (f,))
    if entry["kind"] == "agent":
        return {".claude/agents/%s.md" % name: agent_for_enable(files["agent.md"], default_effort)}
    return {"%s/%s/%s" % (rt, name, f): data for rt in SKILL_DIRS for f, data in files.items()}


def matches(entry, terms, domain, kind):
    if kind and entry["kind"] != kind:
        return 0
    domains = [d.lower() for d in entry.get("domains", [])]
    if domain and domain.lower() not in domains:
        return 0
    if not terms:
        return 1
    score = 0
    name, desc = entry["name"].lower(), entry.get("description", "").lower()
    for term in terms:
        if term == name:
            score += 6
        elif term in name:
            score += 3
        if any(term in d for d in domains):
            score += 3
        if term in desc:
            score += 1
    return score


def cmd_search(project, args):
    terms = [t.lower() for t in args.terms]
    scored = []
    for entry in load_index(project).values():
        score = matches(entry, terms, args.domain, args.kind)
        if score:
            scored.append((-score, entry["id"], entry))
    scored.sort(key=lambda x: (x[0], x[1]))
    for _, _, e in scored[:max(args.limit, 0)]:
        print(" | ".join((e["id"], e["kind"], ",".join(e.get("domains", [])),
                          e.get("description", "").replace("\n", " ")[:140])))
    return 0


def cmd_show(project, args):
    entry = load_index(project).get(args.id)
    if not entry:
        print("not found: " + args.id, file=sys.stderr)
        return 1
    enabled = args.id in read_json(project / ".agent-hub/enabled.json", {})
    print("id: %s\nkind: %s (%s)\npath: %s\nlicense: %s\nsource: %s@%s\nenabled: %s" % (
        entry["id"], entry["kind"], entry["tier"], entry["path"], entry["license"],
        entry["repo"], entry["commit"], "yes" if enabled else "no"))
    return 0


def update_manifest(project, add=None, remove=()):
    path = project / ".agent-hub/manifest.json"
    manifest = read_json(path, None)
    if manifest is None or not isinstance(manifest.get("files"), dict):
        return
    for rel, data in (add or {}).items():
        manifest["files"][rel] = digest(data)
    for rel in remove:
        manifest["files"].pop(rel, None)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def cmd_enable(project, args):
    entry = load_index(project).get(args.id)
    if not entry:
        print("not found: " + args.id, file=sys.stderr)
        return 1
    enabled_path = project / ".agent-hub/enabled.json"
    enabled = read_json(enabled_path, {})
    if entry["tier"] == "active":
        print("%s is already active; nothing to enable." % args.id)
        return 0
    if args.id in enabled:
        print("%s is already enabled." % args.id)
        return 0
    files = source_files(project, entry)
    if not files:
        print("catalog source is missing for " + args.id, file=sys.stderr)
        return 1
    executors, default_effort = policy(project)
    if entry["kind"] == "agent":
        model = agent_model(files["agent.md"])
        if model not in executors:
            print("refused: agent model %r is not in MODEL_POLICY.json executors (%s)"
                  % (model, ", ".join(executors)), file=sys.stderr)
            return 1
        if (project / (".claude/agents/%s.md" % entry["name"])).exists():
            print("refused: an agent named %s already exists" % entry["name"], file=sys.stderr)
            return 1
    else:
        for rt in SKILL_DIRS:
            if (project / rt / entry["name"]).exists():
                print("refused: skill directory %s/%s already exists" % (rt, entry["name"]), file=sys.stderr)
                return 1
    targets = enable_targets(entry, files, default_effort)
    for rel, data in targets.items():
        dest = lp(project / rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    enabled[args.id] = {"kind": entry["kind"], "name": entry["name"],
                        "files": {rel: digest(data) for rel, data in targets.items()}}
    enabled_path.write_text(json.dumps(enabled, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    update_manifest(project, add=targets)
    print("enabled %s (%d file(s))" % (args.id, len(targets)))
    print(NOTE)
    return 0


def cmd_disable(project, args):
    enabled_path = project / ".agent-hub/enabled.json"
    enabled = read_json(enabled_path, {})
    item = enabled.get(args.id)
    if not item:
        print("not enabled: " + args.id, file=sys.stderr)
        return 1
    changed = [rel for rel, want in item["files"].items()
               if lp(project / rel).is_file() and digest(lp(project / rel).read_bytes()) != want]
    if changed:
        print("refused: modified since enabling: " + ", ".join(sorted(changed)), file=sys.stderr)
        return 1
    for rel in item["files"]:
        path = lp(project / rel)
        if path.is_file():
            path.unlink()
        parent = path.parent
        while parent != lp(project) and parent.is_dir() and not any(parent.iterdir()) \
                and parent.name not in (".claude", ".agents", "skills", "agents"):
            parent.rmdir()
            parent = parent.parent
    del enabled[args.id]
    enabled_path.write_text(json.dumps(enabled, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    update_manifest(project, remove=list(item["files"]))
    print("disabled " + args.id)
    print(NOTE)
    return 0


def main(argv=None, project=None):
    parser = argparse.ArgumentParser(description="On-demand skill/agent catalog")
    parser.add_argument("--project", help="project directory (default: derived from this file)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    search = sub.add_parser("search")
    search.add_argument("terms", nargs="*")
    search.add_argument("--domain")
    search.add_argument("--kind", choices=("skill", "agent"))
    search.add_argument("--limit", type=int, default=10)
    for name in ("show", "enable", "disable"):
        sub.add_parser(name).add_argument("id")
    args = parser.parse_args(argv)
    root = project_root(args.project) if project is None else Path(project).resolve()
    return {"search": cmd_search, "show": cmd_show, "enable": cmd_enable,
            "disable": cmd_disable}[args.cmd](root, args)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    sys.exit(main())
