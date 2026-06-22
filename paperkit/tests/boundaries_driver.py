#!/usr/bin/env python3
"""Behavioral-boundary examples for the pump/parse liveness driver (paperkit/driver.py).

⟨P, F, δ⟩ per the boundary practice.  The driver advances a witness in resumable
increments under a budget, never blocking past one increment — so a slow-but-sound
check reads as "resume me", not a falsification.  Bounds: it completes a witness,
resumption is faithful, the soundness round-trip is enforced, and a budget stops it
short (resumably) rather than blocking.

    python3 paperkit/tests/boundaries_driver.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import driver  # noqa: E402

N = 5


class W:
    """A faithful 5-item pump-witness; pump can sleep a hair so a budget can bite."""
    def __init__(self, slow=0.0):
        self.slow = slow

    def initial(self):
        return {"c": 0, "r": []}

    def pump(self, s):
        if self.slow:
            time.sleep(self.slow)
        i = s["c"]
        return s if i >= N else {"c": i + 1, "r": s["r"] + [i * i]}

    def parse(self, s):
        return {"done": s["c"] >= N, "results": s["r"], "progress": f'{s["c"]}/{N}'}

    def serialize(self, s):
        return json.dumps(s, sort_keys=True)

    def deserialize(self, x):
        return json.loads(x)


class Broken(W):
    """Violates the soundness obligation: serialize drops a field, so the state does
    not round-trip."""
    def serialize(self, s):
        return json.dumps({"c": s["c"]})


GOLD = [0, 1, 4, 9, 16]


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("driver behaviors\n")
    m, steps, done = driver.drive(W())
    check("runs a witness to completion (budget 0)", done and steps == N and m["results"] == GOLD)

    f = tempfile.mktemp()
    m2, _, d2 = driver.drive(W(), state_path=f)
    check("resumption via the persisted token yields the same verdict", d2 and m2["results"] == GOLD)
    os.path.exists(f) and os.unlink(f)

    try:
        driver.drive(Broken())
        sound = False
    except AssertionError:
        sound = True
    check("a state that does not round-trip is rejected (soundness assert)", sound)

    f2 = tempfile.mktemp()
    _, sb, db = driver.drive(W(slow=0.02), state_path=f2, budget=0.001)
    check("a budget stops before done (no blocking) — resumable",
          (not db) and sb < N and Path(f2).exists())
    mr, _, dr = driver.drive(W(), state_path=f2, budget=0)
    check("resumes from the persisted token to completion", dr and mr["results"] == GOLD)
    os.path.exists(f2) and os.unlink(f2)
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("the budget toggles done ↔ resume (liveness)", "the time budget",
         "budget 0    → done", driver.drive(W())[2] is True,
         "budget tiny → resume", driver.drive(W(slow=0.02), budget=0.001)[2] is False),
        ("the soundness obligation gates the run", "serialize fidelity (round-trip)",
         "faithful  → runs", driver.drive(W())[2] is True,
         "drops field → rejected", _raises(lambda: driver.drive(Broken()))),
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
    print("BOUNDARIES: PASS (5 behaviors, 2 deltas)")
    return 0


def _raises(thunk):
    try:
        thunk()
        return False
    except AssertionError:
        return True


if __name__ == "__main__":
    raise SystemExit(main())
