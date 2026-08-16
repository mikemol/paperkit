#!/usr/bin/env python3
# Ρ·render·fig — the report's generated claim-DAG figure embeds into a rendered document as a
# Word-native VECTOR (SVG → EMF via libreoffice, mat260's doctrine), NOT a raster: it scales
# crisply at any zoom — no pixelation for a low-vision reader — and stays vector through to the
# PDF.  cwd = render/ ; the figure is report/assets/dag.svg (its palette a11y gated in report/).
import subprocess, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lo   # office convert: isolated profile + unlink-first, so an absence is loud (Ρ·render·provenance)
import svgpad  # pad the SVG viewport so the EMF step cannot shave edges (Ρ·render·svgpad, fidelity)

svg = Path("../report/assets/dag.svg")
assert svg.exists(), "the report's figure is missing"
with tempfile.TemporaryDirectory() as t:
    d = Path(t)
    (d / "dag.svg").write_bytes(svgpad.pad_svg(svg.read_bytes()))
    emf = lo.convert(d / "dag.svg", "emf", d, timeout=120)
    assert emf is not None and emf.stat().st_size > 1000, "SVG did not convert to an EMF vector"
    (d / "m.md").write_text("# Figure\n\n![the claim-DAG](dag.emf)\n")
    subprocess.run(["pandoc", str(d / "m.md"), "-o", str(d / "out.docx")], check=True, cwd=str(d))
    media = [n for n in zipfile.ZipFile(d / "out.docx").namelist() if n.startswith("word/media/")]
    assert any(n.endswith(".emf") for n in media), f"figure not embedded as a vector EMF: {media}"
    assert not any(n.endswith((".png", ".jpg", ".jpeg")) for n in media), f"figure was rasterized in the docx: {media}"
    out_pdf = lo.convert(d / "out.docx", "pdf", d, timeout=120)
    assert out_pdf is not None, "docx did not convert to a PDF (soffice produced no output)"
    rows = subprocess.run(["pdfimages", "-list", str(out_pdf)], capture_output=True, text=True).stdout.splitlines()
    raster = [r for r in rows[2:] if r.strip()]
    assert not raster, f"figure rasterized in the PDF (should stay vector): {len(raster)} raster image(s)"
print("fig vector ok: SVG→EMF→docx→PDF stays a crisp vector, never rasterized")
