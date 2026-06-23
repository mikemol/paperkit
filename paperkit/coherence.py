#!/usr/bin/env python3
"""paperkit coherence (∂²) — measure how far a project's DECLARED structure reflects
its MEASURED sensitivity: the boundary-of-a-boundary residual.

Δ grades whether each check CAN fail; ∂² asks whether the structure the claims declare
actually shows up in what makes them fail.  Three faces, all read from the existing
pipeline (`discriminate --resolution def --json`), so nothing new is measured — re-read:

  STRUCTURE   each claim carries a `from` edge (prose order) and a `rests-on` edge
              (grounding).  Where the two graphs diverge they do not reflect; until a
              typed `move` unifies them (one chiral edge) this divergence is the raw
              residual of face one.

  SENSITIVITY each claim's measured sensitivity set is its Δ `tests` (the inputs whose
              corruption flips it).  --without-K makes the witnesses NAME-distinct, but
              they may still COLLAPSE to one sensitivity signature — name-distinct yet
              measuring the same thing.  At definition resolution every witness carries a
              distinct engine-capability fingerprint, so the collapse closes.

  GROUNDING   each DECLARED grounding edge (rests-on) should be REFLECTED in measured
              sensitivity: a claim that rests-on Y should exercise some of the engine Y
              tests (their fingerprints overlap).  A declared-but-disjoint edge is
              grounding the measurement does not see — the comparison the definition-
              resolution fingerprint makes possible.

A high residual is not a failure to hide — it is the gap between what a document SAYS
grounds it and what DEMONSTRABLY does, surfaced so it can be closed (move-unification
for structure; definition-resolution fingerprints for sensitivity and grounding).

    coherence.py [DIR]            # the residual report
    coherence.py --json [DIR]     # structured
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project as P  # noqa: E402  (read the declared `link` acknowledgments)

_ENGINE = Path(__file__).resolve().parent


def structure_residual(records: list, discharged=frozenset()) -> dict:
    """Face one: where `from` (prose) and `rests-on` (grounding) disagree.  A pure
    function of the records.  Divergence is not a defect — prose and grounding are
    chiral (one edge, two readings), so an author DISCHARGES a divergence with a `link`
    footnote acknowledging the link's strength (graphviz's constraint=false, made
    human).  The residual is ADVISORY: how many divergences remain un-acknowledged."""
    divergent, edges, undischarged = 0, 0, 0
    for r in records:
        d = set(r.get("from", [])) ^ set(r.get("rests-on", []))
        if d:
            divergent += 1
            edges += len(d)
            if r["key"] not in discharged:
                undischarged += 1
    return {"divergent_claims": divergent, "divergent_edges": edges, "undischarged": undischarged}


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


def _engine_cap(tests) -> set:
    """The engine-capability fingerprint: the def-resolution sites under `paperkit/`,
    EXCLUDING the shared witness scaffolding (`paperkit/tests/` — the fixture builder)
    and the claim's own `checks/` script.  Two witnesses always co-flip on the helpers
    they share, so grounding overlap measured on the FULL fingerprint is trivially
    satisfied by scaffolding; restricting to engine capability is what makes it test
    real grounding."""
    return {t for t in tests
            if t.startswith("paperkit/") and not t.startswith("paperkit/tests/")}


def grounding_residual(records: list) -> dict:
    """Face three (the comparison the roadmap reserved): does each DECLARED grounding
    edge (`rests-on`) show up in MEASURED sensitivity?  A claim X that rests-on Y should
    exercise some of the engine Y tests — their engine-capability fingerprints should
    OVERLAP.  A rests-on edge X→Y whose fingerprints are DISJOINT is declared grounding
    the measurement does not see: X says it stands on Y yet flips on nothing Y flips on
    (often because X itself measurably tests no engine capability — a thesis/meta claim
    grounded rhetorically, not behaviourally).  Advisory, like the other two faces."""
    S = {r["key"]: _engine_cap(r.get("tests", [])) for r in records}
    edges = reflected = unreflected = 0
    misses = []
    for r in records:
        sx = S.get(r["key"], set())
        for y in r.get("rests-on", []):
            sy = S.get(y)
            if not sy:                          # Y measures no engine capability — no claim to test
                continue
            edges += 1
            if sx & sy:
                reflected += 1
            else:
                unreflected += 1
                misses.append([r["key"], y])
    return {"grounding_edges": edges, "reflected": reflected,
            "unreflected": unreflected, "misses": misses}


def report(records: list, discharged=frozenset()) -> dict:
    cited = [r for r in records if r.get("cited", True)]
    return {"claims": len(cited),
            "structure": structure_residual(cited, discharged),
            "sensitivity": sensitivity_residual(cited),
            "grounding": grounding_residual(cited)}


def _records(project_dir: Path) -> list:
    # def resolution: the sensitivity face is only meaningful at the per-definition
    # fingerprint — at file resolution every witness collapses to the import-crash
    # signature.  This is the costly grade (the on-demand precision pass), not the hook's.
    r = subprocess.run([sys.executable, str(_ENGINE / "discriminate.py"),
                        "--resolution", "def", "--json", str(project_dir)],
                       capture_output=True, text=True)
    return json.loads(r.stdout or "[]")


def _discharged(project_dir: Path) -> set:
    """Claims carrying a `link` footnote — the author has acknowledged that this claim's
    prose and grounding edges diverge, and why; that discharges the advisory."""
    cfg = P.load_config(project_dir)
    F = {}
    for b in cfg["bibs"]:
        F.update(P.entries(b))
    return {k for k, f in F.items() if f.get("link")}


def main(argv: list) -> int:
    as_json = "--json" in argv
    pos = [a for a in argv if not a.startswith("-")]
    project_dir = Path(pos[0]).resolve() if pos else Path.cwd()
    rep = report(_records(project_dir), _discharged(project_dir))
    if as_json:
        print(json.dumps({"document": project_dir.name or str(project_dir), **rep}, indent=2))
        return 0
    s, se, g = rep["structure"], rep["sensitivity"], rep["grounding"]
    print(f"coherence (∂²): {project_dir.name or project_dir} — {rep['claims']} cited claims")
    print(f"  structure  : {s['divergent_claims']} claims diverge between from and rests-on "
          f"({s['divergent_edges']} edges); {s['undischarged']} un-acknowledged "
          f"(advisory — discharge with a `link` footnote)")
    print(f"  sensitivity: {se['behavioral']} behavioral witnesses → {se['signatures']} distinct "
          f"sensitivity signatures ({se['collapse']} collapse); the largest {se['largest_class']} "
          f"share {se['largest_signature']}")
    print(f"  grounding  : {g['reflected']}/{g['grounding_edges']} rests-on edges reflected in "
          f"measured engine sensitivity; {g['unreflected']} declared-but-disjoint "
          f"(advisory — a claim grounded rhetorically, not behaviourally)")
    for x, y in g["misses"]:
        print(f"               [@{x}] rests-on [@{y}] — engine fingerprints disjoint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
