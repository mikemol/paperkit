r"""Run a paperkit gate target under the repo's OWN resource budget.

⚑ THE FLAGS ARE LOAD-BEARING AND WERE BEING RE-DERIVED BY HAND EVERY TIME.  `.githooks/pre-commit`
says it outright: *Bare `bazel test //:hook` is not the same command as this line.*  Measured
there — running the hook target WITHOUT the budget put 23 sandboxes on a 15GB box and produced
ZERO artifacts in 60 minutes, load 55 with no throughput.

So "which flags does a gate need" is a question about the BUILD's structure, owned by
`tools/sweep_budget.py` and the hook, not something to reconstruct in a shell each turn.  Writing
it out by hand also forces a `$(...)` substitution into the command line, which is exactly the
composed shape the no-chaining and shellcheck guards refuse — the refusal was pointing at this
missing mode, not at the punctuation.

The argv→record conversion follows `tools/cellargs.py` (Ζ·argv·typed): argparse still owns
parsing, and each field is read from the Namespace exactly once under an explicit annotation,
which is what confines the `Any` instead of letting it fan out through every caller.

    python3 tools/rungate.py @paperkit_boundaries//:gate
    python3 tools/rungate.py //:hook --keep-going
    python3 tools/rungate.py @paperkit_render//:gate --dry-run
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = sys.stdout


@dataclass(frozen=True)
class GateArgs:
    """What this invocation was asked to run."""

    target: str
    keep_going: bool
    dry_run: bool


def parse(argv: list[str]) -> GateArgs:
    """Parse `argv` into a typed record."""
    ap = argparse.ArgumentParser(description="Run a gate under the repo's sweep budget.")
    ap.add_argument("target", help="a bazel test target, e.g. @paperkit_boundaries//:gate")
    ap.add_argument("--keep-going", action="store_true",
                    help="keep building after a failure (default: stop at the first)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the command line and exit without running it")
    ns = ap.parse_args(argv)
    target: str = ns.target
    keep_going: bool = ns.keep_going
    dry_run: bool = ns.dry_run
    return GateArgs(target=target, keep_going=keep_going, dry_run=dry_run)


def budget() -> str:
    """Ask the owner (sweep_budget.py) for the sweep's RAM bound, in MB."""
    exe = sys.executable or "python3"
    proc = subprocess.run(  # noqa: S603
        [exe, str(ROOT / "tools" / "sweep_budget.py")],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return proc.stdout.strip()


def argv_for(args: GateArgs, ram: str) -> list[str]:
    """Build the full bazel command line — the one the pre-commit hook runs."""
    return [
        "mise", "exec", "--", "bazel", "test", args.target,
        "--config=mutant",
        f"--local_resources=memory={ram}",
        "--keep_going" if args.keep_going else "--notest_keep_going",
    ]


def main(argv: list[str]) -> int:
    """Resolve the budget, then run the gate and pass its exit code through."""
    args = parse(argv)
    ram = budget()
    cmd = argv_for(args, ram)

    OUT.write(f"  budget: {ram} MB (tools/sweep_budget.py)\n")
    OUT.write(f"  {' '.join(cmd)}\n\n")
    OUT.flush()

    if args.dry_run:
        return 0
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode  # noqa: S603


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
