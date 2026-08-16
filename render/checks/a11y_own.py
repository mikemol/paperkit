#!/usr/bin/env python3
r"""Ρ·render·a11y-own — gate paperkit's OWN paper PDF on PDF/UA-1 conformance.

`a11y.py` is the parametrized, opt-in accessibility gate a downstream project points at its own
deliverable.  This check points it at PAPERKIT'S paper: it builds the deliverable exactly as
`pdf.py` does — pandoc→LibreOffice, then the adopted repair (linkalt describes the undescribed
links, pdfua_meta stamps the PDF/UA identification metadata) — and runs `a11y.check_ua2(..,
flavour="ua1")` on the result, requiring veraPDF UA-1 failedChecks==0.

This is what the adoption EARNS: before it, LibreOffice's export left the paper at 5 UA-1 failures
(one undescribed link → 7.18.1/7.18.5, and three metadata clauses → 5/1, 7.1/9, 7.1/10); after the
two adopted post-export methods it reaches failedChecks==0, so the own paper can be gated conformant
by construction rather than measured opt-in.  The flavour is UA-1 because LibreOffice emits UA-1 and
declares pdfuaid:part=1 (a11y.py's own note) — gate on what the producer targets.

veraPDF absent ⇒ FAIL LOUD (a11y.check_ua2 refuses to skip-green).  The check reuses a11y.py's
functions rather than re-implementing them (one owner for the measurement).

    python3 checks/a11y_own.py            # build the repaired deliverable, gate it UA-1==0
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a11y            # the measurement owner — import, never re-implement
import linkalt
import lo
import pdfua_meta


def _build_deliverable(d: Path) -> Path:
    """Reproduce pdf.py's pipeline + the adopted accessibility repair, returning the PDF path."""
    _bibtext = "".join(p.read_text() for p in sorted(Path("../paper").glob("*.bib")))
    mark = {"file": "(present)", "result": "(verdict imported)"}
    mk = {}
    for m in re.finditer(r"@\w+\{\s*([^,\s]+)\s*,(.*?)\n\}", _bibtext, re.S):
        c = re.search(r"\bcheck\s*=\s*\{(\w+):", m.group(2))
        if c:
            mk[m.group(1)] = mark.get(c.group(1), "(machine-checked)")
    split = re.sub(r"\[@([A-Za-z][\w:.+-]*)\]", lambda x: mk.get(x.group(1), x.group(0)),
                   Path("../paper/paper.md").read_text())
    md, docx = d / "p.md", d / "p.docx"
    md.write_text(split)
    subprocess.run(["pandoc", str(md), "--citeproc", "--bibliography",
                    "../paper/references.bib", "-o", str(docx)], check=True)
    pdf = lo.convert(docx, "pdf", d)
    assert pdf is not None and pdf.stat().st_size > 0, "no PDF deliverable produced"
    linkalt.describe_links(pdf)                                       # the adopted repair
    pdfua_meta.stamp(pdf, pdfua_meta._title(Path("../paper/paper.toml")))
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
