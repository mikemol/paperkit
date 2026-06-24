#!/usr/bin/env python3
"""Behavioral-boundary examples for coherence (∂²) — paperkit/coherence.py.

⟨P, F, δ⟩ per the boundary practice.  ∂² re-reads Δ records and reports three residuals:
STRUCTURE (where a claim's `from` and `rests-on` edges diverge), SENSITIVITY (where
name-distinct witnesses collapse to one sensitivity signature), and GROUNDING (where a
declared `rests-on` edge is disjoint from its premise's measured engine fingerprint).
Bounds: a coherent record set shows zero residual, an incoherent one surfaces it, and the
minimum delta is a single diverging edge / a single shared signature / a single disjoint
grounding edge.

    python3 paperkit/tests/boundaries_coherence.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import coherence as C  # noqa: E402


def rec(key, frm=(), rests=(), grade="behavioral", tests=(), section=None):
    return {"key": key, "from": list(frm), "rests-on": list(rests),
            "grade": grade, "tests": list(tests), "cited": True, "section": section}


# structure: a grounding edge to the immediate prose predecessor is CARRIED; to a
# non-adjacent claim it is a LONG edge owed a projected reference.
CARRIED = [rec("a", section="s"), rec("b", section="s", frm=["a"], rests=["a"])]   # b grounds on its predecessor
LONG = [rec("a", section="s"), rec("b", section="s", frm=["a"]),
        rec("c", section="s", frm=["b"], rests=["a"])]                              # c grounds on a, two back
DISTINCT = [rec("a", tests=["x.py"]), rec("b", tests=["y.py"])]  # different sensitivity
COLLAPSED = [rec("a", tests=["w.py"]), rec("b", tests=["w.py"])]  # same sensitivity
# grounding: b rests-on a; engine fingerprints overlap / disjoint-genuine / disjoint-rhetorical
GROUNDED = [rec("a", tests=["paperkit/gate.py::resolves"]),
            rec("b", rests=["a"], tests=["paperkit/gate.py::resolves", "paperkit/project.py::weave"])]
GENUINE = [rec("a", tests=["paperkit/gate.py::resolves"]),       # b tests engine capability, just not a's
           rec("b", rests=["a"], tests=["paperkit/rhetoric.py::kind_of"])]
RHETORICAL = [rec("a", tests=["paperkit/gate.py::resolves"]),    # b tests NO engine capability (empty)
              rec("b", rests=["a"], tests=["checks/claims.py::b"])]
SCAFFOLD = [rec("a", tests=["checks/claims.py::a"]),             # a measures no engine capability — no edge
            rec("b", rests=["a"], tests=["checks/claims.py::b"])]


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("∂² residual behaviors\n")
    check("structure: a grounding edge to the immediate predecessor is CARRIED (0 owed)",
          C.structure_residual(CARRIED)["carried"] == 1 and C.structure_residual(CARRIED)["owed"] == 0)
    check("structure: a grounding edge two-back is a LONG edge owed a reference",
          C.structure_residual(LONG)["owed"] == 1 and C.structure_residual(LONG)["carried"] == 0)
    check("a long edge is un-acknowledged by default (advisory)",
          C.structure_residual(LONG)["undischarged"] == 1)
    check("a `link` footnote discharges the long edge (still drawn, not flagged)",
          C.structure_residual(LONG, discharged={"c"})["undischarged"] == 0
          and C.structure_residual(LONG, discharged={"c"})["owed"] == 1)
    check("sensitivity: distinct tests → 2 signatures, 0 collapse",
          C.sensitivity_residual(DISTINCT)["signatures"] == 2 and C.sensitivity_residual(DISTINCT)["collapse"] == 0)
    check("sensitivity: shared tests → 1 signature, 1 collapse (name-distinct, sensitivity-same)",
          C.sensitivity_residual(COLLAPSED)["signatures"] == 1 and C.sensitivity_residual(COLLAPSED)["collapse"] == 1)
    check("grounding: overlapping engine fingerprint → edge reflected, 0 residual",
          C.grounding_residual(GROUNDED)["reflected"] == 1 and C.grounding_residual(GROUNDED)["undischarged"] == 0)
    check("grounding: disjoint with a NON-empty fingerprint → genuine undischarged miss",
          C.grounding_residual(GENUINE)["undischarged"] == 1)
    check("grounding: an empty-fingerprint claim is vacuously disjoint → rhetorical, auto-discharged",
          C.grounding_residual(RHETORICAL)["rhetorical"] == 1 and C.grounding_residual(RHETORICAL)["undischarged"] == 0)
    check("grounding: a `link` discharges a genuine miss",
          C.grounding_residual(GENUINE, discharged={"b"})["undischarged"] == 0)
    check("grounding: shared scaffolding is not engine grounding (no edge counted)",
          C.grounding_residual(SCAFFOLD)["grounding_edges"] == 0)
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("structure residual tracks the grounding edge's prose distance",
         "the dependent claim's grounding target (predecessor → two-back)",
         "adjacent → 0 owed", C.structure_residual(CARRIED)["owed"] == 0,
         "non-adjacent → 1 owed", C.structure_residual(LONG)["owed"] == 1),
        ("sensitivity collapse tracks signature sharing",
         "the second witness's tests (y.py → w.py)",
         "distinct → 0 collapse", C.sensitivity_residual(DISTINCT)["collapse"] == 0,
         "shared   → 1 collapse", C.sensitivity_residual(COLLAPSED)["collapse"] == 1),
        ("a `link` footnote discharges a long edge (advisory, not a gate)",
         "acknowledging claim c's link",
         "un-acknowledged → 1", C.structure_residual(LONG)["undischarged"] == 1,
         "footnoted → 0", C.structure_residual(LONG, discharged={"c"})["undischarged"] == 0),
        ("grounding: a disjoint edge is residual only when UN-explained",
         "why the edge is disjoint (empty fingerprint / link / neither)",
         "rhetorical OR linked → 0 residual",
         C.grounding_residual(RHETORICAL)["undischarged"] == 0
         and C.grounding_residual(GENUINE, discharged={"b"})["undischarged"] == 0,
         "genuine + unlinked → 1 residual", C.grounding_residual(GENUINE)["undischarged"] == 1),
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
    print("BOUNDARIES: PASS (11 behaviors, 4 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
