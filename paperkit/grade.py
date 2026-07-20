#!/usr/bin/env python3
"""paperkit.grade — the GRADE LADDER + interpretation (Μ·grade).

The PURE half of the Δ grader: the falsifiability rungs, the clamp/strength/corroboration
orders, and how a measured flip-set becomes a grade.  Separated from grader.py (the SWEEP —
sandbox, AST mutation, sensitivity) so the CALCULATION (the expensive measurement) and the
INTERPRETATION (this cheap reading over it) are distinct modules — Ζ·calc·interp in code.

A LEAF: pure data + one pure function, no engine imports.  So a READING of a grade
(tools/read_grade.py) imports the ladder, not the sweep; and a claim about the ladder
exercises only this, not the whole grader.
"""
from __future__ import annotations

from pathlib import Path

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


# Ζ·ladder — the two DERIVATIONS every consumer needs, so none re-declares the rungs.  A ladder
# re-listed downstream drifts silently and in the WORST direction: a display order that omits a
# rung SILENTLY DROPS claims from its own total (report/gen.py counted 79 of 80), and an adequacy
# gate written as a BLACKLIST of failing grades PASSES any rung added after it was written — the
# gate fails open, which is the one direction a gate must never fail.  Both are stated here as a
# function of RANK_C instead, so a new rung reaches every consumer by being added ONCE, above.

def rungs(descending: bool = True) -> list:
    """Every grade the ladder defines, in rank order — the display order for any summary.  Listing
    rungs by hand is how a report comes to omit one and quietly under-count its own population."""
    return sorted(RANK_C, key=lambda g: RANK_C[g], reverse=descending)


def below(floor: str) -> list:
    """The grades that FAIL a `floor` — derived, so the adequacy gate fails CLOSED.  Stated as a
    blacklist it would admit every future rung by default; stated as `rank < rank(floor)` a new
    rung is judged the moment it exists.  `floor` must be a defined rung (KeyError if it is not —
    a typo'd floor must not silently grade everything green)."""
    return [g for g in rungs(descending=False) if RANK_C[g] < RANK_C[floor]]


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


def mark_content_sensitive(records: list, content: set) -> list:
    """Mark each behavioral check content_sensitive iff a flipped test file is the document's
    OWN content (bib/rubric/out), not merely config/engine: a behavioral check sensitive only
    to config or the engine can-fail by CRASH but does not test the document's content.  A pure
    reading over the grade records + the document's content-file names."""
    for r in records:
        if r["grade"] == "behavioral":
            r["content_sensitive"] = any(Path(t).name in content for t in r["tests"])
    return records


def clamp(records: list) -> list:
    """Effective grade — clamp by entailment: a claim is no better grounded than the weakest
    premise it (transitively) depends on along rests-on.  Annotates each record with
    effective_grade, clamp (rungs dropped from the self-contained grade), and clamped_by (the
    premise that pins it).  A pure reading over the grade records + the RANK ladder."""
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
    return records
