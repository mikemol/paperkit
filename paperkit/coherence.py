#!/usr/bin/env python3
"""paperkit coherence (∂²) — measure how far a project's DECLARED structure reflects
its MEASURED sensitivity: the boundary-of-a-boundary residual.

Δ grades whether each check CAN fail; ∂² asks whether the structure the claims declare
actually shows up in what makes them fail.  Three faces, all read from the existing
pipeline (`discriminate --resolution def --json`), so nothing new is measured — re-read:

  STRUCTURE   prose is a LINEARIZATION of the claim-DAG.  A grounding (`rests-on`) edge
              between prose-ADJACENT claims is carried by the connective for free; a
              NON-ADJACENT one is a LONG EDGE the linear text owes a projected cross-
              reference (citation / figure / expounding — what a connective IS at distance
              > 0).  The residual is the long edges not yet projected.

  SENSITIVITY each claim's measured sensitivity set is its Δ `tests` (the inputs whose
              corruption flips it).  --without-K makes the witnesses NAME-distinct, but
              they may still COLLAPSE to one sensitivity signature — name-distinct yet
              measuring the same thing.  At definition resolution every witness carries a
              distinct engine-capability fingerprint, so the collapse closes.

  GROUNDING   each DECLARED grounding edge (rests-on) should be REFLECTED in measured
              sensitivity: a claim that rests-on Y should exercise some of the engine Y
              tests (their fingerprints overlap).  A disjoint edge is discharged when its
              non-reflection is explained — MEASURABLY (X tests no engine capability, so it
              is vacuously disjoint: rhetorical grounding) or by a `link` (the sibling of
              the structure discharge).  Only a GENUINE, un-acknowledged miss is residual.

  EMERGENCE   the STRICTER sibling of grounding (Ζ·emerge): grounding asks per-edge OVERLAP, this
              asks per-claim COVERAGE — does a claim's fingerprint REDUCE to its premises',
              fp(X) ⊆ ∪fp(rests-on)?  A claim that collapses adds no engine discrimination beyond
              its grounding (its witness emerges by consumption — the proof composes); an increment
              tests engine capability no premise does (under-grounded, or an irreducible leaf); a
              leaf is an axiom.  Where grounding's overlap passes, coverage can still catch a delta.

  UNMEASURED  the SYMDIFF of the two graphs the faces above read (Ζ·symdiff).  STRUCTURE is
              computed from the bib, so it counts every edge whose SOURCE is a record;
              GROUNDING and EMERGENCE need a fingerprint at BOTH ends and silently skip an
              edge whose target was never graded.  On a partial grade that gap is invisible
              and large.  Reported so a partial reading declares its own incompleteness:
              `pending` (target awaiting measurement) shrinks to zero as the grade completes,
              `dangling` (target no bib entry declares) is a broken edge and does not.

A high residual is not a failure to hide — it is the gap between what a document SAYS
grounds it and what DEMONSTRABLY does, surfaced so it can be closed (move-unification
for structure; definition-resolution fingerprints for sensitivity, grounding, and emergence).

    coherence.py [DIR]            # the residual report
    coherence.py --json [DIR]     # structured
    coherence.py --from-cache [DIR]   # read .delta-cache.json — no re-sweep, partial-grade OK
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bib  # noqa: E402  (the parser/data-model leaf — read the bib structure + `link` acknowledgments)

_ENGINE = Path(__file__).resolve().parent


def _linearize(records: list) -> dict:
    """The prose linearization: each section's claims in dep_order (topological by
    `from`), concatenated in section-first-appearance order.  Returns {key: position}."""
    frm = {r["key"]: r.get("from", []) for r in records}
    secs, order = [], {}
    for r in records:                       # sections in first-appearance order
        s = r.get("section")
        order.setdefault(s, []).append(r["key"])
        if s not in secs:
            secs.append(s)
    pos, idx = {}, 0
    for s in secs:
        seen, out = set(), []

        def visit(k):
            if k in seen or k not in order[s]:
                return
            seen.add(k)
            for a in frm.get(k, []):
                visit(a)
            out.append(k)

        for k in order[s]:
            visit(k)
        for k in out:
            pos[k] = idx
            idx += 1
    return pos


def structure_residual(records: list, discharged=frozenset()) -> dict:
    """Face one, by the EDGE-PROJECTION model.  Prose is a LINEARIZATION of the claim-DAG;
    a grounding (`rests-on`) edge to a prose-ADJACENT claim is carried by the connective
    for free, but a NON-ADJACENT one is a LONG EDGE the linear text owes a projected
    cross-reference — a citation / figure / expounding (the same thing a connective is, at
    distance > 0; the direction is the sign of the prose-distance).  The residual is the
    long edges not yet projected; ADVISORY, dischargeable by a `link` footnote (or, the
    constructive close, by actually projecting the reference)."""
    pos = _linearize(records)
    carried, long_edges = 0, []
    for r in records:
        k = r["key"]
        for y in r.get("rests-on", []):
            if y not in pos or k not in pos:
                long_edges.append((k, y, None))      # cross-scope target — always owed
            elif pos[y] == pos[k] - 1:
                carried += 1                          # the immediate predecessor: connective carries it
            else:
                long_edges.append((k, y, pos[k] - pos[y]))
    undischarged = sum(1 for k, _, _ in long_edges if k not in discharged)
    return {"carried": carried, "owed": len(long_edges), "undischarged": undischarged,
            "long_edges": long_edges}


def sensitivity_residual(records: list) -> dict:
    """Face two: how many DISTINCT sensitivity signatures the behavioral witnesses
    actually have, vs how many name-distinct witnesses there are.  The collapse is the
    count that share their signature with another (name-distinct, sensitivity-same)."""
    sigs: dict = {}
    for r in records:
        if r.get("grade") != "behavioral":
            continue
        sigs.setdefault(tuple(sorted(r.get("tests", []))), []).append(r["key"])
    classes = sorted(sigs.values(), key=len, reverse=True)
    behavioral = sum(len(c) for c in classes)
    largest = classes[0] if classes else []
    return {
        "behavioral": behavioral,
        "signatures": len(classes),
        "collapse": behavioral - len(classes),          # redundant witnesses, by sensitivity
        "largest_class": len(largest),
        "largest_signature": list(largest and sorted(sigs.keys(), key=lambda k: len(sigs[k]))[-1]),
    }


def _engine_cap(tests, universal=frozenset()) -> set:
    """The capability fingerprint — the sites that DISCRIMINATE this claim from its siblings.

    Ζ·torsor — the faces below are set algebra over fingerprints (`S[k] - ∪S[premises]`,
    pairwise intersection, equality classes).  That algebra is FRAME-INDEPENDENT: differences
    between fingerprints carry the meaning, the absolute origin does not.  So what must be
    fixed is not WHICH subtree the sites live in, but which sites are UNINFORMATIVE — the ones
    every witness trips, on which overlap is trivially satisfied and tells you nothing.

    This used to hardcode one frame: sites under `paperkit/`, minus `paperkit/tests/`.  That is
    right for a project whose witnesses exercise the ENGINE, and empty for one whose witnesses
    are self-contained — gcalculus's checks run `python3 concepts.py <key>` and never open a
    paperkit module, so every fingerprint came back empty and `_vacuous_exit` refused a document
    that is in fact richly discriminating (14 def-granular sites on its first claim alone).  The
    measurement was not degraded; it was being read in the wrong frame.

    So the shared scaffolding is now COMPUTED rather than named: the sites present in EVERY
    cited claim's fingerprint are the frame's origin, and quotienting them out leaves exactly
    the discrimination.  For the engine case this derives what the old constant asserted (the
    fixture builder is in every witness's footprint); for a self-contained project it derives
    the dispatcher and the assertion guard instead.  Nothing is declared, so nothing can go
    stale against the thing it describes.

    With FEW claims graded, everything looks universal and the fingerprints collapse toward
    empty.  That is not a flaw in the measure — it is the measure reporting that coverage is too
    thin to discriminate, and the answer is to grade more claims.

    Ζ·torsor·own — the computed quotient does NOT subsume one structural exclusion, and dropping
    it was a regression the boundary suite caught: a claim's OWN check script (`checks/<claim>`)
    is per-claim by construction, so it is never in the intersection and no amount of coverage
    will remove it.  It must go by KIND, not by frequency: a witness co-flipping with its own
    script is the check testing itself, which is evidence about the mechanism and never about
    the claim.  `paperkit/tests/` (the shared fixture builder) is the same argument at the
    engine's scale.  So the frame is a COMPOSITION — structural exclusion by kind, then the
    computed quotient by universality — and only the old `paperkit/`-only INCLUSION filter is
    gone, since that is the part that made a self-contained project read as vacuous."""
    return {t for t in tests
            if t not in universal
            and not t.startswith("checks/")
            and not t.startswith("paperkit/tests/")}


def _universal_sites(records: list) -> frozenset:
    """The sites EVERY cited claim's sensitivity contains — the frame origin to quotient out.

    Intersection over all fingerprints.  A site every witness trips (a dispatcher, an assertion
    guard, the bib the gate re-reads) cannot separate two claims, so leaving it in makes
    grounding overlap trivially true.  Empty intersection ⇒ nothing is universal ⇒ every site
    already discriminates, and the quotient is the identity.

    Computed over the STRUCTURALLY-admissible sites only (see `_engine_cap`): a claim's own
    check script and the shared fixture builder are excluded by kind first, so they can neither
    pollute the intersection nor be double-counted by it.

    Ν·frame — universality needs SIBLINGS to be meaningful.  With a single fingerprint every
    site it holds is trivially in the intersection, so the quotient would empty it and the
    measurement would read vacuous — conflating "every claim tests the same thing" (genuinely
    undiscriminating) with "there is only one claim" (nothing to discriminate FROM).  Below two
    fingerprints the frame is UNDEFINED, and the identity quotient is the honest answer: report
    what was measured rather than subtract a frame that was never established."""
    sets = [{t for t in r.get("tests", [])
             if not t.startswith("checks/") and not t.startswith("paperkit/tests/")}
            for r in records if r.get("tests")]
    sets = [s for s in sets if s]
    if len(sets) < 2:
        return frozenset()
    return frozenset(set.intersection(*sets))


def unmeasured_edges(records: list, all_keys=frozenset()) -> dict:
    """Ζ·symdiff — the edges STRUCTURE counts that the MEASURED faces cannot see.

    The faces read two different graphs and never said so.  STRUCTURE is computed from the bib
    alone, so it counts every `rests-on` edge whose SOURCE is in the record set.  GROUNDING and
    EMERGENCE need a fingerprint at BOTH ends: grounding's `if not sy: continue` and emergence's
    `[y for y in rests-on if y in S]` both drop an edge whose target was never graded.  On a
    partial grade that difference is silent and large — widening one claim's grounding by three
    edges moved `owed` 8→11 while `reflected`, `undischarged` and `increment` did not move at
    all, which reads as "the edges changed nothing" when the truth is "three faces never saw
    them."

    Worse, `if not sy` CONFLATES two states that mean opposite things:

      measured empty    Y was graded and its fingerprint is empty — Y tests no capability, so
                        the edge is vacuously disjoint.  Rhetorical grounding, auto-discharged.
                        A real verdict.
      never graded      Y has no record at all.  NOT a verdict — the measurement has not looked.

    Reporting them the same way is the sentinel error one level down: *not measurable from here*
    is not *nothing to measure*.  This face separates them, so a partial reading states its own
    incompleteness instead of implying coverage it does not have.  `pending` shrinks to zero as
    the grade completes; a `dangling` edge names a target no bib entry declares at all, which is
    a broken edge rather than an ungraded one and does not shrink."""
    graded = {r["key"] for r in records}
    pending, dangling = [], []
    for r in records:
        for y in r.get("rests-on", []):
            if y in graded:
                continue
            (dangling if (all_keys and y not in all_keys) else pending).append([r["key"], y])
    return {"pending": pending, "dangling": dangling,
            "unmeasured": len(pending) + len(dangling)}


def grounding_residual(records: list, discharged=frozenset(), universal=frozenset()) -> dict:
    """Face three (the comparison the roadmap reserved): does each DECLARED grounding
    edge (`rests-on`) show up in MEASURED sensitivity?  A claim X that rests-on Y should
    exercise some of the engine Y tests — their engine-capability fingerprints should
    OVERLAP.  A disjoint edge X→Y is discharged when its non-reflection is EXPLAINED:

      rhetorical    X tests no engine capability at all (an empty fingerprint), so the
                    edge is VACUOUSLY disjoint — a thesis/meta claim grounded rhetorically,
                    not behaviourally.  This is MEASURED, not asserted: it auto-discharges.
      acknowledged  X DOES test engine capability, just not Y's, but a `link` footnote
                    acknowledges it (the sibling of the structure face's discharge).

    Only a GENUINE miss — X tests engine capability, disjoint from Y's, and un-acknowledged
    — is the residual: declared grounding the measurement does not see and no one explained."""
    S = {r["key"]: _engine_cap(r.get("tests", []), universal) for r in records}
    edges = reflected = rhetorical = undischarged = 0
    misses = []
    for r in records:
        k = r["key"]
        sx = S.get(k, set())
        for y in r.get("rests-on", []):
            sy = S.get(y)
            if not sy:                          # Y measures no engine capability — no claim to test
                continue
            edges += 1
            if sx & sy:
                reflected += 1
            elif not sx:
                rhetorical += 1                 # X's fingerprint is empty — vacuously disjoint (measured)
            elif k in discharged:
                pass                            # author-acknowledged via a `link` footnote
            else:
                undischarged += 1
                misses.append([k, y])
    return {"grounding_edges": edges, "reflected": reflected, "rhetorical": rhetorical,
            "undischarged": undischarged, "misses": misses}


def emergence_residual(records: list, universal=frozenset()) -> dict:
    """Face four (Ζ·emerge): the STRICTER sibling of grounding.  Grounding asks per-edge OVERLAP
    (does X exercise SOME of what Y tests); emergence asks per-claim COVERAGE — does the claim's
    engine fingerprint REDUCE to its premises', fp(X) ⊆ ∪fp(rests-on)?  A claim that COLLAPSES adds
    no engine discrimination beyond its grounding: its witness is redundant and EMERGES by
    consumption (the proof composes — Ζ·compose).  A claim with an INCREMENT tests engine capability
    NO premise does (the delta).  An increment is NOT by itself an under-grounding: a def-fingerprint
    records what the CHECK exercises, which includes the check's MECHANISM (the engine it RUNS to
    verify a thesis — e.g. a claim about the bib whose check runs the resolver to confirm a check
    resolves) and the claim's OWN origin-capability, not only the thesis's grounding.  So an increment
    means KEEP / contributes (collapse-safe), and reads three ways: under-grounded (add the missing
    rests-on), the claim's irreducible contribution, or pure check mechanism.  The sound under-grounding
    signal is the GROUNDING face (overlap), not this one.  A LEAF (no rests-on) is an axiom.  Where
    grounding's OVERLAP can pass (the edge shares one site) while the claim still tests more,
    emergence's SUBSET catches it: the residual is the increments — claims the grounding does not COVER."""
    S = {r["key"]: _engine_cap(r.get("tests", []), universal) for r in records}
    collapse = leaf = 0
    increments = []
    for r in records:
        k = r["key"]
        prem = [y for y in r.get("rests-on", []) if y in S]
        if not prem:
            leaf += 1
            continue
        delta = sorted(S.get(k, set()) - set().union(*[S[y] for y in prem]))
        if delta:
            increments.append([k, delta])
        else:
            collapse += 1
    return {"collapse": collapse, "increment": len(increments), "leaf": leaf, "increments": increments}


def report(records: list, discharged=frozenset(), all_keys=frozenset()) -> dict:
    cited = [r for r in records if r.get("cited", True)]
    # Ζ·torsor — derive the frame ONCE from the whole record set, then measure every face in it.
    # The origin (the universal sites) is computed, not declared, so it cannot go stale.
    universal = _universal_sites(cited)
    return {"claims": len(cited),
            # Ν·vac — vacuous iff no cited claim retains ANY discriminating site once the frame's
            # origin is quotiented out.  This is now FRAME-RELATIVE and therefore honest: a
            # document whose witnesses all trip exactly the same sites cannot be told apart by
            # this measurement, whether that is a degraded sweep or a corpus too thinly graded to
            # separate.  Either way no real verdict is possible — callers must refuse green.
            "vacuous": bool(cited) and not any(_engine_cap(r.get("tests", []), universal)
                                               for r in cited),
            "frame": {"universal": sorted(universal), "quotiented": len(universal)},
            "structure": structure_residual(cited, discharged),
            "sensitivity": sensitivity_residual(cited),
            "grounding": grounding_residual(cited, discharged, universal),
            "emergence": emergence_residual(cited, universal),
            # Ζ·symdiff — what STRUCTURE counted and the measured faces could not see.  Reported
            # beside them so a partial reading declares its own incompleteness.
            "unmeasured": unmeasured_edges(cited, all_keys)}


def _records(project_dir: Path) -> list:
    # def resolution: the sensitivity face is only meaningful at the per-definition
    # fingerprint — at file resolution every witness collapses to the import-crash
    # signature.  This is the costly grade (the on-demand precision pass), not the hook's.
    r = subprocess.run([sys.executable, str(_ENGINE / "discriminate.py"),
                        "--resolution", "def", "--json", str(project_dir)],
                       capture_output=True, text=True)
    return json.loads(r.stdout or "[]")


def _records_from_calcs(project_dir: Path, calc_files: list) -> list:
    """Ζ·emerge·gate — assemble the records coherence reads from CACHED calc records (the measurement,
    sens) + the bib STRUCTURE (rests-on/section/from), instead of re-running the def-resolution sweep.
    This is what makes the ∂² faces a CHEAP READING over the cached calculation.  The structure comes
    from the canonical parser (paperkit.bib, via bib.parse) — entries already carries rests-on."""
    F = {}
    for b in bib.load_config(project_dir)["bibs"]:
        F.update(bib.parse(b))
    recs = []
    for f in calc_files:
        c = json.loads(Path(f).read_text())
        k = c["claim"]
        st = F.get(k, {})
        recs.append({"key": k, "tests": c.get("sens", []), "rests-on": st.get("rests-on", []),
                     "section": st.get("section", ""), "from": st.get("from", []),
                     "grade": "behavioral" if c.get("sens") else "vacuous", "cited": True})
    return recs


def _records_from_cache(project_dir: Path) -> list:
    """Ζ·emerge·resume — assemble the records from `.delta-cache.json`, the cache `discriminate`
    ALREADY writes, instead of re-running the sweep or reading Bazel calc artifacts.

    The third records source, and the one a plain checkout can use.  `_records` shells out to a
    full `--resolution def` sweep with no --state and no --budget: unresumable, and measured at
    3.5h on a 118-claim project before a kill discarded all of it.  `_records_from_calcs` is the
    cheap path but reads per-claim calc files that only the Bazel pipeline produces.  Between
    them sat the artifact that makes the ∂² faces readable anywhere: the per-check cache, keyed
    on each check's read footprint over the engine epoch, which `discriminate --state/--budget`
    accumulates ACROSS bounded increments.

    So the residual becomes a reading over WHATEVER HAS BEEN GRADED SO FAR.  A partial cache
    yields a partial report — the faces are per-claim, so a claim absent from the cache is simply
    not among the records, exactly as an uncited one is not.  That is what makes a work-list
    derivable incrementally rather than only after a sweep runs to completion: grade for ten
    minutes, read what is known, grade ten more.

    A `file`-resolution cache is REFUSED rather than read: at file resolution every witness
    collapses to the import-crash signature (the reason `_records` asks for def), so reading one
    would feed the sensitivity, grounding and emergence faces a measurement that cannot
    discriminate — and `_vacuous_exit` would then report a vacuous DOCUMENT rather than a wrong
    tool.  Ν·loud: refuse, naming the resolution found, rather than degrade."""
    p = project_dir / ".delta-cache.json"
    if not p.is_file():
        raise SystemExit(f"Ν·loud: no .delta-cache.json in {project_dir} — run "
                         "`discriminate.py --resolution def --state S --budget N` first")
    cached = json.loads(p.read_text())
    if cached.get("resolution") != "def":
        raise SystemExit(
            f"Ν·loud: .delta-cache.json is {cached.get('resolution')!r} resolution, not 'def' — "
            "at file resolution every witness collapses to the import-crash signature, so the "
            "sensitivity, grounding and emergence faces would read a measurement that cannot "
            "discriminate.  Re-grade with --resolution def.")
    F = {}
    for b in bib.load_config(project_dir)["bibs"]:
        F.update(bib.parse(b))
    # a check may serve SEVERAL claims (binding dilution) — the cache keys by check, the faces
    # key by claim, so one cached grade fans out to every claim citing it.
    by_check: dict = {}
    for k, f in F.items():
        if f.get("check"):
            by_check.setdefault(f["check"], []).append(k)
    recs = []
    for chk, entry in sorted(cached.get("checks", {}).items()):
        g = entry.get("grade") or {}
        for k in by_check.get(chk, []):
            st = F.get(k, {})
            recs.append({"key": k, "tests": g.get("tests", []),
                         "rests-on": st.get("rests-on", []), "section": st.get("section", ""),
                         "from": st.get("from", []), "grade": g.get("grade", "indeterminate"),
                         "cited": True})
    return recs


def _all_keys(project_dir: Path) -> frozenset:
    """Every key the bib DECLARES — the set against which an ungraded target is `pending`
    (a claim awaiting measurement) rather than `dangling` (an edge to nothing at all)."""
    F = {}
    for b in bib.load_config(project_dir)["bibs"]:
        F.update(bib.parse(b))
    return frozenset(F)


def _discharged(project_dir: Path) -> set:
    """Claims carrying a `link` footnote — the author has acknowledged that this claim's
    prose and grounding edges diverge, and why; that discharges the advisory."""
    cfg = bib.load_config(project_dir)
    F = {}
    for b in cfg["bibs"]:
        F.update(bib.parse(b))
    return {k for k, f in F.items() if f.get("link")}


def _vacuous_exit(project_dir: Path, rep: dict) -> bool:
    """Ν·vac — print + signal when the measurement carries NO engine capability at all, so a
    caller never reports a verdict (green or red) over a vacuous def-sweep."""
    if not rep["vacuous"]:
        return False
    print(f"Ν·vac: coherence over {project_dir.name or project_dir}: NO claim tests any engine "
          f"capability ({rep['claims']} claims, every fingerprint empty) — a vacuous measurement "
          f"(a degraded def-sweep?); refusing to emit a verdict.", file=sys.stderr)
    return True


def main(argv: list) -> int:
    as_json = "--json" in argv
    pos = [a for a in argv if not a.startswith("-")]
    project_dir = Path(pos[0]).resolve() if pos else Path.cwd()
    if "--from-calcs" in argv:
        # Ζ·emerge·gate — cheap coherence: read CACHED calc records (sens) + the bib structure, no
        # re-sweep.  pos = [project, calc.json...].  The gateable reading over the calculation.
        rep = report(_records_from_calcs(project_dir, pos[1:]), _discharged(project_dir),
                     _all_keys(project_dir))
        if as_json:
            print(json.dumps({"document": project_dir.name or str(project_dir), **rep}, indent=2))
        if _vacuous_exit(project_dir, rep):
            return 2
        return 0 if rep["grounding"]["undischarged"] == 0 else 1
    # Ζ·emerge·resume — read the accumulated per-check cache instead of re-sweeping.  Same
    # faces, same report; the measurement comes from whatever `--state/--budget` increments
    # have graded so far, so a partial grade yields a partial (never a wrong) reading.
    src = _records_from_cache if "--from-cache" in argv else _records
    rep = report(src(project_dir), _discharged(project_dir), _all_keys(project_dir))
    if as_json:
        print(json.dumps({"document": project_dir.name or str(project_dir), **rep}, indent=2))
        return 2 if rep["vacuous"] else 0
    if _vacuous_exit(project_dir, rep):
        return 2
    s, se, g, e = rep["structure"], rep["sensitivity"], rep["grounding"], rep["emergence"]
    print(f"coherence (∂²): {project_dir.name or project_dir} — {rep['claims']} cited claims")
    print(f"  structure  : {s['carried']} grounding edges carried by the prose connective, "
          f"{s['owed']} are LONG edges owed a projected cross-reference; {s['undischarged']} "
          f"un-acknowledged (advisory — project the reference, or discharge with a `link`)")
    print(f"  sensitivity: {se['behavioral']} behavioral witnesses → {se['signatures']} distinct "
          f"sensitivity signatures ({se['collapse']} collapse); the largest {se['largest_class']} "
          f"share {se['largest_signature']}")
    print(f"  grounding  : {g['reflected']}/{g['grounding_edges']} rests-on edges reflected in "
          f"measured engine sensitivity; {g['rhetorical']} vacuously disjoint (rhetorical — the "
          f"claim tests no engine capability); {g['undischarged']} genuine, un-acknowledged "
          f"(advisory — overlap the fingerprints, or discharge with a `link`)")
    for x, y in g["misses"]:
        print(f"               [@{x}] rests-on [@{y}] — tests engine capability, but not [@{y}]'s")
    print(f"  emergence  : {e['collapse']} claims COLLAPSE (engine sensitivity ⊆ grounding → witness "
          f"emerges by consumption), {e['increment']} INCREMENT (test engine capability beyond their "
          f"grounding), {e['leaf']} LEAF axioms (no grounding → self-contained checks)")
    for x, d in e["increments"]:
        print(f"               [@{x}] +{len(d)} engine site(s) beyond its grounding "
              f"— e.g. {[t.split('::')[-1] for t in d[:3]]}")
    um = rep["unmeasured"]
    if um["unmeasured"]:
        print(f"  unmeasured : {len(um['pending'])} declared edge(s) STRUCTURE counts that "
              f"grounding and emergence CANNOT see — the target is not graded, so those faces "
              f"skip the edge silently; {len(um['dangling'])} point at no bib entry at all")
        for x, y in um["pending"][:6]:
            print(f"               [@{x}] rests-on [@{y}] — target ungraded (grade it to measure)")
        for x, y in um["dangling"]:
            print(f"               [@{x}] rests-on [@{y}] — NO SUCH ENTRY (a broken edge)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
