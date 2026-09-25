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
        # ⚑ Ζ·arm·sound — AN ABSENT PRECONDITION IS `cannot-run`, NOT `fail`.  This arm WRITES the
        # build cgroup's cpu.weight and asserts it reads back 37.  A sandboxed cell cannot write
        # that file, so the arm reddened on a MISSING CAPABILITY while passing on the host — the
        # exact fold the engine refuses everywhere else: "a cannot-run is not a refutation"
        # (verb.bzl maps exit 3 to cannot-run, and verdict.py's aggregator bad-set is {fail}
        # alone).  ⚑⚑ FOUND ONLY BECAUSE Ζ·account·stdout STARTED CARRYING THE CHECK'S OUTPUT: the
        # verdict record held one bit and the suite prints its arms to stdout, which the cell
        # discarded.  The probe is the OWNER's own `_writable_weight_file`, already used one arm
        # above — asking the module whether the capability exists rather than inferring it.
        if build_f == self_f:
            print(f"  ~~ δ: apply() — SKIPPED: the caller's cgroup IS the build's ({build_f}), so "
                  "'weights the BUILD's' and 'leaves the CALLER's untouched' name one file and "
                  "cannot both hold.  The property needs two DISTINCT cgroups to be measurable.")
            raise SystemExit(3)
        try:
            W.apply(37)                               # default path: targets the BUILD's cgroup
            _bw, _sw = build_f.read_text().strip(), self_f.read_text().strip()
            print(f"     [δ operands] build_f={build_f} -> {_bw!r} (want 37); "
                  f"self_f={self_f} -> {_sw!r} (want {before!r})")
            # ⚑ this line is why the precondition is right: it showed both paths resolving to
            # paperkit-build.scope/cpu.weight in a cell, which no amount of reading would have.
            check("δ: apply() weights the BUILD's cgroup, and the CALLER's is untouched",
                  _bw == "37" and _sw == before)
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

    # ⚑ A DECOY WHOSE LIFETIME WE END, NOT ONE WE WAIT OUT (a peer's RAII-by-liveness form).
    #
    # This was `Popen(["sleep", "3", "linux-sandbox"])` — a duration neither needed nor
    # controlled, which is only correct while 3s happens to exceed the inspection.  The child
    # now BLOCKS ON A PIPE THE PARENT HOLDS: it exits on EOF when we close the write end, so it
    # is alive across exactly the inspection and not one instant longer.
    #
    # `exec -a linux-sandbox cat` sets the two fields INDEPENDENTLY, which is the whole point of
    # the decoy: comm comes from the executable (`cat`), argv[0] from the exec argument
    # (`linux-sandbox`).  MEASURED: comm='cat', argv='linux-sandbox'.
    # ⚑⚑ AND THE SIMPLER FORM, FROM A SECOND PEER: `cat <sentinel>` needs no exec at all.
    # The first version of this ran `bash -c "exec -a linux-sandbox cat"`, which works but makes
    # /proc briefly show comm='bash' with an empty cmdline while bash execs — so it needed a poll
    # loop to wait for the transition.  Spawning `cat` DIRECTLY has no transition: comm is 'cat'
    # (the executable) and the sentinel is an ordinary argv token, both correct on the FIRST read.
    # Removing the exec removed the race rather than tolerating it.
    _r, _w = os.pipe()
    decoy = subprocess.Popen(["cat", "-", "linux-sandbox-sentinel"], stdin=_r,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(_r)              # only the child holds the read end; it blocks until we close _w
    try:
        # ⚑ NO SLEEP.  This read `time.sleep(0.2)` — load-bearing for the OLDER assertion, which
        # walked /proc and needed the decoy visible to a scan.  The rewrite below reads ONE file
        # by pid, and MEASURED five for five, /proc/<pid>/comm is readable the instant Popen
        # returns.  The wait survived the assertion it existed for: a fix that changes what an
        # arm asserts must revisit the setup that assertion required.
        # And the live check must AGREE with the rule: verify() uses comm, so a decoy naming
        # linux-sandbox in its argv must not appear as a cell.
        # ⚑ Ζ·cpuweight·arm — ASSERT ON THE DECOY, NOT ON A GLOBAL VERDICT'S PROSE.
        #
        # This read `okd, whyd = W.verify(cgv)` and then tested three SUBSTRINGS of the human
        # message — `"nothing to verify" in whyd or "0 cell" in whyd or "all " in whyd` —
        # while `okd`, the bool the function returns, was bound and never used.  Three defects
        # in one arm, and the third is why it mattered:
        #
        #   * IT READ THE WRONG FIELD.  verify() returns (bool, explanation).  Any rewording of
        #     those three messages, down to a typo fix, silently changes what this arm asserts.
        #   * ONE PROBE COULD NEVER MATCH.  `"0 cell"` never appears: the zero case returns
        #     "nothing to verify", and the plural is `{inside} cell(s)`, so a genuine zero
        #     renders "all 0 cell(s) inside" — caught by `"all "`.  Dead code inside a guard.
        #   * AND IT WAS NONDETERMINISTIC, IN A NEGATIVE CONTROL.  verify() counts EVERY cell on
        #     the box, so under load it returns the OUTSIDE string and this F arm RED; idle, it
        #     returns "nothing to verify" and the arm GREEN.  Measured both ways an hour apart,
        #     and the green was published as a result.  An arm whose job is to prove the check
        #     CAN fail is worthless if its own outcome tracks machine state.
        #
        # The claim the decoy exists to make is narrow: a process whose ARGV contains
        # "linux-sandbox" but whose COMM is not a cell comm must not count as one.  That is
        # `is_cell(comm)` — a pure function over one string, deterministic, no ambient state —
        # so the arm asks IT, about THIS process, rather than asking a whole-box aggregate and
        # reading its sentence.
        # ⚑ POLL ON THE CONDITION, NEVER ON THE CLOCK.  bash must exec before /proc reflects
        # the final image, so this waits for a COUNTABLE EVENT — both fields settled — rather
        # than for a guessed interval.  A peer's phrasing: replace a timing window with a
        # countable one, and if the condition never arrives the assertion fails HONESTLY in the
        # output rather than passing on a lucky schedule.
        # Ζ·cpuweight·poll — the paragraph above SPECIFIED this poll and the code below did two
        # unconditional reads, so the race it describes was live: under load the read beats the
        # exec, /proc/<pid>/cmdline still holds bash's pre-exec image, the sentinel is absent and
        # the premise arm reds while the arm that DEPENDS on it passes (comm had settled, cmdline
        # had not).  The countable event is both fields carrying the post-exec image; the loop is
        # bounded by the child's own liveness, so a decoy that never execs fails HONESTLY here
        # rather than on a lucky schedule.
        decoy_comm, decoy_argv = "", b""
        for _ in range(2000):
            decoy_comm = Path(f"/proc/{decoy.pid}/comm").read_text().strip()
            decoy_argv = Path(f"/proc/{decoy.pid}/cmdline").read_bytes()
            if b"linux-sandbox" in decoy_argv and decoy_comm:
                break
            if decoy.poll() is not None:   # the child died before exec'ing — stop, do not spin
                break
        check("F: the decoy's ARGV carries the sentinel (the premise the next arm needs)",
              b"linux-sandbox" in decoy_argv)
        check(f"F: the decoy's argv says linux-sandbox but its comm is {decoy_comm!r}, "
              "and is_cell() reads comm — so it is not a cell",
              not W.is_cell(decoy_comm))
    finally:
        os.close(_w)          # EOF -> the child exits; its lifetime ended by US, not by a timer
        decoy.wait(timeout=5)   # rc is incidental — cat fails on the sentinel, which is argv, not a file

    print(f"CPUWEIGHT BOUNDARIES: {'PASS' if not _fails else 'FAIL'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

