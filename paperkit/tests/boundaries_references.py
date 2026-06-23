#!/usr/bin/env python3
"""Behavioral-boundary examples for reference projection — paperkit/project.py.

⟨P, F, δ⟩ per the boundary practice.  A claim's NON-ADJACENT grounding (`rests-on`) edge
projects as a direction-aware cross-reference (a connective IS a reference at distance 0);
an ADJACENT edge is carried by the connective, no reference; and a target reachable by a
LONGER grounding path is dropped as redundant — the transitive reduction, the `drop` rung
of the reference's materialization ladder (drop < cite < expound < figure).

    python3 paperkit/tests/boundaries_references.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import project as Pr  # noqa: E402

R, TR = Pr.references, Pr.transitive_reduction


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("reference projection behaviors\n")
    check("a non-adjacent grounding edge to ground already laid is a back-reference",
          R("x", ["y"], {"x": 2, "y": 0}) == " (grounded above in [@y])")
    check("a non-adjacent edge to ground laid below is a forward-reference (distance sign)",
          R("x", ["y"], {"x": 0, "y": 2}) == " (developed below at [@y])")
    check("an adjacent grounding edge is carried by the connective (no reference)",
          R("x", ["y"], {"x": 1, "y": 0}) == "")
    check("transitive reduction drops a target reachable by a longer path",
          TR({"x": ["y", "z"], "z": ["y"]})["x"] == ["z"])
    check("transitive reduction keeps a target with no other path",
          TR({"x": ["y", "z"], "z": []})["x"] == ["y", "z"])
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("a reference appears only for a NON-adjacent edge", "the target's prose-distance (1 → 2)",
         "adjacent (dist 1) → no reference", R("x", ["y"], {"x": 1, "y": 0}) == "",
         "non-adjacent (dist 2) → a reference", R("x", ["y"], {"x": 2, "y": 0}) != ""),
        ("the reference direction tracks the distance sign", "the target's side (below → above)",
         "target below → 'developed below'", "developed below" in R("x", ["y"], {"x": 0, "y": 2}),
         "target above → 'grounded above'", "grounded above" in R("x", ["y"], {"x": 2, "y": 0})),
        ("reduction drops a redundant edge iff a longer path exists", "the intermediate edge z→y",
         "z→y present → x→y dropped", TR({"x": ["y", "z"], "z": ["y"]})["x"] == ["z"],
         "z→y absent  → x→y kept", TR({"x": ["y", "z"], "z": []})["x"] == ["y", "z"]),
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
    print("BOUNDARIES: PASS (5 behaviors, 3 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
