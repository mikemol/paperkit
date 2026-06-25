#!/usr/bin/env python3
# Ρ·render·bib — the paper's TWO kinds of citation resolve in the render.  A [@warrant] is an
# INTERNAL verified claim (warrants.bib); a [@source] is an EXTERNAL paper (references.bib).
# Like mat260's cite_split: inline each warrant as a verification marker BEFORE pandoc, then
# --citeproc renders the external sources author-date with a References list.  No [@key] is
# left literal.  Render-time projection — the gated paper.md is untouched.  cwd = render/.
import re, subprocess, tempfile
from pathlib import Path

# marker per warrant = its verification, from the check TYPE (the field the gate runs)
MARK = {"file": "(present)", "result": "(verdict imported)"}
markers = {}
for m in re.finditer(r"@\w+\{\s*([^,\s]+)\s*,(.*?)\n\}", Path("../paper/warrants.bib").read_text(), re.S):
    c = re.search(r"\bcheck\s*=\s*\{(\w+):", m.group(2))
    if c:
        markers[m.group(1)] = MARK.get(c.group(1), "(machine-checked)")

src = Path("../paper/paper.md").read_text()
split = re.sub(r"\[@([A-Za-z][\w:.+-]*)\]", lambda x: markers.get(x.group(1), x.group(0)), src)
with tempfile.TemporaryDirectory() as d:
    md = Path(d) / "p.md"; md.write_text(split)
    txt = subprocess.run(["pandoc", str(md), "--citeproc", "--bibliography", "../paper/references.bib", "-t", "plain"],
                         capture_output=True, text=True, check=True).stdout

leftover = re.findall(r"\[@[A-Za-z][\w:.+-]*\]", txt)
assert not leftover, f"citations left LITERAL (unresolved) in the render: {leftover[:5]}"
assert "machine-checked" in txt, "no warrant rendered inline as a verification marker"
for author in ("Knuth", "Donoho", "Mokhov"):
    assert author in txt, f"external source by {author} did not render into the References list"
print("bib ok: warrants inline (machine-checked), external sources author-date + References, no literal [@key]")
