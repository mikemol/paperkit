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
NEUTRALS = {"white", "#ffffff", "#eeeeee", "#cccccc"}   # background + gridlines/edges


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


CHECKS = {"okabe-ito": okabe_ito, "dark-on-light": dark_on_light, "well-formed": well_formed}


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
