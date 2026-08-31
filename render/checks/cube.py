#!/usr/bin/env python3
r"""Ρ·render·cube — the capabilities × formats × conversions cube: a conversion edge is a MORPHISM
ON THE CAPABILITY SPACE (edge*: Capabilities → Capabilities), DERIVED from the two owned faces plus
the genuine TWISTS the endpoints cannot express.

The render coalgebra has two owned faces over the same format objects: the CONVERSION face (graph.py
— which tool takes format A to format B) and the CAPABILITY face (matrix.py — which format affords
which a11y/fidelity capability).  The third axis is the action of a conversion edge on a capability:
as the paper flows along src→dst, what does capability C BECOME?  This is not a yes/no survival
predicate — a conversion can TWIST one capability into another (editable OMML native-math becomes a
tagged /Formula with /Alt = math-alt across the office pdf edge: a different capability, faithful to
the eye and to Word but no longer editable), a categorical twisted morphism.  So the cell records the
IMAGE capability edge*(C), not a survival state — that is the extra information a bare predicate
discards.

edge*(C) for capability C and edge src→dst, read off the two faces + the TWISTS relation:
  C                — PRESERVED: C afforded on both src and dst, the edge fixes it (edge*(C)=C).
  C  (from ∅)      — ESTABLISHED: C afforded on dst not src, the edge creates it (the office pdf edge
                     establishes PDF/UA by post-processing = graph a11y="post"; latex natively="native").
  C' (≠ C)         — TWISTED: the edge maps C to a DIFFERENT capability C' the dst affords instead
                     (native-math ↦ math-alt), declared in TWISTS where the endpoints cannot derive it.
  None             — LOST: C afforded on src, and neither preserved nor twisted — dst cannot carry it.
  (no cell)        — ABSENT: C on neither endpoint.

Along a ROUTE the edge maps COMPOSE: the capabilities the source affords flow through each edge*'s
action, so "what does route R deliver" is the composite edge* applied to the source capabilities —
a capability can arrive at the final format under a DIFFERENT name than it started (native-math
arrives as math-alt on the office route).  --check ties the derivation back to the graph: every
established/preserved pdf-ua edge matches graph's a11y field, and every capability afforded or
arriving-by-twist at a route's final format is delivered (no silent loss).

    python3 checks/cube.py            # the capability × edge action face + per-route delivery
    python3 checks/cube.py --check    # assert the derivation agrees with the graph's a11y field
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph
import matrix

# The genuine TWISTS: an edge maps capability C to a DIFFERENT capability C' that the destination
# affords instead — the categorical twist the endpoint affordances alone cannot express.  Keyed
# (capability, src, dst) → image capability.  Declared, because a twist is real content (which
# capability an edge transforms into), not derivable from "afforded on both ends".
TWISTS = {
    # the office pdf export TWISTS editable native math into a tagged /Formula with alt text: the
    # equation survives faithfully (eye, Word) but as math-alt, not editable OMML.
    ("native-math", "docx", "pdf"): "math-alt",
    ("native-math", "odt", "pdf"): "math-alt",
}


# The matrix states capabilities over delivery FORMATS (docx, odt, latex, pdf-office, pdf-latex); the
# graph states edges over format OBJECTS (…, pdf).  The pdf object is reached by two edges that
# deliver different PDF formats — docx/odt→pdf is pdf-office, latex→pdf is pdf-latex — so an edge into
# `pdf` maps to the matrix's pdf-office / pdf-latex by its source.
def _dst_format(src: str, dst: str) -> str:
    if dst == "pdf":
        return "pdf-latex" if src == "latex" else "pdf-office"
    return dst


def _affords(cap: str, fmt: str) -> bool:
    """Does format `fmt` afford capability `cap` (native or post)?  Read off the matrix face."""
    st = matrix.CAPABILITIES[cap]["cells"].get(fmt, (None,))[0]
    return st in ("native", "post")


# the four kinds of edge action, as sentinels distinct from any capability name (which are the
# TWISTED/PRESERVED/ESTABLISHED image values).
LOST = None            # C afforded on src, dst carries neither C nor a twist of it
ABSENT = "∅"           # C on neither endpoint — the edge is irrelevant to C


def edge_action(cap: str, src: str, dst: str) -> str | None:
    """edge*(cap) across src→dst: the IMAGE capability (what cap BECOMES), or LOST/ABSENT.  DERIVED
    from the endpoint affordances, with the genuine TWISTS declared.  `md` (the source object)
    affords nothing terminal, so an md→X edge ESTABLISHES cap (image = cap) iff X affords it.
    """
    dstf = _dst_format(src, dst)
    on_dst = _affords(cap, dstf)
    on_src = _affords(cap, src) if src != "md" else False
    twist = TWISTS.get((cap, src, dst))
    if twist is not None:
        return twist                       # the edge maps cap to a different capability
    if on_dst:                             # preserved (also on src) or established (dst only) — image is cap
        return cap
    if on_src:
        return LOST                        # afforded on src, dst cannot carry it, no twist
    return ABSENT


def kind(cap: str, src: str, dst: str) -> str:
    """A label for the edge action (for display / --check), read off edge_action + the endpoints."""
    img = edge_action(cap, src, dst)
    if img is LOST:
        return "lost"
    if img == ABSENT:
        return "absent"
    if img != cap:
        return "twisted"                   # image is a different capability
    on_src = _affords(cap, src) if src != "md" else False
    return "preserved" if on_src else "established"


def route_delivers(cap: str, route: str) -> str | None:
    """What `route` delivers `cap` AS at its final format (the composite edge* action) — the image
    capability name, or None if a losing edge drops it on the way.  A capability may arrive under a
    DIFFERENT name than it started (native-math arrives as math-alt on the office route).
    """
    path = graph.ROUTES[route]
    current = cap
    for a, b in zip(path, path[1:]):
        img = edge_action(current, a, b)
        if img is LOST:
            return None
        if img != ABSENT:
            current = img                  # follow the twist: the capability continues under its image name
    final = _dst_format(path[-2], path[-1])
    return current if _affords(current, final) else None


def _edges():
    return list(graph.MORPHISMS)


def check() -> tuple[bool, list[str]]:
    """The derivation is consistent with the two owned faces: every pdf-ua edge that graph marks
    a11y∈{post,native} must ESTABLISH or PRESERVE pdf-ua; every declared TWIST's image capability must
    be afforded at the edge's destination (an edge cannot twist into a capability the dst does not
    carry); and every capability afforded at a route's final format is delivered there (possibly under
    a twisted name), no silent loss.  This ties the third face back so it cannot drift.
    """
    problems = []
    for (s, d), m in graph.MORPHISMS.items():
        if m["a11y"] in ("post", "native") and kind("pdf-ua", s, d) not in ("established", "preserved"):
            problems.append(f"pdf-ua {s}->{d}: graph a11y={m['a11y']} but cube derives {kind('pdf-ua', s, d)!r}")
        if m["a11y"] is None and d == "pdf":
            problems.append(f"{s}->pdf has a11y=None yet produces a PDF — graph inconsistency")
    # a twist's image must be afforded at the destination (the edge maps INTO a capability dst carries).
    for (cap, s, d), image in TWISTS.items():
        if not _affords(image, _dst_format(s, d)):
            problems.append(f"twist {cap} {s}->{d} → {image!r}: {image} not afforded at {_dst_format(s, d)}")
    # every capability afforded at a route's final format is delivered (as itself or a twist image).
    for cap in matrix.CAPABILITIES:
        for route, path in graph.ROUTES.items():
            final = _dst_format(path[-2], path[-1])
            if _affords(cap, final) and route_delivers(cap, route) is None:
                problems.append(f"{cap} afforded at {final} but route {route} does not deliver it")
    return (not problems), problems


def _face() -> str:
    """The capability × edge ACTION face (rows = capabilities, cols = edges): each cell is the image
    capability edge*(cap) — `=` if preserved/established as itself, the image NAME if twisted, LOST or ·.
    """
    edges = _edges()
    labels = [f"{s}>{d}" for s, d in edges]
    cw = max(max(len(x) for x in labels), 9) + 1
    kw = max(len(c) for c in matrix.CAPABILITIES) + 1
    head = " " * kw + "".join(f"{x:<{cw}}" for x in labels)
    rows = [head]
    for cap in matrix.CAPABILITIES:
        cells = []
        for s, d in edges:
            k = kind(cap, s, d)
            cell = {"preserved": "=", "established": "＋", "lost": "LOST", "absent": "·"}.get(k)
            if k == "twisted":
                cell = "→" + edge_action(cap, s, d)     # the image capability name
            cells.append(cell.ljust(cw))
        rows.append(f"{cap:<{kw}}" + "".join(cells))
    return "\n".join(rows)


def main(argv: list[str]) -> int:
    if "--check" in argv:
        ok, problems = check()
        if not ok:
            for p in problems:
                print(f"cube --check: {p}", file=sys.stderr)
            return 1
        n_twist = sum(1 for c in matrix.CAPABILITIES for s, d in _edges() if kind(c, s, d) == "twisted")
        n_lost = sum(1 for c in matrix.CAPABILITIES for s, d in _edges() if kind(c, s, d) == "lost")
        print(f"cube --check: {len(matrix.CAPABILITIES)} capabilities × {len(_edges())} edges — "
              f"{len(TWISTS)} declared twists, {n_twist} twisted cells, {n_lost} lost; every twist's "
              f"image is afforded at its destination, the pdf-ua edges agree with the graph, and every "
              f"afforded capability is delivered by its route (possibly under a twisted name)")
        return 0
    print("capability × conversion-edge ACTION (edge* : each cell is what the capability BECOMES):\n")
    print(_face())
    print("\ncells: = (preserved) · ＋ (the edge establishes it) · →X (TWISTED into capability X) · "
          "LOST (dst cannot carry it) · · (absent)\n")
    print("per-route delivery (the capability, under the name it ARRIVES as — a twist may rename it):")
    for route in graph.ROUTES:
        delivered = [(c, route_delivers(c, route)) for c in matrix.CAPABILITIES
                     if route_delivers(c, route) is not None]
        shown = [f"{c}→{img}" if img != c else c for c, img in delivered]
        print(f"  {route:<6} delivers {len(delivered)}: {', '.join(shown)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
