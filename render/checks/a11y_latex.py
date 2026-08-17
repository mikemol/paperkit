#!/usr/bin/env python3
r"""Ρ·render·a11y-latex — gate paperkit's OWN paper on PDF/UA-2 through the LaTeX render format.

The sibling of a11y_own (which gates the docx deliverable at PDF/UA-1).  This points the accessibility
measurement at the LaTeX deliverable: it builds the paper the way latex.py does — pandoc → the tagged
`\DocumentMetadata` preamble + a per-codepoint font fallback → lualatex — and requires veraPDF PDF/UA-2
failedChecks==0.

PDF/UA-2 is a HIGHER standard than the docx route's UA-1, and the LaTeX path reaches it BY
CONSTRUCTION: the math tags as a Formula with associated MathML (recoverable structure, not a stamped
/Alt string), and the tagging is native (no post-export surgery).  So this gate proves the second
format is at least as accessible as the first, and on the math axis, more.

The UA-2 verdict SUBSUMES the tofu / missing-glyph check: clause 8.4.5.9 forbids a `.notdef` glyph, so
a paper that used a prose character the fonts do not cover would fail UA-2 here — the LaTeX-format
analog of the docx route's fidelity gate, folded into the one conformance verdict.  (Missing-character
detail, when it fails, is named from the lualatex log so the fix — extend the fallback — is actionable.)

veraPDF absent ⇒ FAIL LOUD (refuse to skip-green); the LaTeX stack absent ⇒ CANNOT-RUN (exit 3), not a
false pass.

    python3 checks/a11y_latex.py       # build the LaTeX deliverable, gate it PDF/UA-2 == 0
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a11y            # the veraPDF measurement owner — import, never re-implement
import latex           # the LaTeX deliverable builder (Ρ·render·latex)


def _missing_glyphs(work: Path) -> list[str]:
    """The lualatex log's 'Missing character' warnings — names the exact codepoints a .notdef came
    from, so a UA-2 8.4.5.9 failure is actionable (extend the font fallback)."""
    log = work / "p.log"
    if not log.exists():
        return []
    return re.findall(r"Missing character: There is no (\S+ \(U\+[0-9A-F]+\))", log.read_text(errors="replace"))


def main() -> int:
    if latex._deps_absent():
        print(f"a11y-latex: {latex._deps_absent()} absent — CANNOT VERIFY the LaTeX format here "
              "(not a pass)", file=sys.stderr)
        return 3
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        pdf = latex.build(Path("../paper/paper.md"), d / "paper.pdf", d)
        if pdf is None:
            print("a11y-latex: FAIL — the LaTeX deliverable did not build", file=sys.stderr)
            return 1
        r = a11y.Result()
        a11y.check_ua2(r, pdf, None, flavour="ua2")          # the conformance gate, UA-2 (subsumes .notdef)
        a11y.check_tagged(r, pdf, None)                      # Tagged: yes
        print(f"\n  a11y-latex (own paper, LaTeX format) — {pdf.name}")
        print("  " + "-" * 60)
        for name, ok, detail in r.rows:
            print(f"  {'✓' if ok else '✗'} {name:<30} {detail}")
        missing = _missing_glyphs(d)
        if missing:
            print(f"  ! lualatex could not place {len(missing)} glyph(s) — extend the font fallback "
                  f"in latex.py: {sorted(set(missing))[:8]}")
        print("  " + "-" * 60)
        if r.ok():
            print("  a11y-latex: PASS — paperkit's paper is PDF/UA-2 conformant through the LaTeX "
                  "format (a higher standard than the docx route's UA-1, with recoverable MathML)")
            return 0
        print("  a11y-latex: FAIL — the LaTeX deliverable is not PDF/UA-2 conformant", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
