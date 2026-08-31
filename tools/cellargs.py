#!/usr/bin/env python3
"""Ζ·argv·typed — one sweep cell's arguments, as a typed record rather than a Namespace.

Split out of `tools/eval.py` (Ζ·eval·split).  Argument parsing is its own concern: it decides
what the cell was ASKED to do, and knows nothing about doing it.

⚑ WHY A DATACLASS AND NOT `argparse.Namespace`.  `Namespace` attributes are typed `Any`, so
every field read poisons every expression derived from it — measured on the original `eval.py`:
of 76 mypy findings, the great majority were `Expression has type "Any"` fanning out from
`a.site`, `a.module`, `a.check` and friends.  `disallow_any_expr` is right about this: a
Namespace is an untyped boundary wearing the shape of a record.

⚑⚑ AND THE NARROWING BUYS A REAL BEHAVIOUR, NOT JUST A CLEAN CHECK.  linux-sources measured the
same thing and named the consequence: hand-parsing into a typed record makes an unknown flag a
TYPED REFUSAL instead of an `AttributeError` at the first use — *"the bug it prevents is 'a
typo'd flag silently does nothing'"*.  For a grid of 137,553 cells whose arguments are generated
by Starlark, a typo'd flag that silently does nothing is a whole sweep's worth of wrong answers
with no red anywhere.

`argparse` still does the PARSING — it owns `--help`, the error messages and the required-flag
checks, and reimplementing that would be the second body of a capability the stdlib already has.
This module converts its result to a record ONCE, at the boundary, and everything downstream sees
concrete types.  One walled seam, callers clean.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class CellArgs:
    """What one def-sweep cell was asked to do."""

    engine_dir: str
    check: str
    claim: str
    site: str
    out: str
    module: str = ""
    mutant_py: str = ""
    mutant_pyc: str = ""
    content_path: str = ""
    content_textfile: str = ""
    peak: str = ""


def _parser() -> argparse.ArgumentParser:
    """Build the cell's argument parser."""
    ap = argparse.ArgumentParser(description="run one def-sweep cell")
    ap.add_argument("--engine-dir", required=True, help="the staged engine dir, e.g. paperkit")
    ap.add_argument("--check", required=True, help="the check script, e.g. paper/checks/claims.py")
    ap.add_argument("--claim", required=True, help="the claim key this cell evaluates")
    ap.add_argument("--site", required=True, help="the def-site label, recorded in the result")
    ap.add_argument("--out", required=True, help="where to write this cell's record")
    ap.add_argument("--module", default="",
                    help="the mutated module's .py path (empty for a file/content cell)")
    ap.add_argument("--mutant-py", default="",
                    help="the mutated module SOURCE (identity for the ∅ baseline)")
    ap.add_argument("--mutant-pyc", default="", help="the mutated module BYTECODE")
    ap.add_argument("--content-path", default="", help="a content cell's target file")
    ap.add_argument("--content-textfile", default="",
                    help="the substring to drop/inject, delivered as a FILE (no shell escaping)")
    ap.add_argument("--peak", default="",
                    help="write this cell's in-scope memory.peak here (empty = not observing)")
    return ap


def parse(argv: list[str]) -> CellArgs:
    """Parse `argv` into a typed record.

    Each field is read from the Namespace exactly ONCE, here, with an explicit `str` annotation —
    which is what confines the Any to this function instead of letting it fan out through every
    caller.  An unknown flag never reaches this point: argparse exits 2 with a message naming it.
    """
    ns = _parser().parse_args(argv)
    engine_dir: str = ns.engine_dir
    check: str = ns.check
    claim: str = ns.claim
    site: str = ns.site
    out: str = ns.out
    module: str = ns.module
    mutant_py: str = ns.mutant_py
    mutant_pyc: str = ns.mutant_pyc
    content_path: str = ns.content_path
    content_textfile: str = ns.content_textfile
    peak: str = ns.peak
    return CellArgs(engine_dir=engine_dir, check=check, claim=claim, site=site, out=out,
                    module=module, mutant_py=mutant_py, mutant_pyc=mutant_pyc,
                    content_path=content_path, content_textfile=content_textfile, peak=peak)
