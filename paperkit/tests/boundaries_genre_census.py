#!/usr/bin/env python3
"""Ξ·bnd-genre-census — every registered genre is a DISTINCT VANTAGE, and the census says so.

⚑ THE APPARATUS'S THESIS, MADE CHECKABLE.  The 21-genre survey was collected to exercise the
codomain of paperkit's architecture, on the design that "each publication genre is its own
vantage" and "disagreement between vantages is DATA, not noise to reconcile".  That thesis is
EMPTY if two genres produce the same partition: they would be one reading wearing two names.

And that is not hypothetical — it is what `brief` was.  It shipped as "the identity on the
grouping" and was measured, one tick later, byte-identical to the built-in `staged` at every γ
(Ν-F1).  A census containing a duplicate reports N vantages and has N−1.

WHAT IS ASSERTED:
  1. no two registered genres produce the SAME partition of the corpus
  2. every genre is TOTAL (already gated elsewhere; re-checked here because a census over a
     non-partition is meaningless)

⚑ DISTANCE IS OVER PAIRS, NOT UNIT COUNTS.  Two genres with the same NUMBER of units may cut
completely differently, and a count would call them identical.  The measure is the fraction of
claim-PAIRS the two disagree about (same-unit vs different-unit) — 0.0 exactly when the partitions
coincide.

⚑ WHAT THIS DOES **NOT** CLAIM.  It does not say the vantages are USEFUL, or that they cover the
codomain, or that 21 was the right number.  It says they are DISTINCT.  A genre measured identical
to another is a finding to record and remove, not a failure of the corpus — and `brief` is kept
deliberately, as the declared-seam regression fixture whose oracle IS `staged`, so it is exempted
BY NAME with its reason rather than by relaxing the check.
"""
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paperkit"))

# ⚑ DECLARED, NOT INFERRED.  `brief` IS `staged` (Ν-F1, measured byte-identical), and it is kept on
# purpose: it is the only regression fixture for the declared-genre seam whose expected output is
# independently derivable from a built-in.  Removing it would delete the test; relaxing the check
# would hide the next accidental duplicate.  So the ONE known duplicate is named here with its
# reason — the `HOOK_EXEMPT` shape (Η-F1), where an exemption states its inhabitant.
# ⚑⚑ AND THE EXEMPTION IS γ-QUALIFIED, BECAUSE THE UNQUALIFIED FORM WAS ALREADY WRONG (Ξ-F4).
# Ν-F1 recorded `brief ≡ staged` "at every γ" — true when measured, because γ was UNREACHABLE then:
# `bib._misplaced_paper_key` refused `gamma` under `[genres.*]` (Ι-F1) so every genre ran at the
# project default.  Ι-F1 made γ reachable, `brief` declares `gamma = 4.0`, and the two now differ
# at their OWN resolutions (0.051) while remaining identical at the SAME one.  A stale-exemption
# check caught the ledger carrying a fact its own repair had invalidated.
KNOWN_DUPLICATE = {
    ("brief", "staged", 4.0): "Ν-F1 — `brief` is the identity on the grouping, which IS `_staged`. "
                              "Kept as the declared-seam regression fixture; `staged` at brief's "
                              "own γ=4.0 is its oracle.",
}


def partition(cfg, genre, project, gamma=None):
    import project as P
    units = [u["keys"] for u in P.observe(cfg, genre, project, gamma)]
    return {k: i for i, u in enumerate(units) for k in u}, units


def disagreement(a, b, keys) -> float:
    n = dis = 0
    for x, y in itertools.combinations(keys, 2):
        n += 1
        if (a[x] == a[y]) != (b[x] == b[y]):
            dis += 1
    return dis / n if n else 0.0


def main() -> int:
    import project as P
    import genre as G

    proj = ROOT / "paper"
    cfg = P.load_config(proj)
    names = sorted(G.registry(proj))
    print("Ξ·bnd-genre-census — every registered genre is a distinct vantage\n")

    cuts, sizes = {}, {}
    for g in names:
        cuts[g], units = partition(cfg, g, proj)
        sizes[g] = len(units)
    keys = sorted(cuts[names[0]])
    bad = 0

    print(f"⟨every genre partitions the corpus⟩\n")
    for g in names:
        total = len(cuts[g]) == len(keys)
        print(f"  {'ok' if total else 'XX'} {g:<11} {sizes[g]:>3} unit(s) over {len(cuts[g])} claims")
        if not total:
            bad += 1

    print(f"\n⟨no two vantages coincide⟩\n")
    dupes = []
    for a, b in itertools.combinations(names, 2):
        d = disagreement(cuts[a], cuts[b], keys)
        if d > 0.0:
            continue
        dupes.append((a, b))
        print(f"  XX {a} ≡ {b} at their own γ — an UNDECLARED duplicate: two names, one reading",
              file=sys.stderr)
        bad += 1
    if not dupes:
        pairs = len(names) * (len(names) - 1) // 2
        print(f"  ok all {pairs} pair(s) are distinct partitions at their declared γ")

    # A stale exemption is the same silent rot the check exists to refuse (Η's lesson).
    # ⚑⚑ THE DECLARED EQUIVALENCE IS ANALYTIC, AND SAYING SO IS THE HONEST FORM (Ξ-F5).
    # A first version tested it "at the γ it is declared at" and called that a stale-exemption
    # guard.  It is not one: an explicit γ overrides BOTH genres' declarations, so `brief` (the
    # identity on the grouping) and `staged` (the identity on the grouping) are compared on the
    # SAME grouping and cannot differ.  The check could not fail — the exact defect Ξ-F3 caught one
    # tick earlier, repeated by me in the fix for it.
    #
    # What IS empirical is whether they differ at their OWN declared resolutions, and that is
    # already covered above: the pairwise scan uses each genre's own γ, so `brief` vs `staged` is a
    # live comparison there (measured 0.051 — they DO differ, which is why the pair is not listed
    # as an undeclared duplicate).  Restating it here would be a second reading of one fact.
    print(f"\n⟨the declared equivalence, stated as what it is⟩\n")
    for (a, b, gamma), why in sorted(KNOWN_DUPLICATE.items()):
        if a not in cuts or b not in cuts:
            print(f"  XX {a} ≡ {b} is declared but one of them is not registered", file=sys.stderr)
            bad += 1
            continue
        live = disagreement(cuts[a], cuts[b], keys)
        print(f"  ok {a} ≡ {b} @γ={gamma} — ANALYTIC (both are the identity on the grouping, so "
              f"at equal γ they cannot differ)")
        print(f"     at their OWN declared γ they differ by {live:.3f} — measured above, not here")
        print(f"     {why}")

    if bad:
        print(f"\nbnd-genre-census: {bad} problem(s) — a census reporting N vantages must HAVE N",
              file=sys.stderr)
        return 1
    print(f"\nBOUNDARIES: PASS ({len(names)} registered genres, all distinct partitions, "
          f"{len(KNOWN_DUPLICATE)} declared duplicate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
