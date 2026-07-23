#!/usr/bin/env python3
"""Ζ·prove·degrade — the prove face's boundary: a certificate is NEVER emitted unmeasured.

A concept witness's --prove face emits ⟨verdict, sensitivity fingerprint⟩.  The degraded arm
of that measurement is the dangerous one: an unreachable/broken engine that still produced a
record would emit `sens: []` — an ABSENT measurement wearing the exact shape of an
INSENSITIVE one (the twice-bitten silent-degradation class, on the one path the grid canary
does not cover).  The contract pinned here, adopted from the downstream consumer's
certificate() (their fingerprint-null-plus-why discipline — the audit's reverse finding):

  P — the same entry point runs green against the REAL engine (the sound path exists);
  F — with the engine UNREACHABLE, --prove exits nonzero and emits NO record at all:
      a fingerprint of [] is only ever a MEASURED result;
  δ — one environment variable (PAPERKIT_ENGINE), presence → absence.

    python3 paperkit/tests/boundaries_prove.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Ζ·prove·degrade — a certificate is never emitted unmeasured\n")

    # P — the sound path: the same entry point, real engine, cheap verdict mode (the prove
    # mode's full def-sweep is gated separately as the library's __dcalc in //:hook — not
    # re-swept here; one oracle, two gates would drift).
    p = subprocess.run([sys.executable, str(LIB / "concepts.py"), "claim-is-record"],
                       cwd=LIB, capture_output=True, text=True)
    check("P: the entry point runs a concept green against the REAL engine", p.returncode == 0)

    # F — the degraded arm: an engine that is not there.  The prove face must fail LOUD with
    # NO record — never a certificate whose empty fingerprint reads as "nothing flips it".
    with tempfile.TemporaryDirectory() as d:
        env = {**os.environ, "PAPERKIT_ENGINE": d}
        f = subprocess.run([sys.executable, str(LIB / "concepts.py"), "adequacy-pitch", "--prove"],
                           cwd=LIB, capture_output=True, text=True, env=env)
    check("F: with the engine unreachable, --prove exits NONZERO", f.returncode != 0)
    emitted_record = False
    for line in f.stdout.splitlines():
        try:
            emitted_record |= isinstance(json.loads(line), dict)
        except ValueError:
            pass
    check("F: ...and emits NO record (an absent measurement cannot masquerade as an insensitive one)",
          not emitted_record and '"fingerprint"' not in f.stdout)

    print("\n⟨P, F, δ⟩")
    print("      P (real engine):    concepts.py <key> → exit 0")
    print("      F (engine absent):  concepts.py <key> --prove → nonzero, zero records emitted")
    print("      δ (min delta): one env var — PAPERKIT_ENGINE, present → an empty dir\n")

    if fails:
        print(f"PROVE: FAIL ({len(fails)} drifted)")
        return 1
    print("PROVE: PASS (1 sound arm, 2 degraded-arm refusals)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
