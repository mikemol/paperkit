#!/usr/bin/env python3
"""Ρ·render·ocr (fonts) — every font in the rendered PDF is EMBEDDED.

A document whose fonts are embedded draws identically on a machine that lacks them: no silent
substitution to a glyph the author never saw, no tofu.  cwd = render/ ; .. = repo root.

⚑ Ζ·witness·component — the body was module-level, so importing this file RAN a pandoc call, a
libreoffice conversion and three asserts.  It is now a callable the framework invokes, and `lo`
is reached by declaration rather than by mutating sys.path.

(pdffonts columns end: ... emb sub uni objnum gen → emb is [-5].)
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

EMBEDDED_COL = -5
HEADER_ROWS = 2


def check() -> int:
    """Return 0 iff every font in the rendered PDF is embedded."""
    from . import lo

    with tempfile.TemporaryDirectory() as d:
        docx = Path(d) / "p.docx"
        subprocess.run(["pandoc", "../paper/paper.md", "-o", str(docx)],
                       check=True)
        pdf = lo.convert(docx, "pdf", d)
        if pdf is None:
            sys.stderr.write("docx did not convert to a PDF (soffice produced no output)\n")
            return 1
        listed = subprocess.run(["pdffonts", str(pdf)],
                                capture_output=True, text=True, check=True).stdout.splitlines()
        rows = [r for r in listed[HEADER_ROWS:] if r.strip()]
        if not rows:
            sys.stderr.write("no fonts found in the rendered PDF\n")
            return 1
        missing = [r.split()[0] for r in rows if r.split()[EMBEDDED_COL] == "no"]
        if missing:
            sys.stderr.write(f"fonts NOT embedded (would substitute/tofu elsewhere): {missing}\n")
            return 1
    sys.stdout.write(f"fonts ok: all {len(rows)} fonts embedded — "
                     f"the PDF draws identically on any machine\n")
    return 0


if __name__ == "__main__":
    # ⚑ THE ADAPTER, not the entry point.  `cmd:python3 checks/fonts.py` is what the bib says and
    # what downstream consumers author against, but a file run BY PATH has no package context, so
    # `from . import lo` would raise.  runpy re-enters through the package; the verdict is
    # check()'s return value and this block only turns it into an exit code.
    if __package__:
        raise SystemExit(check())
    import runpy

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    runpy.run_module("render.checks.fonts", run_name="__main__", alter_sys=True)
