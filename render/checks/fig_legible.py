#!/usr/bin/env python3
"""Ρ·render·fig — the figure's legend survives into the rendered PDF's TEXT LAYER.

Screen-readable and searchable, not locked in pixels.  This is an accessibility property of the
RENDERED artifact — report/ gates the source SVG's palette, and this gates what a reader can
actually select, search and hear.  cwd = render/.

⚑ Ζ·witness·component — the body was module-level, so importing this file ran two libreoffice
conversions and a pandoc render.  It is now a callable; `lo` is reached by declaration.

⚑⚑ THE `re` NARROWING IS LOCAL, AND THAT IS A KNOWN DUPLICATION.  `Match.group()` and
`Pattern.findall()` are typed `Any` in typeshed, so `disallow_any_expr` flags every read.
`paperkit/rematch.py` exists to narrow that ONCE for the whole ecosystem — but `Ζ·engine·reach`
measured that a witness CANNOT import it: the bib runs `python3`, and bare `python3` cannot
`import paperkit` (only the venv's can, because the editable install is a venv property).  So
the seam is unreachable from here until `Ζ·runner·venv` lands, and each regex-carrying witness
pays for its own narrowing meanwhile.  Recorded rather than silently re-derived: this is the
same capability in a second body, which is the thing the seam was built to prevent.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

TEXT = re.compile(r"<text[^>]*>([^<]+)</text>")
WORD = re.compile(r"[a-z]{4,}")


def _legend_words(svg: Path) -> list[str]:
    """Collect the distinct 4+ letter words the figure's text legend carries."""
    labels: list[str] = TEXT.findall(svg.read_text())
    found: set[str] = set()
    for lab in labels:
        words: list[str] = WORD.findall(lab.lower())
        found.update(words)
    return sorted(found)


def _to_pdf_text(svg: Path, d: Path) -> tuple[str, str]:
    """Render the figure through SVG→EMF→docx→PDF; return (pdf text, complaint)."""
    from . import lo

    (d / "dag.svg").write_bytes(svg.read_bytes())
    emf = lo.convert(d / "dag.svg", "emf", d, timeout=120)
    if emf is None:
        return "", "SVG did not convert to an EMF vector (soffice produced no output)"
    (d / "m.md").write_text("# Figure\n\n![the claim-DAG](dag.emf)\n")
    subprocess.run(["pandoc", str(d / "m.md"), "-o", str(d / "out.docx")],
                   check=True, cwd=str(d))
    out_pdf = lo.convert(d / "out.docx", "pdf", d, timeout=120)
    if out_pdf is None:
        return "", "docx did not convert to a PDF (soffice produced no output)"
    subprocess.run(["pdftotext", str(out_pdf), str(d / "t.txt")],
                   check=True)
    return (d / "t.txt").read_text().lower(), ""


def check() -> int:
    """Return 0 iff every legend word reaches the PDF's text layer."""
    svg = Path("../report/assets/dag.svg")
    words = _legend_words(svg)
    if not words:
        sys.stderr.write("the figure has no text legend to preserve\n")
        return 1
    with tempfile.TemporaryDirectory() as t:
        txt, complaint = _to_pdf_text(svg, Path(t))
    if complaint:
        sys.stderr.write(complaint + "\n")
        return 1
    missing = [w for w in words if w not in txt]
    if missing:
        sys.stderr.write(f"figure legend words lost from the PDF text layer "
                         f"(locked in pixels?): {missing}\n")
        return 1
    sys.stdout.write(f"fig legible ok: all {len(words)} legend words survive into the PDF "
                     f"text layer (screen-readable)\n")
    return 0


if __name__ == "__main__":
    if __package__:
        raise SystemExit(check())
    import runpy

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    runpy.run_module("render.checks.fig_legible", run_name="__main__", alter_sys=True)
