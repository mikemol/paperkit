#!/usr/bin/env python3
r"""Ρ·render·matrix — the render capabilities × formats matrix: which format AFFORDS which
capability, demonstrated by which warrant, as one owned grid.

The render coalgebra (graph.py) tracks format OBJECTS × conversion MORPHISMS.  This is the SECOND
matrix over the same objects: format × CAPABILITY — an a11y or fidelity property a render target can
carry (native math, link alt-text, PDF/UA conformance, per-row accessible table rules, …).  Today
each capability lives as a lone render warrant with no owner declaring "capability C on format F is
afforded and demonstrated"; here that becomes DATA, the same one-owner move graph.py made for the
conversion edges — so a capability's reach across formats is stated in ONE place and a new capability
or format is a matrix entry, not scattered prose.

A CELL's state (the vocabulary reconciled with mat230's wcag-audit-table AUTO/FIX/EXT/NA scope map):
  "native"    — the format carries the capability BY CONSTRUCTION (mat230 AUTO): the latex route tags
                for PDF/UA-2 natively; docx transports OMML natively.
  "post"      — reached AFTER a post-processing pass (mat230 FIX): the office route reaches PDF/UA-1
                only after link/math/table repair (this is exactly graph.MORPHISMS[edge]["a11y"]).
  "excepted"  — the format's TOOLCHAIN CANNOT express it (a typed, named exception, never a silent
                gap): a markdown/office table cannot carry per-row rules, so ruler-sequence rules are
                excepted on the docx route — the deliverable SAYS it is excepted, it does not drop
                the cue silently.
  "n/a"       — the capability does not apply to that format.
  None        — no cell (the pair is simply not in the matrix).

The matrix COMPOSES with graph.py: the "pdf-ua" capability's row IS graph.MORPHISMS[edge]["a11y"]
across the pdf-producing edges (post on the office edges, native on the latex edge), so matrix.py
subsumes and generalizes that proto-column.  Composed with the conversion axis it gives the full
capabilities × formats × conversions cube — "does capability C survive edge e" — but the owned datum
here is the capabilities × formats face; the cube is read by composing this with graph.ROUTES.

    python3 checks/matrix.py            # print the capability × format grid
    python3 checks/matrix.py --check    # assert every afforded/post/native cell has its demonstrating
                                        #   warrant, and the pdf-ua row agrees with graph.MORPHISMS
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph

# The render FORMATS the matrix is stated over — the terminal-or-intermediate objects a consumer
# receives (a subset/renaming of graph.OBJECTS: the office route delivers docx/odt/pdf, the latex
# route delivers latex/pdf; "pdf-office" and "pdf-latex" distinguish the two PDF deliverables since
# a capability can differ between them — UA-1 vs UA-2).
FORMATS = ("docx", "odt", "latex", "pdf-office", "pdf-latex")

# The CAPABILITIES — each an a11y or fidelity property, keyed to the warrant(s) that demonstrate it.
# CAPABILITIES[cap] = {"what": one phrase, "wcag": clause or "", "cells": {format: (state, warrant)}}.
# A capability names its demonstrating warrant per cell; matrix --check asserts the warrant exists.
CAPABILITIES = {
    "coalgebra": {
        "what": "the render pipeline is an explicit owned coalgebra (formats × conversions as data)",
        "wcag": "",
        "cells": {f: ("native", "rnd-graph") for f in ("docx", "odt", "latex", "pdf-office", "pdf-latex")},
    },
    "presentation-agreement": {
        "what": "the rendered document presents byte-for-byte the verified paper's prose",
        "wcag": "",
        "cells": {"docx": ("native", "rnd-agree")},
    },
    "structural-headings": {
        "what": "every section renders as a real document heading whose text matches",
        "wcag": "1.3.1",
        "cells": {"docx": ("native", "rnd-wf")},
    },
    "glyph-fidelity": {
        "what": "every non-ASCII glyph survives to the PDF text layer, no missing-glyph tofu",
        "wcag": "",
        "cells": {"pdf-office": ("post", "rnd-fidelity"), "pdf-latex": ("native", "rnd-a11y-latex")},
    },
    "native-math": {
        "what": "equations transport as native editable math, never rasterized",
        "wcag": "",
        "cells": {"docx": ("native", "rnd-omml"), "pdf-latex": ("native", "rnd-a11y-latex")},
    },
    "measured-column-width": {
        "what": "a wide equation in a table cell is sized to measured ink, clip named not silent",
        "wcag": "",
        "cells": {"docx": ("post", "rnd-widen"),
                  "pdf-latex": ("n/a", "")},   # the latex route wraps natively — no measured widen needed
    },
    "ocr-recoverable": {
        "what": "OCR recovers the paper's text from the rasterized PDF pixels (visual layer)",
        "wcag": "",
        "cells": {"pdf-office": ("post", "rnd-ocr")},
    },
    "font-embedding": {
        "what": "every font is embedded, drawing identically where the font is absent",
        "wcag": "",
        "cells": {"pdf-office": ("post", "rnd-fonts"),
                  "pdf-latex": ("native", "rnd-a11y-latex")},  # a UA-2 zero-fail forbids .notdef, subsumes it
    },
    "citations-resolve": {
        "what": "internal warrants inline as markers, external sources render author-date, no bare marker",
        "wcag": "",
        "cells": {f: ("native", "rnd-bib") for f in ("docx", "odt", "latex")},
    },
    "vector-figures": {
        "what": "a generated figure embeds as a native vector, never rasterized, crisp at any zoom",
        "wcag": "1.4.10",
        "cells": {"docx": ("post", "rnd-fig-vector")},
    },
    "legible-figure-text": {
        "what": "a figure's legend survives into the PDF text layer, selectable and screen-readable",
        "wcag": "1.4.5",
        "cells": {"pdf-office": ("post", "rnd-fig-legible")},
    },
    "link-alt": {
        "what": "every link annotation carries a text description",
        "wcag": "7.18",
        "cells": {"pdf-office": ("post", "rnd-link-alt")},
    },
    "math-alt": {
        "what": "every equation carries a text alternative a screen reader announces",
        "wcag": "7.7",
        "cells": {"pdf-office": ("post", "rnd-math-alt"),
                  "pdf-latex": ("native", "rnd-a11y-latex")},  # /AF associated MathML, recoverable structure
    },
    "pdf-ua": {
        "what": "the deliverable is PDF/UA conformant by construction (veraPDF zero fails)",
        "wcag": "PDF/UA",
        # THIS ROW is graph.MORPHISMS[edge]["a11y"]: office edges reach UA-1 post-processing, the
        # latex edge tags natively for UA-2.  --check asserts this against the graph.
        "cells": {"pdf-office": ("post", "rnd-a11y"), "pdf-latex": ("native", "rnd-a11y-latex")},
    },
    "tagged-uno-export": {
        "what": "exported as tagged PDF/UA over the UNO bridge, refreshing indexes, bounded and loud",
        "wcag": "",
        "cells": {"pdf-office": ("post", "rnd-index")},
    },
    "ruler-sequence-rules": {
        "what": "a table's binary row-structure is carried in the rule PATTERN, a non-colour cue (producing side)",
        "wcag": "1.4.1",
        # The 1.4.1 PRODUCING side: LaTeX affords per-row rules (nicematrix), the office route's
        # toolchain CANNOT (a docx/markdown table has no per-row rule mechanism) — a TYPED exception,
        # not a silent gap.
        "cells": {"pdf-latex": ("native", "rnd-ruler"),
                  "docx": ("excepted", "rnd-ruler"),
                  "odt": ("excepted", "rnd-ruler")},
    },
    "use-of-colour": {
        "what": "no table row relies on colour as its sole cue — a meaning colour carries a weight cue too (verifying side)",
        "wcag": "1.4.1",
        # The 1.4.1 VERIFYING side (pairs with ruler-sequence): a LaTeX-source auditor.
        "cells": {"pdf-latex": ("native", "rnd-colour")},
    },
    "route-selector": {
        "what": "which route a consumer builds is one Ω·config selector, refusing an unknown value",
        "wcag": "",
        "cells": {f: ("native", "rnd-format") for f in FORMATS},
    },
}


def _warrant_keys(warrants_bib: Path) -> set:
    """The @misc keys declared in warrants.bib — the demonstrations a cell may name."""
    return set(re.findall(r"@\w+\{\s*([^,\s]+)\s*,", warrants_bib.read_text()))


def _grid() -> str:
    cw = max(len(f) for f in FORMATS) + 1
    kw = max(len(c) for c in CAPABILITIES) + 1
    head = " " * kw + "".join(f"{f:<{cw}}" for f in FORMATS)
    rows = [head]
    for cap, spec in CAPABILITIES.items():
        cells = "".join(((spec["cells"].get(f, (None,))[0] or "·")[:cw - 1]).ljust(cw) for f in FORMATS)
        rows.append(f"{cap:<{kw}}{cells}")
    return "\n".join(rows)


def check(warrants_bib: Path) -> tuple[bool, list[str]]:
    """Every afforded/post/native/excepted cell names a warrant that EXISTS in warrants.bib, and the
    pdf-ua row AGREES with graph.MORPHISMS (the matrix cannot claim a demonstration it does not have,
    nor a PDF/UA affordance the graph contradicts)."""
    keys = _warrant_keys(warrants_bib)
    problems = []
    for cap, spec in CAPABILITIES.items():
        for fmt, (state, warrant) in spec["cells"].items():
            if state in (None, "n/a"):
                continue
            if not warrant:
                problems.append(f"{cap} × {fmt}: state {state!r} but no demonstrating warrant named")
            elif warrant not in keys:
                problems.append(f"{cap} × {fmt}: names warrant {warrant!r} absent from warrants.bib")
    # the pdf-ua row is graph.MORPHISMS[edge].a11y — office pdf edges are "post", the latex edge "native"
    ua = CAPABILITIES["pdf-ua"]["cells"]
    if ua["pdf-office"][0] != graph.MORPHISMS[("docx", "pdf")]["a11y"]:
        problems.append("pdf-ua × pdf-office disagrees with graph.MORPHISMS[(docx,pdf)].a11y")
    if ua["pdf-latex"][0] != graph.MORPHISMS[("latex", "pdf")]["a11y"]:
        problems.append("pdf-ua × pdf-latex disagrees with graph.MORPHISMS[(latex,pdf)].a11y")
    return (not problems), problems


def main(argv: list[str]) -> int:
    bib = Path(__file__).resolve().parent.parent / "warrants.bib"
    if "--check" in argv:
        ok, problems = check(bib)
        if not ok:
            for p in problems:
                print(f"matrix --check: {p}", file=sys.stderr)
            return 1
        n_cells = sum(1 for s in CAPABILITIES.values()
                      for st, _ in s["cells"].values() if st not in (None, "n/a"))
        print(f"matrix --check: {len(CAPABILITIES)} capabilities × {len(FORMATS)} formats, "
              f"{n_cells} demonstrated cells — every cell has its warrant and the pdf-ua row "
              f"agrees with the render graph")
        return 0
    print("render capability × format matrix (row = capability, col = format):\n")
    print(_grid())
    print("\ncell states: native (by construction) · post (after post-processing) · "
          "excepted (toolchain cannot) · · (no cell)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
