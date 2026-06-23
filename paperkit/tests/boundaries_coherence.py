#!/usr/bin/env python3
"""Behavioral-boundary examples for coherence (∂²) — paperkit/coherence.py.

⟨P, F, δ⟩ per the boundary practice.  ∂² re-reads Δ records and reports two residuals:
STRUCTURE (where a claim's `from` and `rests-on` edges diverge) and SENSITIVITY (where
name-distinct witnesses collapse to one sensitivity signature).  Bounds: a coherent
record set shows zero residual, an incoherent one surfaces it, and the minimum delta is
a single diverging edge / a single shared signature.

    python3 paperkit/tests/boundaries_coherence.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import coherence as C  # noqa: E402


def rec(key, frm=(), rests=(), grade="behavioral", tests=()):
    return {"key": key, "from": list(frm), "rests-on": list(rests),
            "grade": grade, "tests": list(tests), "cited": True}


COHERENT = [rec("a"), rec("b", frm=["a"], rests=["a"])]          # from == rests-on
DIVERGED = [rec("a"), rec("b", frm=["a"], rests=["x"])]          # from ≠ rests-on
DISTINCT = [rec("a", tests=["x.py"]), rec("b", tests=["y.py"])]  # different sensitivity
COLLAPSED = [rec("a", tests=["w.py"]), rec("b", tests=["w.py"])]  # same sensitivity


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("∂² residual behaviors\n")
    check("structure residual is 0 when from == rests-on",
          C.structure_residual(COHERENT)["divergent_claims"] == 0)
    check("structure residual flags a from/rests-on mismatch",
          C.structure_residual(DIVERGED)["divergent_claims"] == 1)
    check("sensitivity: distinct tests → 2 signatures, 0 collapse",
          C.sensitivity_residual(DISTINCT)["signatures"] == 2 and C.sensitivity_residual(DISTINCT)["collapse"] == 0)
    check("sensitivity: shared tests → 1 signature, 1 collapse (name-distinct, sensitivity-same)",
          C.sensitivity_residual(COLLAPSED)["signatures"] == 1 and C.sensitivity_residual(COLLAPSED)["collapse"] == 1)
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("structure residual tracks from/rests-on agreement",
         "the second claim's rests-on edge (a → x)",
         "from == rests-on → 0", C.structure_residual(COHERENT)["divergent_claims"] == 0,
         "from ≠ rests-on → 1", C.structure_residual(DIVERGED)["divergent_claims"] == 1),
        ("sensitivity collapse tracks signature sharing",
         "the second witness's tests (y.py → w.py)",
         "distinct → 0 collapse", C.sensitivity_residual(DISTINCT)["collapse"] == 0,
         "shared   → 1 collapse", C.sensitivity_residual(COLLAPSED)["collapse"] == 1),
    ]
    for name, axis, p_lbl, p_ok, f_lbl, f_ok in pairs:
        ok = p_ok and f_ok
        fails.append(name) if not ok else None
        print(f"  {'ok ' if ok else 'XX '}{name}")
        print(f"      P (pass side): {p_lbl}")
        print(f"      F (flag side): {f_lbl}")
        print(f"      δ (min delta): {axis}\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (4 behaviors, 2 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
