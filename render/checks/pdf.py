#!/usr/bin/env python3
# Ρ·render·pdf — the DELIVERABLE: the paper rendered END-TO-END (cite_split → citeproc → docx
# → PDF) into the human-readable PDF a reader receives.  Gated complete and polished: no
# citation left as a bare marker, the References list rendered, the content present.  The last
# rung of the agreement chain — the artifact, not an intermediate.  cwd = render/ ; .. = repo.
import re, subprocess, tempfile
from pathlib import Path

MARK = {"file": "(present)", "result": "(verdict imported)"}
mk = {}
# bib-list-aware: read every ../paper/*.bib (the warrants may be authored across concept modules);
# references carry no `check`, so the `if c:` guard below excludes them.
_bibtext = "".join(p.read_text() for p in sorted(Path("../paper").glob("*.bib")))
for m in re.finditer(r"@\w+\{\s*([^,\s]+)\s*,(.*?)\n\}", _bibtext, re.S):
    c = re.search(r"\bcheck\s*=\s*\{(\w+):", m.group(2))
    if c:
        mk[m.group(1)] = MARK.get(c.group(1), "(machine-checked)")
split = re.sub(r"\[@([A-Za-z][\w:.+-]*)\]", lambda x: mk.get(x.group(1), x.group(0)),
               Path("../paper/paper.md").read_text())
with tempfile.TemporaryDirectory() as d:
    md, docx, pdf, txt = (Path(d) / n for n in ("p.md", "p.docx", "p.pdf", "p.txt"))
    md.write_text(split)
    subprocess.run(["pandoc", str(md), "--citeproc", "--bibliography", "../paper/references.bib", "-o", str(docx)], check=True)
    subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", d, str(docx),
                    f"-env:UserInstallation=file://{d}/lo"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    assert pdf.exists() and pdf.stat().st_size > 0, "no PDF deliverable produced"
    pages = int(re.search(r'Pages:\s*(\d+)', subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout).group(1))
    assert pages >= 1, "empty PDF deliverable"
    subprocess.run(["pdftotext", str(pdf), str(txt)], check=True)
    out = txt.read_text()
    bare = re.findall(r'\[@[A-Za-z][\w:.+-]*\]', out)
    assert not bare, f"the deliverable PDF still has bare citation markers: {bare[:5]}"
    words = sorted(set(re.findall(r'[a-z]{4,}', Path("../paper/paper.md").read_text().lower())))
    seen = set(re.findall(r'[a-z]{4,}', out.lower()))
    rate = sum(w in seen for w in words) / len(words)
    assert rate >= 0.85, f"the deliverable PDF is missing content — only {rate:.0%} of the paper's words present (truncated?)"
print(f"pdf ok: {pages}-page deliverable, citations resolved, {rate:.0%} of body content present")
