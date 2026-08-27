#!/usr/bin/env python3
"""The Δ GRADER — the mutation SWEEP that assigns each check a falsifiability grade by
placing it on the grade ladder (the rungs + pure interpretation now live in grade.py —
Μ·grade: this module is the CALCULATION, that one the interpretation).  Factored out of the
CLI so the sweep can be imported and tested on its own: it depends only on the resolver (to
run a check), layout (project topology), and grade (the ladder) — never on the cache, the
CLI, or the projector.

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

import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import NamedTuple

import config

import resolver
from layout import SKIP_DIRS, _ENGINE, _sandbox_root, _copy_sandbox, _nested_roots, _mutable
from mutate import (  # Ζ·mutant / Μ·sweep·atom — the pure AST mutation primitives (their own leaf)
    _def_sites, _mutate_lines, _branch_sites, _flip_sites, _flip_condition,
    _data_sites, emit_mutant, _drop_data_multi)
from grade import _grade_from_sens


class _Unreachable(int):
    """Falsy like False — every `if not baseline` still holds — but distinguishable, so the
    ONE caller that builds a grade record can say WHY nothing was established."""
    def __new__(cls):
        return super().__new__(cls, 0)
    def __repr__(self):
        return "UNREACHABLE"


UNREACHABLE = _Unreachable()  # Μ·grade — the pure ladder/interpretation (the rungs + clamp
# orders STRENGTH/ORDER/RANK_C/GRADE_C/CORRO_C live in grade.py now; the SWEEP below is the
# calculation, that module the interpretation — Ζ·calc·interp in code).

CORRUPT = b"\x00\x00DELTA-CORRUPTION\x00\x00\n"

# Ω·config — the knobs this module RESOLVES, declared here (place-by-ownership; the kernel
# hosts the mechanism only).
DELTA_REPEAT = config.Param("delta-repeat", "PAPERKIT_DELTA_REPEAT", default="1",
                            help="re-run the pristine baseline N times to detect a flaky (non-deterministic) check")
DELTA_PULSE = config.Param("delta-pulse", "PAPERKIT_DELTA_PULSE", default="2",
                           help="min seconds between Δ progress pulses to a log (0 = silent)")


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


def surface_of(footprint: list | None, sandbox_project: Path, root_copy: Path | None,
               engine_dir: Path | None = None) -> list:
    """Ζ·surface — the candidate files a claim's falsifiability is measured against: its SUBJECT,
    CONSTRUCTED from the check's root-scoped read footprint.

    The footprint used only to FILTER a hardcoded candidate set (the project tree, plus the engine
    iff resolution was "def").  Intersection cannot introduce what the left operand lacks, so a
    claim ABOUT another tree could never be sensitive to it however precisely it was traced: an
    engine-claim filed in `boundaries` graded `indeterminate` not because it was unfalsifiable but
    because the engine was not a candidate.  Here the footprint CONSTRUCTS the set instead.

    This also unwelds two axes `resolution` had fused: GRANULARITY (whole-file corruption vs
    def-body mutation — a cost/precision knob) and ROOT SCOPE (which trees are candidates — a
    property of the CLAIM).  Scope is decided here, from the subject; granularity stays a knob.

    Φ·degrade: no footprint (strace absent/blocked) falls back to the flat tree — over-sweeping is
    the safe direction, and the caller's under-report guard still covers a partial trace."""
    if footprint is None:
        return sandbox_files(sandbox_project, set(), engine_dir)
    base = root_copy or sandbox_project
    named = {(base / p).resolve() for p in footprint}
    out, seen = [], set()
    for f in sorted(base.rglob("*")):
        if not _mutable(f) or any(part in SKIP_DIRS for part in f.parts):
            continue
        if f.suffix == ".sh" and "checks" in f.parts:
            continue                      # a verifier script; its corruption tests itself
        r = f.resolve()
        if r in named and r not in seen:
            seen.add(r)
            out.append(f)
    return out


def unmeasured_reads(footprint: list | None, root_copy: Path | None) -> list:
    """Ζ·surface·kind — the files a claim READS that the sweep cannot MUTATE.

    A grade is only as complete as the surface it was measured over, and `indeterminate` was
    carrying two incompatible meanings: "every input was corrupted and none flipped it" (a real
    falsifiability verdict) and "an input this claim depends on was never corrupted at all" (no
    verdict — we did not look).  The second is the sentinel move one level down: *not measurable
    from here* is not *not falsifiable*, exactly as *no such claim* is not *broken*.

    Three independently-found cases turn out to be ONE set difference, `reads \\ mutable`:
      · `setup/reference.json` — read, but `.json` is not a MUTABLE_SUFFIX, so corrupting the
        DATA was impossible and the claims were behavioral only by crashing the INTERPRETER,
        while the project's own prose asserted the opposite (a downstream consumer's finding);
      · `tools/grade.bzl` — read by bnd-ladder, which ASSERTS things about it, but `.bzl` is not
        a mutable suffix either, so that assertion cannot be falsified (found by this function,
        in a check written the day before);
      · a check invoking a tool OUTSIDE the project entirely (a downstream consumer's
        `../scripts/check`) — read, unreachable by any mutation of the project.
    Whether the file is excluded by SUFFIX or by LOCATION, the epistemic position is identical.

    This is an ORTHOGONAL AXIS, never a rung — the same shape as content_sensitive and
    corroboration.  A grade says how falsifiable a claim is; this says how much of the claim the
    grade actually looked at.  Derived artifacts are excluded via SKIP_DIRS (a __pycache__/*.pyc
    is a build product of a .py that IS in the surface — its source is measured, so it is not a
    gap; see the pyc-is-a-build-artifact reading)."""
    if footprint is None or root_copy is None:
        return []                                     # Φ·degrade: no trace ⇒ no claim either way
    out = []
    for p in footprint:
        f = root_copy / p
        if any(part in SKIP_DIRS for part in Path(p).parts):
            continue                                  # a derived artifact; its SOURCE is measured
        if f.is_file() and not _mutable(f):
            out.append(p)
    return sorted(out)


def _rel(f: Path, sandbox_project: Path, engine_dir: Path | None,
         root_copy: Path | None = None) -> str:
    """Label a corrupted file: relative to the project, or tagged engine/<…> when it is the engine
    (outside the project, e.g. the paper's ../paperkit).  Ζ·surface: a constructed surface can also
    name a THIRD tree (a claim about a sibling's content), labelled root-relative — the engine's own
    label is left byte-identical so existing fingerprints do not move."""
    try:
        return str(f.relative_to(sandbox_project))
    except ValueError:
        pass
    if engine_dir is not None:
        try:
            return f"{engine_dir.name}/{f.relative_to(engine_dir)}"
        except ValueError:
            pass
    return str(f.relative_to(root_copy)) if root_copy else str(f)


# Ζ·mutant — _def_sites / _mutate_lines (the pure AST mutation primitives) now live in their own leaf
# (paperkit/mutate.py, imported at the top), so the Bazel-orchestrated mutant graph builds on them
# without importing this sweep machinery.  The sensitivity INTERPRETATION (group-testing, the
# capability fingerprint) stays here.


class _BranchNode:
    """Μ·sweep·atom — a branch ARM presented to _mutate_lines with the same interface a def node
    has (`.body[0].lineno`, `.end_lineno`, `.body[0].col_offset`), so the arm's body line-span is
    replaced by the SAME uncatchable raise as a def body — zero change to _mutate_lines, and a
    branch: site is a raise-kind site indistinguishable from def: at the mutation atom.  It IS
    monotone (the same primitive) and ADDITIVE (a NEW label, appended beside its def: site)."""
    __slots__ = ("body", "end_lineno")

    def __init__(self, first, last):
        self.body = [first]
        self.end_lineno = last.end_lineno


class _DataNode:
    """Μ·sweep·atom — a module-level DATA DROP (data-:<qn>#<n>) presented to the sweep.  Unlike a def/
    branch node it is NOT a body line-span _mutate_lines can replace — it rewrites a dict/list literal
    in place — so it carries its mutate.py SPEC and renders via emit_mutant.  data-: IS monotone (a
    reader flips when the key is gone), so it belongs in _sites beside def:/branch: and the sweep
    consumes it uniformly; _apply renders a data node by applying its spec to the (possibly already
    def/branch-mutated) file text.  dflip: is NOT here — it is the non-monotone DflipSite the sweep
    cannot receive (the structural bar), like flip:."""
    __slots__ = ("spec",)

    def __init__(self, qualname, n):
        self.spec = f"data-:{qualname}#{n}"


def _sites(sandbox_project: Path, engine_dir: Path | None, files: list | None = None,
           root_copy: Path | None = None) -> list:
    """Every def-resolution mutation SITE as (file, node | None, label): a .py file's
    DEFINITIONS (label `path::qualname`, body→uncatchable-raise) and any other file as one
    whole-file site (label `path`, corrupted).  The unit set the group-testing sweep bisects
    AND the single-site probe (flip_one) selects from — shared so both label sites identically
    (a per-site Bazel action and the in-process sweep agree by construction).

    Μ·sweep·atom — ADDITIVELY appends per-branch-arm sites (label `path::branch:<qn>#<n>`, the
    arm body → the same raise): a finer, still-monotone reach probe that never REPLACES the def:
    site, so the coarse behavioral grade and the def: cache cell both survive beside it.  flip:
    is NOT here — it is a distinct, non-monotone site type (a FlipSite) the sensitivity sweep is
    structurally unable to consume; see _flip_sites_of."""
    sites = []
    for f in (sandbox_files(sandbox_project, set(), engine_dir) if files is None else files):
        label = _rel(f, sandbox_project, engine_dir, root_copy)
        if f.suffix == ".py":
            text = f.read_text()
            for qn, node in _def_sites(text):
                sites.append((f, node, f"{label}::{qn}"))
            for qn, n, (b0, blast) in _branch_sites(text):
                sites.append((f, _BranchNode(b0, blast), f"{label}::branch:{qn}#{n}"))
            for qn, n, _kind, _k, _v in _data_sites(text):
                sites.append((f, _DataNode(qn, n), f"{label}::data-:{qn}#{n}"))
        else:
            sites.append((f, None, label))
    return sites


def _apply(chk: str, sandbox_project: Path, custom: dict, group: list) -> bool:
    """Mutate one GROUP of sites at once (def bodies → uncatchable raise; whole files → CORRUPT),
    run the check, restore.  True iff the mutation flips chk red.  The atom shared by the
    group-testing sweep (sensitivity) and the single-site probe (flip_one)."""
    saved: dict = {}
    linenodes: dict = {}   # def/branch nodes → _mutate_lines (body-span → raise)
    dataspecs: dict = {}   # Μ·sweep·atom — _DataNode specs → emit_mutant (literal rewrite)
    try:
        for f, node, _ in group:
            saved.setdefault(f, f.read_bytes())
            if isinstance(node, _DataNode):
                dataspecs.setdefault(f, []).append(node.spec)
            elif node is not None:
                linenodes.setdefault(f, []).append(node)
        for f in set(list(linenodes) + list(dataspecs)):
            text = saved[f].decode()
            if f in linenodes:
                text = _mutate_lines(text, linenodes[f])   # def/branch body-drops (line-span)
            if f in dataspecs:
                # Μ·sweep·atom — resolve every data-: DROP's (qualname, index) against the CURRENT
                # text ONCE and remove them per-literal in a single index-stable rebuild.  A sequential
                # spec-by-spec drop renumbers a literal as it goes, so a later index of the same literal
                # can vanish; drop_data_multi removes a whole index-SET at once, composition-safe.
                text = _drop_data_multi(text, dataspecs[f])
            f.write_text(text)
        for f, node, _ in group:
            if node is None:
                f.write_bytes(CORRUPT)
        return not resolver.resolves(chk, sandbox_project, custom).passed
    finally:
        for f, b in saved.items():
            f.write_bytes(b)


def sensitivity(chk: str, sandbox_project: Path, custom: dict,
                engine_dir: Path | None = None, footprint: list | None = None,
                root_copy: Path | None = None) -> tuple[bool, list]:
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
    # Ζ·broken·offaxis — read the VERDICT, not `.passed`.  `.passed` is a bool and the resolver
    # is tristate: an UNAVAILABLE ("I could not REACH the thing") and a FAIL ("the claim is
    # false") both collapse to False here, and the grade record downstream then said "repo is
    # not green" about a check that merely could not run.  Measured: exactly that, twice, on a
    # green repo whose cells were being killed by their memory cap.
    _v = resolver.resolves(chk, sandbox_project, custom)
    if not _v.passed:
        return (UNREACHABLE if _v.is_unavailable() else False), []
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
                    flipped = not resolver.resolves(chk, sandbox_project, custom).passed
                finally:
                    f.write_bytes(orig)
                if flipped:
                    hits.append(_rel(f, sandbox_project, engine_dir, root_copy))
            return hits

        if footprint is None:
            return True, sorted(scan(files))
        # Ζ·surface — CONSTRUCT the candidate set from the subject rather than intersecting the
        # project tree with it.  `files` stays only as the under-report guard's remainder.
        scoped = surface_of(footprint, sandbox_project, root_copy, engine_dir)
        sens = scan(scoped)
        if not sens and set(scoped) != set(files):
            # the scoped scan found nothing — scan the rest too, in case the (best-effort)
            # read footprint under-reported; a real flip there means behavioral, not vacuous.
            sens = scan([f for f in files if f not in set(scoped)])
        return True, sorted(sens)
    sites = _sites(sandbox_project, engine_dir)   # (file, node | None, label)

    def apply(group) -> bool:
        return _apply(chk, sandbox_project, custom, group)

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
    root = root_copy or engine_dir.parent
    # Ζ·surface — same construction at def granularity: the subject decides the ROOTS, the
    # granularity knob decides that each candidate contributes its def-sites rather than one
    # whole-file site.  The two axes are now set independently.
    scoped = _sites(sandbox_project, engine_dir,
                    surface_of(footprint, sandbox_project, root, engine_dir), root)
    flips = run(scoped)
    if not flips and len(scoped) < len(sites):
        keep = {s[2] for s in scoped}
        flips = run([s for s in sites if s[2] not in keep])
    return True, flips


def flip_one(chk: str, sandbox_project: Path, custom: dict,
             engine_dir: Path | None, site_label: str) -> bool:
    """Ζ·mutant — the SINGLE-SITE probe: does mutating exactly `site_label` flip chk red?
    The atomic unit the in-process group-testing sweep is built from, exposed so BAZEL can own
    the fanout — one pk_mutant action per (claim, site) — instead of an adaptive in-process
    bisection.  Selects the site from the SAME _sites list the sweep group-tests, then _apply,
    so a per-site action and the sweep agree by construction.  Ν·loud if the label is not a site
    in the surface (a stale/garbled mutant), rather than silently reporting no-flip."""
    for s in _sites(sandbox_project, engine_dir):
        if s[2] == site_label:
            return _apply(chk, sandbox_project, custom, [s])
    raise RuntimeError(f"Ν·loud: site '{site_label}' is not in the mutation surface")


def grade_check(chk: str, project_dir: Path, presupposed: set, custom: dict,
                sandbox_project: Path, engine_dir: Path | None = None,
                footprint: list | None = None, root_copy: Path | None = None) -> dict:
    typ, _, target = chk.partition(":")
    if typ == "result":
        # Ξ·result-imported: a verdict-import is adequacy DELEGATED to a separately-gated sibling.
        # Graded "imported" BY DELEGATION — WITHOUT running the sibling's gate.  Re-running it would
        # both re-derive the sibling per mutation (the rm-status cost bomb) AND drag the sibling's
        # whole transitive footprint into this sandbox.  Sound by COMPOSITION: the sibling carries
        # its own gate AND Δ in //:hook, and the GATE (not Δ) resolves result: live — so a broken or
        # bogus sibling fails THERE.  The falsifiability tier need not, and does not, re-verify it.
        sproj, _, sclaim = target.partition("#")
        return {"grade": "imported", "tests": [target],
                # Λ·pi·carry — the DELEGATION EDGE, carried as data rather than collapsed into the
                # tag.  `imported` alone is an EXISTENTIAL ("somebody vouched") and forgets the
                # owner, which is why a cross-boundary clamp could not be written: the value to
                # clamp against had nowhere to come from.  Naming (owner, claim) makes this a
                # dependent PAIR — the fiber and the point in it — so a reader holding the owner's
                # grade record can resolve the import to a real grade (grade.clamp does exactly
                # this).  The CLI cannot resolve it ITSELF: certificates are build artifacts, and
                # re-deriving one here is the rm-status cost bomb the delegation exists to avoid.
                # So this returns the MAP, not its value; whoever holds the certificate applies it.
                "delegates_to": {"owner": sproj, "claim": sclaim or None, "verb": "result"},
                "why": f"adequacy delegated to the separately-gated sibling project '{target}' "
                       "(composition, not re-derivation — its own gate + Δ are the guarantee)",
                "not_higher": "imported is a delegation, not a falsifiability tier",
                "not_lower": "the sibling is gated independently in the hook; the gate, not Δ, "
                             "resolves the import live, so a broken sibling fails there"}
    if typ == "concept":
        # Λ·witness — a concept: check IMPORTS a witness the concept LIBRARY owns, grades ONCE (a
        # def-sweep whose sensitivity fingerprint IS the engine) and gates in //:hook.  Graded
        # "imported" BY DELEGATION, exactly like result: above — an imported witness lives OUTSIDE this
        # project's mutation surface (sandbox_files never reaches it), so a local sweep is blind to it
        # and could only ever read `indeterminate`: re-deriving here is not just wasteful, it is
        # STRUCTURALLY unable to see the proof.  Sound by COMPOSITION: the library carries its own gate
        # AND Δ in //:hook, so a weak or broken concept fails THERE.  The Bazel path additionally
        # imports the certificate's measured engine fingerprint into this view's adequacy and :cohere
        # (pk_grade over @paperkit_library//:<key>__dcalc), so the proof itself travels with the import.
        return {"grade": "imported", "tests": [f"library/{target}"],
                # Λ·pi·carry — see result: above.  The owner here is the concept LIBRARY, and the
                # Bazel path already resolves this edge for real: pk_grade reads the library's
                # __dcalc certificate, so the importing view's grade record carries the OWNER'S
                # measured grade (verified: paper's paper-is-projection record reads "behavioral",
                # byte-identical to the library's, and paper holds no calc of its own to derive it
                # from).  Naming the edge here lets the in-process clamp reach the same value.
                "delegates_to": {"owner": "library", "claim": target, "verb": "concept"},
                "why": f"adequacy delegated to the concept library, which owns, grades and gates the "
                       f"'{target}' witness (composition, not re-derivation)",
                "not_higher": "imported is a delegation, not a falsifiability tier",
                "not_lower": "the library is gated independently in the hook; a weak or broken concept "
                             "fails there, and the Bazel path imports its measured engine fingerprint"}
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
    reps = max(1, int(config.resolve(DELTA_REPEAT)))
    # The set is over the raw Verdict IDENTITY, NOT `.passed`: an UNAVAILABLE-then-PASS across reps
    # IS a real non-determinism (the verdict is not a function of project content), and collapsing
    # via `.passed` to {False, False} would HIDE it as a stable fail.  Verdict is identity-hashable
    # with no __bool__ precisely so this set has three distinguishable outcomes (ask-result-tristate).
    if reps > 1 and len({resolver.resolves(chk, sandbox_project, custom) for _ in range(reps)}) > 1:
        return {"grade": "broken", "tests": [], "determinism": "flaky",
                "why": f"non-deterministic — {reps} baseline runs in a pristine sandbox disagreed; "
                       "the verdict is not a function of project content (wall-clock / load / "
                       "iteration order / network?), so a single-sample mutation sweep is noise",
                "not_higher": "to rise: make the check a pure function of project content, then Δ can grade it",
                "not_lower": "—"}
    baseline, sens = sensitivity(chk, sandbox_project, custom, engine_dir, footprint, root_copy)
    # Ζ·broken·offaxis — hand the ladder the third state.  `baseline` is UNREACHABLE (falsy,
    # but not plain False) when the check could not be reached at all.
    rec = _grade_from_sens(baseline, sens, reachable=(baseline is not UNREACHABLE))
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
        # Ζ·corro·honest — `distinct`, not `independent`: this measures that the producer
        # STRINGS differ, which is a necessary condition for decorrelation and no evidence
        # of it.  `independent` is reserved for a certified disjoint read footprint.
        rec["corroboration"] = "distinct" if len(set(producers)) >= 2 else "single"
        rec["producers"] = len(producers)
    # Μ·sweep·atom — the decision-coverage AXIS (orthogonal, never a rung): of the branch decisions the
    # check REACHES, which does it never ASSERT on?  Only meaningful at def resolution (branch:/flip:
    # sites live in the engine surface) and only when the sweep found reached arms; the flip: probe is
    # a SEPARATE, non-monotone measurement barred from `sens` by construction (FlipSite).  Never fed to
    # _grade_from_sens: an unasserted decision names a gap, it does not lower the grade.
    if engine_dir is not None and rec.get("grade") == "behavioral":
        unasserted = decisions_unasserted(chk, sandbox_project, custom, engine_dir, sens)
        if unasserted:
            rec["decisions_unasserted"] = unasserted
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
        still_green = resolver.resolves(chk, sandbox_project, custom).passed
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


class FlipSite(NamedTuple):
    """Μ·sweep·atom — a NON-monotone condition site (flip:<qn>#<n>), a DISTINCT TYPE from the raise-
    kind (file, node, label) tuples the sensitivity sweep consumes.  This is the STRUCTURAL bar (not a
    string-prefix filter that could drift): a FlipSite handed to _apply/sensitivity fails when their
    `f, node, _ = …` unpacking meets a 4-field NamedTuple whose fields are not (file, node, label) —
    a value inversion can never enter a falsifiability sweep, because the sweep's signature cannot
    receive one.  Consumed ONLY by decisions_unasserted, which feeds the orthogonal decision-coverage
    axis, never the grade."""
    file: Path
    qualname: str
    n: int
    label: str


def _flip_sites_of(sandbox_project: Path, engine_dir: Path | None,
                   files: list | None = None, root_copy: Path | None = None) -> list:
    """Every flip: condition site as a FlipSite — a SEPARATE generator from _sites, so a flip: site
    is never in the list the sensitivity sweep group-tests (revision c, the structural bar)."""
    out = []
    for f in (sandbox_files(sandbox_project, set(), engine_dir) if files is None else files):
        if f.suffix != ".py":
            continue
        label = _rel(f, sandbox_project, engine_dir, root_copy)
        for qn, n, _test in _flip_sites(f.read_text()):
            out.append(FlipSite(f, qn, n, f"{label}::flip:{qn}#{n}"))
    return out


def decisions_unasserted(chk: str, sandbox_project: Path, custom: dict,
                         engine_dir: Path | None, sens: list) -> list:
    """Μ·sweep·atom — of the decisions a check REACHES, which does it never ASSERT on?  For each flip:
    condition, invert it (a NON-monotone value swap) and read it against the SECOND, independent
    probe that keeps this instrument sound (revision d — the analog of _vacuity_source's disambiguation
    of a single non-flip):

      BOTH SIBLING ARMS must be GENUINELY REACHED — proven per-arm by flip_one (a SINGLE-site probe),
      never by `sens` membership.  Group-testing correlates sibling arms: dropping one arm can flip the
      check via a sibling's raise, so an arm can appear in `sens` a fixture never takes (the
      correlated-flip finding).  flip_one isolates each arm; requiring BOTH arms individually reached
      rules out the "coincidentally invariant because the fixture only takes one path" false positive
      that a single non-flip cannot distinguish.

    Then, with both outcomes provably exercised:
      - inversion FLIPS       → the decision IS asserted (the witness observes which outcome selects).
      - inversion does NOT    → UNASSERTED: the check runs both arms but its verdict is indifferent to
                                which condition selected them — coverage the coarse behavioral grade
                                cannot see (no fixture coincidence survives, since both arms are reached).

    Returns the labels of unasserted decisions.  An orthogonal AXIS, never a rung, never fed to
    _grade_from_sens — an unasserted decision names a coverage gap, it does not lower the grade."""
    out = []
    branch_arms = _branch_arms_by_qn(sandbox_project, engine_dir)
    for fs in _flip_sites_of(sandbox_project, engine_dir):
        arms = branch_arms.get((fs.file, fs.qualname), [])
        # BOTH sibling arms genuinely reached (per-arm flip_one, not the correlated `sens`).
        if len(arms) < 2 or not all(
                flip_one(chk, sandbox_project, custom, engine_dir, lbl) for lbl in arms):
            continue
        if not _flip_flips(chk, sandbox_project, custom, engine_dir, fs):
            out.append(fs.label)
    # Μ·sweep·atom — the DATA analog: a dflip: value is UNASSERTED iff its sibling data-: DROP flips
    # (the key is genuinely READ — a single, unambiguous sibling via flip_one, no correlated-flip
    # confound to disambiguate, so ONE probe suffices where branch needed both arms) AND perturbing the
    # value to a valid same-position counterfactual does NOT flip: the check reads the entry but is
    # indifferent to WHICH valid value it holds — a wrong table value would ride through.
    for ds in _dflip_sites_of(sandbox_project, engine_dir):
        drop_label = f"{_rel(ds.file, sandbox_project, engine_dir)}::data-:{ds.qualname}#{ds.n}"
        if not flip_one(chk, sandbox_project, custom, engine_dir, drop_label):
            continue                                     # key not read → not a gap, just unreached
        if not _perturb_flips(chk, sandbox_project, custom, engine_dir, ds):
            out.append(ds.label)
    return sorted(out)


def _branch_arms_by_qn(sandbox_project: Path, engine_dir: Path | None) -> dict:
    """(file, qualname) → the branch: arm labels of that def — the siblings whose per-arm reach gates a
    flip: as an assertable decision."""
    by_qn: dict = {}
    for f, node, lbl in _sites(sandbox_project, engine_dir):
        if isinstance(node, _BranchNode):
            qn = lbl.split("::branch:", 1)[1].split("#", 1)[0]
            by_qn.setdefault((f, qn), []).append(lbl)
    return by_qn


def _flip_flips(chk: str, sandbox_project: Path, custom: dict, engine_dir: Path | None,
                fs: FlipSite) -> bool:
    """Invert fs's condition in-place, run the check, restore.  True iff the inversion flips chk red —
    the witness asserts on the decision.  A NON-monotone probe (a value swap, not a raise), which is
    exactly why fs is a FlipSite the sensitivity sweep cannot receive."""
    saved = fs.file.read_bytes()
    try:
        fs.file.write_text(_flip_condition(saved.decode(), fs.qualname, fs.n))
        return not resolver.resolves(chk, sandbox_project, custom).passed
    finally:
        fs.file.write_bytes(saved)


class DflipSite(NamedTuple):
    """Μ·sweep·atom — a NON-monotone DATA-VALUE perturb site (dflip:<qn>#<n>), the (data,perturb) cell
    of the Klein group and the DATA analog of FlipSite.  A DISTINCT 5-field type the raise-kind (file,
    node, label) sweep cannot unpack — the STRUCTURAL bar: a value swap can never enter the
    falsifiability sweep.  Consumed only by decisions_unasserted, feeding the orthogonal
    decision-coverage axis, never the grade."""
    file: Path
    qualname: str
    n: int
    kind: str
    label: str


def _dflip_sites_of(sandbox_project: Path, engine_dir: Path | None,
                    files: list | None = None, root_copy: Path | None = None) -> list:
    """Every dflip: data-value site as a DflipSite — a SEPARATE generator from _sites (the structural
    bar), scoped to DICT VALUES and non-set elements (a bare set element has no value to perturb; only
    presence, which data-: already covers).  A set literal contributes NO dflip: sites."""
    out = []
    for f in (sandbox_files(sandbox_project, set(), engine_dir) if files is None else files):
        if f.suffix != ".py":
            continue
        label = _rel(f, sandbox_project, engine_dir, root_copy)
        for qn, n, kind, _k, _v in _data_sites(f.read_text()):
            if kind == "Set":
                continue                                 # a set element has no perturbable value
            out.append(DflipSite(f, qn, n, kind, f"{label}::dflip:{qn}#{n}"))
    return out


def _perturb_flips(chk: str, sandbox_project: Path, custom: dict, engine_dir: Path | None,
                   ds: DflipSite) -> bool:
    """Perturb ds's value to a valid same-position counterfactual in-place, run the check, restore.
    True iff the perturb flips chk red — the witness ASSERTS on the value.  A NON-monotone probe (a
    value swap, not a drop), which is why ds is a DflipSite the sensitivity sweep cannot receive."""
    saved = ds.file.read_bytes()
    try:
        ds.file.write_text(emit_mutant(saved.decode(), f"dflip:{ds.qualname}#{ds.n}"))
        return not resolver.resolves(chk, sandbox_project, custom).passed
    finally:
        ds.file.write_bytes(saved)


# Ζ·delta·tmpdir — WHERE a sweep's sandbox copies live, and why not the default /tmp.
#
# Each concurrent def-sweep copies the WHOLE repo (measured on paperkit itself: 1.4-3.2GB per
# copy, three concurrent = 7.2GB).  On a distro whose /tmp is a tmpfs that is RAM, so the copies
# compete with the page cache AND with the very memory budget the sweep schedules against —
# one resource counted once, spent twice.  Measured the hard way: a //:hook run filled a 7.7GB
# /tmp to 100%, at which point nothing on the box could write a temp file at all.
#
# The scheduler models RAM (tools/sweep_budget.py) and says nothing about disk, so the collision
# is invisible to it.  Rather than teach the budget a second axis, put the copies somewhere disk
# BACKED — 80GB free there against 7.7GB of tmpfs on this box — and the two resources decouple.
#
# Resolution ladder (= the Ω·config ladder): PAPERKIT_SCRATCH > XDG_CACHE_HOME > ~/.cache, and
# only then the platform default.  A machine that WANTS tmpfs sets PAPERKIT_SCRATCH=/tmp.
_SANDBOX_PREFIX = "paperkit-delta-"


def _scratch_dir() -> str | None:
    """The parent for sweep sandboxes — disk-backed by preference.  None ⇒ platform default."""
    for cand in (os.environ.get("PAPERKIT_SCRATCH"),
                 os.environ.get("XDG_CACHE_HOME"),
                 os.path.expanduser("~/.cache") if os.path.expanduser("~") != "~" else None):
        if not cand:
            continue
        d = Path(cand) / "paperkit-sweep" if not os.environ.get("PAPERKIT_SCRATCH") else Path(cand)
        try:
            d.mkdir(parents=True, exist_ok=True)
            if os.access(d, os.W_OK):
                return str(d)
        except OSError:
            continue
    return None                                   # tempfile's default: never a hard failure


def reap_sandboxes(older_than_s: int = 1800) -> int:
    """Ζ·delta·leak — remove sweep sandboxes no live sweep owns.  Returns the count removed.

    `_grade_one` and `mutate_one` both rmtree their sandbox in a `finally`, which is correct and
    runs on every normal exit.  It does NOT run on SIGKILL — and a long sweep gets killed: three
    interrupted //:hook runs in one session left 42 husks behind.  They were small (672K total,
    the copy having been reclaimed by the kernel when the process died mid-write), so this is
    hygiene rather than the disk fix above; the two are separate defects and only one of them
    was ever going to fill a filesystem.
    A directory is reaped only if it is older than the window AND holds no open file — a live
    sweep's copy is neither."""
    import time
    parent = Path(_scratch_dir() or tempfile.gettempdir())
    now, n = time.time(), 0
    for d in parent.glob(_SANDBOX_PREFIX + "*"):
        try:
            if now - d.stat().st_mtime < older_than_s:
                continue
            shutil.rmtree(d, ignore_errors=True)
            n += 1
        except OSError:
            continue
    return n


def _sandbox_setup(project_dir, resolution="def"):
    """A fresh sandbox COPY of the project + engine (the bounded mutation universe), shared by the
    grade sweep (_grade_one) and the single-site probe (mutate_one).  Returns
    (tmp, sandbox_project, engine_dir, root_copy): engine_dir is the COPIED engine when
    resolution == "def" (so witnesses are sensitive to the engine they test, not only their own
    script), None at file resolution (the engine would add only the import-crash flood).  Locate
    the engine by its position UNDER root — directly when _ENGINE lives inside root (a
    self-contained repo), else by name (the Bazel case, where _ENGINE.resolve() follows the staged
    symlink OUT of the execroot though the engine IS copied to root/<name>).  Ν·loud if a def
    sweep's engine copy is missing: refuse to degrade to file resolution and emit a vacuous
    fingerprint (the Bazel-symlink degeneracy that once shipped a green-for-nothing gate).  Caller
    rmtree's tmp."""
    tmp = Path(tempfile.mkdtemp(prefix=_SANDBOX_PREFIX, dir=_scratch_dir()))
    root = _sandbox_root(project_dir)
    _copy_sandbox(root, tmp / root.name)
    root_copy = tmp / root.name
    rel = project_dir.relative_to(root)
    sandbox = root_copy if rel == Path(".") else root_copy / rel
    engine = None
    if resolution == "def":
        eng_rel = _ENGINE.relative_to(root) if _ENGINE.is_relative_to(root) else Path(_ENGINE.name)
        engine = root_copy / eng_rel
        if not engine.is_dir():
            raise RuntimeError(
                f"Ν·loud: def-resolution sweep cannot find the engine in the sandbox "
                f"(expected a directory at {engine}, under the copied root {root}); refusing "
                f"to silently degrade to file resolution and emit a vacuous fingerprint.")
    return tmp, sandbox, engine, root_copy


def _grade_one(project_dir, chk, custom, presupposed, resolution="file"):
    """Grade one check in its own fresh sandbox copy (so concurrent grades never share a
    mutation).  `resolution` ("file"|"def") decides whether the engine joins the surface."""
    tmp, sandbox, engine, root_copy = _sandbox_setup(project_dir, resolution)
    try:
        # the check's READ footprint (strace).  Δ·scope: a def sweep is bounded to the files the
        # check actually reads (sensitivity ⊆ footprint).  A def grade traces ONCE at ROOT scope so
        # the trace sees ENGINE reads ("paperkit/x.py", "<proj>/checks/y.py"); the cache key stays
        # PROJECT-scoped, derived from the same trace (no second strace) — engine entries aren't
        # project inputs (the engine-epoch hash covers them).  File resolution traces project-scoped.
        # Ζ·surface — trace at ROOT scope at BOTH granularities.  The trace's scope used to be welded
        # to the granularity too (file resolution traced project-scoped), which is what made the
        # subject unrepresentable there: a project-relative footprint cannot NAME the engine, so a
        # constructed surface had nothing to construct from and the claim could only read
        # indeterminate.  The cache key stays PROJECT-scoped, derived from the same trace (no second
        # strace) — engine entries aren't project inputs (the engine-epoch hash covers them).
        sweep_fp = resolver.footprint(chk, sandbox, custom, scope=root_copy)
        if sweep_fp is None:
            fp = None
        elif sandbox == root_copy:
            fp = sweep_fp                                        # the root project: its scope IS root
        else:
            pre = str(sandbox.relative_to(root_copy)) + "/"
            fp = sorted(p[len(pre):] for p in sweep_fp if p.startswith(pre))
        rec = grade_check(chk, project_dir, presupposed, custom, sandbox, engine, sweep_fp, root_copy)
        rec["_footprint"] = fp
        # Ζ·surface·kind — how much of the claim the grade actually LOOKED AT.  Orthogonal to the
        # rung: a grade over an incomplete surface is not a weaker grade, it is a narrower one.
        rec["unmeasured"] = unmeasured_reads(sweep_fp, root_copy)
        return rec
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def mutate_one(project_dir: Path, chk: str, custom: dict, site_label: str) -> bool:
    """Ζ·mutant — set up the def-resolution sandbox and probe ONE site (flip_one).  The engine
    entry a pk_mutant action calls: one (claim, site) → flipped, hermetic in its own sandbox copy,
    so Bazel owns and caches the sweep's fanout site-by-site instead of an in-process bisection."""
    tmp, sandbox, engine, _ = _sandbox_setup(project_dir, "def")
    try:
        return flip_one(chk, sandbox, custom, engine, site_label)
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
    every = float(config.resolve(DELTA_PULSE))   # min seconds between log pulses; 0 = off
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
