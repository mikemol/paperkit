#!/usr/bin/env python3
"""Ν·genre·kit — the shared core every project-declared genre in this project needs.

⚑ FACTORED FROM A MEASURED WEDGE, NOT FROM TASTE.  `reuse_check.py --propose serial.py --against
brief.py` reported `main ∩ main = 23` shared support with verdict **OVERLAP — factor the shared
core; each keeps its residue**.  OVERLAP is not "no action" (the wedge skill's first named
anti-pattern); it is the instruction to lift the intersection.  Two genres existed and two more
were about to be written, which would have made four copies of one stdin-parse/print loop.

What is SHARED (lifted here): reading the tab-separated grouping from stdin, reading the records
Κ's channel supplies, writing units back as tab-separated lines.
What is RESIDUE (stays per-genre): the objective itself — the only thing a genre actually IS.

⚑ THE PROTOCOL, so no genre re-derives it (and D1, so no genre trips on it):
  · stdin  — one GROUP per line, keys tab-separated.  KEYS ONLY.
  · stdout — one UNIT per line, same shape.
  · ⚑ `--observe` prints a LEADING SECTION COLUMN (`project.py:639`), so CLI output is NOT valid
    stdin here.  Feeding it back makes `is_total` refuse the section labels as INVENTED KEYS —
    an error naming totality when the fault is a column offset (Θ, tick 20).
  · exit non-zero ⇒ the engine raises rather than reading an empty pagination.
  · the result is held to `is_total`: every input key in EXACTLY one output unit.
"""
import json
import os
import sys


def groups():
    """The incoming grouping: one group per line, tab-separated keys."""
    return [ln.split("\t") for ln in sys.stdin.read().splitlines() if ln.strip()]


def records():
    """The claim records from Κ's channel (`PAPERKIT_GENRE_RECORDS`), or [] if unset.

    Absence is not an error: the engine always sets it, but a hand invocation has no reason to.
    ⚑ What the EMPTY case means is the GENRE's business, not this helper's — `serial` degenerates
    to `atomic` there (no provenance ⇒ no issue structure to assert) while a length-banded genre
    degenerates to the identity.  Returning [] and letting each objective decide is the honest
    split; a default here would silently impose one genre's reading on every other.
    """
    path = os.environ.get("PAPERKIT_GENRE_RECORDS")
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def field(name, default=None):
    """`{key: record[name]}` over the records — the shape every objective actually wants.

    Written as a mapping rather than the record list because every consumer so far immediately
    builds one: `serial` wants `_src`, a budget genre wants `claim`, `_collection`'s declared twin
    would want `rests-on`.
    """
    return {r["key"]: r.get(name, default) for r in records() if "key" in r}


def emit(units):
    """Write units back, one per line, tab-separated — skipping empties.

    An empty unit is not a page; `is_total` compares multisets of KEYS, so dropping one is
    invisible to the invariant and honest about what a unit is.
    """
    for u in units:
        if u:
            print("\t".join(u))


def run(objective):
    """Read the grouping, apply the objective, write the units.  The whole per-genre `main`.

    `objective` takes the grouping and returns units — a pure function of what it was given, which
    is what a pagination IS.
    """
    emit(objective(groups()))
    return 0
