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
OBJECTS = ("md", "docx", "odt", "latex", "pdf")

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
}

# The composed ROUTES from the source to the terminal PDF (each is a list of intermediate objects the
# md passes through).  The router (pdf.py) selects one by its intermediate; the a11y of the route is
# the a11y of its pdf-producing edge.
ROUTES = {
    "docx":  ["md", "docx", "pdf"],
    "odf":   ["md", "odt", "pdf"],
    "latex": ["md", "latex", "pdf"],
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
        for name, path in ROUTES.items():
            for a, b in zip(path, path[1:]):
                if (a, b) not in MORPHISMS:
                    print(f"graph --check: route {name} uses undeclared edge {a}->{b}", file=sys.stderr)
                    return 1
        print(f"graph --check: {len(MORPHISMS)} morphisms over {len(OBJECTS)} objects, "
              f"{len(ROUTES)} routes — every edge's tool is present and every route composes")
        return 0
    print("render coalgebra — conversion morphisms (row = from, col = to):\n")
    print(_matrix())
    print("\nroutes to the terminal PDF:")
    for name, path in ROUTES.items():
        print(f"  {name:<6} {' → '.join(path)}   (a11y: {route_a11y(name)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
