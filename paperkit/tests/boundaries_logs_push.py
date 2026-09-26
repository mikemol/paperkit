"""Behavioral-boundary examples for the findings log push — tools/logs_push.py.

⟨P, F, δ⟩ per the boundary practice.  The tool parses a hook log for the engine's OWN failure
vocabulary and posts it to a log store, on RED as well as green.  Bounds: a red log yields typed
findings, a log with no findings yields none (and posts nothing), and the minimum delta between
reported and silent is a single recognised line.  Every arm is offline — no endpoint is contacted.

The per-spawn timeline arms went with `spawns()`, which read bazel's execution log (dropped,
Ζ·execlog·drop); BuildBuddy's execution records are read by tools/bb_records.py instead.

    python3 paperkit/tests/boundaries_logs_push.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# The bib spells bare `python3`; appending the repo root makes `paperkit` and `tools` importable
# as directories with no install (the boundaries_components.py pattern — APPEND, never insert).
sys.path.append(str(Path(__file__).resolve().parents[2]))

from paperkit.tests._boundary import Suite
from tools import logs_push

RED_LOG = (
    "[pre-commit] ok: hook-index (worktree ≡ index)\n"
    "FAIL: @@+bib+paperkit_talk//:gate (Exit 1) (see /x/test.log)\n"
    "coherence: GROUNDING 2 of 80 rests-on edge(s) un-acknowledged — because\n"
    "  [@a] rests-on [@b] — tests engine capability, but not [@b]'s\n"
    "paperkit-gate: check UNRESOLVABLE for [@t-x]: result:render#rnd-y — could not evaluate\n"
    "java.lang.OutOfMemoryError: Java heap space\n"
    "INFO: some ordinary build chatter nobody needs\n"
)
KINDS = {"hook_step", "bazel_target_fail", "coherence_grounding", "coherence_miss",
         "gate_unresolvable", "jvm_oom"}
OOM_LINE = 6
UNREACHABLE = "http://127.0.0.1:1/insert"


def _write(text: str) -> Path:
    """Write text to a fresh temp hook log and return its path."""
    path = Path(tempfile.mkdtemp()) / "hook.log"
    path.write_text(text, encoding="utf-8")
    return path


def main() -> int:
    """Run the logs_push boundary arms."""
    s = Suite("LOGS-PUSH", "LOGS-PUSH BOUNDARIES ⟨P, F, δ⟩")
    red = _write(RED_LOG)
    ev = logs_push.findings(red)
    kinds = [e.kind for e in ev]

    s.section("P: the engine's failure vocabulary is recognised and TYPED")
    s.check("a red log yields typed findings, one per recognised line", len(ev) == len(KINDS))
    s.check("each KIND is present — a query can ask for one without matching prose",
            set(kinds) == KINDS)
    s.check("the captured fields carry the identifiers, not just the message",
            next(e.fields for e in ev if e.kind == "bazel_target_fail")
            == ("@@+bib+paperkit_talk//:gate", "1"))
    s.check("ordinary build chatter is DROPPED — a store full of noise is not queried",
            all("ordinary build chatter" not in e.msg for e in ev))
    s.check("each finding carries its source LINE, so one run's events are orderable",
            [e.line for e in ev] == sorted(e.line for e in ev))
    s.check("the line numbers are the REAL positions, not a synthetic counter",
            next(e.line for e in ev if e.kind == "jvm_oom") == OOM_LINE)
    s.check("a record carries the run's common fields beneath its own",
            ev[0].record({"verdict": "red"})["verdict"] == "red")

    s.section("F: telemetry must never fail its caller")
    s.check("a MISSING log file yields no findings rather than raising",
            logs_push.findings(Path("/nonexistent/hook.log")) == [])
    ok, why = logs_push.push([], UNREACHABLE, {})
    s.check("an empty finding set posts NOTHING (no endpoint contacted, reported as ok)",
            ok and "no findings" in why)
    ok2, why2 = logs_push.push(ev[:1], UNREACHABLE, {})
    s.check("an UNREACHABLE endpoint is a named failure, not an exception",
            not ok2 and "Error" in why2)
    s.check("main() exits 0 with no endpoint configured (absent sink is a no-op)",
            logs_push.main([str(red)]) == 0 if not os.environ.get("PAPERKIT_LOGS_URL") else True)
    s.check("an unrecognised flag is REFUSED (exit 2), never read as a value or a path",
            logs_push.main([str(red), "--help", "x"]) == logs_push.EXIT_USAGE)

    one = logs_push.findings(_write("java.lang.OutOfMemoryError: heap\n"))
    none = logs_push.findings(_write("INFO: nothing to see\n"))
    s.delta("one recognised line is the difference between reported and silent",
            len(one) == 1, none == [],
            p="a log with one OOM line reports one finding",
            f="the same log without it reports none",
            d="one recognised line")
    return s.finish()


if __name__ == "__main__":
    raise SystemExit(main())
