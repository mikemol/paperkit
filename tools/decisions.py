#!/usr/bin/env python3
"""Μ·sweep·atom — the DECISION-COVERAGE aggregator, the grid twin of grader.decisions_unasserted.

A claim's reached-but-UNASSERTED decisions: conditions (and data values) the check runs both sides of
yet whose verdict is indifferent to which outcome selected — coverage the coarse behavioral grade cannot
see.  An ORTHOGONAL axis, never a rung: it names a coverage gap, it does not lower the grade.

Consumes two pre-built cell sets (each a pk_eval record `{site, flipped}`):
  --flips  the flip:<qn>#<n> cells (a NON-monotone condition inversion).  flipped=True  ⟺ inverting the
           condition flips the check red ⟺ the check ASSERTS on that decision.
  --reach  the raise-kind cells — branch:<qn>#<n> (arm reach) and data-:<QN>#<n> (key read).  flipped=True
           ⟺ that arm/key is genuinely REACHED (its raise/drop flips the check).

THE GRID GIVES SIBLING-INDEPENDENCE FOR FREE.  Each cell is single-site, so a cell's `flipped` bit IS a
per-arm/per-key reach probe — no group-testing correlation, so no flip_one re-probe (the in-process path
needs flip_one precisely because its group-testing `sens` correlates siblings; the grid does not).

Decision rules (mirroring grader.decisions_unasserted):
  flip:<qn>#<n>  UNASSERTED iff BOTH sibling branch:<qn> arms are reached (reach flipped=True) AND the
                 inversion does NOT flip (flips flipped=False) — both outcomes provably exercised, yet the
                 verdict is indifferent to which condition selected them.  Requiring BOTH arms rules out
                 the "coincidentally invariant because the fixture only takes one path" false positive.
  data-:<QN>#<n> A dflip: value's sibling is the SAME (QN,n) data-: DROP (one unambiguous sibling, no
                 correlated-flip confound — so ONE reached sibling suffices where branch needed both).
                 The dflip: PERTURB cell (a valid same-position counterfactual that does NOT flip) is
                 emitted as a flip:-kind record over the data key; UNASSERTED iff the drop is reached AND
                 the perturb does not flip.

Usage: decisions.py --flips <rec>... --reach <rec>...   →  {"decisions_unasserted": [labels]} on stdout."""
import argparse
import json
import sys


def _load(paths):
    return [json.load(open(p)) for p in paths]


def _qn_n(site):
    """`file::flip:qn#n` / `file::branch:qn#n` / `file::data-:QN#n` → (file, kind, qn, n)."""
    file, _, spec = site.partition("::")
    kind, _, rest = spec.partition(":")
    qn, _, n = rest.rpartition("#")
    return file, kind, qn, (int(n) if n.isdigit() else None)


def decisions_unasserted(flips, reach):
    """The reached-but-unasserted decision labels.  flips/reach are pk_eval records `{site, flipped}`."""
    # reach index: (file, kind, qn) → {n: flipped}, so a flip:/dflip: can find its reached siblings.
    reached = {}
    for r in reach:
        file, kind, qn, n = _qn_n(r["site"])
        reached.setdefault((file, kind, qn), {})[n] = bool(r.get("flipped"))

    out = []
    for fr in flips:
        site = fr["site"]
        file, kind, qn, n = _qn_n(site)
        inversion_flips = bool(fr.get("flipped"))
        if inversion_flips:
            continue                                     # the check ASSERTS on this decision — not a gap
        if kind == "flip":
            # a code condition: BOTH sibling branch: arms must be genuinely reached.
            arms = reached.get((file, "branch", qn), {})
            if len(arms) >= 2 and all(arms.values()):
                out.append(site)                         # both arms run, verdict indifferent → unasserted
        elif kind == "dflip":
            # a data value: its ONE sibling is the data-: DROP of the same (QN, n) — the key must be read.
            drop = reached.get((file, "data-", qn), {})
            if drop.get(n):                              # the key IS read (its drop flips), perturb does not
                out.append(site)                         # reads the entry, indifferent to its value → unasserted
    return sorted(out)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--flips", nargs="*", default=[])
    ap.add_argument("--reach", nargs="*", default=[])
    a = ap.parse_args(argv)
    out = decisions_unasserted(_load(a.flips), _load(a.reach))
    print(json.dumps({"decisions_unasserted": out}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
