"""Ζ·re·any — the typed seam over Python's `re`, which is an untyped boundary.

⚑ WHY THIS MODULE EXISTS, MEASURED RATHER THAN ANTICIPATED.  typeshed types `Match.group()`,
`Match.groups()`, `Match.groupdict()` and `Pattern.findall()` as `Any` (or `list[Any]`), because
a pattern's group count and types are not known statically.  Under `disallow_any_expr` — the
load-bearing flag of paperkit's mypy bar — every one of those results POISONS every expression
derived from it, and the poison FANS OUT: a caller of an Any-returning expression is itself Any.

The first converted witness that was regex-heavy (`render/checks/bib.py`) took four lint rounds,
three of them this.  So before converting the rest, the population was counted:

    16 of 31 remaining render witnesses carry a leaky `re` call — 65 sites
    heaviest: widen_tables 11 · omml 10 · slides 7 · ruler_inject 6 · a11y_own 5 · source 5

Half the population, and that is render ALONE — `paperkit/tests` (50 files) and five other
`checks/` trees have the same boundary.  Narrowing 65 times in place would be 65 chances to do it
differently, which is how one capability grows several bodies.

⚑ IT LIVES IN THE ENGINE, NOT IN render/checks/, BECAUSE THE BOUNDARY IS NOT RENDER'S.  Every
project's witnesses parse text; `re` is stdlib.  Placing it beside its first consumer would be
the filesystem encoding what ownership should — the same error this whole arc is retiring.

WHAT IT IS NOT: a wrapper that hides `re`.  Callers still compile their own patterns and still
call `.search()`/`.finditer()`.  These functions narrow only the RESULT-READING seam, which is
exactly where the Any is, and each returns a concrete type.  One walled seam, callers clean.

⚑ `re` IS IMPORTED FOR TYPING ONLY, and that is not an accident of style: every function here
takes an already-built `Match`/`Pattern` and calls a METHOD on it.  The module name appears only
in annotations, so the import belongs in the type-checking block — which also means this seam
adds no import cost to a witness that does not use it.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import re


def group(m: re.Match[str], n: int | str = 0) -> str:
    """Return the `n`th group of `m` as `str`.

    Raises if the group did not participate — use `opt_group` when absence is legal.  The
    distinction is deliberate: a witness reading a group it KNOWS matched should not silently
    receive None and compare it against a string.
    """
    g: str | None = m.group(n)
    if g is None:
        msg = f"group {n!r} did not participate in the match"
        raise ValueError(msg)
    return g


def opt_group(m: re.Match[str], n: int | str = 0) -> str | None:
    """Return the `n`th group of `m`, or None when that group did not participate."""
    g: str | None = m.group(n)
    return g


def groups(m: re.Match[str]) -> tuple[str | None, ...]:
    """Return every group of `m`, each `str` or None — typed, unlike `Match.groups()`."""
    gs: tuple[str | None, ...] = m.groups()
    return gs


def findall(p: re.Pattern[str], s: str) -> list[str]:
    """Return every non-overlapping match of `p` in `s`.

    ⚑ ONLY SOUND FOR A PATTERN WITH ZERO OR ONE GROUP.  `re.findall` returns a list of TUPLES
    when the pattern has two or more groups, so this signature would be a lie there — use
    `tuples()` for that shape.  Asserting it would cost a scan of the results on every call;
    naming the precondition is the honest trade.
    """
    out: list[str] = p.findall(s)
    return out


def tuples(p: re.Pattern[str], s: str) -> list[tuple[str, ...]]:
    """Return every match of `p` in `s` as a group tuple — the multi-group form of `findall`."""
    out: list[tuple[str, ...]] = p.findall(s)
    return out
