#!/usr/bin/env python3
"""Behavioral-boundary examples for the CPU-weight admission lever — tools/cpuweight.py.

⟨P, F, δ⟩ per the boundary practice.  The tool puts the BUILD's cgroup under a proportional
cpu.weight so a background grid yields to interactive work under contention while still taking
all spare CPU at idle.  Bounds: it weights the cgroup the CELLS run in, it is a no-op (never a
failure) wherever the lever is unreachable, and the minimum delta between pass and flag is
WHICH CGROUP is targeted — the defect this suite exists for is a weight that lands on the
operator's terminal instead of the build, which reads back as success while doing nothing.

    python3 paperkit/tests/boundaries_cpuweight.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))
import cpuweight as W

_fails = []


def check(desc, ok):
    print(f"  {'ok' if ok else 'XX'} {desc}")
    if not ok:
        _fails.append(desc)


def main() -> int:
    print("CPUWEIGHT BOUNDARIES ⟨P, F, δ⟩")

    # ---- the reading (P): the box's contention signal is the runnable RATIO, not loadavg ----
    ratio, blocked = W.runnable_ratio()
    check("P: runnable_ratio() reads a non-negative ratio and a blocked count",
          ratio >= 0 and blocked >= 0)
    check("P: the ratio is per-core (procs_running normalised by cpu_count)",
          abs(ratio * (os.cpu_count() or 1) - round(ratio * (os.cpu_count() or 1))) < 1e-9)

    # ---- δ: the SITE.  The defect worth a suite: a weight that lands on the OPERATOR'S
    # cgroup instead of the build's, throttling their terminal/editor while the build runs
    # unweighted.  The tool answers this by CONSTRUCTION -- it creates its own cgroup rather
    # than discovering one -- so the arm asserts membership is exclusive, not merely likely.
    self_cg = W._cgroup_of("self")
    cg, why = W.build_cgroup("paperkit-boundaries-test.scope")
    check("δ: build_cgroup() CREATES a cgroup (does not adopt the caller's)",
          cg is not None and cg != self_cg)
    if cg:
        d = W.CGROUP_ROOT / cg.lstrip("/")
        check("δ: the created cgroup is EMPTY — membership is by construction, not inspection",
              d.joinpath("cgroup.procs").read_text().strip() == "")
        check("δ: it exposes a writable cpu.weight (the `cpu` controller is delegated)",
              W._writable_weight_file(cg) is not None)
        # the caller's own cgroup must be untouched by any of this
        # ACTUALLY run apply() and confirm the caller's cgroup is untouched — the vacuous
        # version of this arm (guarded so it never ran) would pass against the very bug it
        # names, since a test that does not exercise the path cannot observe the damage.
        self_f = W.CGROUP_ROOT / self_cg.lstrip("/") / "cpu.weight"
        before = self_f.read_text().strip()
        build_f = W.CGROUP_ROOT / W.build_cgroup()[0].lstrip("/") / "cpu.weight"
        build_before = build_f.read_text().strip()
        try:
            W.apply(37)                               # default path: targets the BUILD's cgroup
            check("δ: apply() weights the BUILD's cgroup, and the CALLER's is untouched",
                  build_f.read_text().strip() == "37"
                  and self_f.read_text().strip() == before)
        finally:
            build_f.write_text(f"{build_before}\n")  # idempotent: leave no state behind
        try:
            d.rmdir()
        except OSError:
            pass

    # ---- F: the lever is unreachable → a NO-OP with a named reason, never a failure ----
    d = Path(tempfile.mkdtemp())
    try:
        real_root = W.CGROUP_ROOT
        W.CGROUP_ROOT = d                       # an empty tree: no cpu.weight anywhere
        changed, why = W.apply(20, pid="self")
        check("F: cpu.weight absent → no change, and the reason NAMES the cgroup",
              changed is False and "not writable" in why)
        check("F: an unreachable lever still returns cleanly (a QoL knob never fails a build)",
              isinstance(changed, bool) and isinstance(why, str))
    finally:
        W.CGROUP_ROOT = real_root
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    # ---- F: a bogus pid has no cgroup → named no-op, not a traceback ----
    changed, why = W.apply(20, pid=2 ** 30)
    check("F: a nonexistent pid → no change, reason names the missing cgroup entry",
          changed is False and "cgroup" in why)

    # ---- P: main() is best-effort — it returns 0 even when it cannot weight anything ----
    check("P: main() exits 0 even when the lever is unreachable (never fails a build)",
          W.main(["--weight=20", "--report"]) == 0)

    # ---- Ζ·cell·admit·server: the property that MATTERS is where the CELLS are ----
    # The earlier suite asked "was a cgroup created and joined", and that passed while every
    # cell ran outside it at weight 100: bazel's client does not fork the actions, a persistent
    # server JVM does, and it outlives any invocation (measured: alive 2h14m in the operator's
    # terminal cgroup while `joined=True` was printed).  A success message about the action is
    # not evidence about the outcome.
    check("server: the servers that fork cells are enumerable",
          isinstance(W.build_servers(), list))
    cgv, _ = W.build_cgroup()
    ok_v, why_v = W.verify(cgv) if cgv else (False, "no cgroup")
    check("server: verify() answers about CELLS, not about the cgroup's existence",
          isinstance(ok_v, bool) and ("cell" in why_v or "nothing to verify" in why_v))
    # F: the instrument must not COUNT ITSELF.  A /proc/*/cmdline substring test matches this
    # very process and any shell running `pgrep -f linux-sandbox` beside it — measured: it
    # reported 10 cells outside, two of which were the check and its parent shell.
    # Compare the COUNT, not the pass/fail: a decoy that lands inside the scope keeps `ok` True
    # under both readings, so a tuple comparison here would pass against the very bug it names.
    import re
    import subprocess

    # A process whose ARGV names linux-sandbox but whose COMM does not — the exact shape that
    # fooled the first version (it counted the verification's own shell).  Asserted by the
    # DIFFERENCE the two rules give on the SAME process set, so the arm needs no live build.
    # Ζ·cell·admit — the MATCHING RULE, tested on a fixed input rather than on live /proc.
    # Earlier versions spawned a decoy and compared counts; that is flaky by construction (the
    # population changes under the test, and a `bash -c "... # marker"` decoy execs the marker
    # away before it is sampled).  A rule is a function; test it as one.
    argv_rule = lambda a, c: ("linux-sandbox" in a or "execroot/_main" in a)
    comm_rule = lambda a, c: W.is_cell(c)          # the LIVE predicate, not a copy of it
    #                     (argv,                                    comm)
    A_CELL = ("/x/linux-sandbox -W /tmp -- python3 check.py", "linux-sandbox")
    A_PROBE = ("pgrep -f linux-sandbox", "pgrep")
    A_SHELL = ("bash -c grep linux-sandbox /tmp/execroot/_main", "bash")
    check("F: the comm rule counts a real cell and NOT a process merely naming one",
          comm_rule(*A_CELL) and not comm_rule(*A_PROBE) and not comm_rule(*A_SHELL))
    check("F: the argv rule counts ALL THREE — it counts the instrument and its own shell",
          argv_rule(*A_CELL) and argv_rule(*A_PROBE) and argv_rule(*A_SHELL))
    check("F: so the two rules DISAGREE on exactly the self-matches (the measured defect: "
          "10 argv-matched vs 6 real, two of them the check and its parent)",
          sum(argv_rule(*x) for x in (A_CELL, A_PROBE, A_SHELL)) -
          sum(comm_rule(*x) for x in (A_CELL, A_PROBE, A_SHELL)) == 2)

    decoy = subprocess.Popen(["sleep", "3", "linux-sandbox"], stderr=subprocess.DEVNULL)
    try:
        time.sleep(0.2)
        # And the live check must AGREE with the rule: verify() uses comm, so a decoy naming
        # linux-sandbox in its argv must not appear as a cell.
        okd, whyd = W.verify(cgv) if cgv else (True, "no cgroup")
        check("F: verify() does not report the decoy as a cell",
              "nothing to verify" in whyd or "0 cell" in whyd or "all " in whyd)
    finally:
        decoy.kill(); decoy.wait()

    print(f"CPUWEIGHT BOUNDARIES: {'PASS' if not _fails else 'FAIL'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
