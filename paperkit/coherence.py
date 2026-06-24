#!/usr/bin/env python3
"""paperkit coherence (∂²) — measure how far a project's DECLARED structure reflects
its MEASURED sensitivity: the boundary-of-a-boundary residual.

Δ grades whether each check CAN fail; ∂² asks whether the structure the claims declare
actually shows up in what makes them fail.  Three faces, all read from the existing
pipeline (`discriminate --resolution def --json`), so nothing new is measured — re-read:

  STRUCTURE   prose is a LINEARIZATION of the claim-DAG.  A grounding (`rests-on`) edge
              between prose-ADJACENT claims is carried by the connective for free; a
              NON-ADJACENT one is a LONG EDGE the linear text owes a projected cross-
              reference (citation / figure / expounding — what a connective IS at distance
              > 0).  The residual is the long edges not yet projected.

  SENSITIVITY each claim's measured sensitivity set is its Δ `tests` (the inputs whose
              corruption flips it).  --without-K makes the witnesses NAME-distinct, but
              they may still COLLAPSE to one sensitivity signature — name-distinct yet
              measuring the same thing.  At definition resolution every witness carries a
              distinct engine-capability fingerprint, so the collapse closes.

  GROUNDING   each DECLARED grounding edge (rests-on) should be REFLECTED in measured
              sensitivity: a claim that rests-on Y should exercise some of the engine Y
              tests (their fingerprints overlap).  A disjoint edge is discharged when its
              non-reflection is explained — MEASURABLY (X tests no engine capability, so it
              is vacuously disjoint: rhetorical grounding) or by a `link` (the sibling of
              the structure discharge).  Only a GENUINE, un-acknowledged miss is residual.

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


def _linearize(records: list) -> dict:
    """The prose linearization: each section's claims in dep_order (topological by
    `from`), concatenated in section-first-appearance order.  Returns {key: position}."""
    frm = {r["key"]: r.get("from", []) for r in records}
    secs, order = [], {}
    for r in records:                       # sections in first-appearance order
        s = r.get("section")
        order.setdefault(s, []).append(r["key"])
        if s not in secs:
            secs.append(s)
    pos, idx = {}, 0
    for s in secs:
        seen, out = set(), []

        def visit(k):
            if k in seen or k not in order[s]:
                return
            seen.add(k)
            for a in frm.get(k, []):
                visit(a)
            out.append(k)

        for k in order[s]:
            visit(k)
        for k in out:
            pos[k] = idx
            idx += 1
    return pos


def structure_residual(records: list, discharged=frozenset()) -> dict:
    """Face one, by the EDGE-PROJECTION model.  Prose is a LINEARIZATION of the claim-DAG;
    a grounding (`rests-on`) edge to a prose-ADJACENT claim is carried by the connective
    for free, but a NON-ADJACENT one is a LONG EDGE the linear text owes a projected
    cross-reference — a citation / figure / expounding (the same thing a connective is, at
    distance > 0; the direction is the sign of the prose-distance).  The residual is the
    long edges not yet projected; ADVISORY, dischargeable by a `link` footnote (or, the
    constructive close, by actually projecting the reference)."""
    pos = _linearize(records)
    carried, long_edges = 0, []
    for r in records:
        k = r["key"]
        for y in r.get("rests-on", []):
            if y not in pos or k not in pos:
                long_edges.append((k, y, None))      # cross-scope target — always owed
            elif pos[y] == pos[k] - 1:
                carried += 1                          # the immediate predecessor: connective carries it
            else:
                long_edges.append((k, y, pos[k] - pos[y]))
    undischarged = sum(1 for k, _, _ in long_edges if k not in discharged)
    return {"carried": carried, "owed": len(long_edges), "undischarged": undischarged,
            "long_edges": long_edges}


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


def grounding_residual(records: list, discharged=frozenset()) -> dict:
    """Face three (the comparison the roadmap reserved): does each DECLARED grounding
    edge (`rests-on`) show up in MEASURED sensitivity?  A claim X that rests-on Y should
    exercise some of the engine Y tests — their engine-capability fingerprints should
    OVERLAP.  A disjoint edge X→Y is discharged when its non-reflection is EXPLAINED:

      rhetorical    X tests no engine capability at all (an empty fingerprint), so the
                    edge is VACUOUSLY disjoint — a thesis/meta claim grounded rhetorically,
                    not behaviourally.  This is MEASURED, not asserted: it auto-discharges.
      acknowledged  X DOES test engine capability, just not Y's, but a `link` footnote
                    acknowledges it (the sibling of the structure face's discharge).

    Only a GENUINE miss — X tests engine capability, disjoint from Y's, and un-acknowledged
    — is the residual: declared grounding the measurement does not see and no one explained."""
    S = {r["key"]: _engine_cap(r.get("tests", [])) for r in records}
    edges = reflected = rhetorical = undischarged = 0
    misses = []
    for r in records:
        k = r["key"]
        sx = S.get(k, set())
        for y in r.get("rests-on", []):
            sy = S.get(y)
            if not sy:                          # Y measures no engine capability — no claim to test
                continue
            edges += 1
            if sx & sy:
                reflected += 1
            elif not sx:
                rhetorical += 1                 # X's fingerprint is empty — vacuously disjoint (measured)
            elif k in discharged:
                pass                            # author-acknowledged via a `link` footnote
            else:
                undischarged += 1
                misses.append([k, y])
    return {"grounding_edges": edges, "reflected": reflected, "rhetorical": rhetorical,
            "undischarged": undischarged, "misses": misses}


def report(records: list, discharged=frozenset()) -> dict:
    cited = [r for r in records if r.get("cited", True)]
    return {"claims": len(cited),
            "structure": structure_residual(cited, discharged),
            "sensitivity": sensitivity_residual(cited),
            "grounding": grounding_residual(cited, discharged)}


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
    print(f"  structure  : {s['carried']} grounding edges carried by the prose connective, "
          f"{s['owed']} are LONG edges owed a projected cross-reference; {s['undischarged']} "
          f"un-acknowledged (advisory — project the reference, or discharge with a `link`)")
    print(f"  sensitivity: {se['behavioral']} behavioral witnesses → {se['signatures']} distinct "
          f"sensitivity signatures ({se['collapse']} collapse); the largest {se['largest_class']} "
          f"share {se['largest_signature']}")
    print(f"  grounding  : {g['reflected']}/{g['grounding_edges']} rests-on edges reflected in "
          f"measured engine sensitivity; {g['rhetorical']} vacuously disjoint (rhetorical — the "
          f"claim tests no engine capability); {g['undischarged']} genuine, un-acknowledged "
          f"(advisory — overlap the fingerprints, or discharge with a `link`)")
    for x, y in g["misses"]:
        print(f"               [@{x}] rests-on [@{y}] — tests engine capability, but not [@{y}]'s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
