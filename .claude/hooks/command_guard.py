#!/usr/bin/env python3
"""PreToolUse guard for Bash and PowerShell commands.

Exit 2 with a one-line stderr reason denies. A JSON "ask" goes to stdout with exit 0.
Anything else is allowed. Malformed hook input fails closed (exit 2).
"""
import json
import re
import sys

HOOK = "command_guard"
TOOLS = {"Bash", "PowerShell"}
TAMPER_TARGET = re.compile(
    r"model_guard|MODEL_POLICY\.json|\.claude[\\/]settings\.json|\.claude[\\/]hooks[\\/]", re.I)
TAMPER_ACTION = re.compile(
    r"\b(rm|del|erase|rd|rmdir|remove-item|mv|move|sed\s+-i|set-content|out-file)\b|>", re.I)

DENY = [
    (r"\brm\s+(?=.*(?:-[a-z]*r|--recursive))(?:-\S+\s+)*(?:/\*?|~/?|\$HOME/?|\.\.[\\/]?)(?=\s|$|[;&|])",
     "recursive delete of root, home or parent directory"),
    (r"\bremove-item\b(?=.*-recurse\b).*\s(?:[a-z]:[\\/]*|\\\\|~[\\/]*|\$home[\\/]*|\$env:userprofile[\\/]*|\\)\*?"
     r"(?=\s*(?:$|[;&|]|\s-\w))",
     "recursive Remove-Item on a drive, home or UNC root"),
    (r"\b(?:del|erase|rd|rmdir)\s+.*?/s\b.*?\s(?:[a-z]:|\\)[\\/]*\*?\s*(?:$|[;&|])",
     "recursive delete of a drive root"),
    (r"\bformat\s+[a-z]:", "disk format"),
    (r"\bformat-volume\b|\bdiskpart\b|\bmkfs(?:\.\w+)?\b", "disk format or partition tool"),
    (r"\b(?:curl|wget)\b[^|]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b", "remote script piped to shell"),
    (r"\b(?:iwr|irm|invoke-webrequest|invoke-restmethod)\b[^|]*\|\s*(?:iex|invoke-expression)\b",
     "remote script piped to Invoke-Expression"),
    (r"\bgit\s+config\s+--global\b", "global git config change"),
    (r"\bsetx\s", "persistent environment variable change"),
    (r"\[environment\]::setenvironmentvariable\(.*['\"](?:user|machine)['\"]",
     "persistent environment variable change"),
    (r"\breg\s+add\b", "registry write"),
    (r"\bset-itemproperty\b.*\b(?:hklm|hkcu):", "registry write"),
    (r"\bdisableallhooks\b", "disabling hooks"),
]

ASK = [
    (r"\bgit\s+push\b.*(?:--force\b|\s-f\b)", "force push rewrites remote history"),
    (r"\bgit\s+reset\s+--hard\b", "hard reset discards local changes"),
    (r"\bgit\s+clean\s+-(?=\w*f)(?=\w*x)\w+", "git clean -fdx removes ignored files"),
    (r"\bnpm\s+(?:i|install)\b.*\s(?:-g|--global)\b", "global npm install"),
    (r"\bpip3?\s+install\b.*--user\b|\bpipx\s+install\b|\bwinget\s+install\b|\bchoco\s+install\b"
     r"|\bscoop\s+install\b|\buv\s+tool\s+install\b|\bcargo\s+install\b",
     "global or user-level package install"),
]


def classify(cmd):
    for pattern, reason in DENY:
        if re.search(pattern, cmd, re.I):
            return "deny", reason
    if TAMPER_TARGET.search(cmd) and TAMPER_ACTION.search(cmd):
        return "deny", "tampering with guard, model policy or hook files"
    for pattern, reason in ASK:
        if re.search(pattern, cmd, re.I):
            return "ask", reason
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
    tool_input = data.get("tool_input")
    cmd = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(cmd, str):
        return malformed("no command string")
    verdict, reason = classify(cmd)
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
