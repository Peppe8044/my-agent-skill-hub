#!/usr/bin/env python3
"""PreToolUse guard for file edits (Edit, Write, MultiEdit, NotebookEdit).

Denies edits to model guard files and hook scripts, and content with credential
patterns (the secret is never echoed). Asks for project settings.json and paths
outside the project. Malformed hook input fails closed (exit 2).
"""
import json
import os
import re
import sys

HOOK = "file_guard"
TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SECRETS = [
    r"gh[opusr]_[A-Za-z0-9]{20,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"sk-ant-[A-Za-z0-9-]{20,}",
    r"sk-[A-Za-z0-9]{32,}",
    r"AKIA[0-9A-Z]{16}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}",
    r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----",
]
SECRET_RE = re.compile("|".join(f"(?:{p})" for p in SECRETS))


def project_dir():
    return os.path.normcase(os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()))


def resolve(path, proj):
    full = path if os.path.isabs(path) else os.path.join(proj, path)
    return os.path.normcase(os.path.realpath(full))


def rel_to(proj, target):
    try:
        return os.path.relpath(target, proj).replace("\\", "/")
    except ValueError:  # different drive: outside the project
        return None


def contents(tool_input):
    texts = [tool_input.get(k) for k in ("content", "new_string", "new_source")]
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        texts += [e.get("new_string") for e in edits if isinstance(e, dict)]
    return [t for t in texts if isinstance(t, str)]


def check(data, proj):
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return "deny", "no tool_input object"
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(path, str) or not path:
        return "deny", "no file path"
    target = resolve(path, proj)
    rel = rel_to(proj, target)
    if rel == ".claude/hooks/model_guard.py":
        return "deny", "protected model guard file"
    if os.path.basename(target).lower() == "model_policy.json":  # target is normcased (lowercase on Windows)
        return "deny", "protected MODEL_POLICY.json"
    if rel is not None and rel.startswith(".claude/hooks/"):
        return "deny", "files under .claude/hooks are protected"
    if any(SECRET_RE.search(text) for text in contents(tool_input)):
        return "deny", "content contains a credential pattern (value not shown)"
    if rel is None or rel == ".." or rel.startswith("../"):
        return "ask", "edit targets a path outside the project directory"
    if rel == ".claude/settings.json":
        return "ask", "edit changes project .claude/settings.json"
    return "allow", ""


def malformed(reason):
    print(f"{HOOK}: malformed hook input, denied ({reason})", file=sys.stderr)
    return 2


def main():
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError) as exc:
        return malformed(type(exc).__name__)
    if not isinstance(data, dict):
        return malformed("payload is not an object")
    if data.get("tool_name") not in TOOLS:
        return 0
    verdict, reason = check(data, project_dir())
    if verdict == "deny":
        print(f"{HOOK}: denied, {reason}", file=sys.stderr)
        return 2
    if verdict == "ask":
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
