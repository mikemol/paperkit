#!/usr/bin/env python3
"""Behavioral-boundary examples for Ε·agree·grade — the CORROBORATION axis of the Δ grade.

⟨P, F, δ⟩ per the boundary practice.  A grade is the PAIR (falsifiability, corroboration),
NOT one collapsed scalar.  The grade ("behavioral" …) asks whether a mutation flips the
check; corroboration ("single" | "independent") asks whether the verdict is confirmed by ≥2
TEXTUALLY DISTINCT producers (agree:).  The axes are ORTHOGONAL — a lone behavioral witness
and a behaviorally-agreeing oracle share a GRADE but differ in corroboration.

    python3 paperkit/tests/boundaries_corroboration.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture_delta import discriminate  # noqa: E402
from _fixture_model import entry  # noqa: E402


def grade(check):
    _, out = discriminate([entry("w", claim="c", check=check)], "--all", "--json",
                          assets={"a.txt": "CANON\n"})
    return json.loads(out)[0]


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Ε·agree·grade — the corroboration axis (orthogonal to the falsifiability grade)\n")
    lone = grade("cmd:grep -q CANON a.txt")            # one witness, behavioral
    indep = grade("agree:cat a.txt ||| printf CANON")  # two distinct producers, behavioral
    trivial = grade("agree:printf CANON ||| printf CANON")   # identical producers
    disagree = grade("agree:cat a.txt ||| printf NOPE")      # producers disagree

    check("a lone witness is behavioral but NOT independently corroborated",
          lone["grade"] == "behavioral" and lone.get("corroboration", "single") == "single")
    check("agree: of ≥2 distinct concurring producers is independently corroborated",
          indep["grade"] == "behavioral" and indep["corroboration"] == "independent")
    check("ORTHOGONAL — same falsifiability grade, different corroboration (not one scalar)",
          lone["grade"] == indep["grade"] and lone.get("corroboration", "single") != indep["corroboration"])
    check("identical producers concur TRIVIALLY — single, not independent",
          trivial.get("corroboration", "single") == "single")
    check("disagreeing producers do not corroborate — broken, no independence claimed",
          disagree["grade"] == "broken" and disagree.get("corroboration", "single") == "single")

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    P = indep.get("corroboration")
    F = grade("agree:cat a.txt ||| cat a.txt").get("corroboration", "single")
    ok = P == "independent" and F == "single"
    fails.append("distinct-producer-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}an independent oracle vs a copy flips corroboration")
    print("      P (independent): agree:cat a.txt ||| printf CANON  — a distinct oracle confirms it")
    print("      F (single):      agree:cat a.txt ||| cat a.txt     — the second producer is a copy")
    print("      δ (min delta): the second producer is textually distinct (independent), not a duplicate\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (5 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
