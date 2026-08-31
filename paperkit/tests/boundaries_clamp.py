#!/usr/bin/env python3
"""Behavioral-boundary examples for the effective-grade clamp — paperkit/grade.py::clamp.

⟨P, F, δ⟩ per the boundary practice.  The clamp bounds a claim's effective grade by the weakest
premise it transitively rests on, and (Λ·pi·carry) resolves a DELEGATION edge to the owner's real
grade when the caller supplies one.  Bounds: a healthy corpus clamps nothing, a weak owner clamps
its importer AND everything resting on it, and the minimum delta is one owner grade — the SAME
records clamp or do not depending solely on whether the owner's grade is in hand.

    python3 paperkit/tests/boundaries_clamp.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import grade as G

_fails = []


def check(desc, ok):
    print(f"  {'ok' if ok else 'XX'} {desc}")
    if not ok:
        _fails.append(desc)


def recs():
    """`a` rests on `b`; `b` delegates to library#w.  Rebuilt per call — clamp() MUTATES."""
    return [
        {"key": "a", "grade": "behavioral", "rests-on": ["b"]},
        {"key": "b", "grade": "imported", "rests-on": [],
         "delegates_to": {"owner": "library", "claim": "w", "verb": "concept"}},
    ]


def by(rs):
    return {r["key"]: r for r in rs}


def main() -> int:
    print("CLAMP BOUNDARIES ⟨P, F, δ⟩")

    # ---- P: no owner grades → the pre-Λ·pi·carry behaviour, exactly ----
    r = by(G.clamp(recs()))
    check("P: with no owner grades, an unresolved delegation does NOT clamp (imported ranks top)",
          r["b"]["effective_grade"] == "imported" and r["a"]["effective_grade"] == "behavioral")
    check("P: and nothing is credited as the pin",
          r["b"]["clamped_by"] is None)

    # ---- P: a STRONG owner resolves the edge and still clamps nothing ----
    r = by(G.clamp(recs(), {("library", "w"): "behavioral"}))
    check("P: a behavioral owner resolves the edge without weakening the importer",
          r["b"]["effective_grade"] == "behavioral" and r["a"]["effective_grade"] == "behavioral")

    # ---- F: a WEAK owner clamps the importer, and the taint TRANSITS rests-on ----
    r = by(G.clamp(recs(), {("library", "w"): "vacuous"}))
    check("F: a vacuous owner clamps its importer to vacuous",
          r["b"]["effective_grade"] == "vacuous")
    check("F: and the clamp CROSSES the boundary then transits rests-on to the dependent claim",
          r["a"]["effective_grade"] == "vacuous")
    check("F: the pin NAMES the owning claim, not a local key",
          r["b"]["clamped_by"] == "library#w")

    # ---- δ: the minimum delta is ONE owner grade over identical records ----
    without = by(G.clamp(recs()))["a"]["effective_grade"]
    with_ = by(G.clamp(recs(), {("library", "w"): "vacuous"}))["a"]["effective_grade"]
    check("δ: identical records, one owner grade apart → behavioral vs vacuous",
          (without, with_) == ("behavioral", "vacuous"))

    # ---- F: an owner grade for a DIFFERENT claim must not resolve this edge ----
    r = by(G.clamp(recs(), {("library", "other"): "vacuous"}))
    check("F: a non-matching owner key leaves the edge unresolved (no accidental clamp)",
          r["b"]["effective_grade"] == "imported")
    # ---- F: ...and neither does the right claim under the WRONG owner ----
    r = by(G.clamp(recs(), {("paper", "w"): "vacuous"}))
    check("F: the owner is part of the key — same claim, wrong owner, no clamp",
          r["b"]["effective_grade"] == "imported")

    # ---- P: a record with no delegation edge is untouched by owner_grades ----
    plain = [{"key": "p", "grade": "existence", "rests-on": []}]
    check("P: a non-delegating record is unaffected by owner grades",
          by(G.clamp(plain, {("library", "w"): "vacuous"}))["p"]["effective_grade"] == "existence")

    # ---- the grade is TWO-DIMENSIONAL: (self, effective) both cross the edge ----
    # Two owners with the SAME effective grade but DIFFERENT self grades must stay
    # distinguishable on the importing side — one has a weak WITNESS, the other a weak PREMISE,
    # and an importer chasing the problem needs to know which.  Collapsing to one scalar at the
    # boundary is the truncation Ζ·pi·effective closes.
    weak_witness = {("library", "w"): {"grade": "vacuous", "effective_grade": "vacuous",
                                       "clamped_by": None}}
    weak_premise = {("library", "w"): {"grade": "behavioral", "effective_grade": "vacuous",
                                       "clamped_by": "some-premise"}}
    rw = by(G.clamp(recs(), weak_witness))["b"]
    rp = by(G.clamp(recs(), weak_premise))["b"]
    check("2D: both owners clamp the importer identically (effective is the bound)",
          rw["effective_grade"] == rp["effective_grade"] == "vacuous")
    check("2D: but the owner's SELF grade survives the crossing — the two stay distinguishable",
          rw["delegated"]["grade"] == "vacuous" and rp["delegated"]["grade"] == "behavioral")
    check("2D: and the owner's own pin travels with it (not a dead end on the far side)",
          rp["delegated"]["clamped_by"] == "some-premise")
    check("2D: a bare grade string still works (a caller holding one number)",
          by(G.clamp(recs(), {("library", "w"): "vacuous"}))["b"]["effective_grade"] == "vacuous")

    # ---- Ζ·pi·unresolved: THREE states, not two ----
    # "No constraint recorded" and "constraint recorded as: none" render identically once
    # collapsed.  substrate inverted five zero-tolerance gates by reading an EMPTY baseline as
    # ABSENT; linux-sources' reader says "UNAVAILABLE at this version — NOT a claim it does not
    # exist", naming a boundary while imposing nothing.  Paperkit's own verdicts are already
    # tristate for this reason; the unfold needs the same.
    strong = {("library", "w"): {"grade": "behavioral", "effective_grade": "behavioral",
                                 "clamped_by": None}}
    u = by(G.clamp(recs()))["b"]
    ok = by(G.clamp(recs(), strong))["b"]
    check("3-state: an UNRESOLVED edge is named as a value, not left as silence",
          u["unresolved"] == ["library#w"])
    check("3-state: a RESOLVED edge that clamps nothing records NO unresolved entry",
          ok["unresolved"] == [])
    check("3-state: the two are distinguishable — silence would have merged them",
          u["unresolved"] != ok["unresolved"])

    # ---- Λ·pi·path: the prefix, not just the last step ----
    # An importer asking "distrust the witness, or chase the premise?" is answerable from the
    # chain and only sometimes from the final name (substrate: `take n` vs the last CF digit).
    deep = {("library", "w"): {"grade": "behavioral", "effective_grade": "vacuous",
                               "clamped_by": "lib-premise"}}
    rr = by(G.clamp(recs(), deep))
    check("path: the clamped claim carries the WHOLE chain, crossing the boundary",
          rr["b"]["clamp_path"] == ["library#w", "lib-premise"])
    check("path: and a dependent claim's chain is its own step PLUS the chain beneath it",
          rr["a"]["clamp_path"] == ["b", "library#w", "lib-premise"])
    check("path: an unclamped claim has an empty chain (nothing to follow)",
          by(G.clamp(recs(), strong))["a"]["clamp_path"] == [])

    # ---- Ζ·pi·unresolved is a FOURTH ORTHOGONAL AXIS, not a rung ----
    # The discipline is already stated twice in grade.py (corroboration, decision-coverage):
    # incompleteness is not a weaker rung, so it NEVER lowers a grade — it names the gap.
    # The case that forces the axis: `imported` ranks TOP, so a RESOLVED delegation to a healthy
    # owner clamps nothing — numerically identical to never having resolved it, and opposite in
    # meaning.  Only a separate axis tells them apart.
    strong2 = {("library", "w"): "behavioral"}
    t = by(G.clamp(recs()))["b"]
    rz = by(G.clamp(recs(), strong2))["b"]
    check("axis: an unresolved delegation does NOT lower the grade (incompleteness is not a rung)",
          t["grade"] == t["effective_grade"] == "imported" and t["clamp"] == 0)
    check("axis: resolution is a readable VALUE, not inferred from an empty list",
          (t["resolution"], rz["resolution"]) == ("truncated", "resolved"))
    # The pure form of the collision: an owner that is ITSELF `imported` clamps nothing, so the
    # resolved and truncated readings are IDENTICAL on every grade field and differ only here.
    chained = by(G.clamp(recs(), {("library", "w"): "imported"}))["b"]
    check("axis: resolved-imposing-nothing and never-resolved are identical on grade AND "
          "effective — only the axis separates them",
          (chained["grade"], chained["effective_grade"], chained["clamp"]) ==
          (t["grade"], t["effective_grade"], t["clamp"])
          and chained["resolution"] != t["resolution"])
    check("axis: resolving the rank-4 placeholder to a real grade DOES clamp (it is not a no-op)",
          rz["effective_grade"] == "behavioral" and rz["clamp"] == 1)
    check("axis: the ladder owns its rungs — resolution is NOT one of them",
          "truncated" not in G.RANK_C and "resolved" not in G.RANK_C
          and G.RESOLUTION_C == {"truncated": 0, "resolved": 1})

    # ---- Ζ·pi·interval: a truncation WIDENS A BRACKET instead of vanishing ----
    # effective_grade is the OPTIMISTIC endpoint (unresolved imposes nothing), which alone reads
    # a truncation as strength.  The pessimistic endpoint puts every unresolved premise at the
    # ladder floor.  The WIDTH is the cost of not having unfolded — same units, monotone, and
    # zero once every edge resolves.  Not a bound on the EDGE: an error bound on a step you
    # should not take licenses taking it (linux-sources retracted exactly that method).
    t2 = by(G.clamp(recs()))
    strong3 = {("library", "w"): {"grade": "behavioral", "effective_grade": "behavioral",
                                  "clamped_by": None}}
    weak3 = {("library", "w"): {"grade": "vacuous", "effective_grade": "vacuous",
                                "clamped_by": None}}
    s3, w3 = by(G.clamp(recs(), strong3)), by(G.clamp(recs(), weak3))
    check("interval: an unresolved edge WIDENS the bracket rather than vanishing",
          t2["b"]["interval_width"] > 0 and t2["b"]["effective_min"] == "broken")
    check("interval: resolving it collapses the bracket to a point",
          s3["b"]["interval_width"] == 0
          and s3["b"]["effective_min"] == s3["b"]["effective_max"])
    check("interval: the optimistic endpoint IS effective_grade (the reading we already had)",
          t2["b"]["effective_max"] == t2["b"]["effective_grade"])
    # THE SHAPE DISTINCTION — one collapsed number cannot carry it:
    check("interval: a weak WITNESS is low-and-NARROW; an unresolved edge is WIDE",
          (w3["b"]["effective_min"], w3["b"]["interval_width"]) == ("vacuous", 0)
          and t2["b"]["interval_width"] > 0)
    check("interval: the bracket propagates — a dependent claim widens too",
          t2["a"]["interval_width"] > 0)
    check("resolution is TRANSITIVE: resting on a truncated premise reads truncated",
          t2["a"]["resolution"] == "truncated" and s3["a"]["resolution"] == "resolved")

    # ---- Λ·pi·fold: each hop is INDEPENDENTLY verifiable ----
    # A chain that records its steps asks the reader to trust the computation behind it; one
    # that certifies them gives a per-hop obligation the reader can discharge alone.  The step
    # consults this hop's own data and its PREMISES' results — never anything above it.
    chain = [{"key": "a", "grade": "behavioral", "rests-on": ["b"]},
             {"key": "b", "grade": "existence", "rests-on": ["c"]},
             {"key": "c", "grade": "vacuous", "rests-on": []}]
    ch = by(G.clamp([dict(x) for x in chain]))
    check("fold: the base case (no premises) verifies against the claim's own grade",
          G.verify_hop(ch["c"], {})[0])
    check("fold: an interior hop verifies from its premise's RESULT alone",
          G.verify_hop(ch["b"], {"c": "vacuous"})[0]
          and G.verify_hop(ch["a"], {"b": "vacuous"})[0])
    forged = dict(ch["a"])
    forged["effective_grade"] = "behavioral"     # a link claiming more than its premise allows
    okf, expected, why = G.verify_hop(forged, {"b": "vacuous"})
    check("fold: a FORGED hop is caught locally, and the reason names the recomputation",
          okf is False and expected == "vacuous" and "record says behavioral" in why)
    # THE BOUND that makes a hop checkable — substrate's `r < b`, here monotonicity:
    check("fold: the bound is that a hop may only LOWER — never exceed its weakest premise",
          G.verify_hop({"key": "x", "grade": "behavioral",
                        "effective_grade": "behavioral"}, {"p": "vacuous"})[0] is False)
    check("fold: a delegation hop verifies from the OWNER's grade, nothing above it",
          G.verify_hop({"key": "y", "grade": "imported", "effective_grade": "vacuous",
                        "delegates_to": {"owner": "library", "claim": "w", "verb": "concept"}},
                       {}, {("library", "w"): "vacuous"})[0])

    # ---- Ζ·broken·offaxis: a cannot-run is not a refutation ----
    # `_grade_from_sens` emits `broken` on `not baseline`, and a baseline fails for two
    # categorically different reasons: the claim is FALSE, or the check could not be REACHED.
    # The resolver separates them (tristate); `grader.sensitivity` used to read `.passed` and
    # collapse both to False, so a check killed by its memory cap graded "repo is not green"
    # about a green repo.  Measured, twice, 2026-08-26.
    import grader as GR
    ref = G._grade_from_sens(False, [], reachable=True)
    unr = G._grade_from_sens(False, [], reachable=False)
    check("a REFUTED baseline says the repo is not green",
          ref["baseline"] == "refuted" and "not green" in ref["why"])
    check("an UNREACHABLE baseline says nothing was ESTABLISHED, and says so out loud",
          unr["baseline"] == "unreachable" and "not a statement that the repo is red"
          in unr["why"].lower())
    # δ: the ONE differing input, and the grade is deliberately UNCHANGED — the axis names the
    # gap, it never moves the rung (the discipline CORRO_C/DECISIONS_C/RESOLUTION_C state thrice)
    check("δ: reachable is the only difference, and the GRADE does not move",
          ref["grade"] == unr["grade"] == "broken" and ref["baseline"] != unr["baseline"])
    # and the sentinel stays FALSY, so every existing `if not baseline` in the tree still holds
    check("UNREACHABLE is falsy — every existing `if not baseline` is unaffected",
          not GR.UNREACHABLE and GR.UNREACHABLE is not False)

    # ---- Ζ·rests·unresolved: an UNGRADED premise is a truncation, not a free pass ----
    # A `rests-on` target with no record is SKIPPED by the clamp loop, and silence about that
    # reads identically to an edge that resolved to no constraint.  Two cases hide in the skip:
    # genuinely outside this argument, or in it and never graded (tier/nonmechanical exclusion,
    # or a grading that did not finish).  The second is an unfold that STOPPED — and letting it
    # pass silently leaves `behavioral` (rung 3 of 5) standing as if measured, which verify_hop's
    # monotonicity bound then certifies against.
    def _one(rests, **kw):
        rs = [{"key": "a", "grade": "behavioral", "rests-on": rests}]
        G.clamp(rs, **kw)
        return rs[0]

    ung = _one(["ghost"], keys={"a", "ghost"})
    check("an IN-ARGUMENT premise that was never graded reads as TRUNCATED",
          ung.get("resolution") == "truncated" and ung.get("unresolved") == ["ghost"])
    check("and the bracket WIDENS to the floor — the honest width of an unfold that stopped",
          ung.get("effective_min") == "broken" and ung.get("effective_max") == "behavioral")
    # δ: the SAME record, one key removed from the universe — now genuinely out of argument
    out = _one(["ghost"], keys={"a"})
    check("δ: the same edge, out of the argument, imposes nothing and is NOT a truncation",
          out.get("resolution") == "resolved" and not out.get("unresolved")
          and out.get("effective_min") == out.get("effective_max") == "behavioral")
    # and omitting the key universe reproduces the prior behaviour exactly
    check("no key set supplied ⇒ behaviour is unchanged (backward-compatible by construction)",
          _one(["ghost"]).get("resolution") == "resolved")

    print(f"CLAMP BOUNDARIES: {'PASS' if not _fails else 'FAIL'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
