#!/usr/bin/env python3
"""Ζ·mutant·eval — run a claim's check against a mutated engine and report whether it FLIPS.

One cell of the def-sweep grid.  The engine runs off its .pyc BUILD ARTIFACTS with ONE module's
bytecode swapped for its mutant; the ∅ baseline swaps a module's identity .pyc, a no-op.

⚑ Ζ·eval·split — THIS FILE WAS 238 LINES WITH A 127-LINE `main()` DOING FIVE JOBS, and ruff's
C901 + PLR0915 named it.  The operator's reading of that finding was the right one — *the whole
file should get n-split* — so three concerns moved out, each to a module with ONE subject:

    tools/cellargs.py     what the cell was ASKED to do (a typed record, not a Namespace)
    tools/cellstage.py    what the check SEES (bytecode placement, the four counterfactual kinds)
    tools/cellcgroup.py   what the cell COST (its own cgroup: peak memory, OOM events)

What remains is the cell's actual job: run the check, decide what its exit meant, record it.
The linter did not ask for tidier code; it said the file did too much.

⚑⚑ AND THE SPLIT COULD NOT LAND UNTIL `tools/` WAS A PACKAGE.  A bare `import cellcgroup` beside
this file works at RUNTIME (the interpreter puts a script's own directory on sys.path) and is
invisible to a CHECKER, which has no such rule — so decomposing a module into siblings created
edges nothing could follow.  Ζ·tools·package added the `__init__.py`: you cannot split a file
into siblings without a package to put them in.

⚑ THE COUNT, because it is the argument for the method: the original file reported 76 mypy
findings, and the great majority fanned out from `argparse.Namespace` attributes being `Any`.
Splitting the parse into a typed record (Ζ·argv·typed) collapsed them at the seam rather than
annotating 76 expressions downstream.

Idempotency: invoke by an ABSOLUTE interpreter path so `sys.executable` is populated — the check
re-spawns the projector as `[sys.executable, …]` (the history of the '' spurious-flip bug).
"""
from __future__ import annotations

import contextlib
import json
import os
import pathlib
import resource
import signal
import subprocess
import sys

from tools import cellargs, cellcgroup, cellstage

CANNOT_RUN = 3
WHY_CHARS = 300
CPU_GRACE = 3
BASELINE = "0"


def _cap_cpu(cpu: int) -> None:
    """Cap CPU time for this process and everything it forks.

    Μ·sweep·atom — a flip:/branch: mutant can make the check NON-TERMINATING (inverting
    `bib._unescaped_braces`'s `while` is the live example).  A mutant that never answers HAS
    flipped the check — a real behavioural change the sweep must see — and measuring CPU rather
    than wall keeps a lease-queued cell from a false flip.

    ⚑ NOT A `preexec_fn`, WHICH RUFF'S PLW1509 REFUSED AND WAS RIGHT TO.  `preexec_fn` runs
    between fork and exec, where a THREADED parent has only the calling thread while other
    threads' locks stay held forever.  This file is single-threaded, so it HAPPENS to be safe —
    and "happens to be safe" is what the rule exists to catch.  Setting the limit on the parent
    lets the child inherit it across fork+exec, with no callback in the unsafe window.
    """
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + CPU_GRACE))


def _last_line(raw: bytes | None) -> str:
    """Return the final non-empty output line — the check's own account of what happened."""
    if not raw:
        return ""
    lines = [ln for ln in raw.decode("utf-8", "replace").strip().splitlines() if ln.strip()]
    return lines[-1][:WHY_CHARS] if lines else ""


def _run(check: str, claim: str, wall: int) -> tuple[bool, str]:
    """Run one check; return (flipped, its last output line).

    ⚑ Ζ·sweep·message — EVERY CELL NOW KEEPS ITS LAST LINE, and the old reasoning for muting
    mutants was right about the wrong artifact.  `Ζ·eval·mute` captured output for the BASELINE
    only, because "48,011 tracebacks would be noise" — true of tracebacks, false of ONE LINE.
    Measured 2026-08-30: 77 → 126 bytes per record (+6.4 MiB over 137,553 cells) and +0.50 ms per
    cell (+69s SERIAL, and the grid runs parallel).  Against a ~3h sweep, noise.

    What it buys is a distinction paperkit's grading could not draw.  gcalculus stated the rule:
    *"it went red" is not evidence; "it went red HERE, saying THIS" is.*  A mutation the check
    genuinely CAUGHT and a mutation that broke the witness so it raised BEFORE the check ran are
    both `rc != 0` — one bit cannot separate them, one line can.

    ⚑ AND THE ENGINE'S OWN PRIMITIVE IS WHY IT MATTERS.  `mutate.py` plants an UNCATCHABLE
    `raise BaseException('PAPERKIT_MUT')` and statically REFUSES regions that could swallow it —
    real effort to make "the mutation REACHED the check" unambiguous.  That is orthogonal to
    whether the check NOTICED THE RIGHT THING, and care over the first makes the absence of the
    second more visible.

    This RECORDS a reason; it does not GATE on one.  A message PREDICATE is a per-cell contract
    change, and measure-before-gate is the order this repo uses.

    Both streams are merged because the check reports its diagnosis on STDOUT (concepts.py prints
    "concept X: …" there) — a stderr-only capture once reported "no stderr" for a check that had
    explained itself perfectly well one stream over.
    """
    p = subprocess.Popen(
        [sys.executable, check, claim],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, process_group=0)
    try:
        # ⚑ communicate(), NEVER wait() — a PIPE nothing drains DEADLOCKS the child the moment it
        # writes past the 64KB buffer.  Measured 2026-08-26 on the in-process path: a cell sat at
        # 0.0% CPU for 11+ minutes and `wchan` named both halves.  Capturing output and wait()ing
        # is exactly that bug; communicate() drains and waits in one call.
        out, _ = p.communicate(timeout=wall)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)  # the whole tree, no orphan spinning on
        p.wait()
        return True, f"did not terminate within {wall}s (killed) — the mutation flipped it"
    # `Popen.returncode` is `int | Any` in typeshed (it is None before the child exits), so the
    # narrowing is at the read, not downstream: after communicate() it is always an int.
    rc: int = p.returncode
    return rc != 0, _last_line(out)


def _env_int(name: str, default: int) -> int:
    """Read a positive integer knob from the environment, falling back to `default`."""
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def main(argv: list[str]) -> int:
    """Stage the counterfactual, run the check, and record whether it flipped and why."""
    a = cellargs.parse(argv)
    tag = cellstage.cache_tag()
    cellstage.place_engine(a.engine_dir, tag)
    cellstage.deliver(
        cellstage.Site(a.site, a.module, a.mutant_py, a.mutant_pyc,
                       a.content_path, a.content_textfile), tag)

    _cap_cpu(_env_int("PAPERKIT_CHECK_CPU", 60))
    before = cellcgroup.oom_counts()
    flipped, why = _run(a.check, a.claim, _env_int("PAPERKIT_CHECK_TIMEOUT", 600))

    if a.site == BASELINE and flipped:
        # the ∅ cell is the canary: sens.py FAILS LOUD on it rather than emitting a
        # plausible-but-wrong sens set, and it must say WHY on the spot.
        sys.stderr.write("eval: BASELINE FLIPPED (the identity mutation broke the check) — "
                         f"{why or 'no output'}\n")

    # Ζ·climb·oom·signal — an OOM is NOT a flip.  `rc != 0` is right for a HANG (a mutant that
    # never answers HAS changed behaviour) and wrong for a cell the kernel killed for memory:
    # that is a verdict about the HARNESS.  Measured on compose-chains: cap ≤32MB ⇒ "flipped",
    # cap ≥64MB ⇒ not — the same claim graded `broken` or `behavioral` by its memory ladder
    # alone.  Exiting non-zero hands the signal back to the layer that OWNS the retry
    # (cgroup-scope retries on a nonzero PAYLOAD exit, and this process IS the payload).
    if flipped and cellcgroup.oom_happened(before, cellcgroup.oom_counts()):
        sys.stderr.write("eval: OOM-KILLED at this cell's cap (not a flip) — deferring to the "
                         "climb\n")
        cellcgroup.write_peak(a.peak)
        return CANNOT_RUN

    cellcgroup.write_peak(a.peak)
    rec: dict[str, object] = {"claim": a.claim, "site": a.site, "flipped": flipped, "why": why}
    pathlib.Path(a.out).write_text(json.dumps(rec) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
