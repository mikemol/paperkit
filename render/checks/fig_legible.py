#!/usr/bin/env python3
# Ρ·render·fig — the figure's legend SURVIVES into the rendered PDF's TEXT LAYER: screen-
# readable and searchable, not locked in pixels.  An accessibility property of the RENDERED
# artifact (where report/ gates the source SVG's palette).  cwd = render/.
import re, subprocess, tempfile
from pathlib import Path

svg = Path("../report/assets/dag.svg")
labels = re.findall(r"<text[^>]*>([^<]+)</text>", svg.read_text())
words = sorted({w for lab in labels for w in re.findall(r"[a-z]{4,}", lab.lower())})
assert words, "the figure has no text legend to preserve"
with tempfile.TemporaryDirectory() as t:
    d = Path(t)
    (d / "dag.svg").write_bytes(svg.read_bytes())
    subprocess.run(["libreoffice", "--headless", "--convert-to", "emf", "--outdir", str(d), str(d / "dag.svg"),
                    f"-env:UserInstallation=file://{d}/lo"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    (d / "m.md").write_text("# Figure\n\n![the claim-DAG](dag.emf)\n")
    subprocess.run(["pandoc", str(d / "m.md"), "-o", str(d / "out.docx")], check=True, cwd=str(d))
    subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(d), str(d / "out.docx"),
                    f"-env:UserInstallation=file://{d}/lo2"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    subprocess.run(["pdftotext", str(d / "out.pdf"), str(d / "t.txt")], check=True)
    txt = (d / "t.txt").read_text().lower()
    missing = [w for w in words if w not in txt]
    assert not missing, f"figure legend words lost from the PDF text layer (locked in pixels?): {missing}"
print(f"fig legible ok: all {len(words)} legend words survive into the PDF text layer (screen-readable)")
