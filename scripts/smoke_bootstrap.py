#!/usr/bin/env python3
"""End-to-end bootstrap smoke check: python scripts/smoke_bootstrap.py <dir> [--fetch].

Creates (or reuses) a project directory, runs bootstrap twice with the runtime MCP scan
disabled, exercises the catalog helper and prints one JSON object. Exit 0 only if every
expectation holds. The directory is never deleted.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import model_policy as mp  # noqa: E402
from scripts.bootstrap import bootstrap, verify_project  # noqa: E402

EXPECT_AGENTS, EXPECT_SKILLS = 30, 43


def snapshot(target):
    skip = {".agent-hub/bootstrap-report.json"}
    return {p.relative_to(target).as_posix(): p.read_bytes()
            for p in target.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(target).parts
            and p.relative_to(target).as_posix() not in skip}


def backups(target):
    base = target / ".agent-hub/backups"
    return sorted(p.name for p in base.iterdir()) if base.is_dir() else []


def helper(target, *args):
    proc = subprocess.run([sys.executable, str(target / ".agent-hub/bin/catalog.py"), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          cwd=str(target), timeout=60)
    return proc.returncode, proc.stdout.strip()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    fetch = "--fetch" in argv
    argv = [a for a in argv if a != "--fetch"]
    if len(argv) != 1:
        print("usage: smoke_bootstrap.py <dir> [--fetch]", file=sys.stderr)
        return 2
    target = Path(argv[0]).resolve()
    target.mkdir(parents=True, exist_ok=True)
    if not (target / ".git").exists():
        subprocess.run(["git", "init", "-q", str(target)], check=False, timeout=60)
    first = bootstrap(ROOT, target, fetch_external=fetch, runtime_scan=False)
    after_first, backups_first = snapshot(target), backups(target)
    second = bootstrap(ROOT, target, fetch_external=False, runtime_scan=False)
    after_second = snapshot(target)
    changed = sorted(k for k in set(after_first) | set(after_second) if after_first.get(k) != after_second.get(k))
    hub_skills = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    claude_skills = sorted(p.name for p in (target / ".claude/skills").iterdir() if p.is_dir())
    dupes = sorted({n for n in claude_skills if claude_skills.count(n) > 1})
    ext = first["installation"]["external"]
    index_path = target / ".agent-hub/catalog/index.jsonl"
    entries = ([json.loads(x) for x in index_path.read_text(encoding="utf-8").splitlines() if x.strip()]
               if index_path.is_file() else [])
    licenses_dir = target / ".agent-hub/catalog/licenses"
    settings = json.loads((target / ".claude/settings.json").read_text(encoding="utf-8"))
    report = {
        "own_agents": len(list((target / ".claude/agents").glob("*.md"))),
        "own_skills": len(hub_skills & set(claude_skills)),
        "external_status": ext["status"],
        "active_external_skills": ext["active_skills"],
        "catalog_skills": ext["catalog_skills"],
        "catalog_agents": ext["catalog_agents"],
        "external_skipped": len(ext["skipped"]),
        "licenses_copied": len([p for p in licenses_dir.rglob("*") if p.is_file()]) if licenses_dir.is_dir() else 0,
        "duplicate_skill_names": dupes,
        "verify_errors": verify_project(target),
        "guard_file": (target / mp.HOOK_REL).is_file(),
        "guard_registered": mp.has_model_guard(settings),
        "settings_model": settings.get("model"),
        "subagent_env": settings.get("env", {}).get(mp.SUBAGENT_ENV),
        "second_run": {"changed_files": changed, "conflicts": second["installation"]["conflicts"],
                       "new_backups": len(backups(target)) - len(backups_first),
                       "backup": second["installation"]["backup"]},
        "catalog_search": [], "enable_disable": "skipped",
    }
    ok = (report["own_agents"] == EXPECT_AGENTS and report["own_skills"] == EXPECT_SKILLS
          and not dupes and not report["verify_errors"] and report["guard_file"]
          and report["guard_registered"] and report["settings_model"] == "opus"
          and report["subagent_env"] in mp.EXECUTORS
          and not changed and not second["installation"]["conflicts"]
          and report["second_run"]["new_backups"] == 0)
    if ext["status"] == "ok":
        term = entries[0]["name"].split("-")[0] if entries else "skill"
        code, out = helper(target, "search", term, "--limit", "3")
        report["catalog_search"] = out.splitlines()[:3]
        pick = next((e for e in entries if e["tier"] == "catalog" and e["kind"] == "skill"), None)
        trip = False
        if pick:
            c1, _ = helper(target, "enable", pick["id"])
            present = (target / ".claude/skills" / pick["name"] / "SKILL.md").is_file()
            c2, _ = helper(target, "disable", pick["id"])
            trip = c1 == 0 and present and c2 == 0 and not (target / ".claude/skills" / pick["name"]).exists()
            report["enable_disable"] = "ok" if trip else "FAILED"
        ok = ok and code == 0 and bool(report["catalog_search"]) and (trip or pick is None) \
            and not verify_project(target) and report["licenses_copied"] > 0
    else:
        report["note"] = "external capabilities unavailable; catalog checks skipped"
    report["ok"] = ok
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
