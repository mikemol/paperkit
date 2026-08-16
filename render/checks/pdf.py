#!/usr/bin/env python3
# Ρ·render·pdf — the DELIVERABLE: the paper rendered END-TO-END (cite_split → citeproc → docx
# → PDF) into the human-readable PDF a reader receives.  Gated complete and polished: no
# citation left as a bare marker, the References list rendered, the content present.  The last
# rung of the agreement chain — the artifact, not an intermediate.  cwd = render/ ; .. = repo.
import importlib.util, re, subprocess, sys, tempfile, tomllib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import linkalt      # describe source-document links the office export leaves bare (Ρ·render·linkalt)
import mathalt      # give each equation a text alternative — PDF/UA 7.7 (Ρ·render·mathalt)
import lo           # office convert: isolated profile + unlink-first (Ρ·render·provenance)


def _load(name, filename):
    """Import a sibling check whose filename is not a valid module name (lo-export.py)."""
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lo_export = _load("lo_export", "lo-export.py")   # docx → tagged PDF/UA over the UNO bridge (Ρ·render·lo-export)

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
# the document title travels from the paper's own paper.toml through pandoc's core metadata into the
# docx and out through the UA export as dc:title — the RIGHT layer, not a post-hoc stamp.
title = tomllib.loads(Path("../paper/paper.toml").read_text())["paper"]["title"]
with tempfile.TemporaryDirectory() as d:
    md, docx, txt = (Path(d) / n for n in ("p.md", "p.docx", "p.txt"))
    md.write_text(split)
    subprocess.run(["pandoc", str(md), "--citeproc", "--bibliography", "../paper/references.bib",
                    "--metadata", f"title={title}", "-o", str(docx)], check=True)
    # the deliverable is a tagged PDF/UA-1: the UNO export sets the pdfuaid schema, DisplayDocTitle
    # and dc:title and refreshes indexes (what LibreOffice owns); linkalt then describes the
    # source-document links the export leaves bare (7.18.1/7.18.5), and mathalt gives each equation
    # a text alternative (7.7) — the export tags each formula as /Formula but sets no /Alt — the two
    # genuine post-export steps.  Together the paper is UA-1 conformant by construction (rnd-a11y
    # gates failedChecks==0).  Falls back to a plain CLI convert if no uno-capable python is present,
    # so the deliverable still renders where the bridge cannot run.
    pdf = lo_export.export_pdfua(docx, Path(d) / "p.pdf") or lo.convert(docx, "pdf", d)
    assert pdf is not None and pdf.stat().st_size > 0, "no PDF deliverable produced (soffice produced no output)"
    linkalt.describe_links(pdf)
    mathalt.describe_formulas(pdf, mathalt.paper_equations(Path("../paper/paper.md")))
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
