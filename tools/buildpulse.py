r"""Ζ·pulse — report a running //:hook's progress and its WINDOWED action rate, so a stall is named.

⚑ THE HOOK HAS NO PROGRESS PULSE, AND THAT IS A RECORDED GAP (`tooling-self-regulates`): a
126k-action sweep prints a live action counter and nothing that says whether the counter is
MOVING.  Idle CPU with a slow wall clock is the lease queue behaving correctly; idle CPU with a
FROZEN counter is a stall.  The two look identical in a `tail`, and telling them apart takes two
samples separated in time — which is precisely the judgement that evaporates when a turn ends.

⚑⚑ SO THE STATE IS PERSISTED, NOT HELD IN THE READER.  Each run appends a sample to a JSONL file
and reports the rate against the OLDEST sample still inside the window.  A monitor invoking this
every 15 minutes therefore gets a real actions-per-minute, and the verdict travels with the
artifact instead of being re-derived (differently) by whoever reads the log next.

⚑ SILENCE IS NOT SUCCESS.  The Monitor contract is explicit that a watcher which only matches the
happy path stays quiet through a crash.  This exits non-zero and says so when the build process is
GONE, when the counter has not moved for `--stall-after`, or when the log's tail carries a failure
signature — three distinct terminal states, each named, none of them a silent hang.  `--selftest`
proves each of those arms can FIRE; an alarm whose red path has never run is not a control.

⚑ IT WAS WRITTEN IN A SCRATCHPAD AND LANDED AFTERWARDS, WHICH IS THE POINT (Λ·quiesce).  Writing
it into the repo while a //:hook run was in flight would have invalidated that run — a sandboxed
cell whose input changes reds with `input dependency modified during execution`, which reads as an
engine defect rather than as interference.  The repo's own PreToolUse guard refused the write and
was right to; the tool lived outside the tree until the tree was quiet.

    python3 tools/buildpulse.py --log <hook.output>     # one sample, human-readable
    python3 tools/buildpulse.py --log <f> --window 3600 # rate over the last hour
    python3 tools/buildpulse.py --selftest              # prove every arm can fire
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

OUT = sys.stdout

# Bazel's progress line: "[39,547 / 116,688] Ζ·eval ..."
PROGRESS = re.compile(r"\[([\d,]+)\s*/\s*([\d,]+)\]")
# Terminal-state signatures worth waking a reader for.  Deliberately broader than the failures
# seen so far: the Monitor contract says to widen rather than narrow when enumeration is uncertain.
TROUBLE = re.compile(
    r"\bFAIL(?:ED)?\b|\bERROR\b|Traceback|OutOfMemoryError|"
    r"input dependency modified during execution|Build did NOT complete",
)
# ⚑ THE EXECUTABLE NAME, NOT THE COMMAND LINE (Λ·probe·self).  This read `pgrep -f "bazel test
# //:hook"`, and a watcher looping that predicate MATCHES ITSELF: the loop's own command line
# contains the literal, so it can never see the build as gone.  Measured — a monitor kept pulsing
# after a completed run, and the first fix (`installs/bazel/.*bazel test //:hook`) was wrong the
# same way.  `pgrep -x` matches the executable, which a shell cannot spoof.
#
# This module survived the `-f` form only because it runs as its own process whose argv does not
# contain the pattern — safe by accident, which is not the same as safe.
BUILD_EXE = "bazel"

MINUTES_PER_HOUR = 60.0
PAIR = 2
DEFAULT_WINDOW = 3600.0        # seconds of history the rate is measured over
DEFAULT_STALL = 1800.0         # seconds with an unmoved counter before calling it a stall
EPS = 0.01


@dataclass(frozen=True)
class Sample:
    """One observation of the build's progress counter."""

    at: float
    done: int
    total: int


def _tail(path: Path, nbytes: int) -> str:
    """Read the last `nbytes` of a file as text.

    ⚑ ONLY THE TAIL, DELIBERATELY.  A //:hook log reaches hundreds of MB and every answer here is
    at the end.  Reading the whole file to find the last line is the shape that put a 4.45 GB
    execution log in RAM (Ζ·execlog·leak) — the same lesson, on the reading side.
    """
    size = path.stat().st_size
    with path.open("rb") as fh:
        fh.seek(max(0, size - nbytes))
        return fh.read().decode("utf-8", "replace")


def read_progress(log: Path, tail_bytes: int = 200_000) -> tuple[int, int]:
    """Read the most recent [done / total] the log carries, or (0, 0) when there is none.

    ⚑ The `findall` Any is narrowed HERE, at the seam, so callers see concrete ints.
    """
    hits: object = PROGRESS.findall(_tail(log, tail_bytes))
    if not isinstance(hits, list) or not hits:
        return (0, 0)
    last: object = hits[-1]
    if not isinstance(last, tuple) or len(last) != PAIR:
        return (0, 0)
    done, total = str(last[0]), str(last[1])
    return (int(done.replace(",", "")), int(total.replace(",", "")))


def read_trouble(log: Path, tail_bytes: int = 20_000) -> str:
    """Return the newest line matching a failure signature, or "" when the tail is clean."""
    hits = [ln for ln in _tail(log, tail_bytes).splitlines() if TROUBLE.search(ln)]
    return hits[-1][:160] if hits else ""


def build_alive() -> bool:
    """Report whether the //:hook build process is still running."""
    r = subprocess.run(["pgrep", "-x", BUILD_EXE],  # noqa: S603, S607
                       capture_output=True, text=True, check=False)
    return r.returncode == 0


def load(state: Path) -> list[Sample]:
    """Read the samples recorded so far, skipping any line that is not one."""
    if not state.exists():
        return []
    out: list[Sample] = []
    for ln in state.read_text().splitlines():
        if not ln.strip():
            continue
        try:
            rec: object = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(rec, dict):
            continue
        at: object = rec.get("at")
        done: object = rec.get("done")
        total: object = rec.get("total")
        if isinstance(at, float) and isinstance(done, float) and isinstance(total, float):
            out.append(Sample(at=at, done=int(done), total=int(total)))
    return out


def append(state: Path, s: Sample) -> None:
    """Append one sample to the state file."""
    rec: dict[str, float] = {"at": s.at, "done": float(s.done), "total": float(s.total)}
    with state.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")


def rate(now: Sample, past: list[Sample], window: float) -> tuple[float, float]:
    """Actions per minute against the oldest sample inside `window`, with that span in minutes.

    Returns (0, 0) when there is no earlier sample to measure against — an honest "not yet known"
    rather than a zero that reads as a stall on the very first call.
    """
    inside = [p for p in past if now.at - p.at <= window]
    if not inside:
        return (0.0, 0.0)
    ref = inside[0]
    if now.at <= ref.at:
        return (0.0, 0.0)
    mins = (now.at - ref.at) / 60.0
    return ((now.done - ref.done) / mins, mins)


def stalled(now: Sample, past: list[Sample], stall_after: float) -> float:
    """Minutes the counter has been frozen, or 0.0 when it has moved (or nothing to compare).

    One function so the predicate has ONE definition — the selftest asserts against the same code
    the reporting path runs, not a restatement of it.

    ⚑ THE WINDOW IS A FLOOR ON THE AGE, NOT A CEILING — AND THE FIRST CUT HAD IT BACKWARDS.  It
    kept only samples NEWER than `stall_after`, so a counter frozen for LONGER than the window
    left the set empty and reported NO STALL: the alarm went silent exactly as the outage got
    worse, which is the `silence is not success` failure committed by the thing built to prevent
    it.  Caught by --selftest on its first run, not by a build.

    The correct predicate: find the OLDEST sample that still agrees with the current count and has
    no DISAGREEING sample after it, then report how long ago it was.  A sample with a different
    count means the counter moved at that point, so the freeze can only have run since then.
    """
    if not past:
        return 0.0
    moved = [p.at for p in past if p.done != now.done]
    since = max(moved) if moved else None
    agreeing = [p.at for p in past if p.done == now.done and (since is None or p.at > since)]
    if not agreeing:
        return 0.0
    held = (now.at - min(agreeing)) / 60.0
    return held if held * 60.0 >= stall_after else 0.0


def eta(now: Sample, per_min: float) -> str:
    """Render a remaining-time estimate, or "" when the rate cannot support one.

    ⚑ AN ESTIMATE, AND LABELLED AS ONE.  The grid's cells are not uniform and the aggregation
    phases come last, so a linear extrapolation is a floor on the honest answer rather than a
    prediction.  It is printed because "is this minutes or hours away" is the actual question,
    and withheld entirely when the rate is zero rather than rendered as infinity.
    """
    if per_min <= 0 or now.total <= now.done:
        return ""
    mins = (now.total - now.done) / per_min
    if mins >= MINUTES_PER_HOUR:
        return f" · ~{mins / MINUTES_PER_HOUR:.1f}h left at this rate (linear est.)"
    return f" · ~{mins:.0f}m left at this rate (linear est.)"


def _selftest() -> int:
    """Prove each arm can FIRE, on synthetic inputs with known contents.

    ⚑ AN ALARM WHOSE RED PATH HAS NEVER RUN IS NOT A CONTROL (Λ·instrument-vs-gate).  The Monitor
    contract's own warning is that silence looks identical to "still running", so the question
    that matters is not "does it print a percentage" but "would it emit anything if the build died
    right now".  Each case constructs the failure and asserts the arm names it.

    ⚑⚑ AND THE STALL CASE SEEDS ITS CLOCK rather than waiting on one.  A probe that must sleep 30
    minutes to exercise its 30-minute predicate never gets run, and a predicate that is never run
    is the one that is wrong.
    """
    ok = 0
    bad: list[str] = []

    def check(name: str, cond: bool) -> None:  # noqa: FBT001
        nonlocal ok
        if cond:
            ok += 1
            OUT.write(f"  ok {name}\n")
        else:
            bad.append(name)
            OUT.write(f"  XX {name}\n")

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # ⟨P⟩ a healthy tail parses and stays quiet
        good = d / "good.log"
        good.write_text("[42,387 / 120,269] eval something; 1s linux-sandbox\n")
        check("progress parses a comma-formatted counter", read_progress(good) == (42387, 120269))
        check("a clean tail yields no failure signature", read_trouble(good) == "")

        # ⟨F⟩ every failure signature is caught
        for sig in ("FAIL: @@x//:y (Exit 1)",
                    "ERROR: Build did NOT complete successfully",
                    "java.lang.OutOfMemoryError: Java heap space",
                    "Traceback (most recent call last):",
                    "err: input dependency modified during execution"):
            f = d / "f.log"
            f.write_text(f"[1 / 2] fine\n{sig}\n")
            check(f"caught: {sig[:42]}", read_trouble(f) != "")

        # ⟨F⟩ a frozen counter across the window is a STALL, and ⟨δ⟩ one action clears it
        st = d / "s.pulse"
        old = time.time() - DEFAULT_WINDOW
        seed: dict[str, float] = {"at": old, "done": 42.0, "total": 100.0}
        st.write_text(json.dumps(seed) + "\n")
        past = load(st)
        check("a seeded sample round-trips through load()", len(past) == 1)
        now = Sample(at=time.time(), done=42, total=100)
        check("F — a frozen counter is reported as a stall",
              stalled(now, past, DEFAULT_STALL) > 0)
        check("δ — ONE action of progress clears the stall verdict",
              stalled(Sample(at=now.at, done=43, total=100), past, DEFAULT_STALL) == 0.0)

        # ⚑ THE REGRESSION THIS SELFTEST ALREADY CAUGHT ONCE: a freeze LONGER than the window.
        # The first predicate kept only samples newer than stall_after, so the longer the outage
        # ran the more certainly it reported nothing.  A day-old frozen sample must still stall.
        far = Sample(at=old - 86_400, done=42, total=100)
        check("F — a freeze OLDER than the window still stalls (not silence)",
              stalled(now, [far, *past], DEFAULT_STALL) > 0)

        # a counter that moved recently is not a stall, even with old agreeing samples
        check("P — a counter that moved since the old sample is not a stall",
              stalled(Sample(at=now.at, done=99, total=100),
                      [far, Sample(at=old + 1, done=98, total=100)], DEFAULT_STALL) == 0.0)

        # ⟨P⟩ the rate is withheld until there is something to measure against
        check("no prior sample ⇒ rate (0,0), never a false stall",
              rate(now, [], DEFAULT_WINDOW) == (0.0, 0.0))
        check("no prior sample ⇒ no stall verdict either",
              stalled(now, [], DEFAULT_STALL) == 0.0)
        r, span = rate(Sample(at=old + 600, done=142, total=1000),
                       [Sample(at=old, done=42, total=1000)], DEFAULT_WINDOW)
        check("100 actions in 10m reads as 10/min",
              abs(r - 10.0) < EPS and abs(span - 10.0) < EPS)

    OUT.write(f"\nbuildpulse selftest: {ok}/{ok + len(bad)}\n")
    return 1 if bad else 0


def _parse(argv: list[str]) -> tuple[Path, Path, float, float, bool]:
    """Read the command line into concrete types (a Namespace attribute is Any)."""
    ap = argparse.ArgumentParser(description="Report a running build's progress and action rate.")
    ap.add_argument("--log", default="", help="the build's output file")
    ap.add_argument("--state", default="", help="where samples accumulate (default: <log>.pulse)")
    ap.add_argument("--window", type=float, default=DEFAULT_WINDOW,
                    help="seconds of history the rate is measured over")
    ap.add_argument("--stall-after", type=float, default=DEFAULT_STALL,
                    help="seconds with an unmoved counter before calling it a STALL")
    ap.add_argument("--selftest", action="store_true", help="prove every arm can fire, then exit")
    ns = ap.parse_args(argv)
    log: str = ns.log
    state: str = ns.state
    window: float = ns.window
    stall_after: float = ns.stall_after
    selftest: bool = ns.selftest
    return (Path(log), Path(state) if state else Path(log + ".pulse"),
            window, stall_after, selftest)


def main(argv: list[str]) -> int:
    """Sample the build once, report progress + windowed rate, and name any terminal state."""
    log, state, window, stall_after, selftest = _parse(argv)
    if selftest:
        return _selftest()

    if not log.name or not log.exists():
        OUT.write(f"pulse: no log at {log}\n")
        return 2

    done, total = read_progress(log)
    now = Sample(at=time.time(), done=done, total=total)
    past = load(state)
    append(state, now)

    per_min, span = rate(now, past, window)
    pct = (100.0 * done / total) if total else 0.0

    line = f"pulse: {done:,}/{total:,} ({pct:.1f}%)"
    if span:
        line += f" · {per_min:,.0f} actions/min over {span:.0f}m" + eta(now, per_min)
    else:
        line += " · rate: first sample"
    OUT.write(line + "\n")

    # ── terminal states, each named ────────────────────────────────────────────────────────
    trouble = read_trouble(log)
    if trouble:
        OUT.write(f"  ⚑ FAILURE SIGNATURE in the log tail: {trouble}\n")
        return 1

    if not build_alive():
        OUT.write("  ⚑ the //:hook build process is GONE — finished, or killed.  Read the log's "
                  "tail for its verdict; a pulse cannot tell a green exit from a kill.\n")
        return 1

    held = stalled(now, past, stall_after)
    if held:
        OUT.write(f"  ⚑ STALL: the action counter has not moved in {held:.0f}m "
                  f"(still {done:,}).  Alive but not progressing.\n")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
