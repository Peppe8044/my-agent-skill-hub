"""Single source of truth for the model policy (stdlib only)."""
import json
import re
from pathlib import Path

POLICY_KEYS = {
    "orchestrator": str, "executors": list, "allow_inherit": bool,
    "allow_executor_opus": bool, "default_parallel_agents": int,
    "max_parallel_agents": int, "max_retries": int,
    "executor_efforts": list, "default_executor_effort": str,
}
EFFORTS = ("low", "medium", "high")
ORCHESTRATOR_EFFORTS = ("high", "medium")
DENIED_EFFORTS = ("xhigh", "max")
EXECUTORS = {"sonnet", "haiku"}
SUBAGENT_ENV = "CLAUDE_CODE_SUBAGENT_MODEL"
FORBIDDEN_ENV = (
    "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",
)
HOOK_REL = ".claude/hooks/model_guard.py"
# Keep this literal identical to .claude/hooks/model_guard.py (a test checks parity).
MODEL_RE = re.compile(r"(?m)^model:[ \t]*(\S+)[ \t]*$")
EFFORT_RE = re.compile(r"(?m)^effort:[ \t]*(\S+)[ \t]*$")
GUARD_ENTRY = {
    "matcher": "Agent|Task",
    "hooks": [{"type": "command", "command": 'python "$CLAUDE_PROJECT_DIR/' + HOOK_REL + '"'}],
}


def parse_model(text):
    """Return the frontmatter model value of an agent file, or None."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return None
    match = MODEL_RE.search(parts[1])
    return match.group(1) if match else None


def parse_effort(text):
    """Return the frontmatter effort value of an agent file, or None."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return None
    match = EFFORT_RE.search(parts[1])
    return match.group(1) if match else None


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_policy(policy):
    if not isinstance(policy, dict):
        return ["MODEL_POLICY.json must be an object"]
    errors = []
    unknown, missing = set(policy) - set(POLICY_KEYS), set(POLICY_KEYS) - set(policy)
    if unknown:
        errors.append(f"MODEL_POLICY.json unknown keys: {sorted(unknown)}")
    if missing:
        errors.append(f"MODEL_POLICY.json missing keys: {sorted(missing)}")
    for key, kind in POLICY_KEYS.items():
        if key in policy:
            value = policy[key]
            ok = _is_int(value) if kind is int else isinstance(value, kind)
            if not ok:
                errors.append(f"MODEL_POLICY.json {key} must be {kind.__name__}")
    if errors:
        return errors
    if policy["orchestrator"] != "opus":
        errors.append("MODEL_POLICY.json orchestrator must be opus")
    ex = policy["executors"]
    if not all(isinstance(x, str) for x in ex) or len(ex) != len(set(ex)) or set(ex) != EXECUTORS:
        errors.append("MODEL_POLICY.json executors must be exactly sonnet and haiku, no duplicates")
    if policy["allow_inherit"] is not False:
        errors.append("MODEL_POLICY.json allow_inherit must be false")
    if policy["allow_executor_opus"] is not False:
        errors.append("MODEL_POLICY.json allow_executor_opus must be false")
    if not 1 <= policy["default_parallel_agents"] <= policy["max_parallel_agents"] <= 3:
        errors.append("MODEL_POLICY.json requires 1 <= default_parallel_agents <= max_parallel_agents <= 3")
    ef = policy["executor_efforts"]
    if (not ef or not all(isinstance(x, str) and x in EFFORTS for x in ef)
            or len(ef) != len(set(ef))):
        errors.append("MODEL_POLICY.json executor_efforts must list unique values from low, medium, high")
    elif policy["default_executor_effort"] not in ef:
        errors.append("MODEL_POLICY.json default_executor_effort must be one of executor_efforts")
    if not 0 <= policy["max_retries"] <= 2:
        errors.append("MODEL_POLICY.json max_retries must be between 0 and 2")
    return errors


def validate_agents(directory):
    directory = Path(directory)
    errors, opus = [], []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        model, effort = parse_model(text), parse_effort(text)
        if model == "opus" and path.stem == "orchestrator":
            if effort not in ORCHESTRATOR_EFFORTS:
                errors.append(f"{path}: orchestrator must declare `effort: high` or `effort: medium`")
        elif model in EXECUTORS and effort not in EFFORTS:
            errors.append(f"{path}: executor must declare `effort:` low, medium or high (MODEL_POLICY.json executor_efforts)")
        if model is None:
            errors.append(f"{path}: forbidden or missing model")
        elif model == "opus":
            opus.append(path.stem)
            if path.stem != "orchestrator":
                errors.append(f"{path}: executor must not use opus")
        elif model not in EXECUTORS:
            errors.append(f"{path}: model `{model}` is not sonnet or haiku (no inherit, aliases or full IDs)")
    if opus != ["orchestrator"]:
        errors.append(f"Exactly one opus agent (orchestrator) is required, found: {opus}")
    return errors


def _covers(matcher, name):
    try:
        return re.fullmatch(matcher, name) is not None
    except re.error:
        return False


def has_model_guard(settings):
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    entries = hooks.get("PreToolUse") if isinstance(hooks, dict) else None
    if not isinstance(entries, list):
        return False
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("matcher"), str):
            continue
        if not (_covers(entry["matcher"], "Agent") and _covers(entry["matcher"], "Task")):
            continue
        for hook in entry.get("hooks") or []:
            if isinstance(hook, dict) and HOOK_REL in str(hook.get("command", "")):
                return True
    return False


def validate_settings(settings, root=None):
    if not isinstance(settings, dict):
        return ["settings.json must be an object"]
    errors = []
    if settings.get("model") != "opus":
        errors.append("settings.json model must be opus")
    env = settings.get("env", {})
    if not isinstance(env, dict):
        errors.append("settings.json env must be an object")
        env = {}
    for key in FORBIDDEN_ENV:
        if key in env:
            errors.append(f"settings.json env must not set {key}")
    if env.get(SUBAGENT_ENV) not in EXECUTORS:
        errors.append(f"settings.json env.{SUBAGENT_ENV} is required and must be sonnet or haiku")
    if not has_model_guard(settings):
        errors.append("settings.json lacks the PreToolUse model_guard hook (matcher Agent|Task)")
    if root is not None and not (Path(root) / HOOK_REL).is_file():
        errors.append(f"Missing hook file: {HOOK_REL}")
    return errors


def check_runtime_env(environ):
    problems = [f"Environment variable {key} must not be set (it overrides the model policy)"
                for key in FORBIDDEN_ENV if key in environ]
    if SUBAGENT_ENV in environ and environ[SUBAGENT_ENV] not in EXECUTORS:
        problems.append(f"Environment variable {SUBAGENT_ENV} must be sonnet or haiku")
    return problems


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
