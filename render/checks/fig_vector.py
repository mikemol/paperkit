#!/usr/bin/env python3
"""Ρ·render·fig — the claim-DAG figure embeds as a Word-native VECTOR, never a raster.

The report's generated figure goes SVG → EMF via libreoffice (mat260's doctrine) and stays vector
through the docx and on into the PDF: it scales crisply at any zoom, so a low-vision reader gets
no pixelation.  cwd = render/ ; the figure is report/assets/dag.svg (its palette a11y-gated in
report/).

⚑ Ζ·witness·component — THE FIRST WITNESS CONVERTED, AND THE PATTERN IS THE POINT.  This file used
to run its entire body at module level and reach its sibling with
`sys.path.insert(0, str(Path(__file__).resolve().parent))`.  Both are now gone:

  * the work lives in `check()`, so IMPORTING this module does nothing.  A witness is a component
    in a framework, not an individual imperative — the framework decides when the thing happens.
  * `lo` is reached by DECLARATION (`from . import lo`), which needs no path mutation, no import
    ordering, and no guess about the caller's cwd.

⚑ THE `__main__` BLOCK IS AN ADAPTER, NOT THE ENTRY POINT.  `cmd:python3 checks/fig_vector.py` is
what render/warrants.bib says and what downstream consumers author against, so it must keep
working — but a file run BY PATH has no package context (`__package__` is empty) and a relative
import raises.  The block below re-enters through the package so the declaration resolves.  The
verdict is `check()`'s return value; the block only turns it into an exit code.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

MIN_EMF_BYTES = 1000
RASTER_SUFFIXES = (".png", ".jpg", ".jpeg")


def _embed(d: Path, svg: Path) -> str:
    """Build a docx embedding `svg` as EMF; return "" if it is a vector, else the complaint.

    ⚑ SPLIT OUT BECAUSE PLR0911 SAID SO (7 returns > 6), and the linter was right about the
    design rather than the style: one function was doing convert-embed-verify-render-verify.
    This is the decomposition pressure linux-sources described — *the gate does not tell you to
    clean the file, it tells you the file does too much*.
    """
    from . import lo

    (d / "dag.svg").write_bytes(svg.read_bytes())
    emf = lo.convert(d / "dag.svg", "emf", d, timeout=120)
    if emf is None or emf.stat().st_size <= MIN_EMF_BYTES:
        return "SVG did not convert to an EMF vector"
    (d / "m.md").write_text("# Figure\n\n![the claim-DAG](dag.emf)\n")
    subprocess.run(["pandoc", str(d / "m.md"), "-o", str(d / "out.docx")],
                   check=True, cwd=str(d))
    with zipfile.ZipFile(d / "out.docx") as z:
        media = [n for n in z.namelist() if n.startswith("word/media/")]
    if not any(n.endswith(".emf") for n in media):
        return f"figure not embedded as a vector EMF: {media}"
    if any(n.endswith(RASTER_SUFFIXES) for n in media):
        return f"figure was rasterized in the docx: {media}"
    return ""


def _stays_vector(d: Path) -> str:
    """Render the docx to PDF; return "" if no raster image appears, else the complaint."""
    from . import lo

    out_pdf = lo.convert(d / "out.docx", "pdf", d, timeout=120)
    if out_pdf is None:
        return "docx did not convert to a PDF (soffice produced no output)"
    listed = subprocess.run(["pdfimages", "-list", str(out_pdf)],
                            capture_output=True, text=True, check=False).stdout.splitlines()
    raster = [r for r in listed[2:] if r.strip()]
    if raster:
        return (f"figure rasterized in the PDF (should stay vector): "
                f"{len(raster)} raster image(s)")
    return ""


def check() -> int:
    """Return 0 iff the figure survives SVG→EMF→docx→PDF as a vector."""
    svg = Path("../report/assets/dag.svg")
    if not svg.exists():
        sys.stderr.write("the report's figure is missing\n")
        return 1
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        # ⚑ SEQUENCED, NOT A TUPLE.  A first cut wrote `for c in (_embed(...), _stays_vector(...))`
        # — which EVALUATES BOTH before testing either, so a failed embed still ran the PDF
        # render against a docx that was never built.  A tuple of calls is not a short-circuit.
        for step in (lambda: _embed(d, svg), lambda: _stays_vector(d)):
            complaint = step()
            if complaint:
                sys.stderr.write(complaint + "\n")
                return 1
    sys.stdout.write("fig vector ok: SVG→EMF→docx→PDF stays a crisp vector, never rasterized\n")
    return 0


if __name__ == "__main__":
    # ⚑ THE ADAPTER.  Run by path there is no package, so `from . import lo` inside check() would
    # raise; runpy re-enters this module AS a package member, where the declaration resolves.
    if __package__:
        raise SystemExit(check())
    import runpy

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    runpy.run_module("render.checks.fig_vector", run_name="__main__", alter_sys=True)
