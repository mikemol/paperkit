#!/usr/bin/env python3
"""Ζ·cell·admit — put the build's OWN cgroup under a proportional CPU weight.

THE PROBLEM.  Bazel's local scheduler admits actions against RAM (`--local_resources=memory`)
and its own job count.  It has NO view of the box: another repo's test suite running
concurrently is invisible to it, so two individually-reasonable builds oversubscribe together.
Measured here at 4.7-5.4 runnable/core on 10 cores with procs_blocked=0 (pure CPU contention,
not an I/O wedge) while substrate ran its selftests alongside paperkit's grid.

WHY THIS IS THE ONLY LEVER.  paperkit used to ALSO set SCHED_BATCH + nice 19 + a 100ms slice
per-cell (Ζ·sched-batch).  All three were removed: they were not orthogonal to this weight, they
fought it.  Verified against kernel/sched/ on 7.0.0-30.30 and by a live A/B:
  * SCHED_BATCH is VESTIGIAL post-EEVDF.  Its only semantic site is `fair_policy()` in
    kernel/sched/sched.h, which returns true for BATCH and NORMAL alike -- the fair class cannot
    tell them apart.  The GENTLE_FAIR_SLEEPERS wakeup-preemption path it once suppressed is gone.
  * nice 19 is INTRA-group: calc_group_shares() clamps a group's share to tg_shares (this
    cpu.weight), so nice can never RAISE it -- but the group's `load` term is the sum of member
    task weights, so nice 19 (weight 15 vs NICE_0_LOAD 1024) shrinks it ~68x and can push the
    group toward MIN_SHARES under contention.  It fights the weight downward.
  * the 100ms slice is converted to virtual time by calc_delta_fair(), scaled INVERSELY with task
    weight -- so nice 19 inflated it ~68x, putting our virtual deadlines ~6.8s out and making our
    own cells the last thing EEVDF picks whenever anything else is eligible.
Measured A/B (3 tuned vs 3 untuned burners, same contention): untuned 19.2-25.0M iters (1.3x
spread), tuned 4.2-26.2M (6.2x spread), worst tuned cell 4.5x slower than its untuned peer.
A scheduling class governs who yields once running; it cannot govern ADMISSION, which is what we
actually needed -- and this weight governs SHARE, which is the honest lever for "yield to the
operator's interactive work."  Reducing context-switching WITHIN the group is a THIRD question
(fewer concurrent cells), and no scheduling policy answers it.

WHY A WEIGHT AND NOT A CAP.  A hard wall (CPUQuota, a --jobs cap) cannot lend idle capacity:
cassian measured CPUQuota=50% starving postgres to 0.496 cores while 9.4 cores sat IDLE.
cpu.weight is PROPORTIONAL -- it yields under contention and takes ALL spare CPU at idle, which
is what a background build should do on an interactive machine.  It also avoids the priority
inversion a hard SCHED_BATCH risks: a weighted task keeps a small-but-nonzero share, so a cell
holding a lock (an action-cache entry, a shared fd) never fully deschedules.  This is the form
cassian's postgres quadlet settled on (CPUWeight=20) after trying both alternatives.

WHY THIS CGROUP.  The weight must sit on the cgroup that CONTAINS THE WORK.  Two placements
were measured and rejected:
  * per-cell `systemd-run`: needs DBUS_SESSION_BUS_ADDRESS + XDG_RUNTIME_DIR, which Bazel's
    sandbox scrubs -- the documented reason .bazelrc calls systemd-run "dead in the scrubbed
    sandbox env".
  * a scope we launch bazel INTO: the server daemonizes, and a setsid child ESCAPES the scope
    back to the terminal's cgroup (measured).  The weight would be set on a cgroup the cells
    are not in -- a lever that reads back correctly while doing nothing, which is strictly
    worse than no lever (cassian's io.weight-on-`none`-scheduler trap, one axis over).
So we weight the cgroup the cells ACTUALLY land in, discovered at runtime from a live cell
rather than assumed: under `mise exec -- bazel` every sandbox and cell shares one scope.

Best-effort by construction: on a machine without cgroup-v2, without `cpu` delegated to the
user hierarchy, or with the file unwritable, this is a no-op and the build proceeds unweighted.
A QoL lever must never be able to fail a build.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

CGROUP_ROOT = Path("/sys/fs/cgroup")
DEFAULT_WEIGHT = 20  # cassian's postgres figure: yields hard under contention, all spare at idle


def _cgroup_of(pid: str | int) -> str | None:
    """The cgroup-v2 path of a pid, or None. Line format: `0::/the/path`."""
    try:
        for line in Path(f"/proc/{pid}/cgroup").read_text().splitlines():
            hid, ctrl, path = line.split(":", 2)
            if hid == "0" and ctrl == "":       # the unified hierarchy
                return path
    except OSError:
        pass
    return None


def _self_cgroup() -> str | None:
    return _cgroup_of("self")


def _writable_weight_file(cg: str) -> Path | None:
    """`cpu.weight` for a cgroup path, if it exists and we may write it.

    `cpu` must be enabled in the parent's subtree_control for the file to exist at all; we test
    for the file rather than parsing subtree_control, since the file's presence IS the
    delegation (and os.access answers the ownership question directly).
    """
    f = CGROUP_ROOT / cg.lstrip("/") / "cpu.weight"
    return f if f.is_file() and os.access(f, os.W_OK) else None


def _app_slice() -> str:
    """The user's app.slice — the parent under which we create the build's cgroup.

    Derived from OUR OWN cgroup rather than hardcoded: everything up to and including
    `app.slice` is the user's session hierarchy, and that is where transient scopes live.
    """
    cg = _cgroup_of("self") or ""
    marker = "/app.slice"
    i = cg.find(marker)
    return cg[:i + len(marker)] if i >= 0 else cg


def build_cgroup(name: str = "paperkit-build.scope") -> tuple[str | None, str]:
    """CREATE (or reuse) a cgroup that holds the build, and nothing else.

    Ζ·cell·admit·site — the earlier version of this tool tried to DISCOVER which cgroup the
    cells had landed in and then prove that cgroup safe to weight.  That was the wrong shape:
    under `mise exec -- bazel` the cells get a dedicated scope, but under a bare `bazel` they
    inherit the CALLER's cgroup -- the operator's terminal, alongside their editor and browser
    (measured: 87 foreign processes, including soffice.bin and chrome_crashpad).  Weighting that
    would throttle the machine to make a build slower.  Distinguishing the two cases after the
    fact required scanning every process in the subtree and guessing which were "build-ish" --
    a heuristic standing in for a fact we can simply establish.

    So: do not inspect a cgroup, MAKE one.  cgroup-v2 is a hierarchy and `cpu` is delegated to
    the user session, so we can mkdir our own node under app.slice and move the build into it.
    Membership is then true by CONSTRUCTION -- only what we put there is there -- and the weight
    provably applies to the build and nothing else.  No scan, no hints, no ancestry walk.
    """
    parent = _app_slice()
    if not parent:
        return None, "no cgroup-v2 hierarchy — unweighted"
    d = CGROUP_ROOT / parent.lstrip("/") / name
    try:
        d.mkdir(exist_ok=True)
    except OSError as e:
        return None, f"cannot create {d} ({e}) — unweighted"
    if not (d / "cpu.weight").is_file():
        return None, (f"`cpu` not delegated to {parent} — the weight file does not exist in a "
                      f"cgroup we own; unweighted")
    return f"{parent}/{name}", f"{parent}/{name}"


def join(cg: str, pid: str | int = "self") -> tuple[bool, str]:
    """Move a process into `cg`. Moving a pid moves that process only; its FUTURE children
    inherit the cgroup.
    """
    try:
        (CGROUP_ROOT / cg.lstrip("/") / "cgroup.procs").write_text(
            f"{os.getpid() if pid == 'self' else pid}\n")
        return True, cg
    except OSError as e:
        return False, f"cannot join {cg} ({e})"


def build_servers() -> list:
    """Every long-lived Bazel SERVER JVM — the processes that actually fork this build's cells.

    Ζ·cell·admit·server — joining the launcher is NOT enough, and believing it was is the whole
    defect this function exists to close.  Bazel's client does not run the actions: it hands the
    request to a persistent server JVM that survives between invocations.  Cells are forked by
    THAT process, so they inherit ITS cgroup, and a client that joins a fresh scope moves only
    itself.  Measured: the server had been alive for 2h14m in the operator's terminal cgroup,
    the client joined the new scope, `cpuweight` printed joined=True, and every cell landed in
    the terminal's cgroup at weight 100 while the build scope sat empty with 0 procs.

    A lever that reports success while doing nothing to the work is strictly worse than no
    lever — the failure this module's own docstring warns about, committed anyway one layer up.
    The check that would have caught it is not "did I create and join a cgroup" but "are the
    CELLS in it", which is what verify() below asks.
    """
    out = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            argv = (d / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
        except OSError:
            continue
        # the server announces itself as `bazel(<workspace>)`; the client does not
        if "bazel(" in argv:
            out.append(d.name)
    return out


# The cell predicate, named so a test can exercise THIS function rather than restate the rule
# (a guard that carries its own copy of the set it guards certifies a tautology).  Matches on
# COMM — the executable's own name — never on argv: a /proc/*/cmdline substring test matches the
# checking process and any shell running `pgrep -f linux-sandbox` beside it.
_CELL_COMMS = ("linux-sandbox", "process-wrapper")


def is_cell(comm: str) -> bool:
    """Whether a process COMM is one of this build's cells."""
    return comm in _CELL_COMMS


def verify(cg: str) -> tuple[bool, str]:
    """Are this build's CELLS actually in `cg`?  The property that matters, versus the one the
    earlier version tested (that a cgroup was created and the caller joined it).
    """
    inside = outside = 0
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        # Match on COMM (the executable's own name), never on the full argv: a substring test
        # over /proc/*/cmdline matches this process's OWN command line, and any shell running a
        # `pgrep -f linux-sandbox` alongside it.  Measured: the argv form reported 10 cells
        # outside the scope, two of which were the verification itself and its parent shell.
        # An instrument that counts itself cannot answer the question it was built for.
        try:
            comm = (d / "comm").read_text().strip()
        except OSError:
            continue
        if is_cell(comm):
            if _cgroup_of(d.name) == cg:
                inside += 1
            else:
                outside += 1
    if inside == 0 and outside == 0:
        return True, "no cells running yet — nothing to verify"
    if outside:
        return False, f"{outside} cell(s) OUTSIDE {cg} ({inside} inside) — the weight is inert"
    return True, f"all {inside} cell(s) inside {cg}"


def apply(weight: int = DEFAULT_WEIGHT, pid: str | int | None = None) -> tuple[bool, str]:
    """Set cpu.weight on the BUILD's cgroup (or `pid`'s, when given explicitly)."""
    if pid is not None:
        cg = _cgroup_of(pid)
    else:
        cg, why = build_cgroup()
        if cg is None:
            return False, why
    if cg is None:
        return False, "no cgroup-v2 entry (not a cgroup-v2 machine?) — unweighted"
    f = _writable_weight_file(cg)
    if f is None:
        return False, f"cpu.weight not writable for {cg} (cpu not delegated?) — unweighted"
    try:
        before = f.read_text().strip()
        if before == str(weight):
            return False, f"already at {weight} ({cg})"
        f.write_text(f"{weight}\n")
        return True, f"{before} → {weight} ({cg})"
    except OSError as e:
        return False, f"cpu.weight write failed ({e}) — unweighted"


def runnable_ratio() -> tuple[float, int]:
    """(procs_running / cores, procs_blocked) — the box's CPU-contention reading.

    procs_running counts tasks that want CPU NOW.  It is NOT loadavg: the 1-minute average is
    decayed (it lags a burst and lingers after one) and counts D-state as runnable, so it cannot
    tell a CPU-saturated box from an I/O-wedged one.  procs_blocked carries the I/O half, so the
    PAIR discriminates: high ratio with blocked≈0 is pure CPU contention.
    """
    running = blocked = 0
    for line in Path("/proc/stat").read_text().splitlines():
        if line.startswith("procs_running"):
            running = int(line.split()[1])
        elif line.startswith("procs_blocked"):
            blocked = int(line.split()[1])
    return running / (os.cpu_count() or 1), blocked


def main(argv: list) -> int:
    """`--report` reads the box; `--exec CMD...` puts THIS process in the weighted cgroup and
    execs CMD (so every child of the build inherits it); bare invocation just creates+weights.
    """
    weight = DEFAULT_WEIGHT
    for i, a in enumerate(argv):
        if a == "--weight" and i + 1 < len(argv):
            weight = int(argv[i + 1])
        elif a.startswith("--weight="):
            weight = int(a.split("=", 1)[1])
    if "--report" in argv:
        ratio, blocked = runnable_ratio()
        print(f"runnable/core={ratio:.2f} blocked={blocked} cores={os.cpu_count()}")
        return 0

    cg, why = build_cgroup()
    if cg is None:
        print(f"cpu.weight: {why}", file=sys.stderr)
    else:
        changed, why = apply(weight)
        joined, jwhy = join(cg)
        # Ζ·cell·admit·server — move the SERVER too.  It forks the cells, it outlives any single
        # invocation, and joining only the client leaves every cell in whatever cgroup the server
        # was started in.  Moving a pid moves that process alone, so this must name the server
        # explicitly; its already-running children stay put, but every cell forked from here on
        # inherits the scope.
        moved = [q for q in build_servers() if join(cg, q)[0]]
        ratio, blocked = runnable_ratio()
        print(f"cpu.weight: {why}; joined={joined}; servers_moved={len(moved)}; "
              f"box runnable/core={ratio:.2f} blocked={blocked}", file=sys.stderr)

    if "--verify" in argv:
        cg2, _ = build_cgroup()
        ok, why2 = verify(cg2) if cg2 else (False, "no build cgroup")
        print(f"cpuweight verify: {why2}", file=sys.stderr)
        return 0 if ok else 1

    if "--exec" in argv:
        cmd = argv[argv.index("--exec") + 1:]
        if not cmd:
            print("cpuweight: --exec needs a command", file=sys.stderr)
            return 2
        os.execvp(cmd[0], cmd)                  # inherits the cgroup we just joined
    return 0                                    # best-effort: never fail the build


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
