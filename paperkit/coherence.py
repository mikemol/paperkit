#!/usr/bin/env python3
"""paperkit coherence (∂²) — measure how far a project's DECLARED structure reflects
its MEASURED sensitivity: the boundary-of-a-boundary residual.

Δ grades whether each check CAN fail; ∂² asks whether the structure the claims declare
actually shows up in what makes them fail.  Two faces, both read from the existing
pipeline (`discriminate --json`), so nothing new is measured — only re-read:

  STRUCTURE   each claim carries a `from` edge (prose order) and a `rests-on` edge
              (grounding).  Where the two graphs diverge they do not reflect; until a
              typed `move` unifies them (one chiral edge) this divergence is the raw
              residual of face one.

  SENSITIVITY each claim's measured sensitivity set is its Δ `tests` (the inputs whose
              corruption flips it).  --without-K makes the witnesses NAME-distinct, but
              they may still COLLAPSE to one sensitivity signature — name-distinct yet
              measuring the same thing.  A document whose N witnesses share K << N
              signatures is non-closed: distinctness that the measurement does not see.

A high residual is not a failure to hide — it is the gap between what a document SAYS
grounds it and what DEMONSTRABLY does, surfaced so it can be closed (move-unification
for structure; a wider mutation surface / real per-claim witnesses for sensitivity).

    coherence.py [DIR]            # the residual report
    coherence.py --json [DIR]     # structured
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ENGINE = Path(__file__).resolve().parent


def structure_residual(records: list) -> dict:
    """Face one: where `from` (prose) and `rests-on` (grounding) disagree.  A pure
    function of the records, so it is independent of how they were graded."""
    divergent, edges = 0, 0
    for r in records:
        d = set(r.get("from", [])) ^ set(r.get("rests-on", []))
        if d:
            divergent += 1
            edges += len(d)
    return {"divergent_claims": divergent, "divergent_edges": edges}


def sensitivity_residual(records: list) -> dict:
    """Face two: how many DISTINCT sensitivity signatures the behavioral witnesses
    actually have, vs how many name-distinct witnesses there are.  The collapse is the
    count that share their signature with another (name-distinct, sensitivity-same)."""
    sigs: dict = {}
    for r in records:
        if r.get("grade") != "behavioral":
            continue
        sigs.setdefault(tuple(sorted(r.get("tests", []))), []).append(r["key"])
    classes = sorted(sigs.values(), key=len, reverse=True)
    behavioral = sum(len(c) for c in classes)
    largest = classes[0] if classes else []
    return {
        "behavioral": behavioral,
        "signatures": len(classes),
        "collapse": behavioral - len(classes),          # redundant witnesses, by sensitivity
        "largest_class": len(largest),
        "largest_signature": list(largest and sorted(sigs.keys(), key=lambda k: len(sigs[k]))[-1]),
    }


def report(records: list) -> dict:
    cited = [r for r in records if r.get("cited", True)]
    return {"claims": len(cited),
            "structure": structure_residual(cited),
            "sensitivity": sensitivity_residual(cited)}


def _records(project_dir: Path) -> list:
    r = subprocess.run([sys.executable, str(_ENGINE / "discriminate.py"), "--json", str(project_dir)],
                       capture_output=True, text=True)
    return json.loads(r.stdout or "[]")


def main(argv: list) -> int:
    as_json = "--json" in argv
    pos = [a for a in argv if not a.startswith("-")]
    project_dir = Path(pos[0]).resolve() if pos else Path.cwd()
    rep = report(_records(project_dir))
    if as_json:
        print(json.dumps({"document": project_dir.name or str(project_dir), **rep}, indent=2))
        return 0
    s, se = rep["structure"], rep["sensitivity"]
    print(f"coherence (∂²): {project_dir.name or project_dir} — {rep['claims']} cited claims")
    print(f"  structure  : {s['divergent_claims']} claims diverge between from and rests-on "
          f"({s['divergent_edges']} edges) — prose and grounding graphs do not yet reflect")
    print(f"  sensitivity: {se['behavioral']} behavioral witnesses → {se['signatures']} distinct "
          f"sensitivity signatures ({se['collapse']} collapse); the largest {se['largest_class']} "
          f"share {se['largest_signature']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
