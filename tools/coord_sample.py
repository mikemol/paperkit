#!/usr/bin/env python3
"""Ρ·telemetry·red — sample the COORDINATOR's memory to a durable file, live.

WHY THIS EXISTS, and it is a correction to the end-of-run pushers.  `logs_push` (and the retired
`otlp_push`, W44) POST at the END of a run, which by construction cannot report a crash that
kills the run: they buffer, and they die with the thing they are recording.  Measured cost -
the bazel server died twice with `Build completed successfully, 32325 total actions` directly
above `java.lang.OutOfMemoryError`, and BOTH runs pushed nothing.  The runs worth keeping are
exactly the ones that never report.

SCOPED TO THE COORDINATOR, NOT THE BOX.  A peer's host collectors already sample host memory
and PSI continuously - queried across that crash window, memory PSI peaked near 4%, so the box
was never stressed and its series were never missing.  What NOTHING sampled was the bazel server
itself: every sweep cell runs under a per-action cgroup lease, and the process holding them all
runs unbudgeted and unobserved.  That is the curve that would have shown a ceiling being
approached, and it is the only one this adds.

APPEND, NEVER BUFFER.  One flush per sample, so a SIGKILL loses at most the current line.  A
replayed timeline is a fabrication rather than a recovery.

    coord_sample.py <pid> <out.jsonl> [--interval=SECONDS]

Exits when the pid does.  Best-effort in every arm: a sampler that can fail a build is a
liability, not an instrument - the same rule the pushers follow.  An unrecognised argument is
REFUSED (exit 2) rather than read as a path to append to.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

USAGE = "coord_sample.py <pid> <out.jsonl> [--interval=SECONDS]"
EXIT_USAGE = 2
POSITIONALS = 2
INTERVAL_FLAG = "--interval="
STATM_RSS_FIELD = 1
CGROUP_ROOT = Path("/sys/fs/cgroup")


def _rss_bytes(pid: int) -> int | None:
    """Resident set, from statm (pages) - cheap, and present on every Linux."""
    try:
        fields = Path(f"/proc/{pid}/statm").read_text(encoding="ascii").split()
        return int(fields[STATM_RSS_FIELD]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        return None


def _cgroup_current(pid: int) -> int | None:
    """memory.current for the pid's OWN cgroup, or None where v2 is not reachable.

    Read via /proc/<pid>/cgroup rather than a computed path: the depth differs by QoS class
    under a kubelet, and a hardcoded relative path is right for some and wrong for others.
    """
    try:
        line = Path(f"/proc/{pid}/cgroup").read_text(encoding="ascii").strip()
        rel = line.rsplit(":", 1)[-1].lstrip("/")
        return int((CGROUP_ROOT / rel / "memory.current").read_text(encoding="ascii").strip())
    except (OSError, ValueError, IndexError):
        return None


def _alive(pid: int) -> bool:
    """Liveness by signal 0: nothing is delivered."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _parse(argv: list[str]) -> tuple[int, Path, float] | None:
    """(pid, out, interval), or None when argv is not exactly the documented shape."""
    positional: list[str] = []
    every = 1.0
    for arg in argv:
        if arg.startswith(INTERVAL_FLAG):
            try:
                every = float(arg.removeprefix(INTERVAL_FLAG))
            except ValueError:
                return None
        elif arg.startswith("-"):
            return None
        else:
            positional.append(arg)
    if len(positional) != POSITIONALS or not positional[0].isdigit():
        return None
    return int(positional[0]), Path(positional[1]), every


def main(argv: list[str]) -> int:
    """Append one sample per interval until the coordinator is gone."""
    parsed = _parse(argv)
    if parsed is None:
        sys.stderr.write(USAGE + "\n")
        return EXIT_USAGE
    pid, out, every = parsed
    with out.open("a", buffering=1, encoding="utf-8") as sink:  # line-buffered: one flush each
        while _alive(pid):
            rss = _rss_bytes(pid)
            current = _cgroup_current(pid)
            if rss is None and current is None:
                return 0  # unreadable: gone, or not ours
            rec = {"t": round(time.time(), 3), "pid": pid, "rss": rss, "cgroup_current": current}
            sink.write(json.dumps(rec) + "\n")
            time.sleep(every)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        raise SystemExit(0) from None
