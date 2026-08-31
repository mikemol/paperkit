#!/usr/bin/env python3
r"""Ρ·render·pdf — the render graph's PDF node: the terminal deliverable, reached by a chosen route.

The PDF is where every route in the render coalgebra (graph.py) terminates, and it is reached from
several intermediates — a docx or an odt through the office suite, a LaTeX source through lualatex.
So this is a ROUTER: it takes an intermediate (`--via docx|odf|latex`, default docx), produces that
format from the one resolved source (the docx/odf/latex nodes), runs the pdf-producing morphism, and
applies the route's accessibility by construction:

  - the office routes (docx, odf) reach PDF/UA-1: the UNO export sets the pdfuaid/title/DisplayDocTitle
    metadata and refreshes indexes, then linkalt describes the source-document links the export leaves
    bare (7.18) and mathalt gives each equation a text alternative (7.7); table columns are sized to
    measured ink first so a wide math cell cannot clip.  This is the "post" a11y the graph records for
    those edges — PDF-level repair after the office export.
  - the latex route reaches PDF/UA-2 natively (the a11y is "native" in the graph): the tagging is in
    the source (\DocumentMetadata), so this route delegates wholesale to the latex node, no repair.

    python3 checks/pdf.py [--via docx|odf|latex]   # produce + gate the PDF via the chosen route
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import docx as docx_node
import graph
import latex as latex_node
import linkalt  # 7.18 link descriptions (office routes)
import lo  # office convert: isolated profile + unlink-first
import mathalt  # 7.7 equation alternatives (office routes)
import odf as odf_node
import source
import widen_tables  # size table columns to measured ink so a wide math cell can't clip


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lo_export = _load("lo_export", "lo-export.py")   # docx/odt → tagged PDF/UA over the UNO bridge


def _office_pdf(intermediate: Path, out_pdf: Path, work: Path) -> Path | None:
    """The office pdf-producing morphism (soffice) + its "post" a11y: UA export → linkalt → mathalt.
    Table columns are sized to measured ink BEFORE the export (a wide oMath run cannot wrap).  Falls
    back to a plain convert if no uno-capable python is present, so the deliverable still renders.
    """
    sized = work / ("sized" + intermediate.suffix)
    widen_tables.widen(intermediate, sized)
    pdf = lo_export.export_pdfua(sized, out_pdf) or lo.convert(sized, "pdf", work)
    if pdf is None or pdf.stat().st_size == 0:
        return None
    if pdf != out_pdf:
        out_pdf.write_bytes(pdf.read_bytes())
    linkalt.describe_links(out_pdf)                                              # 7.18
    mathalt.describe_formulas(out_pdf, mathalt.paper_equations(Path("../paper/paper.md")))  # 7.7
    return out_pdf


def render(paper_md: Path, out_pdf: Path, via: str, work: Path) -> Path | None:
    """Produce `paper_md` as a PDF via route `via`, composing the graph's morphisms.  None if the
    route's toolchain is unavailable (loud) — so a box lacking one route's tools still serves another.
    """
    path = graph.ROUTES[via]                                    # e.g. ["md","docx","pdf"]
    a11y = graph.route_a11y(via)                                # "post" (office) | "native" (latex)
    if a11y == "native":                                        # the latex route: tagging is in source
        return latex_node.build(paper_md, out_pdf, work)
    # an office route: produce the intermediate node, then the office pdf edge + post-a11y
    inter_fmt = path[1]                                         # "docx" or "odt"
    producer = {"docx": docx_node.docx, "odt": odf_node.odt}[inter_fmt]
    intermediate = producer(paper_md, work / f"p.{inter_fmt}")
    return _office_pdf(intermediate, out_pdf, work)


def _formula_alts(pdf: Path) -> tuple[int, int]:
    """(formula count, how many carry an EMPTY /Alt) in the deliverable's structure tree — the
    office route's math alternative, read from the shipped artifact rather than trusted from the
    step that wrote it.
    """
    try:
        import pikepdf
    except ImportError:
        return (0, 0)
    alts: list = []

    def walk(n, d=0):
        if d > 20 or not hasattr(n, "get"):
            return
        if str(n.get("/S") or "") == "/Formula":
            alts.append(str(n.get("/Alt") or ""))
        for k in (n.get("/K") or []):
            if hasattr(k, "get"):
                walk(k, d + 1)

    with pikepdf.open(str(pdf)) as doc:
        root = doc.Root.get("/StructTreeRoot")
        if root is not None:
            walk(root)
    return (len(alts), sum(1 for a in alts if not a.strip()))


def _link_count(pdf: Path) -> int:
    """Every /Link annotation in the deliverable — the denominator the informative-description
    ratio is stated over, read from the PDF rather than assumed from the source.
    """
    try:
        import pikepdf
    except ImportError:
        return 0
    with pikepdf.open(str(pdf)) as doc:
        return sum(1 for pg in doc.pages for a in (pg.get("/Annots") or [])
                   if a.get("/Subtype") == "/Link")


def main(argv: list[str]) -> int:
    via = argv[argv.index("--via") + 1] if "--via" in argv else "docx"
    if via not in graph.ROUTES:
        print(f"pdf: unknown route --via {via} (expected {'|'.join(graph.ROUTES)})", file=sys.stderr)
        return 3
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        pdf = render(Path("../paper/paper.md"), d / "p.pdf", via, d)
        if pdf is None:
            print(f"pdf: CANNOT BUILD via {via} — the route's toolchain is unavailable", file=sys.stderr)
            return 3                                            # cannot-run, not a false pass
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        pages = int((re.search(r"Pages:\s*(\d+)", info) or [0, 0])[1])
        txt = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
        bare = re.findall(r"\[@[A-Za-z][\w:.+-]*\]", txt)
        words = sorted(set(re.findall(r"[a-z]{4,}", source.cite_split(Path("../paper/paper.md")).lower())))
        seen = set(re.findall(r"[a-z]{4,}", txt.lower()))
        rate = sum(w in seen for w in words) / len(words)
        # Ρ·render·alt·live — the SHIPPED deliverable's link descriptions must actually say
        # something.  linkalt describes every link (PDF/UA 7.18) and reports how many descriptions
        # are uninformative, but reporting alone let a real defect ship: measured on this very
        # deliverable, 18 of 19 links carried a bare footnote digit, so a screen reader announced
        # "link, one" while the check said 0 undescribed remain.  The report is now a GATE.
        #
        # The threshold is not zero.  A link over a figure has no words beneath it and honestly
        # falls back to "link"; failing the build for that would be measuring the wrong thing —
        # the same trap as counting the office suite's table-preview thumbnail as an undescribed
        # image.  What must not recur is the BULK case, where the marker-expansion has regressed
        # and most links say nothing.  So: a minority may sit on the honest floor; a majority may
        # not.
        # Ρ·render·alt·selfbar — SWEPT: seven render warrants are graded ONLY by their producer's
        # own --selftest.  That is legitimate for a METHOD (a ⟨P,F,δ⟩ proof of the technique), and
        # veraPDF at UA-1 does cover link and formula descriptions on the deliverable — but only
        # for PRESENCE, which is exactly the bar that passed 18 bare digits.  The gap is QUALITY on
        # the shipped artifact, and these two lines close it for the two producers whose output is
        # a description.  widen_tables remains selftest-only for its measured column widths.
        #
        # mathalt WRITES /Alt on every /Formula and nothing verified it on
        # the deliverable: its own selftest was the only witness, while the LaTeX route asserts its
        # formulas carry a real alternative in the SHIPPED artifact.  A producer whose output no
        # verifier grades is the same shape as a description that is present but useless — the
        # check and the thing checked were the same party.  Measured here: 21 formulas, 0 empty.
        formulas, empty_alt = _formula_alts(pdf)
        math_ok = not empty_alt

        thin = linkalt.uninformative(pdf)
        nlinks = _link_count(pdf)
        thin_ok = (not nlinks) or (len(thin) * 2 <= nlinks)

        ok = pages >= 1 and not bare and rate >= 0.85 and thin_ok and math_ok
        print(f"pdf: {'ok' if ok else 'FAIL'} via {via} — {pages}-page deliverable "
              f"({'no bare markers, ' if not bare else f'{len(bare)} bare markers, '}"
              f"{rate:.0%} of body content present, "
              f"{nlinks - len(thin)}/{nlinks} links informatively described, "
              f"{formulas - empty_alt}/{formulas} formulas with a math alternative"
              f"{'' if math_ok else f' — {empty_alt} EMPTY /Alt'}"
              f"{'' if thin_ok else ' — MOST LINKS SAY NOTHING: ' + str(sorted({c for _, c in thin})[:6])}"
              f")")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
