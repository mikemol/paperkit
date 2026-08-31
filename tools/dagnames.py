r"""Ξ·dag·dotted — name every engine module IMPORTABLY, from the component partition.

⚑ THE FOURTH PRIVATE COPY OF THE NAMESPACE TRANSLATION, AND THE ONE THAT BROKE.
`tools/dagderive.py`'s docstring names three consumers that each wrote their own conversion
between the PATH namespace (`tests/boundaries_jobs.py`, what `COMPONENTS` and `IMPORTS` record)
and the NAME namespace (what `import` and a Bazel target use).  Ξ·dag·dotted deleted two of them
by putting both sides of an edge in one namespace.  The one it did not reach was
`paperkit/tests/boundaries_config.py`, which derives the engine's module list as

    [f[:-3] for c, fs in COMPONENTS.items() if c != "tests" for f in fs]

— stripping `.py` and leaving the DIRECTORY in place.  Correct for exactly as long as the engine
was flat.  The moment `paperkit/tools/` appeared (the bibstruct relocation) that slice produced
the module name `tools/bibstruct`, and `importlib.import_module` raised ModuleNotFoundError —
reddening bnd-config on a suite whose own source had not changed.

⚑⚑ SO IT IS OWNED HERE RATHER THAN PATCHED THERE.  A slash-to-dot fix at the call site would be a
FIFTH copy of the translation: correct today, equally unowned, and waiting for the next consumer
to write a sixth.  "What is this module's importable name" is a question about the partition, and
it gets one answer with one owner.

⚑ SEPARATE FROM `dagbzl` DELIBERATELY.  `dagbzl` owns the ARTIFACT and imports `paperkit.durable`
for its atomic write; `durable` carries two `IO[Any]` findings, so under the per-file gate's
`--disallow-any-expr` nothing can be added to `dagbzl` until that is paid down.  This question
needs no writer, so it does not inherit that dependency.

    python3 tools/dagnames.py                       # the engine's importable module names
    python3 tools/dagnames.py --skip tests
    python3 tools/dagnames.py --skip tests --verify # and prove every one of them imports
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "paperkit"
OUT = sys.stdout


def literal(path: Path, name: str) -> dict[str, list[str]]:
    """Read the one dict literal `name` is bound to in a .bzl file.

    ⚑ The `literal_eval` Any is narrowed HERE, at the seam, so callers see a concrete type.
    Same body as `dagbzl.literal`; kept local rather than imported so this module depends on
    nothing that carries a writer (see the module docstring).
    """
    src = path.read_text()
    i = src.index(name + " = ")
    val: object = ast.literal_eval(src[src.index("{", i):src.index("\n}", i) + 2])
    if not isinstance(val, dict):
        return {}
    out: dict[str, list[str]] = {}
    for k, v in val.items():
        if isinstance(v, list):
            out[str(k)] = [str(x) for x in v]
    return out


def to_module(path: str, pkg: str = "") -> str:
    """Convert one engine-relative PATH to the name an `import` would use.

    ⚑ A SUBPACKAGE NAME MUST BE QUALIFIED, BECAUSE THE BARE ONE IS AMBIGUOUS.  The engine has
    `paperkit/tools/` and the repo root has `tools/`, so a bare `tools.bibstruct` resolves to
    whichever directory a consumer happened to bind FIRST — measured: bnd-config imports
    `tools.dagnames` (the root package) and then could not find `tools.bibstruct` (the engine's),
    while dagnames' own --verify, which binds nothing first, reported all 29 green.  A name whose
    referent depends on load order is not a name; qualifying it with `pkg` makes it one.

    A top-level module keeps its bare name: `bib`, not `paperkit.bib` — that is the flat spelling
    every engine module still uses, and changing it is Ζ·engine·flat's job, not this function's.
    """
    name = path.removesuffix(".py").replace("/", ".")
    return f"{pkg}.{name}" if pkg and "." in name else name


def module_names(eng: Path = ENGINE, skip: tuple[str, ...] = (), pkg: str = "") -> list[str]:
    """Name every engine module in the partition, omitting the components in `skip`.

    `skip` lets a caller state its filter (bnd-config excludes `tests`, whose modules are not
    engine entries) instead of re-deriving the list with its own comprehension.  `pkg` qualifies
    the SUBPACKAGE names against the engine's own package — see `to_module`.
    """
    comps = literal(eng / "components.bzl", "COMPONENTS")
    return sorted(to_module(f, pkg) for c, fs in comps.items() if c not in skip for f in fs)


def unresolvable(names: list[str], eng: Path = ENGINE) -> list[tuple[str, str]]:
    """Report which of `names` do NOT import, on the flat route bnd-config takes.

    ⚑ THE CLAIM THIS MODULE MAKES IS THAT ITS NAMES ARE IMPORTABLE, so it answers that itself
    rather than leaving each consumer to discover a bad name as a ModuleNotFoundError mid-suite —
    which is exactly how `tools/bibstruct` surfaced.  The route mirrors the consumer's:
    `paperkit/` on sys.path (the suite's own `sys.path.insert(ENGINE)`), imported by name.

    Run in a SUBPROCESS, one per name: importing the engine's modules has side effects, and a
    failure part-way through must not poison the answer for the rest.
    """
    exe = sys.executable or "python3"
    # ⚑ BOTH ROOTS ON THE PATH, AND THE ROOT `tools` PACKAGE BOUND FIRST — BECAUSE THE CONSUMER
    # DOES BOTH.  A probe that imports only the name under test cannot see the collision between
    # `paperkit/tools/` and the repo root's `tools/`: measured, it reported 29 of 29 green while
    # bnd-config, which imports `tools.dagnames` before walking the partition, died on
    # `tools.bibstruct`.  Reproducing the consumer's binding order is what makes the probe answer
    # the consumer's question — and it is why the engine's subpackage names must be QUALIFIED
    # (`paperkit.tools.x`), since with either path order one of the two bare `tools` is shadowed.
    prelude = (f"import sys; sys.path.insert(0, {str(eng)!r}); "
               f"sys.path.insert(0, {str(eng.parent)!r}); "
               "import tools.dagnames; import importlib; ")
    out: list[tuple[str, str]] = []
    for n in names:
        code = prelude + f"importlib.import_module({n!r})"
        r = subprocess.run([exe, "-c", code], cwd=ROOT,  # noqa: S603
                           capture_output=True, text=True, timeout=120, check=False)
        if r.returncode:
            tail = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()]
            out.append((n, tail[-1][:96] if tail else ""))
    return out


def main(argv: list[str]) -> int:
    """Print the engine's importable module names, or verify that they all import."""
    args = list(argv)
    verify = "--verify" in args
    if verify:
        args.remove("--verify")
    skip: tuple[str, ...] = ()
    pkg = ""
    while len(args) >= 2:  # noqa: PLR2004
        if args[0] == "--skip":
            skip = tuple(args[1].split(","))
        elif args[0] == "--pkg":
            pkg = args[1]
        else:
            break
        args = args[2:]

    names = module_names(skip=skip, pkg=pkg)
    if not verify:
        for name in names:
            OUT.write(name + "\n")
        return 0

    bad = unresolvable(names)
    for n, why in bad:
        OUT.write(f"  XX {n:<28} {why}\n")
    OUT.write(f"\n{len(names) - len(bad)} of {len(names)} engine modules import by name\n")
    if bad:
        OUT.write("  ⚑ a name here is a ModuleNotFoundError in every consumer that walks the "
                  "partition.\n")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
