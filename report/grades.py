#!/usr/bin/env python3
# Ρ·report·grades — rpt-delta's DISCRIMINATING witness: Δ actually GRADES, it does not label.
#
# ⚑ WHY NOT `fresh:delta.md`.  rpt-delta claims "Δ grades each cited claim's check by whether it
# can actually fail".  rpt-delta-out claims the emitted table carries every grade with why-this
# and why-not-higher/lower.  The SECOND is a property of the FILE, so `fresh:delta.md` is its
# right witness.  The FIRST is a property of the GRADING, and sharing the freshness check would
# put two claims on one witness — the collapse this project was split to fix.
#
# The distinction has teeth: delta_md() renders whatever grades it is given.  If the grader
# regressed to stamping one constant on every claim, the table would still regenerate, still
# match its committed copy, and `fresh:delta.md` would still be green — while rpt-delta's claim
# ("grades by whether it can actually FAIL") had become false.  A uniform label is not a grade.
#
# What this asserts, each independently falsifiable:
#   1. grading REACHED every cited claim (no unmeasured records)
#   2. the grade is DISCRIMINATING — more than one distinct value over the corpus, so the ladder
#      is being used rather than a constant stamped
#   3. every grade is a rung on the DECLARED ladder, not an ad-hoc string
#   4. every record carries its justification (why / not_higher / not_lower) — the evidence that
#      the grade was reasoned per claim rather than defaulted
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen  # noqa: E402
from paperkit.grade import RANK_C  # noqa: E402  — the declared ladder, not a local copy


def main() -> int:
    try:
        records = gen._delta("paper")
    except (gen.CannotGrade, subprocess.SubprocessError) as e:
        # ⚑ NOT a refutation — see grounding.py.  Since Γ, _delta RAISES rather than returning [],
        # so cannot-run and graded-nothing are distinguishable.  Exit 3 = resolver._CANNOT_RUN.
        print(f"could not grade the paper: {e}\nNot evaluated; this is NOT a refutation of "
              "rpt-delta.", file=sys.stderr)
        return 3

    if not records:
        # The grader RAN and graded nothing — "Δ grades each cited claim" over an empty set is
        # vacuous, not witnessed.
        print("discriminate --json paper graded NO claims — rpt-delta's 'each cited claim' has "
              "no instances, so the claim is vacuous rather than witnessed", file=sys.stderr)
        return 1

    unmeasured = [r["key"] for r in records if not r.get("grade")]
    if unmeasured:
        print(f"{len(unmeasured)} cited claim(s) carry NO grade "
              f"({', '.join(sorted(unmeasured)[:5])}…) — Δ did not reach them, so rpt-delta's "
              "'each cited claim' is not witnessed", file=sys.stderr)
        return 1

    grades = {r["grade"] for r in records}
    off_ladder = sorted(g for g in grades if g not in RANK_C)
    if off_ladder:
        print(f"grade(s) not on the declared ladder: {', '.join(off_ladder)} — "
              f"known rungs are {', '.join(RANK_C)}", file=sys.stderr)
        return 1

    if len(grades) < 2:
        only = next(iter(grades))
        print(f"every one of the {len(records)} cited claims graded `{only}` — a constant is a "
              "LABEL, not a grade by whether the check can actually fail.  Either the corpus is "
              "genuinely uniform (then rpt-delta needs a stronger witness) or the grader "
              "regressed to stamping.", file=sys.stderr)
        return 1

    unjustified = [r["key"] for r in records
                   if not (r.get("why") and r.get("not_higher") and r.get("not_lower"))]
    if unjustified:
        print(f"{len(unjustified)} claim(s) carry a grade with no why/not_higher/not_lower "
              f"({', '.join(sorted(unjustified)[:5])}…) — an unjustified grade was defaulted, "
              "not reasoned", file=sys.stderr)
        return 1

    dist = ", ".join(f"{g}={sum(1 for r in records if r['grade'] == g)}"
                     for g in sorted(grades, key=lambda g: RANK_C[g]))
    print(f"Δ graded {len(records)} cited claims across {len(grades)} rungs ({dist}); "
          "every grade is on the declared ladder and carries why / not-higher / not-lower")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
