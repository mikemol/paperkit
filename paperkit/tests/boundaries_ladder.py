#!/usr/bin/env python3
"""Ζ·ladder — the GRADE LADDER's boundary: one owner, and a floor that fails CLOSED.

grade.py owns the rungs (RANK_C).  Every consumer that orders, displays, or gates on them must
DERIVE from it, because a re-declared ladder drifts in two specific and opposite ways:

  * a DISPLAY order that omits a rung silently under-counts its own population.  report/gen.py's
    summary listed five of six and read "80 cited claims — self-grade: 79 behavioral"; the 80th
    was a `concept:` import and simply vanished from the total it was being counted into.
  * an adequacy gate written as a BLACKLIST of failing grades FAILS OPEN.  Every rung added to the
    ladder after the list was written is absent from it, so it passes by default.  That is the one
    direction a gate must never fail, and it is the direction a hand-maintained list always fails.

So the ladder exposes `rungs()` (display order) and `below(floor)` (the failing set), and this
checks that the consumers ask rather than re-list — behaviorally for the ladder's own properties,
by source for the ones that are Starlark or a separate process.

    python3 paperkit/tests/boundaries_ladder.py     # exit 0 = every consumer derives from grade.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
ROOT = ENGINE.parent
sys.path.insert(0, str(ENGINE))

import grade  # noqa: E402

# Every consumer that orders/displays/gates on the ladder, and the file it lives in.
CONSUMERS = {
    "report/gen.py": ROOT / "report" / "gen.py",
    "report/figure.py": ROOT / "report" / "figure.py",
    "paperkit/discriminate.py": ENGINE / "discriminate.py",
    "tools/grade.bzl": ROOT / "tools" / "grade.bzl",
    "tools/verdict.py": ROOT / "tools" / "verdict.py",
}
# A rung name appearing in a LIST or comma-run is a re-declaration; one appearing in a comment or
# a single-key lookup is not.  Match runs of >=3 quoted-or-bare rung names — the shape of a copy.
RUNGS = sorted(grade.RANK_C)
_RUN = re.compile(r"(?:[\"'`]?(?:" + "|".join(RUNGS) + r")[\"'`]?\s*[,:]\s*){3,}")


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Ζ·ladder — the grade ladder's boundary\n")
    print("⟨one owner⟩\n")
    check(f"grade.RANK_C totally orders the {len(RUNGS)} rungs (distinct ranks, no ties)",
          len(set(grade.RANK_C.values())) == len(grade.RANK_C))
    check("rungs() is that order, descending — the display order, derived",
          grade.rungs() == sorted(grade.RANK_C, key=grade.RANK_C.get, reverse=True))
    check("every --min-strength floor is a real rung (the knob cannot name what the ladder cannot rank)",
          set(grade.ORDER) <= set(grade.RANK_C))

    print("\n⟨the floor fails CLOSED⟩\n")
    # below() must be a function of the ORDER, not a list: for every floor, exactly the lower rungs.
    ok = all(set(grade.below(f)) == {g for g in grade.RANK_C if grade.RANK_C[g] < grade.RANK_C[f]}
             for f in grade.RANK_C)
    check("below(floor) is exactly the rungs ranked under it, for EVERY floor", ok)
    check("`imported` clears the behavioral floor (a delegation is not a weak grade)",
          "imported" not in grade.below("behavioral"))
    check("`indeterminate` does NOT clear it (the grade a missing delegation arm produces)",
          "indeterminate" in grade.below("behavioral"))
    # the fail-open property, stated positively: a rung inserted BELOW the floor is caught by
    # derivation, and would have been missed by any list written before it existed.
    was = dict(grade.RANK_C)
    try:
        grade.RANK_C["hypothetical"] = -2
        caught = "hypothetical" in grade.below("behavioral")
    finally:
        grade.RANK_C.clear()
        grade.RANK_C.update(was)
    check("a NEW sub-floor rung is failed the moment it exists (a blacklist would pass it)", caught)

    print("\n⟨every consumer derives⟩\n")
    for name, path in CONSUMERS.items():
        src = path.read_text()
        copies = _RUN.findall(src)
        check(f"{name} re-declares no rung list" + (f" (found {copies[:1]})" if copies else ""),
              not copies)
    check("tools/verdict.py derives an adequacy floor via grade.below (not a literal bad-set)",
          "grade.below(" in (ROOT / "tools" / "verdict.py").read_text())
    gbzl = (ROOT / "tools" / "grade.bzl").read_text()
    check("tools/grade.bzl names a FLOOR (below:<rung>) and stages the ladder as an input",
          "below:" in gbzl and "//paperkit:grade.py" in gbzl)

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    # F = the blacklist as it was actually written, and the rung it was actually blind to.
    literal = ",".join(["vacuous", "existence", "indeterminate", "broken"])   # the list as written
    blind = [g for g in grade.below("behavioral") if g not in literal.split(",")]
    caught = ("below:behavioral" in gbzl and literal not in gbzl)
    fails.append("ladder-delta") if not caught else None
    print(f"  {'ok ' if caught else 'XX '}re-hardcoding the adequacy blacklist is CAUGHT")
    print(f"      P (intact):  grade.bzl names `below:behavioral` → the failing set is derived")
    print(f"      F (literal): `{literal}` → any rung added later passes adequacy unjudged"
          + (f"; ALREADY blind to {blind}" if blind else " (not yet blind — no rung added since)"))
    print(f"      δ (min delta): one argument, a floor NAME → a frozen list of failing grades\n")

    if fails:
        print(f"LADDER: FAIL ({len(fails)} consumers drifted from grade.py)")
        return 1
    print(f"LADDER: PASS ({len(RUNGS)} rungs, {len(CONSUMERS)} consumers, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
