r"""Ζ·lint·sort — find every file where an import SORT moved a load-bearing import.

⚑ THE DEFECT HAS BITTEN FIVE TIMES AND I FIXED IT FIVE TIMES ONE FAILURE AT A TIME.
`_fixture_gate`, `_fixture_project`, `_fixture_delta`, `boundaries_emit`, `boundaries_gate_json`:
in each, `ruff --select I001 --fix` moved an engine import ABOVE the module whose IMPORT SIDE
EFFECT puts the engine on sys.path.  Alphabetically correct; the file then dies with
`ModuleNotFoundError`.  isort assumes imports are order-independent, and a module that mutates
sys.path on import is exactly where that assumption fails.

⚑⚑ AND FIXING THE NAMED INSTANCES IS THE WRONG MOVE, WHICH IS WHY THIS EXISTS.  Three fixtures
failed, I fixed three fixtures; two more suites carried the identical shape and surfaced only
when a sandbox run reddened seven at once (Λ·artifact — repair the population, not the roster a
failure happened to print).  42 files were touched by that pass.

THE PREDICATE IS SYNTACTIC, not a guess: a file is at risk when an import that USED to sit AFTER
a `sys.path` mutation now sits BEFORE it.  That is exactly what the sort does and exactly what
breaks; anything else the sort changed is harmless reordering within one group.

    python3 tools/sortaudit.py                  # paperkit/tests (the swept population)
    python3 tools/sortaudit.py render/checks    # any other tree
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = sys.stdout


def changed(tree: str) -> list[str]:
    """List the .py files under `tree` that differ from HEAD."""
    r = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", tree],  # noqa: S603, S607
                       cwd=ROOT, capture_output=True, text=True, check=False)
    return [ln for ln in r.stdout.splitlines() if ln.endswith(".py")]


def at_head(path: str) -> str:
    """Read a file's committed text."""
    r = subprocess.run(["git", "show", f"HEAD:{path}"],  # noqa: S603, S607
                       cwd=ROOT, capture_output=True, text=True, check=False)
    return r.stdout


def import_order(text: str) -> list[str]:
    """Collect the module-level import lines and sys.path mutations, in source order.

    ⚑ TEXTUAL BY NECESSITY, AND SCOPED TO SAY SO.  The question is about LINE ORDER, which an AST
    walk normalises away — `ast` carries line numbers but the comparison wanted here is literally
    "did this line move relative to that one".  Restricted to module level (no leading
    whitespace), so an in-function import is not counted.
    """
    out: list[str] = []
    for raw in text.splitlines():
        if raw[:1] in (" ", "\t"):
            continue
        s = raw.strip()
        if s.startswith(("import ", "from ")) or "sys.path.insert" in s or "sys.path.append" in s:
            out.append(s)
    return out


def bootstrap_index(lines: list[str]) -> int:
    """Return the index of the last sys.path mutation, or -1 when there is none."""
    hits = [i for i, s in enumerate(lines) if "sys.path" in s]
    return hits[-1] if hits else -1


def main(argv: list[str]) -> int:
    """Report files whose import order changed relative to a sys.path bootstrap."""
    tree = argv[0] if argv else "paperkit/tests"
    files = changed(tree)
    OUT.write(f"{len(files)} changed .py files under {tree}\n\n")

    risky = 0
    for f in files:
        now = import_order((ROOT / f).read_text())
        was = import_order(at_head(f))
        if not now or not was or now == was:
            continue
        b_now, b_was = bootstrap_index(now), bootstrap_index(was)
        if b_now < 0 and b_was < 0:
            continue
        # an import that USED to sit after the bootstrap and now sits before it
        moved = [s for s in now
                 if s in was
                 and not s.startswith("import sys")
                 and now.index(s) < b_now <= was.index(s)]
        if moved:
            risky += 1
            OUT.write(f"  ⚑ {f}\n")
            for s in moved:
                OUT.write(f"       moved ABOVE the bootstrap: {s}\n")
        elif b_now != b_was:
            OUT.write(f"  ?  {f}: the bootstrap itself moved ({b_was} → {b_now})\n")

    OUT.write(f"\n  {risky} file(s) have an import the sort lifted above its bootstrap.\n")
    if risky:
        OUT.write("  ⚑ each is a ModuleNotFoundError waiting for something to run it.\n")
    return 1 if risky else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
