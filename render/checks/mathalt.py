#!/usr/bin/env python3
r"""Ρ·render·mathalt — give every equation an alternate description, so the math is accessible.

PDF/UA-1 clause 7.7 (mathematical expressions) requires every formula to carry a text alternative:
a screen reader that reaches an untagged `/Formula` announces nothing.  LibreOffice's PDF/UA export
TAGS each equation as a `/Formula` structure element (good) but sets no `/Alt` on it (the 7.7 gap) —
so native OMML transports the equation faithfully to the eye and to Word, but not to a screen reader.

The math's own source IS its accessible form (mat230's doctrine: luamml emits a MathML alternative
per formula; on the office route the equation's LaTeX is the recoverable structure).  This reads the
paper's inline-math spans in document order and writes each, verbatim, as the `/Alt` of the
corresponding `/Formula` element — pandoc emits equations in source order and the struct tree
preserves it, so the Nth formula gets the Nth equation.  A count mismatch is reported LOUD (never a
silent partial description).

    python3 checks/mathalt.py DELIVERABLE.pdf EQ1 EQ2 …   # set /Alt on each /Formula in order
    describe_formulas(pdf, alts) -> int                   # the API pdf.py calls
    python3 checks/mathalt.py --selftest                  # ⟨P,F,δ⟩
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import pikepdf
except ImportError:                          # Ζ·tier·exit — pikepdf absent is CANNOT-RUN (exit 3, guarded
    pikepdf = None                           # in main), not an uncaught ImportError read as a failure

_MATH_SPAN = re.compile(r"(?<!\\)\$(?!\$)([^$]+?)\$|\$\$(.+?)\$\$", re.S)


def paper_equations(paper_md: Path) -> list[str]:
    """The inline- and display-math spans of paper.md, in document order, as readable alt text
    (the LaTeX source with its delimiters stripped and whitespace collapsed).
    """
    text = paper_md.read_text()
    out = []
    for m in _MATH_SPAN.finditer(text):
        eq = (m.group(1) or m.group(2) or "").strip()
        if eq:
            out.append(re.sub(r"\s+", " ", eq))
    return out


def _formulas(doc: pikepdf.Pdf) -> list:
    """Every `/Formula` structure element in the struct tree, in traversal (document) order."""
    found = []

    def walk(node, depth=0):
        if depth > 12 or not isinstance(node, pikepdf.Dictionary):
            return
        if str(node.get("/S")) == "/Formula":
            found.append(node)
        k = node.get("/K")
        if k is not None:
            items = k if isinstance(k, pikepdf.Array) else [k]
            for it in items:
                if isinstance(it, pikepdf.Dictionary):
                    walk(it, depth + 1)

    root = doc.Root.get("/StructTreeRoot")
    if root is not None:
        walk(root)
    return found


def describe_formulas(pdf: Path, alts: list[str]) -> int:
    """Set `/Alt` on each `/Formula` element from `alts` (positional).  Saves in place.  Returns
    the count described.  Raises if the counts disagree — a formula with no alt fails 7.7, and an
    alt with no formula means the positional match slipped, either way a LOUD failure not a silent
    partial.
    """
    doc = pikepdf.open(str(pdf), allow_overwriting_input=True)
    formulas = _formulas(doc)
    if len(formulas) != len(alts):
        raise SystemExit(
            f"mathalt: {len(formulas)} /Formula element(s) but {len(alts)} equation(s) — the "
            "positional match cannot be trusted; refusing to describe (7.7 would be left partial)")
    for elem, alt in zip(formulas, alts):
        elem["/Alt"] = pikepdf.String(alt)
    doc.save(str(pdf))
    return len(formulas)


def _undescribed(pdf: Path) -> int:
    doc = pikepdf.open(str(pdf))
    return sum(1 for f in _formulas(doc) if f.get("/Alt") is None)


def _selftest() -> int:
    """⟨P, F, δ⟩ — a PDF with a /Formula element carrying no /Alt:
    P: after describe_formulas, the /Formula carries the equation as /Alt, 0 undescribed remain.
    F: a count mismatch (2 formulas, 1 alt) raises rather than describing a partial set.
    δ: whether the /Formula has an /Alt — the exact bit clause 7.7 checks.
    """
    import tempfile
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    with tempfile.TemporaryDirectory() as d:
        dd = Path(d)
        # a minimal tagged PDF with two /Formula structure elements, no /Alt
        pdf = dd / "fix.pdf"
        _make_fixture(pdf)
        before = _undescribed(pdf)
        check("fixture starts with undescribed /Formula elements", before == 2)

        # F: a count mismatch refuses
        raised = False
        try:
            describe_formulas(pdf, ["only one alt"])
        except SystemExit:
            raised = True
        check("F: a count mismatch (2 formulas, 1 alt) raises, describes nothing", raised)
        check("F: nothing was described on the mismatch (still 2 undescribed)",
              _undescribed(pdf) == 2)

        # P: matched counts describe both
        n = describe_formulas(pdf, [r"a = b", r"x + y"])
        check("P: matched alts describe every /Formula (0 undescribed remain)",
              n == 2 and _undescribed(pdf) == 0)
        # the alt text landed verbatim
        doc = pikepdf.open(str(pdf))
        alts = [str(f.get("/Alt")) for f in _formulas(doc)]
        check("δ: the /Alt carries the equation (the bit 7.7 checks)", alts == ["a = b", "x + y"])

        # paper_equations extracts inline + display math in order
        (dd / "p.md").write_text("text $a+b$ and $$\\frac{c}{d}$$ done\n")
        eqs = paper_equations(dd / "p.md")
        check("paper_equations reads inline and display math in document order",
              eqs == ["a+b", r"\frac{c}{d}"])

    if fails:
        print(f"MATHALT SELFTEST: FAIL ({len(fails)})")
        return 1
    print("MATHALT SELFTEST: PASS")
    return 0


def _make_fixture(pdf: Path) -> None:
    """A 1-page tagged PDF whose struct tree has two /Formula elements, neither carrying /Alt."""
    doc = pikepdf.Pdf.new()
    page = doc.add_blank_page(page_size=(200, 100))
    page.Contents = doc.make_stream(b"BT /F1 12 Tf 20 50 Td (eq) Tj ET")
    page.Resources = pikepdf.Dictionary(
        Font=pikepdf.Dictionary(F1=pikepdf.Dictionary(
            Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica)))
    f1 = doc.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name("/Formula")))
    f2 = doc.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name("/Formula")))
    root = doc.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name.StructTreeRoot, K=pikepdf.Array([f1, f2])))
    doc.Root.StructTreeRoot = root
    doc.save(str(pdf))


def main(argv: list[str]) -> int:
    if pikepdf is None:                      # Ζ·tier·exit — the toolchain (pikepdf) is absent here
        print("mathalt: pikepdf absent — CANNOT VERIFY the /Formula alt text (not a pass)", file=sys.stderr)
        return 3
    if argv and argv[0] == "--selftest":
        return _selftest()
    if len(argv) < 1:
        print("usage: mathalt.py DELIVERABLE.pdf EQ1 EQ2 … | --selftest", file=sys.stderr)
        return 3
    pdf, alts = Path(argv[0]), argv[1:]
    if not pdf.exists():
        print(f"mathalt: PDF not found at {pdf}", file=sys.stderr)
        return 1
    n = describe_formulas(pdf, alts)
    left = _undescribed(pdf)
    print(f"mathalt: described {n} formula(s); {left} undescribed remain")
    if left:
        print("mathalt: FAIL — a /Formula element still carries no /Alt (PDF/UA 7.7)", file=sys.stderr)
        return 1
    print("mathalt: ok — every equation carries a text alternative (PDF/UA 7.7)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
