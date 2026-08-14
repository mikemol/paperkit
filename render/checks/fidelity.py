#!/usr/bin/env python3
# Ρ·render·integrity (fidelity) — render the .docx all the way to a PDF (libreoffice) and
# confirm the READER's view is faithful: every non-ASCII glyph the paper uses survives into
# the PDF text layer (no missing-glyph tofu), and every heading is present there.  What the
# consumer copies / searches / hears via a screen reader is the paper.  cwd = render/.
import re, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lo   # office convert: isolated profile + unlink-first, so an absence is loud (Ρ·render·provenance)

src = Path("../paper/paper.md").read_text()
glyphs = sorted({c for c in src if ord(c) > 127})
heads = [re.sub(r'^#{1,6}\s+', '', ln).rstrip() for ln in src.splitlines() if re.match(r'^#{1,6}\s', ln)]
with tempfile.TemporaryDirectory() as d:
    docx, txt = Path(d) / "p.docx", Path(d) / "p.txt"
    subprocess.run(["pandoc", "../paper/paper.md", "-o", str(docx)], check=True)
    pdf = lo.convert(docx, "pdf", d)
    assert pdf is not None, "docx did not convert to a PDF (soffice produced no output)"
    subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=True)
    rendered = txt.read_text()
    norm = " ".join(rendered.split())
    lost = [g for g in glyphs if g not in rendered]
    assert not lost, f"glyphs lost to tofu in the rendered PDF: {lost!r}"
    absent = [h for h in heads if h and " ".join(h.split()) not in norm]
    assert not absent, f"section headings absent from the PDF text layer: {absent}"
print(f"fidelity ok: glyphs {glyphs} + all {len(heads)} headings survive to the PDF text layer")
