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
