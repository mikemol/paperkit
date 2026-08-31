r"""Ζ·flat·order — the FLAT-IMPORT population, and the order it has to be repaired in.

⚑ THE ARC IS NOT A SET OF FILE CLEANUPS, AND MEASURING IT AS ONE UNDERSTATES IT.
A module that reaches a sibling by a bare `import x` behind a `sys.path.insert` is unresolvable
to mypy, so `x` types as `Any` and every expression derived from it inherits that.  The obvious
plan — name the imports in full, one file at a time — looks cheap per file and is not: naming
them makes mypy FOLLOW the edge, so the file inherits its dependency's debt too.

MEASURED on `paperkit/tests/boundaries_toplevel.py` (2026-08-31): 62 mypy errors in 1 file
before, 237 across 2 files after naming its two imports in full — because `tools/closure.py`
(87 ruff findings, itself flat: `from imports import imports`) entered the check.  The flat
spelling was not hiding 60 findings; it was hiding a DEPENDENCY CONE.

⚑⚑ SO THE ORDER IS TOPOLOGICAL, BOTTOM-UP.  A file can only be converted once everything it
imports is already clean, or the conversion imports somebody else's backlog into its own gate
verdict — and the per-file gate has no partial credit.  This derives that order from the actual
unresolvable-import edges rather than from a reading of the source, and reports the per-file debt
at each rung so the cost is known before the first edit rather than discovered at file three.

    python3 tools/flatorder.py                  # the population, in repair order
    python3 tools/flatorder.py --roots          # just the leaves — where to start
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = sys.stdout

# mypy's unresolvable-import line:
#   `path:LINE: error: Cannot find implementation ... named "NAME"  [import-not-found]`
UNRESOLVED = re.compile(r'^(\S+?):\d+: error: Cannot find .*? named "([^"]+)"')
MYPY: tuple[str, ...] = (".venv/bin/mypy", "--strict", "--disallow-any-expr", "--no-error-summary")
RUFF: tuple[str, ...] = (".venv/bin/ruff", "check", "--output-format", "concise")
CODE = re.compile(r"^\S+?:\d+:\d+: ([A-Z]+\d+)")

# ⚑ THE COST IS NOT THE FINDING COUNT, IT IS THE DECISION COUNT (operator, 2026-08-31:
# *"It's not weeks if it's mechanized."*).  Most of this population is annotations, docstring
# mood and line length — deterministic edits a tool applies without judgement.  What actually
# costs is the residue: a suppression that has to be argued, a signature nobody can infer, an
# Any that needs a real type.  Splitting the report on that axis turns "2,883 findings" from a
# number that reads as weeks into a number that reads as one mechanical pass plus a small
# reviewable remainder.
#
# MECHANICAL = ruff can fix it, or the fix is a fixed rewrite with no design content:
#   ANN*  a missing annotation on a function whose types are already determined by its callers
#   D*    docstring mood/format/period — the text is there, the form is wrong
#   E501  line length
#   I001  import order (⚑ NOT blindly: sortaudit.py exists because this one moved a
#         load-bearing import above its sys.path bootstrap five times)
#   COM/Q/UP/FURB/PTH/RUF  formatting and modernisation with a deterministic rewrite
MECHANICAL = ("ANN", "D1", "D2", "D4", "E501", "I001", "COM", "Q0", "UP", "FURB", "PTH", "RUF")


def candidates() -> list[Path]:
    """Collect every engine + tools .py a flat import could live in."""
    out = [p for p in (ROOT / "paperkit").rglob("*.py") if "__pycache__" not in p.parts]
    out += list((ROOT / "tools").glob("*.py"))
    return sorted(out)


def unresolved(paths: list[Path]) -> dict[str, set[str]]:
    """Map each file to the module names mypy cannot resolve from it.

    ⚑ ASKED OF THE CHECKER, NOT PARSED FROM SOURCE.  Whether a name resolves depends on
    sys.path, the editable install and the package layout — an AST walk sees the `import x` but
    not whether `x` is reachable, which is the entire question here.
    """
    proc: subprocess.CompletedProcess[str] = subprocess.run(  # noqa: S603
        [str(ROOT / MYPY[0]), *MYPY[1:], *[str(p) for p in paths]],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    out: dict[str, set[str]] = {}
    for ln in proc.stdout.splitlines():
        m = UNRESOLVED.match(ln)
        if m:
            out.setdefault(m.group(1), set()).add(m.group(2))
    return out


def ruff_count(path: str) -> int:
    """Count a file's ruff findings — the cost of converting it at its rung."""
    proc: subprocess.CompletedProcess[str] = subprocess.run(  # noqa: S603
        [str(ROOT / RUFF[0]), *RUFF[1:], path],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    return len([ln for ln in proc.stdout.splitlines() if ln.startswith(path)])


def owner_of(name: str, paths: list[Path]) -> str:
    """Name the repo file that provides `name`, or "" when nothing here uniquely does."""
    hits = [p for p in paths if p.stem == name]
    return str(hits[0].relative_to(ROOT)) if len(hits) == 1 else ""


def flat_only(pop: dict[str, set[str]], owners: dict[str, str]) -> dict[str, set[str]]:
    """Keep only the unresolvable names THIS REPO owns — the ones a full name would fix.

    ⚑ THE FIRST CUT OVER-REPORTED, BECAUSE "mypy cannot resolve it" IS WIDER THAN "it is flat".
    Measured: `paperkit/tools/vfs.py` was listed for `pygit2` and `tools/otlp_push.py` for three
    `opentelemetry.proto.*` modules.  Those are genuine third-party dependencies — pygit2 is not
    installed, and the otlp protos are fetched on demand by the hook's `uv run --with`.  Neither
    is fixable by naming an import in full; they need a stub or a declared dependency, which is a
    different job with a different owner.

    Counting them inflated the population by two files and 386 ruff findings — 13% of the total —
    and the two are the 1st and 2nd most expensive files in the whole set, so the distortion fell
    exactly where a reader would anchor.  A population is only honest once it states its filter
    (Λ·declared-partial); this is that filter, named.
    """
    out: dict[str, set[str]] = {}
    for f, names in pop.items():
        mine = {n for n in names if owners.get(n)}
        if mine:
            out[f] = mine
    return out


def _by_count(kv: tuple[str, int]) -> int:
    """Sort key: most-frequent rule first (a lambda here types as Callable[[Any], Any])."""
    return -kv[1]


def finding_codes(path: str) -> dict[str, int]:
    """Count a file's ruff findings BY RULE, so mechanical and manual work separate."""
    proc: subprocess.CompletedProcess[str] = subprocess.run(  # noqa: S603
        [str(ROOT / RUFF[0]), *RUFF[1:], path],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    out: dict[str, int] = {}
    for ln in proc.stdout.splitlines():
        m = CODE.match(ln)
        if m:
            out[m.group(1)] = out.get(m.group(1), 0) + 1
    return out


def layer(pop: dict[str, set[str]], owners: dict[str, str]) -> list[list[str]]:
    """Group the population into repair rungs; rung 0 depends on nothing else in the population.

    A file whose unresolvable imports are all owned OUTSIDE the population is a LEAF — converting
    it drags in no further debt.  Each later rung depends only on earlier ones.  A cycle is
    reported as one rung rather than looped on, so the tool cannot hang on its own input.
    """
    remaining = dict(pop)
    rungs: list[list[str]] = []
    while remaining:
        blocked = {f: {owners[n] for n in names if owners.get(n) in remaining}
                   for f, names in remaining.items()}
        ready = sorted(f for f, deps in blocked.items() if not deps)
        if not ready:
            rungs.append(sorted(remaining))
            break
        rungs.append(ready)
        for f in ready:
            del remaining[f]
    return rungs


def main(argv: list[str]) -> int:
    """Report the flat-import population in the order it must be repaired."""
    paths = candidates()
    pop = unresolved(paths)
    if not pop:
        OUT.write("flatorder: no unresolvable imports — the population is empty\n")
        return 0

    names = {n for names in pop.values() for n in names}
    owners = {n: owner_of(n, paths) for n in names}
    dropped = sorted({n for n in names if not owners.get(n)})
    pop = flat_only(pop, owners)
    rungs = layer(pop, owners)

    if "--roots" in argv:
        for f in rungs[0]:
            OUT.write(f"{f}\n")
        return 0

    total = mech = 0
    manual: dict[str, int] = {}
    for i, rung in enumerate(rungs):
        why = "convert FIRST (no in-population deps)" if not i else "depends only on earlier rungs"
        OUT.write(f"\nrung {i} — {why}\n")
        for f in rung:
            codes = finding_codes(f)
            cost = sum(codes.values())
            m = sum(v for k, v in codes.items() if k.startswith(MECHANICAL))
            total += cost
            mech += m
            for k, v in codes.items():
                if not k.startswith(MECHANICAL):
                    manual[k] = manual.get(k, 0) + v
            unres = ", ".join(sorted(pop[f]))
            OUT.write(f"    {f:<46} {cost:>4} ({cost - m:>3} manual) · {unres}\n")

    OUT.write(f"\n{len(pop)} file(s) across {len(rungs)} rung(s) · {total} ruff findings\n")
    OUT.write(f"  {mech} MECHANICAL ({100 * mech // max(total, 1)}%) · "
              f"{total - mech} needing judgement\n")
    if manual:
        top = sorted(manual.items(), key=_by_count)[:8]
        OUT.write("  the judgement half, by rule: "
                  + ", ".join(f"{k}={v}" for k, v in top) + "\n")
    if dropped:
        OUT.write("\n  ⚑ EXCLUDED as third-party (no in-repo owner, a full name cannot fix):\n"
                  f"      {', '.join(dropped)}\n")
    OUT.write("  ⚑ converting a file before its rung imports its dependencies' debt into its\n"
              "    own gate verdict — the per-file gate has no partial credit.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
