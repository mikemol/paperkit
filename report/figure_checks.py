#!/usr/bin/env python3
"""Per-property witnesses for the adequacy figure — the `fig:` check type
(report/paper.toml: [checks.fig] cmd = "python3 figure_checks.py {target}").

Feature bullet-points and unit tests are the same thing viewed twice: claims.  So
the figure's data/accessibility guarantees are themselves gated claims, asserted
against the generated assets/dag.svg.  Run: figure_checks.py <property>.
"""
import re
import sys
import xml.dom.minidom as minidom
from pathlib import Path

HERE = Path(__file__).resolve().parent
SVG = (HERE / "assets" / "dag.svg").read_text()

OKABE_ITO = {"#E69F00", "#56B4E9", "#009E73", "#F0E442",
             "#0072B2", "#D55E00", "#CC79A7", "#000000"}
INK = "#1a1a1a"
NEUTRALS = {"white", "#ffffff", "#eeeeee", "#cccccc", "#999999", "none"}   # bg/gridlines/rings


def _fills():
    return re.findall(r'fill="([^"]+)"', SVG)


def okabe_ito():
    # every graphic colour is from the Okabe-Ito colour-blind-safe palette
    bad = sorted(set(_fills()) - (OKABE_ITO | {INK} | NEUTRALS))
    assert not bad, f"non-palette fills present: {bad}"
    assert OKABE_ITO & set(_fills()), "no Okabe-Ito colour is actually used"


def dark_on_light():
    # all text is the dark ink; the canvas is white
    text_fills = re.findall(r"<text[^>]*fill=\"([^\"]+)\"", SVG)
    off = sorted(set(text_fills) - {INK})
    assert text_fills and not off, f"text is not dark-on-light: {off}"
    assert re.search(r"<rect[^>]*fill=\"white\"", SVG), "the canvas is not white"


def well_formed():
    # well-formed vector SVG with real primitives
    doc = minidom.parseString(SVG)
    assert doc.documentElement.tagName == "svg", "root element is not <svg>"
    assert "<circle" in SVG or "<line" in SVG, "no vector primitives drawn"


def shows_clamp():
    # the figure encodes clamping: nodes sit at their EFFECTIVE grade, with the clamp
    # legend present.  Drop-lines appear only where a node is actually clamped — which
    # is legitimately zero once every claim is fully grounded, so the legend (not a
    # live drop-line) is the invariant.
    assert "self (if clamped)" in SVG, "the figure has no clamp legend"


def shows_terminal():
    # terminal theses (nothing rests on them) are ringed, with a legend entry
    assert "terminal (nothing rests on it)" in SVG, "no terminal legend in the figure"
    assert 'r="7.5"' in SVG, "no terminal rings drawn (every claim has a dependent?)"


def shows_layout():
    # Ρ·report·fig·layout — rpt-dag-fig's own witness: foundational atoms on the LEFT, the theses
    # they ground on the RIGHT, the effective grade on the VERTICAL axis.
    #
    # ⚑ It used to share `fresh:dag.svg` with rpt-fig-data, whose claim is the different one that
    # the figure is RENDERED FROM PIPELINE DATA, never placed by hand.  Freshness witnesses that
    # the committed file matches its generator; it says nothing about what the generator LAID OUT,
    # so a generator that plotted every node at one coordinate would still be fresh.  Two claims,
    # one witness, neither discriminating — the collapse --without-K exists to name.
    #
    # The axes are read from the rendered figure rather than from figure.py, so this fails if the
    # renderer stops encoding depth horizontally or grade vertically.
    circles = re.findall(r"<circle[^>]*\bcx=\"([\d.]+)\"[^>]*\bcy=\"([\d.]+)\"", SVG)
    assert len(circles) > 1, f"the figure plots {len(circles)} node(s) — nothing to lay out"
    xs = {float(x) for x, _ in circles}
    ys = {float(y) for _, y in circles}
    assert len(xs) > 1, ("every node shares one x — grounding depth is not on the horizontal "
                         "axis, so there is no atoms-left-to-theses-right walk")
    assert len(ys) > 1, ("every node shares one y — the effective grade is not on the vertical "
                         "axis")
    # the axis is LABELLED as a grade axis, so "vertical position" is not merely incidental spread
    assert re.search(r"<text[^>]*>\s*(behavioral|existence|imported|vacuous|indeterminate)\s*<",
                     SVG), "no grade rung is labelled on the figure's vertical axis"


CHECKS = {"okabe-ito": okabe_ito, "dark-on-light": dark_on_light, "well-formed": well_formed,
          "shows-clamp": shows_clamp, "shows-terminal": shows_terminal,
          "shows-layout": shows_layout}


def main(argv):
    if len(argv) != 2 or argv[1] not in CHECKS:
        print(f"usage: figure_checks.py <{'|'.join(CHECKS)}>", file=sys.stderr)
        return 2
    try:
        CHECKS[argv[1]]()
    except AssertionError as e:
        print(f"fig {argv[1]}: FAIL — {e}", file=sys.stderr)
        return 1
    print(f"fig {argv[1]}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
