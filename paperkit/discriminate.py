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

Grades are memoized PER CHECK (Δ·footprint-cache): each check's grade is keyed on the
content of the files it actually READS (Φ·footprint) plus a global engine epoch, so a
commit re-grades only the checks whose footprint the diff touched — not the whole
project.  (.delta-cache.json, git-ignored.  content_key below is the coarse soundness
basis the per-check key refines: a grade is a pure function of project+engine content.)

DIR defaults to the current directory and must contain paper.toml.
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project as P  # noqa: E402
import gate as G  # noqa: E402
import driver as D  # noqa: E402  (pump/parse liveness driver — resumable grading)

CORRUPT = b"\x00\x00DELTA-CORRUPTION\x00\x00\n"

# Project topology and the grade cache now live in their own small modules (so each is
# testable apart from the grader); imported under the names the grader/CLI below already use.
from layout import SKIP_DIRS, _ENGINE, _sandbox_root, _nested_roots, _mutable  # noqa: E402,F401
from cache import (content_key, engine_hash as _engine_hash,  # noqa: E402,F401
                   footprint_hash as _footprint_hash, load as _load_cache, save as _save_cache)

STRENGTH = {"vacuous": 0, "existence": 1, "indeterminate": 1, "behavioral": 2, "imported": 3}
ORDER = {"existence": 1, "behavioral": 2}  # valid --min-strength thresholds

# Total order for clamping (effective grade = min over self + premises).  Conservative:
# vacuous < indeterminate (runs, falsifiability unproven) < existence (presence proven)
# < behavioral (falsifiability proven) < imported (Ξ·seam: verified whole in a separately-
# gated sibling — a delegated premise never weakens what rests on it, so it ranks at top).
RANK_C = {"broken": -1, "vacuous": 0, "indeterminate": 1, "existence": 2, "behavioral": 3,
          "imported": 4}
GRADE_C = {v: k for k, v in RANK_C.items()}


def presupposed_inputs(project_dir: Path, cfg: dict) -> set:
    """Resolved paths whose existence the build already presupposes — a file:
    check naming one of these is redundant with the project being runnable, so
    it is provably vacuous.  The declared bibs / rubric / config / output, plus
    the engine scripts the checks invoke via ../paperkit."""
    req = set(cfg["bibs"]) | {cfg["rubric"], cfg["out"], project_dir / "paper.toml"}
    engine = Path(__file__).resolve().parent
    req |= set(engine.glob("*.py"))
    return {p.resolve() for p in req}


def sandbox_files(sandbox_project: Path, exclude_scripts: set, engine_dir: Path | None = None) -> list:
    """Mutable text inputs Δ may corrupt: the sandboxed project's own files PLUS the
    engine the checks run through (`engine_dir`) — so an engine-claim's witness is
    sensitive to the engine source it tests, not only to its own script.  The verifier
    scripts and sibling projects are excluded; the engine is deduped if already inside."""
    out, seen = [], set()

    def collect(base: Path, skip_nested: bool):
        nested = _nested_roots(base) if skip_nested else []
        for f in sorted(base.rglob("*")):
            if not _mutable(f) or any(part in SKIP_DIRS for part in f.parts):
                continue
            if any(nr in f.parents for nr in nested):
                continue  # a sibling project's file — not this project's to mutate
            if f.suffix == ".sh" and "checks" in f.parts:
                continue  # a verifier script; its corruption tests itself, not the claim
            r = f.resolve()
            if r not in seen:
                seen.add(r)
                out.append(f)

    collect(sandbox_project, skip_nested=True)
    if engine_dir is not None:
        collect(engine_dir, skip_nested=False)   # the engine the checks run through
    return out


def _rel(f: Path, sandbox_project: Path, engine_dir: Path | None) -> str:
    """Label a corrupted file: relative to the project, or tagged engine/<…> when it is
    the engine (outside the project, e.g. the paper's ../paperkit)."""
    try:
        return str(f.relative_to(sandbox_project))
    except ValueError:
        return f"{engine_dir.name}/{f.relative_to(engine_dir)}"


# Mutation resolution (the granularity knob g, set by main() from --resolution):
#   "file"  whole-file corruption, project surface only — fast, coarse, the gate's
#           pass/fail falsifiability question (the default, the pre-commit hook).
#   "def"   definition-resolution group testing over project + ENGINE — the precise
#           per-claim capability fingerprint that closes ∂²'s sensitivity face, but
#           ~an order of magnitude costlier (the on-demand coherence pass).
_RESOLUTION = "file"


def _def_sites(text: str) -> list:
    """Every def/method in a .py source as (qualname, node).  Mutation resolution
    for code is the DEFINITION, not the file: corrupting a whole engine file breaks
    its `import` and flips EVERY witness identically (the import-crash flood, one
    collapsed signature); breaking one function's BODY leaves the module importable,
    so a witness flips only if it actually exercises that function — the sensitivity
    set becomes the measured fingerprint of the engine capabilities the claim rests on."""
    out: list = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out

    def rec(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # a one-liner (`def f(): return 1`) shares its signature line with the
                # body, so a line-span replacement can't isolate the body — skip it.
                if child.body[0].lineno > child.lineno:
                    out.append((prefix + child.name, child))
                rec(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                rec(child, prefix + child.name + ".")
            else:
                rec(child, prefix)

    rec(tree, "")
    return out


def _mutate_lines(text: str, nodes: list) -> str:
    """Replace each given def's body line-span with an UNCATCHABLE raise, leaving the
    rest of the file byte-identical (so a source-grep witness flips only when ITS
    grepped text lived in a mutated body, not because the file was reformatted).
    BaseException — not Exception — so a witness's own `except Exception` cannot
    swallow the mutation; that makes group testing MONOTONE BY CONSTRUCTION (a group
    fails iff some member fails alone) rather than resting on an assumption that no
    witness catches the raise."""
    lines = text.splitlines(keepends=True)
    for node in sorted(nodes, key=lambda n: n.body[0].lineno, reverse=True):
        s, e = node.body[0].lineno, node.end_lineno
        col = node.body[0].col_offset
        lines[s - 1:e] = [" " * col + "raise BaseException('PAPERKIT_MUT')\n"]
    return "".join(lines)


def sensitivity(chk: str, sandbox_project: Path, custom: dict,
                engine_dir: Path | None = None) -> tuple[bool, list]:
    """The sensitivity set — the mutations that flip chk red — found by BINARY-SPLIT
    GROUP TESTING, not a linear scan over every site.  Mutate a whole group of sites
    at once: if it does NOT flip, the entire group is proven clear in ONE run (the
    sparse non-flippers cost nothing); if it flips, bisect.  O(k·log n) runs for k
    flips, against O(n) for the scan — and the bisection's size-1 leaves ARE the
    individual confirmations, so each reported site is a confirmed single-mutation
    flip, never assumed.  A .py file's sites are its DEFINITIONS (label
    `path::qualname`, body→raise); any other file is one whole-file site (label
    `path`, corrupted).  Monotonicity (a cleared group truly holds no flipper) is by
    construction — the uncatchable raise in _mutate_lines."""
    baseline = G.resolves(chk, sandbox_project, custom)
    if not baseline:
        return False, []
    if _RESOLUTION == "file":
        # coarse, fast: corrupt each whole file, label by path
        sens = []
        for f in sandbox_files(sandbox_project, set(), engine_dir):
            orig = f.read_bytes()
            f.write_bytes(CORRUPT)
            try:
                flipped = not G.resolves(chk, sandbox_project, custom)
            finally:
                f.write_bytes(orig)
            if flipped:
                sens.append(_rel(f, sandbox_project, engine_dir))
        return True, sorted(sens)
    sites = []   # (file, node | None, label) — node None ⇒ whole-file corruption
    for f in sandbox_files(sandbox_project, set(), engine_dir):
        label = _rel(f, sandbox_project, engine_dir)
        if f.suffix == ".py":
            for qn, node in _def_sites(f.read_text()):
                sites.append((f, node, f"{label}::{qn}"))
        else:
            sites.append((f, None, label))

    def apply(group) -> bool:
        saved: dict = {}
        pyfiles: dict = {}
        try:
            for f, node, _ in group:
                saved.setdefault(f, f.read_bytes())
                if node is not None:
                    pyfiles.setdefault(f, []).append(node)
            for f, nodes in pyfiles.items():
                f.write_text(_mutate_lines(saved[f].decode(), nodes))
            for f, node, _ in group:
                if node is None:
                    f.write_bytes(CORRUPT)
            return not G.resolves(chk, sandbox_project, custom)
        finally:
            for f, b in saved.items():
                f.write_bytes(b)

    flips: list[str] = []

    def split(group):
        if not group or not apply(group):
            return                       # cleared in one run: no flipper here
        if len(group) == 1:
            flips.append(group[0][2])    # a confirmed single-mutation flip
            return
        m = len(group) // 2
        split(group[:m])
        split(group[m:])

    split(sites)
    return True, sorted(flips)


def grade_check(chk: str, project_dir: Path, presupposed: set,
                custom: dict, sandbox_project: Path, engine_dir: Path | None = None) -> dict:
    typ, _, target = chk.partition(":")
    if typ == "result":
        # Ξ·seam: a verdict-import — adequacy DELEGATED to a separately-gated sibling.
        # NOT mutation-swept (that would re-run the sibling's whole gate per mutation,
        # the rm-status cost bomb); graded "imported" iff the sibling gates green now,
        # else "broken".  Sound because every imported sibling is itself behaviorally
        # gated in the hook — a project rests-on a sibling as a claim rests-on a premise.
        if G.resolves(chk, sandbox_project, custom):
            return {"grade": "imported", "tests": [target],
                    "why": f"adequacy delegated to sibling project '{target}', which gates "
                           "green and is itself behaviorally gated (composition, not re-derivation)",
                    "not_higher": "imported is a delegation, not a falsifiability tier — the "
                                  "sibling's own Δ pass is the behavioral guarantee",
                    "not_lower": "not broken: the imported sibling currently gates green"}
        return {"grade": "broken", "tests": [target],
                "why": f"verdict-import of sibling project '{target}' does not gate green",
                "not_higher": "to rise: make the imported sibling gate green",
                "not_lower": "—"}
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
    # cmd: / custom — Δ·det: determinism guard, then empirically probe falsifiability.
    # Δ assumes a check is a PURE FUNCTION of project content; a flaky check (wall-clock,
    # load, iteration order, the date, network) gets a single-sample grade that is noise.
    # PAPERKIT_DELTA_REPEAT=N (default 1, off) re-runs the pristine baseline N times; if
    # they disagree the check is PROVABLY non-deterministic, so the sweep would be noise.
    reps = max(1, int(os.environ.get("PAPERKIT_DELTA_REPEAT", "1")))
    if reps > 1 and len({G.resolves(chk, sandbox_project, custom) for _ in range(reps)}) > 1:
        return {"grade": "broken", "tests": [], "determinism": "flaky",
                "why": f"non-deterministic — {reps} baseline runs in a pristine sandbox disagreed; "
                       "the verdict is not a function of project content (wall-clock / load / "
                       "iteration order / network?), so a single-sample mutation sweep is noise",
                "not_higher": "to rise: make the check a pure function of project content, then Δ can grade it",
                "not_lower": "—"}
    baseline, sens = sensitivity(chk, sandbox_project, custom, engine_dir)
    rec = _grade_from_sens(baseline, sens)
    if rec["grade"] == "indeterminate":
        rec = _vacuity_source(rec, chk, sandbox_project, custom, engine_dir)
    return rec


def _vacuity_source(rec: dict, chk: str, sandbox_project: Path,
                    custom: dict, engine_dir: Path | None) -> dict:
    """Δ·vacuity-source — split the indeterminate verdict by the ALL-CORRUPTED probe.
    No SINGLE mutation flipped it; corrupt EVERY mutable input at once and look again.
    Still green ⇒ insensitive to all project content: it reads only external/live state,
    or asserts the absence of content no corruption supplies — Δ cannot falsify it, and
    the fix is to read a PROJECT input (the dataset-backed pattern) or a Π counter-fixture.
    Goes red ⇒ it does read project content, just not via any one file alone."""
    files = sandbox_files(sandbox_project, set(), engine_dir)
    saved = {f: f.read_bytes() for f in files}
    try:
        for f in files:
            f.write_bytes(CORRUPT)
        still_green = G.resolves(chk, sandbox_project, custom)
    finally:
        for f, b in saved.items():
            f.write_bytes(b)
    if still_green:
        return {**rec, "vacuity": "total",
                "why": "corrupting EVERY project input AT ONCE leaves it green — it is blind to all "
                       "project content: it reads only external/live state, or asserts the absence "
                       "of content no corruption supplies; Δ cannot falsify it by mutation",
                "not_higher": "to rise: read a PROJECT input a mutation can corrupt (a captured "
                              "dataset — the dataset-backed pattern), or supply a Π counter-fixture "
                              "(only the latter helps a negative assertion; an external read needs the former)"}
    return {**rec, "vacuity": "combination",
            "why": "no single input flips it, but corrupting all of them at once does — it depends "
                   "on project content in concert, not on any one file",
            "not_higher": "to rise: a Π counter-fixture isolating the responsible inputs proves it behavioral",
            "not_lower": "not external: corrupting all inputs DOES flip it, so it reads project content"}


def _grade_from_sens(baseline: bool, sens: list) -> dict:
    """The cmd/custom verdict as a pure function of (baseline-passes, flip-set) — shared
    by the per-check path (grade_check → sensitivity) and the flat work-queue grader."""
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
        # the engine in the sandbox copy — included in the mutation surface (def
        # resolution only) so the witnesses are sensitive to the engine they test, not
        # only to their own script.  At file resolution the engine would only add the
        # import-crash flood (one collapsed signature), so it is left out.
        engine = ((tmp / root.name / _ENGINE.relative_to(root))
                  if _RESOLUTION == "def" and _ENGINE.is_relative_to(root) else None)
        return grade_check(chk, project_dir, presupposed, custom, sandbox, engine)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _grade_parallel(project_dir, checks, custom, presupposed):
    """Grade every distinct check CONCURRENTLY — each is an independent target with
    its own sandbox, so the sweep's wall-clock is the slowest single check, not their
    sum.  Bounded at cpu_count (a heavy check may itself fan out a nested gate).

    Δ·pulse: emit a progress heartbeat to stderr as checks complete, so a slow grade
    (a cold sweep paging through swap) reads as LIVE, never stalled — the batch path's
    answer to the liveness the resumable pump has by construction.  \\r-updates a tty;
    throttled newline pulses to a log/pipe; PAPERKIT_DELTA_PULSE=0 silences it."""
    jobs = max(1, min(len(checks), os.cpu_count() or 4))
    total, done, lock, t0 = len(checks), [0], threading.Lock(), time.monotonic()
    tty = sys.stderr.isatty()
    every = float(os.environ.get("PAPERKIT_DELTA_PULSE", "2"))   # min seconds between log pulses; 0 = off
    last = [t0]

    def pulse_grade(c):
        r = _grade_one(project_dir, c, custom, presupposed)
        with lock:
            done[0] += 1
            now = time.monotonic()
            if not every:
                return r
            if tty:
                print(f"paperkit-discriminate: graded {done[0]}/{total} ({now - t0:.0f}s)",
                      end="\r", file=sys.stderr, flush=True)
            elif now - last[0] >= every or done[0] == total:
                last[0] = now
                print(f"paperkit-discriminate: graded {done[0]}/{total} ({now - t0:.0f}s)",
                      file=sys.stderr, flush=True)
        return r

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        graded = list(ex.map(pulse_grade, checks))
    if tty and every:
        print(file=sys.stderr)                                  # close the \r-updated line
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

    global _RESOLUTION
    _RESOLUTION = optval("--resolution") or "file"
    if _RESOLUTION not in ("file", "def"):
        sys.exit("paperkit-discriminate: --resolution must be 'file' or 'def'")

    consumed = {x for x in (min_strength, state_file, budget_str, optval("--resolution"))
                if x is not None}
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

    if "--footprint" in flags:
        # Φ·footprint: each considered check's READ footprint (the project files it opens),
        # the SOUND per-check key a footprint cache invalidates on — a diff touching none of
        # a check's footprint cannot change its verdict.  Reads ⊇ Δ's sensitivity `tests`.
        print(json.dumps({c: G.footprint(c, project_dir, custom) for c in sorted(share)}, indent=2))
        return 0

    # Δ·footprint-cache: a Δ grade is a pure function of its inputs, so cache it PER CHECK,
    # keyed on the content of the files it actually READS (Φ·footprint) plus the engine
    # EPOCH (_engine_hash).  A commit then re-grades only the checks whose footprint the diff
    # touched — where the old whole-project content_key cache invalidated EVERY check on any
    # edit.  Reuse a check while its footprint files (and the engine) are unchanged.
    no_cache = "--no-cache" in flags
    engine = _engine_hash()
    cached = {} if no_cache else _load_cache(project_dir)
    valid = cached.get("engine") == engine and cached.get("resolution") == _RESOLUTION
    entries = cached.get("checks", {}) if valid else {}

    reuse, stale = {}, []
    for c in share:
        e = entries.get(c)
        if e and _footprint_hash(project_dir, e["footprint"]) == e["fp"]:
            reuse[c] = e
        else:
            stale.append(c)

    fresh, fresh_grader = {}, None
    if stale and state_file is None and budget_str is None:
        # Batch grade — the default.  Test the RAW flag (budget_str): an absent --budget
        # coerces to 0.0 ("run to done"), so `budget is None` would never hold and would
        # leave this path dead (the Σ·flat·gate guard-fix).  Only the STALE checks are swept.
        fresh_grader = "_grade_parallel"
        fresh = _grade_parallel(project_dir, stale, custom, presupposed)
    elif stale:
        # Resumable path: grade the stale checks as a pump-witness under an optional budget
        # (--state/--budget make a long grade resume across short calls — pump-ask liveness).
        witness = GradeWitness(project_dir, stale, custom, presupposed)
        meaning, steps, done = D.drive(witness, state_path=state_file, budget=budget)
        if not done:
            print(f"paperkit-discriminate: graded {meaning['progress']} in {steps} increment(s) — "
                  f"not done; state persisted to {state_file}, re-run to resume", file=sys.stderr)
            return 2
        fresh = meaning["graded"]
        fresh_grader = "GradeWitness"

    # assemble grades + a PER-CHECK grader, and refresh the cache entry of each graded check
    # with its fresh footprint (Σ·flat·witness: a reused grade reports grader "cache").
    graded, grader_of, new_entries = {}, {}, dict(reuse)
    for c, e in reuse.items():
        graded[c], grader_of[c] = e["grade"], "cache"
    for c in stale:
        fp = G.footprint(c, project_dir, custom)
        graded[c], grader_of[c] = fresh[c], fresh_grader
        new_entries[c] = {"grade": fresh[c], "footprint": fp, "fp": _footprint_hash(project_dir, fp)}

    if not no_cache:
        _save_cache(project_dir, {"engine": engine, "resolution": _RESOLUTION, "checks": new_entries})

    if stale:
        print(f"paperkit-discriminate: graded by {fresh_grader} "
              f"({len(stale)} graded, {len(reuse)} reused from footprint cache)", file=sys.stderr)
    else:
        print(f"paperkit-discriminate: all {len(reuse)} grade(s) reused from footprint cache", file=sys.stderr)
    records = []
    for k in keys:
        chk = F[k]["check"]
        g = dict(graded[chk])
        g.update(key=k, check=chk, cited=k in cited, section=F[k].get("section"),
                 shared_with=[o for o in share[chk] if o != k])
        g["from"] = F[k].get("from", [])
        g["rests-on"] = F[k].get("rests-on", [])     # grounding edges (for clamping)
        g["grader"] = grader_of[chk]
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
    order = {"broken": 0, "vacuous": 1, "indeterminate": 2, "existence": 3,
             "behavioral": 4, "imported": 5}
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
