#!/usr/bin/env python3
"""Deterministic starter utilities for My Agent Skill Hub. No LLM/API required."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys

try:
    from .project_install import install
    from .integrations import status as integration_status
    from .bootstrap import bootstrap, launch
    from . import model_policy as mp
    from . import doctor as doctor_mod
except ImportError:
    from project_install import install
    from integrations import status as integration_status
    from bootstrap import bootstrap, launch
    import model_policy as mp
    import doctor as doctor_mod
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills"
RUNTIMES = [ROOT / ".claude" / "skills", ROOT / ".agents" / "skills"]
REQUIRED = (
    "AGENTS.md", "CLAUDE.md", "README.md", "MODEL_POLICY.json", ".claude/settings.json",
    ".claude/hooks/model_guard.py",
    "docs/GOVERNANCE.md", "docs/WORK_LOG.md", "docs/CHANGELOG.md",
    "docs/EXCEPTIONS.md", "docs/ARCHITECTURE.md",
    "templates/project/PROJECT_BRIEF.md",
    "templates/project/STACK_DECISION.md",
    "templates/project/WORK_LOG.md",
    "templates/project/QUALITY_REPORT.md",
    "templates/project/HANDOFF.md",
    "templates/project/AGENT_RUNS.md",
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


def check_agent_skills(path: Path, known_skills: set[str]) -> list[str]:
    """Cada agente ejecutable debe precargar skills existentes (campo `skills`),
    incluir las obligatorias y exigir el bloque `### Run report` en su entrega."""
    content = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    front = content.split("---\n", 2)[1] if content.startswith("---\n") else ""
    block = re.search(r"(?m)^skills:\n((?:  - [a-z0-9-]+\n?)+)", front)
    if not block:
        return [f"{path}: missing `skills` frontmatter list"]
    listed = re.findall(r"  - ([a-z0-9-]+)", block.group(1))
    errors = [f"{path}: unknown skill `{s}`" for s in listed if s not in known_skills]
    missing = MANDATORY_SKILLS - set(listed)
    if missing:
        errors.append(f"{path}: missing mandatory skills {sorted(missing)}")
    if "### Run report" not in content:
        errors.append(f"{path}: missing `### Run report` contract")
    return errors


def check_external_pins(root: Path, notes: list[str] | None = None) -> list[str]:
    """.gitmodules == registry repositories == gitlinks == pins in docs."""
    notes = notes if notes is not None else []
    errors = []
    gm_path = root / ".gitmodules"
    gm = gm_path.read_text(encoding="utf-8") if gm_path.is_file() else ""
    paths = set(re.findall(r"(?m)^\s*path\s*=\s*(\S+)\s*$", gm))
    registry = {f"external/{r}" for r in load_json(root / "registry/integrations.json")["repositories"]}
    if paths != registry:
        errors.append(f"External pins: .gitmodules vs registry differ: {sorted(paths ^ registry)}")
    doc_path = root / "docs/EXTERNAL_INTEGRATIONS.md"
    doc_text = doc_path.read_text(encoding="utf-8") if doc_path.is_file() else ""
    docs = dict(re.findall(r"`(external/[^`]+)`:\s*`([0-9a-f]{40})`", doc_text))
    if set(docs) != registry:
        errors.append("External pins: docs/EXTERNAL_INTEGRATIONS.md vs registry differ: "
                      f"{sorted(set(docs) ^ registry)}")
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=30)
        inside = top.returncode == 0 and Path(top.stdout.strip()).resolve() == root.resolve()
    except (OSError, subprocess.SubprocessError):
        inside = False
    if not inside:
        notes.append("external pin gitlink check skipped: not inside a git checkout")
        return errors
    tree = subprocess.run(["git", "-C", str(root), "ls-tree", "HEAD", "external/"],
                          capture_output=True, text=True, timeout=30)
    links = {}
    for line in tree.stdout.splitlines():
        meta, _, name = line.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[0] == "160000":
            links[name] = parts[2]
    if set(links) != registry:
        errors.append(f"External pins: gitlinks vs registry differ: {sorted(set(links) ^ registry)}")
    for name in sorted(set(links) & set(docs)):
        if links[name] != docs[name]:
            errors.append(f"External pin mismatch for {name}: gitlink {links[name]} != docs {docs[name]}")
    return errors


def validate(root: Path = ROOT, notes: list[str] | None = None) -> list[str]:
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
                errors += check_agent_skills(path, actual_skills)
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
    errors += mp.validate_policy(load_json(root / "MODEL_POLICY.json"))
    errors += mp.validate_settings(load_json(root / ".claude/settings.json"), root)
    errors += mp.validate_agents(root / ".claude/agents")
    errors += check_external_pins(root, notes)
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
    install(ROOT, destination, fetch_external=False)
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
    diag = sub.add_parser("doctor")
    diag.add_argument("--json", action="store_true")
    sub.add_parser("validate")
    sub.add_parser("sync")
    boot = sub.add_parser("bootstrap")
    boot.add_argument("--target", required=True, type=Path)
    boot.add_argument("--no-fetch", action="store_true")
    boot.add_argument("--no-runtime-mcp-scan", action="store_true")
    start = sub.add_parser("launch")
    start.add_argument("--target", required=True, type=Path)
    integration = sub.add_parser("integrations")
    integration.add_argument("--target", required=True, type=Path)
    setup = sub.add_parser("install")
    setup.add_argument("--target", required=True, type=Path)
    setup.add_argument("--profile", choices=("full", "core"), default="full")
    setup.add_argument("--no-fetch", action="store_true")
    setup.add_argument("--no-runtime-mcp-scan", action="store_true")
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
        if args.cmd == "doctor":
            checks = doctor_mod.doctor(ROOT, lambda notes: validate(ROOT, notes))
            if args.json:
                print(json.dumps(checks, indent=2))
            else:
                print(doctor_mod.format_checks(checks))
            return 1 if any(c["status"] == "FAIL" for c in checks) else 0
        if args.cmd == "validate":
            notes = []
            errors = validate(ROOT, notes)
            for note in notes:
                print("NOTE:", note)
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
        if args.cmd == "bootstrap":
            report = bootstrap(ROOT, args.target, not args.no_fetch, runtime_scan=not args.no_runtime_mcp_scan)
            print(json.dumps(report, indent=2))
            return 1 if report["static_errors"] else 0
        if args.cmd == "launch":
            return launch(args.target)
        if args.cmd == "integrations":
            print(json.dumps(integration_status(ROOT, args.target), indent=2))
            return 0
        if args.cmd == "install":
            print(json.dumps(install(ROOT, args.target, args.profile, not args.no_fetch,
                                        runtime_scan=not args.no_runtime_mcp_scan), indent=2))
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
    except (ValueError, FileExistsError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
