#!/usr/bin/env python3
"""Ρ·render·integrity (fidelity) — the READER's view of the PDF is faithful to the paper.

Render the .docx all the way to a PDF (libreoffice) and confirm that every non-ASCII glyph the
paper uses survives into the PDF TEXT LAYER (no missing-glyph tofu), and that every heading is
present there.  What the consumer copies, searches, or hears via a screen reader is the paper.
cwd = render/.

⚑ Ζ·witness·component — the body was module-level, so importing this file rendered a document.
It is now a callable; `lo` is reached by declaration rather than a sys.path mutation.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ASCII_MAX = 127
HEADING = re.compile(r"^#{1,6}\s")


def _wanted(src: str) -> tuple[list[str], list[str]]:
    """Collect the non-ASCII glyphs and the headings the rendered PDF must carry."""
    glyphs = sorted({c for c in src if ord(c) > ASCII_MAX})
    heads = [re.sub(r"^#{1,6}\s+", "", ln).rstrip()
             for ln in src.splitlines() if HEADING.match(ln)]
    return glyphs, heads


def check() -> int:
    """Return 0 iff every glyph and heading survives into the PDF text layer."""
    from . import lo

    src = Path("../paper/paper.md").read_text()
    glyphs, heads = _wanted(src)
    with tempfile.TemporaryDirectory() as d:
        docx, txt = Path(d) / "p.docx", Path(d) / "p.txt"
        subprocess.run(["pandoc", "../paper/paper.md", "-o", str(docx)],
                       check=True)
        pdf = lo.convert(docx, "pdf", d)
        if pdf is None:
            sys.stderr.write("docx did not convert to a PDF (soffice produced no output)\n")
            return 1
        subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)],
                       check=True)
        rendered = txt.read_text()
        norm = " ".join(rendered.split())
        lost = [g for g in glyphs if g not in rendered]
        if lost:
            sys.stderr.write(f"glyphs lost to tofu in the rendered PDF: {lost!r}\n")
            return 1
        absent = [h for h in heads if h and " ".join(h.split()) not in norm]
        if absent:
            sys.stderr.write(f"section headings absent from the PDF text layer: {absent}\n")
            return 1
    sys.stdout.write(f"fidelity ok: glyphs {glyphs} + all {len(heads)} headings "
                     f"survive to the PDF text layer\n")
    return 0


if __name__ == "__main__":
    if __package__:
        raise SystemExit(check())
    import runpy

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    runpy.run_module("render.checks.fidelity", run_name="__main__", alter_sys=True)
