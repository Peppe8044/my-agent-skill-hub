"""One-command project bootstrap and truthful local diagnostics."""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

try:
    from .project_install import install, digest, lp
    from .integrations import status
    from . import model_policy as mp
except ImportError:
    from project_install import install, digest, lp
    from integrations import status
    import model_policy as mp

INCOMING = ".agent-hub/incoming"

def check_target_settings(target):
    path=Path(target)/".claude/settings.json"
    if not path.is_file():
        return ["Missing .claude/settings.json"]
    try:
        settings=json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return ["Invalid JSON in .claude/settings.json: "+str(exc)]
    return mp.validate_settings(settings,target)

def pending_reconciliation(target):
    base=Path(target)/INCOMING
    if not base.is_dir():
        return []
    return sorted(p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file())

def verify_project(target):
    target=Path(target).resolve()
    manifest=json.loads((target/".agent-hub/manifest.json").read_text(encoding="utf-8"))
    errors=[]
    merged=set(manifest.get("merged",[]))
    for rel, expected in manifest["files"].items():
        if rel in merged:
            continue
        p=target/rel
        if not p.resolve().is_relative_to(target) or not lp(p).is_file() or digest(lp(p).read_bytes())!=expected:
            errors.append("Missing or changed managed file: "+rel)
    policy=target/"MODEL_POLICY.json"
    if policy.is_file():
        try:
            errors+=mp.validate_policy(json.loads(policy.read_text(encoding="utf-8")))
        except ValueError as exc:
            errors.append("Invalid MODEL_POLICY.json: "+str(exc))
    errors+=mp.validate_agents(target/".claude/agents")
    errors+=check_target_settings(target)
    return errors

def probe_memory():
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open("http://127.0.0.1:3111/agentmemory/health",timeout=3) as response:
            return {"http_status":response.status,"state":"endpoint-reachable; persistence and isolation unverified"}
    except (OSError,ValueError):
        return {"state":"unreachable"}

def bootstrap(root,target,fetch_external=True,*,runtime_scan=True,home=None,runner=None,which=None):
    root,target=Path(root).resolve(),Path(target).resolve()
    result=install(root,target,fetch_external=fetch_external,home=home,runtime_scan=runtime_scan,runner=runner,which=which)
    errors=verify_project(target)
    report={"installation":result,"static_errors":errors,"environment":status(root,target),
            "agentmemory":probe_memory(),
            "openviking":"provider, isolated server and retrieval test required",
            "ecc":"review project-local hooks and model routing before activation",
            "mcp":"configuration only; interactive authentication and tool calls required",
            "model_runtime":"not verified"}
    pending=pending_reconciliation(target)
    report["pending_reconciliation"]=pending
    blockers=[]
    if pending:
        blockers.append("pending_reconciliation: review .agent-hub/incoming")
    if errors:
        blockers.append("policy or integrity checks failed")
    blockers.append("model runtime not verified")
    report["ready_blockers"]=blockers
    report["ready"]=False
    path=target/".agent-hub/bootstrap-report.json"
    if path.is_symlink():
        raise ValueError("Unsafe report path")
    path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

def update(root,target,fetch_external=False,*,runtime_scan=False,home=None,runner=None,which=None):
    """Safe update of an installed project: same profile, project values for tunable keys kept."""
    root,target=Path(root).resolve(),Path(target).resolve()
    manifest=target/".agent-hub/manifest.json"
    if not manifest.is_file():
        raise ValueError("Not an Agent Hub project (no .agent-hub/manifest.json); use install")
    profile=json.loads(manifest.read_text(encoding="utf-8")).get("profile","full")
    result=install(root,target,profile,fetch_external,home=home,runtime_scan=runtime_scan,runner=runner,which=which)
    return {"installation":result,"static_errors":verify_project(target),
            "pending_reconciliation":pending_reconciliation(target)}
def verify_hub(root):
    """The central hub has no install manifest; it is checked with the hub validators instead."""
    try:
        from . import hub
    except ImportError:
        import hub
    return hub.validate(Path(root).resolve())

def launch(target,environ=None,phase=None,root=None):
    environ=os.environ if environ is None else environ
    problems=mp.check_runtime_env(environ)
    target=Path(target).resolve()
    root=Path(__file__).resolve().parents[1] if root is None else Path(root).resolve()
    if target!=root and (target/".agent-hub/manifest.json").is_file() and not problems:
        # Every launch applies the current central rules (policy, hooks, agents, skills, budget).
        report=update(root,target)
        if report["installation"]["conflicts"]:
            problems.append("update left changed managed files in .agent-hub/incoming: "
                            +", ".join(report["installation"]["conflicts"]))
    problems+=check_target_settings(target)
    if problems:
        for problem in problems:
            print("PROBLEM:",problem)
        return 3
    errors=verify_hub(target) if target==root else verify_project(target)
    if errors:
        raise ValueError("; ".join(errors))
    executable=shutil.which("claude")
    if not executable:
        raise ValueError("Claude Code not on PATH")
    # Pass the orchestrator's declared effort explicitly: a user-level modelSettings effort
    # (observed: xhigh) otherwise wins over the agent frontmatter for the main session.
    orchestrator=target/".claude/agents/orchestrator.md"
    effort=mp.parse_effort(orchestrator.read_text(encoding="utf-8")) if orchestrator.is_file() else None
    effort=effort if effort in mp.ORCHESTRATOR_EFFORTS else "medium"
    cmd=[executable,"--agent","orchestrator","--model","opus","--effort",effort]
    if phase:
        # The phase ledger survives sessions; a new phase id starts a new budget.
        code=subprocess.call([sys.executable,str(target/".claude/hooks/model_guard.py"),"--budget","start-phase",str(phase),"--keep-if-same","--project",str(target)])
        if code!=0:
            print("PROBLEM: model_guard start-phase failed with exit code",code)
            return 4
        cmd.append(f"Fase {phase}: usa docs/reports/LATEST_REPORT.md como traspaso; no releas fases anteriores ni repitas auditorias.")
    return subprocess.call(cmd,cwd=target)
