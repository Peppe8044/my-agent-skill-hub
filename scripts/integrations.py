"""Pinned external skills and project-local MCP configuration."""
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
