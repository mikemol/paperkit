#!/usr/bin/env python3
"""paperkit discriminate (Δ) — grade each warrant's check by whether it can FAIL.

A check earns a claim only to the extent it is sensitive to the world: a check
that passes no matter what the project says verifies nothing.  The gate enforces
that every sentence NAMES a passing check; Δ asks the next question — could that
check ever have failed?  It grades every warrant's `check` on a computable
discrimination ladder, and for runnable (cmd/custom) checks it empirically
discovers the check's SENSITIVITY SET — the input files whose corruption flips
the check red — by single-file mutation in a throwaway sandbox.

Grades (this is also the `strength` field that Γ — graded thresholds — will read):

  vacuous     PROVABLY cannot fail: a file: check whose target is a required
              project input or engine source, so its existence is presupposed by
              the build itself.  Tests presence of something that must be there
              anyway — 0 bits about the claim.
  existence   file: of a CONTINGENT artifact (a build output, a figure) — its
              absence is a real failure, so it discriminates "the artifact was
              produced", but nothing about the artifact's content.
  behavioral  PROVEN falsifiable: some single-file mutation flips this cmd/custom
              check red.  It runs, and it can go red — the sensitivity set names
              exactly which inputs it actually tests.
  indeterminate  a cmd/custom check that no generic mutation could flip.  Either
              genuinely vacuous OR a NEGATIVE-ASSERTION check (one that passes
              precisely when the system correctly rejects bad input, e.g. a
              drift-rejection test — garbage input keeps the rejection true).
              Δ refuses to guess: falsifiability is not demonstrated.  Closing
              this needs a targeted counter-fixture (a Π task), not a verdict.

Δ does NOT judge whether a behavioral check's sensitivity set actually concerns
the CLAIM's content — a check sensitive to the right files for the wrong claim is
the launder case, left to Λ.  Δ reports the set; Λ judges relevance.

Binding dilution: a check shared by N cited claims supplies one verdict for N
sentences — reported as `shared_with`, the per-claim signal being the per-check
signal split N ways.

    paperkit-discriminate [DIR]                  report (exit 0)
    paperkit-discriminate --min-strength L [DIR] gate: exit 1 if any considered
                                                 warrant grades below L
                                                 (L = existence | behavioral)
    paperkit-discriminate --all [DIR]            grade every checked warrant, not
                                                 just those cited in the prose
    paperkit-discriminate --json [DIR]           machine output (feeds Γ / Π)
    paperkit-discriminate --state F --budget S [DIR]   resumable grading (pump-witness):
                                                 grade under an S-second budget, persist the
                                                 token to F, exit 2 if not done — re-run to
                                                 resume.  A slow grade resumes, never dies.
    paperkit-discriminate --no-cache [DIR]       ignore the content-addressed cache

Grades are memoized by content_key (the project's files + the engine): an unchanged
project re-grades in milliseconds (.delta-cache.json, git-ignored), recomputed only
when something a check could read changes.

DIR defaults to the current directory and must contain paper.toml.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project as P  # noqa: E402
import gate as G  # noqa: E402
import driver as D  # noqa: E402  (pump/parse liveness driver — resumable grading)

CORRUPT = b"\x00\x00DELTA-CORRUPTION\x00\x00\n"
MUTABLE_SUFFIXES = {".bib", ".tsv", ".toml", ".md", ".sh", ".py", ".txt"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "out"}
_ENGINE = Path(__file__).resolve().parent


def _sandbox_root(project_dir):
    """The dir to copy into the mutation sandbox: project_dir itself when the engine
    lives INSIDE it (a self-contained project — the README at the repo root, whose
    deps are paperkit/), else its parent (a project whose deps are a sibling — the
    paper's ../paperkit — or a self-contained fixture whose engine is elsewhere)."""
    return project_dir if _ENGINE.is_relative_to(project_dir) else project_dir.parent


def _nested_roots(base: Path) -> list:
    """Directories under `base` that are OTHER paperkit projects (each has its own
    paper.toml).  A root-level project (the README, whose project dir IS the repo)
    must not key on, or mutate, sibling projects' files — only its own + the engine."""
    return [t.parent for t in base.rglob("paper.toml") if t.parent != base]


def _mutable(f: Path) -> bool:
    """A text input Δ may corrupt: a known source suffix, or a versioned git hook
    (no suffix, but a checked artifact — the README's ci claim names it)."""
    return f.is_file() and (f.suffix in MUTABLE_SUFFIXES or ".githooks" in f.parts)

STRENGTH = {"vacuous": 0, "existence": 1, "indeterminate": 1, "behavioral": 2}
ORDER = {"existence": 1, "behavioral": 2}  # valid --min-strength thresholds

# Total order for clamping (effective grade = min over self + premises).  Conservative:
# vacuous < indeterminate (runs, falsifiability unproven) < existence (presence proven)
# < behavioral (falsifiability proven).
RANK_C = {"broken": -1, "vacuous": 0, "indeterminate": 1, "existence": 2, "behavioral": 3}
GRADE_C = {v: k for k, v in RANK_C.items()}


def content_key(project_dir: Path) -> str:
    """A hash of every file a check in this project could read — the project's own
    files plus the engine.  A Δ grade is a pure function of these (the mutation probe
    only ever reads them), so a cached grade is valid exactly while this key holds."""
    engine = Path(__file__).resolve().parent
    parts = []
    for tag, base in (("proj", project_dir), ("engine", engine)):
        nested = _nested_roots(base) if tag == "proj" else []
        for f in sorted(base.rglob("*")):
            if (_mutable(f) and not any(p in SKIP_DIRS for p in f.parts)
                    and not any(nr in f.parents for nr in nested)):
                parts.append(f"{tag}/{f.relative_to(base)}:{hashlib.sha256(f.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(sorted(parts)).encode()).hexdigest()


def _load_cache(project_dir: Path) -> dict:
    p = project_dir / ".delta-cache.json"
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}


def presupposed_inputs(project_dir: Path, cfg: dict) -> set:
    """Resolved paths whose existence the build already presupposes — a file:
    check naming one of these is redundant with the project being runnable, so
    it is provably vacuous.  The declared bibs / rubric / config / output, plus
    the engine scripts the checks invoke via ../paperkit."""
    req = set(cfg["bibs"]) | {cfg["rubric"], cfg["out"], project_dir / "paper.toml"}
    engine = Path(__file__).resolve().parent
    req |= set(engine.glob("*.py"))
    return {p.resolve() for p in req}


def sandbox_files(sandbox_project: Path, exclude_scripts: set) -> list:
    """Mutable text inputs under the sandboxed project (the verifier scripts
    themselves are excluded — corrupting a check's own script is a trivial,
    uninformative self-break)."""
    out = []
    nested = _nested_roots(sandbox_project)
    for f in sorted(sandbox_project.rglob("*")):
        if not _mutable(f):
            continue
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        if any(nr in f.parents for nr in nested):
            continue  # a sibling project's file — not this project's to mutate
        if f.suffix == ".sh" and "checks" in f.parts:
            continue  # a verifier script; its corruption tests itself, not the claim
        out.append(f)
    return out


def sensitivity(chk: str, sandbox_project: Path, custom: dict) -> tuple[bool, list]:
    """Run chk against single-file corruptions of the sandbox; return
    (baseline_passes, sensitivity_set) where the set is the relative paths whose
    corruption flips chk from pass to fail."""
    baseline = G.resolves(chk, sandbox_project, custom)
    sens: list[str] = []
    if not baseline:
        return False, sens
    for f in sandbox_files(sandbox_project, set()):
        orig = f.read_bytes()
        f.write_bytes(CORRUPT)
        try:
            flipped = not G.resolves(chk, sandbox_project, custom)
        finally:
            f.write_bytes(orig)
        if flipped:
            sens.append(str(f.relative_to(sandbox_project)))
    return True, sens


def grade_check(chk: str, project_dir: Path, presupposed: set,
                custom: dict, sandbox_project: Path) -> dict:
    typ, _, target = chk.partition(":")
    if typ == "file":
        resolved = (project_dir / target).resolve()
        if resolved in presupposed:
            return {"grade": "vacuous", "tests": [target],
                    "why": "existence of a required project/engine source — presupposed by the build",
                    "not_higher": "to rise: give it a check that can FAIL — a file: of a presupposed input is removed by no real change",
                    "not_lower": "vacuous is the floor"}
        return {"grade": "existence", "tests": [target],
                "why": "existence of a contingent artifact — presence only, not content",
                "not_higher": "to rise: test the artifact's CONTENT, not just its presence (a content-sensitive cmd:)",
                "not_lower": "not vacuous: the artifact is contingent, not a presupposed build input, so its absence is a real failure"}
    # cmd: / custom — empirically probe falsifiability
    baseline, sens = sensitivity(chk, sandbox_project, custom)
    if not baseline:
        return {"grade": "broken", "tests": [],
                "why": "check does not pass in a pristine sandbox — repo is not green",
                "not_higher": "—", "not_lower": "—"}
    if sens:
        return {"grade": "behavioral", "tests": sens,
                "why": f"falsifiable — corrupting {len(sens)} input(s) flips it red",
                "not_higher": "behavioral is the top tier; a proof-grade (total, postulate-free witness) tier is not yet defined",
                "not_lower": f"not indeterminate/vacuous: a mutation DOES flip it (sensitive to {len(sens)} input(s))"}
    return {"grade": "indeterminate", "tests": [],
            "why": "no generic mutation flips it — vacuous OR a negative-assertion check; needs a targeted counter-fixture (Π)",
            "not_higher": "to rise: a targeted counter-fixture (a positive mutation) would prove it behavioral",
            "not_lower": "not provably vacuous: it runs a cmd:, not a presupposed file:"}


def _grade_one(project_dir, chk, custom, presupposed):
    """Grade one check in its own fresh sandbox copy (so concurrent grades never
    share a mutation).  The copy is the bounded universe of the project + engine."""
    tmp = Path(tempfile.mkdtemp(prefix="paperkit-delta-"))
    try:
        root = _sandbox_root(project_dir)
        shutil.copytree(root, tmp / root.name,
                        ignore=shutil.ignore_patterns(*SKIP_DIRS, "*.pyc"), dirs_exist_ok=True)
        rel = project_dir.relative_to(root)
        sandbox = tmp / root.name if rel == Path(".") else tmp / root.name / rel
        return grade_check(chk, project_dir, presupposed, custom, sandbox)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _grade_parallel(project_dir, checks, custom, presupposed):
    """Grade every distinct check CONCURRENTLY — each is an independent target with
    its own sandbox, so the sweep's wall-clock is the slowest single check, not their
    sum.  Bounded at cpu_count (a heavy check may itself fan out a nested gate)."""
    jobs = max(1, min(len(checks), os.cpu_count() or 4))
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        graded = list(ex.map(lambda c: _grade_one(project_dir, c, custom, presupposed), checks))
    return dict(zip(checks, graded))


class GradeWitness:
    """Δ's grading sweep as a pump()/parse() witness: one distinct check graded per
    pump(), state = {cursor, graded}.  The heavy per-check sandbox is rebuilt INSIDE
    pump and never crosses the serialization boundary — only the cheap cursor and the
    scalar grade results are persisted, so a long grade is resumable (driver.py).
    Used for the resumable (--state/--budget) path; the default path grades in
    parallel via _grade_parallel."""

    def __init__(self, project_dir, checks, custom, presupposed):
        self.project_dir, self.checks = project_dir, checks
        self.custom, self.presupposed = custom, presupposed

    def initial(self):
        return {"cursor": 0, "graded": {}}

    def pump(self, state):
        i = state["cursor"]
        if i >= len(self.checks):
            return state
        chk = self.checks[i]
        g = _grade_one(self.project_dir, chk, self.custom, self.presupposed)
        return {"cursor": i + 1, "graded": {**state["graded"], chk: g}}

    def parse(self, state):
        return {"done": state["cursor"] >= len(self.checks), "graded": state["graded"],
                "progress": f'{state["cursor"]}/{len(self.checks)}'}

    def serialize(self, state):
        return json.dumps(state, sort_keys=True)

    def deserialize(self, s):
        return json.loads(s)


def main(argv: list) -> int:
    flags = [a for a in argv if a.startswith("-")]
    args = [a for a in argv if not a.startswith("-")]

    def optval(name):
        return argv[argv.index(name) + 1] if name in argv else None

    min_strength = optval("--min-strength")
    if min_strength is not None and min_strength not in ORDER:
        sys.exit(f"paperkit-discriminate: --min-strength must be one of {sorted(ORDER)}")
    state_file = optval("--state")          # resumable grading: persist the token here
    budget_str = optval("--budget")         # seconds per invocation (<=0 = run to done)
    budget = float(budget_str) if budget_str else 0.0
    consider_all = "--all" in flags
    as_json = "--json" in flags

    consumed = {x for x in (min_strength, state_file, budget_str) if x is not None}
    pos = [a for a in args if a not in consumed]
    project_dir = Path(pos[0]).resolve() if pos else Path.cwd()
    cfg = P.load_config(project_dir)
    custom = tomllib.loads((project_dir / "paper.toml").read_text()).get("checks", {})
    presupposed = presupposed_inputs(project_dir, cfg)

    F = {}
    for b in cfg["bibs"]:
        F.update(P.entries(b))

    out = cfg["out"]
    cited = G.cited_keys(out.read_text()) if out.exists() else set()

    # which warrants to grade
    keys = [k for k, f in F.items() if f.get("check")
            and (consider_all or k in cited)]

    # share counts: how many CONSIDERED warrants lean on each distinct check
    share: dict[str, list] = {}
    for k in keys:
        share.setdefault(F[k]["check"], []).append(k)

    # Memoize: a Δ grade is a pure function of content_key(project), so a cached
    # graded-set is reused verbatim while nothing the checks read has changed — the
    # expensive mutation sweep runs only when the project or engine actually changes.
    no_cache = "--no-cache" in flags
    key = content_key(project_dir)
    cached = {} if no_cache else _load_cache(project_dir)
    if cached.get("key") == key and all(c in cached.get("graded", {}) for c in share):
        graded = cached["graded"]
    elif state_file is None and budget is None:
        # Default: grade every distinct check CONCURRENTLY (each its own sandbox), so a
        # project with heavy checks (the README's gate-paper / boundary-suite) grades in
        # the time of its slowest check, not the sum.
        graded = _grade_parallel(project_dir, list(share), custom, presupposed)
        if not no_cache:
            (project_dir / ".delta-cache.json").write_text(json.dumps({"key": key, "graded": graded}))
    else:
        # Resumable path: grade as a pump-witness, one check per increment, under an
        # optional budget (--state/--budget make a long grade resume across short calls
        # instead of dying with nothing — the pump-ask liveness rule).
        witness = GradeWitness(project_dir, list(share), custom, presupposed)
        meaning, steps, done = D.drive(witness, state_path=state_file, budget=budget)
        if not done:
            print(f"paperkit-discriminate: graded {meaning['progress']} in {steps} increment(s) — "
                  f"not done; state persisted to {state_file}, re-run to resume", file=sys.stderr)
            return 2
        graded = meaning["graded"]
        if not no_cache:
            (project_dir / ".delta-cache.json").write_text(json.dumps({"key": key, "graded": graded}))

    records = []
    for k in keys:
        chk = F[k]["check"]
        g = dict(graded[chk])
        g.update(key=k, check=chk, cited=k in cited, section=F[k].get("section"),
                 shared_with=[o for o in share[chk] if o != k])
        g["from"] = F[k].get("from", [])
        g["rests-on"] = F[k].get("rests-on", [])     # grounding edges (for clamping)
        records.append(g)

    # content inputs = the files a check must touch to discriminate the paper's
    # CONTENT (not merely its config/engine); a behavioral check sensitive only
    # to paper.toml or the engine can-fail by CRASH, but does not test content.
    content = {p.name for p in cfg["bibs"]} | {cfg["rubric"].name, cfg["out"].name}
    for r in records:
        if r["grade"] == "behavioral":
            r["content_sensitive"] = any(Path(t).name in content for t in r["tests"])

    # EFFECTIVE grade — clamp by entailment: a claim is no better grounded than the
    # weakest premise it (transitively) depends on.  `clamp` = rungs dropped from the
    # self-contained grade; `clamped_by` = the premise that pins it.
    rby = {r["key"]: r for r in records}
    effc: dict = {}

    def eff(k, stack=()):
        if k in effc:
            return effc[k]
        r = rby.get(k)
        if r is None:
            return (RANK_C["behavioral"], None)   # not in scope: impose no constraint
        best, by = RANK_C.get(r["grade"], 0), None
        for d in r.get("rests-on", []):              # clamp over GROUNDING edges
            if d in rby and d not in stack and d != k:
                de, _ = eff(d, stack + (k,))
                if de < best:
                    best, by = de, d
        effc[k] = (best, by)
        return effc[k]

    for r in records:
        e, by = eff(r["key"])
        r["effective_grade"] = GRADE_C[e]
        r["clamp"] = RANK_C.get(r["grade"], 0) - e
        r["clamped_by"] = by

    if as_json:
        print(json.dumps(records, indent=2))
    else:
        report(records, share, graded, len(cited), len(keys), consider_all)

    rc = 0
    if min_strength is not None:
        floor = ORDER[min_strength]
        weak = [r for r in records if STRENGTH.get(r["grade"], 0) < floor]
        if weak:
            print(f"\npaperkit-discriminate: {len(weak)} warrant(s) below "
                  f"strength '{min_strength}':", file=sys.stderr)
            for r in weak:
                print(f"  [@{r['key']}] {r['grade']} — {r['check']}", file=sys.stderr)
            rc = 1
        else:
            print(f"\npaperkit-discriminate: all {len(records)} warrant(s) "
                  f"meet strength '{min_strength}'")
    return rc


def report(records, share, graded, n_cited, n_checked, consider_all):
    scope = "all checked" if consider_all else f"of {n_cited} cited"
    print(f"paperkit-discriminate (Δ): {n_checked} {scope} warrant(s) carry a "
          f"check, {len(share)} distinct check(s)\n")
    order = {"broken": 0, "vacuous": 1, "indeterminate": 2, "existence": 3, "behavioral": 4}
    for r in sorted(records, key=lambda r: (order.get(r["grade"], 9), r["key"])):
        share_n = len(r["shared_with"]) + 1
        dil = f"  (shared by {share_n} claims)" if share_n > 1 else ""
        crash = (r["grade"] == "behavioral" and not r.get("content_sensitive"))
        tag = "  ⚠ config/crash-sensitive only" if crash else ""
        print(f"  {r['grade']:13} [@{r['key']}]{dil}{tag}")
        print(f"  {'':13} check: {r['check']}")
        if r["tests"]:
            shown = ", ".join(r["tests"][:6]) + ("…" if len(r["tests"]) > 6 else "")
            print(f"  {'':13} sensitive to: {shown}")
        why = r["why"]
        if crash:
            why += " — but touches no content input (warrants/rubric/prose); flips only by crashing on malformed config"
        print(f"  {'':13} {why}\n")
    counts: dict[str, int] = {}
    for r in records:
        counts[r["grade"]] = counts.get(r["grade"], 0) + 1
    summary = ", ".join(f"{n} {g}" for g, n in sorted(counts.items()))
    print(f"  summary (self-grade): {summary}")
    eff_counts: dict[str, int] = {}
    for r in records:
        eff_counts[r.get("effective_grade", r["grade"])] = \
            eff_counts.get(r.get("effective_grade", r["grade"]), 0) + 1
    print(f"  summary (effective):  {', '.join(f'{n} {g}' for g, n in sorted(eff_counts.items()))}")
    clamped = [r for r in records if r.get("clamp", 0) > 0]
    vac = counts.get("vacuous", 0)
    if vac:
        print(f"  ⚠ {vac} cited claim(s) rest on a check that PROVABLY cannot fail.")
    if clamped:
        print(f"  ⚠ {len(clamped)} cited claim(s) are CLAMPED below their self grade by "
              f"weaker premises (effective < self).")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
