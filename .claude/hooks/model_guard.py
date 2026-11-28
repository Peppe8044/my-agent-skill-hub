#!/usr/bin/env python3
"""PreToolUse guard: only the MODEL_POLICY.json executor models may run subagents.

Self-contained (stdlib only) because it is copied into installed projects.
Exit 0 = allow (silent). Exit 2 = deny (reason on stderr). Fails closed.
"""
import json
import os
import re
import sys

# Keep this literal identical to scripts/model_policy.py (a test checks parity).
MODEL_RE = re.compile(r"(?m)^model:[ \t]*(\S+)[ \t]*$")
DEFAULT_EXECUTORS = {"sonnet", "haiku"}
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")


def deny(reason):
    sys.stderr.write("model_guard: " + reason + "\n")
    return 2


def agent_model(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read().replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return None
    match = MODEL_RE.search(parts[1])
    return match.group(1) if match else None


def decide(event, project):
    if not isinstance(event, dict):
        return deny("malformed hook input; blocked (MODEL_POLICY.json)")
    if event.get("tool_name") not in ("Agent", "Task"):
        return 0
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return deny("malformed tool_input; blocked (MODEL_POLICY.json)")
    allowed = set(DEFAULT_EXECUTORS)
    policy_path = os.path.join(project, "MODEL_POLICY.json")
    if os.path.isfile(policy_path):
        with open(policy_path, encoding="utf-8") as handle:
            executors = json.load(handle).get("executors")
        if isinstance(executors, list) and executors and all(isinstance(x, str) for x in executors):
            # A policy file can narrow the executors, never widen them beyond sonnet/haiku.
            allowed = set(executors) & DEFAULT_EXECUTORS
            if not allowed:
                return deny("MODEL_POLICY.json executors allow no sonnet/haiku model; blocked")
    subagent = tool_input.get("subagent_type")
    if subagent == "fork":
        return deny("fork subagents inherit the Opus parent; MODEL_POLICY.json allows only "
                    + "/".join(sorted(allowed)) + " executors")
    if tool_input.get("model") is not None:
        model = tool_input["model"]
        if not isinstance(model, str) or model not in allowed:
            return deny("model %r is not allowed for subagents; MODEL_POLICY.json executors: %s"
                        % (model, ", ".join(sorted(allowed))))
        return 0
    if isinstance(subagent, str) and SAFE_NAME.fullmatch(subagent):
        path = os.path.join(project, ".claude", "agents", subagent + ".md")
        if os.path.isfile(path):
            model = agent_model(path)
            if model in allowed:
                return 0
            return deny("project agent %r has model %r outside MODEL_POLICY.json executors"
                        % (subagent, model))
    return deny("subagent %r has no explicit model and is not a project agent with an allowed "
                "model (built-ins may inherit the Opus parent); pass model: sonnet or haiku "
                "explicitly (MODEL_POLICY.json)" % (subagent,))


def main():
    try:
        event = json.loads(sys.stdin.read())
        project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        return decide(event, project)
    except Exception as exc:  # fail closed
        return deny("guard error (%s); blocked (MODEL_POLICY.json)" % type(exc).__name__)


if __name__ == "__main__":
    sys.exit(main())
