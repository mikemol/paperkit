#!/usr/bin/env python3
# Ρ·render·ocr (fonts) — every font in the rendered PDF is EMBEDDED, so it draws identically
# on a machine that lacks the font: no silent substitution to a glyph the author never saw.
# cwd = render/ ; .. = repo root.  (pdffonts columns end: ... emb sub uni objnum gen → emb is [-5].)
import subprocess, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as d:
    docx, pdf = Path(d) / "p.docx", Path(d) / "p.pdf"
    subprocess.run(["pandoc", "../paper/paper.md", "-o", str(docx)], check=True)
    subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", d, str(docx),
                    f"-env:UserInstallation=file://{d}/lo"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    rows = [r for r in subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True, check=True)
            .stdout.splitlines()[2:] if r.strip()]
    assert rows, "no fonts found in the rendered PDF"
    not_embedded = [r.split()[0] for r in rows if r.split()[-5] == "no"]
    assert not not_embedded, f"fonts NOT embedded (would substitute/tofu elsewhere): {not_embedded}"
print(f"fonts ok: all {len(rows)} fonts embedded — the PDF draws identically on any machine")
