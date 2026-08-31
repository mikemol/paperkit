r"""Ζ·engine·reach — load every witness the way the bib spells it: BARE python3, project cwd.

⚑ THE INTERPRETER IN THE BIB IS NOT THE ONE A DEVELOPER TYPES.  Every `cmd:` check reads
`python3 checks/<w>.py`, which is the mise interpreter with no virtualenv.  A developer probing
with `.venv/bin/python3` gets the editable install and therefore `paperkit` on sys.path; the gate
gets neither.  Measured 2026-08-30: `render/checks/bib.py` passed every route I probed and
reddened a 61,000-action sweep with `ModuleNotFoundError: No module named 'paperkit'`.

⚑⚑ AND A GATE STOPS AT THE FIRST RED PER PROJECT, so one failure says nothing about the other 33
checks in that project.  This asks for ALL of them in seconds, so the cone is known before the
next sweep rather than one red per two-hour run.

⚑ LOAD, NOT RUN — DELIBERATELY.  Most render witnesses shell out to pandoc/soffice/tesseract and
take minutes; the question here is only whether the module LOADS under the gate's interpreter,
which is exactly what ModuleNotFoundError answers.  A witness that loads may still fail its own
check; that is a different question and the gate's to ask.

    python3 tools/witness_reach.py            # every witness tree
    python3 tools/witness_reach.py render     # one project's checks/
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = sys.stdout
EXCLUDE = {"__init__.py"}


def trees() -> list[Path]:
    """Find every `<project>/checks/` directory in the repo."""
    return sorted(p for p in ROOT.glob("*/checks") if p.is_dir())


def probe(tree: Path, name: str) -> tuple[int, str]:
    """Load one witness on the ROUTE THE BIB SPELLS and return (rc, the last output line).

    ⚑ THE ROUTE IS THE WHOLE POINT, AND MY FIRST CUT GOT IT WRONG THE SAME WAY THE BUG DID.  It
    imported `<project>.checks.<w>` as a package from the repo root and reported three failures —
    `registry`, `a11y`, `lo` — that are SIBLING imports, resolvable on the real route because
    python puts a script's own directory on sys.path first.  All three pass when run as the bib
    spells them.  A probe answering for a route nobody takes manufactures findings exactly as
    readily as it misses them (Λ·path, twice in one afternoon).

    So: cwd = the PROJECT dir and `checks/` prepended to sys.path, which is what running
    `python3 checks/<w>.py` produces — then import the module by name, which executes everything
    except the `if __name__ == "__main__"` body.
    """
    stem = name[: -len(".py")]
    code = ("import sys; sys.path.insert(0, 'checks'); "
            f"import importlib; importlib.import_module({stem!r})")
    r = subprocess.run(["python3", "-c", code], cwd=tree.parent,  # noqa: S603, S607
                       capture_output=True, text=True, timeout=120, check=False)
    tail = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()]
    return r.returncode, (tail[-1][:96] if tail else "")


def main(argv: list[str]) -> int:
    """Report which witnesses fail to load under the interpreter and cwd the bib names."""
    want = set(argv)
    total = bad = 0
    for tree in trees():
        project = tree.parent.name
        if want and project not in want:
            continue
        names = sorted(p.name for p in tree.glob("*.py") if p.name not in EXCLUDE)
        OUT.write(f"\n{project}/checks — {len(names)} witnesses\n")
        for n in names:
            total += 1
            rc, last = probe(tree, n)
            if rc:
                bad += 1
                OUT.write(f"  XX {n:<24} {last}\n")
    OUT.write(f"\n{total - bad} of {total} load cleanly under bare python3 · {bad} FAIL\n")
    if bad:
        OUT.write("  ⚑ each failure is a gate red waiting for a sweep to reach it.\n")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
