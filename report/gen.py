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
import re
import subprocess
import sys
from pathlib import Path

import figure  # report/figure.py — the claim-DAG adequacy plot

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "paperkit"))
import grade  # noqa: E402  (Μ·grade — the ladder LEAF; the summary DERIVES its rungs, never lists them)
ASSETS = HERE / "assets"
_DELTA, _GATE = {}, {}


def _delta(project):
    """discriminate --json — per-cited-claim records (key, section, check, grade)."""
    if project not in _DELTA:
        r = subprocess.run([sys.executable, "paperkit/discriminate.py", "--json", project],
                           cwd=ROOT, capture_output=True, text=True)
        _DELTA[project] = json.loads(r.stdout or "[]")
    return _DELTA[project]


def _gate_once(project, *flags):
    """One gate --json run.  Robust to a document whose gate can't RUN here: a missing toolchain
    (podman/pandoc/systemd) or a runaway check is caught and reported as an ERROR, distinct from a
    verification FAIL — so an on-demand document is never falsely accused of failing verification
    when the real cause is the environment."""
    try:
        r = subprocess.run([sys.executable, "paperkit/gate.py", "--json", *flags, project],
                           cwd=ROOT, capture_output=True, text=True, timeout=300)
        return json.loads(r.stdout) if r.stdout.strip() else {"error": (r.stderr.strip() or "no output").splitlines()[-1][:60]}
    except subprocess.TimeoutExpired:
        return {"error": "timed out (>300s)"}
    except json.JSONDecodeError:
        return {"error": "no verdict"}


def _gate(project, *flags):
    key = (project, flags)
    if key not in _GATE:
        _GATE[key] = _gate_once(project, *flags)
    return _GATE[key]


def _gate_stable(project, *flags, tries=3, runner=None):
    """Retry to a WARM-CACHE FIXPOINT.  An on-demand gate's FIRST (cache-populating) run can differ
    from later ones — podman builds its layers, apk fetches over the network, libreoffice writes its
    profile — so rerun WHILE the verdict changes and return the converged (warm) result; convergence
    is two consecutive runs agreeing.  If it never converges within `tries`, the variance is NOT
    cache-warmth but a clock/threshold cause: return it flagged `_stable=False` for separate
    characterization, never laundering an unstable verdict as reproducible.  `runner` is injectable so
    the fixpoint logic is proven deterministically (mitigation.py) without running the flaky builds."""
    run = runner or (lambda: _gate_once(project, *flags))
    prev = last = None
    for i in range(tries):
        last = run()
        k = (last.get("pass"), last.get("verified"), last.get("error"))
        if k == prev:
            return {**last, "_stable": True, "_tries": i + 1}
        prev = k
    return {**last, "_stable": False, "_tries": tries}


def _all_docs():
    """EVERY document in the repository (a dir with a paper.toml), excluding nested fixtures and the
    report itself.  The gate-status table covers all of them with their REAL status on THIS machine —
    so the report is environment-dependent for the on-demand documents (render/image/setup need
    pandoc/podman/systemd), BY DESIGN: it reports what this run could actually verify, honestly, and
    the CI-tier column says which documents the reproducible local CI gates vs which gate on-demand."""
    tomls = sorted(p.parent for p in ROOT.rglob("paper.toml") if ".git" not in p.parts)
    out = []
    for d in tomls:
        if d == HERE or any(o not in (d, ROOT) and o in d.parents for o in tomls):
            continue
        out.append(("README" if d == ROOT else d.name, "." if d == ROOT else str(d.relative_to(ROOT))))
    out.sort(key=lambda nr: (nr[0] != "paper", nr[0]))
    return out


def _hook_names():
    block = re.search(r'test_suite\(name = "hook".*?tests = \[(.*?)\]',
                      (ROOT / "BUILD.bazel").read_text(), re.S).group(1)
    return {"README" if n == "root" else n for n in re.findall(r'@paperkit_(\w+)//:gate\b', block)}


def _wired_names():
    return {"README" if p == "." else p
            for p in re.findall(r'bib\.project\([^)]*project\s*=\s*"([^"]+)"', (ROOT / "MODULE.bazel").read_text())}


def _local_names():
    out = set()
    for line in (ROOT / "MODULE.bazel").read_text().splitlines():
        m = re.search(r'bib\.project\([^)]*project\s*=\s*"([^"]+)"', line)
        if m and "local = True" in line:
            out.add("README" if m.group(1) == "." else m.group(1))
    return out


def _ondemand_names():
    """Documents whose gate is NON-reproducible, so the report lists but does not RUN them: a project
    that is not Bazel-wired (render/image — external toolchains) or is host-coupled `local` (setup —
    its experiment is non-deterministic).  A `wired && !local` document gates sandbox-clean and
    deterministically, so it is run and recorded with real status.  See the rpt-reproducible claim
    and determinism.py — the reproducibility boundary is itself a checked claim, not a silent scope."""
    wired, local = _wired_names(), _local_names()
    return {n for n, _ in _all_docs() if n not in wired or n in local}


def _graded():
    """The documents with a REPRODUCIBLE Δ grade — the //:hook set.  The deep grade/proof tables cover
    these; mutation-grading the on-demand documents is impractical (it re-runs pandoc/podman/systemd
    per mutation site, per claim), so the gate-status table above covers all documents but the Δ and
    proof analyses cover the CI-gated ones."""
    hook = _hook_names()
    return [(n, p) for n, p in _all_docs() if n in hook]


def _tier(name):
    if name in _hook_names():
        return "//:hook"
    return "wired" if name in _wired_names() else "on-demand"


def gate_md():
    ondemand = _ondemand_names()
    rows = []
    for name, proj in _all_docs():
        if name in ondemand:   # non-reproducible gate — listed, not run (see rpt-reproducible)
            rows.append(f"| {name} | on-demand | — | — | — | {_tier(name)} |")
            continue
        g = _gate(proj, "--safe")
        status = f"n/a — {g['error']}" if "error" in g else ("PASS" if g.get("pass") else "FAIL")
        rows.append(f"| {name} | {status} | {'yes' if g.get('project_ok') else '—'} | "
                    f"{g.get('verified', 0)} | {g.get('sections', 0)} | {_tier(name)} |")
    return ("| document | gate (--safe) | prose ≡ projection | checks verified | sections | CI tier |\n"
            "| --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n")


def _delta_section(name, recs):
    # Ζ·ladder — DERIVED from the engine's ladder, never re-listed: this line used to omit
    # `imported`, so a view importing a concept certificate had its claim dropped from the
    # summary's own total ("80 cited claims — self-grade: 79 behavioral", the 80th unaccounted).
    order = grade.rungs()
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
    return "\n".join(_delta_section(name, _delta(proj)) for name, proj in _graded())


def without_k_md():
    parts = []
    for name, proj in _graded():
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
