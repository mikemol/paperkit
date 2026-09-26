"""Ρ·telemetry·logs — push a gate run's STRUCTURED FINDINGS to a log store.

WHY THIS EXISTS.  A build's timing can come from anywhere (BuildBuddy keeps it per action; see
tools/bb_records.py), but the REASON a gate failed exists only in the hook's own output, and the
builds worth keeping are precisely the ones that fail.  Measured cost: a coherence residual naming
two undischarged edges — and a `java.lang.OutOfMemoryError` in the bazel server — existed only in a
/tmp log the next run would overwrite.  The residual was emitted correctly; nothing durable caught
it.  So this pushes on RED as well as green, and it pushes the FINDINGS: the reason a gate failed,
in the form the engine already computed it.  A red build should emit MORE than a green one.

Parsed from the hook log rather than instrumented per-site, deliberately: the residual lines are
already the engine's own output (`coherence: GROUNDING ...`, `paperkit-gate: ...`, `FAIL: //...`),
so a parser cannot drift from a format the checks do not know about, and this can be deleted
without touching a single check.

The endpoint is resolved by the hook (PAPERKIT_LOGS_URL, queried by service name at the moment of
use).  Absent: a silent no-op.  Best-effort in every arm — telemetry that can fail a commit is a
liability, not an instrument.  (The per-spawn timeline this once read from bazel's execution log
went with that log, Ζ·execlog·drop; the per-action record is BuildBuddy's now.)

    logs_push.py <hook-log> [--rc N] [--seconds N] [--run-id ID] [--url URL]
"""

from __future__ import annotations

import json
import os
import re
import socket
import sys
import urllib.parse
from dataclasses import dataclass, field
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path

USAGE = "logs_push.py <hook-log> [--rc N] [--seconds N] [--run-id ID] [--url URL]"
EXIT_USAGE = 2
TIMEOUT_S = 10
MSG_MAX = 2000
HTTP_OK_LO = 200
HTTP_OK_HI = 300
FLAGS = ("--rc", "--seconds", "--run-id", "--url")

# The engine's own failure vocabulary.  Each pattern names a KIND, so a query can ask for one
# without string-matching prose that may be reworded.
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("bazel_target_fail", re.compile(r"^(?:FAIL|ERROR): (\S+) \(Exit (\d+)\)")),
    ("gate_unresolvable",
     re.compile(r"^paperkit-gate: check UNRESOLVABLE for \[@([\w.-]+)\]: (\S+)")),
    ("coherence_grounding", re.compile(r"^coherence: GROUNDING (\d+) of (\d+) rests-on")),
    ("coherence_miss", re.compile(r"^\s+\[@([\w.-]+)\] rests-on \[@([\w.-]+)\]")),
    ("jvm_oom", re.compile(r"^(java\.lang\.OutOfMemoryError.*)$")),
    ("hook_step", re.compile(r"^\[pre-commit\] (ok|FAIL): (.+)$")),
    ("sandbox_invalidated", re.compile(r"input dependency (\S+) was modified during execution")),
)


@dataclass(frozen=True)
class Finding:
    """One recognised line: its kind, the identifiers it names, and where it sat in the log."""

    kind: str
    fields: tuple[str, ...]
    line: int
    msg: str

    def record(self, common: dict[str, object]) -> dict[str, object]:
        """Render as the JSON-lines record the store ingests, over the run's common fields."""
        out: dict[str, object] = dict(common)
        out["kind"] = self.kind
        out["fields"] = list(self.fields)
        out["line"] = self.line
        out["_msg"] = self.msg
        return out


def findings(log: Path) -> list[Finding]:
    """Return every recognised finding in a hook log, in order.

    Unrecognised lines are DROPPED, not forwarded: a store full of build chatter is a store nobody
    queries.  `line` orders one run's findings against each other, since bazel's console output
    carries no clock and every finding otherwise shares the ingest timestamp.  A missing or
    unreadable log yields no findings rather than raising.
    """
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out: list[Finding] = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        for kind, pat in PATTERNS:
            m = pat.match(line)
            if m:
                out.append(Finding(kind, tuple(str(g) for g in m.groups()), lineno,
                                   line[:MSG_MAX]))
                break
    return out


def push(events: list[Finding], url: str, common: dict[str, object]) -> tuple[bool, str]:
    """POST the findings as JSON-lines.  Return (ok, detail); never raise."""
    if not events:
        return True, "no findings to push"
    body = "\n".join(json.dumps(e.record(common)) for e in events)
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return False, f"unusable sink URL: {url!r}"
    conn_cls = HTTPSConnection if parts.scheme == "https" else HTTPConnection
    target = parts.path + (f"?{parts.query}" if parts.query else "")
    try:
        conn = conn_cls(parts.hostname, parts.port, timeout=TIMEOUT_S)
        try:
            conn.request("POST", target or "/", body=body,
                         headers={"Content-Type": "application/stream+json"})
            status = conn.getresponse().status
        finally:
            conn.close()
    except (OSError, ValueError) as err:
        return False, f"{type(err).__name__}: {err}"
    return HTTP_OK_LO <= status < HTTP_OK_HI, f"{status} ({len(events)} events)"


@dataclass
class Args:
    """The parsed command line: exactly the documented shape, nothing else."""

    log: Path
    opts: dict[str, str] = field(default_factory=dict)


def parse(argv: list[str]) -> Args | None:
    """Parse argv, or return None when it is not exactly the documented shape."""
    if not argv or argv[0].startswith("-"):
        return None
    args = Args(Path(argv[0]))
    rest = argv[1:]
    if len(rest) % 2:
        return None
    for flag, value in zip(rest[::2], rest[1::2], strict=True):
        if flag not in FLAGS or flag in args.opts:
            return None
        args.opts[flag] = value
    return args


def main(argv: list[str]) -> int:
    """Push one hook log's findings; always 0 unless argv itself is wrong."""
    args = parse(argv)
    if args is None:
        sys.stderr.write(USAGE + "\n")
        return EXIT_USAGE
    url = args.opts.get("--url") or os.environ.get("PAPERKIT_LOGS_URL", "")
    if not url:
        sys.stderr.write("logs_push: PAPERKIT_LOGS_URL unset — no log sink configured, skipping\n")
        return 0
    rc = args.opts.get("--rc", "")
    host = socket.gethostname()
    stamp = int(args.log.stat().st_mtime) if args.log.exists() else 0
    # A RUN ID ties one invocation's findings together; without it two runs interleave.
    common: dict[str, object] = {
        "service": "paperkit", "host": host,
        "run": args.opts.get("--run-id") or os.environ.get("PK_RUN_ID") or f"{host}-{stamp}",
        "verdict": "red" if rc not in {"", "0"} else "green",
    }
    if rc:
        common["rc"] = rc
    if "--seconds" in args.opts:
        common["build_seconds"] = args.opts["--seconds"]
    ok, detail = push(findings(args.log), url, common)
    sys.stderr.write(f"logs_push: {'pushed' if ok else 'FAILED'} — {detail}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
