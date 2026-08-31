#!/usr/bin/env python3
"""Ρ·render·ocr — VISUAL fidelity: what the EYE sees, recovered by OCR, must be the paper.

Render the paper to PDF, RASTERIZE to images, and OCR them.  This catches a glyph that maps
correctly in the TEXT layer (pdftotext, Ρ·render·integrity) but renders as a box — the two
checks are different subjects, and only this one reads pixels.

Robust by construction: a font or render regression that turned the body to tofu would crater
recovery.  Measured, a faithful render recovers ~100% of the body words, so the 90% floor is
well below the signal and well above noise.  cwd = render/ ; .. = repo root.

⚑ Ζ·witness·component — the body was module-level, so importing this file ran a full render,
rasterize and OCR pass.  It is now a callable; `lo` is reached by declaration.

⚑⚑ The `re` narrowing is local, and duplicated — see fig_legible.py for the reason: the shared
seam (`paperkit/rematch.py`) is unreachable from a witness until `Ζ·runner·venv` lands.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

WORD = re.compile(r"[a-z]{4,}")
FLOOR = 0.90
DPI = "150"


def _words(text: str) -> set[str]:
    """Collect the distinct 4+ letter lowercase words in `text`."""
    found: list[str] = WORD.findall(text.lower())
    return set(found)


def _ocr_pages(pdf: Path, d: Path) -> str:
    """Rasterize `pdf` and return the concatenated OCR text of every page."""
    subprocess.run(["pdftoppm", "-r", DPI, "-png", str(pdf), str(d / "page")],
                   check=True, timeout=120)
    out = ""
    for png in sorted(d.glob("page*.png")):
        r = subprocess.run(["tesseract", str(png), "-"],
                           capture_output=True, text=True, timeout=120, check=False)
        out += r.stdout.lower()
    return out


def check() -> int:
    """Return 0 iff OCR recovers at least the floor share of the paper's words."""
    from . import lo

    want = sorted(_words(Path("../paper/paper.md").read_text()))
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        docx = d / "p.docx"
        subprocess.run(["pandoc", "../paper/paper.md", "-o", str(docx)],
                       check=True)
        pdf = lo.convert(docx, "pdf", d)
        if pdf is None:
            sys.stderr.write("docx did not convert to a PDF (soffice produced no output)\n")
            return 1
        seen = _words(_ocr_pages(pdf, d))
    rate = sum(w in seen for w in want) / len(want)
    if rate < FLOOR:
        sys.stderr.write(f"OCR recovered only {rate:.0%} of the paper's words from the rendered "
                         f"pixels — visual fidelity broken (tofu?)\n")
        return 1
    sys.stdout.write(f"ocr ok: {rate:.0%} of {len(want)} body words OCR-recovered from the "
                     f"rendered pixels — visually legible\n")
    return 0


if __name__ == "__main__":
    if __package__:
        raise SystemExit(check())
    import runpy

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    runpy.run_module("render.checks.ocr", run_name="__main__", alter_sys=True)
