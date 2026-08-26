#!/usr/bin/env python3
r"""Ρ·render·graph — the render coalgebra: format OBJECTS and conversion MORPHISMS, as data.

The render pipeline is a coalgebra — objects are FORMAT nodes, morphisms are CONVERSION edges — and
it is MANY-TO-MANY: pandoc takes markdown to several formats, and a PDF is reached from several
(a docx or an odt through LibreOffice, a LaTeX source through lualatex).  So the graph is tracked
HERE as an explicit adjacency matrix rather than scattered across per-check imports: the format-node
producers and the pdf router DERIVE their edges from this, so the graph has one owner and a new node
or edge (a beamer slide target, a reveal.js one — the slide-deck prototype composes onto exactly this
matrix) is added in one place.

MORPHISMS[(src, dst)] = a conversion, named by the TOOL that performs it.  The absence of a key is the
absence of a direct edge (a route composes edges: md → docx → pdf is two morphisms).  Each morphism
carries only what the graph needs to reason: the tool, and whether the edge is a11y-native (the
LaTeX→pdf edge tags for PDF/UA by construction) or needs post-processing (the office edges reach
PDF/UA only after link/math/table repair).

Objects a node produces are terminal-capable: a consumer may want the .docx or the .odt itself, or
route on through to a .pdf.  ROUTES enumerates the composed paths to the terminal PDF.

    python3 checks/graph.py            # print the morphism matrix (the graph, as a table)
    python3 checks/graph.py --check    # assert the declared edges match the tools actually present
"""
from __future__ import annotations

import shutil
import subprocess
import sys

# The format OBJECTS (nodes).  `md` is the source; the rest are producible, terminal-capable formats.
# pptx/odp are the SLIDE objects (Ρ·deck·node) — see the DECK BOUND note below.
# `units` is the OBSERVATION object (Ρ·deck·route): project.observe()'s segmentation of the
# claim-DAG, a SIBLING source to `md` (project()'s linearization), not downstream of it.
OBJECTS = ("md", "units", "docx", "odt", "latex", "pdf", "pptx", "odp")

# The conversion MORPHISMS (edges): (src, dst) -> {tool, a11y}.  a11y: "native" (the edge tags for
# PDF/UA by construction), "post" (reaches PDF/UA only after post-processing), or None (not a
# pdf-producing edge, so a11y does not apply).  MANY-TO-MANY: md fans out; pdf fans in.
MORPHISMS = {
    ("md", "docx"):  {"tool": "pandoc",   "a11y": None},
    ("md", "odt"):   {"tool": "pandoc",   "a11y": None},
    ("md", "latex"): {"tool": "pandoc",   "a11y": None},
    ("docx", "pdf"): {"tool": "soffice",  "a11y": "post"},    # + linkalt/mathalt/widen → PDF/UA-1
    ("odt", "pdf"):  {"tool": "soffice",  "a11y": "post"},    # + linkalt/mathalt/widen → PDF/UA-1
    ("latex", "pdf"): {"tool": "lualatex", "a11y": "native"},  # \DocumentMetadata tagging → PDF/UA-2
    ("docx", "odt"): {"tool": "soffice",  "a11y": None},      # the office hub converts between them
    ("odt", "docx"): {"tool": "soffice",  "a11y": None},
    # The SLIDE objects (Ρ·deck·node).  pandoc emits pptx from markdown; the office hub converts
    # pptx↔odp exactly as it does docx↔odt.  See DECK BOUND: these are TRANSFORM edges of the
    # pandoc observation, not a new observation of the claim-DAG.
    ("md", "pptx"):  {"tool": "pandoc",   "a11y": None},
    # Ρ·deck·route — the UNIT-carrying edge.  Its source is `units` (the observation), not `md`
    # (the linearization), which is what makes the route's deliverable a PROJECTION of the DAG
    # rather than a reflow of finished prose.  Same tool; different source object, and the object
    # is the whole difference.
    ("units", "pptx"): {"tool": "pandoc",   "a11y": None},
    ("pptx", "odp"): {"tool": "soffice",  "a11y": None},
    ("odp", "pptx"): {"tool": "soffice",  "a11y": None},
}

# ── DECK BOUND (Ρ·deck·node) ──────────────────────────────────────────────────────────────────
# The slide nodes above make the slide FORMATS first-class and tool-gated.  They do NOT make a deck
# a paperkit PROJECTION.  Every edge here is a downstream TRANSFORM of the pandoc observation of an
# ALREADY-LINEARIZED document: project() is S -> String (one flat stream seeded by rubric-order ×
# dep-order), and these edges reflow that stream onto slides.
#
# A deck as a genuine OBSERVATION of the claim-DAG is S -> RoseTree(S) indexed by (target, genre) —
# a SEGMENTATION into bounded observation-windows, not a linearization.  That is Ρ·deck·observe, and
# it is NOT what this matrix delivers; prototypes/slides.bib holds its design DAG, whose
# `docx-pdf-are-transforms-not-observations` names exactly the trap of shipping an
# exporter-of-finished-prose and calling it a deck target.
#
# So: `.odp`/`.pptx` OUT of paperkit — yes, gated, from the resolved source.  A deck PROJECTED from
# the DAG — not yet.  Any warrant citing these nodes must carry that bound.
# ──────────────────────────────────────────────────────────────────────────────────────────────

# The composed ROUTES from the source to the terminal PDF (each is a list of intermediate objects the
# md passes through).  The router (pdf.py) selects one by its intermediate; the a11y of the route is
# the a11y of its pdf-producing edge.
ROUTES = {
    "docx":  ["md", "docx", "pdf"],
    "odf":   ["md", "odt", "pdf"],
    "latex": ["md", "latex", "pdf"],
}

# The composed routes to a terminal SLIDE deliverable (Ρ·deck·node).  Kept SEPARATE from ROUTES
# because ROUTES is the fan-in to the terminal PDF and route_a11y() reads its final edge's a11y
# field; a slide route terminates at a slide object, so folding it into ROUTES would make
# route_a11y raise on a None-a11y edge.  Same composition rule: consecutive pairs must be
# declared morphisms (deck --check asserts it, exactly as ROUTES does).
SLIDE_ROUTES = {
    "pptx": ["md", "pptx"],
    "odp":  ["md", "pptx", "odp"],
    # the OBSERVED routes (Ρ·deck·route): same terminal formats, sourced from the segmentation.
    # A consumer asking for a deck picks between them by which SOURCE it wants, and the graph
    # names the difference instead of leaving two things that look alike indistinguishable.
    "pptx-observed": ["units", "pptx"],
    "odp-observed":  ["units", "pptx", "odp"],
}


def tool_for(src: str, dst: str) -> str | None:
    m = MORPHISMS.get((src, dst))
    return m["tool"] if m else None


def route_a11y(route: str) -> str | None:
    """The a11y kind of a route = the a11y of its FINAL (pdf-producing) morphism."""
    path = ROUTES[route]
    return MORPHISMS[(path[-2], path[-1])]["a11y"]


def _matrix() -> str:
    w = max(len(o) for o in OBJECTS) + 1
    head = " " * w + "".join(f"{d:<{w}}" for d in OBJECTS)
    rows = [head]
    for s in OBJECTS:
        cells = "".join((tool_for(s, d) or "·")[:w - 1].ljust(w) for d in OBJECTS)
        rows.append(f"{s:<{w}}{cells}")
    return "\n".join(rows)


def main(argv: list[str]) -> int:
    if "--check" in argv:
        # every declared morphism's tool must actually be present (the graph cannot claim an edge
        # the toolchain cannot perform).  A missing tool is a graph that lies about its reach.
        missing = sorted({m["tool"] for m in MORPHISMS.values() if not shutil.which(m["tool"])})
        if missing:
            print(f"graph --check: declared morphism tool(s) absent: {missing} — the graph claims "
                  "an edge the toolchain cannot perform", file=sys.stderr)
            return 1
        # every route composes real edges (each consecutive pair is a declared morphism)
        for label, table in (("route", ROUTES), ("slide route", SLIDE_ROUTES)):
            for name, path in table.items():
                for a, b in zip(path, path[1:]):
                    if (a, b) not in MORPHISMS:
                        print(f"graph --check: {label} {name} uses undeclared edge {a}->{b}",
                              file=sys.stderr)
                        return 1
        # every declared object is REACHED by some morphism (an object no edge produces or consumes
        # is a node the graph claims but cannot deliver — the OBJECTS/MORPHISMS drift guard)
        touched = {o for pair in MORPHISMS for o in pair}
        orphans = sorted(set(OBJECTS) - touched)
        if orphans:
            print(f"graph --check: object(s) {orphans} appear in no morphism — the graph declares a "
                  "node it cannot reach", file=sys.stderr)
            return 1
        print(f"graph --check: {len(MORPHISMS)} morphisms over {len(OBJECTS)} objects, "
              f"{len(ROUTES)} pdf routes + {len(SLIDE_ROUTES)} slide routes — every edge's tool is "
              "present, every object is reachable, and every route composes")
        return 0
    print("render coalgebra — conversion morphisms (row = from, col = to):\n")
    print(_matrix())
    print("\nroutes to the terminal PDF:")
    for name, path in ROUTES.items():
        print(f"  {name:<6} {' → '.join(path)}   (a11y: {route_a11y(name)})")
    print("\nroutes to a terminal SLIDE deliverable (transforms, not observations — see DECK BOUND):")
    for name, path in SLIDE_ROUTES.items():
        print(f"  {name:<6} {' → '.join(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
