#!/usr/bin/env python3
r"""Ρ·render·linkalt — restore link descriptions the office suite omits, AFTER export.

Adopted from sre-troubleshooting's `workaround-link-alt-post-export` (summit floor,
ask-adopt-pdfua-render-workarounds), against the pandoc→LibreOffice route paperkit's paper
renders through.  PDF/UA 7.18.1 and 7.18.5 require every link annotation to carry a text
description; LibreOffice's headless export leaves some `/Link` annotations with an empty
`/Contents`, so a screen reader announces a bare "link" with no destination.

The method, on sre's reasoning — *the words a sighted reader sees are what a screen reader should
hear*: a pass over the FINISHED PDF reads the words whose boxes fall inside each undescribed link's
rectangle and writes them back as that link's `/Contents`.  sre's first version described only HALF
of a pair of adjacent citations, because two adjacent links extract as a single word whose CENTRE
lies inside neither rectangle.  This carries the fix forward: a word is selected by BOX OVERLAP with
the link rect (any intersection), not by its centre — so a word straddling two links is counted for
both, and every undescribed link that covers visible text gets a description.

Coordinate note (the one correctness trap): a PDF `/Rect` is user space (origin BOTTOM-left,
y-up); `pdftotext -bbox` reports TOP-left, y-down.  We flip the rect through the page `/MediaBox`
height before intersecting.  The F-arm of the ⟨P,F,δ⟩ fixture guards exactly this.

    python3 checks/linkalt.py DELIVERABLE.pdf   # describe in place; exit 0 iff 0 undescribed remain
    python3 checks/linkalt.py --selftest        # ⟨P,F,δ⟩ against a built fixture (no args)

`describe_links(pdf) -> int` returns the count restored, for pdf.py to call in the render pipeline.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pikepdf


def _words(pdf: Path) -> list[list[tuple[float, float, float, float, str]]]:
    """Per-page word boxes from `pdftotext -bbox` (top-left, y-down): [(x0,y0,x1,y1,text), ...]."""
    out = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"],
                         capture_output=True, text=True).stdout
    pages: list[list[tuple[float, float, float, float, str]]] = []
    for chunk in out.split("</page>")[:-1]:
        ws: list[tuple[float, float, float, float, str]] = []
        for m in re.finditer(
                r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>',
                chunk):
            x0, y0, x1, y1 = (float(g) for g in m.groups()[:4])
            ws.append((x0, y0, x1, y1, m.group(5)))
        pages.append(ws)
    return pages


def describe_links(pdf: Path) -> int:
    """Describe every undescribed `/Link` from the words whose box OVERLAPS its rect.  Saves in
    place.  Returns the number of links given a `/Contents`."""
    words = _words(pdf)
    doc = pikepdf.open(str(pdf), allow_overwriting_input=True)
    restored = 0
    for i, page in enumerate(doc.pages):
        mb = page.MediaBox
        ph = float(mb[3]) - float(mb[1])                      # page height, for the y-flip
        ws = words[i] if i < len(words) else []
        for a in page.get("/Annots", []):
            if a.get("/Subtype") != "/Link" or a.get("/Contents"):
                continue
            r = [float(x) for x in a["/Rect"]]
            rx0, rx1 = min(r[0], r[2]), max(r[0], r[2])
            ry0, ry1 = ph - max(r[1], r[3]), ph - min(r[1], r[3])   # /Rect (y-up) → pdftotext (y-down)
            hits = [w for w in ws
                    if not (w[2] < rx0 or w[0] > rx1 or w[3] < ry0 or w[1] > ry1)]  # BOX OVERLAP
            hits.sort(key=lambda w: (round(w[1] / 3), w[0]))    # reading order: line then x
            desc = " ".join(w[4] for w in hits).strip()
            if desc:
                a["/Contents"] = pikepdf.String(desc)
                restored += 1
    if restored:
        doc.save(str(pdf))
    return restored


def _undescribed(pdf: Path) -> int:
    doc = pikepdf.open(str(pdf))
    return sum(1 for pg in doc.pages for a in pg.get("/Annots", [])
               if a.get("/Subtype") == "/Link" and not a.get("/Contents"))


def _selftest() -> int:
    """⟨P, F, δ⟩ — build a 1-page PDF with an undescribed link over 'see Figure', then:
      P: after describe_links, that link carries /Contents and 0 undescribed remain.
      F: the CENTRE rule (sre's bug) on two adjacent links leaves one bare; OVERLAP describes both.
      δ: overlap-vs-centre selection — one link that is bare under centre carries /Contents here."""
    import tempfile
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    with tempfile.TemporaryDirectory() as d:
        dd = Path(d)
        # A minimal tagged-ish PDF via pikepdf: one page, two words, two link annots (one over each
        # word) with NO /Contents.  We assert the OVERLAP rule describes both, and that the CENTRE
        # rule (a straddling extracted word) would leave one bare.
        pdf = dd / "fix.pdf"
        _make_fixture(pdf)
        before = _undescribed(pdf)
        # centre-rule reference (the bug): a word whose centre is outside both rects → 0 described
        centre_desc = _describe_by_centre(pdf)
        n = describe_links(pdf)                              # the overlap rule (the fix)
        after = _undescribed(pdf)
        check("fixture starts with undescribed links", before >= 1)
        check("P: overlap rule describes every undescribed link (0 remain)", after == 0 and n >= 1)
        check("F: the centre rule leaves at least one bare (sre's half-description bug)",
              centre_desc < n)
        check("δ: overlap describes strictly more than centre", n > centre_desc)

    if fails:
        print(f"LINKALT SELFTEST: FAIL ({len(fails)})")
        return 1
    print("LINKALT SELFTEST: PASS")
    return 0


def _make_fixture(pdf: Path) -> None:
    """A 1-page PDF reproducing sre's adjacent-citation trap: ONE tightly-set token '[1][2]' that
    pdftotext extracts as a SINGLE word, covered by TWO adjacent link annots (one over its left
    half, one over its right), both with empty /Contents.  The single word's CENTRE lies inside
    only ONE rect (or neither, if split at the seam), so the centre rule describes at most one link
    while the OVERLAP rule — the word box intersects BOTH rects — describes both."""
    doc = pikepdf.Pdf.new()
    page = doc.add_blank_page(page_size=(200, 100))
    # one contiguous token, no space, so pdftotext yields a single <word> spanning both links
    stream = b"BT /F1 12 Tf 20 50 Td ([1][2]) Tj ET"
    page.Contents = doc.make_stream(stream)
    page.Resources = pikepdf.Dictionary(
        Font=pikepdf.Dictionary(F1=pikepdf.Dictionary(
            Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica)))
    # the token '[1][2]' renders ~from x=20 to x=54 at 12pt; two links split it at the seam (~x=37),
    # so the extracted word's centre (~x=37) lies at the boundary — inside at most one rect.
    a1 = pikepdf.Dictionary(Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Link,
                            Rect=pikepdf.Array([20, 48, 37, 64]), Border=pikepdf.Array([0, 0, 0]))
    a2 = pikepdf.Dictionary(Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Link,
                            Rect=pikepdf.Array([37, 48, 54, 64]), Border=pikepdf.Array([0, 0, 0]))
    page.Annots = pikepdf.Array([doc.make_indirect(a1), doc.make_indirect(a2)])
    doc.save(str(pdf))


def _describe_by_centre(pdf: Path) -> int:
    """The sre-bug reference: select a word only if its CENTRE lies inside the rect.  A word that
    extracts as one token straddling two links has a centre in neither → described by neither.
    Returns the count that WOULD be described (does not save)."""
    words = _words(pdf)
    doc = pikepdf.open(str(pdf))
    n = 0
    for i, page in enumerate(doc.pages):
        ph = float(page.MediaBox[3]) - float(page.MediaBox[1])
        ws = words[i] if i < len(words) else []
        for a in page.get("/Annots", []):
            if a.get("/Subtype") != "/Link" or a.get("/Contents"):
                continue
            r = [float(x) for x in a["/Rect"]]
            rx0, rx1 = min(r[0], r[2]), max(r[0], r[2])
            ry0, ry1 = ph - max(r[1], r[3]), ph - min(r[1], r[3])
            hit = [w for w in ws
                   if rx0 <= (w[0] + w[2]) / 2 <= rx1 and ry0 <= (w[1] + w[3]) / 2 <= ry1]
            if hit:
                n += 1
    return n


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--selftest":
        return _selftest()
    if not argv:
        print("usage: linkalt.py DELIVERABLE.pdf | --selftest", file=sys.stderr)
        return 2
    pdf = Path(argv[0])
    if not pdf.exists():
        print(f"linkalt: PDF not found at {pdf} — build the deliverable first", file=sys.stderr)
        return 1
    n = describe_links(pdf)
    left = _undescribed(pdf)
    print(f"linkalt: described {n} link(s); {left} undescribed remain")
    if left:
        print("linkalt: FAIL — a link covering visible text is still undescribed", file=sys.stderr)
        return 1
    print("linkalt: ok — every link annotation carries a description (PDF/UA 7.18.1, 7.18.5)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
