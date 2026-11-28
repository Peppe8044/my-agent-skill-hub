#!/usr/bin/env python3
"""PreToolUse guard: only the MODEL_POLICY.json executor models may run subagents.

Self-contained (stdlib only) because it is copied into installed projects.
Exit 0 = allow (silent). Exit 2 = deny (reason on stderr). Fails closed.

It also enforces the executor token budget of MODEL_POLICY.json per phase and per session.
Usage is read from this session's subagent transcripts (input, output, cache creation and
cache read, each message once) and persisted per phase in .agent-hub/budget/state.json, so
a new session does not reset the phase. Limitation: the check runs before each delegation;
an executor that is already running cannot be stopped by a hook and may exceed the budget.

Every delegation must target a project agent (.claude/agents) that preloads the mandatory
skills (MODEL_POLICY.json mandatory_agent_skills, token-budget always included) and whose
skill files exist; built-in, unknown and fork subagents cannot preload skills and are denied.
Missing or invalid policy values fall back to the central defaults below (fallback only:
MODEL_POLICY.json is the single source of truth), so an outdated project stays protected.

Budget CLI: model_guard.py --budget status | start-phase ID [--keep-if-same] |
            authorize-recovery N   [--project PATH]
"""
import json
import os
import re
import sys

# Keep this literal identical to scripts/model_policy.py (a test checks parity).
MODEL_RE = re.compile(r"(?m)^model:[ \t]*(\S+)[ \t]*$")
DEFAULT_EXECUTORS = {"sonnet", "haiku"}
DENIED_EFFORTS = ("xhigh", "max")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
STATE_REL = os.path.join(".agent-hub", "budget", "state.json")
FIELDS = {"input": "input_tokens", "output": "output_tokens",
          "cache_creation": "cache_creation_input_tokens", "cache_read": "cache_read_input_tokens"}
DEFAULT_WEIGHTS = {"input": 1.0, "output": 1.0, "cache_creation": 1.0, "cache_read": 0.1}
DEFAULT_LIMITS = {"executor_budget_per_phase": 50000, "executor_budget_per_session": 50000,
                  "executor_budget_reserve_per_active": 10000, "max_parallel_agents": 2}
MAX_PARALLEL_CAP = 2
REQUIRED_SKILL = "token-budget"
SKILLS_RE = re.compile(r"(?m)^skills:[ \t]*\n((?:[ \t]+-[ \t]*\S+[ \t]*(?:\n|$))+)")


def deny(reason):
    sys.stderr.write("model_guard: " + reason + "\n")
    return 2


def agent_front(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read().replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return ""
    parts = text.split("---\n", 2)
    return parts[1] if len(parts) == 3 else ""


def agent_model(path):
    match = MODEL_RE.search(agent_front(path))
    return match.group(1) if match else None


def agent_skills(path):
    match = SKILLS_RE.search(agent_front(path))
    return re.findall(r"-[ \t]*(\S+)", match.group(1)) if match else []


def mandatory_skills(policy):
    listed = policy.get("mandatory_agent_skills")
    names = [s for s in listed if isinstance(s, str)] if isinstance(listed, list) else []
    return [REQUIRED_SKILL] + [s for s in names if s != REQUIRED_SKILL]


def limit(policy, key):
    value = policy.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < (0 if "reserve" in key else 1):
        value = DEFAULT_LIMITS[key]
    return min(value, MAX_PARALLEL_CAP) if key == "max_parallel_agents" else value


def load_policy(project):
    path = os.path.join(project, "MODEL_POLICY.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


# ------------------------------------------------------------------ budget ledger
def session_usage(transcript_path):
    """(usage by category, executors still running) for this session, or None if unmeasurable."""
    if not isinstance(transcript_path, str) or not transcript_path.endswith(".jsonl") \
            or not os.path.isfile(transcript_path):
        return None
    usage, active, seen = {k: 0 for k in FIELDS}, 0, set()
    folder = os.path.join(transcript_path[:-len(".jsonl")], "subagents")
    if not os.path.isdir(folder):
        return usage, 0
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if name.startswith("agent-") and name.endswith(".meta.json"):
            try:
                with open(path, encoding="utf-8") as handle:
                    meta = json.load(handle)
            except (OSError, ValueError):
                meta = {}
            if not meta.get("finished"):
                active += 1
        elif name.startswith("agent-") and name.endswith(".jsonl"):
            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if '"usage"' not in line:
                        continue
                    try:
                        message = json.loads(line).get("message") or {}
                    except ValueError:
                        continue
                    row, key = message.get("usage"), (name, message.get("id"))
                    if not isinstance(row, dict) or key in seen:
                        continue
                    seen.add(key)
                    for category, field in FIELDS.items():
                        usage[category] += int(row.get(field) or 0)
    return usage, active


def weighted(usage, weights):
    return int(round(sum(float(weights.get(k, DEFAULT_WEIGHTS[k])) * usage.get(k, 0) for k in FIELDS)))


def load_state(project):
    try:
        with open(os.path.join(project, STATE_REL), encoding="utf-8") as handle:
            state = json.load(handle)
    except (OSError, ValueError):
        state = {}
    if not isinstance(state, dict):
        state = {}
    state.setdefault("phase", "unassigned")
    state.setdefault("sessions", {})
    state.setdefault("recovery_delegations", 0)
    state.setdefault("history", [])
    return state


def save_state(project, state):
    path = os.path.join(project, STATE_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
    os.replace(tmp, path)


def phase_used(state):
    return sum(int(s.get("weighted") or 0) for s in state["sessions"].values())


def check_budget(event, project, policy):
    per_phase = limit(policy, "executor_budget_per_phase")
    per_session = limit(policy, "executor_budget_per_session")
    reserve = limit(policy, "executor_budget_reserve_per_active")
    max_parallel = limit(policy, "max_parallel_agents")
    weights = policy.get("budget_weights")
    if not isinstance(weights, dict) or set(weights) != set(FIELDS):
        weights = DEFAULT_WEIGHTS
    state = load_state(project)
    measured = session_usage(event.get("transcript_path"))
    if measured is None:
        if int(state.get("recovery_delegations") or 0) > 0:
            state["recovery_delegations"] = int(state["recovery_delegations"]) - 1
            save_state(project, state)
            return 0
        return deny("cannot measure executor token usage for this session (no readable transcript); "
                    "delegation blocked until the user authorizes recovery with "
                    "`python scripts/hub.py budget authorize-recovery 1` (MODEL_POLICY.json)")
    usage, active = measured
    session_id = str(event.get("session_id") or os.path.basename(event["transcript_path"])[:-len(".jsonl")])
    session_total = weighted(usage, weights)
    # Earlier sessions of this phase keep counting: refresh them from their transcripts when they
    # still exist (their executors may have kept spending after their last delegation).
    for other, record in state["sessions"].items():
        if other != session_id and isinstance(record, dict) and record.get("transcript"):
            again = session_usage(record["transcript"])
            if again is not None:
                record["usage"], record["weighted"] = again[0], weighted(again[0], weights)
    state["sessions"][session_id] = {"usage": usage, "weighted": session_total,
                                     "transcript": event["transcript_path"]}
    save_state(project, state)
    if active >= max_parallel:
        return deny("%d executors still running; max_parallel_agents is %d (MODEL_POLICY.json)"
                    % (active, max_parallel))
    needed = reserve * (active + 1)
    if session_total + needed > per_session:
        return deny("executor token budget for this session exhausted: %d used + %d reserved > %d "
                    "(MODEL_POLICY.json executor_budget_per_session); stop delegating and report progress"
                    % (session_total, needed, per_session))
    total = phase_used(state)
    if total + needed > per_phase:
        return deny("executor token budget for phase %s exhausted: %d used + %d reserved > %d "
                    "(MODEL_POLICY.json executor_budget_per_phase); stop delegating and report progress"
                    % (state["phase"], total, needed, per_phase))
    return 0


# ------------------------------------------------------------------ model policy
def model_verdict(tool_input, project, policy):
    allowed = set(DEFAULT_EXECUTORS)
    executors = policy.get("executors")
    if isinstance(executors, list) and executors and all(isinstance(x, str) for x in executors):
        # A policy file can narrow the executors, never widen them beyond sonnet/haiku.
        allowed = set(executors) & DEFAULT_EXECUTORS
        if not allowed:
            return deny("MODEL_POLICY.json executors allow no sonnet/haiku model; blocked")
    subagent = tool_input.get("subagent_type")
    if subagent == "fork":
        return deny("fork subagents inherit the Opus parent; MODEL_POLICY.json allows only "
                    + "/".join(sorted(allowed)) + " executors")
    model = tool_input.get("model")
    if model is not None and (not isinstance(model, str) or model not in allowed):
        return deny("model %r is not allowed for subagents; MODEL_POLICY.json executors: %s"
                    % (model, ", ".join(sorted(allowed))))
    path = None
    if isinstance(subagent, str) and SAFE_NAME.fullmatch(subagent):
        candidate = os.path.join(project, ".claude", "agents", subagent + ".md")
        path = candidate if os.path.isfile(candidate) else None
    if path is None:
        return deny("subagent %r is not a project agent in .claude/agents; built-in and unknown "
                    "subagents cannot preload the mandatory skills and may inherit the Opus parent; "
                    "delegate to a project agent with model sonnet or haiku (MODEL_POLICY.json)"
                    % (subagent,))
    if model is None and agent_model(path) not in allowed:
        return deny("project agent %r has model %r outside MODEL_POLICY.json executors"
                    % (subagent, agent_model(path)))
    listed = agent_skills(path)
    missing = [s for s in mandatory_skills(policy) if s not in listed or not os.path.isfile(
        os.path.join(project, ".claude", "skills", s, "SKILL.md"))]
    if missing:
        return deny("project agent %r does not preload the mandatory skills %s (frontmatter `skills:` "
                    "and .claude/skills/<name>/SKILL.md); run hub.py update (MODEL_POLICY.json "
                    "mandatory_agent_skills)" % (subagent, ", ".join(missing)))
    return 0


def decide(event, project):
    if not isinstance(event, dict):
        return deny("malformed hook input; blocked (MODEL_POLICY.json)")
    if event.get("tool_name") not in ("Agent", "Task"):
        return 0
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return deny("malformed tool_input; blocked (MODEL_POLICY.json)")
    if tool_input.get("effort") in DENIED_EFFORTS:
        return deny("effort %r is not allowed for subagents; MODEL_POLICY.json executor_efforts "
                    "allow only low, medium or high" % (tool_input["effort"],))
    policy = load_policy(project)
    verdict = model_verdict(tool_input, project, policy)
    if verdict:
        return verdict
    return check_budget(event, project, policy)


# ------------------------------------------------------------------ budget CLI
def budget_cli(argv):
    args, project = list(argv), os.getcwd()
    if "--project" in args:
        i = args.index("--project")
        project = args[i + 1]
        del args[i:i + 2]
    keep = "--keep-if-same" in args
    args = [a for a in args if a != "--keep-if-same"]
    state, policy = load_state(project), load_policy(project)
    if args == ["status"]:
        used = phase_used(state)
        cap = limit(policy, "executor_budget_per_phase")
        print(json.dumps({"phase": state["phase"], "phase_used_weighted": used, "phase_budget": cap,
                          "phase_remaining": cap - used,
                          "session_budget": limit(policy, "executor_budget_per_session"),
                          "reserve_per_active": limit(policy, "executor_budget_reserve_per_active"),
                          "weights": policy.get("budget_weights") or DEFAULT_WEIGHTS,
                          "sessions": state["sessions"], "recovery_delegations": state["recovery_delegations"],
                          "history": state["history"]}, indent=2, sort_keys=True))
        return 0
    if len(args) == 2 and args[0] == "start-phase":
        if keep and state["phase"] == args[1]:
            print("phase %s kept (%d weighted tokens used)" % (args[1], phase_used(state)))
            return 0
        if state["sessions"]:
            state["history"].append({"phase": state["phase"], "used_weighted": phase_used(state),
                                     "sessions": len(state["sessions"])})
        state.update(phase=args[1], sessions={}, recovery_delegations=0)
        save_state(project, state)
        print("phase %s started" % args[1])
        return 0
    if len(args) == 2 and args[0] == "authorize-recovery" and args[1].isdigit():
        state["recovery_delegations"] = int(args[1])
        save_state(project, state)
        print("recovery authorized for %s delegation(s)" % args[1])
        return 0
    sys.stderr.write("usage: model_guard.py --budget status | start-phase ID [--keep-if-same] | "
                     "authorize-recovery N [--project PATH]\n")
    return 2


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--budget"]:
        return budget_cli(argv[1:])
    try:
        event = json.loads(sys.stdin.read())
        project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        return decide(event, project)
    except Exception as exc:  # fail closed
        return deny("guard error (%s); blocked (MODEL_POLICY.json)" % type(exc).__name__)


if __name__ == "__main__":
    sys.exit(main())
