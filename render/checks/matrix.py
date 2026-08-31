r"""Ρ·render·matrix — which render format AFFORDS which capability, as one owned grid.

The render coalgebra (graph.py) tracks format OBJECTS × conversion MORPHISMS.  This is the
SECOND matrix over the same objects: format × CAPABILITY — an a11y or fidelity property a
render target can carry (native math, link alt-text, PDF/UA conformance, per-row accessible
table rules, …).  Today each capability lives as a lone render warrant with no owner declaring
"capability C on format F is afforded and demonstrated"; here that becomes DATA, the same
one-owner move graph.py made for the conversion edges — so a capability's reach across formats
is stated in ONE place and a new capability or format is a matrix entry, not scattered prose.

A CELL's state (vocabulary reconciled with mat230's wcag-audit-table AUTO/FIX/EXT/NA scope map):
  "native"    — the format carries the capability BY CONSTRUCTION (mat230 AUTO): the latex
                route tags for PDF/UA-2 natively; docx transports OMML natively.
  "post"      — reached AFTER a post-processing pass (mat230 FIX): the office route reaches
                PDF/UA-1 only after link/math/table repair (exactly
                graph.MORPHISMS[edge]["a11y"]).
  "excepted"  — the format's TOOLCHAIN CANNOT express it (a typed, named exception, never a
                silent gap): a markdown/office table cannot carry per-row rules, so
                ruler-sequence rules are excepted on the docx route — the deliverable SAYS it
                is excepted, it does not drop the cue silently.
  "n/a"       — the capability does not apply to that format.
  None        — no cell (the pair is simply not in the matrix).

The matrix COMPOSES with graph.py: the "pdf-ua" capability's row IS
graph.MORPHISMS[edge]["a11y"] across the pdf-producing edges (post on the office edges, native
on the latex edge), so matrix.py subsumes and generalizes that proto-column.  Composed with the
conversion axis it gives the full capabilities × formats × conversions cube — "does capability C
survive edge e" — but the owned datum here is the capabilities × formats face; the cube is read
by composing this with graph.ROUTES.

    python3 checks/matrix.py            # print the capability × format grid
    python3 checks/matrix.py --check    # assert every afforded/post/native cell has its
                                        #   demonstrating warrant, and the pdf-ua row agrees
                                        #   with graph.MORPHISMS
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict

# ⚑ Ζ·witness·sibling — THE SIBLING IS NAMED IN FULL; THE ROOT IS BOOTSTRAPPED, NOT SHADOWED.
# This module used `sys.path.insert(0, str(Path(__file__).resolve().parent))` plus a bare
# `import graph`.  That is the injection being retired ecosystem-wide, and the harm is specific:
# it puts THIS DIRECTORY first, so a sibling named like an engine module wins over the engine —
# the collision recorded one file over, where `render/checks/bib.py` shadowed `paperkit/bib.py`
# and reddened seven talk claims.
#
# ⚑⚑ THREE SPELLINGS WERE MEASURED AND ONLY THIS ONE HOLDS ON EVERY ROUTE:
#   `from . import graph`             ImportError on ROUTE 1 — the bib's check field runs
#                                     `python3 checks/matrix.py`, which has no parent package,
#                                     and this raises at MODULE level, before `__main__`.
#   `if TYPE_CHECKING: from render…`  ruff refuses it, correctly: `graph.OBJECTS` is read at
#                                     RUNTIME, so the block would be a lie that crashes.
#   root on path, then absolute       works on all three routes.
#
# ⚑⚑⚑ AND `render` IS NOT AN INSTALLED PACKAGE, WHICH I ASSERTED WRONGLY BEFORE MEASURING.  An
# earlier probe found `import paperkit` reachable from cwd=render/ and I generalised it to "a
# witness can import" — but `pyproject.toml` declares `packages = ["paperkit"]` ONLY.  `render`
# resolves by CWD from the repo root and nowhere else, so the sibling edge has no declaration to
# lean on and this insert is what supplies it.  Appending the ROOT is a different act from
# prepending THIS directory: it adds a namespace without shadowing one.  Declaring `render` as a
# package properly is Ζ·render·declare, and this line retires with it.
#
# ⚑ NAMING THE EDGE IS ALSO WHAT MADE THE TYPE DEBT VISIBLE — 12 untyped-dict findings in
# `graph.py`, then 21 of the SAME SHAPE here, all invisible while mypy could not follow a bare
# `import graph`.  The injection was HIDING that debt, not causing it.  Both paid by
# Ζ·graph·typed.
sys.path.append(str(Path(__file__).resolve().parents[2]))

from paperkit import bibfidelity
from render.checks import graph

# The render FORMATS the matrix is stated over — the terminal-or-intermediate objects a consumer
# receives (a subset/renaming of graph.OBJECTS: the office route delivers docx/odt/pdf, the latex
# route delivers latex/pdf; "pdf-office" and "pdf-latex" distinguish the two PDF deliverables
# since a capability can differ between them — UA-1 vs UA-2).
FORMATS = ("docx", "odt", "latex", "pdf-office", "pdf-latex", "pptx", "odp")

# Ρ·render·matrix·cover — the graph OBJECTS this grid deliberately does NOT state capabilities
# over, each with the reason.  Declared rather than left implicit: `FORMATS` was described in
# prose as "a subset of graph.OBJECTS" and nothing checked it, so adding pptx/odp to the
# coalgebra left them silently ungraded here — the grid kept passing because it only ever
# compared itself to itself.  An object must now be in FORMATS or in this map, so a new node
# cannot be quietly uncovered.
NOT_STATED = {
    "md":    "the SOURCE, not a deliverable — capabilities are properties of what a consumer "
             "receives",
    "units": "the OBSERVATION (project.observe's segmentation), a carrier of claims rather than a "
             "rendered format; its capabilities are those of whatever format it is rendered into",
    "pdf":   "split into pdf-office and pdf-latex, since a capability can differ between the two "
             "producers (UA-1 vs UA-2)",
}

class Capability(TypedDict):
    """One a11y-or-fidelity property: what it is, its WCAG clause, and its per-format cells.

    ⚑ Ζ·graph·typed, SECOND INSTANCE — THE SAME UNTYPED-LITERAL SHAPE, ONE FILE OVER.  The
    comment below already specified this exactly (`{"what": one phrase, "wcag": clause or "",
    "cells": {fmt: (state, warrant)}}`), and inference reduced it to `Collection[str]` because
    the values are heterogeneous — so `spec["cells"].items()` was an attribute error waiting on
    a type checker nobody had pointed here.  21 findings, one root cause, and the same remedy
    `graph.Morphism` just took: state the shape that was already written in prose.

    A `cell` is (state, warrant): state in native/post/excepted/n/a, warrant the key that
    DEMONSTRATES it — `--check` asserts that key exists in warrants.bib.
    """

    what: str
    wcag: str
    cells: dict[str, tuple[str | None, str]]


# The CAPABILITIES — each an a11y or fidelity property, keyed to the warrant(s) demonstrating it.
# CAPABILITIES[cap] = {"what": one phrase, "wcag": clause or "", "cells": {fmt: (state, warrant)}}.
# A capability names its demonstrating warrant per cell; matrix --check asserts the warrant exists.
CAPABILITIES: dict[str, Capability] = {
    "slide-alt-text": {
        "what": "a non-text element on a slide carries a text alternative",
        "wcag": "1.1.1",
        # MEASURED: the produced .odp contains ZERO svg:desc — pandoc's pptx writer emits no
        # alt-text and the office edge invents none.  EXCEPTED, not silently absent: the deck's
        # current content is text and lists, so nothing NEEDS an alternative today, but a figure
        # placed on a slide would ship without one and the grid says so.
        "cells": {"pptx": ("excepted", "rnd-slides"), "odp": ("excepted", "rnd-slides")},
    },
    "coalgebra": {
        "what": "the render pipeline is an explicit owned coalgebra (formats × conversions as "
                "data)",
        "wcag": "",
        "cells": dict.fromkeys(("docx", "odt", "latex", "pdf-office", "pdf-latex"),
                               ("native", "rnd-graph")),
    },
    "presentation-agreement": {
        "what": "the rendered document presents byte-for-byte the verified paper's prose",
        "wcag": "",
        # the prose survives into the PDF text layer (rnd-pdf gates that the content is present,
        # with no bare marker).
        "cells": {"docx": ("native", "rnd-agree"), "pdf-office": ("post", "rnd-pdf")},
    },
    "slide-structure": {
        "what": "each slide carries a real title placeholder and its content as list structure, "
                "so a screen reader announces the slide and walks its points",
        "wcag": "1.3.1",
        # MEASURED on the observed deck: 59 title placeholders, 50 outline placeholders, 286
        # lists.  `post` rather than `native`: pandoc's pptx writer places them and the office
        # edge carries them through — neither format guarantees it by construction.
        "cells": {"pptx": ("post", "rnd-slides"), "odp": ("post", "rnd-slides")},
    },
    "structural-headings": {
        "what": "every section renders as a real document heading whose text matches",
        "wcag": "1.3.1",
        # a docx heading becomes a tagged heading in the tagged PDF (rnd-fidelity checks the
        # headings are present).
        "cells": {"docx": ("native", "rnd-wf"), "pdf-office": ("post", "rnd-fidelity")},
    },
    "glyph-fidelity": {
        "what": "every non-ASCII glyph survives to the PDF text layer, no missing-glyph tofu",
        "wcag": "",
        "cells": {"pdf-office": ("post", "rnd-fidelity"),
                  "pdf-latex": ("native", "rnd-a11y-latex")},
    },
    "native-math": {
        "what": "equations transport as native editable math, never rasterized",
        "wcag": "",
        # docx affords EDITABLE OMML; the office pdf edge does NOT preserve editability — it
        # TWISTS native-math into math-alt (a tagged /Formula with /Alt).  So there is no
        # pdf-office cell here; the twist is recorded in TRANSFORMS below.  The latex PDF
        # carries math natively (MathML /AF).
        "cells": {"docx": ("native", "rnd-omml"),
                  "pdf-latex": ("native", "rnd-a11y-latex")},
    },
    "measured-column-width": {
        "what": "a wide equation in a table cell is sized to measured ink, clip named not silent",
        "wcag": "",
        # the latex route wraps natively — no measured widen needed
        "cells": {"docx": ("post", "rnd-widen"),
                  "pdf-latex": ("n/a", "")},
    },
    "ocr-recoverable": {
        "what": "OCR recovers the paper's text from the rasterized PDF pixels (visual layer)",
        "wcag": "",
        "cells": {"pdf-office": ("post", "rnd-ocr")},
    },
    "font-embedding": {
        "what": "every font is embedded, drawing identically where the font is absent",
        "wcag": "",
        # a UA-2 zero-fail forbids .notdef, subsuming this
        "cells": {"pdf-office": ("post", "rnd-fonts"),
                  "pdf-latex": ("native", "rnd-a11y-latex")},
    },
    "citations-resolve": {
        "what": "internal warrants inline as markers, external sources render author-date, no "
                "bare marker",
        "wcag": "",
        # citations resolve at the source formats AND survive into the delivered PDF (rnd-pdf
        # gates no bare marker in the PDF); the latex PDF carries them too.
        "cells": {**dict.fromkeys(("docx", "odt", "latex"), ("native", "rnd-bib")),
                  "pdf-office": ("post", "rnd-pdf"), "pdf-latex": ("native", "rnd-a11y-latex")},
    },
    "vector-figures": {
        "what": "a generated figure embeds as a native vector, never rasterized, crisp at any "
                "zoom",
        "wcag": "1.4.10",
        # the vector is carried through to the PDF without rasterizing (rnd-fig-vector gates
        # this end-to-end).
        "cells": {"docx": ("post", "rnd-fig-vector"), "pdf-office": ("post", "rnd-fig-vector")},
    },
    "legible-figure-text": {
        "what": "a figure's legend survives into the PDF text layer, selectable and "
                "screen-readable",
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
        # /AF associated MathML — recoverable structure
        "cells": {"pdf-office": ("post", "rnd-math-alt"),
                  "pdf-latex": ("native", "rnd-a11y-latex")},
    },
    "pdf-ua": {
        "what": "the deliverable is PDF/UA conformant by construction (veraPDF zero fails)",
        "wcag": "PDF/UA",
        # THIS ROW is graph.MORPHISMS[edge]["a11y"]: office edges reach UA-1 post-processing, the
        # latex edge tags natively for UA-2.  --check asserts this against the graph.
        "cells": {"pdf-office": ("post", "rnd-a11y"), "pdf-latex": ("native", "rnd-a11y-latex")},
    },
    "tagged-uno-export": {
        "what": "exported as tagged PDF/UA over the UNO bridge, refreshing indexes, bounded and "
                "loud",
        "wcag": "",
        "cells": {"pdf-office": ("post", "rnd-index")},
    },
    "ruler-sequence-rules": {
        "what": "a table's binary row-structure is carried in the rule PATTERN, a non-colour cue "
                "(producing side)",
        "wcag": "1.4.1",
        # The 1.4.1 PRODUCING side: LaTeX affords per-row rules (nicematrix), the office route's
        # toolchain CANNOT (a docx/markdown table has no per-row rule mechanism) — a TYPED
        # exception, not a silent gap.
        "cells": {"pdf-latex": ("native", "rnd-ruler"),
                  "docx": ("excepted", "rnd-ruler"),
                  "odt": ("excepted", "rnd-ruler")},
    },
    "use-of-colour": {
        "what": "no table row relies on colour as its sole cue — a meaning colour carries a "
                "weight cue too (verifying side)",
        "wcag": "1.4.1",
        # The 1.4.1 VERIFYING side (pairs with ruler-sequence): a LaTeX-source auditor.
        "cells": {"pdf-latex": ("native", "rnd-colour")},
    },
    "route-selector": {
        "what": "which route a consumer builds is one Ω·config selector, refusing an unknown value",
        "wcag": "",
        "cells": dict.fromkeys(FORMATS, ("native", "rnd-format")),
    },
}


def _warrant_keys(warrants_bib: Path) -> set[str]:
    r"""Collect the entry keys declared in warrants.bib — the demonstrations a cell may name.

    ⚑ Ζ·re·structural — READ BY THE ENGINE'S PARSER, NOT A LOCAL HEADER REGEX.  This site used
    `re.findall(r"@\w+\{\s*([^,\s]+)\s*,")`, the header half of a pattern copied seven times
    across this tree.  It happened to be RIGHT — a key never nests braces, so the depth-1 defect
    that cost `paper/model.bib` its `claim` field could not reach it — and that is exactly why
    it would have gone wrong QUIETLY if the format ever moved: a grammar that does not match
    simply yields fewer keys, and "fewer keys" is indistinguishable from "fewer warrants".

    ⚑⚑ AND A KEY THAT VANISHES HERE FAILS OPEN, THE DANGEROUS DIRECTION.  `--check` asserts
    every afforded cell NAMES a declared warrant, so a key the reader could not see reports a
    LIVE demonstration as missing — refusing a matrix that is in fact complete.
    """
    return set(bibfidelity.entries(warrants_bib.read_text()))


def _grid() -> str:
    cw = max(len(f) for f in FORMATS) + 1
    kw = max(len(c) for c in CAPABILITIES) + 1
    head = " " * kw + "".join(f"{f:<{cw}}" for f in FORMATS)
    rows = [head]
    for cap, spec in CAPABILITIES.items():
        cells = "".join(((spec["cells"].get(f, (None,))[0] or "·")[:cw - 1]).ljust(cw)
                        for f in FORMATS)
        rows.append(f"{cap:<{kw}}{cells}")
    return "\n".join(rows)


def check(warrants_bib: Path) -> tuple[bool, list[str]]:
    """Assert every demonstrated cell names a real warrant and the pdf-ua row matches the graph.

    Every afforded/post/native/excepted cell must name a warrant that EXISTS in warrants.bib, and
    the pdf-ua row must AGREE with graph.MORPHISMS — the matrix cannot claim a demonstration it
    does not have, nor a PDF/UA affordance the graph contradicts.
    """
    keys = _warrant_keys(warrants_bib)
    problems = []
    for cap, spec in CAPABILITIES.items():
        for fmt, (state, warrant) in spec["cells"].items():
            if state in (None, "n/a"):
                continue
            if not warrant:
                problems.append(f"{cap} × {fmt}: state {state!r} but no demonstrating warrant "
                                f"named")
            elif warrant not in keys:
                problems.append(f"{cap} × {fmt}: names warrant {warrant!r} absent from "
                                f"warrants.bib")
    # the pdf-ua row is graph.MORPHISMS[edge].a11y — office pdf edges "post", the latex "native"
    ua = CAPABILITIES["pdf-ua"]["cells"]
    # COVERAGE — every graph object is either stated over here or declared not-stated, with a
    # reason.  Without this the two faces of "one owned coalgebra" drift silently: a node added to
    # the graph simply never appears in the capability grid, and each face keeps passing because
    # each checks itself against its own list.
    uncovered = [o for o in graph.OBJECTS if o not in FORMATS and o not in NOT_STATED]
    if uncovered:
        problems.append(f"graph object(s) {uncovered} are neither stated over nor declared "
                        f"NOT_STATED — the capability grid and the conversion graph have "
                        f"diverged, and each face would keep passing against its own object list")
    stale = [o for o in NOT_STATED if o not in graph.OBJECTS]
    if stale:
        problems.append(f"NOT_STATED names {stale}, absent from the graph — the exemption "
                        f"outlived its object")

    if ua["pdf-office"][0] != graph.MORPHISMS[("docx", "pdf")]["a11y"]:
        problems.append("pdf-ua × pdf-office disagrees with graph.MORPHISMS[(docx,pdf)].a11y")
    if ua["pdf-latex"][0] != graph.MORPHISMS[("latex", "pdf")]["a11y"]:
        problems.append("pdf-ua × pdf-latex disagrees with graph.MORPHISMS[(latex,pdf)].a11y")
    return (not problems), problems


def main(argv: list[str]) -> int:
    """Print the capability grid, or with --check assert it against warrants.bib and the graph."""
    bib = Path(__file__).resolve().parent.parent / "warrants.bib"
    if "--check" in argv:
        ok, problems = check(bib)
        if not ok:
            for p in problems:
                sys.stderr.write(f"matrix --check: {p}\n")
            return 1
        n_cells = sum(1 for s in CAPABILITIES.values()
                      for st, _ in s["cells"].values() if st not in (None, "n/a"))
        sys.stdout.write(f"matrix --check: {len(CAPABILITIES)} capabilities × {len(FORMATS)} "
                         f"formats, {n_cells} demonstrated cells — every cell has its warrant "
                         f"and the pdf-ua row agrees with the render graph\n")
        return 0
    sys.stdout.write("render capability × format matrix (row = capability, col = format):\n\n")
    sys.stdout.write(_grid() + "\n")
    sys.stdout.write("\ncell states: native (by construction) · post (after post-processing) · "
                     "excepted (toolchain cannot) · · (no cell)\n")
    return 0


if __name__ == "__main__":
    # ⚑ Ζ·witness·component — THE SHIM IS WHAT MAKES A RELATIVE IMPORT SURVIVE ROUTE 1.  The
    # bib's `check` field spells `python3 checks/matrix.py`, and a file run that way has NO
    # parent package, so `from . import graph` raises ImportError before main() is reached
    # (measured, not predicted — the first cut of this conversion died exactly there).  Run as a
    # module, `__package__` is set and the import resolves; run as a script, this re-enters
    # through runpy with the repo root on the path so the SAME module is imported by name.
    #
    # ⚑⚑ THE PATH INSERT HERE IS NOT THE INJECTION BEING RETIRED.  It appends the REPO ROOT so
    # `render.checks.matrix` is nameable at all, and it runs once at entry rather than shadowing
    # the search path for every later import — which is what `sys.path.insert(0, <this dir>)`
    # did, making a sibling win over the engine's own modules.
    if __package__:
        raise SystemExit(main(sys.argv[1:]))
    import runpy

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    runpy.run_module("render.checks.matrix", run_name="__main__", alter_sys=True)
