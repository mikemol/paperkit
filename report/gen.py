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

import figure  # report/figure.py — the claim-DAG adequacy plot

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


def _projects():
    """The paperkit projects this report covers: every dir with a paper.toml,
    EXCLUDING nested fixtures (a paper.toml inside another project's subtree) and
    the report itself (its own checks regenerate this report, so gating/grading it
    here would recurse).  Discovered, not hard-coded — new projects join the report
    automatically.  Paper first (the flagship), then the rest by name."""
    tomls = sorted(p.parent for p in ROOT.rglob("paper.toml") if ".git" not in p.parts)
    out = []
    for d in tomls:
        # skip the report itself, and any project nested inside ANOTHER NON-ROOT
        # project (a fixture — every project is trivially under the root project, so
        # the root must not count as the container).
        if d == HERE or any(o not in (d, ROOT) and o in d.parents for o in tomls):
            continue
        name = "README" if d == ROOT else d.name
        out.append((name, "." if d == ROOT else str(d.relative_to(ROOT))))
    out.sort(key=lambda nr: (nr[0] != "paper", nr[0]))
    return out


def gate_md():
    rows = []
    for name, proj in _projects():
        g = _gate(proj, "--safe")
        rows.append(f"| {name} | {'PASS' if g.get('pass') else 'FAIL'} | "
                    f"{'yes' if g.get('project_ok') else 'NO'} | "
                    f"{g.get('verified', 0)} | {g.get('sections', 0)} |")
    return ("| document | gate (--safe) | prose ≡ projection | checks verified | sections |\n"
            "| --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n")


def _delta_section(name, recs):
    order = ["behavioral", "existence", "indeterminate", "vacuous", "broken"]
    counts, eff_counts, clamped = {}, {}, 0
    for r in recs:
        counts[r["grade"]] = counts.get(r["grade"], 0) + 1
        e = r.get("effective_grade", r["grade"])
        eff_counts[e] = eff_counts.get(e, 0) + 1
        clamped += 1 if r.get("clamp", 0) > 0 else 0
    selfs = ", ".join(f"{counts[g]} {g}" for g in order if counts.get(g))
    effs = ", ".join(f"{eff_counts[g]} {g}" for g in order if eff_counts.get(g))

    def cell(r):
        e = r.get("effective_grade", r["grade"])
        return r["grade"] if r.get("clamp", 0) == 0 else f"{r['grade']} → **{e}**"

    rows = [f"| `{r['key']}` | {cell(r)} | `{r['check']}` | "
            f"{r.get('why', '')} | {r.get('not_higher', '')} | {r.get('not_lower', '')} |"
            for r in recs]
    return (f"### {name}\n\n_{len(recs)} cited claims — self-grade: {selfs}; effective "
            f"(clamped by entailment): {effs}; {clamped} clamped below self._\n\n"
            "| claim | self → effective | witness | why this grade | why not higher | why not lower |\n"
            "| --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n")


def delta_md():
    return "\n".join(_delta_section(name, _delta(proj)) for name, proj in _projects())


def without_k_md():
    parts = []
    for name, proj in _projects():
        groups = _gate(proj).get("collapses", {})
        if not groups:
            parts.append(f"**{name}** — every cited claim carries a distinct witness; "
                         "`--without-K` is clean.")
        else:
            rows = [f"| `{c}` | {len(k)} | {', '.join(k)} |" for c, k in sorted(groups.items())]
            parts.append(f"**{name}**\n\n| shared witness | claims | collapsed onto it |\n"
                         "| --- | --- | --- |\n" + "\n".join(rows))
    return "\n\n".join(parts) + "\n"


def dag_svg():
    # The figure is the PAPER's grounding DAG — it is the only project with rests-on
    # (grounding) edges; the others have flat claim sets, nothing to plot.
    return figure.svg(_delta("paper"))


GENERATORS = {"gate.md": gate_md, "delta.md": delta_md, "without-k.md": without_k_md,
              "dag.svg": dag_svg}


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
