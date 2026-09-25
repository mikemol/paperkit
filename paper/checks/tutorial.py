#!/usr/bin/env python3
"""Ν·genre·tutorial — one unit per GROUNDING DEPTH: the prerequisite cut.

A tutorial is read forward by someone who does not yet know the material, so nothing may appear
before what it rests on.  That is exactly the grounding DAG's depth: a claim at depth `d` has every
premise at depth `< d`, so reading the units in order is reading the argument in dependency order.
Depth 0 is the foundational atoms — everything that rests on nothing, which is where a tutorial
starts by definition rather than by choice.

⚑ NOT A BUILT-IN IN DISGUISE (checked BEFORE writing — Ν-F1).  No built-in at any of six γ values
produces the depth partition.  It cannot be one: γ moves the BRACKETING of the section grouping,
while depth cuts across every section by a property of the rests-on graph.

⚑⚑ FIVE SIBLING PROPOSALS WERE REFUTED BY THE SAME CHECK, AND THAT IS THE FINDING (Ν-F9).  The
survey's "needs a script" column listed six; measured against the objective population first:
`cookbook` (one unit per problem-cone) is `atomic` — every claim's cone is distinct on this corpus;
`procedure` (singletons absorbed forward — THE PLAN'S OWN WORKED EXAMPLE) is `staged@γ=1.0`;
`example-collection`, `effective/style` and `service-manual` are degenerate (99%, 71%, 100% of the
corpus in one unit).  Writing any of them would have produced a file whose objective the registry
already had, or a pagination that does not paginate.

DEPTH IS COMPUTED HERE, NOT READ.  `rests-on` arrives on the records (Κ's channel, the same path
`serial` reads `_src` through); depth is its transitive property.  The walk is cycle-safe by the
guard `clamp()` uses — a key already on the current path contributes 0 rather than recursing —
because a cycle is a POSTULATE, not a crash (Δ: `boundaries_grounding.py` asserts a cycle
TERMINATES and gates, where a DANGLING edge FAILS).

⚑ AN EDGE TO A KEY OUTSIDE THE GROUPING IS IGNORED, NOT TREATED AS DEPTH 0.  A `rests-on` naming a
claim in another project (an `imported` grade) would otherwise silently deepen everything that
mentions it, so only premises present in the corpus count — the same restriction `_collection`
places on its cross-group edges (`owner.get(y) is not None`).

TOTALITY.  Every key has exactly one depth, so grouping by it is a partition by construction.  A
key with no record lands at depth 0 — the honest default: nothing is known to precede it.
"""
import genrekit


def depths(rests):
    """key -> grounding depth. 0 for an atom; else 1 + max over premises IN the corpus."""
    memo = {}

    def d(k, path):
        if k in memo:
            return memo[k]
        if k in path:
            return 0                       # a cycle contributes nothing (the clamp() guard shape)
        ps = [p for p in rests.get(k, ()) if p in rests]
        v = 0 if not ps else 1 + max(d(p, path | {k}) for p in ps)
        memo[k] = v
        return v

    return {k: d(k, frozenset()) for k in rests}


def tutorial(groups):
    """One unit per depth, shallowest first — prerequisites before what needs them."""
    rests = genrekit.field("rests-on", [])
    # every key in the grouping is a node, even if its record carried no rests-on: a claim absent
    # from the graph is an atom, not a missing one.
    for g in groups:
        for k in g:
            rests.setdefault(k, [])
    depth = depths(rests)          # computed ONCE — it is a property of the graph, not of a key
    by_depth = {}
    for g in groups:
        for k in g:
            by_depth.setdefault(depth.get(k, 0), []).append(k)
    return [by_depth[d] for d in sorted(by_depth)]


if __name__ == "__main__":
    raise SystemExit(genrekit.run(tutorial))
