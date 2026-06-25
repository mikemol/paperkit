#!/usr/bin/env python3
# Ρ·render·fig — the report's generated claim-DAG figure embeds into a rendered document as a
# Word-native VECTOR (SVG → EMF via libreoffice, mat260's doctrine), NOT a raster: it scales
# crisply at any zoom — no pixelation for a low-vision reader — and stays vector through to the
# PDF.  cwd = render/ ; the figure is report/assets/dag.svg (its palette a11y gated in report/).
import subprocess, tempfile, zipfile
from pathlib import Path

svg = Path("../report/assets/dag.svg")
assert svg.exists(), "the report's figure is missing"
with tempfile.TemporaryDirectory() as t:
    d = Path(t)
    (d / "dag.svg").write_bytes(svg.read_bytes())
    subprocess.run(["libreoffice", "--headless", "--convert-to", "emf", "--outdir", str(d), str(d / "dag.svg"),
                    f"-env:UserInstallation=file://{d}/lo"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    emf = d / "dag.emf"
    assert emf.exists() and emf.stat().st_size > 1000, "SVG did not convert to an EMF vector"
    (d / "m.md").write_text("# Figure\n\n![the claim-DAG](dag.emf)\n")
    subprocess.run(["pandoc", str(d / "m.md"), "-o", str(d / "out.docx")], check=True, cwd=str(d))
    media = [n for n in zipfile.ZipFile(d / "out.docx").namelist() if n.startswith("word/media/")]
    assert any(n.endswith(".emf") for n in media), f"figure not embedded as a vector EMF: {media}"
    assert not any(n.endswith((".png", ".jpg", ".jpeg")) for n in media), f"figure was rasterized in the docx: {media}"
    subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(d), str(d / "out.docx"),
                    f"-env:UserInstallation=file://{d}/lo2"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    rows = subprocess.run(["pdfimages", "-list", str(d / "out.pdf")], capture_output=True, text=True).stdout.splitlines()
    raster = [r for r in rows[2:] if r.strip()]
    assert not raster, f"figure rasterized in the PDF (should stay vector): {len(raster)} raster image(s)"
print("fig vector ok: SVG→EMF→docx→PDF stays a crisp vector, never rasterized")
