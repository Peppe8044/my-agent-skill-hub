"""Project-local installation; never execute upstream code automatically."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

try:
    from .integrations import approved_files, mcp_config
except ImportError:
    from integrations import approved_files, mcp_config

def digest(data):
    return hashlib.sha256(data).hexdigest()

def install(root, target, profile="full", fetch_external=True):
    root, target = Path(root).resolve(), Path(target).resolve()
    if target == root or root in target.parents and target.parent != root / "workspaces":
        # Nested workspaces are supported, but never overwrite the hub itself.
        if target == root or root / "external" in target.parents:
            raise ValueError("Unsafe installation target")
    if profile not in {"full", "core"}:
        raise ValueError("Unknown installation profile")
    if fetch_external and profile == "full":
        subprocess.run(["git", "-C", str(root), "submodule", "update", "--init"], check=True)
    files = {}
    def add(rel, data):
        files[str(rel).replace("\\", "/")] = data
    for rel in ("AGENTS.md", "CLAUDE.md", "MODEL_POLICY.json", ".claude/settings.json"):
        add(rel, (root / rel).read_bytes())
    for src in sorted((root / ".claude/agents").glob("*.md")):
        add(src.relative_to(root), src.read_bytes())
    for folder in ("skills",):
        for src in sorted((root / folder).glob("*/SKILL.md")):
            for runtime in (".claude/skills", ".agents/skills"):
                add(f"{runtime}/{src.parent.name}/SKILL.md", src.read_bytes())
    if profile == "full":
        for rel, data in approved_files(root).items():
            if rel in files:
                raise ValueError("External skill conflicts with hub skill: " + rel)
            add(rel, data)
        add(".mcp.json", (json.dumps(mcp_config(root), indent=2)+"\n").encode())
    catalog = []
    if profile == "full":
        for repo in sorted((root / "external").iterdir()) if (root / "external").exists() else []:
            if not repo.is_dir() or repo.is_symlink():
                continue
            for src in sorted(repo.rglob("SKILL.md")):
                if src.is_symlink() or not src.is_file() or ".git" in src.relative_to(repo).parts:
                    continue
                catalog.append({"source": repo.name, "path": src.relative_to(repo).as_posix(), "status": "review-required"})
    add(".agent-hub/external-catalog.json", (json.dumps(catalog, indent=2)+"\n").encode())
    add(".agent-hub/README.md", b"# Agent Hub\nOwn agents and skills are installed. External catalog entries require review before activation; MCP services need their own setup. Start Claude with: claude --agent orchestrator --model opus\n")
    manifest_path = target / ".agent-hub/manifest.json"
    def safe_path(rel):
        p = target / rel
        if not p.resolve().is_relative_to(target) or any(q.is_symlink() for q in [p, *p.parents] if q != target and target in q.parents):
            raise ValueError(f"Unsafe path: {rel}")
        return p
    safe_path(".agent-hub/manifest.json")
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": {}}
    conflicts = []
    for rel, data in files.items():
        p = safe_path(rel)
        if p.exists() and (not p.is_file() or (p.read_bytes() != data and previous["files"].get(rel) != digest(p.read_bytes()))):
            conflicts.append(rel)
    if conflicts:
        raise FileExistsError("Preserving existing files; reconcile before install: " + ", ".join(conflicts))
    # Preflight all paths before writing; no deletion of user files.
    for rel, data in files.items():
        p = safe_path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"profile": profile, "files": {k:digest(v) for k,v in files.items()}}, indent=2)+"\n", encoding="utf-8")
    return {"installed_files": len(files), "external_candidates": len(catalog), "external_activation": "review-required", "target": str(target)}
