#!/usr/bin/env python3
"""Deterministic, read-only scanner for the pinned submodules in external/.

It only READS files (never executes, imports or installs anything from
external/). It inventories and classifies skills, agents, hooks, MCP, plugin
manifests, configs, scripts and dependencies, and generates the registry and
reports. Rules R1-R9 are documented in docs/SKILL_COMPATIBILITY_REPORT.md.

Usage: python scripts/external_scan.py [--check] [--root PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA = 1
GENERATED_BY = "scripts/external_scan.py"
OUT_INVENTORY = "registry/EXTERNAL_SKILLS_INVENTORY.json"
OUT_REGISTRY = "registry/external_capabilities.json"
OUT_REPORT = "docs/EXTERNAL_SKILLS_REPORT.md"
OUT_COMPAT = "docs/SKILL_COMPATIBILITY_REPORT.md"
OUT_LICENSES = "docs/LICENSE_REGISTRY.md"

PRUNE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache"}
ALLOWED_LICENSES = ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0",
                    "CC-BY-4.0", "CC-BY-SA-4.0", "Unlicense"]
CODE_EXTS = {".py", ".sh", ".bash", ".js", ".mjs", ".cjs", ".ts", ".ps1", ".bat", ".cmd", ".rb",
             ".go", ".exe", ".dll", ".so", ".bin"}
TEXT_EXTS = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".toml"}
REPO_PRIORITY = ["scientific-agent-skills", "Anthropic-Cybersecurity-Skills", "diagram-design", "ECC"]
REPO_RULES = {"agentmemory": "requires-service:agentmemory", "rea": "requires-toolchain:rea"}
NONCANON_SEGMENTS = {".kiro", ".cursor", ".cursor-plugin", ".agents", ".codex", "pi", "examples",
                     "tests", "fixtures"}
LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z]{2,4})?$")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MAX_SKILL_BYTES = 100 * 1024
MAX_ACTIVE = 14
JSON_SCAN_LIMIT = 512 * 1024
CONFIG_DIRS = {".claude-plugin", ".claude", ".cursor", ".cursor-plugin", ".kiro", ".codex"}
HARD_PREFIXES = ("license-not-allowed", "non-canonical-copy", "duplicate-of-own", "duplicate-of",
                 "requires-service", "requires-toolchain", "offensive-security", "unsafe-pattern",
                 "invalid-name", "description-too-short", "skill-too-large", "out-of-scope-domain",
                 "model-opus-not-allowed", "model-missing-or-inherit", "agent-config-not-allowed")

# ---------------------------------------------------------------- R9 domains
DOMAIN_ORDER = ["general", "data-science", "games", "web", "sre-devops", "security-defensive",
                "automation"]
DOMAIN_KEYWORDS = {
    "general": ["testing", "tdd", "unit test", "code review", "review", "refactor", "refactoring",
                "debugging", "debug", "git", "documentation", "architecture", "planning", "python",
                "typescript", "javascript", "golang", "rust", "java", "kotlin", "c#", "sql"],
    "data-science": ["data", "dataset", "statistics", "statistical", "pandas", "numpy", "scipy", "ml",
                     "machine learning", "notebook", "visualization", "bioinformatics", "genomics",
                     "chemistry", "scientific", "simulation"],
    "games": ["game", "godot", "unity", "unreal", "sprite", "shader", "level design", "gameplay",
              "steam"],
    "web": ["frontend", "backend", "react", "next.js", "nextjs", "vue", "svelte", "css", "html",
            "api", "http", "rest", "graphql", "django", "flask", "fastapi", "rails", "laravel",
            "node", "nodejs"],
    "sre-devops": ["docker", "kubernetes", "k8s", "terraform", "ansible", "ci/cd", "deploy",
                   "deployment", "monitoring", "observability", "incident", "aws", "azure", "gcp",
                   "helm", "linux", "nginx"],
    "security-defensive": ["security", "threat", "detection", "forensics", "incident response",
                           "vulnerability", "hardening", "siem", "soc", "compliance", "audit",
                           "malware analysis"],
    "automation": ["automation", "workflow", "scripting", "cron", "bot", "integration", "n8n",
                   "zapier", "scraping"],
}


def _kw_re(kw: str) -> re.Pattern:
    tail = "s?" if kw[-1].isalnum() else ""
    return re.compile(r"(?<![a-z0-9])" + re.escape(kw) + tail + r"(?![a-z0-9])")


DOMAIN_RES = {d: [_kw_re(k) for k in kws] for d, kws in DOMAIN_KEYWORDS.items()}

# ------------------------------------------------------------- R6 offensive
_STRONG = [r"exploit development", r"red[- ]team(?:ing|er|s)?", r"malware development",
           r"credential (?:dumping|harvesting)", r"password cracking", r"lateral movement",
           r"persistence mechanisms?", r"privilege escalation", r"keyloggers?", r"ddos",
           r"jailbreak(?:s|ing)?", r"phishing campaigns?", r"(?:av|edr|antivirus)[ /-]+(?:evasion )?bypass",
           r"command[- ]and[- ]control", r"c2"]
_WEAK = [r"payloads?", r"shellcode", r"ransomware", r"evasion"]
_OFF_VERBS = (r"(?:build|building|develop|developing|create|creating|craft|crafting|deploy|deploying|"
              r"write|writing|generate|generating|launch|launching|execute|executing|perform|"
              r"performing|conduct|conducting|automat\w+|implement\w*|obfuscat\w+|deliver\w*|"
              r"inject\w*)")
STRONG_RE = re.compile(r"(?<![a-z0-9])(?:" + "|".join(_STRONG) + r")(?![a-z0-9])")
WEAK_RE = re.compile(r"(?<![a-z0-9])(?:" + "|".join(_WEAK) + r")(?![a-z0-9])")
OFF_VERB_RE = re.compile(r"(?<![a-z0-9])" + _OFF_VERBS + r"(?:\s+\w+){0,2}\s*$")
DEF_BEFORE_RE = re.compile(
    r"(?:detect\w*|hunt\w*|investigat\w*|analy[sz]\w*|respon\w*|mitigat\w*|defen\w*|against|prevent\w*|"
    r"identif\w*|monitor\w*|block\w*|remediat\w*|recover\w*|protect\w*|triage|forensic\w*|counter\w*)")
DEF_AFTER_RE = re.compile(
    r"^\W*(?:\w+\s+){0,2}?(?:detect\w*|hunt\w*|mitigat\w*|prevent\w*|defen\w*|analy[sz]\w*|response|"
    r"investigat\w*|recover\w*|forensic\w*|remediat\w*)")

# ---------------------------------------------------------- R7 unsafe patterns
UNSAFE = [
    ("ignore-previous-instructions", re.compile(r"ignore (?:all )?previous instructions", re.I)),
    ("curl-pipe-shell", re.compile(r"curl .*\|\s*(?:ba)?sh", re.I)),
    ("iwr-pipe-iex", re.compile(r"iwr .*\|\s*iex", re.I)),
    ("rm-rf-root", re.compile(r"rm\s+-rf\s+/(?:\s|$|\*)")),
    ("dangerously-skip-permissions", re.compile(r"--dangerously-skip-permissions")),
    ("bypassPermissions", re.compile(r"bypassPermissions")),
    ("disable-hook-guard-sandbox", re.compile(r"disable (?:the )?(?:hook|guard|sandbox)", re.I)),
    ("base64-blob", re.compile(r"[A-Za-z0-9+/=]{1000,}")),
]

# ----------------------------------------------------------------- utilities


def rel(p: Path, base: Path) -> str:
    return p.relative_to(base).as_posix()


def read_text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8", errors="replace").lstrip("﻿")
    except OSError:
        return ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def trunc(text: str, n: int = 200) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[: n - 3].rstrip() + "..."


def parse_frontmatter(text: str) -> dict:
    """Minimal top-level YAML frontmatter parser (scalars, quoted, block scalars)."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    lines = text[4:end].split("\n")
    out: dict = {}
    i = 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        i += 1
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        block = []
        while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
            block.append(lines[i].strip())
            i += 1
        if val in (">", "|", ">-", "|-", ">+", "|+", ""):
            val = " ".join(b for b in block if b)
        elif len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key] = val
    return out


def walk_files(root: Path):
    """Yield (relative posix path, absolute Path) for regular files, sorted; skips symlinks."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in PRUNE_DIRS
                             and not os.path.islink(os.path.join(dirpath, d)))
        for fn in sorted(filenames):
            full = Path(dirpath) / fn
            if full.is_symlink():
                continue
            yield rel(full, root), full


# ------------------------------------------------------------------- R1 license
def normalize_license(value: str) -> str:
    s = (value or "").strip().strip("\"'").strip()
    low = s.lower()
    low = re.sub(r"\s+(licen[sc]e|licensed)\b.*$", "", low) if not low.startswith("proprietary") else low
    low = low.strip(" .")
    if not low:
        return "unknown"
    if low.startswith("proprietary") or "all rights reserved" in low:
        return "proprietary"
    if "agpl" in low or "affero" in low:
        return "AGPL-3.0"
    if "lgpl" in low or "lesser general" in low:
        return "LGPL"
    if re.search(r"\bgpl\b|gnu general public|^gpl", low):
        return "GPL"
    if re.search(r"cc[- ]by[- ](?:nc|nd)", low):
        return "CC-BY-NC/ND"
    if re.search(r"cc[- ]by[- ]sa", low):
        return "CC-BY-SA-4.0"
    if re.match(r"cc[- ]by(?:[- ]4(?:\.0)?)?$", low):
        return "CC-BY-4.0"
    if low.startswith("cc0"):
        return "CC0-1.0"
    if "apache" in low:
        return "Apache-2.0"
    if re.match(r"mit\b", low):
        return "MIT"
    if "bsd" in low:
        if "2" in low:
            return "BSD-2-Clause"
        return "BSD-3-Clause"
    if re.match(r"isc\b", low):
        return "ISC"
    if low.startswith("unlicense"):
        return "Unlicense"
    return s[:40] if s else "unknown"


def detect_repo_license(text: str) -> str:
    t = re.sub(r"\s+", " ", text[:20000].lower())
    if not t.strip():
        return "unknown"
    if "gnu affero general public license" in t:
        return "AGPL-3.0"
    if "gnu lesser general public license" in t:
        return "LGPL"
    if "gnu general public license" in t:
        return "GPL"
    if "apache license" in t and "version 2.0" in t:
        return "Apache-2.0"
    if "mozilla public license" in t:
        return "MPL-2.0"
    if "creative commons" in t and "noncommercial" in t:
        return "CC-BY-NC/ND"
    if "permission is hereby granted, free of charge" in t:
        return "MIT"
    if "neither the name" in t and "redistribution and use" in t:
        return "BSD-3-Clause"
    if "redistribution and use" in t:
        return "BSD-2-Clause"
    if "permission to use, copy, modify, and/or distribute" in t:
        return "ISC"
    if "this is free and unencumbered software" in t:
        return "Unlicense"
    if "cc0" in t or "public domain dedication" in t:
        return "CC0-1.0"
    return "unknown"


def license_allowed(spdx: str) -> bool:
    return spdx in ALLOWED_LICENSES


# ------------------------------------------------------------ location helpers
def noncanonical(path: str) -> bool:
    parts = path.split("/")[:-1]
    for i, seg in enumerate(parts):
        if seg in NONCANON_SEGMENTS:
            return True
        if seg == "docs" and i + 1 < len(parts) and LANG_RE.match(parts[i + 1]):
            return True
    return False


def canon_rank(path: str, kind: str) -> int:
    folder = "skills" if kind == "skill" else "agents"
    parts = path.split("/")
    if noncanonical(path):
        return 3
    if parts[0] == folder:
        return 0
    if parts[0] in ("plugin", "plugins") and folder in parts[1:-1]:
        return 1
    return 2


def repo_prio(repo: str) -> int:
    return REPO_PRIORITY.index(repo) if repo in REPO_PRIORITY else len(REPO_PRIORITY)


# ------------------------------------------------------------------- R6 / R9
def offensive_hits(text: str):
    """Return (offensive_terms, defensive_exempt_terms) for lowercase text."""
    text = text.lower()
    bad, kept = [], []
    for rx, weak in ((STRONG_RE, False), (WEAK_RE, True)):
        for m in rx.finditer(text):
            before = re.split(r"[.;:!?\n]", text[max(0, m.start() - 60): m.start()])[-1]
            after = text[m.end(): m.end() + 40]
            after = re.split(r"[.;:!?\n]", after)[0]
            exempt = bool(DEF_BEFORE_RE.search(before)) or bool(DEF_AFTER_RE.match(after))
            if weak and not OFF_VERB_RE.search(before):
                continue  # weak nouns only count with an offensive verb
            (kept if exempt else bad).append(m.group(0))
    return sorted(set(bad)), sorted(set(kept))


# R6b: a defensive intent in the skill name (verb prefix or analysis/tracking noun) overrides
# description hits unless the name itself carries an offensive token.
DEFENSIVE_NAME_RE = re.compile(
    r"^(?:analyzing|detecting|hunting|implementing|deploying|tracking|deobfuscating|investigating|"
    r"monitoring|hardening|securing)-|-(?:analysis|tracking|detection|hunting)(?:-|$)")
OFFENSIVE_NAME_RE = re.compile(
    r"(?:^|-)(?:c2|red-team(?:ing)?|exploit(?:ing)?|cracking|privesc|privilege-escalation|"
    r"lateral-movement|phishing|pass-the-ticket|kerberoast(?:ing)?|credential-access|shadow-credentials)(?:-|$)")
# R9b: repositories whose whole scope is one domain.
REPO_DEFAULT_DOMAINS = {"Anthropic-Cybersecurity-Skills": "security-defensive",
                        "scientific-agent-skills": "data-science"}
# Active tier excludes self-referential tooling and other orchestration harnesses, which
# would compete with the hub's own Opus-orchestrator policy (they stay in the catalog).
ACTIVE_EXCLUDE_RE = re.compile(r"(?<![a-z0-9])(?:ecc|dmux|tmux|multi-agent|orchestrat\w*|harness)(?![a-z0-9])")


def defensive_name(name: str) -> bool:
    return bool(DEFENSIVE_NAME_RE.search(name)) and not OFFENSIVE_NAME_RE.search(name)


def domain_scores(text: str) -> dict:
    text = text.lower()
    scores = {}
    for d in DOMAIN_ORDER:
        n = sum(len(rx.findall(text)) for rx in DOMAIN_RES[d])
        if n:
            scores[d] = n
    return scores


def unsafe_ids(text: str) -> list:
    return [pid for pid, rx in UNSAFE if rx.search(text)]


# ------------------------------------------------------------------ item build
def classify_common(fm: dict, text: str, repo_license: str, name: str, size: int, path: str,
                    repo: str = ""):
    """Shared R1/R6/R7/R8/R9 checks. Returns (reasons, license, domains, scores, r6)."""
    reasons = []
    lic = normalize_license(fm["license"]) if fm.get("license") else repo_license
    if not license_allowed(lic):
        reasons.append(f"license-not-allowed:{lic}")
    desc = fm.get("description", "")
    if not NAME_RE.match(name):
        reasons.append("invalid-name")
    if len(desc) < 20:
        reasons.append("description-too-short")
    if size > MAX_SKILL_BYTES:
        reasons.append("skill-too-large")
    bad, kept = offensive_hits(f"{name} {desc}")
    if bad and defensive_name(name):
        bad, kept = [], sorted(set(kept) | set(bad))
    if bad:
        reasons.append("offensive-security")
    for pid in unsafe_ids(text):
        reasons.append(f"unsafe-pattern:{pid}")
    scores = domain_scores(f"{name} {desc} {path}")
    if repo in REPO_DEFAULT_DOMAINS:
        scores.setdefault(REPO_DEFAULT_DOMAINS[repo], 1)
    if not scores:
        reasons.append("out-of-scope-domain")
    return reasons, lic, sorted(scores), scores, {"bad": bad, "kept": kept}


def collect_skill_files(repo_dir: Path, skill_dir: str):
    base = repo_dir / skill_dir if skill_dir else repo_dir
    out = []
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in PRUNE_DIRS
                             and not (Path(dirpath, d, "SKILL.md")).is_file())
        for fn in sorted(filenames):
            full = Path(dirpath) / fn
            if not full.is_symlink():
                out.append((rel(full, base), full))
    return out


def scan_repo(repo_dir: Path, repo: str, own: dict) -> dict:
    lic_files = sorted(f.name for f in repo_dir.iterdir()
                       if f.is_file() and re.match(r"(?i)^(licen[sc]e|copying|notice)", f.name))
    lic_text = ""
    for f in lic_files:
        if re.match(r"(?i)^(licen[sc]e|copying)", f):
            lic_text = read_text(repo_dir / f)
            break
    repo_license = detect_repo_license(lic_text) if lic_text else "none"
    files = list(walk_files(repo_dir))
    paths = [p for p, _ in files]
    info = {"license": repo_license, "license_files": lic_files}
    skills, agents, invalid = [], [], []
    scripts = Counter()
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        if ext in CODE_EXTS:
            scripts[ext] += 1
    # skills
    for p, full in files:
        if p.rsplit("/", 1)[-1] != "SKILL.md":
            continue
        text = read_text(full)
        fm = parse_frontmatter(text)
        if not fm.get("name") or not fm.get("description"):
            invalid.append(p)
            continue
        sdir = p.rsplit("/", 1)[0] if "/" in p else ""
        size = full.stat().st_size
        reasons, lic, doms, scores, r6 = classify_common(fm, text, repo_license, fm["name"], size, p, repo)
        sfiles = collect_skill_files(repo_dir, sdir)
        code = sorted(r for r, _ in sfiles if os.path.splitext(r)[1].lower() in CODE_EXTS)
        referenced = False
        if code:
            low = text.lower()
            referenced = "scripts/" in low or any(c.rsplit("/", 1)[-1].lower() in low for c in code)
        item = {"kind": "skill", "id": f"{repo}--{fm['name']}", "name": fm["name"], "repo": repo,
                "path": sdir, "reasons": reasons, "license": lic, "domains": doms,
                "desc": trunc(fm["description"]), "size": size,
                "md": hashlib.sha256(text.encode("utf-8", "replace")).hexdigest(),
                "_scores": scores, "_r6": r6, "_license_fm": bool(fm.get("license")),
                "_files": sfiles, "_nname": norm_name(fm["name"]), "_ref": referenced, "code": code}
        if repo in REPO_RULES:
            item["reasons"].append(REPO_RULES[repo])
        if referenced:
            item["reasons"].append("requires-script-review")
        skills.append(item)
    # agents
    for p, full in files:
        parts = p.split("/")
        if not p.endswith(".md") or "agents" not in parts[:-1] or parts[-1].lower().startswith("readme"):
            continue
        text = read_text(full)
        fm = parse_frontmatter(text)
        if not fm.get("name") or not fm.get("description"):
            continue
        size = full.stat().st_size
        reasons, lic, doms, scores, r6 = classify_common(fm, text, repo_license, fm["name"], size, p, repo)
        model = fm.get("model", "").strip().lower()
        if model == "opus":
            reasons.append("model-opus-not-allowed")
        elif model not in ("sonnet", "haiku"):
            reasons.append("model-missing-or-inherit")
        for key in ("hooks", "mcpServers", "permissionMode"):
            if key in fm:
                reasons.append(f"agent-config-not-allowed:{key}")
        if repo in REPO_RULES:
            reasons.append(REPO_RULES[repo])
        agents.append({"kind": "agent", "id": f"{repo}--{fm['name']}", "name": fm["name"], "repo": repo,
                       "path": p, "reasons": reasons, "license": lic, "domains": doms,
                       "model": model or "missing", "sha256": sha256_file(full), "desc": trunc(fm["description"]), "size": size,
                       "md": hashlib.sha256(text.encode("utf-8", "replace")).hexdigest(),
                       "_scores": scores, "_r6": r6, "_nname": norm_name(fm["name"])})
    info.update(skills=skills, agents=agents, invalid_skill_md=sorted(invalid))
    info.update(scan_aux(repo_dir, files))
    info["scripts"] = dict(sorted(scripts.items()))
    return info


def scan_aux(repo_dir: Path, files) -> dict:
    hooks, mcp, plugins, configs, deps = [], [], [], [], []
    for p, full in files:
        parts = p.split("/")
        name = parts[-1]
        low = name.lower()
        ext = os.path.splitext(low)[1]
        in_cfg_dir = bool(CONFIG_DIRS.intersection(parts[:-1]))
        is_cfg = (re.match(r"^settings.*\.json$", low) or low in (".mcp.json", "plugin.json", "marketplace.json",
                  "hooks.json") or (in_cfg_dir and ext in (".json", ".toml", ".yaml", ".yml"))
                  or (low == "config.toml" and ".codex" in parts))
        if is_cfg:
            configs.append(p)
        if parts[-2:-1] in (["hooks"],) or "hooks" in parts[:-1]:
            hooks.append({"path": p, "kind": "hooks-dir"})
        elif low == "hooks.json":
            hooks.append({"path": p, "kind": "hooks.json"})
        if (".claude-plugin" in parts[:-1] or ".cursor-plugin" in parts[:-1]) and ext == ".json":
            plugins.append(p)
        elif low == "plugin.json":
            plugins.append(p)
        if ext == ".json":
            try:
                size = full.stat().st_size
            except OSError:
                continue
            if size <= JSON_SCAN_LIMIT:
                text = read_text(full)
                if '"mcpServers"' in text or '"hooks"' in text:
                    try:
                        data = json.loads(text)
                    except ValueError:
                        data = None
                    if data is not None:
                        servers = sorted(set(find_server_names(data)))
                        if '"mcpServers"' in text and servers is not None and has_key(data, "mcpServers"):
                            mcp.append({"path": p, "servers": servers})
                        if is_cfg and low != "hooks.json" and has_key(data, "hooks"):
                            hooks.append({"path": p, "kind": "hooks-key"})
            if low == "package.json":
                names = sorted(_pkg_deps(read_text(full)))
                deps.append({"path": p, "kind": "npm", "names": names})
        if re.match(r"^requirements.*\.txt$", low):
            deps.append({"path": p, "kind": "pip", "names": sorted(_req_names(read_text(full)))})
        if low == "pyproject.toml":
            deps.append({"path": p, "kind": "pyproject", "names": sorted(_pyproject_deps(read_text(full)))})
    key = lambda d: d["path"] if isinstance(d, dict) else d  # noqa: E731
    return {"hooks": sorted(hooks, key=lambda h: (h["path"], h["kind"])),
            "mcp": sorted(mcp, key=key), "plugins": sorted(set(plugins)),
            "configs": sorted(set(configs)), "dependencies": sorted(deps, key=key)}


def has_key(data, key, depth=0) -> bool:
    if depth > 6:
        return False
    if isinstance(data, dict):
        return key in data or any(has_key(v, key, depth + 1) for v in data.values())
    if isinstance(data, list):
        return any(has_key(v, key, depth + 1) for v in data)
    return False


def find_server_names(data, depth=0):
    if depth > 6:
        return
    if isinstance(data, dict):
        for k, v in data.items():
            if k == "mcpServers" and isinstance(v, dict):
                yield from (str(s) for s in v)
            else:
                yield from find_server_names(v, depth + 1)
    elif isinstance(data, list):
        for v in data:
            yield from find_server_names(v, depth + 1)


def _pkg_deps(text: str):
    try:
        data = json.loads(text)
    except ValueError:
        return []
    names = []
    if isinstance(data, dict):
        for k in ("dependencies", "devDependencies"):
            if isinstance(data.get(k), dict):
                names += [str(n) for n in data[k]]
    return names


def _req_names(text: str):
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if m:
            out.append(m.group(1).lower())
    return out


def _pyproject_deps(text: str):
    try:
        data = tomllib.loads(text)
    except Exception:
        return []
    out = []
    for dep in (data.get("project", {}) or {}).get("dependencies", []) or []:
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", str(dep))
        if m:
            out.append(m.group(1).lower())
    return out


# ------------------------------------------------------------------------ own
def own_names(hub_root: Path) -> dict:
    skills, agents = set(), set()
    for f in sorted((hub_root / "skills").glob("*/SKILL.md")):
        fm = parse_frontmatter(read_text(f))
        skills.add(norm_name(fm.get("name") or f.parent.name))
    for d in (hub_root / ".claude" / "agents", hub_root / "agents"):
        for f in sorted(d.glob("*.md")):
            fm = parse_frontmatter(read_text(f))
            agents.add(norm_name(fm.get("name") or f.stem))
    return {"skills": sorted(skills), "agents": sorted(agents)}


def gitlink(hub_root: Path, repo: str) -> str:
    try:
        out = subprocess.run(["git", "ls-tree", "HEAD", "--", f"external/{repo}"], cwd=hub_root,
                             capture_output=True, text=True, timeout=30).stdout.split()
        if len(out) >= 3 and out[1] == "commit" and re.fullmatch(r"[0-9a-f]{40}", out[2]):
            return out[2]
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


# --------------------------------------------------------------- cross-item rules
def is_hard(reasons) -> bool:
    return any(r.startswith(HARD_PREFIXES) for r in reasons)


def apply_cross_rules(items: list, own_set: set, kind: str):
    by_name = defaultdict(list)
    for it in items:
        by_name[it["_nname"]].append(it)
    # R2: non-canonical copy when a canonical copy exists (any repo)
    for it in items:
        if noncanonical(it["path"]) and any(
                o is not it and not noncanonical(o["path"]) for o in by_name[it["_nname"]]):
            it["reasons"].append("non-canonical-copy")
    # R3 own priority
    for it in items:
        if it["_nname"] in own_set:
            it["reasons"].append(f"duplicate-of-own:{it['_nname']}")

    def prio(it):
        return (repo_prio(it["repo"]), canon_rank(it["path"], kind), len(it["path"]), it["id"], it["path"])

    for keyfn in (lambda i: i["_nname"], lambda i: i["md"]):
        groups = defaultdict(list)
        for it in items:
            if not is_hard(it["reasons"]):
                groups[keyfn(it)].append(it)
        for key in sorted(groups):
            g = sorted(groups[key], key=prio)
            for loser in g[1:]:
                loser["reasons"].append(f"duplicate-of:{g[0]['id']}")


def duplicate_groups(items: list) -> dict:
    out = {}
    for label, keyfn in (("by_name", lambda i: i["_nname"]), ("by_hash", lambda i: i["md"][:16])):
        groups = defaultdict(set)
        for it in items:
            groups[keyfn(it)].add(f"{it['repo']}:{it['path']}")
        out[label] = [{"key": k, "members": sorted(v)} for k, v in sorted(groups.items()) if len(v) > 1]
    return out


def decide(it: dict):
    it["reasons"] = list(dict.fromkeys(it["reasons"]))
    if is_hard(it["reasons"]):
        it["decision"] = "rejected"
    elif "requires-script-review" in it["reasons"]:
        it["decision"] = "requires-review"
    else:
        it["decision"] = "approved"


def select_tiers(skills: list) -> list:
    approved = [s for s in skills if s["decision"] == "approved"]
    chosen = []
    for d in DOMAIN_ORDER:
        cands = sorted((s for s in approved if d in s["_scores"] and s not in chosen
                        and not ACTIVE_EXCLUDE_RE.search(f"{s['name']} {s.get('desc', '')}".lower())),
                       key=lambda s: (-s["_scores"][d], s["size"], s["id"]))
        for s in cands[:2]:
            if len(chosen) < MAX_ACTIVE:
                chosen.append(s)
    ids = {id(s) for s in chosen}
    for s in approved:
        s["tier"] = "active" if id(s) in ids else "catalog"
    return [s["id"] for s in sorted(chosen, key=lambda s: s["id"])]


# --------------------------------------------------------------------- scan()
def scan(hub_root: Path) -> dict:
    hub_root = Path(hub_root)
    ext = hub_root / "external"
    own = own_names(hub_root)
    repos_found = sorted(d.name for d in ext.iterdir() if d.is_dir() and any(d.iterdir())) \
        if ext.is_dir() else []
    infos = {r: scan_repo(ext / r, r, own) for r in repos_found}
    all_skills = [s for r in repos_found for s in infos[r]["skills"]]
    all_agents = [a for r in repos_found for a in infos[r]["agents"]]
    apply_cross_rules(all_skills, set(own["skills"]), "skill")
    apply_cross_rules(all_agents, set(own["agents"]), "agent")
    for it in all_skills + all_agents:
        decide(it)
    active = select_tiers(all_skills)
    for a in all_agents:
        if a["decision"] == "approved":
            a["tier"] = "catalog"
    # approved skills: files + hashes (code and non-text excluded)
    for s in all_skills:
        sfiles = s.pop("_files")
        s["file_count"] = len(sfiles)
        if s["decision"] == "approved":
            keep = [(r, f) for r, f in sfiles if os.path.splitext(r)[1].lower() in TEXT_EXTS]
            s["files"] = sorted(r for r, _ in keep)
            s["sha256"] = {r: sha256_file(f) for r, f in sorted(keep)}
            if s["code"]:
                s["excluded_code"] = s["code"]
        s.pop("_ref", None)
    repos = {}
    for r in repos_found:
        i = infos[r]
        lic = i["license"]
        if license_allowed(lic):
            redis, reason = "allowed", f"Licencia {lic} permite redistribucion con atribucion."
        elif lic == "none":
            redis, reason = "forbidden", "Sin archivo LICENSE: todos los derechos reservados; solo referencia."
        else:
            redis, reason = "forbidden", f"Licencia {lic} no esta en la lista permitida."
        repos[r] = {"commit": gitlink(hub_root, r), "license": lic, "license_files": i["license_files"],
                    "redistribution": redis, "reason": reason,
                    "repo_rule": REPO_RULES.get(r, "reference-only" if r == "awesome-harness-engineering" else ""),
                    "skills": sorted(i["skills"], key=lambda s: (s["path"], s["id"])),
                    "agents": sorted(i["agents"], key=lambda s: (s["path"], s["id"])),
                    "invalid_skill_md": i["invalid_skill_md"], "hooks": i["hooks"], "mcp": i["mcp"],
                    "plugins": i["plugins"], "configs": i["configs"], "scripts": i["scripts"],
                    "dependencies": i["dependencies"]}
    inv = {"schema": SCHEMA, "generated_by": GENERATED_BY, "own": own, "repos": repos,
           "duplicates": {"skills": duplicate_groups(all_skills), "agents": duplicate_groups(all_agents)}}
    inv["summary"] = summarize(inv, active)
    for it in all_skills + all_agents:
        for k in [k for k in it if k.startswith("_")]:
            it.pop(k)
        it.pop("kind", None)
    return inv


def summarize(inv: dict, active: list) -> dict:
    # NOTE: runs before private keys are stripped.
    decisions, reasons = Counter(), Counter()
    per_repo = {}
    r6_bad, r6_kept = [], []
    for r, d in inv["repos"].items():
        c = Counter()
        for it in d["skills"] + d["agents"]:
            decisions[it["decision"]] += 1
            c[f"{it['kind']}s-{it['decision']}"] += 1
            for rs in it["reasons"]:
                reasons[rs.split(":")[0]] += 1
            if "offensive-security" in it["reasons"]:
                r6_bad.append((it["id"], it["_r6"]["bad"], it["desc"]))
            elif it["_r6"]["kept"]:
                r6_kept.append((it["id"], it["_r6"]["kept"], it["desc"]))
        per_repo[r] = {"skills": len(d["skills"]), "agents": len(d["agents"]), "hooks": len(d["hooks"]),
                       "mcp": len(d["mcp"]), "plugins": len(d["plugins"]), "configs": len(d["configs"]),
                       "scripts": sum(d["scripts"].values()),
                       "dependency_manifests": len(d["dependencies"]), **dict(sorted(c.items()))}
    ex = lambda lst: [{"id": i, "terms": t, "desc": ds[:120]} for i, t, ds in sorted(lst)[:10]]  # noqa: E731
    return {"decisions": dict(sorted(decisions.items())), "reason_codes": dict(sorted(reasons.items())),
            "per_repo": per_repo, "active": active,
            "r6": {"rejected_count": len(r6_bad), "kept_count": len(r6_kept),
                   "rejected_examples": ex(r6_bad), "kept_examples": ex(r6_kept)}}


# ------------------------------------------------------------------- registry
def build_registry(inv: dict) -> dict:
    repos, skills, agents = {}, [], []
    for r, d in sorted(inv["repos"].items()):
        repos[r] = {"commit": d["commit"], "license": d["license"], "license_files": d["license_files"],
                    "redistribution": d["redistribution"], "reason": d["reason"]}
        for s in d["skills"]:
            if s["decision"] == "approved":
                skills.append({"id": s["id"], "name": s["name"], "repo": r, "path": s["path"],
                               "files": s["files"], "sha256": s["sha256"], "license": s["license"],
                               "domains": s["domains"], "tier": s["tier"], "description": s["desc"]})
        for a in d["agents"]:
            if a["decision"] == "approved":
                agents.append({"id": a["id"], "name": a["name"], "repo": r, "path": a["path"],
                               "sha256": a["sha256"], "license": a["license"],
                               "model": a["model"], "domains": a["domains"], "tier": "catalog",
                               "description": a["desc"]})
    return {"schema": SCHEMA, "generated_by": GENERATED_BY, "repositories": repos,
            "skills": sorted(skills, key=lambda s: s["id"]), "agents": sorted(agents, key=lambda s: s["id"])}


# -------------------------------------------------------------------- output
def dumps(obj, level=0, limit=3) -> str:
    """JSON with indent 1 down to `limit` levels, compact below; stable key order."""
    sep = (",", ":")
    if level >= limit or not isinstance(obj, (dict, list)) or not obj:
        return json.dumps(obj, sort_keys=True, separators=sep, ensure_ascii=False)
    pad, pad_in = " " * level, " " * (level + 1)
    if isinstance(obj, dict):
        body = [f"{pad_in}{json.dumps(k, ensure_ascii=False)}:{dumps(v, level + 1, limit)}"
                for k, v in sorted(obj.items())]
        return "{\n" + ",\n".join(body) + f"\n{pad}}}"
    body = [pad_in + dumps(v, level + 1, limit) for v in obj]
    return "[\n" + ",\n".join(body) + f"\n{pad}]"


def md_table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in row) + " |" for row in rows]
    return "\n".join(out)


def all_items(inv, section):
    return [it for d in inv["repos"].values() for it in d[section]]


def report_main(inv: dict, reg: dict) -> str:
    s = inv["summary"]
    L = ["# Reporte de skills externas", "",
         "Generado por `scripts/external_scan.py` (solo lectura, sin timestamps). "
         "Regenerar con `python scripts/hub.py external-scan`.", "", "## Repositorios", ""]
    rows = []
    for r, d in inv["repos"].items():
        p = s["per_repo"][r]
        rows.append([r, d["commit"][:12], d["license"], d["redistribution"], p["skills"], p["agents"],
                     p["hooks"], p["mcp"], p["scripts"], p["dependency_manifests"], p["configs"]])
    L.append(md_table(["Repo", "Commit", "Licencia", "Redistribucion", "Skills", "Agentes", "Hooks",
                       "MCP", "Scripts", "Manifiestos deps", "Configs"], rows))
    tot = lambda k: sum(v[k] for v in s["per_repo"].values())  # noqa: E731
    L += ["", "## Totales encontrados", "",
          f"Skills: {tot('skills')}; agentes: {tot('agents')}; hooks: {tot('hooks')}; mcp: {tot('mcp')}; "
          f"scripts: {tot('scripts')}; manifiestos de dependencias: {tot('dependency_manifests')}; "
          f"configs: {tot('configs')}; manifiestos de plugin: {tot('plugins')}.", "",
          "Hooks, MCP, plugins, settings y dependencias son siempre `inventory-only` (nunca se activan).",
          "", "## Decisiones", ""]
    for kind in ("skills", "agents"):
        c = Counter(it["decision"] for it in all_items(inv, kind))
        L.append(f"- {kind}: " + ", ".join(f"{k}={v}" for k, v in sorted(c.items())))
    L += ["", "### Por motivo", "", md_table(["Motivo", "Items"], sorted(s["reason_codes"].items())), "",
          "## Skills activas aprobadas", ""]
    act = [x for x in reg["skills"] if x["tier"] == "active"]
    L.append(md_table(["Id", "Dominios", "Descripcion"],
                      [[x["id"], ", ".join(x["domains"]), x["description"][:120]] for x in act]))
    cat = Counter(d for x in reg["skills"] if x["tier"] == "catalog" for d in x["domains"])
    L += ["", f"## Skills catalogo por dominio (total {sum(1 for x in reg['skills'] if x['tier']=='catalog')})", "",
          md_table(["Dominio", "Skills"], [[d, cat.get(d, 0)] for d in DOMAIN_ORDER]), "",
          f"## Agentes aprobados ({len(reg['agents'])})", ""]
    L.append(md_table(["Id", "Modelo", "Dominios"],
                      [[a["id"], a["model"], ", ".join(a["domains"])] for a in reg["agents"]])
             if reg["agents"] else "Ninguno.")
    return "\n".join(L) + "\n"


RULES_ES = [
    ("R1", "Licencia efectiva = frontmatter `license` normalizada o LICENSE del repo. Permitidas: "
           + ", ".join(ALLOWED_LICENSES) + ". AGPL/GPL/LGPL, NC/ND, propietaria, desconocida o repo sin LICENSE: `license-not-allowed:<valor>`."),
    ("R2", "Copias/ports/traducciones (`docs/<lang>/`, `.kiro/`, `.cursor/`, `.cursor-plugin/`, `.agents/`, `.codex/`, `pi/`, `examples/`, `tests/`, `fixtures/`) con otra copia canonica del mismo nombre: `non-canonical-copy`. Prioridad canonica: `skills/`|`agents/` raiz > `plugin(s)/.../skills` > otros."),
    ("R3", "Duplicados por nombre normalizado o hash identico de SKILL.md. Las propias siempre ganan (`duplicate-of-own:<n>`); entre externas: scientific-agent-skills > Anthropic-Cybersecurity-Skills > diagram-design > ECC > otras, luego ruta canonica y ruta mas corta (`duplicate-of:<id>`)."),
    ("R4", "Skill con codigo (" + " ".join(sorted(CODE_EXTS)) + ") referenciado en su SKILL.md (nombre de archivo o `scripts/`): `requires-script-review`. Si no, se aprueba como solo instrucciones: `files` solo incluye .md/.txt/.json/.yaml/.yml/.csv/.toml y el codigo queda en `excluded_code`."),
    ("R5", "agentmemory: `requires-service:agentmemory`; rea: `requires-toolchain:rea`; OpenViking cae por R1 (AGPL); awesome-harness-engineering solo referencia (sin licencia)."),
    ("R6", "Solo seguridad defensiva: terminos ofensivos fuertes (exploit development, red team, c2, credential dumping, lateral movement, privilege escalation, ddos, jailbreak, keylogger...) en nombre+descripcion; terminos debiles (payload, shellcode, ransomware, evasion) solo con verbo ofensivo previo (build, create, deploy...). Se exime si hay contexto defensivo (detect, hunt, investigate, analyze, respond, mitigate, defend, prevent, against... antes o detection/mitigation/analysis... despues). Resultado `offensive-security`."),
    ("R7", "Patrones inseguros en SKILL.md/agente: " + ", ".join(p for p, _ in UNSAFE) + " (`rm -rf /` solo raiz). Resultado `unsafe-pattern:<id>`."),
    ("R8", "Calidad: nombre `^[a-z0-9][a-z0-9-]{0,63}$` (`invalid-name`), descripcion >= 20 caracteres, SKILL.md <= 100 KB."),
    ("R9", "Dominios por palabras clave sobre nombre+descripcion+ruta: " + ", ".join(DOMAIN_ORDER) + ". Sin dominio: `out-of-scope-domain`. Tier `active`: los 2 mejores por dominio (puntaje de coincidencias, desempate SKILL.md menor, luego id), maximo 14; resto aprobado = `catalog`."),
    ("A", "Agentes: R1/R2/R3/R6/R7/R8/R9 mas modelo exactamente `sonnet` o `haiku` (`model-opus-not-allowed`, `model-missing-or-inherit`); claves `hooks`, `mcpServers`, `permissionMode` -> `agent-config-not-allowed:<k>`; tier siempre `catalog`."),
]


def report_compat(inv: dict, reg: dict) -> str:
    s = inv["summary"]
    L = ["# Reporte de compatibilidad de skills", "", "## Reglas", ""]
    L += [f"- **{rid}**: {txt}" for rid, txt in RULES_ES]
    L += ["", "## Matriz dominio x decision (skills)", ""]
    skills = all_items(inv, "skills")
    rows = []
    for d in DOMAIN_ORDER + ["(sin dominio)"]:
        c = Counter(it["decision"] for it in skills
                    if (d in it["domains"] if d != "(sin dominio)" else not it["domains"]))
        rows.append([d, c["approved"], c["requires-review"], c["rejected"]])
    L.append(md_table(["Dominio", "approved", "requires-review", "rejected"], rows))
    dup = inv["duplicates"]
    L += ["", "## Duplicados", "",
          f"- Skills: {len(dup['skills']['by_name'])} grupos por nombre, {len(dup['skills']['by_hash'])} por hash.",
          f"- Agentes: {len(dup['agents']['by_name'])} grupos por nombre, {len(dup['agents']['by_hash'])} por hash.", "",
          "Colisiones con nombres propios (prioridad propia):", ""]
    own_col = sorted({(it["id"], it["path"]) for it in skills + all_items(inv, "agents")
                      for r in it["reasons"] if r.startswith("duplicate-of-own")})
    L += [f"- `{i}` ({p})" for i, p in own_col[:40]] or ["- ninguna"]
    L += ["", "## requires-review por repo", ""]
    for r, d in inv["repos"].items():
        rr = [it for it in d["skills"] if it["decision"] == "requires-review"]
        L.append(f"- **{r}**: {len(rr)}" + (" (ej.: " + ", ".join(f"`{i['id']}`" for i in rr[:10]) + ")" if rr else ""))
    r6 = s["r6"]
    L += ["", "## Filtro de seguridad ofensiva (R6)", "",
          f"Rechazadas: {r6['rejected_count']}; mantenidas con frase defensiva: {r6['kept_count']}.", "",
          "Ejemplos rechazados:", ""]
    L += [f"- `{e['id']}` {e['terms']}: {e['desc']}" for e in r6["rejected_examples"]] or ["- ninguno"]
    L += ["", "Ejemplos mantenidos (termino ofensivo en contexto defensivo):", ""]
    L += [f"- `{e['id']}` {e['terms']}: {e['desc']}" for e in r6["kept_examples"]] or ["- ninguno"]
    return "\n".join(L) + "\n"


def report_licenses(inv: dict, reg: dict) -> str:
    L = ["# Registro de licencias", "", md_table(
        ["Repo", "Licencia", "Redistribucion", "Motivo", "Archivos de licencia"],
        [[r, d["license"], d["redistribution"], d["reason"], ", ".join(d["license_files"]) or "-"]
         for r, d in inv["repos"].items()]), "",
         "## Obligaciones de atribucion", "",
         "- Copiar LICENSE/NOTICE del repo de origen junto al contenido copiado.",
         "- Copias sin modificar (los hashes sha256 del registro permiten verificarlo).",
         "- Repos con redistribucion `forbidden` no se copian: solo referencia o inventario.",
         "", "## Licencias por skill (frontmatter) distintas de la del repo", ""]
    rows = []
    for r, d in inv["repos"].items():
        c = Counter(it["license"] for it in d["skills"] + d["agents"] if it["license"] != d["license"])
        if c:
            rows.append([r, sum(c.values()), ", ".join(f"{k}={v}" for k, v in sorted(c.items()))])
    L.append(md_table(["Repo", "Overrides", "Detalle"], rows) if rows else "Ninguna.")
    return "\n".join(L) + "\n"


def generate(hub_root: Path):
    inv = scan(hub_root)
    reg = build_registry(inv)
    outputs = {OUT_INVENTORY: dumps(inv) + "\n", OUT_REGISTRY: dumps(reg) + "\n",
               OUT_REPORT: report_main(inv, reg), OUT_COMPAT: report_compat(inv, reg),
               OUT_LICENSES: report_licenses(inv, reg)}
    return inv, outputs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="external-scan", description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if outputs differ from disk")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args(argv)
    root = Path(args.root)
    inv, outputs = generate(root)
    if not inv["repos"]:
        print("external-scan: external/ has no checked-out submodules; nothing to scan.")
        return 0
    if args.check:
        drift = [p for p, text in outputs.items()
                 if not (root / p).is_file() or (root / p).read_bytes() != text.encode("utf-8")]
        if drift:
            print("external-scan: outputs out of date: " + ", ".join(drift))
            return 1
        print("external-scan: outputs up to date.")
        return 0
    for p, text in outputs.items():
        target = root / p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
    print(f"external-scan: wrote {len(outputs)} files; decisions={inv['summary']['decisions']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
