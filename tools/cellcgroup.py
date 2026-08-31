#!/usr/bin/env python3
"""Τ·mem·observe·inside — a sweep cell's view of ITS OWN cgroup.

Split out of `tools/eval.py` (Ζ·eval·split): four functions that read `/sys/fs/cgroup` for the
scope this process is already in.  They share one subject — the cell's own resource accounting —
and none of them knows anything about mutations, .pyc placement or verdicts.

⚑ WHY IT IS A SEPARATE MODULE AND NOT A SECTION.  `eval.py` ran 137,553 times in the last full
sweep and its `main()` was 127 lines doing five jobs; ruff's `C901` + `PLR0915` named it.  The
gate does not say "tidy the file" — it says the file does too much.  This is the first cut, and
it is the easy one precisely because the seam was already there: no caller of these four needs
anything else in eval.py, and nothing here needs anything from it.

READ FROM IN HERE, NEVER FROM THE SHELL AFTERWARDS.  The cell's command is
`cgroup-scope N -- eval.py … ; read-the-peak`, so a trailing read runs AFTER the scope has exited
and lands in bazel's sandbox cgroup — a DIFFERENT tree from the one that ran the check.  Measured
on compose-chains: the outside read reported 4.7MB for a cell whose real in-scope peak is 35MB
and which OOMs at a 32MB cap.  Under-reporting is the dangerous direction: a manifest built from
it sizes the cell BELOW what it needs, so the loop re-derives the same OOM every run and never
converges.
"""
from __future__ import annotations

import pathlib

CGROUP_ROOT = "/sys/fs/cgroup"


def own_cgroup() -> str | None:
    """Return this process's own v2 cgroup path, or None where v2 is not reachable."""
    try:
        return pathlib.Path("/proc/self/cgroup").read_text().strip().rsplit(":", 1)[-1]
    except OSError:
        return None


def peak_bytes() -> int | None:
    """Return `memory.peak` for this process's cgroup, or None.

    ⚑ THE PEAK INCLUDES TMPFS.  A cgroup is charged for the page cache of files its processes
    write, and TMPDIR is a tmpfs on some hosts — so a witness that projects an out.md into a
    mkdtemp() pays for it in MEMORY, not just disk, and freeing it needs the directory removed
    rather than the process exited.  Measured on compose-chains the split is anon 32.7MB / file
    0.6MB, so THAT cell is driven by nested interpreters rather than scratch files; a witness
    projecting a large document would be the other way round.  Either way the reservation is the
    same number — memory.peak already counts both — but a reader diagnosing a surprising peak
    must check the split (memory.stat's anon/file) before blaming the code.
    """
    cg = own_cgroup()
    if cg is None:
        return None
    try:
        return int(pathlib.Path(CGROUP_ROOT + cg + "/memory.peak").read_text().strip())
    except (OSError, ValueError):
        return None


def write_peak(path: str) -> None:
    """Deposit this cell's in-scope peak at `path`, in the vocabulary mem_harvest parses."""
    if not path:
        return
    b = peak_bytes()
    pathlib.Path(path).write_text(str(b) if b is not None else "unavailable:unreadable")


def oom_counts() -> tuple[int, int] | None:
    """Return (oom, oom_kill) for this process's own cgroup, or None where v2 is unreachable.

    Ζ·climb·oom·signal — a cell runs INSIDE the cgroup-scope, so its own `memory.events` IS the
    cell's.  No env var, no plumbing: the scope that caps the check is the scope this process is
    already in.
    """
    cg = own_cgroup()
    if cg is None:
        return None
    try:
        ev = pathlib.Path(CGROUP_ROOT + cg + "/memory.events").read_text()
    except OSError:
        return None
    d = dict(line.split() for line in ev.splitlines() if " " in line)
    try:
        return int(d.get("oom", 0)), int(d.get("oom_kill", 0))
    except ValueError:
        return None


def oom_happened(before: tuple[int, int] | None, after: tuple[int, int] | None) -> bool:
    """Report whether an OOM occurred between two `oom_counts()` readings.

    ⚑ INCREMENT, never a delta size.  `oom_kill` counts PROCESSES and `oom_group_kill` counts
    EVENTS, so under kubelet's `memory.oom.group=1` one OOM raises oom_kill by the whole tree size
    while oom_group_kill rises by 1.  Asking only "did it increment" is correct under both;
    dividing, or assuming +1, would not be (linux-sources, 2026-08-26).
    """
    if before is None or after is None:
        return False
    return after[0] > before[0] or after[1] > before[1]
