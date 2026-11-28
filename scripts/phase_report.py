#!/usr/bin/env python3
"""Consolidated phase report renderer (stdlib only). Also runs inside projects as .agent-hub/bin/phase_report.py.

render --data docs/reports/data/PHASE_NN.json [--out F] [--usage-dir D] [--repo .]
latest [--dir docs/reports]
check  [--dir docs/reports] [--usage-dir D] [--repo .]

Output is deterministic (no timestamps). Exit 2 when the privacy scan refuses output.
"""
import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

SECTIONS = [
    "Número de fase y objetivo", "Resumen ejecutivo", "Estado inicial y estado final",
    "Componentes implementados", "Archivos creados y modificados", "Versiones y dependencias",
    "Comandos relevantes ejecutados", "Resultados reales de pruebas", "Evidencia de funcionamiento",
    "Riesgos y hallazgos de seguridad", "Decisiones técnicas y justificación",
    "Consumo de tokens por agente y modelo", "Costos medidos", "Duración de la fase",
    "Problemas encontrados y soluciones", "Componentes pendientes",
    "Decisiones que requieren autorización", "Commits, Pull Requests y enlaces",
    "Recomendación para la siguiente fase",
]
EMPTY = "No registrado en la evidencia disponible."
STATUS = {"passed": "✅ pasó", "failed": "❌ falló", "pending": "⏳ pendiente", "not-measured": "➖ no medido"}
USAGE_FIELDS = ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                "cache_read_input_tokens", "messages")
CREDENTIALS = [
    r"gh[opusr]_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}", r"sk-ant-[A-Za-z0-9-]{20,}",
    r"sk-[A-Za-z0-9]{32,}", r"AKIA[0-9A-Z]{16}", r"xox[baprs]-[A-Za-z0-9-]{10,}",
    r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----",
]
PERSONAL = [r"[A-Za-z]:\\Users\\[^\\\s]+", r"/home/[^/\s]+", r"/Users/[^/\s]+"]


class PrivacyError(Exception):
    def __init__(self, findings):
        super().__init__("privacy scan refused output")
        self.findings = findings


def privacy_findings(text):
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        if any(re.search(p, line) for p in CREDENTIALS):
            found.append(f"linea {number}: posible credencial (valor no mostrado)")
        if any(re.search(p, line) for p in PERSONAL):
            found.append(f"linea {number}: ruta personal")
    return found


def as_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def bullets(items):
    items = [str(i) for i in items or []]
    return "\n".join(f"- {i}" for i in items) if items else EMPTY


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(c).replace("|", "/") for c in row) + " |" for row in rows]
    return "\n".join(lines)


def git_files(git_range, repo):
    out = subprocess.run(
        ["git", "-C", repo, "diff", "--name-status", f"{git_range['base']}..{git_range['head']}"],
        capture_output=True, text=True, check=True).stdout
    created, modified = [], []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            (created if parts[0].startswith("A") else modified).append(parts[-1])
    return created, modified


def files_section(data, repo):
    files = data.get("files") or {}
    created, modified = list(files.get("created") or []), list(files.get("modified") or [])
    parts = []
    if files.get("git_range"):
        gc, gm = git_files(files["git_range"], repo)
        created += gc
        modified += gm
        counts = {}
        for path in created + modified:
            norm = path.replace("\\", "/")
            top = norm.split("/")[0] if "/" in norm else "(raíz)"
            counts[top] = counts.get(top, 0) + 1
        parts.append("Conteo por directorio de nivel superior: " +
                     (", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "0"))
    elif not created and not modified:
        return EMPTY
    parts.append("Creados:\n" + bullets(created))
    parts.append("Modificados:\n" + bullets(modified))
    return "\n\n".join(parts)


def tests_section(tests):
    if not tests:
        return EMPTY
    rows = []
    for test in tests:
        status = test.get("status")
        if status not in STATUS:
            raise ValueError(f"estado de prueba no válido: {status}")
        rows.append([test.get("name", ""), STATUS[status], test.get("evidence", "")])
    return table(["Prueba", "Estado", "Evidencia"], rows)


def tokens_section(tokens):
    if not tokens:
        return EMPTY
    rows, total = [], [0, 0, 0.0]
    for t in tokens:
        n, calls, dur = as_int(t.get("tokens")), as_int(t.get("tool_uses")), float(t.get("duration_s") or 0)
        total = [total[0] + n, total[1] + calls, total[2] + dur]
        rows.append([t.get("agent", ""), t.get("model", ""), n, calls, round(dur, 1), t.get("source", "")])
    rows.append(["**Total**", "", total[0], total[1], round(total[2], 1), ""])
    return table(["Agente", "Modelo", "Tokens", "Llamadas a herramientas", "Duración (s)", "Fuente"], rows)


def usage_table(usage_dir):
    if not usage_dir:
        return ""
    totals = {}
    for path in sorted(glob.glob(str(Path(usage_dir) / "*.json"))):
        try:
            doc = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for key, counts in usage_by_role(doc if isinstance(doc, dict) else {}):
            if isinstance(counts, dict):
                acc = totals.setdefault(key, {f: 0 for f in USAGE_FIELDS})
                for f in USAGE_FIELDS:
                    acc[f] += as_int(counts.get(f))
    if not totals:
        return ""
    rows = [[role, m] + [t[f] for f in USAGE_FIELDS] for (role, m), t in sorted(totals.items())]
    return ("\n\n### Consumo medido por usage_tracker (orquestador y ejecutores por separado)\n\n" +
            table(["Rol", "Modelo", "Entrada", "Salida", "Escritura caché", "Lectura caché", "Mensajes"], rows))


def usage_by_role(doc):
    """((role, model), counts): main session = orquestador, subagents = ejecutores."""
    if isinstance(doc.get("main"), dict) or isinstance(doc.get("subagents"), list):
        for model, counts in (doc.get("main") or {}).items():
            yield ("orquestador", model), counts
        for sub in doc.get("subagents") or []:
            for model, counts in ((sub.get("models") or {}).items() if isinstance(sub, dict) else []):
                yield ("ejecutores", model), counts
        return
    for model, counts in (doc.get("totals_by_model") or {}).items():
        yield ("total", model), counts


def render(data, usage_dir=None, repo="."):
    phase = data.get("phase") if isinstance(data, dict) else None
    valid = (isinstance(phase, int) and not isinstance(phase, bool)) or (
        isinstance(phase, str) and re.fullmatch(r"[0-9]+(?:[.][0-9]+)?", phase))
    if not valid or not data.get("title"):
        raise ValueError("el JSON requiere 'phase' (entero o subfase como \"4.1\") y 'title'")
    g = data.get
    github = g("github") or {}
    costs = [f"{c.get('item', '')}: USD {float(c.get('usd') or 0):.2f} (fuente: {c.get('source', '')})"
             for c in g("costs") or []]
    bodies = [
        f"Fase {data['phase']}: {g('title')}\n\nObjetivo: {g('objective') or EMPTY}",
        bullets(g("executive_summary")),
        "**Estado inicial:**\n" + bullets(g("initial_state")) + "\n\n**Estado final:**\n" + bullets(g("final_state")),
        bullets(g("components")),
        files_section(data, repo),
        bullets(g("versions")),
        bullets([f"`{c.get('cmd', '')}`: {c.get('result', '')}" for c in g("commands") or []]),
        tests_section(g("tests")),
        bullets(g("evidence")),
        bullets(g("risks")),
        bullets([f"{d.get('decision', '')}: {d.get('why', '')}" for d in g("decisions") or []]),
        tokens_section(g("tokens")) + usage_table(usage_dir),
        bullets(costs),
        g("duration") or EMPTY,
        bullets([f"{p.get('problem', '')}: {p.get('solution', '')}" for p in g("problems") or []]),
        bullets(g("pending")),
        bullets(g("authorizations")),
        "**Commits:**\n" + bullets(github.get("commits")) + "\n\n**Pull Requests:**\n" +
        bullets(github.get("prs")) + "\n\n**Enlaces:**\n" + bullets(github.get("links")),
        g("next_phase") or EMPTY,
    ]
    parts = [f"# Reporte de fase {phase_label(data['phase'], '.')}: {g('title')}", "",
             "Documento sintético generado de forma determinista. No incluye registros completos."]
    for number, (name, body) in enumerate(zip(SECTIONS, bodies), 1):
        parts += ["", f"## {number}. {name}", "", body]
    text = "\n".join(parts) + "\n"
    findings = privacy_findings(text)
    if findings:
        raise PrivacyError(findings)
    return text


def phase_parts(phase):
    """Phase 4 -> (4, 0); sub-phase "4.1" -> (4, 1)."""
    major, _, minor = str(phase).partition(".")
    return int(major), int(minor or 0)


def phase_label(phase, sep="_"):
    major, minor = phase_parts(phase)
    return f"{major:02d}" + (f"{sep}{minor}" if minor else "")


def find_reports(directory):
    found = {}
    for path in Path(directory).glob("PHASE_*_REPORT.md"):
        match = re.fullmatch(r"PHASE_(\d+)(?:_(\d+))?_REPORT\.md", path.name)
        if match:
            found[(int(match.group(1)), int(match.group(2) or 0))] = path
    return found


def lf(text):
    return text.replace("\r\n", "\n")


def latest_text(path):
    return f"Copia de {path.name}\n\n" + path.read_bytes().decode("utf-8")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_render(args):
    data_path = Path(args.data)
    text = render(load(data_path), args.usage_dir, args.repo)
    out = Path(args.out) if args.out else data_path.parent.parent / f"PHASE_{phase_label(load(data_path)['phase'])}_REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text.encode("utf-8"))
    print(f"Escrito {out}")
    return 0


def cmd_latest(args):
    reports = find_reports(args.dir)
    if not reports:
        print("No hay reportes PHASE_NN_REPORT.md", file=sys.stderr)
        return 1
    newest = reports[max(reports)]
    (Path(args.dir) / "LATEST_REPORT.md").write_bytes(latest_text(newest).encode("utf-8"))
    print(f"LATEST_REPORT.md <- {newest.name}")
    return 0


def cmd_check(args):
    directory = Path(args.dir)
    reports = find_reports(directory)
    problems = []
    for data_path in sorted((directory / "data").glob("PHASE_*.json")):
        try:
            data = load(data_path)
            text = render(data, args.usage_dir, args.repo)
        except PrivacyError as exc:
            problems += [f"{data_path.name}: {f}" for f in exc.findings]
            continue
        report = directory / f"PHASE_{phase_label(data['phase'])}_REPORT.md"
        if not report.exists():
            problems.append(f"falta {report.name}")
        elif lf(report.read_bytes().decode("utf-8")) != text:  # autocrlf checkouts use CRLF
            problems.append(f"deriva: {report.name} no coincide con {data_path.name}")
    if reports:
        newest = reports[max(reports)]
        latest = directory / "LATEST_REPORT.md"
        if not latest.exists() or lf(latest.read_bytes().decode("utf-8")) != lf(latest_text(newest)):
            problems.append("LATEST_REPORT.md no coincide con el reporte más reciente")
        for path in reports.values():
            problems += [f"{path.name}: {f}" for f in privacy_findings(path.read_bytes().decode("utf-8"))]
    for problem in problems:
        print(problem, file=sys.stderr)
    print("check: " + ("fallido" if problems else "correcto"))
    return 1 if problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="phase_report")
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--data", required=True)
    r.add_argument("--out")
    r.add_argument("--usage-dir", default=".agent-hub/usage")
    r.add_argument("--repo", default=".")
    lt = sub.add_parser("latest")
    lt.add_argument("--dir", default="docs/reports")
    c = sub.add_parser("check")
    c.add_argument("--dir", default="docs/reports")
    c.add_argument("--usage-dir", default=".agent-hub/usage")
    c.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    handlers = {"render": cmd_render, "latest": cmd_latest, "check": cmd_check}
    try:
        return handlers[args.cmd](args)
    except PrivacyError as exc:
        for finding in exc.findings:
            print(f"refused: {finding}", file=sys.stderr)
        return 2
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {type(exc).__name__}: {str(exc)[:200]}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
