"""One-command project bootstrap and truthful local diagnostics."""
import json
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

try:
    from .project_install import install, digest
    from .integrations import status
except ImportError:
    from project_install import install, digest
    from integrations import status

def verify_project(target):
    target=Path(target).resolve()
    manifest=json.loads((target/".agent-hub/manifest.json").read_text(encoding="utf-8"))
    errors=[]
    for rel, expected in manifest["files"].items():
        p=target/rel
        if not p.resolve().is_relative_to(target) or not p.is_file() or digest(p.read_bytes())!=expected:
            errors.append("Missing or changed managed file: "+rel)
    agents=target/".claude/agents"
    for p in agents.glob("*.md"):
        front=p.read_text(encoding="utf-8").split("---",2)
        match=re.search(r"(?m)^model:\s*(\S+)\s*$",front[1]) if len(front)==3 else None
        allowed={"opus"} if p.stem=="orchestrator" else {"sonnet","haiku"}
        if not match or match.group(1) not in allowed:
            errors.append("Invalid agent model: "+p.name)
    return errors

def probe_memory():
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open("http://127.0.0.1:3111/agentmemory/health",timeout=3) as response:
            return {"http_status":response.status,"state":"endpoint-reachable; persistence and isolation unverified"}
    except (OSError,ValueError):
        return {"state":"unreachable"}

def bootstrap(root,target,fetch_external=True):
    root,target=Path(root).resolve(),Path(target).resolve()
    result=install(root,target,fetch_external=fetch_external)
    errors=verify_project(target)
    report={"installation":result,"static_errors":errors,"environment":status(root,target),
            "agentmemory":probe_memory(),
            "openviking":"provider, isolated server and retrieval test required",
            "ecc":"review project-local hooks and model routing before activation",
            "mcp":"configuration only; interactive authentication and tool calls required",
            "model_runtime":"not verified"}
    report["ready"]=False
    path=target/".agent-hub/bootstrap-report.json"
    if path.is_symlink():
        raise ValueError("Unsafe report path")
    path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

def launch(target):
    target=Path(target).resolve()
    errors=verify_project(target)
    if errors:
        raise ValueError("; ".join(errors))
    executable=shutil.which("claude")
    if not executable:
        raise ValueError("Claude Code not on PATH")
    return subprocess.call([executable,"--agent","orchestrator","--model","opus"],cwd=target)
