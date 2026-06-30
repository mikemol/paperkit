#!/usr/bin/env python3
"""Ζ·mutant — the PURE def-site mutation leaf: given a .py module and a def-site qualname, emit the
module with exactly that definition's body replaced by an uncatchable raise (the rest byte-identical).

This is the mechanical primitive ONLY — the AST surgery — NOT the sensitivity interpretation (what a
flip MEANS, the group-testing, the capability fingerprint), which stays in grader.py.  It is its own
leaf so the Bazel-orchestrated mutant graph (pk_mutate prepares one mutated module per (module,site),
pk_eval runs a check against it) builds on a pure function and never imports the grader's sweep
machinery.  CLI: `mutate.py <module.py> <qualname>` prints the mutated module to stdout.
"""
from __future__ import annotations

import ast
import sys


def _def_sites(text: str) -> list:
    """Every def/method in a .py source as (qualname, node).  Mutation resolution for code is the
    DEFINITION, not the file: corrupting a whole file breaks its import and flips every witness
    identically; replacing one function's BODY leaves the module importable, so a witness flips only
    if it actually exercises that function.  A one-liner (`def f(): return 1`) shares its signature
    line with the body, so a line-span replacement can't isolate the body — it is skipped."""
    out: list = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out

    def rec(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.body[0].lineno > child.lineno:
                    out.append((prefix + child.name, child))
                rec(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                rec(child, prefix + child.name + ".")
            else:
                rec(child, prefix)

    rec(tree, "")
    return out


def _mutate_lines(text: str, nodes: list) -> str:
    """Replace each given def's body line-span with an UNCATCHABLE raise, leaving the rest of the
    file byte-identical (so a source-grep witness flips only when ITS grepped text lived in a mutated
    body, not because the file was reformatted).  BaseException — not Exception — so a witness's own
    `except Exception` cannot swallow the mutation (MONOTONE BY CONSTRUCTION)."""
    lines = text.splitlines(keepends=True)
    for node in sorted(nodes, key=lambda n: n.body[0].lineno, reverse=True):
        s, e = node.body[0].lineno, node.end_lineno
        col = node.body[0].col_offset
        lines[s - 1:e] = [" " * col + "raise BaseException('PAPERKIT_MUT')\n"]
    return "".join(lines)


def emit_mutant(text: str, qualname: str) -> str:
    """The module with exactly the def-site `qualname`'s body replaced by the uncatchable raise.
    Raises KeyError (Ν·loud) if the qualname is not a def-site in the module — never silently a no-op."""
    for qn, node in _def_sites(text):
        if qn == qualname:
            return _mutate_lines(text, [node])
    raise KeyError(f"Ζ·mutant: '{qualname}' is not a def-site in the module")


if __name__ == "__main__":
    module, qualname = sys.argv[1], sys.argv[2]
    sys.stdout.write(emit_mutant(open(module).read(), qualname))
