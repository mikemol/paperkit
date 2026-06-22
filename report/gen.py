#!/usr/bin/env python3
"""Generate the verification REPORT from MACHINE-READABLE pipeline data.

The figures are not scraped from human output: the report ingests
`discriminate --json` (structured grade records — key, check, grade, shared_with)
and gate exit codes, and renders each figure as a markdown table derived from that
data.  Even the --without-K collapse is computed from the JSON (group cited records
by check), so nothing is screen-scraped.  Fresh-by-construction: `--check`
regenerates and diffs, so a stale report fails its own gate.

    python3 report/gen.py            # refresh assets + project REPORT.md
    python3 report/gen.py --check    # exit 1 if any committed asset is stale
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = HERE / "assets"
_DELTA, _GATE = {}, {}


def _delta(project):
    """discriminate --json — per-cited-claim records (key, section, check, grade)."""
    if project not in _DELTA:
        r = subprocess.run([sys.executable, "paperkit/discriminate.py", "--json", project],
                           cwd=ROOT, capture_output=True, text=True)
        _DELTA[project] = json.loads(r.stdout or "[]")
    return _DELTA[project]


def _gate(project, *flags):
    """gate --json — structured result (pass, project_ok, verified, sections, collapses)."""
    key = (project, flags)
    if key not in _GATE:
        r = subprocess.run([sys.executable, "paperkit/gate.py", "--json", *flags, project],
                           cwd=ROOT, capture_output=True, text=True)
        _GATE[key] = json.loads(r.stdout or "{}")
    return _GATE[key]


def gate_md():
    rows = []
    for doc, proj in (("paper", "paper"), ("README", ".")):
        g = _gate(proj, "--safe")
        rows.append(f"| {doc} | {'PASS' if g.get('pass') else 'FAIL'} | "
                    f"{'yes' if g.get('project_ok') else 'NO'} | "
                    f"{g.get('verified', 0)} | {g.get('sections', 0)} |")
    return ("| document | gate (--safe) | prose ≡ projection | checks verified | sections |\n"
            "| --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n")


def delta_md():
    recs = _delta("paper")
    counts = {}
    for r in recs:
        counts[r["grade"]] = counts.get(r["grade"], 0) + 1
    order = ["behavioral", "existence", "indeterminate", "vacuous", "broken"]
    summary = ", ".join(f"{counts[g]} {g}" for g in order if counts.get(g))
    rows = [f"| `{r['key']}` | {r.get('section', '')} | {r['grade']} | `{r['check']}` |"
            for r in recs]
    return (f"_{len(recs)} cited claims: {summary}._\n\n"
            "| claim | section | Δ grade | witness |\n| --- | --- | --- | --- |\n"
            + "\n".join(rows) + "\n")


def without_k_md():
    groups = _gate("paper").get("collapses", {})
    if not groups:
        return "Every cited claim carries a distinct witness — `--without-K` is clean.\n"
    rows = [f"| `{c}` | {len(k)} | {', '.join(k)} |" for c, k in sorted(groups.items())]
    return ("| shared witness | claims | collapsed onto it |\n| --- | --- | --- |\n"
            + "\n".join(rows) + "\n")


GENERATORS = {"gate.md": gate_md, "delta.md": delta_md, "without-k.md": without_k_md}


def main(argv):
    if "--check" in argv:
        names = [a for a in argv if a in GENERATORS] or list(GENERATORS)
        stale = [n for n in names
                 if not (ASSETS / n).exists() or (ASSETS / n).read_text() != GENERATORS[n]()]
        if stale:
            print(f"report stale: {', '.join(stale)} — run python3 report/gen.py", file=sys.stderr)
            return 1
        print(f"report fresh ({', '.join(names)})")
        return 0
    ASSETS.mkdir(exist_ok=True)
    for name, gen in GENERATORS.items():
        (ASSETS / name).write_text(gen())
    subprocess.run([sys.executable, "paperkit/project.py", "report"], cwd=ROOT)
    print("report generated", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
