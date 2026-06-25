#!/usr/bin/env python3
# Ρ·render·integrity (structure) — the rendered .docx is well-formed OOXML, and every paper
# heading is presented as a REAL Word heading with matching text (the section structure
# survives the render, not flattened into body text).  cwd = render/ ; .. = repo root.
import re, subprocess, tempfile, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
paper = Path("../paper/paper.md")
md_heads = [re.sub(r'^#{1,6}\s+', '', ln).rstrip()
            for ln in paper.read_text().splitlines() if re.match(r'^#{1,6}\s', ln)]
with tempfile.TemporaryDirectory() as d:
    docx = Path(d) / "p.docx"
    subprocess.run(["pandoc", str(paper), "-o", str(docx)], check=True)
    root = ET.fromstring(zipfile.ZipFile(docx).read("word/document.xml").decode())  # raises if malformed
    docx_heads = []
    for p in root.iter(f'{{{W}}}p'):
        st = p.find(f'.//{{{W}}}pStyle')
        if st is not None and st.get(f'{{{W}}}val', '').startswith('Heading'):
            docx_heads.append(''.join(t.text or '' for t in p.iter(f'{{{W}}}t')))
    assert docx_heads == md_heads, f"heading structure not preserved:\n md  ={md_heads}\n docx={docx_heads}"
print(f"structure ok: well-formed OOXML, {len(docx_heads)} headings preserved as Word headings")
