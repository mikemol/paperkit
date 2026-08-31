#!/usr/bin/env python3
"""Ρ·telemetry·logs — push a gate run's STRUCTURED FINDINGS to a log store.

WHY THIS EXISTS, and it is a correction to the metrics push beside it.  `otlp_push.py` reports
build-loop TIMING, and the hook fires it only after a GREEN run (pre-commit's `run()` aborts the
commit on red, so the push line is unreachable on failure).  That is happy-path-only telemetry:
the builds worth keeping are precisely the ones that never report.  Measured cost, this session:
a coherence residual naming two undischarged edges — and a `java.lang.OutOfMemoryError` in the
bazel server — existed only in a /tmp log that the next run would overwrite.  The residual was
emitted correctly; nothing durable caught it.

So this pushes on RED as well as green, and it pushes the FINDINGS, not the timings: the reason
a gate failed, in the form the engine already computed it.  A red build should emit MORE than a
green one, never less.

Parsed from a hook log rather than instrumented per-site, deliberately: the residual lines are
already the engine's own output (`coherence: GROUNDING ...`, `paperkit-gate: ...`, `FAIL: //...`),
so a parser cannot drift from a format the checks do not know about.  The alternative — teaching
every check to emit structured events — is the larger, more invasive design, and this one can be
deleted without touching a single check.

Endpoint is a POINTER a machine sets (PAPERKIT_LOGS_URL, in the gitignored .githooks/local.env),
never tracked: each clone's operator points at their own store.  Absent ⇒ silent no-op.
Best-effort in every arm — telemetry that can fail a commit is a liability, not an instrument.

    logs_push.py <hook-log> [--rc N] [--seconds N] [--execlog F] [--run-id ID] [--url URL]
"""
from __future__ import annotations

import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

# The engine's own failure vocabulary.  Each pattern names a KIND, so a query can ask for one
# without string-matching prose that may be reworded.
_PATTERNS = [
    ("bazel_target_fail", re.compile(r"^(?:FAIL|ERROR): (\S+) \(Exit (\d+)\)")),
    ("gate_unresolvable", re.compile(r"^paperkit-gate: check UNRESOLVABLE for \[@([\w.-]+)\]: (\S+)")),
    ("coherence_grounding", re.compile(r"^coherence: GROUNDING (\d+) of (\d+) rests-on")),
    ("coherence_miss", re.compile(r"^\s+\[@([\w.-]+)\] rests-on \[@([\w.-]+)\]")),
    ("jvm_oom", re.compile(r"^(java\.lang\.OutOfMemoryError.*)$")),
    ("hook_step", re.compile(r"^\[pre-commit\] (ok|FAIL): (.+)$")),
    ("sandbox_invalidated", re.compile(r"input dependency (\S+) was modified during execution")),
]


def findings(log: Path) -> list:
    """Every recognised finding in a hook log, in order.  Unrecognised lines are DROPPED, not
    forwarded: a log store full of build chatter is a log store nobody queries.
    """
    out = []
    try:
        text = log.read_text(errors="replace")
    except OSError:
        return out
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.rstrip()
        for kind, pat in _PATTERNS:
            m = pat.match(line)
            if m:
                # `line` orders a run's findings against EACH OTHER even when no clock is
                # available: bazel's console output carries none, so without this every finding
                # from one run shares the ingest timestamp and the sequence is lost.
                out.append({"kind": kind, "fields": list(m.groups()),
                            "line": lineno, "_msg": line[:2000]})
                break
    return out


def spawns(execlog: Path) -> list:
    """Ζ·telemetry·time — a per-spawn TIMELINE from bazel's execution log.

    The findings above are what a run FOUND; this is when it DID things.  Without it the store
    holds a bag of events sharing one ingest timestamp — orderable neither among themselves nor
    against anything else — so the question that actually matters after a red build ("which cells
    were running when the heap died?") cannot be asked.  Measured: a 4-hour run's OOM and its two
    coherence misses all landed at the same `_time`, the moment of the push.

    The clock is bazel's own `metrics.startTime` (absolute ISO-8601) plus `executionWallTime`, so
    a spawn's interval is exact and needs no correlation with our own wall clock.  Bazel's console
    output carries NO wall clock — only per-action elapsed — which is why the log text alone
    cannot supply this and the execution log must.
    """
    out = []
    try:
        text = execlog.read_text()
    except OSError:
        return out
    dec, i, n = json.JSONDecoder(), 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        try:
            obj, i = dec.raw_decode(text, i)
        except ValueError:
            break
        m = obj.get("metrics") or {}
        start = m.get("startTime")
        if not start:
            continue
        out.append({"kind": "spawn", "_time": start,
                    "mnemonic": obj.get("mnemonic") or "?",
                    "target": obj.get("targetLabel") or "",
                    "wall": (m.get("executionWallTime") or "").rstrip("s"),
                    "runner": obj.get("runner") or "",
                    "cache_hit": bool(obj.get("cacheHit")),
                    "exit_code": obj.get("exitCode", 0),
                    "_msg": f"{obj.get('mnemonic')} {obj.get('targetLabel')} "
                            f"{m.get('executionWallTime')}"})
    return out


def push(events: list, url: str, common: dict) -> tuple:
    """POST JSON-lines to VictoriaLogs.  Returns (ok, detail); never raises."""
    if not events:
        return True, "no findings to push"
    body = "\n".join(json.dumps({**common, **e}) for e in events).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/stream+json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return (200 <= r.status < 300), f"{r.status} ({len(events)} events)"
    except (urllib.error.URLError, OSError, ValueError) as e:
        return False, f"{type(e).__name__}: {e}"


def main(argv: list) -> int:
    if not argv:
        print("usage: logs_push.py <hook-log> [--rc N] [--seconds N] [--url URL]", file=sys.stderr)
        return 2
    log = Path(argv[0])
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default
    url = opt("--url") or os.environ.get("PAPERKIT_LOGS_URL", "")
    if not url:
        print("logs_push: PAPERKIT_LOGS_URL unset — no log sink configured, skipping",
              file=sys.stderr)
        return 0                                  # absent endpoint is a no-op, never an error
    rc = opt("--rc", "")
    ev = findings(log)
    # Ζ·telemetry·time — the spawn timeline, when the caller has an execution log.  Pushed in the
    # SAME batch and under the same run id, so a query can interleave "what happened" with "what
    # was running", which is the whole point of carrying a clock.
    if opt("--execlog"):
        ev += spawns(Path(opt("--execlog")))
    # A RUN ID ties findings and spawns from one invocation together; without it two runs'
    # events interleave in the store and neither can be read alone.
    common = {"service": "paperkit", "host": socket.gethostname(),
              "run": opt("--run-id") or os.environ.get("PK_RUN_ID")
                     or f"{socket.gethostname()}-{int(log.stat().st_mtime) if log.exists() else 0}",
              "verdict": "red" if rc not in ("", "0") else "green"}
    if rc != "":
        common["rc"] = rc
    if opt("--seconds"):
        common["build_seconds"] = opt("--seconds")
    ok, detail = push(ev, url, common)
    print(f"logs_push: {'pushed' if ok else 'FAILED'} — {detail}", file=sys.stderr)
    return 0                                      # best-effort: never fail the caller


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
