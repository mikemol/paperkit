#!/usr/bin/env python3
r"""Ρ·render·docx — the render graph's DOCX node: paper.md → a Word document.

A format node in the render coalgebra (graph.py): it performs the md→docx morphism (pandoc), from the
one resolved source (source.py) every node shares.  Terminal-capable — a consumer may want the .docx
itself — or the intermediate the docx→pdf route (pdf.py --via docx) reads on the way to a tagged PDF.
The document title travels from paper.toml through pandoc's core metadata (--metadata title), so it
is set at the layer that owns it and flows out through the PDF export as dc:title.

    docx(paper_md, out_docx) -> Path      # produce the .docx (the node's morphism)
    python3 checks/docx.py                # produce + gate: a valid, round-trippable OOXML package
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


def docx(paper_md: Path, out_docx: Path) -> Path:
    """The md→docx morphism (graph.tool_for('md','docx') = pandoc): cite_split the source, then
    pandoc it to a .docx with the title in the core metadata.
    """
    assert graph.tool_for("md", "docx") == "pandoc"          # the edge the graph declares
    with tempfile.TemporaryDirectory() as t:
        md = Path(t) / "p.md"
        md.write_text(source.cite_split(paper_md))
        subprocess.run(["pandoc", str(md), "--citeproc", "--bibliography",
                        str(paper_md.parent / "references.bib"),
                        "--metadata", f"title={source.title(paper_md)}", "-o", str(out_docx)],
                       check=True)
    return out_docx


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        out = docx(Path("../paper/paper.md"), Path(t) / "paper.docx")
        # a valid OOXML package pandoc can read back (the docx node's own fidelity)
        names = zipfile.ZipFile(out).namelist()
        wf = "word/document.xml" in names
        rt = subprocess.run(["pandoc", str(out), "-t", "plain"], capture_output=True).returncode == 0
        ok = wf and rt and out.stat().st_size > 0
        print(f"docx: {'ok' if ok else 'FAIL'} — paper.md → .docx "
              f"({'well-formed OOXML, ' if wf else 'NOT OOXML, '}"
              f"{'round-trips' if rt else 'does NOT round-trip'})")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
