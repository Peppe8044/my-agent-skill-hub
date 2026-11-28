"""Pinned external skills and project-local MCP configuration."""
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.STDOUT)

def approved_files(root, approvals=None):
    root = Path(root).resolve()
    config = json.loads((root/"registry/integrations.json").read_text(encoding="utf-8"))
    entries = config["approved_skills"] if approvals is None else approvals
    result = {}
    for item in entries:
        name, repo_name, rel, commit = (item[k] for k in ("name","repository","path","commit"))
        if not re.fullmatch(r"[a-z][a-z0-9-]+",name) or repo_name not in config["repositories"]:
            raise ValueError("Invalid skill approval")
        repo = root/"external"/repo_name
        skill = repo/rel
        if not skill.resolve().is_relative_to(repo.resolve()) or not (skill/"SKILL.md").is_file():
            raise ValueError("Approved skill not present: "+name)
        if git(repo,"rev-parse","HEAD").decode().strip()!=commit or git(repo,"status","--porcelain","--untracked-files=all").strip():
            raise ValueError("External checkout differs from reviewed clean revision: "+repo_name)
        tracked = git(repo,"ls-files","-z","--",rel).decode().split("\0")
        for filename in filter(None,tracked):
            src=repo/filename
            if not src.resolve().is_relative_to(skill.resolve()) or any(p.is_symlink() for p in [src,*src.parents] if p==repo or repo in p.parents):
                raise ValueError("Unsafe external file: "+filename)
            if not src.is_file():
                raise ValueError("External file not available: "+filename)
            relative=src.relative_to(skill).as_posix()
            for runtime in (".claude/skills",".agents/skills"):
                key=f"{runtime}/{name}/{relative}"
                if key in result:
                    raise ValueError("Duplicate external skill path: "+key)
                result[key]=src.read_bytes()
    return result

def mcp_config(root):
    config=json.loads((Path(root)/"registry/integrations.json").read_text(encoding="utf-8"))
    return {"mcpServers":config["project_mcp"]}

def status(root, target):
    root,target=Path(root),Path(target)
    config=json.loads((root/"registry/integrations.json").read_text(encoding="utf-8"))
    return {"tools":{x:bool(shutil.which(x)) for x in ("git","node","npm","npx","claude","uv","docker")},
            "repositories":{name:(root/"external"/name/"README.md").is_file() for name in config["repositories"]},
            "approved_skills":len(config["approved_skills"]),
            "project_mcp_configured":(target/".mcp.json").is_file(),
            "runtime_status":"not verified; authenticate and run live checks locally"}


# ------------------------------------------------- approved external capabilities
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
REGISTRY_REL = "registry/external_capabilities.json"


def load_external_registry(root):
    """Return the approved external capability registry, or None when absent."""
    path = Path(root) / REGISTRY_REL
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(REGISTRY_REL + " must be an object")
    return data


def _safe_rel(value):
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def _read_source(repo, rel):
    """Read a source file from a checkout, refusing symlinks and path escapes."""
    src = repo / rel
    chain = [src, *[p for p in src.parents if p != repo and repo in p.parents]]
    if any(p.is_symlink() for p in chain) or not src.resolve().is_relative_to(repo.resolve()):
        raise ValueError("unsafe path " + rel)
    if not src.is_file():
        raise ValueError("file missing " + rel)
    return src.read_bytes()


def repo_problem(root, name, info):
    """Return (kind, reason) when a repo cannot be used, else None."""
    if info.get("redistribution") != "allowed":
        return "forbidden", "redistribution %s: %s" % (info.get("redistribution"), info.get("reason", "no reason given"))
    repo = Path(root) / "external" / name
    if not (repo / ".git").exists():
        return "uninit", "submodule not initialized"
    try:
        head = git(repo, "rev-parse", "HEAD").decode().strip()
        dirty = git(repo, "status", "--porcelain", "--untracked-files=all").strip()
    except (subprocess.CalledProcessError, OSError):
        return "uninit", "submodule not readable"
    if head != info.get("commit"):
        return "mismatch", "commit %s differs from registry %s" % (head[:12], str(info.get("commit"))[:12])
    if dirty:
        return "mismatch", "checkout is not clean"
    return None


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def plan_external(root, reserved_names=(), executors=("sonnet", "haiku")):
    """Compute the approved external files to install, verifying every source.

    Returns a dict: files {rel: bytes}, meta {rel: provenance}, index [dict], catalog
    {id: {kind, name, files{name: bytes}, meta{name: provenance}}}, skipped {id: reason},
    counts, status, used_repos.
    """
    root = Path(root).resolve()
    out = {"files": {}, "meta": {}, "index": [], "catalog": {}, "skipped": {},
           "active_skills": 0, "catalog_skills": 0, "catalog_agents": 0,
           "status": "ok", "used_repos": []}
    try:
        registry = load_external_registry(root)
    except ValueError as exc:
        out["status"] = "unavailable: invalid registry (%s)" % exc
        return out
    if registry is None:
        out["status"] = "unavailable: registry missing"
        return out
    repos = registry.get("repositories") or {}
    items = [("skill", i) for i in registry.get("skills") or []] + \
            [("agent", i) for i in registry.get("agents") or []]
    items.sort(key=lambda pair: str(pair[1].get("id")))
    problems = {}
    for name in sorted({str(i.get("repo")) for _, i in items}):
        info = repos.get(name)
        problems[name] = (repo_problem(root, name, info) if isinstance(info, dict)
                          else ("mismatch", "repository not in registry"))
    considered = [p for p in problems.values() if not (p and p[0] == "forbidden")]
    if considered and all(p and p[0] == "uninit" for p in considered):
        out["status"] = "unavailable: submodules not initialized"
        return out
    taken = set(reserved_names)
    for kind, item in items:
        iid = str(item.get("id"))
        try:
            if not SAFE_ID.fullmatch(iid) or not SAFE_ID.fullmatch(str(item.get("name"))):
                raise ValueError("invalid id or name")
            problem = problems.get(str(item.get("repo")))
            if problem:
                raise ValueError(problem[1])
            tier, name = item.get("tier"), item["name"]
            repo = root / "external" / item["repo"]
            info = repos[item["repo"]]
            if not _safe_rel(item.get("path")):
                raise ValueError("unsafe path")
            if kind == "skill":
                if tier not in ("active", "catalog"):
                    raise ValueError("invalid tier")
                if tier == "active" and name in taken:
                    raise ValueError("skill name collision: " + name)
                sums = item.get("sha256") or {}
                names = item.get("files") or []
                if "SKILL.md" not in names or set(names) != set(sums):
                    raise ValueError("incomplete file list")
                blobs = {}
                for fname in names:
                    if not _safe_rel(fname):
                        raise ValueError("unsafe path")
                    data = _read_source(repo, item["path"] + "/" + fname)
                    if _sha(data) != sums[fname]:
                        raise ValueError("sha256 mismatch: " + fname)
                    blobs[fname] = data
                if tier == "active":
                    installed = ".claude/skills/" + name
                    dests = {"%s/%s/%s" % (rt, name, f): f
                             for rt in (".claude/skills", ".agents/skills") for f in blobs}
                else:
                    installed = ".agent-hub/catalog/skills/" + iid
                    dests = {"%s/%s" % (installed, f): f for f in blobs}
                srcs = {f: "external/%s/%s/%s" % (item["repo"], item["path"], f) for f in blobs}
            else:
                if tier != "catalog":
                    raise ValueError("agents are catalog-only")
                if item.get("model") not in executors:
                    raise ValueError("agent model not in MODEL_POLICY executors")
                data = _read_source(repo, item["path"])
                if _sha(data) != item.get("sha256"):
                    raise ValueError("sha256 mismatch")
                blobs = {"agent.md": data}
                installed = ".agent-hub/catalog/agents/%s.md" % iid
                dests = {installed: "agent.md"}
                srcs = {"agent.md": "external/%s/%s" % (item["repo"], item["path"])}
        except (ValueError, KeyError, OSError, TypeError) as exc:
            out["skipped"][iid] = str(exc)
            continue
        if kind == "skill" and tier == "active":
            taken.add(name)
        commit = info["commit"]
        lic = item.get("license", info.get("license"))
        for rel, fname in dests.items():
            out["files"][rel] = blobs[fname]
            out["meta"][rel] = {"repo": item["repo"], "commit": commit, "source": srcs[fname],
                                "sha256": _sha(blobs[fname]), "license": lic, "id": iid}
        if item["repo"] not in out["used_repos"]:
            out["used_repos"].append(item["repo"])
        out["index"].append({"id": iid, "kind": kind, "name": name, "tier": tier,
                             "domains": item.get("domains", []), "license": lic,
                             "repo": item["repo"], "commit": commit, "path": installed,
                             "description": item.get("description", "")})
        if tier == "catalog":
            out["catalog"][iid] = {"kind": kind, "name": name, "files": blobs,
                                   "meta": {f: out["meta"][r] for r, f in dests.items()}}
        counter = "active_skills" if tier == "active" else ("catalog_skills" if kind == "skill" else "catalog_agents")
        out[counter] += 1
    for repo_name in out["used_repos"]:
        for lic_file in repos[repo_name].get("license_files") or []:
            try:
                data = _read_source(root / "external" / repo_name, lic_file)
            except (ValueError, OSError):
                continue
            rel = ".agent-hub/catalog/licenses/%s/%s" % (repo_name, Path(lic_file).name)
            out["files"][rel] = data
            out["meta"][rel] = {"repo": repo_name, "commit": repos[repo_name]["commit"],
                                "source": "external/%s/%s" % (repo_name, lic_file), "sha256": _sha(data),
                                "license": repos[repo_name].get("license"), "id": repo_name + ":license"}
    out["index"].sort(key=lambda e: e["id"])
    return out
