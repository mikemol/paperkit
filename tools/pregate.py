"""Run the boundary suites on the host BEFORE the remote gate (W339).

A migration commit used to pay a 90-minute gate per discovery: each gate stops at the first red,
and the reds were all things a suite run on the host shows in seconds (a probe interpreter that
lost a dependency, a count pinned beside its own prose).  This runs every
`paperkit/tests/boundaries_*.py` suite, or the ones named, in parallel, each as
`python -m paperkit.tests.NAME` in the repository root, and reports one line per suite.

Each suite runs in its OWN process (one task per child), so a suite that monkeypatches a module
cannot leak into the next.  The exit code is read the way the engine reads it: 0 passes, 3 CANNOT
RUN (the suite needs something only a Bazel cell has, e.g. the built wheel: not a refutation and
not a pass), and anything else fails.  A summary over ZERO suites is refused (rc 2): a green that
measured nothing is the false pass this repository exists to refuse.

A suite that cannot even be imported is reported as a failure of THAT suite (its exception is the
reason), never as a crash of the run.  Invoke it as a module from the repository root, like the
other tools, so `tools` and `paperkit` are importable by layout:

    python3 -m tools.pregate              every boundaries suite
    python3 -m tools.pregate NAME...      these suites (boundaries_clamp, ...)
    python3 -m tools.pregate --selftest   prove the summary on fixtures
"""

from __future__ import annotations

import contextlib
import io
import os
import runpy
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANNOT_RUN = 3
WORKERS = 6

Result = tuple[str, int]


def classify(code: int) -> str:
    """Name an exit code: pass, cannot-run (the engine's rc 3) or fail."""
    if code == 0:
        return "pass"
    return "cannot-run" if code == CANNOT_RUN else "fail"


def summarize(results: list[Result]) -> tuple[int, str]:
    """Return (exit code, text) for the results: 2 when empty, 1 when any failed, else 0."""
    if not results:
        return 2, "pregate: no suites ran -- refusing to report green over nothing\n"
    kinds = {name: classify(code) for name, code in results}
    lines = [f"{kind:10} {name}\n" for name, kind in sorted(kinds.items())]
    failed = sorted(name for name, kind in kinds.items() if kind == "fail")
    cannot = sorted(name for name, kind in kinds.items() if kind == "cannot-run")
    lines.append(
        f"pregate: {len(results)} suite(s), {len(failed)} failed, {len(cannot)} cannot-run\n"
    )
    return (1 if failed else 0), "".join(lines)


def run_suite(name: str) -> Result:
    """Run one suite as `__main__` in the repository root and return its exit code."""
    os.chdir(ROOT)
    sink = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        try:
            runpy.run_module(f"paperkit.tests.{name}", run_name="__main__")
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else int(exc.code is not None)
    return name, code


def selftest() -> bool:
    """Pass arm, flag arm, cannot-run arm and the empty refusal, on fixture results."""
    green, _ = summarize([("a", 0), ("b", 0)])
    red, text = summarize([("a", 0), ("b", 1)])
    skipped, _ = summarize([("a", 0), ("w", CANNOT_RUN)])
    empty, _ = summarize([])
    return (green, red, skipped, empty) == (0, 1, 0, 2) and "1 failed" in text


def main(argv: list[str] | None = None) -> int:
    """Run the pre-gate: suite names or none for all; --selftest; anything else is rc 2."""
    args = sys.argv[1:] if argv is None else argv
    if args == ["--selftest"]:
        ok = selftest()
        sys.stdout.write(f"pregate selftest: {'PASS' if ok else 'FAIL'}\n")
        return 0 if ok else 1
    if any(a.startswith("-") for a in args):
        sys.stderr.write("usage: pregate.py [--selftest | SUITE...]\n")
        return 2
    names = args or sorted(p.stem for p in (ROOT / "paperkit" / "tests").glob("boundaries_*.py"))
    results: list[Result] = []
    with ProcessPoolExecutor(max_workers=WORKERS, max_tasks_per_child=1) as pool:
        futures = {name: pool.submit(run_suite, name) for name in names}
        for name, future in futures.items():
            error = future.exception()
            if error is None:
                results.append(future.result())
            else:
                sys.stdout.write(f"{name}: did not run to an exit code: {error!r}\n")
                results.append((name, 1))
    code, text = summarize(results)
    sys.stdout.write(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
