#!/usr/bin/env python3
"""The Δ GRADER — the mutation sweep that assigns each check a falsifiability grade, and
the grade ladder it places them on.  Factored out of the CLI so the sweep can be imported
and tested on its own: it depends only on the resolver (to run a check) and layout (project
topology), never on the cache, the CLI, or the projector.

The mutation RESOLUTION (granularity) is THREADED as a parameter, not a module global:
  "file"  whole-file corruption, project surface only — fast, coarse, the gate's pass/fail
          falsifiability question (the default, the pre-commit hook).  engine_dir is None.
  "def"   definition-resolution group testing over project + ENGINE — the precise per-claim
          capability fingerprint that closes ∂²'s sensitivity face, ~an order costlier (the
          on-demand coherence pass).  engine_dir is the sandboxed engine.
A function downstream of _grade_one needs no resolution string: engine_dir IS the mode
(None ⇒ file, a path ⇒ def), so the sweep branches on it.
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
from pathlib import Path

import config

import resolver
from layout import SKIP_DIRS, _ENGINE, _sandbox_root, _copy_sandbox, _nested_roots, _mutable

CORRUPT = b"\x00\x00DELTA-CORRUPTION\x00\x00\n"

STRENGTH = {"vacuous": 0, "existence": 1, "indeterminate": 1, "behavioral": 2, "imported": 3}
ORDER = {"existence": 1, "behavioral": 2}  # valid --min-strength thresholds

# Total order for clamping (effective grade = min over self + premises).  Conservative:
# vacuous < indeterminate (runs, falsifiability unproven) < existence (presence proven)
# < behavioral (falsifiability proven) < imported (Ξ·seam: verified whole in a separately-
# gated sibling — a delegated premise never weakens what rests on it, so it ranks at top).
RANK_C = {"broken": -1, "vacuous": 0, "indeterminate": 1, "existence": 2, "behavioral": 3,
          "imported": 4}
GRADE_C = {v: k for k, v in RANK_C.items()}

# Corroboration — a SECOND, ORTHOGONAL evidence axis (Ε·agree·grade), NOT another rung on
# RANK_C above.  The grade above asks "does a mutation flip this check" (FALSIFIABILITY);
# this asks "is the verdict confirmed by INDEPENDENT producers" (CORROBORATION).  A check's
# strength is the PAIR (falsifiability, corroboration), never one collapsed scalar: a lone
# behavioral witness and a behaviorally-agreeing oracle share a GRADE but differ HERE.  An
# agree: verdict that passes with ≥2 textually-distinct producers is `independent`; one
# witness — or identical producers concurring trivially — is `single`.  single < independent.
CORRO_C = {"single": 0, "independent": 1}


def presupposed_inputs(project_dir: Path, cfg: dict) -> set:
    """Resolved paths whose existence the build already presupposes — a file:
    check naming one of these is redundant with the project being runnable, so
    it is provably vacuous.  The declared bibs / rubric / config / output, plus
    the engine scripts the checks invoke via ../paperkit."""
    req = set(cfg["bibs"]) | {cfg["rubric"], cfg["out"], project_dir / "paper.toml"}
    req |= set(_ENGINE.glob("*.py"))
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
                engine_dir: Path | None = None, footprint: list | None = None) -> tuple[bool, list]:
    """The sensitivity set — the mutations that flip chk red — found by BINARY-SPLIT
    GROUP TESTING, not a linear scan over every site.  Mutate a whole group of sites
    at once: if it does NOT flip, the entire group is proven clear in ONE run (the
    sparse non-flippers cost nothing); if it flips, bisect.  O(k·log n) runs for k
    flips, against O(n) for the scan — and the bisection's size-1 leaves ARE the
    individual confirmations, so each reported site is a confirmed single-mutation
    flip, never assumed.  A .py file's sites are its DEFINITIONS (label
    `path::qualname`, body→raise); any other file is one whole-file site (label
    `path`, corrupted).  Monotonicity (a cleared group truly holds no flipper) is by
    construction — the uncatchable raise in _mutate_lines.  engine_dir is None ⇒ file
    resolution (the whole-file scan); a path ⇒ def resolution over project + engine."""
    baseline = resolver.resolves(chk, sandbox_project, custom)
    if not baseline:
        return False, []
    if engine_dir is None:
        # file resolution — corrupt each whole file, label by path.  Ξ·depth·explain: scope
        # the scan to the check's READ footprint (Φ — the files it actually opens) when one
        # is given.  A file the check never reads cannot flip it (sensitivity ⊆ footprint),
        # so a project is graded against what each check TOUCHES, not the whole repo — the
        # engine appears only in the surface of the checks that read it.
        files = sandbox_files(sandbox_project, set(), engine_dir)

        def scan(fs):
            hits = []
            for f in fs:
                orig = f.read_bytes()
                f.write_bytes(CORRUPT)
                try:
                    flipped = not resolver.resolves(chk, sandbox_project, custom)
                finally:
                    f.write_bytes(orig)
                if flipped:
                    hits.append(_rel(f, sandbox_project, engine_dir))
            return hits

        if footprint is None:
            return True, sorted(scan(files))
        fp = set(footprint)
        scoped = [f for f in files if str(f.relative_to(sandbox_project)) in fp]
        sens = scan(scoped)
        if not sens and len(scoped) < len(files):
            # the scoped scan found nothing — scan the rest too, in case the (best-effort)
            # read footprint under-reported; a real flip there means behavioral, not vacuous.
            sens = scan([f for f in files if f not in set(scoped)])
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
            return not resolver.resolves(chk, sandbox_project, custom)
        finally:
            for f, b in saved.items():
                f.write_bytes(b)

    def run(group) -> list:
        flips: list[str] = []

        def split(g):
            if not g or not apply(g):
                return                   # cleared in one run: no flipper here
            if len(g) == 1:
                flips.append(g[0][2])    # a confirmed single-mutation flip
                return
            m = len(g) // 2
            split(g[:m])
            split(g[m:])

        split(group)
        return sorted(flips)

    # Δ·scope — restrict the def sweep to sites in files the check actually READS (its Φ footprint,
    # root-relative so engine reads count): sensitivity ⊆ footprint, so a def in a file the check
    # never opens cannot flip it.  This is what makes the def sweep affordable — mutate only the
    # engine the claim exercises, not the whole engine.  Mirrors the file-resolution scoping above;
    # same under-report guard (sweep the rest iff the scoped sweep finds nothing); Φ·degrade
    # (footprint None) sweeps the full surface.
    if footprint is None:
        return True, run(sites)
    root_copy = engine_dir.parent
    fp = set(footprint)
    scoped = [s for s in sites if str(s[0].relative_to(root_copy)) in fp]
    flips = run(scoped)
    if not flips and len(scoped) < len(sites):
        keep = {s[2] for s in scoped}
        flips = run([s for s in sites if s[2] not in keep])
    return True, flips


def grade_check(chk: str, project_dir: Path, presupposed: set, custom: dict,
                sandbox_project: Path, engine_dir: Path | None = None,
                footprint: list | None = None) -> dict:
    typ, _, target = chk.partition(":")
    if typ == "result":
        # Ξ·result-imported: a verdict-import is adequacy DELEGATED to a separately-gated sibling.
        # Graded "imported" BY DELEGATION — WITHOUT running the sibling's gate.  Re-running it would
        # both re-derive the sibling per mutation (the rm-status cost bomb) AND drag the sibling's
        # whole transitive footprint into this sandbox.  Sound by COMPOSITION: the sibling carries
        # its own gate AND Δ in //:hook, and the GATE (not Δ) resolves result: live — so a broken or
        # bogus sibling fails THERE.  The falsifiability tier need not, and does not, re-verify it.
        return {"grade": "imported", "tests": [target],
                "why": f"adequacy delegated to the separately-gated sibling project '{target}' "
                       "(composition, not re-derivation — its own gate + Δ are the guarantee)",
                "not_higher": "imported is a delegation, not a falsifiability tier",
                "not_lower": "the sibling is gated independently in the hook; the gate, not Δ, "
                             "resolves the import live, so a broken sibling fails there"}
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
    reps = max(1, int(config.resolve(config.DELTA_REPEAT)))
    if reps > 1 and len({resolver.resolves(chk, sandbox_project, custom) for _ in range(reps)}) > 1:
        return {"grade": "broken", "tests": [], "determinism": "flaky",
                "why": f"non-deterministic — {reps} baseline runs in a pristine sandbox disagreed; "
                       "the verdict is not a function of project content (wall-clock / load / "
                       "iteration order / network?), so a single-sample mutation sweep is noise",
                "not_higher": "to rise: make the check a pure function of project content, then Δ can grade it",
                "not_lower": "—"}
    baseline, sens = sensitivity(chk, sandbox_project, custom, engine_dir, footprint)
    rec = _grade_from_sens(baseline, sens)
    rec["baseline"] = baseline   # Ζ·calc — the measured baseline (the verdict), part of the CALCULATION
    if rec["grade"] == "indeterminate":
        rec = _vacuity_source(rec, chk, sandbox_project, custom, engine_dir)
    # Ε·agree·grade — the corroboration AXIS, orthogonal to the falsifiability grade above:
    # an agree: verdict that PASSES with ≥2 TEXTUALLY DISTINCT producers is corroborated by
    # independent means (a shared bug a lone witness carries is ruled out) — a stronger FACT,
    # not a higher rank.  Identical producers concur trivially (single).  Only agree: carries
    # the field; its absence reads as single (one witness).
    if typ == "agree" and rec["grade"] != "broken":
        producers = [p.strip() for p in target.split("|||") if p.strip()]
        rec["corroboration"] = "independent" if len(set(producers)) >= 2 else "single"
        rec["producers"] = len(producers)
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
        still_green = resolver.resolves(chk, sandbox_project, custom)
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


def _grade_one(project_dir, chk, custom, presupposed, resolution="file"):
    """Grade one check in its own fresh sandbox copy (so concurrent grades never
    share a mutation).  The copy is the bounded universe of the project + engine.
    `resolution` ("file"|"def") decides whether the engine joins the mutation surface."""
    tmp = Path(tempfile.mkdtemp(prefix="paperkit-delta-"))
    try:
        root = _sandbox_root(project_dir)
        _copy_sandbox(root, tmp / root.name)
        rel = project_dir.relative_to(root)
        sandbox = tmp / root.name if rel == Path(".") else tmp / root.name / rel
        # the engine in the sandbox copy — included in the mutation surface (def
        # resolution only) so the witnesses are sensitive to the engine they test, not
        # only to their own script.  At file resolution the engine would only add the
        # import-crash flood (one collapsed signature), so it is left out.  Locate it by
        # its position UNDER root: directly when _ENGINE lives inside root (a self-contained
        # repo), else by name — the Bazel case, where _ENGINE.resolve() follows the staged
        # symlink OUT to the source tree so is_relative_to(root) is false, though the engine
        # IS copied into the sandbox at root/<name>.  Guard on the copy existing, so a
        # Ν·loud — fail rather than silently degrade if the engine copy is missing (below).
        engine = None
        if resolution == "def":
            eng_rel = _ENGINE.relative_to(root) if _ENGINE.is_relative_to(root) else Path(_ENGINE.name)
            engine = tmp / root.name / eng_rel
            if not engine.is_dir():
                # Ν·loud — a def sweep with no engine in the mutation surface measures NOTHING
                # (an empty fingerprint), and that once shipped a green-for-nothing emergence gate
                # (the Bazel-symlink degeneracy).  Refuse to degrade to file resolution: FAIL, so
                # the silence becomes a loud build error instead of a vacuous record.
                raise RuntimeError(
                    f"Ν·loud: def-resolution sweep cannot find the engine in the sandbox "
                    f"(expected a directory at {engine}, under the copied root {root}); refusing "
                    f"to silently degrade to file resolution and emit a vacuous fingerprint.")
        # the check's READ footprint (strace).  Δ·scope: a def sweep is bounded to the files the
        # check actually reads (sensitivity ⊆ footprint) — so it mutates only the engine the claim
        # exercises, not the whole engine.  For that the trace must see ENGINE reads, so a def grade
        # traces ONCE at ROOT scope ("paperkit/x.py", "<proj>/checks/y.py").  The cache key stays
        # PROJECT-scoped, DERIVED from the same trace (no second strace): keep this project's
        # entries, project-relative; engine entries aren't project inputs (the engine-epoch hash
        # covers them).  File resolution traces project-scoped directly.
        if engine:
            root_copy = tmp / root.name
            sweep_fp = resolver.footprint(chk, sandbox, custom, scope=root_copy)
            if sweep_fp is None:
                fp = None
            elif sandbox == root_copy:
                fp = sweep_fp                                    # the root project: its scope IS root
            else:
                pre = str(sandbox.relative_to(root_copy)) + "/"
                fp = sorted(p[len(pre):] for p in sweep_fp if p.startswith(pre))
        else:
            fp = sweep_fp = resolver.footprint(chk, sandbox, custom)
        rec = grade_check(chk, project_dir, presupposed, custom, sandbox, engine, sweep_fp)
        rec["_footprint"] = fp
        return rec
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _grade_parallel(project_dir, checks, custom, presupposed, resolution="file"):
    """Grade every distinct check CONCURRENTLY — each is an independent target with
    its own sandbox, so the sweep's wall-clock is the slowest single check, not their
    sum.  Bounded at cpu_count (a heavy check may itself fan out a nested gate).

    Δ·pulse: emit a progress heartbeat to stderr as checks complete, so a slow grade
    (a cold sweep paging through swap) reads as LIVE, never stalled — the batch path's
    answer to the liveness the resumable pump has by construction.  \\r-updates a tty;
    throttled newline pulses to a log/pipe; PAPERKIT_DELTA_PULSE=0 silences it."""
    from concurrent.futures import ThreadPoolExecutor
    jobs = max(1, min(len(checks), os.cpu_count() or 4))
    total, done, lock, t0 = len(checks), [0], threading.Lock(), time.monotonic()
    tty = sys.stderr.isatty()
    every = float(config.resolve(config.DELTA_PULSE))   # min seconds between log pulses; 0 = off
    last = [t0]

    def pulse_grade(c):
        r = _grade_one(project_dir, c, custom, presupposed, resolution)
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

    def __init__(self, project_dir, checks, custom, presupposed, resolution="file"):
        self.project_dir, self.checks = project_dir, checks
        self.custom, self.presupposed = custom, presupposed
        self.resolution = resolution

    def initial(self):
        return {"cursor": 0, "graded": {}}

    def pump(self, state):
        i = state["cursor"]
        if i >= len(self.checks):
            return state
        chk = self.checks[i]
        g = _grade_one(self.project_dir, chk, self.custom, self.presupposed, self.resolution)
        return {"cursor": i + 1, "graded": {**state["graded"], chk: g}}

    def parse(self, state):
        return {"done": state["cursor"] >= len(self.checks), "graded": state["graded"],
                "progress": f'{state["cursor"]}/{len(self.checks)}'}

    def serialize(self, state):
        return json.dumps(state, sort_keys=True)

    def deserialize(self, s):
        return json.loads(s)
