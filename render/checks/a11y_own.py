#!/usr/bin/env python3
r"""Ρ·render·a11y-own — gate paperkit's OWN paper PDF on PDF/UA-1 conformance.

`a11y.py` is the parametrized, opt-in accessibility gate a downstream project points at its own
deliverable.  This check points it at PAPERKIT'S paper: it builds the deliverable exactly as
`pdf.py` does — pandoc (with the paper's title as core metadata) → the UNO PDF/UA export (which sets
the pdfuaid schema, DisplayDocTitle and dc:title and refreshes indexes) → linkalt (describes the
source-document links the export leaves bare) — and runs `a11y.check_ua2(.., flavour="ua1")` on the
result, requiring veraPDF UA-1 failedChecks==0.

This is what the adoption EARNS: a plain office conversion leaves the paper non-conformant (a bare
link → 7.18.1/7.18.5, and the identification metadata unset → 5/1, 7.1/9, 7.1/10).  Driving the
export in PDF/UA mode closes the metadata clauses AT THE RIGHT LAYER (LibreOffice owns them), and
linkalt closes the link clauses, so the paper reaches failedChecks==0 by construction rather than
by a post-hoc stamp.  The flavour is UA-1 because LibreOffice emits UA-1 and declares pdfuaid:part=1
(a11y.py's own note) — gate on what the producer targets.

veraPDF absent ⇒ FAIL LOUD (a11y.check_ua2 refuses to skip-green).  The check reuses a11y.py's
functions rather than re-implementing them (one owner for the measurement).

    python3 checks/a11y_own.py            # build the conformant deliverable, gate it UA-1==0
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a11y            # the measurement owner — import, never re-implement
import linkalt
import lo
import mathalt
import widen_tables


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lo_export = _load("lo_export", "lo-export.py")


def _build_deliverable(d: Path) -> Path:
    """Reproduce pdf.py's deliverable pipeline (pandoc-title → UA export → linkalt), returning the
    PDF path.  The same right-layer chain — kept in step with pdf.py."""
    _bibtext = "".join(p.read_text() for p in sorted(Path("../paper").glob("*.bib")))
    mark = {"file": "(present)", "result": "(verdict imported)"}
    mk = {}
    for m in re.finditer(r"@\w+\{\s*([^,\s]+)\s*,(.*?)\n\}", _bibtext, re.S):
        c = re.search(r"\bcheck\s*=\s*\{(\w+):", m.group(2))
        if c:
            mk[m.group(1)] = mark.get(c.group(1), "(machine-checked)")
    split = re.sub(r"\[@([A-Za-z][\w:.+-]*)\]", lambda x: mk.get(x.group(1), x.group(0)),
                   Path("../paper/paper.md").read_text())
    title = tomllib.loads(Path("../paper/paper.toml").read_text())["paper"]["title"]
    md, docx = d / "p.md", d / "p.docx"
    md.write_text(split)
    subprocess.run(["pandoc", str(md), "--citeproc", "--bibliography", "../paper/references.bib",
                    "--metadata", f"title={title}", "-o", str(docx)], check=True)
    widen_tables.widen(docx, d / "sized.docx")               # size columns before export (pandoc→widen→export)
    docx = d / "sized.docx"
    pdf = lo_export.export_pdfua(docx, d / "p.pdf") or lo.convert(docx, "pdf", d)
    assert pdf is not None and pdf.stat().st_size > 0, "no PDF deliverable produced"
    linkalt.describe_links(pdf)                                       # links: PDF/UA 7.18.1/7.18.5
    mathalt.describe_formulas(pdf, mathalt.paper_equations(Path("../paper/paper.md")))  # 7.7
    return pdf


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        pdf = _build_deliverable(Path(t))
        r = a11y.Result()
        a11y.check_ua2(r, pdf, None, flavour="ua1")                  # the conformance gate, UA-1
        a11y.check_tagged(r, pdf, None)                              # Tagged: yes
        print(f"\n  a11y (own paper) — {pdf.name}")
        print("  " + "-" * 60)
        for name, ok, detail in r.rows:
            print(f"  {'✓' if ok else '✗'} {name:<30} {detail}")
        print("  " + "-" * 60)
        if r.ok():
            print("  a11y-own: PASS — paperkit's paper is PDF/UA-1 conformant by construction "
                  "(veraPDF failedChecks==0, Tagged)")
            return 0
        print("  a11y-own: FAIL — the paper is not PDF/UA-1 conformant "
              "(the adopted repair did not close every failure)", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
