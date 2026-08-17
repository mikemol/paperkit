#!/usr/bin/env python3
r"""Behavioral-boundary examples for Ζ·tier·exit — the verdict TRISTATE (pass / fail / cannot-run).

A toolchain-tier check whose host toolchain is absent must report CANNOT-RUN, not fail: a considered
"I could not verify this here" is not "the property is false".  pk_cmd (verb.bzl) maps a check's exit
0 → pass, 3 (_REFUSE, engine-aligned with gate.py/discriminate) → cannot-run, any other nonzero → fail;
verdict.py records the tristate; pk_gate's aggregator keys on {fail} alone, so a cannot-run does NOT
red the gate (no false-red on a toolchain-less box) yet stays distinguishable from pass (no false-green
— it is honestly "not verified here").  ⟨P, F, δ⟩ per the boundary practice.

Run:  python3 paperkit/tests/boundaries_verdict.py
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ENG = Path(__file__).resolve().parent.parent
VERDICT = str(ENG.parent / "tools" / "verdict.py")


def _emit(value: str) -> str:
    """Run `verdict.py emit cmd <value>` and return the recorded verdict."""
    with tempfile.TemporaryDirectory() as d:
        out = f"{d}/v.json"
        subprocess.run(["python3", VERDICT, "emit", "cmd", value, out], check=True)
        return json.load(open(out))["verdict"]


def _agg(*verdicts: str) -> str:
    """Emit each verdict then aggregate (pk_gate's oracle: pass iff no record reads `fail`)."""
    with tempfile.TemporaryDirectory() as d:
        recs = []
        for i, v in enumerate(verdicts):
            r = f"{d}/r{i}.json"
            subprocess.run(["python3", VERDICT, "emit", "cmd", v, r], check=True)
            recs.append(r)
        out = f"{d}/g.json"
        subprocess.run(["python3", VERDICT, "agg", "gate", out, "verdict", "fail", *recs], check=True)
        return json.load(open(out))["verdict"]


def main() -> int:
    fails = []

    def check(desc, cond):
        print(f"  {'ok ' if cond else 'XX '}{desc}")
        if not cond:
            fails.append(desc)

    print("Ζ·tier·exit — verdict tristate behaviors\n")

    # the record layer carries three distinct verdicts, none collapsed to another.
    check("emit records `pass` verbatim", _emit("pass") == "pass")
    check("emit records `fail` verbatim", _emit("fail") == "fail")
    check("emit records `cannot-run` as its OWN verdict (not pass, not fail)",
          _emit("cannot-run") == "cannot-run")
    check("an unknown verdict fails CLOSED (a caller bug is not silently a pass)",
          _emit("garbage") == "fail")

    # the aggregator (pk_gate) keys on {fail} alone: cannot-run does not red, a real fail does.
    check("a cannot-run alongside a pass does NOT red the gate (no false-red)",
          _agg("cannot-run", "pass") == "pass")
    check("a cannot-run alone does NOT red the gate", _agg("cannot-run") == "pass")
    check("a cannot-run does NOT MASK a real fail beside it (no false-green either)",
          _agg("cannot-run", "fail") == "fail")
    check("a plain fail still reds the gate", _agg("pass", "fail") == "fail")

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    # P (pass side): a check that CANNOT RUN (exit 3) is cannot-run → the gate stays green.
    # F (flag side): a check that RAN-AND-FAILED (any other nonzero) is fail → the gate reds.
    # δ: the check's exit code — 3 (cannot-run) vs 1 (fail) — the ONE bit that separates
    #    "I could not verify" from "the property is false".
    P = _agg("cannot-run")
    F = _agg("fail")
    ok = P == "pass" and F == "fail"
    fails.append("cannot-run-vs-fail") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}exit 3 (cannot-run) leaves the gate green; exit 1 (fail) reds it")
    print("      P (pass side): a check exits 3 — its toolchain is absent, verdict cannot-run, gate green")
    print("      F (flag side): a check exits 1 — it ran and the property failed, verdict fail, gate red")
    print("      δ (min delta): the exit code 3 vs 1 — cannot-verify vs the-property-is-false\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (8 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
