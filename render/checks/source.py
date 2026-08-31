#!/usr/bin/env python3
r"""Ρ·render·source — the render graph's SOURCE node: paper.md with its warrant citations resolved.

Every format node (docx, odf, latex) starts from the same resolved source: the paper's prose with
each internal `[@warrant]` inlined as its verification marker (cite_split, before any format
conversion), plus the document title from paper.toml.  This is the ONE place that logic lives — the
graph's md node — so the docx, odf and latex producers all render the SAME resolved prose and cannot
drift from each other.

    cite_split(paper_md) -> str      # the resolved markdown a format node renders from
    title(paper_md)      -> str      # the document title (for pandoc --metadata / a LaTeX \title)
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

_MARK = {"file": "(present)", "result": "(verdict imported)"}


def cite_split(paper_md: Path) -> str:
    """The paper's prose with every internal `[@warrant]` inlined as its verification marker (the
    marker its check TYPE earns), so an internal warrant reads as a machine-checked claim and never
    a bare citation.  External `[@source]` citations (references.bib, no `check`) are left for the
    format's own bibliography step.
    """
    mk = {}
    bibtext = "".join(p.read_text() for p in sorted(paper_md.parent.glob("*.bib")))
    for m in re.finditer(r"@\w+\{\s*([^,\s]+)\s*,(.*?)\n\}", bibtext, re.S):
        c = re.search(r"\bcheck\s*=\s*\{(\w+):", m.group(2))
        if c:
            mk[m.group(1)] = _MARK.get(c.group(1), "(machine-checked)")
    return re.sub(r"\[@([A-Za-z][\w:.+-]*)\]", lambda x: mk.get(x.group(1), x.group(0)),
                  paper_md.read_text())


def title(paper_md: Path) -> str:
    """The document title, from the paper's own paper.toml [paper] title — the owner of it."""
    return tomllib.loads((paper_md.parent / "paper.toml").read_text())["paper"]["title"]
