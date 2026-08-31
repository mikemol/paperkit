#!/usr/bin/env python3
"""Behavioral-boundary examples for Ε·agree·grade — the CORROBORATION axis of the Δ grade.

⟨P, F, δ⟩ per the boundary practice.  A grade is the PAIR (falsifiability, corroboration),
NOT one collapsed scalar.  The grade ("behavioral" …) asks whether a mutation flips the
check; corroboration ("single" | "correlated" | "distinct" | "independent") asks whether the verdict is confirmed by ≥2
TEXTUALLY DISTINCT producers (agree:).  The axes are ORTHOGONAL — a lone behavioral witness
and a behaviorally-agreeing oracle share a GRADE but differ in corroboration.

    python3 paperkit/tests/boundaries_corroboration.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture_delta import discriminate
from _fixture_model import entry


def grade(check):
    _, out = discriminate([entry("w", claim="c", check=check)], "--all", "--json",
                          assets={"a.txt": "CANON\n"})
    return json.loads(out)[0]


def main() -> int:
    fails = []

    ran = []

    def check(desc, cond):
        # Λ·guard-must-not-copy — `ran` COUNTS the arms.  The summary line used to restate a
        # number authored beside the set it describes, and every one of the 26 suites carrying
        # such a line UNDERSTATED it (24 mismatched, none overstated): arms were added and the
        # literal never moved, so it tracked the suite's authoring history rather than its
        # content — and would have read a SHRINKING suite as an unchanged one.
        ran.append(desc)
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Ε·agree·grade — the corroboration axis (orthogonal to the falsifiability grade)\n")
    lone = grade("cmd:grep -q CANON a.txt")            # one witness, behavioral
    indep = grade("agree:cat a.txt ||| printf CANON")  # two distinct producers, behavioral
    trivial = grade("agree:printf CANON ||| printf CANON")   # identical producers
    disagree = grade("agree:cat a.txt ||| printf NOPE")      # producers disagree

    check("a lone witness is behavioral but NOT independently corroborated",
          lone["grade"] == "behavioral" and lone.get("corroboration", "single") == "single")
    # Ζ·corro·honest — the value names what was MEASURED (the producer strings differ), not
    # what was hoped (they share no upstream).  `independent` is now reserved for a certified
    # disjoint read footprint, which nothing yet computes — so it must be UNREACHABLE here.
    # Ε·corro·phi landed, so `independent` is now REACHABLE — and earned by measurement rather
    # than by the producer strings differing.  These two producers read disjoint inputs.
    check("agree: of producers with DISJOINT footprints is independent — certified, not assumed",
          indep["grade"] == "behavioral" and indep["corroboration"] == "independent")
    check("ORTHOGONAL — same falsifiability grade, different corroboration (not one scalar)",
          lone["grade"] == indep["grade"] and lone.get("corroboration", "single") != indep["corroboration"])
    check("identical producers concur TRIVIALLY — single; string-distinctness is a NECESSARY\n           condition and this is the case it correctly rejects",
          trivial.get("corroboration", "single") == "single")
    check("disagreeing producers do not corroborate — broken, no corroboration claimed",
          disagree["grade"] == "broken" and disagree.get("corroboration", "single") == "single")

    # ---- Ε·corro·phi: the MEASURED verdict, from per-producer read footprints ----
    # `distinct` says the producer strings differ.  Their FOOTPRINTS say whether they share an
    # input — disjoint reads provably share no ground (a certificate, not a heuristic), and an
    # overlap NAMES the files a bug could hide in.  Φ·degrade leaves `distinct` standing: an
    # unmeasurable sharing must not read as a measured one, in either direction.
    import shutil as _sh
    import tempfile as _tf

    import resolver as _R
    _d = Path(_tf.mkdtemp())
    try:
        (_d / "a.txt").write_text("CANON\n")
        # two producers reading the SAME file — correlated, and the file is named
        v = _R.corroboration_of("agree:cat a.txt ||| cat a.txt && true", _d, {})
        check("two producers reading one file are CORRELATED, and the shared read is NAMED",
              v is not None and v[0] == "correlated" and "a.txt" in v[1])
        # δ: the second producer reads NOTHING — the only change, and the verdict flips
        v2 = _R.corroboration_of("agree:cat a.txt ||| printf CANON", _d, {})
        check("δ: a producer that reads nothing shared ⇒ INDEPENDENT, certified not assumed",
              v2 is not None and v2[0] == "independent" and v2[1] == [])
        check("a non-agree check has no producers to partition ⇒ None, never a verdict",
              _R.corroboration_of("cmd:true", _d, {}) is None)
    finally:
        _sh.rmtree(_d, ignore_errors=True)

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    P = indep.get("corroboration")
    F = grade("agree:cat a.txt ||| cat a.txt").get("corroboration", "single")
    ok = P == "independent" and F == "single"
    fails.append("distinct-producer-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}an independent oracle vs a copy flips corroboration")
    print("      P (independent): agree:cat a.txt ||| printf CANON  — disjoint footprints — MEASURED")
    print("      F (single):      agree:cat a.txt ||| cat a.txt     — the second producer is a copy")
    print("      δ (min delta): the second producer shares no read with the first\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    bad = len([b for b in ran if not b])
    if bad:
        print(f"BOUNDARIES: FAIL ({bad} of {len(ran)} behaviors drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
