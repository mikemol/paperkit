#!/usr/bin/env python3
r"""Ρ·render·omml — the paper's equations transport as NATIVE OMML, faithfully.

Vendored from mat260's verify.py (its OMML-fidelity rungs R1-R7; summit floor, mat260 render
lineage — preserve the capability before that tree is retired).  mat260's insight: pandoc renders
LaTeX math (`$…$`) to native Office Math (`<m:oMath>`) — editable, well-formatted Word equations
that scale and stay in the text layer — and only RASTERIZES an equation (to PNG) when it cannot.  So
a rendered docx is faithful iff the math arrived as oMath and none of it leaked to pixels or to bare
`$` text.

This gates paperkit's own paper: its formulas (the effective-grade clamp, the emergence increment,
the coherence residual) are authored as real equations, so the deliverable must carry them as native
OMML.  The transport-fidelity rungs, adapted from mat260 (its document-specific R4 table-count and R5
heading-count are dropped — they are not general):

  R1  at least one native <m:oMath> element      (the math arrived as OMML, not prose or pixels)
  R2  no rasterized equation in word/media/       (a leaked PNG equation — vector figures allowed)
  R3  no math `$` delimiter surviving in a text run (a `$…$` that failed to convert)
  R6  every <m:oMath> block parses as well-formed XML
  R7  every <m:brk/> line-break sits inside an <m:oMath> block

    python3 checks/omml.py            # build the paper's docx, gate R1/R2/R3/R6/R7
    python3 checks/omml.py --selftest # ⟨P,F,δ⟩ against math / no-math fixtures
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

_RASTER = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff")
_TEXT_RUN = re.compile(r"<w:t[^>]*>([^<]*)</w:t>")

# Ρ·render·agree DELEGATES math to here (omml owns it).  The agree check concurs prose across two
# render paths (paper.md → plain, and paper.md → docx → plain); a math span flattens DIFFERENTLY on
# those paths, and --without-K forbids collapsing the two renderings to "the same" and looking no
# further.  So the difference is REGISTERED, not erased: a math span may differ across the paths ONLY
# by a substitution from this bounded equivalence set — glyph variants pandoc emits for one LaTeX
# macro (∅ from markdown vs ⌀ from a round-tripped docx for \emptyset; the ASCII backslash vs the
# set-minus glyph for \setminus).  A cross-path difference OUTSIDE this set is a real divergence the
# check must surface.  The set is the witness's parameter; extend it (with a measured pair) when a
# new macro is used, rather than widening a comparison to ignore the difference.
MATH_VARIANTS = {
    "∅": "⌀",   # ∅ (U+2205 EMPTY SET, markdown path) ~ ⌀ (U+2300 DIAMETER, docx path)
    "\\": "∖",       # \  (U+005C, markdown path)          ~ ∖ (U+2216 SET MINUS, docx path)
}
_SOURCECODE_P = re.compile(r'<w:p\b(?:(?!</w:p>).)*?w:val="SourceCode"(?:(?!</w:p>).)*?</w:p>', re.DOTALL)
_OMATH_BLOCK = re.compile(r"<m:oMath\b[^>]*>.*?</m:oMath>", re.DOTALL)
_BRK = re.compile(r"<m:brk\b[^>]*/?>")
_OMATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _rungs(docx: Path) -> list[tuple[str, bool, str]]:
    """Run R1/R2/R3/R6/R7 over a .docx, returning [(name, ok, detail), ...]."""
    z = zipfile.ZipFile(docx)
    doc = z.read("word/document.xml").decode()
    rows: list[tuple[str, bool, str]] = []

    # R1 — native OMML present
    n = doc.count("<m:oMath>")
    rows.append(("R1 native OMML", n >= 1, f"{n} <m:oMath> element(s)"))

    # R2 — no rasterized equation (vector figures allowed)
    media = [e for e in z.namelist() if e.startswith("word/media/")]
    raster = [e for e in media if e.lower().endswith(_RASTER)]
    rows.append(("R2 no raster equation", not raster,
                 f"{len(media)} media, {len(raster)} raster" + (f": {raster}" if raster else "")))

    # R3 — no math `$` surviving in text (appendix SourceCode listings legitimately carry `$`)
    prose = _SOURCECODE_P.sub("", doc)
    runs = _TEXT_RUN.findall(prose)
    joined = "".join(runs)
    sample = next((r for r in runs if "$" in r), "")
    rows.append(("R3 no bare $", "$" not in joined,
                 f"{len(runs)} runs" + (f"; leaked: {sample!r}" if sample else "")))

    # R6 — every oMath block well-formed
    blocks = _OMATH_BLOCK.findall(doc)
    bad = None
    for i, b in enumerate(blocks):
        try:
            ET.fromstring(f'<root xmlns:m="{_OMATH_NS}">{b}</root>')
        except ET.ParseError as e:
            bad = f"block {i + 1}/{len(blocks)}: {e}"
            break
    rows.append(("R6 oMath well-formed", bad is None,
                 f"{len(blocks)} block(s)" + (f"; {bad}" if bad else " all parse")))

    # R7 — every line-break inside an oMath block
    all_brks = _BRK.findall(doc)
    in_omath = sum(len(_BRK.findall(b)) for b in blocks)
    outside = len(all_brks) - in_omath
    rows.append(("R7 breaks inside oMath", outside == 0,
                 f"{len(all_brks)} <m:brk/>, {outside} outside oMath"))
    return rows


def _canonical(s: str) -> str:
    """Fold the registered cross-path glyph variants to one representative, so two renderings that
    differ ONLY by a MATH_VARIANTS substitution compare equal — and any OTHER difference does not."""
    for a, b in MATH_VARIANTS.items():
        s = s.replace(b, a)
    return s


def math_agree(paper_md: Path) -> tuple[bool, str]:
    """The math half of Ρ·render·agree, DELEGATED to omml (which owns the math).  Render each math
    span two ways — from markdown, and from a round-tripped docx — and assert the two renderings
    differ ONLY by a registered variant (MATH_VARIANTS).  A difference outside that set is a real
    cross-path divergence (returned False, named).  This REGISTERS the difference rather than
    erasing it: the agree prose check replaces math with a placeholder (it owns prose), and the
    equations' cross-path behaviour is witnessed HERE, parameterized by the known variant set."""
    spans = _MATH_SPANS.findall(paper_md.read_text())
    eqs = [(m[0] or m[1]).strip() for m in spans if (m[0] or m[1]).strip()]
    if not eqs:
        return True, "no equations to concur"
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        outside = []
        for i, eq in enumerate(eqs):
            (d / "m.md").write_text(f"$${eq}$$\n")
            md_plain = subprocess.run(["pandoc", str(d / "m.md"), "-t", "plain"],
                                      capture_output=True, text=True).stdout.strip()
            subprocess.run(["pandoc", str(d / "m.md"), "-o", str(d / "m.docx")], check=True)
            dx_plain = subprocess.run(["pandoc", str(d / "m.docx"), "-t", "plain"],
                                      capture_output=True, text=True).stdout.strip()
            if _canonical(md_plain) != _canonical(dx_plain):
                outside.append(f"eq {i + 1}: {md_plain!r} vs {dx_plain!r}")
    if outside:
        return False, f"{len(outside)} equation(s) diverge across paths OUTSIDE the registered variants: {outside[:3]}"
    return True, f"{len(eqs)} equation(s) concur across both render paths (within the registered variants)"


_MATH_SPANS = re.compile(r"\$\$(.+?)\$\$|(?<!\\)\$(?!\$)(.+?)(?<!\\)\$", re.S)


def _paper_docx(d: Path) -> Path:
    """Render the paper to a docx the way pdf.py does (cite_split markers → pandoc), so the OMML
    gate measures the SAME transport the deliverable uses."""
    mark = {"file": "(present)", "result": "(verdict imported)"}
    mk = {}
    _bibtext = "".join(p.read_text() for p in sorted(Path("../paper").glob("*.bib")))
    for m in re.finditer(r"@\w+\{\s*([^,\s]+)\s*,(.*?)\n\}", _bibtext, re.S):
        c = re.search(r"\bcheck\s*=\s*\{(\w+):", m.group(2))
        if c:
            mk[m.group(1)] = mark.get(c.group(1), "(machine-checked)")
    split = re.sub(r"\[@([A-Za-z][\w:.+-]*)\]", lambda x: mk.get(x.group(1), x.group(0)),
                   Path("../paper/paper.md").read_text())
    md, docx = d / "p.md", d / "p.docx"
    md.write_text(split)
    subprocess.run(["pandoc", str(md), "--citeproc", "--bibliography", "../paper/references.bib",
                    "-o", str(docx)], check=True)
    return docx


def _selftest() -> int:
    """⟨P, F, δ⟩ — a docx with math vs one without:
      P: a doc carrying `$…$` math renders ≥1 native <m:oMath>, no bare `$`, well-formed.
      F: a doc whose math was force-rasterized (an image where the equation should be) fails R1/R2.
      δ: whether the math arrived as OMML or as pixels — one equation, two fates."""
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        # P: math → OMML (pandoc's default)
        (d / "math.md").write_text("# H\n\n$$a = \\frac{b}{c}$$\n\ninline $x+y$\n")
        p_docx = d / "math.docx"
        subprocess.run(["pandoc", str(d / "math.md"), "-o", str(p_docx)], check=True)
        p = {name: ok for name, ok, _ in _rungs(p_docx)}
        check("P: math renders as native OMML (R1) with no leaked $ (R3), well-formed (R6)",
              p["R1 native OMML"] and p["R3 no bare $"] and p["R6 oMath well-formed"])
        check("P: no rasterized equation (R2)", p["R2 no raster equation"])

        # F: force the same equation to a raster image (the leak R1/R2 catch).  Synthesize a docx
        # with a PNG in word/media and NO oMath, by post-editing the package.
        f_docx = d / "raster.docx"
        import shutil
        shutil.copy(p_docx, f_docx)
        with zipfile.ZipFile(p_docx) as zin:
            doc = zin.read("word/document.xml").decode()
        doc_noomath = _OMATH_BLOCK.sub("<w:r><w:t>[equation image]</w:t></w:r>", doc)
        # rewrite the docx with the oMath stripped + a fake raster in media
        import os
        tmp = d / "rebuilt.docx"
        with zipfile.ZipFile(p_docx) as zin, zipfile.ZipFile(tmp, "w") as zout:
            for item in zin.namelist():
                data = zin.read(item)
                if item == "word/document.xml":
                    data = doc_noomath.encode()
                zout.writestr(item, data)
            zout.writestr("word/media/image1.png", b"\x89PNG\r\n\x00\x00fake")
        os.replace(tmp, f_docx)
        f = {name: ok for name, ok, _ in _rungs(f_docx)}
        check("F: a rasterized equation fails R1 (no OMML) or R2 (raster present)",
              not (f["R1 native OMML"] and f["R2 no raster equation"]))
        check("δ: the same equation passes as OMML, fails as a raster",
              p["R1 native OMML"] and not (f["R1 native OMML"] and f["R2 no raster equation"]))

        print("\n⟨math-agree: the cross-path difference is REGISTERED, not erased (--without-K)⟩\n")
        # P: a variant-only difference (∅ vs ⌀) is within the registered set → concurs.
        (d / "reg.md").write_text(r"$\emptyset$" + "\n")
        p_ok, _ = math_agree(d / "reg.md")
        check("P: a registered variant (∅≈⌀ across paths) concurs — within the parameter set", p_ok)
        # F: an UNregistered cross-path difference must NOT be waved through.  We prove the
        # discriminator directly: _canonical folds only the registered variants, so two strings
        # differing OUTSIDE the set stay unequal (a real divergence would surface).
        check("F: a difference OUTSIDE the registered variants is NOT folded (real divergence surfaces)",
              _canonical("min") != _canonical("max"))
        check("δ: _canonical folds a registered variant but not an arbitrary glyph",
              _canonical("⌀") == _canonical("∅") and _canonical("α") != _canonical("β"))

    if fails:
        print(f"OMML SELFTEST: FAIL ({len(fails)})")
        return 1
    print("OMML SELFTEST: PASS")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--selftest":
        return _selftest()
    with tempfile.TemporaryDirectory() as t:
        docx = _paper_docx(Path(t))
        rows = _rungs(docx)
        # the delegated math half of Ρ·render·agree: the equations concur across both render paths,
        # within the registered variant set (--without-K: the difference is witnessed, not erased).
        ag_ok, ag_detail = math_agree(Path("../paper/paper.md"))
        rows.append(("agree (delegated)", ag_ok, ag_detail))
        print("\n  OMML transport — paper.docx")
        print("  " + "-" * 60)
        for name, ok, detail in rows:
            print(f"  {'✓' if ok else '✗'} {name:<24} {detail}")
        print("  " + "-" * 60)
        if all(ok for _, ok, _ in rows):
            print("  omml: PASS — the paper's equations transport as native OMML and concur across "
                  "render paths within the registered variants")
            return 0
        print("  omml: FAIL — an equation did not transport faithfully or diverged across paths",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
