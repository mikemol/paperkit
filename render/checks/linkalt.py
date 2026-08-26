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

try:
    import pikepdf
except ImportError:                          # Ζ·tier·exit — pikepdf absent is CANNOT-RUN (exit 3, guarded
    pikepdf = None                           # in main), not an uncaught ImportError read as a failure


def _words_by_page(pdf: Path) -> dict[int, list[tuple[float, float, float, float, str]]]:
    """{1-based page: [(x0,y0,x1,y1,word)]} in PDF coordinates (y-up, bottom origin).
    The page height comes from each `<page height=...>` element — pdftotext measures from the top,
    PDF annotations from the bottom, so each word is flipped through its own page's height."""
    xml = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"],
                         capture_output=True, text=True).stdout
    out: dict[int, list[tuple[float, float, float, float, str]]] = {}
    page = 0
    for chunk in xml.split("<page")[1:]:
        page += 1
        h = re.match(r'[^>]*height="([\d.]+)"', chunk)
        if not h:
            continue
        height = float(h.group(1))
        ws: list[tuple[float, float, float, float, str]] = []
        for m in re.finditer(
                r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>',
                chunk):
            x0, y0, x1, y1 = (float(g) for g in m.groups()[:4])
            ws.append((x0, height - y1, x1, height - y0, m.group(5)))   # top-down → bottom-up
        out[page] = ws
    return out


def uninformative(pdf: Path) -> list:
    """Ρ·render·alt·audit — links whose description is PRESENT but says nothing.

    The defect class, found on the slide route and audited back here: a presence test passes a
    useless description.  `describe_links` writes the literal "link" when no visible text falls
    under the annotation — PDF/UA requires *a* description, so that is the honest floor — but the
    exit condition counted such a link as DESCRIBED, so a deliverable could satisfy "0 undescribed
    remain" while announcing "link, link, link" to a screen reader.

    This names them instead of hiding them: the count is reported beside the described count, so a
    deliverable states how much of its link description is real.  It is deliberately a REPORT and
    not a hard failure — a link over a figure genuinely has no words under it, and failing the
    build for an honest floor would be measuring the wrong thing.  What was wrong was the silence.
    """
    out = []
    with pikepdf.open(str(pdf)) as doc:
        for i, page in enumerate(doc.pages, 1):
            for a in (page.get("/Annots") or []):
                if a.get("/Subtype") == "/Link":
                    c = str(a.get("/Contents") or "").strip()
                    # ONE owner for "is this description thin": _is_marker.  This branch used to
                    # carry its own copy (link-literal or under two tokens), which disagreed with
                    # it — a URI counted as thin here and as a real description there, so the two
                    # sides of the same question gave different answers.
                    if c and (c.lower() == "link" or _is_marker(c)):
                        out.append((i, c))
    return out


def _is_marker(text: str) -> bool:
    """A description that is a bare reference MARKER — a digit, a bracketed number, a single
    token — rather than words.  These are what a footnote or citation link covers, and they carry
    no information out of context."""
    t = text.strip().strip("[]()")
    # A URI is a DESCRIPTION, not a marker: "https://doi.org/10.1145/3236774" is one token and
    # says exactly where the link goes, which is what a description is for.  Measured on the latex
    # route, whose external links are bare DOIs — flagging them would have called a perfectly good
    # description thin, the same measure-the-wrong-thing error as counting a table thumbnail.
    if re.match(r"^(https?|mailto|doi):", t, re.I) or t.startswith("www."):
        return False
    if t.isdigit() or len(t.split()) < 2:
        return True
    # A trailing bare number with at most one leading word is still a marker: the overlap rule
    # catches the word ADJACENT to a footnote reference, so "and 5" or "build 2" arrives looking
    # like prose while carrying no more information than "5" did.  Measured: 8 of 19 links on the
    # real deliverable took this shape once the digit-only case was fixed.
    parts = t.split()
    return len(parts) <= 2 and parts[-1].strip("[]().,").isdigit()


def _destination_hint(annot) -> str:
    """What KIND of thing a link points at, from its own destination — so a marker-only link can
    say "footnote 1" rather than "1".  Read from the annotation, never guessed: an internal
    destination is a note or section within the document, an external URI names its host."""
    try:
        act = annot.get("/A")
        if act is not None and act.get("/URI") is not None:
            uri = str(act.get("/URI"))
            host = uri.split("//")[-1].split("/")[0]
            return f"link to {host}" if host else "external link"
    except Exception:
        pass
    # "note" plus a digit is two tokens, which _is_marker rejects — correctly, and the
    # disagreement was mine: an expansion must clear the SAME bar it applies.  The LaTeX route,
    # whose links lualatex describes natively, sets the standard to match ("Go to destination
    # footnote*.1"): say what the target IS and where it goes, in words.
    return "go to footnote"


def describe_links(pdf: Path) -> int:
    """Give EVERY undescribed `/Link` a `/Contents`: the words whose box OVERLAPS its rect by at
    least half a word's width (so a text extractor that merges two adjacent links into one word,
    whose centre lies in neither rect, still describes both), joined; a link with no text under it
    gets the literal "link" (PDF/UA requires a description on every link, even an empty target).
    Saves in place.  Returns the count described from their OWN text (excludes the "link" fallback).

    Vendored from sre-troubleshooting's linkalt.py (summit floor, ask-adopt-pdfua-render-workarounds)
    — the authoritative method, preserved before that tree is retired."""
    words = _words_by_page(pdf)
    doc = pikepdf.open(str(pdf), allow_overwriting_input=True)
    filled = 0
    for pno, page in enumerate(doc.pages, 1):
        for a in page.get("/Annots", []):
            if a.get("/Subtype") != "/Link":
                continue
            # An EXISTING description is left alone — overwriting real prose would be worse than
            # the gap.  But a description that is a bare MARKER is not left alone: the office
            # export sets /Contents to the reference glyph itself ("1", "2"), so skipping every
            # already-described link meant the marker expansion never ran on the real deliverable
            # at all.  Measured: 18 of 19 links kept their bare digit until this exception existed.
            existing = a.get("/Contents")
            if existing is not None and not _is_marker(str(existing)):
                continue
            r = [float(v) for v in a["/Rect"]]
            x0, y0, x1, y1 = min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3])
            hit = []
            for wx0, wy0, wx1, wy1, w in words.get(pno, []):
                ox = min(x1, wx1) - max(x0, wx0)
                oy = min(y1, wy1) - max(y0, wy0)
                if ox > 0 and oy > 0 and ox >= 0.5 * min(x1 - x0, wx1 - wx0):   # ≥ half a word wide
                    hit.append(w)
            text = " ".join(hit).strip()
            # Ρ·render·alt·measure — a link whose own text is a bare MARKER describes nothing.
            # Measured on the real deliverable: 18 of 19 links carried a single digit ("1", "2", …)
            # because a footnote reference covers only its marker glyph, so a screen reader
            # announced "link, one".  The check said "0 undescribed remain" and was correct — the
            # description was present and useless, the same presence-for-meaning failure found on
            # the slide route.  So a marker-only description is EXPANDED with what it points at:
            # the link's own words stay, prefixed by the kind of destination they lead to.
            if text and _is_marker(text):
                text = f"{_destination_hint(a)} {text}".strip()
            if text:
                a["/Contents"] = pikepdf.String(text)
                filled += 1
            else:
                a["/Contents"] = pikepdf.String("link")        # never leave a link undescribed
    doc.save(str(pdf))
    return filled


def _undescribed(pdf: Path) -> int:
    doc = pikepdf.open(str(pdf))
    return sum(1 for pg in doc.pages for a in pg.get("/Annots", [])
               if a.get("/Subtype") == "/Link" and a.get("/Contents") is None)


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

        # ── the MARKER-DESCRIBED arm (Ρ·render·alt·fixture) ──────────────────────────────────
        # The arms above build links with NO /Contents — a state the real pipeline never presents.
        # LibreOffice's PDF/UA export always sets /Contents, to the reference GLYPH itself, so a
        # fixture of bare links let describe_links' already-described skip pass the selftest while
        # 18 of 19 links on the actual deliverable kept a bare digit.  The verification method, not
        # only the code, produced the false result: a fixture that cannot exhibit the shipping
        # condition cannot witness the shipping bug.
        mk = dd / "marker.pdf"
        _make_fixture(mk)
        with pikepdf.open(str(mk), allow_overwriting_input=True) as doc:
            for a in doc.pages[0].get("/Annots", []):
                a["/Contents"] = pikepdf.String("1")          # what the office export writes
            doc.save(str(mk))
        pre_thin = len(uninformative(mk))
        describe_links(mk)
        post_thin = len(uninformative(mk))
        check("P(marker): a link already described by its own GLYPH is expanded, not skipped",
              pre_thin >= 1 and post_thin == 0)
        # and the guard that keeps it honest: REAL prose is never overwritten.
        pr = dd / "prose.pdf"
        _make_fixture(pr)
        with pikepdf.open(str(pr), allow_overwriting_input=True) as doc:
            for a in doc.pages[0].get("/Annots", []):
                a["/Contents"] = pikepdf.String("see the adequacy section for the full ladder")
            doc.save(str(pr))
        describe_links(pr)
        with pikepdf.open(str(pr)) as doc:
            kept = all("adequacy" in str(a.get("/Contents") or "")
                       for a in doc.pages[0].get("/Annots", []))
        check("F(marker): an existing PROSE description is left alone, never overwritten", kept)

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
    words = _words_by_page(pdf)
    doc = pikepdf.open(str(pdf))
    n = 0
    for pno, page in enumerate(doc.pages, 1):
        for a in page.get("/Annots", []):
            if a.get("/Subtype") != "/Link" or a.get("/Contents") is not None:
                continue
            r = [float(v) for v in a["/Rect"]]
            x0, y0, x1, y1 = min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3])
            hit = [w for w in words.get(pno, [])
                   if x0 <= (w[0] + w[2]) / 2 <= x1 and y0 <= (w[1] + w[3]) / 2 <= y1]
            if hit:
                n += 1
    return n


def main(argv: list[str]) -> int:
    if pikepdf is None:                      # Ζ·tier·exit — the toolchain (pikepdf) is absent here
        print("linkalt: pikepdf absent — CANNOT VERIFY link descriptions (not a pass)", file=sys.stderr)
        return 3
    if argv and argv[0] == "--selftest":
        return _selftest()
    if not argv:
        print("usage: linkalt.py DELIVERABLE.pdf | --selftest", file=sys.stderr)
        return 3
    pdf = Path(argv[0])
    if not pdf.exists():
        print(f"linkalt: PDF not found at {pdf} — build the deliverable first", file=sys.stderr)
        return 1
    n = describe_links(pdf)
    left = _undescribed(pdf)
    thin = uninformative(pdf)
    print(f"linkalt: described {n} link(s); {left} undescribed remain; "
          f"{len(thin)} carry an UNINFORMATIVE description (the \"link\" floor or a single "
          f"token) — present, but announcing little to a screen reader")
    if left:
        print("linkalt: FAIL — a link covering visible text is still undescribed", file=sys.stderr)
        return 1
    print("linkalt: ok — every link annotation carries a description (PDF/UA 7.18.1, 7.18.5)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
