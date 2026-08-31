#!/usr/bin/env python3
r"""Ρ·render·agree helper — normalize what the agree check does NOT own before it concurs two paths.

The agree check concurs two independent render paths (paper.md's own plain text, and the plain text
of paper.md → docx → back) to rule out a shared bug.  It owns PROSE fidelity — and DELEGATES anything
whose cross-path rendering is owned by another check, the way every paperkit view delegates a
cross-boundary judgment to its owner.  Two things are delegated, both by replacing the span with a
stable placeholder BEFORE either path renders (so both sides carry the identical placeholder and
agree concurs the prose around it):

  - MATH spans (`$…$` / `$$…$$`) → `[EQ]`.  A math span is OMML content, not prose, and its plain-text
    FLATTENING differs across the paths (pandoc renders `\emptyset` as ∅ from markdown but ⌀ from a
    round-tripped docx — two math flatteners, not a fidelity failure).  Its fidelity is owned by the
    OMML check (rnd-omml).

  - a RAW placement block (`<!-- paperkit:raw -->` … `<!-- /paperkit:raw -->`) → `[RAW]`.  A raw
    placement is document syntax the engine did not construct — here, the formula TABLE.  A table's
    plain-text layout is render-context-dependent: the docx path wraps cells and re-widths columns
    while the markdown path keeps rows on one line, so comparing the two flattened tables compares
    LAYOUT, not content — the very column-width variance measured-column-width (rnd-widen) exists to
    manage.  The raw block's own fidelity is owned elsewhere: its STRUCTURE by the fresh check that
    GENERATES it from the claims (gen_formulas.py) and its MATH by rnd-omml.  So agree delegates it
    whole rather than concur a layout it does not own.

Reads markdown on stdin, writes it with math spans → `[EQ]` and raw blocks → `[RAW]`, to stdout.
Used by both agree producers, so the substitution is identical on both sides.

    pandoc-input | python3 checks/prose.py   # (invoked inside the agree producers)
"""
from __future__ import annotations

import re
import sys

# a whole raw placement block (matched FIRST, so a table's `$` cells aren't touched as loose math)
_RAW = re.compile(r"<!-- paperkit:raw -->.*?<!-- /paperkit:raw -->", re.S)
# a `$…$` inline span or a `$$…$$` display span; the display form is matched first so its outer
# `$$` is not mistaken for two empty inline spans.
_MATH = re.compile(r"\$\$.+?\$\$|(?<!\\)\$(?!\$).+?(?<!\\)\$", re.S)


def strip_math(md: str) -> str:
    """Delegate the render-context-owned spans: a raw placement block → `[RAW]` (its layout is owned
    by rnd-widen, its structure by the fresh check, its math by rnd-omml), then each remaining math
    span → `[EQ]` (owned by rnd-omml).  What is left is the prose agree concurs.
    """
    md = _RAW.sub("[RAW]", md)
    return _MATH.sub("[EQ]", md)


if __name__ == "__main__":
    sys.stdout.write(strip_math(sys.stdin.read()))
