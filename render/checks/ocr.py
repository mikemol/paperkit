#!/usr/bin/env python3
# Ρ·render·ocr — VISUAL fidelity: render the paper to PDF, RASTERIZE to images, and OCR them.
# The text the EYE sees (the pixels), recovered by OCR, must be the paper — catching a glyph
# that maps right in the TEXT layer (pdftotext, ·integrity) but renders as a box.  Robust by
# construction: a font/render regression that turned the body to tofu would crater recovery
# (measured: a faithful render recovers ~100% of the body words).  cwd = render/ ; .. = repo.
import re, subprocess, tempfile
from pathlib import Path

words = sorted(set(re.findall(r'[a-z]{4,}', Path("../paper/paper.md").read_text().lower())))
with tempfile.TemporaryDirectory() as d:
    docx, pdf = Path(d) / "p.docx", Path(d) / "p.pdf"
    subprocess.run(["pandoc", "../paper/paper.md", "-o", str(docx)], check=True)
    subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", d, str(docx),
                    f"-env:UserInstallation=file://{d}/lo"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    subprocess.run(["pdftoppm", "-r", "150", "-png", str(pdf), str(Path(d) / "page")], check=True, timeout=120)
    ocr = ""
    for png in sorted(Path(d).glob("page*.png")):
        ocr += subprocess.run(["tesseract", str(png), "-"], capture_output=True, text=True, timeout=120).stdout.lower()
    seen = set(re.findall(r'[a-z]{4,}', ocr))
    rate = sum(w in seen for w in words) / len(words)
    assert rate >= 0.90, f"OCR recovered only {rate:.0%} of the paper's words from the rendered pixels — visual fidelity broken (tofu?)"
print(f"ocr ok: {rate:.0%} of {len(words)} body words OCR-recovered from the rendered pixels — visually legible")
