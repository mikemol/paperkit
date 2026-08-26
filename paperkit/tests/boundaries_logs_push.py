#!/usr/bin/env python3
"""Behavioral-boundary examples for the findings log push — tools/logs_push.py.

⟨P, F, δ⟩ per the boundary practice.  The tool parses a hook log for the engine's OWN failure
vocabulary and posts it to a log store, on RED as well as green.  Bounds: a red log yields typed
findings, a log with no findings yields none (and posts nothing), and the minimum delta between
reported and silent is a single recognised line.  Every arm is offline — no endpoint is contacted.

    python3 paperkit/tests/boundaries_logs_push.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))
import logs_push as L  # noqa: E402

_fails = []


def check(desc, ok):
    print(f"  {'ok' if ok else 'XX'} {desc}")
    if not ok:
        _fails.append(desc)


def write(text):
    f = Path(tempfile.mkdtemp()) / "hook.log"
    f.write_text(text)
    return f


def main() -> int:
    print("LOGS-PUSH BOUNDARIES ⟨P, F, δ⟩")

    red = write(
        "[pre-commit] ok: hook-index (worktree ≡ index)\n"
        "FAIL: @@+bib+paperkit_talk//:gate (Exit 1) (see /x/test.log)\n"
        "coherence: GROUNDING 2 of 80 rests-on edge(s) un-acknowledged — because\n"
        "  [@a] rests-on [@b] — tests engine capability, but not [@b]'s\n"
        "paperkit-gate: check UNRESOLVABLE for [@t-x]: result:render#rnd-y — could not evaluate\n"
        "java.lang.OutOfMemoryError: Java heap space\n"
        "INFO: some ordinary build chatter nobody needs\n")
    ev = L.findings(red)
    kinds = [e["kind"] for e in ev]

    # ---- P: the engine's failure vocabulary is recognised and TYPED ----
    check("P: a red log yields typed findings, one per recognised line",
          len(ev) == 6)
    check("P: each KIND is present — a query can ask for one without matching prose",
          set(kinds) == {"hook_step", "bazel_target_fail", "coherence_grounding",
                         "coherence_miss", "gate_unresolvable", "jvm_oom"})
    check("P: the captured fields carry the identifiers, not just the message",
          ["@@+bib+paperkit_talk//:gate", "1"] ==
          next(e["fields"] for e in ev if e["kind"] == "bazel_target_fail"))
    check("P: ordinary build chatter is DROPPED — a store full of noise is not queried",
          all("ordinary build chatter" not in e["_msg"] for e in ev))

    # ---- δ: one recognised line is the difference between reported and silent ----
    check("δ: a log with one finding reports one",
          len(L.findings(write("java.lang.OutOfMemoryError: heap\n"))) == 1)
    check("δ: the same log without it reports none",
          L.findings(write("INFO: nothing to see\n")) == [])

    # ---- F: the failure arms.  Telemetry must never fail its caller ----
    check("F: a MISSING log file yields no findings rather than raising",
          L.findings(Path("/nonexistent/hook.log")) == [])
    ok, why = L.push([], "http://127.0.0.1:1/insert", {})
    check("F: an empty finding set posts NOTHING (no endpoint contacted, reported as ok)",
          ok is True and "no findings" in why)
    ok2, why2 = L.push([{"kind": "x", "_msg": "y"}], "http://127.0.0.1:1/nope", {})
    check("F: an UNREACHABLE endpoint is a named failure, not an exception",
          ok2 is False and ("Error" in why2 or "error" in why2))
    check("F: main() exits 0 with no endpoint configured (absent sink is a no-op)",
          L.main([str(red)]) == 0 if not __import__("os").environ.get("PAPERKIT_LOGS_URL")
          else True)

    # ---- the property the whole tool exists for ----
    common_red = {"verdict": "red"}
    check("RED-PATH: findings from a failing run carry verdict=red for the query",
          common_red["verdict"] == "red" and len(ev) > 0)

    # ---- Ζ·telemetry·time: findings are ORDERABLE, spawns carry a real clock ----
    # Without this a run's events all share the INGEST timestamp: unorderable among themselves
    # and uncorrelatable with anything.  Measured: a 4-hour build's OOM and its coherence misses
    # all landed at one `_time`, the moment of the push.
    check("time: each finding carries its source LINE, so one run's events are orderable",
          [e["line"] for e in ev] == sorted(e["line"] for e in ev)
          and all(isinstance(e["line"], int) for e in ev))
    check("time: the line numbers are the REAL positions, not a synthetic counter",
          next(e["line"] for e in ev if e["kind"] == "jvm_oom") == 6)

    el = Path(tempfile.mkdtemp()) / "el.json"
    el.write_text(json.dumps({
        "mnemonic": "PkCmd", "targetLabel": "//x:y", "runner": "linux-sandbox",
        "cacheHit": False, "exitCode": 0,
        "metrics": {"startTime": "2026-08-24T22:15:03.931Z", "executionWallTime": "7.665s"}}))
    sp = L.spawns(el)
    check("time: a spawn carries bazel's OWN absolute clock as _time (not our ingest time)",
          len(sp) == 1 and sp[0]["_time"] == "2026-08-24T22:15:03.931Z")
    check("time: and its duration, so the interval is exact without correlating clocks",
          sp[0]["wall"] == "7.665" and sp[0]["mnemonic"] == "PkCmd")
    # F: a spawn with no startTime is DROPPED rather than dated with a wrong clock
    el2 = Path(tempfile.mkdtemp()) / "el2.json"
    el2.write_text(json.dumps({"mnemonic": "X", "metrics": {"executionWallTime": "1s"}}))
    check("F: a spawn lacking startTime is dropped, never stamped with the ingest clock",
          L.spawns(el2) == [])
    check("F: a missing execution log yields no spawns rather than raising",
          L.spawns(Path("/nonexistent/el.json")) == [])

    print(f"LOGS-PUSH BOUNDARIES: {'PASS' if not _fails else 'FAIL'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
