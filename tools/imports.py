#!/usr/bin/env python3
"""Ξ·dag — enumerate a .py module's ENGINE-INTERNAL imports (the import edges), the analog of
def_sites.py for the mutation surface.  Emits `module<TAB>imported` per edge, where `imported` is
another module in the given set (a bare `import x` / `from x import …`, since the engine is on
sys.path).  Derived from the AST, never a grep (a grep matches the name in comments/strings — the
project↔rhetoric "cycle" was such a phantom).

The build DAG is a PROJECTION of this: each module's .pyc is a target whose deps are its imports, so
a consumer stages a module's transitive closure, not the flat engine — the incrementality is exact
by construction (Ξ·dag·build).  Usage: imports.py <module.py>… → the edges over that module set."""
import ast
import sys
from pathlib import Path


def imports(text, names):
    out = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names if a.name in names}
        elif isinstance(n, ast.ImportFrom) and n.module in names:
            out.add(n.module)
    return out


if __name__ == "__main__":
    paths = sys.argv[1:]
    names = {Path(p).stem for p in paths}
    for p in paths:
        stem = Path(p).stem
        for imp in sorted(imports(Path(p).read_text(), names) - {stem}):
            print("{}\t{}".format(p, imp))
