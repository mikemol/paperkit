"""Ξ·dag — enumerate a .py module's ENGINE-INTERNAL imports (the import edges).

The analog of def_sites.py for the mutation surface.  Emits `module<TAB>imported` per edge, where
`imported` is another module in the given set (a bare `import x` / `from x import …`, since the
engine is on sys.path).  Derived from the AST, never a grep (a grep matches the name in
comments/strings — the project↔rhetoric "cycle" was such a phantom).

The build DAG is a PROJECTION of this: each module's .pyc is a target whose deps are its imports, so
a consumer stages a module's transitive closure, not the flat engine — the incrementality is exact
by construction (Ξ·dag·build).  Usage: imports.py <module.py>… → the edges over that module set.

⚑ THE dag.bzl GENERATOR IS NOT HERE ANY MORE.  Its CLI half (`--write` / `--check`, the header, the
rendering) is `tools/dagbzl.py` over `tools/dagderive.py`; this module kept a second copy that
nothing ran and that disagreed with the file it claimed to own (`--check` read STALE at HEAD).
What is left is the one function other tools import (`imports`, used by closure.py and sites.py)
and its CLI, so this module imports nothing outside the standard library — closure.py runs in
sandboxes whose PYTHONPATH carries no dists.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# ⚑ THE ENGINE IMPORTS ITSELF AS A PACKAGE (paperkit:W296): `import paperkit.layout`,
# `import paperkit.tests._fixture_model`, `from paperkit import layout`. An engine module is
# named by its stem whichever spelling reaches it, so the flat `import layout` and the package
# one are the same edge.
PACKAGES = ("paperkit", "paperkit.tests", "paperkit.library")


def _engine_module(dotted: str) -> str:
    """Return the stem an import names: `layout` for `layout` and for `paperkit[.tests].layout`."""
    parts = dotted.split(".")
    if parts[0] == "paperkit" and len(parts) > 1:
        return parts[-1]
    return dotted


def imports(text: str, names: set[str]) -> set[str]:
    """Return the members of `names` that the module `text` imports."""
    out: set[str] = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {m for a in n.names if (m := _engine_module(a.name)) in names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            if (m := _engine_module(n.module)) in names:
                out.add(m)
            elif n.module in PACKAGES:
                out |= {a.name for a in n.names if a.name in names}
    return out


def main(argv: list[str]) -> int:
    """Print `module<TAB>imported` for each edge over the named modules."""
    names = {Path(p).stem for p in argv}
    for p in argv:
        stem = Path(p).stem
        for imp in sorted(imports(Path(p).read_text(), names) - {stem}):
            sys.stdout.write(f"{p}\t{imp}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
