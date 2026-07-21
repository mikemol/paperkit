#!/usr/bin/env python3
"""Ζ·surface·kind — the boundary between what a grade MEASURED and what it merely read.

A grade is only as complete as the surface it was measured over.  `indeterminate` was carrying
two incompatible meanings — "every input was corrupted and none flipped it" (a falsifiability
verdict) and "an input this claim depends on was never corrupted at all" (no verdict; we did not
look).  The second is the sentinel move one level down: *not measurable from here* is not *not
falsifiable*, exactly as *no such claim* is not *broken*.

Three cases found independently — a downstream consumer's `.json` dataset, a downstream
consumer's tool outside the project, and this repo's own `tools/grade.bzl` — are ONE set
difference: `reads \\ mutable`.  Excluded by SUFFIX or by LOCATION, the epistemic position is
identical.  So the instrument is that difference, reported as an ORTHOGONAL AXIS (like
content_sensitive and corroboration), never as a rung.

    python3 paperkit/tests/boundaries_surface.py     # exit 0 = the axis measures what it says
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))

import grader  # noqa: E402
import layout  # noqa: E402


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Ζ·surface·kind — measured vs merely read\n")
    # The gap-suffix is DELIBERATELY not a real one.  A first version of this check used `.json`
    # — and then `.json` was admitted to MUTABLE_SUFFIXES the next day, so the fixture's premise
    # evaporated and the check went red.  "Synthetic fixture, not the live instance" was the right
    # instinct applied to the wrong half: the FILES were synthetic, the PROPERTY under test was
    # borrowed from the real suffix set.  A test of a mechanism must not depend on a policy value
    # that the mechanism exists to help change.  The assert below is the guard: if this suffix ever
    # becomes real, this says so loudly instead of silently passing on a hollow premise.
    GAP = ".not-a-paperkit-input"
    assert GAP not in layout.MUTABLE_SUFFIXES, "the fixture's gap-suffix became a real input"

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "proj").mkdir()
        (root / "proj" / "doc.md").write_text("x\n")           # mutable     — measured
        (root / "proj" / f"data{GAP}").write_text("{}\n")      # NOT mutable — a gap
        (root / "proj" / "__pycache__").mkdir()
        (root / "proj" / "__pycache__" / "m.cpython-313.pyc").write_bytes(b"\x00")
        reads = ["proj/doc.md", f"proj/data{GAP}", "proj/__pycache__/m.cpython-313.pyc"]
        un = grader.unmeasured_reads(reads, root)

        print("⟨the axis⟩\n")
        check("a file the claim READS but the sweep CANNOT MUTATE is reported",
              f"proj/data{GAP}" in un)
        check("a file that IS mutable is not reported (it was measured)",
              "proj/doc.md" not in un)
        check("a DERIVED artifact is not reported — its source is in the surface",
              not any("__pycache__" in u for u in un))
        check("exactly the gap, nothing else", un == [f"proj/data{GAP}"])

        print("\n⟨it is an axis, not a rung⟩\n")
        # The whole point of the sentinel lesson: incompleteness is not a weaker grade.  If this
        # ever became a rung, `grade.below()` would start FAILING claims for being unmeasured —
        # punishing the claim for the instrument's blind spot.
        import grade
        check("`unmeasured` is not a rung on the ladder (incompleteness is not a grade)",
              "unmeasured" not in grade.RANK_C and "unmeasured" not in grade.STRENGTH)
        check("...so no adequacy floor can fail a claim for it",
              all("unmeasured" not in grade.below(f) for f in grade.ORDER))

        print("\n⟨Φ·degrade⟩\n")
        check("no trace ⇒ no claim either way (never a false 'nothing is unmeasured')",
              grader.unmeasured_reads(None, root) == [] and
              grader.unmeasured_reads(reads, None) == [])

        print("\n⟨P, F, δ⟩ minimum-delta pair\n")
        # δ is one entry in MUTABLE_SUFFIXES: the gap exists BECAUSE a suffix is absent, and
        # closing it is a deliberate, measurable act rather than a silent proxy decision.
        was = set(layout.MUTABLE_SUFFIXES)
        try:
            layout.MUTABLE_SUFFIXES.add(GAP)
            closed = grader.unmeasured_reads(reads, root)
        finally:
            layout.MUTABLE_SUFFIXES.clear()
            layout.MUTABLE_SUFFIXES.update(was)
        ok = un == [f"proj/data{GAP}"] and closed == []
        fails.append("surface-delta") if not ok else None
        print(f"  {'ok ' if ok else 'XX '}admitting the suffix CLOSES the gap, and the axis says so")
        print(f"      P (as shipped): data{GAP} is read, not mutable → reported as unmeasured")
        print("      F (suffix added): the same file becomes measurable → the gap is empty")
        print("      δ (min delta): one entry in MUTABLE_SUFFIXES\n")

    if fails:
        print(f"SURFACE: FAIL ({len(fails)})")
        return 1
    print("SURFACE: PASS (7 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
