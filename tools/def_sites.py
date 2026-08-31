#!/usr/bin/env python3
"""Τ·mem·cpu / Ζ·mutant — enumerate the def-sites of a .py source, the unit of def-resolution
mutation.  Mirrors grader._def_sites (the SAME rule the in-process sweep uses): every def/method
whose body starts on a line after its signature (a one-liner can't be body-isolated, so it is
skipped), qualname-prefixed by enclosing class/def.  Emits `relpath\tqualname` per site so the bib
generator can declare one pk_mutant per (claim, site) at analysis time — lifting the sweep's fanout
into Bazel's graph (parallel + per-site cached) instead of an adaptive in-process group-test.
"""
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


def def_lines(text):
    """{qualname: (first_line, last_line)} — where each def-site SITS.

    ⚑ A SEPARATE WALK, DELIBERATELY, AND `def_sites` IS UNTOUCHED.  That function mirrors
    `grader._def_sites` and its output IS the mutation surface: every claim's sensitivity
    fingerprint is a set of `module::qualname` strings drawn from it, so a change to what it
    emits — or to the order it emits in — silently re-keys the entire grid.  This walk answers
    a different question (WHERE a site is, for a reader) and shares only the recursion shape.
    Skipping the one-liner rule here is correct for the same reason: a reader asking where
    `add_entry` lives wants an answer even for a def the sweep cannot body-isolate.
    """
    out = {}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out

    def rec(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) or isinstance(child, ast.ClassDef):
                out[prefix + child.name] = (child.lineno, child.end_lineno)
                rec(child, prefix + child.name + ".")
            else:
                rec(child, prefix)

    rec(tree, "")
    return out


if __name__ == "__main__":
    # ⚑ `--lines` IS OPT-IN so the DEFAULT output stays byte-identical.  The generator consumes
    # this stdout; adding a column unconditionally would change every emitted cell name.
    args = sys.argv[1:]
    want_lines = "--lines" in args
    args = [a for a in args if a != "--lines"]
    if not args:
        print("usage: def_sites.py [--lines] <file.py> ...\n"
              "  bare      relpath<TAB>qualname — the mutation surface (grader._def_sites)\n"
              "  --lines   relpath<TAB>qualname<TAB>first-last — where each site SITS",
              file=sys.stderr)
        raise SystemExit(2)
    for arg in args:
        p = Path(arg)
        if want_lines:
            for qn, (a, b) in def_lines(p.read_text()).items():
                print(f"{arg}\t{qn}\t{a}-{b}")
        else:
            for qn in def_sites(p.read_text()):
                print(f"{arg}\t{qn}")
