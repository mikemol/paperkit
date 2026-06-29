#!/usr/bin/env python3
"""Τ·mem·cpu / Ζ·mutant — enumerate the def-sites of a .py source, the unit of def-resolution
mutation.  Mirrors grader._def_sites (the SAME rule the in-process sweep uses): every def/method
whose body starts on a line after its signature (a one-liner can't be body-isolated, so it is
skipped), qualname-prefixed by enclosing class/def.  Emits `relpath\tqualname` per site so the bib
generator can declare one pk_mutant per (claim, site) at analysis time — lifting the sweep's fanout
into Bazel's graph (parallel + per-site cached) instead of an adaptive in-process group-test."""
import ast
import sys
from pathlib import Path


def def_sites(text):
    out = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out

    def rec(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.body[0].lineno > child.lineno:
                    out.append(prefix + child.name)
                rec(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                rec(child, prefix + child.name + ".")
            else:
                rec(child, prefix)

    rec(tree, "")
    return out


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        p = Path(arg)
        for qn in def_sites(p.read_text()):
            print(f"{arg}\t{qn}")
