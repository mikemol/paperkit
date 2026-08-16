#!/usr/bin/env python3
r"""Ρ·render·odf — the render graph's ODF node: paper.md → an OpenDocument Text (.odt).

A format node in the render coalgebra (graph.py): it performs the md→odt morphism (pandoc), from the
one resolved source (source.py).  OpenDocument is LibreOffice's NATIVE format — it is the object the
office edges pass through (a docx→pdf conversion runs through ODF inside LibreOffice), so surfacing it
as its own node makes the hidden intermediate a first-class, terminal-capable deliverable: a consumer
may want the .odt itself, or route it on to a PDF (pdf.py --via odf).

    odt(paper_md, out_odt) -> Path        # produce the .odt (the node's morphism)
    python3 checks/odf.py                 # produce + gate: a valid ODF package
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph
import source


def odt(paper_md: Path, out_odt: Path) -> Path:
    """The md→odt morphism (graph.tool_for('md','odt') = pandoc): cite_split the source, then pandoc
    it to a .odt (OpenDocument)."""
    assert graph.tool_for("md", "odt") == "pandoc"
    with tempfile.TemporaryDirectory() as t:
        md = Path(t) / "p.md"
        md.write_text(source.cite_split(paper_md))
        subprocess.run(["pandoc", str(md), "--citeproc", "--bibliography",
                        str(paper_md.parent / "references.bib"),
                        "--metadata", f"title={source.title(paper_md)}", "-o", str(out_odt)],
                       check=True)
    return out_odt


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        out = odt(Path("../paper/paper.md"), Path(t) / "paper.odt")
        # a valid ODF package: an OpenDocument zip carries content.xml + the odt mimetype
        z = zipfile.ZipFile(out)
        names = z.namelist()
        content = "content.xml" in names
        mimetype = "mimetype" in names and z.read("mimetype") == b"application/vnd.oasis.opendocument.text"
        ok = content and mimetype and out.stat().st_size > 0
        print(f"odf: {'ok' if ok else 'FAIL'} — paper.md → .odt "
              f"({'valid ODF (content.xml + odt mimetype)' if ok else 'not a valid ODF package'})")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
