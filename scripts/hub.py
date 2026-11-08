#!/usr/bin/env python3
"""Deterministic starter utilities for My Agent Skill Hub. No LLM/API required."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills"
RUNTIMES = [ROOT / ".claude" / "skills", ROOT / ".agents" / "skills"]
REQUIRED = (
    "AGENTS.md", "CLAUDE.md", "README.md",
    "docs/GOVERNANCE.md", "docs/WORK_LOG.md", "docs/CHANGELOG.md",
    "docs/EXCEPTIONS.md", "docs/ARCHITECTURE.md",
    "templates/project/PROJECT_BRIEF.md",
    "templates/project/STACK_DECISION.md",
    "templates/project/WORK_LOG.md",
    "templates/project/QUALITY_REPORT.md",
    "templates/project/HANDOFF.md",
    "stacks/catalog.json", "registry/agents.json", "registry/skills.json"
)
MANDATORY_SKILLS = {"documentation-ledger", "token-budget"}
PROJECT_KINDS = (
    "web", "api", "data-science", "data-pipeline", "automation", "sre",
    "ai", "mobile", "cli", "existing"
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def slug(value: str) -> str:
    value = value.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
        raise ValueError("Use a name of 1–64 lowercase letters, digits, hyphens or underscores")
    return value


def check_frontmatter(path: Path, expected_name: str) -> list[str]:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n") or "\n---\n" not in content[4:]:
        return [f"{path}: missing YAML frontmatter"]
    front = content.split("---\n", 2)[1]
    match_name = re.search(r"(?m)^name: ([a-z][a-z0-9-]+)\s*$", front)
    match_desc = re.search(r"(?m)^description:\s*(\S.+)$", front)
    errors = []
    if not match_name or match_name.group(1) != expected_name:
        errors.append(f"{path}: frontmatter name mismatch")
    if not match_desc:
        errors.append(f"{path}: missing nonempty description")
    return errors


def validate(root: Path = ROOT) -> list[str]:
    errors = [f"Missing required file: {p}" for p in REQUIRED if not (root / p).is_file()]
    if errors:
        return errors
    registered = load_json(root / "registry/skills.json")
    registered_names = {s["name"] for s in registered}
    actual_skills = {
        p.parent.name for p in (root / "skills").glob("*/SKILL.md")
    }
    if registered_names != actual_skills:
        errors.append(f"Skill registry differs from filesystem: {registered_names ^ actual_skills}")
    if not MANDATORY_SKILLS.issubset(actual_skills):
        errors.append("Mandatory skills missing: " + str(MANDATORY_SKILLS - actual_skills))
    for name in sorted(actual_skills):
        canonical = root / "skills" / name / "SKILL.md"
        errors += check_frontmatter(canonical, name)
        for runtime in (root / ".claude/skills", root / ".agents/skills"):
            target = runtime / name / "SKILL.md"
            if not target.is_file():
                errors.append(f"Missing runtime copy: {target}")
            elif target.read_bytes() != canonical.read_bytes():
                errors.append(f"Skill copy out of sync: {target} (run hub.py sync)")
    agents = load_json(root / "registry/agents.json")
    if not any(a["name"] == "documentation-keeper" for a in agents):
        errors.append("Missing mandatory documentation-keeper agent")
    for agent in agents:
        name = agent["name"]
        for key in ("profile_path", "claude_path"):
            path = root / agent[key]
            if not path.is_file():
                errors.append(f"Missing agent {name} path: {path}")
            elif key == "claude_path":
                errors += check_frontmatter(path, name)
    try:
        profiles = load_json(root / "stacks/catalog.json")
        if len({p["id"] for p in profiles}) != len(profiles):
            errors.append("Duplicate stack profiles")
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid stack catalog: {exc}")
    policy = (root / "AGENTS.md").read_text(encoding="utf-8")
    for name in MANDATORY_SKILLS:
        if name not in policy:
            errors.append(f"AGENTS.md missing mandatory skill route: {name}")
    return errors


def sync(root: Path = ROOT) -> int:
    count = 0
    for source in sorted((root / "skills").glob("*/SKILL.md")):
        for runtime in (root / ".claude/skills", root / ".agents/skills"):
            target = runtime / source.parent.name / "SKILL.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            count += 1
    return count


def new_project(name: str, kind: str, directory: Path | None = None) -> Path:
    slug_name = slug(name)
    if kind not in PROJECT_KINDS:
        raise ValueError(f"Unknown kind {kind}; choose from {PROJECT_KINDS}")
    output_root = (directory or ROOT / "workspaces").resolve()
    destination = output_root / slug_name
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing project: {destination}")
    destination.mkdir(parents=True, exist_ok=False)
    for src in sorted((ROOT / "templates/project").iterdir()):
        if src.is_file():
            shutil.copy2(src, destination / src.name)
    conf = load_json(destination / "project.json")
    conf["name"], conf["kind"] = slug_name, kind
    (destination / "project.json").write_text(
        json.dumps(conf, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return destination


def recommend(data: dict, root: Path = ROOT) -> list[dict]:
    kind = data.get("kind", "")
    if kind not in PROJECT_KINDS:
        raise ValueError(f"Unknown project kind: {kind}")
    req = data.get("requirements", {})
    results = []
    for p in load_json(root / "stacks/catalog.json"):
        score = 60 if kind in p["kind"] else 0
        tags = set(p["tags"])
        if req.get("has_ui") and "ui" in tags:
            score += 10
        if req.get("needs_api") and "api" in tags:
            score += 10
        if req.get("has_ml") and ("ml" in tags or "agents" in tags):
            score += 15
        if req.get("needs_automation") and "automation" in tags:
            score += 10
        if req.get("needs_persistence") and "persistence" in tags:
            score += 5
        if req.get("requires_offline") and "offline" in tags:
            score += 15
        if req.get("team_prefers_python") and "python" in tags:
            score += 10
        if req.get("team_prefers_typescript") and "typescript" in tags:
            score += 10
        if kind == "existing" and "existing" in tags:
            score += 25
        results.append({"id": p["id"], "score": score, "summary": p["summary"]})
    return sorted(results, key=lambda x: (-x["score"], x["id"]))


def check_docs(base: str) -> list[str]:
    if not re.fullmatch(r"[a-zA-Z0-9_./-]+", base):
        return ["Unsafe base ref"]
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        cwd=ROOT, check=False, capture_output=True, text=True
    )
    if proc.returncode:
        return [f"Cannot check PR docs against {base}: {proc.stderr.strip()}"]
    changed = set(proc.stdout.splitlines())
    if not changed:
        return []
    if changed.issubset({"docs/WORK_LOG.md", "docs/CHANGELOG.md"}):
        return []
    if "docs/EXCEPTIONS.md" in changed:
        if "docs/WORK_LOG.md" not in changed:
            return ["Exception still requires docs/WORK_LOG.md with approval and risks"]
        return []
    required = {"docs/WORK_LOG.md", "docs/CHANGELOG.md"}
    if changed.isdisjoint(required):
        return ["Missing mandatory documentation updates: docs/WORK_LOG.md and docs/CHANGELOG.md"]
    return [f"Missing documentation update: {path}" for path in sorted(required - changed)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor")
    sub.add_parser("validate")
    sub.add_parser("sync")
    make = sub.add_parser("new")
    make.add_argument("--name", required=True)
    make.add_argument("--kind", required=True, choices=PROJECT_KINDS)
    make.add_argument("--directory", type=Path)
    rank = sub.add_parser("recommend")
    rank.add_argument("--input", required=True, type=Path)
    rank.add_argument("--out", type=Path)
    checks = sub.add_parser("check-docs")
    checks.add_argument("--base", required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd in {"doctor", "validate"}:
            errors = validate()
            print(f"Agent profiles: {len(list((ROOT/'.claude/agents').glob('*.md')))}")
            print(f"Skills: {len(list((ROOT/'skills').glob('*/SKILL.md')))}")
            print(f"Stack profiles: {len(load_json(ROOT/'stacks/catalog.json'))}")
            for error in errors:
                print("ERROR:", error, file=sys.stderr)
            if errors:
                return 1
            print("PASS: library structure, registrations, skills, copies and required policies")
            return 0
        if args.cmd == "sync":
            print(f"Updated {sync()} skill runtime copies")
            return 0
        if args.cmd == "new":
            print(new_project(args.name, args.kind, args.directory))
            return 0
        if args.cmd == "recommend":
            result = recommend(load_json(args.input))
            content = (
                "# Stack candidates (heuristic, NOT approved)\n\n"
                "Scores only rank profiles and are not compatibility, price or quality benchmarks.\n\n"
                + "\n".join(f"- **{v['id']}** ({v['score']}): {v['summary']}" for v in result[:5])
                + "\n\nDecision requires comparison, context and approval in STACK_DECISION.md.\n"
            )
            if args.out:
                args.out.write_text(content, encoding="utf-8")
                print(f"Wrote: {args.out}")
            else:
                print(content)
            return 0
        if args.cmd == "check-docs":
            errors = check_docs(args.base)
            for error in errors:
                print("ERROR:", error, file=sys.stderr)
            if errors:
                return 1
            print("PASS: PR documentation ledger")
            return 0
    except (ValueError, FileExistsError, OSError, json.JSONDecodeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
