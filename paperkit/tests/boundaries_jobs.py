#!/usr/bin/env python3
"""Behavioral-boundary examples for the parallel gate (--jobs).

⟨P, F, δ⟩ per the boundary practice.  The gate runs a project's distinct checks
concurrently (the bib IS the makefile: independent checks are independent targets).
The load-bearing invariant is DETERMINISM — the verdict is a property of the checks,
never of the worker count: parallel ≡ serial.  This bounds that --jobs is a speed
knob with no semantic effect.

    python3 paperkit/tests/boundaries_jobs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture import entry, gate  # noqa: E402

# A multi-check project, so parallelism actually fans out (3 distinct checks).
PASS = [entry("a", claim="alpha", check="cmd:true"),
        entry("b", claim="beta", check="cmd:true", frm="a"),
        entry("c", claim="gamma", check="cmd:true", frm="b")]
# Same shape, but one check fails — the verdict must flip regardless of --jobs.
FAIL = [entry("a", claim="alpha", check="cmd:true"),
        entry("b", claim="beta", check="cmd:false", frm="a"),
        entry("c", claim="gamma", check="cmd:true", frm="b")]
# Memory bounding lives entirely in the Bazel layer (Τ·mem: the bib generator projects the learned
# mem.json to a per-sweep resource_set).  The engine is INERT to memory — it just resolves the
# check — so a `mem` annotation on a check leaves the verdict identical to a run without one.
LEASED_PASS = [entry("a", claim="alpha", check="cmd:true", mem="256"),
               entry("b", claim="beta", check="cmd:true", frm="a", mem="256")]
LEASED_FAIL = [entry("a", claim="alpha", check="cmd:true", mem="256"),
               entry("b", claim="beta", check="cmd:false", frm="a", mem="256")]


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    rc_pass_serial, _ = gate(PASS, "--jobs=1")
    rc_pass_par, _ = gate(PASS, "--jobs=8")
    rc_fail_serial, _ = gate(FAIL, "--jobs=1")
    rc_fail_par, _ = gate(FAIL, "--jobs=8")
    rc_leased_pass, _ = gate(LEASED_PASS)     # mem declared; the engine is inert to it
    rc_leased_fail, _ = gate(LEASED_FAIL)

    print("parallel-gate behaviors\n")
    check("a clean project passes serial (--jobs=1 → exit 0)", rc_pass_serial == 0)
    check("a failing check fails serial (--jobs=1 → exit 1)", rc_fail_serial == 1)
    check("parallel agrees with serial on PASS (--jobs=8 → exit 0)", rc_pass_par == 0)
    check("parallel agrees with serial on FAIL (--jobs=8 → exit 1)", rc_fail_par == 1)
    check("a declared mem keeps a clean verdict (engine inert to mem → exit 0)", rc_leased_pass == 0)
    check("a declared mem keeps a failing verdict (engine inert to mem → exit 1)", rc_leased_fail == 1)
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("verdict tracks the checks, not the worker count",
         "one of three checks (cmd:true → cmd:false)",
         "all pass → exit 0", rc_pass_serial == 0 and rc_pass_par == 0,
         "one fails → exit 1", rc_fail_serial == 1 and rc_fail_par == 1),
        ("--jobs is semantically inert (parallel ≡ serial)",
         "the worker count (1 → 8)",
         "serial verdicts", (rc_pass_serial, rc_fail_serial) == (0, 1),
         "parallel verdicts (identical)", (rc_pass_par, rc_fail_par) == (rc_pass_serial, rc_fail_serial)),
        ("a declared mem is semantically inert (verdict unchanged by mem)",
         "declaring mem={256} on every check (memory bounding is Bazel's resource_set; engine inert)",
         "unleased → (0, 1)", (rc_pass_serial, rc_fail_serial) == (0, 1),
         "leased   → (0, 1) identical", (rc_leased_pass, rc_leased_fail) == (0, 1)),
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
    print("BOUNDARIES: PASS (6 behaviors, 3 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
