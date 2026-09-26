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
import os
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


class CannotGrade(RuntimeError):
    """Γ·delta·tristate — the grader could not RUN.  Distinct from "it graded nothing"."""


def _repo(project: str) -> str:
    """The generated repo's apparent name — MODULE.bazel names it the path's LAST segment
    (`bib.project(name = "paperkit_library", project = "paperkit/library")`), `paperkit_root` for `.`."""
    return "paperkit_" + ("root" if project == "." else project.split("/")[-1])


def _record(name: str, project: str) -> str:
    """Ζ·report·records — the TEXT of one of a project's records, staged by Bazel via `consumes` and
    named in PAPERKIT_CONSUMED_RECORDS as `<repo>/<name>` (tools/verb.bzl _consume_key) — in a check,
    and in the refresh (tools/report_refresh.py builds the same records and hands them here).
    `name` ∈ gate_rec (the //:hook verdict), rec_struct.json (the structure-only gate run),
    rec_grades.json (the per-claim Δ table).

    ⚑ WHY THE REPORT NO LONGER SPAWNS THE GATE INSIDE ITS CHECKS.  Every rpt-* witness used to run
    gate.py / discriminate.py over sibling projects in-process, so its footprint was the whole
    working tree — 80-620 files per claim, caches and agent state included, measured 2026-09-25
    once strace reached luthen — and no declaration could cover it.  Bazel's per-claim graph
    already computes each verdict and grade; this reads them (tools/bibtex.bzl, pk_json/pk_grades).

    ⚑⚑ AND THERE IS NO SILENT FALLBACK TO THE LIVE RUN.  A check that finds no record (the footprint
    audit traces checks on the host, where nothing is staged) raises CannotGrade → exit 3, never a
    verdict.  A fallback would re-create exactly the undeclared read this exists to remove, and it
    would do it only in the one environment the audit measures.
    """
    env = os.environ.get("PAPERKIT_CONSUMED_RECORDS")
    if env is None:
        raise CannotGrade(f"no consumed {name} record for {project} — these tables read "
                          "Bazel-built records only; refresh with `python3 tools/report_refresh.py`")
    recs = dict(p.partition("=")[::2] for p in env.split())
    key = f"{_repo(project)}/{name}"
    if key not in recs:
        kind = name.split(".")[0]
        raise CannotGrade(f"no consumed record {key} — the warrant must declare "
                          f"`consumes = {{*#{kind}}}`")
    return Path(recs[key]).read_text()


def _delta(project):
    """discriminate --json — per-cited-claim records (key, section, check, grade).

    ⚑ Γ·delta·tristate — A GRADER THAT COULD NOT RUN IS NOT AN EMPTY CORPUS.  This read
    `json.loads(r.stdout or "[]")` and never looked at `returncode`, so discriminate's REFUSAL
    (it exits 1 with empty stdout when no Δ sandbox root is declared — layout._sandbox_root, the
    guard that exists because inferring the parent once copied ~/github ten times) arrived here
    as the SAME value as a project with no cited claims: `[]`.

    Every generator downstream then rendered a degenerate asset from that empty list, and
    `gen.py --check` reported all four assets STALE.  The report was not stale; its grader had
    refused, and the refusal was wearing a staleness verdict.  That is the FAILED/UNAVAILABLE
    collapse the sibling _gate_once (below) is careful to avoid — {"error": ...}, never a false
    FAIL — applied everywhere in this file except here.

    Raising is the right shape rather than returning a sentinel: a caller that forgets to check
    a sentinel silently renders the degenerate asset, which is the defect being fixed.  Callers
    that must tolerate a cannot-run (the per-claim witnesses) catch this and exit 3
    (resolver._CANNOT_RUN), never a refutation.
    """
    if project not in _DELTA:
        # Ζ·report·records — the project's Δ table over its per-claim grade records (pk_grades).
        _DELTA[project] = json.loads(_record("rec_grades.json", project) or "[]")
    return _DELTA[project]


def _gate_once(project, *flags):
    """One gate --json run.  Robust to a document whose gate can't RUN here: a missing toolchain
    (podman/pandoc/systemd) or a runaway check is caught and reported as an ERROR, distinct from a
    verification FAIL — so an on-demand document is never falsely accused of failing verification
    when the real cause is the environment."""
    # ⚑ Ζ·report·records — STRUCTURE from the structure-only run, VERDICT from gate_rec.  The first
    # construction ran the whole gate in one cell, where cross-project checks cannot resolve: six
    # projects read FAIL while //:hook was green.  The table's PASS/FAIL is now exactly //:hook's.
    if flags not in ((), ("--safe",)):
        raise ValueError(f"no record exists for gate flags {flags}")
    out = _record("rec_struct.json", project)
    try:
        struct = json.loads(out) if out.strip() else {"error": "no structure record output"}
    except json.JSONDecodeError:
        return {"error": "no verdict"}
    if not flags or "error" in struct:
        return struct                        # --without-K collapses: structure only
    verdict = json.loads(_record("gate_rec", project) or "{}").get("verdict")
    if verdict == "cannot-run":
        return {**struct, "error": "cannot run here"}
    return {**struct, "pass": verdict == "pass"}


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
    the CI-tier column says which documents the reproducible local CI gates vs which gate on-demand.

    ⚑ Ζ·census·roster — READ FROM THE ROSTER, NOT DISCOVERED BY WALKING.  This used to be
    `ROOT.rglob("paper.toml")` filtered by `git check-ignore`, and once strace reached luthen
    (2026-09-25) the footprint audit showed what that costs: the walk descends EVERYTHING before
    filtering (.mypy_cache, .claude/, agent worktrees, .githooks/local.env), and the git call reads
    the live repository (.git/HEAD) rather than anything staged — so the census depended on the
    disk, not on declared inputs, and no `builds` list could declare it.  The document set already
    has an owner: MODULE.bazel's `bib.project` roster, which bnd-roster-wired gates in BOTH
    directions against the tracked paper.toml files.  A new document that is not wired therefore
    reds that gate instead of silently entering or leaving this census.
    """
    out = []
    for rel in sorted(_project_paths()):
        d = ROOT if rel == "." else ROOT / rel
        if d == HERE or not (d / "paper.toml").is_file():
            continue
        # ⚑ THE NAME IS THE REPO-RELATIVE PATH, NOT `d.name` (Β / A2-F2).  `d.name` is the LAST
        # SEGMENT, which is not an identity: `paperkit/library` and a stale wheel copy at
        # `build/lib/paperkit/library` both became `library`, and MODULE.bazel already keys this
        # document as `project = "paperkit/library"` — so `_wired_names()` produced a name
        # `_all_docs()` could never match.  Measured before the fix: the concept library was
        # simultaneously reported ON-DEMAND (absent from the wired set) and graded TWICE.
        rel = "." if d == ROOT else str(d.relative_to(ROOT))
        out.append(("README" if d == ROOT else rel, rel))
    out.sort(key=lambda nr: (nr[0] != "paper", nr[0]))
    return out


def _project_paths() -> set:
    """The repo-relative project paths MODULE.bazel wires (`bib.project(project = ...)`), `.` for
    the root — the census's input.

    ⚑ Β / A2-F2, kept for the record: the census once walked the filesystem, so a gitignored
    `build/` copy of the concept library (a wheel build's leftover) entered REPORT.md, and clean CI
    and a developer checkout disagreed.  `git check-ignore` was added to exclude it.  Reading the
    roster removes the walk that needed the exclusion: a stale copy is not in MODULE.bazel.
    """
    return set(re.findall(r'bib\.project\([^)]*project\s*=\s*"([^"]+)"',
                          (ROOT / "MODULE.bazel").read_text()))


def _hook_names():
    """The //:hook member set, as REPO-RELATIVE PROJECT PATHS.

    ⚑ The hook names Bazel REPOS (`@paperkit_library`), MODULE.bazel names PROJECT PATHS
    (`project = "paperkit/library"`), and the two are not the same string.  The old regex returned
    the repo suffix, which happened to equal the path for eleven of twelve projects and silently
    diverged for the twelfth.  So the repo→project map is read from MODULE.bazel — its owner —
    rather than assumed to be the identity.
    """
    block = re.search(r'test_suite\(name = "hook".*?tests = \[(.*?)\]',
                      (ROOT / "BUILD.bazel").read_text(), re.S).group(1)
    repo_to_project = dict(re.findall(
        r'bib\.project\(\s*name\s*=\s*"paperkit_(\w+)"[^)]*?project\s*=\s*"([^"]+)"',
        (ROOT / "MODULE.bazel").read_text()))
    out = set()
    for repo in re.findall(r'@paperkit_(\w+)//:gate\b', block):
        proj = repo_to_project.get(repo, repo)
        out.add("README" if proj == "." else proj)
    return out


def _wired_names():
    return {"README" if p == "." else p for p in _project_paths()}


def _local_names():
    """The host-coupled projects: `bib.project(..., tier = "local")`.

    ⚑ Ζ·report·records — this matched `local = True`, an attribute bib.project does not have (the
    declaration is `tier = "local"`), so it ALWAYS returned the empty set: nothing was on-demand,
    and the gate table ran image's podman and setup's systemd-run gates on the host — the exact
    non-reproducible runs rpt-reproducible says the report lists but does not run.  Found while
    moving the table onto run-once records, which exclude `local` projects by the same rule.
    """
    out = set()
    for call in re.findall(r"bib\.project\([^)]*\)", (ROOT / "MODULE.bazel").read_text(), re.S):
        m = re.search(r'project\s*=\s*"([^"]+)"', call)
        if m and re.search(r'tier\s*=\s*"local"', call):
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
    # Ζ·report·records — the figure plots a claim at its GRADE; a claim with no grade record (gated,
    # never Δ-swept — rec_grades lists it as "not graded") has no position on that axis, so it is
    # left off the plot rather than invented a band.  delta.md still lists it.
    return figure.svg([r for r in _delta("paper") if r["grade"] in grade.rungs()])


GENERATORS = {"gate.md": gate_md, "delta.md": delta_md, "without-k.md": without_k_md,
              "dag.svg": dag_svg}


def main(argv):
    if "--check" in argv:
        # Ρ·report·fresh·named — an UNKNOWN asset name is a REFUSAL, not a wildcard.
        #
        # ⚑ This used to read `[a for a in argv if a in GENERATORS] or list(GENERATORS)`, so any
        # name that was not a generator key filtered to [] and fell through to checking ALL of
        # them.  `fresh:all` was the spelling seven claims used, and "all" is not a key — so seven
        # distinct claims ran one identical, maximally-broad check and none of them discriminated
        # its own asset.  --without-K exists to catch exactly that and could not: report/ is not
        # wired into MODULE.bazel, so no :invariants target ever ran over it.
        #
        # The fallthrough is silent in the SAFE direction (it over-checks), which is why it
        # survived: nothing was ever falsely green.  The cost is that a typo'd or invented asset
        # name reads as "check everything" and passes, so the check string stops naming what the
        # claim is ABOUT.  A name is now either a generator key or an error.
        wanted = [a for a in argv[1:] if not a.startswith("--")]
        unknown = [a for a in wanted if a not in GENERATORS]
        if unknown:
            print(f"report: unknown asset(s) {', '.join(unknown)} — "
                  f"known: {', '.join(GENERATORS)} (use --all for every asset)", file=sys.stderr)
            return 2
        names = wanted or (list(GENERATORS) if "--all" in argv else [])
        if not names:
            print("report: --check names no asset — pass an asset name or --all", file=sys.stderr)
            return 2
        # Γ·delta·tristate — a grader that could not RUN is not a stale asset.  _delta raises
        # rather than yielding [], so this reports CANNOT-RUN (exit 3, resolver._CANNOT_RUN)
        # instead of accusing four committed assets of drift they do not have.
        try:
            stale = [n for n in names
                     if not (ASSETS / n).exists() or (ASSETS / n).read_text() != GENERATORS[n]()]
        except CannotGrade as e:
            print(f"report: cannot check freshness — {e}\nThe committed assets are NOT accused of "
                  "drift; the pipeline that regenerates them could not run.", file=sys.stderr)
            return 3
        if stale:
            print(f"report stale: {', '.join(stale)} — run python3 report/gen.py", file=sys.stderr)
            return 1
        print(f"report fresh ({', '.join(names)})")
        return 0
    # ⚑ Ζ·report·records — THE REFRESH READS THE SAME RECORDS THE CHECKS DO.  It used to run
    # gate.py/discriminate.py live on the host, and the first refresh after the records existed
    # showed why that is wrong: boundaries, render and talk read FAIL from the host run while
    # //:hook was green in the executors — a different environment answering a different question,
    # and assets the in-cell `fresh:` checks would then call stale.  Run tools/report_refresh.py,
    # which builds the records through Bazel and hands them here.
    # ⚑ Γ·delta·tristate — GENERATE ALL, THEN WRITE.  This wrote each asset as it was produced,
    # so an unrunnable grader (discriminate refusing for want of a declared Δ root) silently
    # OVERWROTE the committed assets with the degenerate rendering of an empty record list — the
    # write path being strictly worse than the check path, which merely misreported.  Producing
    # every asset before touching the tree makes a cannot-run leave the committed copies intact.
    try:
        produced = {name: g() for name, g in GENERATORS.items()}
    except CannotGrade as e:
        print(f"report: cannot generate — {e}\nNo asset was written; the committed copies are "
              "unchanged.", file=sys.stderr)
        return 3
    ASSETS.mkdir(exist_ok=True)
    for name, text in produced.items():
        (ASSETS / name).write_text(text)
    subprocess.run([sys.executable, "paperkit/project.py", "report"], cwd=ROOT)
    print("report generated", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
