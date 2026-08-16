#!/usr/bin/env python3
# Ρ·render·fig — the figure's legend SURVIVES into the rendered PDF's TEXT LAYER: screen-
# readable and searchable, not locked in pixels.  An accessibility property of the RENDERED
# artifact (where report/ gates the source SVG's palette).  cwd = render/.
import re, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lo   # office convert: isolated profile + unlink-first, so an absence is loud (Ρ·render·provenance)
import svgpad  # pad the SVG viewport so the EMF step cannot clip legend words (Ρ·render·svgpad)

svg = Path("../report/assets/dag.svg")
labels = re.findall(r"<text[^>]*>([^<]+)</text>", svg.read_text())
words = sorted({w for lab in labels for w in re.findall(r"[a-z]{4,}", lab.lower())})
assert words, "the figure has no text legend to preserve"
with tempfile.TemporaryDirectory() as t:
    d = Path(t)
    (d / "dag.svg").write_bytes(svgpad.pad_svg(svg.read_bytes()))
    emf = lo.convert(d / "dag.svg", "emf", d, timeout=120)
    assert emf is not None, "SVG did not convert to an EMF vector (soffice produced no output)"
    (d / "m.md").write_text("# Figure\n\n![the claim-DAG](dag.emf)\n")
    subprocess.run(["pandoc", str(d / "m.md"), "-o", str(d / "out.docx")], check=True, cwd=str(d))
    out_pdf = lo.convert(d / "out.docx", "pdf", d, timeout=120)
    assert out_pdf is not None, "docx did not convert to a PDF (soffice produced no output)"
    subprocess.run(["pdftotext", str(out_pdf), str(d / "t.txt")], check=True)
    txt = (d / "t.txt").read_text().lower()
    missing = [w for w in words if w not in txt]
    assert not missing, f"figure legend words lost from the PDF text layer (locked in pixels?): {missing}"
print(f"fig legible ok: all {len(words)} legend words survive into the PDF text layer (screen-readable)")
