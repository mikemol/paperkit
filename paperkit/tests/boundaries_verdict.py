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


def _run_ok(cmd: str) -> str:
    """resolves()'s cmd: arm, as a caller reads it."""
    import sys as _s
    _s.path.insert(0, str(ENG))
    import resolver
    with tempfile.TemporaryDirectory() as d:
        v = resolver.run_ok(cmd, Path(d))
        return "cannot-run" if v.is_unavailable() else ("pass" if v.passed else "fail")


def _cli_parity() -> list:
    """Ζ·tier·exit — the SAME check must answer the same verdict on both routes.

    pk_cmd has typed the exit since the tier work (rc 0 pass / rc 3 cannot-run / other fail), but
    run_ok -- the CLI route -- read `rc == 0` and folded EVERY nonzero into FAIL.  One check, two
    verdicts, decided by which route ran it: render's wcag checks return 3 when veraPDF is absent,
    so `bazel test` called them cannot-run while `gate.py` called them a REFUTATION and reported
    them in `bad`.  That is the false-red the tier work closed, still open on the other route.

    This is NOT the fold the Verdict docstring forbids (discriminate's `3 REFUSE` = "you asked
    wrong", an ENGINE-internal caller bug, vs UNAVAILABLE = "could not reach the thing to ask").
    The rc here crosses a PROCESS boundary from an external check reporting an absent toolchain --
    the could-not-evaluate arm by definition.  The two share a number, not a meaning.
    """
    return [
        ("rc 0 → pass", _run_ok("true"), "pass"),
        ("rc 1 → fail (ran and did not hold)", _run_ok("false"), "fail"),
        ("rc 3 → cannot-run, NOT fail", _run_ok("exit 3"), "cannot-run"),
        ("rc 7 → fail (only 3 is typed)", _run_ok("exit 7"), "fail"),
        ("un-spawnable → fail, not cannot-run (the shell RAN and reported 127)",
         _run_ok("no-such-binary-xyz"), "fail"),
    ]


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

    # ROUTE PARITY — the record layer above is pk_cmd's; this is the CLI resolver's.  Both routes
    # run the SAME check, so both must type its exit the same way (see _cli_parity's rationale).
    print()
    for desc, got, want in _cli_parity():
        check(f"cmd: {desc:<52} got={got}", got == want)

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
    bad = len([b for b in ran if not b])
    if bad:
        print(f"BOUNDARIES: FAIL ({bad} of {len(ran)} behaviors drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
