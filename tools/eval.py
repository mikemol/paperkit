#!/usr/bin/env python3
"""Ζ·mutant·eval — run a claim's check against the engine RUN OFF ITS .pyc BUILD ARTIFACTS, with ONE
module's bytecode swapped for its mutant, and report whether the mutation FLIPS the check.

The engine is compiled once (//paperkit:pyc, Ζ·pyc·engine) and staged as `paperkit/<relpath>.pyc`
beside the source `paperkit/<relpath>.py`.  This tool places each precompiled .pyc at its real
import location — `paperkit/<dir>/__pycache__/<stem>.<cache-tag>.pyc` — so Python runs the bytecode
directly (UNCHECKED_HASH ⇒ the source is never rechecked; see tools/pyc.py).  The counterfactual is
delivered by overwriting the ONE mutated module's __pycache__ slot with its mutant .pyc — the .py
stays original (only for findability + __file__).  The ∅ baseline passes the module's own identity
.pyc, a no-op swap.  No import-time compilation: the def-sweep compiles the engine once, not per eval.

Ζ·mutant·struct·node-kinds — a perturbation TOGGLES an element's presence, and a FILE's presence is
togglable like an import's (one artifact-kind down).  When `--site` is a FILE spec (no module to
mutate) the counterfactual is delivered by toggling that path in the sandbox instead of swapping a
.pyc:
    file+:<path>   INJECT an absent file (create it) — falsifies a "X does not exist" assertion (the
                   contrapositive of rm-next's roadmap-pending claim: if cli.py ships, the check must
                   fail).  The NEGATIVE-existence polarity, the file analog of import+.
    file-:<path>   DROP a present file (remove it) — falsifies a "X exists" assertion.  The POSITIVE
                   polarity, the file analog of import-.
The path is sandbox-relative, aligned with the check's own Path(__file__).resolve() root (the
hermetic sandbox keeps both in the same tree).  A file cell needs no --module/--mutant (nothing is
recompiled); it still stages the check's engine .pyc closure and runs it.

Idempotency: invoke this tool by an ABSOLUTE interpreter path so sys.executable is populated — the
check re-spawns the projector as [sys.executable, …] (see the history of the '' spurious-flip bug)."""
import argparse
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys


def _own_cgroup():
    """This process's own v2 cgroup path, or None."""
    try:
        return pathlib.Path("/proc/self/cgroup").read_text().strip().rsplit(":", 1)[-1]
    except OSError:
        return None


def _peak_bytes():
    """memory.peak for THIS process's cgroup, or None.

    Τ·mem·observe·inside — read from IN HERE, not from the shell afterwards.  The cell's
    command is `cgroup-scope N -- eval.py … ; read-the-peak`, so the trailing read runs
    AFTER the scope has exited and lands in bazel's sandbox cgroup — a DIFFERENT tree from
    the one that ran the check.  Measured on compose-chains: the outside read reported
    4.7MB for a cell whose real in-scope peak is 35MB and which OOMs at a 32MB cap.  The
    sensor under-reported by ~8x, and under-reporting is the dangerous direction: a
    manifest built from it sizes the cell BELOW what it needs, so the loop re-derives the
    same OOM every run and never converges.

    ⚑ THE PEAK INCLUDES TMPFS.  A cgroup is charged for the page cache of files its
    processes write, and TMPDIR here is a tmpfs — so a witness that projects an out.md
    into a mkdtemp() pays for it in MEMORY, not just disk, and freeing it needs the
    directory removed rather than the process exited.  Measured on compose-chains the
    split is anon 32.7MB / file 0.6MB, so THIS cell is driven by nested interpreters
    rather than its scratch files; a witness projecting a large document would be the
    other way round.  Either way the reservation is the same number — memory.peak already
    counts both — but a reader diagnosing a surprising peak must know to check the split
    (memory.stat's anon/file) before blaming the code.
    """
    cg = _own_cgroup()
    if cg is None:
        return None
    try:
        return int(pathlib.Path("/sys/fs/cgroup" + cg + "/memory.peak").read_text().strip())
    except (OSError, ValueError):
        return None


def _write_peak(path):
    """Deposit this cell's in-scope peak, in the vocabulary mem_harvest already parses."""
    if not path:
        return
    b = _peak_bytes()
    pathlib.Path(path).write_text(
        ("%d" % b) if b is not None else "unavailable:unreadable")


def _oom_counts():
    """(oom, oom_kill) for THIS process's own cgroup, or None where v2 is not reachable.

    Ζ·climb·oom·signal — eval.py runs INSIDE the cgroup-scope cell, so its own
    memory.events IS the cell's.  No env var, no plumbing: the scope that caps the
    check is the scope this process is already in.
    """
    cg = _own_cgroup()
    if cg is None:
        return None
    try:
        ev = pathlib.Path("/sys/fs/cgroup" + cg + "/memory.events").read_text()
    except OSError:
        return None
    d = dict(l.split() for l in ev.splitlines() if " " in l)
    try:
        return int(d.get("oom", 0)), int(d.get("oom_kill", 0))
    except ValueError:
        return None


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine-dir", required=True, help="the staged engine dir, e.g. paperkit")
    ap.add_argument("--module", default="", help="the mutated module's .py path, e.g. paperkit/bib.py (empty for a file cell)")
    ap.add_argument("--mutant-py", default="", help="the mutated module SOURCE (pk_mutate; identity for ∅; empty for a file cell)")
    ap.add_argument("--mutant-pyc", default="", help="the mutated module BYTECODE (pk_pyc of it; empty for a file cell)")
    ap.add_argument("--check", required=True, help="the check script, e.g. paper/checks/claims.py")
    ap.add_argument("--claim", required=True)
    ap.add_argument("--site", required=True, help="the def-site label, recorded in the result")
    ap.add_argument("--content-path", default="", help="a content cell's target file (its substring toggled)")
    ap.add_argument("--content-textfile", default="", help="the substring to drop/inject, delivered as a file (no shell escaping)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--peak", default="", help="write this cell's in-scope memory.peak here "
                    "(Τ·mem·observe·inside; empty = the caller is not observing)")
    a = ap.parse_args(argv)

    tag = sys.implementation.cache_tag                       # e.g. cpython-313 — matches THIS runtime

    def slot(py_path):                                       # paperkit/x.py → paperkit/__pycache__/x.<tag>.pyc
        p = pathlib.Path(py_path)
        d = p.parent / "__pycache__"
        d.mkdir(parents=True, exist_ok=True)
        return d / (p.stem + "." + tag + ".pyc")

    # place every precompiled engine .pyc (staged as paperkit/<relpath>.pyc) at its import location
    for pyc in pathlib.Path(a.engine_dir).rglob("*.pyc"):
        if "__pycache__" in pyc.parts:
            continue
        shutil.move(str(pyc), str(slot(pyc.with_suffix(".py"))))
    op, sep, arg = a.site.partition(":")
    if op == "file+":
        # Ζ·mutant·struct·node-kinds — INJECT an absent file: its mere existence is the counterfactual
        # (an empty file suffices; the assertion tests .exists(), not content), so no module is mutated.
        p = pathlib.Path(arg)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("")
    elif op == "file-":
        pathlib.Path(arg).unlink(missing_ok=True)      # DROP a present file — the counterfactual absence
    elif op in ("content-", "content+"):
        # Ζ·mutant·struct·node-kinds (content) — TOGGLE a substring's presence in a staged file: the
        # precise DAG-EDGE perturbation (drop `result:paper` from the README bib → the "does the README
        # import the paper" grep fails).  The substring arrives as a FILE (no shell-escaping of quotes/
        # colons).  Unlink-then-write: remove the sandbox hardlink, never the source inode.
        text = pathlib.Path(a.content_textfile).read_text()
        f = pathlib.Path(a.content_path)
        orig = f.read_text()
        f.unlink(missing_ok=True)
        f.write_text(orig.replace(text, "") if op == "content-" else orig + text)
    else:
        # … deliver the ONE mutated module on BOTH paths (∅ = identity = no-op): its .pyc (used when
        # the module is IMPORTED) AND its .py source (used when the module is run as a MAIN SCRIPT — a
        # main script's bytecode is never read from __pycache__, so an entry-point module like
        # project.py would otherwise escape the mutation).
        mod = pathlib.Path(a.module)
        mod.unlink(missing_ok=True)   # Ξ·dag·eval: D may lie outside its own check's closure .py (a
        shutil.copyfile(a.mutant_py, mod)   # non-sensitive cell) → not staged; deliver the mutant anyway
        shutil.copyfile(a.mutant_pyc, slot(mod))

    # Μ·sweep·atom — a flip:/branch: mutant can make the check NON-TERMINATING (e.g. inverting
    # bib._unescaped_braces's `while` loop spins forever).  The GRID path bounds the check by CPU time
    # exactly as the in-process resolver.run_ok does (RLIMIT_CPU via preexec, a wall backstop, kill the
    # whole session so no orphan spins on): a mutant that never answers HAS flipped the check (a real
    # behavioural change the sweep must see), and measuring CPU not wall keeps a lease-queued cell from a
    # false flip.  Without this the grid hangs the moment a flip:/dflip: non-terminating mutant is swept
    # ([[witness-the-live-path]] — the in-process path was bounded, the grid path was not).
    cpu = int(os.environ.get("PAPERKIT_CHECK_CPU", 60))
    wall = int(os.environ.get("PAPERKIT_CHECK_TIMEOUT", 600))

    def _cpu_rlimit():
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 3))

    # Ζ·eval·mute — the BASELINE's stderr is kept.  A ∅-mutation cell that flips is the canary
    # (sens.py FAILS LOUD on it rather than emitting a plausible-but-wrong sens set), and with both
    # streams to DEVNULL the cell knew WHY and threw it away — so the loud failure said only
    # "flipped", and diagnosing one took an hour of inference.  Mutated cells stay muted: a flip
    # there is the SIGNAL, expected and uninteresting, and 48,011 tracebacks would be noise.
    _base = a.site == "0"
    _oom_before = _oom_counts()
    p = subprocess.Popen([sys.executable, a.check, a.claim],
                         stdout=(subprocess.PIPE if _base else subprocess.DEVNULL),
                         stderr=(subprocess.STDOUT if _base else subprocess.DEVNULL),
                         start_new_session=True, preexec_fn=_cpu_rlimit)
    try:
        rc = p.wait(timeout=wall)
        if _base and rc != 0 and p.stdout is not None:
            # Ζ·eval·mute — the check reports its diagnosis on STDOUT (concepts.py prints
            # "concept X: ..." there), so a stderr-only capture reported "no stderr" for a
            # check that had explained itself perfectly well one stream over.
            err = p.stdout.read().decode("utf-8", "replace").strip().splitlines()
            print("eval: BASELINE FLIPPED (the identity mutation broke the check) — %s"
                  % ("rc=%d; %s" % (rc, " ⏎ ".join(err[-6:]) if err else "no output")), file=sys.stderr)
        flipped = rc != 0                                # SIGXCPU/SIGKILL ⇒ negative rc ⇒ flipped (the hang IS a flip)
        # Ζ·climb·oom·signal — an OOM is NOT a flip.  `flipped = rc != 0` is right for a HANG (a
        # mutant that never answers HAS changed behaviour) but wrong for a cell the kernel killed
        # for memory: that is a verdict about the HARNESS, not the mutant — and for the ∅-baseline
        # it is impossible on its face, since an identity mutation cannot make a check need more
        # RAM.  Measured on compose-chains: cap ≤32MB ⇒ "flipped", cap ≥64MB ⇒ not — the same
        # claim graded `broken` or `behavioral` depending only on the cell's memory ladder.
        #
        # ⚑ AND THE OOM WAS INVISIBLE TO THE CLIMB.  cgroup-scope retries on a nonzero PAYLOAD
        # exit, but its payload is THIS process, which catches the child's death, records a
        # verdict and exits 0 — so the ladder saw success and never climbed (holder-vs-worker: the
        # exit code belongs to the holder, the OOM belongs to the worker).  Exiting non-zero hands
        # the signal back to the layer that OWNS the retry.
        # ⚑ INCREMENT, never a delta size.  `oom_kill` counts PROCESSES and `oom_group_kill`
        # counts EVENTS, so under kubelet's `memory.oom.group=1` one OOM raises oom_kill by the
        # whole tree size while oom_group_kill rises by 1.  Asking only "did it increment" is
        # correct under both; dividing, or assuming +1, would not be (linux-sources, 2026-08-26).
        _oom_after = _oom_counts()
        if flipped and _oom_before is not None and _oom_after is not None and (
                _oom_after[0] > _oom_before[0] or _oom_after[1] > _oom_before[1]):
            print("eval: OOM-KILLED at this cell's cap (not a flip) — deferring to the climb",
                  file=sys.stderr)
            _write_peak(a.peak)
            return 3
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)  # kill the whole tree, no orphan spinning on
        except ProcessLookupError:
            pass
        p.wait()
        flipped = True                                   # did not terminate → the mutation flipped it
    _write_peak(a.peak)
    pathlib.Path(a.out).write_text(
        json.dumps({"claim": a.claim, "site": a.site, "flipped": flipped}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
