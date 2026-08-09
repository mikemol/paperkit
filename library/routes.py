#!/usr/bin/env python3
"""library/routes.py — Λ·key·graded: the GRADED concept-route walk, and the exit-code protocol.

A concept library maps a KEY to a witness.  The flat form — `key -> nullary function` — forces a
distinct Python function per claim, because `--without-K` requires every cited claim to carry a
distinct witness (gate.py: it compares check STRINGS, so distinctness is at KEY granularity).  A
domain with a parameter axis therefore has to choose between a copy per argument (drift) or one
witness serving many claims (which --without-K forbids).

The graded key dissolves that: a key is `family[/subfamily]/argument`, resolved by walking a nested
dict to a `(fn, arg)` leaf.  `orbit/OR` and `orbit/XOR` are DISTINCT keys — so distinct witnesses to
the gate — while SHARING one implementation.  The parameter is what makes reuse and proof-relevance
compatible.

GRADE IS A DEGENERATE CASE, NOT A KIND.  The walk consumes `/`-separated segments until it reaches a
non-dict, so it serves every grade with one loop:

    grade 0   `adequacy-pitch`              a flat table: key -> leaf
    grade 1   `orbit/XOR`                   family -> arg
    grade 2   `operator/closure/all`        family -> subfamily -> arg
    grade n   ...                           no bound; the walk is depth-agnostic

This matters concretely: paperkit's own library is a GRADE-0 table, so adopting this file is a no-op
for its ~20 existing keys and bib records, not a migration.  (mdt's dispatch hard-codes
`if "/" not in key: return 2`, which would reject grade 0; that line is the one thing here that is
deliberately NOT lifted.)

THE EXIT-CODE PROTOCOL is the load-bearing generic, more than the walk:

    0   certified
    1   FAILED          — the witness raised AssertionError
    2   not mine        — no such route, OR the leaf raised KeyError

`KeyError -> 2` is deliberate and easy to get wrong.  A witness whose argument arm ends in
`raise KeyError(which)` is saying "this argument is not one I serve", which is indistinguishable
from an unresolved route — so both must read as "not mine" and fall through to the next resolver.
That is exactly the sentinel `resolver.py` relies on (Λ·library·fallthrough: a project library
answering 2 falls through to the engine's).

The INVERSE rule belongs beside it, because the two are a pair and only make sense together:
a MISSING TOOL must exit 1 (FAILED), never 2.  A check that cannot run has not been shown to
apply-and-pass; reading it as "not mine" lets a gate skip it silently, which is the one failure a
gate exists to prevent.  Resolvers for external toolchains (mdt's `agda:`) state this explicitly.
"""
from __future__ import annotations

import sys


def walk(routes: dict, key: str):
    """Resolve KEY against ROUTES to its `(fn, arg)` leaf, or None if this table does not serve it.

    Depth-agnostic: segments are consumed until a non-dict is reached.  A leftover segment (the key
    is longer than the table is deep) and a non-tuple leaf both resolve to None — "not mine", not an
    error, because a longer key may well belong to a different library."""
    node, rest = routes, key
    while isinstance(node, dict):
        head, _, rest = rest.partition("/")
        if head not in node:
            return None
        node = node[head]
        if not isinstance(node, dict):
            break
    if not isinstance(node, tuple) or rest:
        return None
    return node


def leaves(routes: dict):
    """Every `(path, (fn, arg))` leaf in ROUTES, path as a tuple of segments.

    THE one recursive leaf-walk.  The resolver, the `meta` family, and the check cache all need to
    enumerate a table, and mdt had two implementations of this contract — the dispatch walk was
    depth-agnostic while the cache's was hard-coded to two levels, so a grade-3 family would be
    served by one and silently DROPPED by the other (dropped from the cache's driver loop, hence
    never run at all).  One function, one contract."""
    out = []

    def rec(node, path):
        for k, v in node.items():
            if isinstance(v, dict):
                rec(v, path + [k])
            else:
                out.append((tuple(path + [k]), v))

    rec(routes, [])
    return out


def dispatch(routes: dict, key: str, name: str = "concept", report: bool = True) -> int:
    """Run KEY's witness and return its exit code under the protocol above.

    NAME prefixes the verdict lines so a reader can tell WHICH library answered — `concept:` falls
    back from a project's library to the engine's, and the fallback is silent by design, so an
    unprefixed message reads as coming from a library the reader never wrote.

    REPORT=False returns the code SILENTLY, for callers that consume the verdict rather than
    display it: a check cache recording it, or a witness asserting over the protocol itself (whose
    own probe lines would otherwise land on the real streams and read as the caller's output)."""
    node = walk(routes, key)
    if node is None:
        return 2                                    # not mine — fall through
    fn, arg = node
    try:
        fn(arg) if arg is not None else fn()
    except KeyError:
        return 2                                    # "not an argument I serve" — also not mine
    except AssertionError as e:
        if report:
            print(f"{name}/{key}: FAILED — {e}", file=sys.stderr)
        return 1
    if report:
        print(f"{name}/{key}: certified")
    return 0


def meta_family(routes: dict):
    """The SECOND-ORDER witness: a family whose ARGUMENT names another family.

    A first-order witness speaks only about its own argument; a second-order one speaks about the
    SHAPE of a family — which is where an empty-subfamily defect hides, being invisible to every
    individual key.  Three operations:

        total/<fam>      every key in the family certifies
        occupancy/<fam>  the argument axis is fully occupied at its declared grade — no empty
                         subfamily, and the grade is not spurious
        distinct/<fam>   no two keys route to the SAME witness — `--without-K` asked of a FAMILY
                         rather than of the cited claims

    ROUTES is INJECTED, not read from a module global: that is what makes this reusable across
    libraries (mdt's version closed over its own `ROUTES` at module scope)."""

    def meta(which_and_target):
        if "/" not in which_and_target:
            raise KeyError(which_and_target)
        op, fam = which_and_target.split("/", 1)
        route = routes.get(fam)
        if route is None or not isinstance(route, dict):
            raise KeyError(which_and_target)
        ls = leaves(route)
        if op == "total":
            bad = []
            for path, (fn, arg) in ls:
                try:
                    fn(arg) if arg is not None else fn()
                except AssertionError:
                    bad.append("/".join(path))
            assert not bad, f"{fam}: keys that do not certify: {bad}"
            assert ls, f"{fam} is empty"
        elif op == "occupancy":
            # TABLE-HEALTH, not content: a grade that carries no distinction is spurious.  A
            # one-subfamily grade-2 family and a singleton grade-1 family both announce an axis
            # they do not actually have.
            subs = {k: v for k, v in route.items() if isinstance(v, dict)}
            if subs:
                empty = [k for k, v in subs.items() if not v]
                assert not empty, f"{fam}: EMPTY subfamilies {empty}"
                assert len(subs) > 1, f"{fam} has one subfamily — grade 2 is spurious"
            else:
                assert len(route) > 1, f"{fam} is a singleton at grade 1"
        elif op == "distinct":
            seen = {}
            for path, target in ls:
                seen.setdefault((target[0].__name__, target[1]), []).append("/".join(path))
            dup = {k: v for k, v in seen.items() if len(v) > 1}
            assert not dup, f"{fam}: keys sharing a witness: {dup}"
        else:
            raise KeyError(which_and_target)

    return meta


def register_meta(routes: dict, ops=("total", "occupancy", "distinct")) -> dict:
    """Install the `meta` family into ROUTES, over the families present AT THIS MOMENT.

    An explicit FINALISER, which mdt's module-level `ROUTES["meta"] = {...}` comprehension was not:
    that construction reads `for fam in ROUTES` and so silently snapshots whatever the table held at
    whatever line it happened to sit on, making "the table is now closed" a line-number accident.
    Naming it makes the moment explicit — and makes it an error to add a family afterwards and
    expect `meta/` to see it.  Mutates and returns ROUTES."""
    meta = meta_family(routes)
    routes["meta"] = {op: {fam: (meta, f"{op}/{fam}") for fam in routes if fam != "meta"}
                      for op in ops}
    return routes
