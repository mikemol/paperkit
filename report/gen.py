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
_DELTA = {}


def _delta(project):
    """discriminate --json for a project (cached — the data source for the report)."""
    if project not in _DELTA:
        r = subprocess.run([sys.executable, "paperkit/discriminate.py", "--json", project],
                           cwd=ROOT, capture_output=True, text=True)
        _DELTA[project] = json.loads(r.stdout or "[]")
    return _DELTA[project]


def _passes(*args):
    return subprocess.run([sys.executable, "paperkit/gate.py", *args],
                          cwd=ROOT, capture_output=True).returncode == 0


def gate_md():
    rows = [f"| {doc} | {'PASS' if _passes('--safe', proj) else 'FAIL'} |"
            for doc, proj in (("paper", "paper"), ("README", "."))]
    return "| document | gate (--safe, zero postulates) |\n| --- | --- |\n" + "\n".join(rows) + "\n"


def delta_md():
    counts = {}
    for r in _delta("paper"):
        counts[r["grade"]] = counts.get(r["grade"], 0) + 1
    order = ["behavioral", "existence", "indeterminate", "vacuous", "broken"]
    rows = [f"| {g} | {counts[g]} |" for g in order if counts.get(g)]
    return "| Δ grade | cited claims |\n| --- | --- |\n" + "\n".join(rows) + "\n"


def without_k_md():
    by_check = {}
    for r in _delta("paper"):
        by_check.setdefault(r["check"], []).append(r["key"])
    groups = {c: sorted(k) for c, k in by_check.items() if len(k) > 1}
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
