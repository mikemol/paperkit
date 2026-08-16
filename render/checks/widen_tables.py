#!/usr/bin/env python3
"""widen_tables.py — size docx table columns to their MEASURED content, so a wide
math cell is never clipped (the R-1 defect: an un-wrappable OMML run wider than its
fixed cell paints past the page edge and is truncated).

Why measurement, not a proxy: LibreOffice renders OMML math at a document-wide base
size that ignores both the table style's `rPr` and per-run `<w:sz>` — so the font
cannot be shrunk, and a character-count proxy mis-sizes columns badly (math is wider
per character than text).  The only working lever is column width, and the only
reliable way to set it is to MEASURE each cell's rendered width.

Method (self-calibrating, no magic numbers):
  1. Emit every table cell's paragraph(s) as standalone body paragraphs in a probe
     docx (cloned from the real one, so styles/fonts/page geometry are identical).
     Every cell is < text width, so each renders on one line = one ink band.
  2. Render the probe with LibreOffice; measure each band's ink width, in order.
  3. Per (table, column): take the max measured width (+ cell margins + slack).
  4. Lay each table out at full text width: if the column needs sum to <= text width,
     use them (and grow the widest column to fill); if they exceed it (the hard minimums
     do not fit UNDER COLUMN-WIDTH SIZING — a wider page or a broken equation is untried),
     scale all columns down proportionally — minimal, uniform shrink rather than clipping
     one cell, and --check flags it.
  5. Rewrite each table's <w:tblGrid> and per-cell <w:tcW>, fixed layout.

Usage:  widen_tables.py IN.docx OUT.docx [--text-width-twips N]   # size columns
        widen_tables.py DOCX --check                              # G9 guard
A no-op (copy) if LibreOffice/poppler/Pillow are unavailable, so the build never
breaks on a missing dependency.

--check is the R-1 regression guard (G9): it re-measures every cell and asserts each
fits its column, failing if any would clip.  NB a pure margin-overflow guard does NOT
work here — LibreOffice clips an over-wide run AT the text margin, so a clipped cell
and a fitting cell end at the same x; the only reliable signal is per-cell fit.  Run
inside mkdocx.sh (build refuses to emit a clipping docx) and in the JI gate.
"""
import sys
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import lo  # sibling helper: isolated-profile libreoffice conversion (race/provenance-safe)

EMU_MARGIN = 216          # 2 * 108-twip default cell margin (Table style)
SLACK = 120               # ~0.08in breathing room past measured ink
FLOOR = 700               # never below ~0.5in
TOL = 80                  # twips: re-measurement jitter tolerance for --check
DPI = 300


def _have(tool):
    return shutil.which(tool) is not None


def read_document(docx):
    with zipfile.ZipFile(docx) as z:
        return z.read("word/document.xml").decode()


def write_document(src, dst, new_doc):
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = new_doc.encode() if it.filename == "word/document.xml" else zin.read(it.filename)
            zout.writestr(it, data)


def collect_cells(doc):
    """[(table_index, col_index, cell_paragraph_xml)] in document order."""
    cells = []
    for ti, tm in enumerate(re.finditer(r"<w:tbl>.*?</w:tbl>", doc, re.S)):
        for row in re.findall(r"<w:tr\b.*?</w:tr>", tm.group(0), re.S):
            for ci, tc in enumerate(re.findall(r"<w:tc>.*?</w:tc>", row, re.S)):
                ps = re.findall(r"<w:p\b.*?</w:p>", tc, re.S)
                cells.append((ti, ci, "".join(ps) or "<w:p/>"))
    return cells


def build_probe(doc, cells):
    """Clone the body, replacing its content with the cells as standalone paragraphs on
    a VERY WIDE page (so no cell wraps), each cell followed by a full-width RULE
    sentinel.  The rule — not a white-space gap — is the cell boundary: no cell's ink
    ever reaches the rule's near-full-page width, so segmentation is exact even when
    tall math opens vertical gaps inside a cell (the old gap heuristic mistook those for
    breaks).  Each cell's width is then its true single-line width — which, for an
    un-wrappable math run, IS the width it will demand in the real table."""
    body = re.search(r"<w:body>(.*)</w:body>", doc, re.S).group(1)
    sect = re.search(r"<w:sectPr\b.*?</w:sectPr>", body, re.S)
    sect_xml = sect.group(0) if sect else "<w:sectPr></w:sectPr>"
    # widen the probe page to 40in so nothing wraps.  pandoc's sectPr usually carries NO
    # pgSz/pgMar (it inherits them from the reference doc), so drop any that exist and
    # INSERT ours right after the <w:sectPr> opening tag.
    pg = ('<w:pgSz w:w="57600" w:h="15840" />'
          '<w:pgMar w:top="720" w:right="360" w:bottom="720" w:left="360" '
          'w:header="0" w:footer="0" w:gutter="0" />')
    sect_xml = re.sub(r'<w:pg(Sz|Mar)\b[^>]*/?>', '', sect_xml)
    sect_xml = re.sub(r'(<w:sectPr\b[^>]*>)', r'\1' + pg, sect_xml, count=1)
    # RULE = an empty paragraph with a bottom border → a solid line at the text width
    # (~39.5in on the 40in page).  One after every cell; the count of rules == the count
    # of cells, so measurement can never miscount.
    rule = ('<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="12" w:space="1" '
            'w:color="000000"/></w:pBdr></w:pPr></w:p>')
    probe_body = "<w:body>" + "".join(p + rule for _, _, p in cells) + sect_xml + "</w:body>"
    return re.sub(r"<w:body>.*</w:body>", lambda _m: probe_body, doc, flags=re.S)


def measure_cells(pngs):
    """Cell widths (inches) in order, one per RULE sentinel.  A rule row is detected by
    ink near the right edge (x≈0.9w / 0.95w), where only the near-full-width border can
    reach — cell content never does.  Each rule closes the current cell; ink between
    rules accumulates into it, ACROSS page breaks, so a cell split by a page boundary is
    still measured whole.  Tall math no longer matters: intra-cell vertical gaps are not
    boundaries — only the rule is.

    PIL-only port of mat260's numpy version (paperkit stays numpy-free; PIL is already a
    render-layer dep via ocr.py).  The row STATE MACHINE is byte-identical to the original —
    only the per-row ink arrays (any-ink / leftmost / rightmost) are built with PIL: the image
    is binarized at mat260's exact <150 threshold (so the measured ink set equals numpy's
    `arr < 150`, not the antialias halo a raw getbbox would sweep in), and each row's ink extent
    is `getbbox()` on that row's 1px strip — a TRUE EXISTENTIAL (None iff no ink), the PIL equal
    of `arr.any(axis=1)` + argmax.  It deliberately does NOT collapse the row with `resize`: a
    downscale filter averages a lone dark pixel back to white and would silently drop a thin
    stroke, biasing columns too narrow (measured).  Cross-page accumulation (left/right/have/
    in_rule initialized ONCE before the png loop) is preserved exactly — a cell split by a page
    break is measured whole, and `margin` is recomputed per page (relative rule detection, so a
    page whose rule is not full-width still segments)."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None            # the probe page is intentionally huge
    widths = []
    left, right, have, in_rule = 10 ** 9, 0, False, False
    for png in pngs:
        # Pre-binarize at mat260's exact <150 threshold, so getbbox measures ONLY the ink darker
        # than 150 (not the antialias halo a getbbox on the raw image would sweep in) and matches
        # numpy's `arr < 150` set exactly.
        bw = Image.open(png).convert("L").point(lambda p: 255 if p < 150 else 0)   # ink → 255
        w, h = bw.size
        # Ink extent per row by getbbox on the 1px-tall strip — a TRUE EXISTENTIAL (None iff the
        # strip has no ink), the PIL equal of numpy's `arr.any(axis=1)` + argmax leftmost/rightmost.
        # NOT resize-to-one-pixel: a downscale filter AVERAGES a lone dark pixel back to white and
        # would silently DROP a thin stroke (a fraction bar, a minus) — biasing columns too narrow
        # (mat260's flag; measured: resize((1,h)) returns 255 for one ink pixel in 12000).  getbbox
        # sees the single pixel.
        extent = {}                                            # y -> (leftmost, rightmost) ink column
        for y in range(h):
            b = bw.crop((0, y, w, y + 1)).getbbox()            # (l, 0, r_exclusive, 1) or None
            if b:
                extent[y] = (b[0], b[2] - 1)
        if not extent:
            continue
        margin = max(r for _l, r in extent.values())           # widest ink on the page = the rule/border
        for y in range(h):
            is_rule = y in extent and extent[y][1] >= 0.9 * margin
            if is_rule:
                if not in_rule:                                 # close the cell once, on rule entry
                    widths.append((max(0, right - left) / DPI) if have else 0.0)
                    left, right, have, in_rule = 10 ** 9, 0, False, True
            elif y in extent:                                   # a content (non-rule) ink row
                in_rule = False
                lm, rm = extent[y]
                left = min(left, lm)
                right = max(right, rm)
                have = True
            else:
                in_rule = False
    return widths


def render_widths(src_docx, doc, cells, work):
    probe_doc = build_probe(doc, cells)
    probe = Path(work, "probe.docx")
    write_document(src_docx, probe, probe_doc)
    pdf = lo.convert(probe, "pdf", work)   # isolated profile: a concurrent soffice can't corrupt the probe
    if pdf is None:
        return None
    subprocess.run(["pdftoppm", "-png", "-r", str(DPI), str(pdf), str(Path(work, "pg"))],
                   capture_output=True)
    pngs = sorted(Path(work).glob("pg-*.png"),
                  key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)))   # numeric page order
    return measure_cells(pngs)


def _unwrappable(xml):
    """True only if the cell cannot reflow at ALL — so its full single-line width is a
    hard minimum.  That holds for a LONE math object (LibreOffice never breaks inside an
    OMML run) with no surrounding prose, or a single whitespace-free token (e.g.
    'ChaCha20').  A cell that mixes prose with inline math (crypto's witness columns)
    wraps at the prose spaces: its widest unbreakable atom is a word or the small inline
    math, NOT the 30-inch single-line render — so it is NOT rigid, and its full width is
    only a preferred hint."""
    prose = re.sub(r"<m:oMath\b.*?</m:oMath>", "", xml, flags=re.S)        # strip math objects
    prose_txt = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", prose)).strip()
    if "<m:oMath" in xml:
        return prose_txt == ""                                            # lone math, no prose → rigid
    return bool(prose_txt) and " " not in prose_txt                       # single bare token → rigid


def col_widths(cells, ink_widths, key):
    """(table,col) -> max twips (ink + cell margins) over cells whose xml satisfies key."""
    out = {}
    for (ti, ci, xml), iw in zip(cells, ink_widths):
        if key(xml):
            out[(ti, ci)] = max(out.get((ti, ci), 0), int(iw * 1440) + EMU_MARGIN)
    return out


def read_grids(doc):
    """table_index -> [gridCol twips] as actually present in the docx."""
    return {ti: [int(w) for w in re.findall(r'<w:gridCol w:w="(\d+)"', tm.group(0))]
            for ti, tm in enumerate(re.finditer(r"<w:tbl>.*?</w:tbl>", doc, re.S))}


def lay_out(doc, cells, ink_widths, text_w):
    """Map measured widths back to (table,col)->max, compute target grids, rewrite."""
    if len(ink_widths) != len(cells):
        print(f"widen_tables: band/cell count mismatch ({len(ink_widths)} vs {len(cells)}); "
              f"skipping (no change)", file=sys.stderr)
        return doc, False
    pref = col_widths(cells, ink_widths, lambda _x: True)        # full content width, any cell
    hard = col_widths(cells, ink_widths, _unwrappable)           # un-wrappable cells: hard minimum
    ncol = {}        # ti -> column count
    for (ti, ci, _), _iw in zip(cells, ink_widths):
        ncol[ti] = max(ncol.get(ti, 0), ci + 1)

    targets = {}     # ti -> [widths]
    for ti, n in ncol.items():
        base = [max(FLOOR, hard.get((ti, c), 0)) for c in range(n)]          # must-fit floor per column
        want = [max(FLOOR, pref.get((ti, c), 0) + SLACK) for c in range(n)]  # preferred width
        if sum(base) >= text_w:
            # un-wrappable content alone exceeds the page — shrink to fit (will clip; --check flags it)
            cols = [max(FLOOR, int(b * text_w / sum(base))) for b in base]
        else:
            # every column keeps its hard floor; the slack is shared ∝ preferred width, so wrappable
            # prose columns absorb the compression and math columns are never starved below their need.
            slack, wsum = text_w - sum(base), sum(want)
            cols = [base[c] + slack * want[c] // wsum for c in range(n)]
        cols[cols.index(max(cols))] += text_w - sum(cols)        # absorb rounding to exactly text_w
        targets[ti] = cols

    out, last, changed = [], 0, False
    for ti, tm in enumerate(re.finditer(r"<w:tbl>.*?</w:tbl>", doc, re.S)):
        out.append(doc[last:tm.start()])
        tbl = tm.group(0)
        cols = targets[ti]
        grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}" />' for w in cols) + "</w:tblGrid>"
        tbl = re.sub(r"<w:tblGrid>.*?</w:tblGrid>", grid, tbl, flags=re.S)
        ci = [0]

        def repl_tcw(_m):
            w = cols[ci[0] % len(cols)]
            ci[0] += 1
            return f'<w:tcW w:w="{w}" w:type="dxa" />'

        tbl = re.sub(r"<w:tcW\b[^/]*/>", repl_tcw, tbl)
        out.append(tbl)
        last = tm.end()
        changed = True
    out.append(doc[last:])
    return "".join(out), changed


def _deps_absent():
    # PIL-only port: numpy is NOT a paperkit dependency and must not be required.  PIL is
    # already a render-layer dep (ocr.py); libreoffice + pdftoppm are the render toolchain.
    if not (_have("libreoffice") and _have("pdftoppm")):
        return "libreoffice/poppler"
    try:
        import PIL  # noqa: F401
    except ImportError:
        return "Pillow"
    return None


def _measure(src):
    """-> (doc, cells, ink_widths) or (doc, cells, None) on render failure."""
    doc = read_document(src)
    cells = collect_cells(doc)
    if not cells:
        return doc, cells, []
    with tempfile.TemporaryDirectory() as work:
        ink = render_widths(src, doc, cells, work)
    return doc, cells, ink


def check(src):
    """G9 guard: assert every cell fits its column, so the R-1 clip can't recur.
    A pure margin guard misses this — LibreOffice clips the overflow AT the margin,
    so broken and fixed both stop at the same x; the real signal is per-cell fit."""
    # Ζ·degrade positive-control: a check that CANNOT MEASURE must NOT read as a green pass (that
    # is a false verification — the R-1 clip could recur unseen).  Exit 2 = CANNOT-RUN (the engine's
    # typed-exit alphabet: 0 pass, 1 ran-and-failed, 2 could-not-run), distinct from the fit verdict.
    absent = _deps_absent()
    if absent:
        print(f"widen_tables --check: {absent} absent — CANNOT VERIFY (not a pass)", file=sys.stderr)
        return 2
    doc, cells, ink = _measure(src)
    if not cells:
        print("widen_tables --check: no tables to check")   # nothing to clip is a genuine pass
        return 0
    if ink is None or len(ink) != len(cells):
        print(f"widen_tables --check: could not measure ({'render failed' if ink is None else 'band mismatch'})"
              " — CANNOT VERIFY (not a pass)", file=sys.stderr)
        return 2
    grids = read_grids(doc)
    # only UN-WRAPPABLE cells can clip (math runs + single whitespace-free tokens); prose reflows.
    need = col_widths(cells, ink, _unwrappable)
    bad = []
    for (ti, ci), nd in need.items():
        col = grids.get(ti, [])
        alloc = col[ci] if ci < len(col) else 0
        if nd > alloc + TOL:
            bad.append((ti, ci, nd, alloc))
    if bad:
        for ti, ci, nd, al in bad:
            print(f"widen_tables --check: table {ti} col {ci}: content needs {nd}tw > column {al}tw "
                  f"(overflows by {nd - al}tw → CLIPS)", file=sys.stderr)
        # A FIRST-PASS verdict, not an exhaustion proof: the cell does not fit under the ONE lever
        # this tool pulls — column width sizing.  Other levers are UN-TRIED here (a wider/landscape
        # page, narrower margins, breaking the equation into a multi-line form — which on the pandoc
        # route needs the equation re-emitted with breaks, since LibreOffice never breaks inside an
        # oMath run).  One lever is PROVEN unavailable: shrinking the math font — LibreOffice renders
        # OMML at a fixed base size and ignores both rPr and per-run w:sz, so column width is the only
        # sizing lever (mat260, measured).  So this says "over-wide under column sizing", not "too wide".
        print(f"widen_tables --check: {len(bad)} cell(s) do not fit under column-width sizing — run "
              "widen_tables to size to measured ink, or widen the page (landscape / margins) or shorten "
              "the equation; the math font cannot be shrunk (LibreOffice ignores it)", file=sys.stderr)
        return 1
    print(f"widen_tables --check: all {len(need)} cells fit their columns across {len(grids)} table(s)")
    return 0


def _selftest():
    """⟨P, F, δ⟩ — a docx with a math cell wider than its column:
      F: --check on the un-widened docx reports the un-wrappable math cell overflows → CLIPS (rc 1).
      P: after widen() sizes the columns to measured ink, --check finds every cell fits (rc 0).
      δ: the column sizing — the tblGrid/tcW twips widen() writes; a pure margin guard cannot tell P
         from F (LibreOffice clips AT the margin, so both end at the same x — per-cell fit is the signal).
    SKIPS LOUD (never green) if the render deps are absent — the same degrade discipline as --check."""
    absent = _deps_absent()
    if absent:
        print(f"  -- {absent} absent; the measurement cannot run here.\n"
              "     WIDEN SELFTEST: SKIP (loud) — the method is present but unrunnable on this box")
        return 0
    fails = []

    def check_(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    # measurement accuracy against a KNOWN width — a synthetic probe page (a cell of known ink width
    # + a near-full-width rule), so the measured band is checkable against ground truth.  This is the
    # guard against the silent-bias class (a resize-averaged any-ink test drops a thin stroke and
    # under-measures; a raw getbbox sweeps the antialias halo and over-measures) — both pass a
    # thick-math ⟨P,F,δ⟩ while shifting every width.  (mat260's proposed one-run check, made permanent.)
    from PIL import Image, ImageDraw
    with tempfile.TemporaryDirectory() as t:
        pg = Path(t) / "pg-1.png"
        img = Image.new("L", (2000, 30), 255)
        dr = ImageDraw.Draw(img)
        dr.rectangle([100, 5, 500, 10], fill=0)          # cell ink: exactly 400 px wide
        dr.rectangle([0, 20, 1900, 25], fill=0)          # rule: 95% of the page width
        img.save(pg)
        measured = measure_cells([pg])
        want = 400 / DPI
        check_(f"measures a known 400px band as {want:.3f}in (±1px) — not resize-biased narrow "
               "nor halo-biased wide",
               len(measured) == 1 and abs(measured[0] - want) < 2 / DPI)
        # a single ink pixel in a wide row is SEEN (the thin-stroke existential) — a resize-averaged
        # any-ink test returns white for one dark pixel in 2000 and would miss it.  Assert the binarized
        # row's getbbox finds it, the exact property the fix restores.
        thin = Image.new("L", (2000, 1), 255)
        thin.putpixel((1000, 0), 0)
        bw = thin.point(lambda p: 255 if p < 150 else 0)
        check_("a lone ink pixel in a wide row is seen (getbbox existential, not a resize average)",
               bw.getbbox() is not None)

    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        # a one-row, one-column table whose single cell is a WIDE lone-math run (the rigid case that
        # clips), inside a deliberately NARROW gridCol — built via pandoc so the OMML is real.  The
        # equation is chosen to be wider than the narrow column but NARROWER than the page (so a
        # correct layout CAN fit it — the realistic R-1 case, not an unfittable one).
        (d / "f.md").write_text(
            "| f |\n|---|\n| "
            r"$\mathrm{eff}(c) = \min\{\, \mathrm{grade}(c)\,\} \cup \{\, \mathrm{eff}(d) : d \in "
            r"\mathrm{rests\text{-}on}(c)\,\}$"
            " |\n")
        src = d / "f.docx"
        subprocess.run(["pandoc", str(d / "f.md"), "-o", str(src)], check=True)
        # force a narrow column so the wide math overflows (the R-1 condition)
        doc = read_document(src)
        doc = re.sub(r"<w:gridCol w:w=\"\d+\"", '<w:gridCol w:w="1440"', doc)   # 1in column
        write_document(src, d / "narrow.docx", doc)
        src = d / "narrow.docx"

        rc_f = check(str(src))
        check_("F: the wide math cell overflows its narrow column unwidened (--check → CLIPS, rc 1)",
               rc_f == 1)

        widened = widen(src, d / "wide.docx", text_w=9360)
        rc_p = check(str(widened))
        check_("P: after widen() sizes the column to measured ink, every cell fits (--check rc 0)",
               rc_p == 0)
        check_("δ: widen() changed the column sizing (the tblGrid twips differ)",
               read_grids(read_document(widened)) != read_grids(read_document(src)))

    if fails:
        print(f"WIDEN SELFTEST: FAIL ({len(fails)})")
        return 1
    print("WIDEN SELFTEST: PASS")
    return 0


def widen(src_docx, dst_docx, text_w=9360):
    """Library entry for the render pipeline: size `src_docx`'s table columns to measured ink
    and write to `dst_docx` (the main() body minus argv).  Copies through unchanged if deps are
    absent, there are no tables, or the probe render fails — so the deliverable NEVER breaks on a
    missing dependency (the loud-absence doctrine of lo.py).  text_w = the page's text width in
    twips (9360 = US-Letter, 1in margins)."""
    if _deps_absent() or not (doc_cells := _measure(src_docx))[1]:
        shutil.copy(src_docx, dst_docx)
        return dst_docx
    doc, cells, ink = doc_cells
    if ink is None:
        print("widen_tables: probe render failed — copying unchanged", file=sys.stderr)
        shutil.copy(src_docx, dst_docx)
        return dst_docx
    new_doc, changed = lay_out(doc, cells, ink, text_w)
    if changed:
        write_document(src_docx, dst_docx, new_doc)
    else:
        shutil.copy(src_docx, dst_docx)
    return dst_docx


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    if "--check" in sys.argv:
        src = next(a for a in sys.argv[1:] if not a.startswith("--"))
        return check(src)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src, dst = args[0], args[1]
    text_w = 9360
    if "--text-width-twips" in sys.argv:
        text_w = int(sys.argv[sys.argv.index("--text-width-twips") + 1])

    absent = _deps_absent()
    if absent:
        print(f"widen_tables: {absent} absent — copying unchanged", file=sys.stderr)
        shutil.copy(src, dst)
        return 0
    doc, cells, ink = _measure(src)
    if not cells:
        shutil.copy(src, dst)
        return 0
    if ink is None:
        print("widen_tables: probe render failed — copying unchanged", file=sys.stderr)
        shutil.copy(src, dst)
        return 0
    new_doc, changed = lay_out(doc, cells, ink, text_w)
    if changed:
        write_document(src, dst, new_doc)
        print(f"widen_tables: sized {len({t for t, _, _ in cells})} table(s) to measured content")
    else:
        shutil.copy(src, dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
