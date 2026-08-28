#!/usr/bin/env python3
r"""Ρ·deck·node — the DECK BOUND: slide FORMATS are first-class; a deck PROJECTION is not.

The render coalgebra (graph.py) now carries `pptx` and `odp` as format objects, so paperkit emits a
gated slide deliverable from the resolved source.  That is a TRANSFORM of the pandoc observation of
an already-linearized document.  It is NOT a new OBSERVATION of the claim-DAG.

The distinction is the whole content of prototypes/slides.bib's `docx-pdf-are-transforms-not-
observations`: an exporter-of-finished-prose makes a deck a second-class artifact that has ALREADY
lost the DAG structure.  `project(cfg, target)` is S -> String — ONE flat stream seeded by
rubric-order × dep-order.  A deck is S -> List(Unit) indexed by (target, genre) — a SEGMENTATION
(one level: slides.bib's recursive RoseTree is unbuilt, Ζ·observe·rosetree) —
into bounded observation-windows.  Different observation type, not a different file extension.

This check gates the bound so it cannot rot into a comment nobody honours.  It asserts:

  1. the slide objects are declared in the coalgebra and every slide route composes real edges
     (the POSITIVE half — the formats really are first-class, so the claim's first clause holds);
  2. no slide format is a citation-materialization TARGET of project.py.  This is what keeps the
     transform and the observation distinguishable now that BOTH exist: Ρ·deck·observe landed as
     project.observe(), a SIBLING function returning units, so the claim no longer says "a deck
     from the DAG is unbuilt" — it says the render graph's deliverable is the TRANSFORM's.  The
     falsifier still bites: make a slide format a render target and the two collapse into one
     surface, at which point a .odp off the graph could be either and nothing would say which.

    python3 checks/deck_bound.py    # assert the bound holds
"""
from __future__ import annotations


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph

# The slide objects the coalgebra declares (Ρ·deck·node).  Derived from the graph, not restated:
# a slide object is one that no PDF route passes through and that a SLIDE_ROUTE terminates at.
SLIDE_OBJECTS = tuple(sorted({path[-1] for path in graph.SLIDE_ROUTES.values()} |
                             {o for path in graph.SLIDE_ROUTES.values() for o in path[1:]}))


def _projector_targets() -> set[str]:
    """The render TARGETS the projector affords — the observation functors it actually has.

    Read from the OWNER, not restated and not source-grepped: `project.TARGET` is a config.Param
    whose `choices` enumerate the target set (Ω·config — the knob is declared as data in the module
    that resolves it, and gate/discriminate reference this same Param).  Importing it means a new
    target CANNOT be added without this check seeing it; a grep over dispatch sites would miss the
    default (`pandoc` never appears in a `target == …` comparison).
    """
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "paperkit"))
    import project  # the owner of the target knob
    return set(project.TARGET.choices or ())


def main() -> int:
    # ── 1. the POSITIVE half: the slide formats really are first-class in the coalgebra ──
    if not SLIDE_OBJECTS:
        print("deck_bound: the coalgebra declares no slide objects — the claim's first clause "
              "('paperkit emits a gated .pptx and .odp') has no referent", file=sys.stderr)
        return 1
    for obj in ("pptx", "odp"):
        if obj not in graph.OBJECTS:
            print(f"deck_bound: {obj!r} is not a declared format object", file=sys.stderr)
            return 1
    for name, path in graph.SLIDE_ROUTES.items():
        for a, b in zip(path, path[1:]):
            if (a, b) not in graph.MORPHISMS:
                print(f"deck_bound: slide route {name} uses undeclared edge {a}->{b}",
                      file=sys.stderr)
                return 1

    # ── 2. the FALSIFIER: the projector must not treat a slide format as an observation ──
    targets = _projector_targets()
    if not targets:
        print("deck_bound: read NO render targets out of project.py — the falsifier cannot see "
              "its subject, so a slide target could be added unnoticed (source-grep witness lost "
              "its grip; re-point it at the projector's dispatch)", file=sys.stderr)
        return 1
    leaked = sorted(set(SLIDE_OBJECTS) & targets)
    if leaked:
        print(f"deck_bound: project.py now dispatches on slide target(s) {leaked} — a slide format "
              "has become a projector OBSERVATION.  The DECK BOUND no longer holds: either this is "
              "Ρ·deck·observe landing (rewrite the claim and this check), or a transform has been "
              "mislabelled as an observation.", file=sys.stderr)
        return 1

    print(f"deck_bound: slide objects {list(SLIDE_OBJECTS)} are first-class in the coalgebra "
          f"({len(graph.SLIDE_ROUTES)} composing routes); project.py's {len(targets)} render "
          f"targets {sorted(targets)} include none of them — transforms, not observations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
