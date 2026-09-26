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
    # ⚑ W42 — SOFT == HARD.  With soft < hard the kernel sends SIGXCPU at the soft limit, whose
    # default action is a core dump: even at RLIMIT_CORE=0 each one reached systemd-coredump as a
    # crash record ("terminated abnormally with signal 24/XCPU"), so every mutant this cap stopped
    # — the EXPECTED outcome — read on luthen as a crash (62 in six hours).  Measured by luthen:
    # `prlimit --cpu=1 --core=0` → exit 137 (SIGKILL) and NO record; `--cpu=1:3` → exit 152 and a
    # record.  With soft == hard the first action is SIGKILL, so a coredump means a real crash.
    # The verdict does not change (_run folds any nonzero rc into a flip, -9 as -24 before); the
    # grace seconds did nothing a spinning mutant needed.
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    # Ζ·core·off — SIGXCPU's default action DUMPS CORE, so every mutant this cap stops wrote a core
    # file the verdict never reads.  The kill is the signal; the dump is only I/O and disk.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _cap_mem(mb: int) -> None:
    """Cap ADDRESS SPACE for this process and everything it forks — the memory twin of _cap_cpu.

    ⚑ Ζ·cell·rlimit — KEPT, BUT IT DID NOT FIX THE CASE IT WAS BUILT FOR, and saying so is the
    point of this note.  The theory was: a flip: mutant that loops WHILE APPENDING burns memory
    rather than CPU, so _cap_cpu never fires.  Proven to BIND in isolation (a runaway allocation
    raises MemoryError under it; a real witness passes), and REFUTED against the live cell —
    `concept-views__config__flip_positionals_arm_2` still exhausted the 4→8192MB climb with no
    MemoryError anywhere in the log.

    ⚑⚑ TWO REASONS IT CANNOT REACH THAT CELL, both of which the tree already documented:
      · calc.bzl:107 — cgroup-scope caps the cell with memory.max AND memory.swap.max=0, and its
        first rung is 4MB.  The cgroup OOM-kills the tree long before any process's ADDRESS SPACE
        reaches 2048MB, so RLIMIT_AS is never the binding constraint.  A second memory cap was
        added to a system that already had one.
      · config.positionals is a BOUNDED `for` over argv — it cannot spin.  Inverting its condition
        changes WHICH tokens survive, and gate.py:133 reads `pos[0]` with an empty-pos fallback to
        `Path.cwd()`.  So the flip does not make one process allocate; it makes the gate target a
        DIFFERENT project, resolve its concepts, and spawn another gate.  The runaway is PROCESS
        RECURSION, and neither a per-process RLIMIT nor a per-process CPU cap bounds a tree that
        grows by forking.

    This cap stays because it is correct for the case it names — a single process that allocates
    without bound is still worth stopping, and it costs one setrlimit.  It is NOT the fix for
    Ζ·mem·ceiling, and recording that here is cheaper than the next reader re-deriving it.

    MEASURED: `concept-views__config__flip_positionals_arm_2` inverts a condition in
    config.positionals (an argv-stripping loop) and exhausted the whole membudget climb TWICE —
    4→8→…→4096MB, then again to 8192MB after the ceiling was raised — killing a full //:hook run
    each time.  Neither the witness nor the closure explains it: the witness peaks at 28 MB against
    a 22 MB control, and the cell's cone is 10 of 26 engine modules, not the flat engine.

    ⚑⚑ THE CLIMB IS STILL THE WRONG INSTRUMENT, THOUGH NOT FOR THE REASON FIRST WRITTEN HERE.
    membudget doubles to DISCOVER a cell's honest footprint, and a RECURSING PROCESS TREE has no
    footprint to discover: every rung re-runs the recursion and dies the same way, so the climb
    turns a detectable flip into an exhausted ceiling reported as `not all outputs were created or
    valid` — a HARNESS verdict wearing a claim verdict's clothes.  ⚑ The first draft of this note
    said "a runaway allocation has no footprint" and proposed MemoryError as the honest answer.
    That was the refuted theory: no single process allocates without bound, so no per-process limit
    of any kind — memory or CPU — can convert this into a verdict.  What the sweep needs to see it
    is a bound on the TREE (a process count or a pids cgroup controller), which cgroup-scope
    already has the shape for and does not currently set.

    RLIMIT_AS rather than RLIMIT_DATA: it bounds mmap too, which is where a large list's realloc
    actually lands.  Set on the parent so the child inherits it across fork+exec — no preexec_fn,
    for the reason _cap_cpu records.
    """
    b = mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (b, b))


# ⚑ Ζ·cell·tree — THE BOUND ON THE TREE THAT _cap_mem's DOCSTRING SAYS IS MISSING, WITHOUT A CGROUP.
# `concept-views__config__flip_positionals_arm_2` is a fork-bomb mutant: flipping config.positionals
# makes the gate spawn gates recursively, and no per-process rlimit bounds a tree that grows by
# forking (see _cap_mem).  On the old host the per-cell cgroup held it.  In the REMOTE EXECUTOR
# (BuildBuddy, isolation `none`) there is NO per-action cgroup, so the tree grew until the whole
# executor pod OOM-killed — MEASURED 2026-09-23 by luthen-observability: pids.peak 15,491 against
# a normal 219, OOMKilled at 4Gi and again at 25Gi, the same action in flight both times, and every
# other tenant's work on that executor lost with it.
# The check already runs in its own process group (process_group=0), so the tree is countable from
# /proc — the pgrp field of each process's stat.  Counting between communicate() slices and killing
# the group past TREE_MAX turns the runaway into a FLIP with its reason, the same fold this file
# makes for a hang.  TREE_MAX sits far above a legitimate check's tree (a witness that runs a
# sibling gate is a handful of processes); the ∅ baseline cell FAILS LOUD if it is ever too low.
# The executor's pod pids limit (luthen's, pending) is the floor under every tenant; this is the
# bound that makes paperkit's own runaway a verdict instead of relying on that floor.
# ⚑ TREE_MAX IS A TRIGGER, NOT A HARD CAP — MEASURED 2026-09-23 on the live fork-bomb cell (inv
# 5a06cf57): the harness counted 279 at the poll that fired, but the executor pod's pids.peak was
# 562 (luthen-observability's 2 s sampler), because the recursion keeps forking for up to one
# TREE_POLL_S interval and during the kill sweeps.  So the real ceiling is "TREE_MAX + one poll of
# growth + kill latency" — a few hundred here, far below any pod limit, and nothing survived
# (pids back to 33).  Tighten the poll or lower the trigger only if that margin ever matters.
TREE_MAX = 256
# ⚑ 0.2s, NOT 0.05s — MEASURED 2026-09-23 (inv 00930313): at 50ms the harness's OWN /proc scans,
# made costlier by the growing tree, tripped the 60s RLIMIT_CPU that _cap_cpu sets on THIS process
# (the limit is inherited, and the parent's own time counts too), killing eval.py before it could
# write a verdict.  The bound fires early, while the tree is still small, so a slower poll costs
# little detection latency and keeps the scan's CPU well inside the cap.
TREE_POLL_S = 0.2

# ⚑⚑ BY ANCESTRY, NOT BY PROCESS GROUP — THE FIRST VERSION COUNTED THE PGID AND THE REAL BOMB
# ESCAPED IT.  The recursing gates run their own checks with process_group=0 (resolver.py does
# exactly what this file does), so every level of the recursion starts a NEW group: a pgrp count
# stayed tiny, the bound never fired, and killpg on one group orphaned the rest INSIDE THE SHARED
# EXECUTOR.  My local probe had used a flat single-group tree — it tested the shape I assumed, not
# the shape that exists.  So: count every DESCENDANT of this process by walking ppid, and register
# this process as a CHILD SUBREAPER so an orphaned descendant reparents to US (not to the pod's
# init), stays countable, and stays killable.  setsid/process_group changes a process's group and
# session; neither changes who its parent is.
_PR_SET_CHILD_SUBREAPER = 36


def _become_subreaper() -> None:
    """Make orphaned descendants reparent to this process (Linux prctl), so none escape the count.

    Best-effort: on a kernel or libc without it, orphans reparent to init and would escape — the
    count then still covers every descendant whose parent is alive, which is the recursion's shape.
    """
    import ctypes  # noqa: PLC0415 — Linux-only, used once, at the one site that needs it
    with contextlib.suppress(OSError, AttributeError):
        libc = ctypes.CDLL(None, use_errno=True)
        libc.prctl(_PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0)


def _descendants(root: int) -> list[int]:
    """Return every live descendant pid of `root`, from one /proc scan — no cgroup needed.

    A process that exits between listing and reading is simply not counted: vanished is gone.
    """
    # ⚑ ZOMBIES ARE NOT COUNTED.  As subreaper we inherit orphans, and one that exits becomes a
    # zombie under us until reaped — still a /proc entry.  Counting them would let a LEGITIMATE
    # check whose grandchildren outlive their parents creep toward TREE_MAX.  And they are NOT
    # reaped while the check runs: waitpid(-1) could reap the check itself out from under
    # communicate(), which would then report a wrong exit code.  Reaping happens in _kill_tree.
    children: dict[int, list[tuple[int, bool]]] = {}
    try:
        entries = os.listdir("/proc")
    except OSError:
        return []
    for name in entries:
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/stat", "rb") as fh:
                raw = fh.read()
        except OSError:
            continue
        # fields after the comm's closing ')': state ppid …  (comm may contain spaces/parens)
        rest = raw.rsplit(b")", 1)[-1].split()
        if len(rest) > 1:
            children.setdefault(int(rest[1]), []).append((int(name), rest[0] == b"Z"))
    out: list[int] = []
    frontier = [root]
    while frontier:
        nxt: list[int] = []
        for pid in frontier:
            for c, zombie in children.get(pid, ()):
                if not zombie:
                    out.append(c)
                nxt.append(c)
        frontier = nxt
    return out


def _kill_tree(p: subprocess.Popen[bytes]) -> None:
    """SIGKILL every descendant of this process until none survive, then reap them all.

    Repeated because a fork bomb can create members between one sweep and the next; reaped
    because, as subreaper, orphans are OUR children and would otherwise linger as zombies.
    """
    me = os.getpid()
    for _ in range(50):
        victims = _descendants(me)
        if not victims:
            break
        for pid in victims:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGKILL)
        with contextlib.suppress(ChildProcessError):
            while os.waitpid(-1, os.WNOHANG)[0] > 0:
                pass
    with contextlib.suppress(Exception):
        p.wait(timeout=5)


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
    # ⚑ Ζ·cell·pids — A FORK THAT CANNOT HAPPEN IS A FLIP, and this Popen sat OUTSIDE the try.
    # The pids bound (cgroup-scope) stops a mutant that recurses by forking — measured: the bound
    # FIRED, `BlockingIOError: [Errno 11] Resource temporarily unavailable` at _fork_exec.  But the
    # budget is exhausted by the CHECK's own recursion, so the next process that cannot fork is
    # EVAL.PY ITSELF, one frame above: the harness died before writing .eval.json and bazel reported
    # `not all outputs were created or valid` — a HARNESS verdict, the exact fold this file refuses
    # for the non-terminating case one function up ("A mutant that never answers HAS flipped the
    # check").  Same argument, the other resource: a mutant that exhausts the process budget has
    # flipped it too, and the harness must SAY so rather than die of it.
    _become_subreaper()  # Ζ·cell·tree — orphaned descendants must stay countable and killable
    try:
        p = subprocess.Popen(
            [sys.executable, check, claim],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, process_group=0)
    except OSError as e:
        return True, f"could not spawn the check ({e.__class__.__name__}: {e}) — the mutation exhausted the cell's process budget, which is a flip"
    # ⚑ communicate(), NEVER wait() — a PIPE nothing drains DEADLOCKS the child the moment it
    # writes past the 64KB buffer.  Measured 2026-08-26 on the in-process path: a cell sat at
    # 0.0% CPU for 11+ minutes and `wchan` named both halves.  Capturing output and wait()ing
    # is exactly that bug; communicate() drains and waits in one call.  It is called in short
    # SLICES so the tree can be counted between them (communicate() may be re-called after a
    # TimeoutExpired without losing output).
    tree_max = _env_int("PAPERKIT_CHECK_TREE", TREE_MAX)
    waited = 0.0
    while True:
        try:
            out, _ = p.communicate(timeout=TREE_POLL_S)
            break
        except subprocess.TimeoutExpired:
            waited += TREE_POLL_S
        size = len(_descendants(os.getpid()))
        if size > tree_max:
            _kill_tree(p)
            return True, (f"process tree reached {size} > {tree_max} (killed) — the mutation "
                          "recursed by forking, which is a flip")
        if waited >= wall:
            _kill_tree(p)
            return True, f"did not terminate within {wall}s (killed) — the mutation flipped it"
    # `Popen.returncode` is `int | Any` in typeshed (it is None before the child exits), so the
    # narrowing is at the read, not downstream: after communicate() it is always an int.
    rc: int = p.returncode
    # ⚑ W42/W32 — A CAP KILL SAYS SO.  A child killed at the CPU cap (SIGKILL now that soft ==
    # hard; SIGXCPU before) left only its last output line, which says nothing about why it died —
    # the same blindness that let a deterministic CPU kill read as a "flake" in a consumer.  The
    # verdict is unchanged (any nonzero rc is a flip); only the RECORDED reason gains the cause.
    if rc in (-signal.SIGKILL, -signal.SIGXCPU):
        cap = resource.getrlimit(resource.RLIMIT_CPU)[1]
        used = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu_s = used.ru_utime + used.ru_stime
        # 90%, not ≥: the kernel kills AT the limit and the reaped child's accounted time lands just
        # under it (measured: a 2s cap reported <2.0).  An OOM kill (-9 too) burns far less, so
        # the margin still separates the two.
        if cap != resource.RLIM_INFINITY and cpu_s >= 0.9 * cap:
            return True, (f"exceeded its {cap}s CPU cap ({cpu_s:.1f}s used; killed by "
                          f"{signal.Signals(-rc).name}) — the mutation made it spin, which is a flip")
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
    # Ζ·cell·rlimit — 2048MB: an order of magnitude above the 28 MB a real witness peaks at,
    # and well under the 4096MB rung that a runaway allocation blew through.
    _cap_mem(_env_int("PAPERKIT_CHECK_MEM_MB", 2048))
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
