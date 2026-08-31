#!/usr/bin/env python3
"""Ρ·render·integrity (structure) — the section structure survives the render.

The rendered .docx is well-formed OOXML, and every paper heading is presented as a REAL Word
heading with matching text — not flattened into body text that merely looks like a heading.
A screen reader navigates by that structure, so losing it is losing navigation.
cwd = render/ ; .. = repo root.

⚑ Ζ·witness·component — the body was module-level, so importing this file ran pandoc and parsed
a docx.  It is now a callable the framework invokes.  This module has no sibling imports, so it
carried no sys.path injection to retire: the conversion here is purely the side-effect lift.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
HEADING = re.compile(r"^#{1,6}\s")


def _md_headings(paper: Path) -> list[str]:
    """Collect the headings the markdown source declares."""
    return [re.sub(r"^#{1,6}\s+", "", ln).rstrip()
            for ln in paper.read_text().splitlines() if HEADING.match(ln)]


def _docx_headings(docx: Path) -> list[str]:
    """Collect the paragraphs the rendered docx styles as Word headings.

    Parsing also PROVES the OOXML is well-formed — `ET.fromstring` raises on malformed input,
    which is half of what this witness asserts.
    """
    with zipfile.ZipFile(docx) as z:
        root = ET.fromstring(z.read("word/document.xml").decode())
    out: list[str] = []
    for p in root.iter(f"{{{W}}}p"):
        st = p.find(f".//{{{W}}}pStyle")
        if st is not None and st.get(f"{{{W}}}val", "").startswith("Heading"):
            out.append("".join(t.text or "" for t in p.iter(f"{{{W}}}t")))
    return out


def check() -> int:
    """Return 0 iff the docx is well-formed and preserves every heading."""
    paper = Path("../paper/paper.md")
    md_heads = _md_headings(paper)
    with tempfile.TemporaryDirectory() as d:
        docx = Path(d) / "p.docx"
        subprocess.run(["pandoc", str(paper), "-o", str(docx)],
                       check=True)
        docx_heads = _docx_headings(docx)
    if docx_heads != md_heads:
        sys.stderr.write(f"heading structure not preserved:\n md  ={md_heads}\n"
                         f" docx={docx_heads}\n")
        return 1
    sys.stdout.write(f"structure ok: well-formed OOXML, {len(docx_heads)} headings "
                     f"preserved as Word headings\n")
    return 0


if __name__ == "__main__":
    # ⚑ THE ADAPTER, not the entry point — see render/checks/__init__.py.  No relative import
    # here, so the package re-entry is not strictly required; it is kept identical to its
    # siblings so the pattern is ONE shape rather than a per-file judgement about whether this
    # particular witness happens to need it.
    if __package__:
        raise SystemExit(check())
    import runpy

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    runpy.run_module("render.checks.structure", run_name="__main__", alter_sys=True)
