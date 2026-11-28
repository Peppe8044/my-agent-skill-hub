#!/usr/bin/env python3
"""Stop hook: token usage per session into .agent-hub/usage/<session_id>.json (numbers only).
The hook path never exits non-zero. CLI: usage_tracker.py --summary [--project P]
"""
import glob
import json
import os
import re
import sys

HOOK = "usage_tracker"
FIELDS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def project_dir():
    return os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def empty():
    return {**{f: 0 for f in FIELDS}, "messages": 0}


def as_int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def add_counts(dst, counts):
    for key in FIELDS + ("messages",):
        dst[key] = dst.get(key, 0) + as_int(counts.get(key))


def add_models(dst, models):
    for model, counts in models.items():
        if isinstance(counts, dict):
            add_counts(dst.setdefault(model, empty()), counts)
    return dst


def read_models(path):
    """Per-model counts from assistant lines; one entry per message.id (last line wins)."""
    seen = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for index, line in enumerate(fh):
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict) or rec.get("type") != "assistant":
                continue
            msg = rec.get("message") or {}
            usage, model, mid = msg.get("usage"), msg.get("model"), msg.get("id")
            if not isinstance(usage, dict) or not isinstance(model, str):
                continue
            seen[mid if isinstance(mid, str) else ("line", index)] = (model, usage)
    models = {}
    for model, usage in seen.values():
        counts = models.setdefault(model, empty())
        add_counts(counts, {f: as_int(usage.get(f)) for f in FIELDS} | {"messages": 1})
    return models


def sub_files(transcript):
    stem = transcript[:-len(".jsonl")] if transcript.endswith(".jsonl") else transcript
    return sorted(glob.glob(os.path.join(stem, "subagents", "agent-*.jsonl")))


def subagent_entry(path):
    try:
        with open(path[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
            agent_type = json.load(fh).get("agentType")
    except (OSError, ValueError, AttributeError):
        agent_type = None
    return {"agent_type": agent_type if isinstance(agent_type, str) else "unknown",
            "file": os.path.basename(path), "models": read_models(path)}


def signature(paths):
    stats = [os.stat(p) for p in paths]
    return {"size": sum(s.st_size for s in stats), "mtime_ns": max(s.st_mtime_ns for s in stats),
            "files": len(paths)}


def write_atomic(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
    os.replace(path + ".tmp", path)


def track(payload, proj):
    sid, transcript = payload.get("session_id"), payload.get("transcript_path")
    if not isinstance(sid, str) or not sid or not isinstance(transcript, str) or not transcript:
        raise ValueError("missing session_id or transcript_path")
    if not os.path.isfile(transcript):
        raise FileNotFoundError("transcript not found, nothing recorded")
    out = os.path.join(proj, ".agent-hub", "usage", re.sub(r"[^A-Za-z0-9_.-]", "_", sid) + ".json")
    subs = sub_files(transcript)
    sig = signature([transcript] + subs)
    try:
        with open(out, encoding="utf-8") as fh:
            if json.load(fh).get("signature") == sig:
                return "unchanged"
    except (OSError, ValueError, AttributeError):
        pass
    main = read_models(transcript)
    subagents = [subagent_entry(p) for p in subs]
    totals = add_models({}, main)
    for entry in subagents:
        add_models(totals, entry["models"])
    doc = {"session_id": sid, "signature": sig, "main": main,
           "subagents": subagents, "totals_by_model": totals}
    write_atomic(out, doc)
    return "written"


def hook_main():
    try:
        track(json.load(sys.stdin), project_dir())  # non-object payloads raise and are skipped
    except Exception as exc:  # the Stop hook must never block the session
        print(f"{HOOK}: skipped ({type(exc).__name__}: {str(exc)[:120]})", file=sys.stderr)
    return 0


def summary(proj):
    by_model, by_agent = {}, {}
    for path in sorted(glob.glob(os.path.join(proj, ".agent-hub", "usage", "*.json"))):
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        if not isinstance(doc, dict):
            continue
        add_models(by_model, doc.get("totals_by_model") or {})
        add_models(by_agent.setdefault("main", {}), doc.get("main") or {})
        for sub in doc.get("subagents") or []:
            if isinstance(sub, dict):
                key = str(sub.get("agent_type", "unknown"))
                add_models(by_agent.setdefault(key, {}), sub.get("models") or {})
    return {"by_model": by_model, "by_agent_type": by_agent}


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--summary"]:
        base = os.path.realpath(args[args.index("--project") + 1]) if "--project" in args else project_dir()
        print(json.dumps(summary(base), indent=2, sort_keys=True))
        sys.exit(0)
    sys.exit(hook_main())
