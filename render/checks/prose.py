#!/usr/bin/env python3
r"""Ρ·render·agree helper — replace each inline/display math span with a stable placeholder.

The agree check concurs two independent render paths (paper.md's own plain text, and the plain text
of paper.md → docx → back) to rule out a shared bug.  It owns PROSE fidelity.  A math span is not
prose: it is OMML content, and its plain-text FLATTENING differs between the two paths (pandoc
flattens `\emptyset` to ∅ from markdown but to ⌀ from a round-tripped docx — two different math
flatteners, not a fidelity failure).  Comparing those flattenings would have agree re-derive a
math-equivalence judgment it does not own.

So agree DELEGATES the math, the way every paperkit view delegates a cross-boundary judgment to its
owner: each math span is replaced with a single stable placeholder BEFORE either path renders, so
agree concurs the prose and the placeholders (identical by construction), while the equations' own
fidelity is owned by the OMML check (rnd-omml — native oMath, well-formed, none rasterized).

Reads markdown on stdin, writes it with every `$…$` / `$$…$$` span replaced by `[EQ]`, to stdout.
Used by both agree producers, so the substitution is identical on both sides.

    pandoc-input | python3 checks/prose.py   # (invoked inside the agree producers)
"""
from __future__ import annotations

import re
import sys

# a `$…$` inline span or a `$$…$$` display span; the display form is matched first so its outer
# `$$` is not mistaken for two empty inline spans.
_MATH = re.compile(r"\$\$.+?\$\$|(?<!\\)\$(?!\$).+?(?<!\\)\$", re.S)


def strip_math(md: str) -> str:
    """Replace every math span with the placeholder `[EQ]` (delegating the math to rnd-omml)."""
    return _MATH.sub("[EQ]", md)


if __name__ == "__main__":
    sys.stdout.write(strip_math(sys.stdin.read()))
