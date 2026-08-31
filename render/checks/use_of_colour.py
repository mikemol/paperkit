#!/usr/bin/env python3
r"""Ρ·render·use-of-colour — WCAG 2.2 SC 1.4.1 (Use of Colour), the VERIFYING side.

The 1.4.1 pair: ruler-sequence rules (rulerseq.py) is the PRODUCING side — it EMITS a non-colour
cue.  This is the VERIFYING side — it AUDITS a LaTeX source so that colour is never the SOLE cue:
every `\\`-delimited table row that uses a MEANING colour (`\textcolor{c}` with c not the default
ink) must also carry a WEIGHT cue (`\mathbf`/`\textbf`/…) in that same row.  A row that leans on
colour alone fails, because a reader who cannot perceive that colour then has no handle on the
distinction the colour was carrying.

A sufficient-condition auditor over the LaTeX the render's latex node produces (the office route has
no colour-as-meaning surface to audit, and per-row structure it cannot express anyway — see
rulerseq's toolchain exception), vendored from mat230's `bin/check-a11y` (`_check_use_of_colour`)
before mat230 erases.  Paired with the producing side, WCAG 1.4.1 is covered from both ends.

    use_of_colour(tex) -> (ok, detail)   # audit a LaTeX string
    python3 checks/use_of_colour.py      # ⟨P,F,δ⟩ over synthetic rows
"""
from __future__ import annotations

import re
import sys

# A weight cue that redundantly carries what a colour might (bold in text or math).
_WEIGHT = re.compile(r"\\(mathbf|textbf|boldsymbol|bfseries|bf)\b")
# Colours that do NOT carry meaning (the default ink); every other colour is meaningful.
_MEANING_FREE = {"black"}


def use_of_colour(tex: str) -> tuple[bool, list[str]]:
    """Every `\\`-delimited row that uses a MEANING colour must also carry a WEIGHT cue in that same
    row, so colour is never the sole cue (WCAG 1.4.1).  Sufficient condition (a row with a weight cue
    passes even if the colour also happens to be decorative).
    """
    bad = 0
    for row in re.split(r"\\\\", tex):
        colours = re.findall(r"\\textcolor\{([^}]+)\}", row)
        meaningful = [c for c in colours if c not in _MEANING_FREE]
        if meaningful and not _WEIGHT.search(row):
            bad += 1
    if bad:
        return False, [f"{bad} row(s) use a meaning colour with NO weight cue — colour is the sole cue"]
    return True, ["every colour-marked row also carries a weight cue (bold)"]


def _selftest() -> int:
    # ⟨P,F,δ⟩: the cue-redundancy predicate.
    ok = 0
    # P: a meaning-colour row that ALSO carries a weight cue passes; a black-only row is vacuous.
    passing = r"\textcolor{red}{\textbf{Invalid}} = 3 \\ plain row \\ \textcolor{black}{ink} only"
    if not use_of_colour(passing)[0]:
        ok = 1
    # F: a row using a meaning colour as the SOLE cue fails (δ from P: the weight cue removed).
    failing = r"\textcolor{red}{Invalid} = 3 \\ plain row"
    if use_of_colour(failing)[0]:
        ok = 1
    # δ: the ONE difference is the weight cue — same colour, same row, presence of \textbf flips it.
    if use_of_colour(r"\textcolor{red}{x}")[0] or not use_of_colour(r"\textcolor{red}{\textbf{x}}")[0]:
        ok = 1
    # a source with no \textcolor at all is vacuously OK (nothing to fail).
    if not use_of_colour(r"plain \\ rows \\ only")[0]:
        ok = 1
    if ok == 0:
        print("use-of-colour: ok — WCAG 1.4.1 verifying side (colour never the sole cue)")
        print("  P: a meaning-colour row carrying a weight cue passes; black/no-colour is vacuous")
        print("  F: a meaning colour as the SOLE cue in a row fails")
        print("  δ: the weight cue (\\textbf) in the row — same colour, its presence flips the verdict")
        return 0
    print("use-of-colour: FAIL — the sole-cue predicate is wrong", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    # Audit the paper rendered through the latex node (the only route with a colour-as-meaning surface).
    if "--selftest" in argv or len(argv) == 0:
        return _selftest()
    tex = open(argv[0]).read()
    ok, detail = use_of_colour(tex)
    print(f"use-of-colour: {'ok' if ok else 'FAIL'} — {detail[0]}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
