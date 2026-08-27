#!/usr/bin/env python3
"""Ρ·telemetry·red — sample the COORDINATOR's memory to a durable file, live.

WHY THIS EXISTS, and it is a correction to the two pushers beside it.  `otlp_push` and
`logs_push` are a POST at the END of a run, which by construction cannot report a crash that
kills the run: they buffer, and they die with the thing they are recording.  Measured cost —
the bazel server died twice with `Build completed successfully, 32325 total actions` directly
above `java.lang.OutOfMemoryError`, and BOTH runs pushed nothing.  The runs worth keeping are
exactly the ones that never report.

⚑ SCOPED TO THE COORDINATOR, NOT THE BOX.  A peer's host collectors already sample host memory
and PSI continuously — queried across that crash window, memory PSI peaked near 4%, so the box
was never stressed and its series were never missing.  What NOTHING sampled was the bazel server
itself: every sweep cell runs under a per-action cgroup lease, and the process holding them all
runs unbudgeted and unobserved.  That is the curve that would have shown a ceiling being
approached, and it is the only one this adds.

APPEND, NEVER BUFFER.  One flush per sample, so a SIGKILL loses at most the current line.  A
replayed timeline is a fabrication rather than a recovery.

    coord_sample.py <pid> <out.jsonl> [--interval SECONDS]

Exits when the pid does.  Best-effort in every arm: a sampler that can fail a build is a
liability, not an instrument — the same rule the pushers already follow.
"""
from __future__ import annotations

import json
import os
import sys
import time


def _rss_bytes(pid: int) -> int | None:
    """Resident set, from statm (pages) — cheap, and present on every Linux."""
    try:
        with open(f"/proc/{pid}/statm") as f:
            return int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        return None


def _cgroup_current(pid: int) -> int | None:
    """memory.current for the pid's OWN cgroup, or None where v2 is not reachable.

    Read via /proc/<pid>/cgroup rather than a computed path: the depth differs by QoS class
    under a kubelet, and a hardcoded relative path is right for some and wrong for others.
    """
    try:
        rel = open(f"/proc/{pid}/cgroup").read().strip().rsplit(":", 1)[-1]
        with open("/sys/fs/cgroup" + rel + "/memory.current") as f:
            return int(f.read().strip())
    except (OSError, ValueError, IndexError):
        return None


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__.strip().splitlines()[-3], file=sys.stderr)
        return 2
    pid, out = int(args[0]), args[1]
    every = 1.0
    for a in argv:
        if a.startswith("--interval"):
            try:
                every = float(a.split("=", 1)[1])
            except (IndexError, ValueError):
                pass

    with open(out, "a", buffering=1) as f:                 # line-buffered: one flush per sample
        while True:
            try:
                os.kill(pid, 0)                            # liveness, no signal delivered
            except OSError:
                return 0                                   # the coordinator is gone; so are we
            rec = {"t": round(time.time(), 3), "pid": pid,
                   "rss": _rss_bytes(pid), "cgroup_current": _cgroup_current(pid)}
            if rec["rss"] is None and rec["cgroup_current"] is None:
                return 0                                   # unreadable ⇒ gone or not ours
            f.write(json.dumps(rec) + "\n")
            time.sleep(every)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        raise SystemExit(0)
