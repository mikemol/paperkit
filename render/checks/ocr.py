#!/usr/bin/env python3
# Ρ·render·ocr — VISUAL fidelity: render the paper to PDF, RASTERIZE to images, and OCR them.
# The text the EYE sees (the pixels), recovered by OCR, must be the paper — catching a glyph
# that maps right in the TEXT layer (pdftotext, ·integrity) but renders as a box.  Robust by
# construction: a font/render regression that turned the body to tofu would crater recovery
# (measured: a faithful render recovers ~100% of the body words).  cwd = render/ ; .. = repo.
import re, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lo   # office convert: isolated profile + unlink-first, so an absence is loud (Ρ·render·provenance)

words = sorted(set(re.findall(r'[a-z]{4,}', Path("../paper/paper.md").read_text().lower())))
with tempfile.TemporaryDirectory() as d:
    docx = Path(d) / "p.docx"
    subprocess.run(["pandoc", "../paper/paper.md", "-o", str(docx)], check=True)
    pdf = lo.convert(docx, "pdf", d)
    assert pdf is not None, "docx did not convert to a PDF (soffice produced no output)"
    subprocess.run(["pdftoppm", "-r", "150", "-png", str(pdf), str(Path(d) / "page")], check=True, timeout=120)
    ocr = ""
    for png in sorted(Path(d).glob("page*.png")):
        ocr += subprocess.run(["tesseract", str(png), "-"], capture_output=True, text=True, timeout=120).stdout.lower()
    seen = set(re.findall(r'[a-z]{4,}', ocr))
    rate = sum(w in seen for w in words) / len(words)
    assert rate >= 0.90, f"OCR recovered only {rate:.0%} of the paper's words from the rendered pixels — visual fidelity broken (tofu?)"
print(f"ocr ok: {rate:.0%} of {len(words)} body words OCR-recovered from the rendered pixels — visually legible")
