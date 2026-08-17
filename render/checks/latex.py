#!/usr/bin/env python3
r"""Ρ·render·latex — the paper as a LaTeX deliverable: a tagged PDF/UA-2 with recoverable MathML.

paperkit's SECOND render FORMAT, beside docx (one consumer class wants docx+PDF, another latex+PDF;
both terminate in PDF).  The LaTeX path reaches a HIGHER accessibility standard than docx and does it
by construction rather than by post-export surgery:

  - the math transports as native LaTeX and TAGS as a Formula structure element with an ASSOCIATED
    MathML file (/AF) — recoverable structure a screen reader reads, not the /Alt string the docx
    route stamps on;
  - the text layer is clean (unicode-math's OpenType maps, no ToUnicode wall);
  - the whole document is tagged PDF/UA-2 (veraPDF failedChecks==0), a later standard than the docx
    route's UA-1, which the PDF-2.0 lualatex output naturally targets.

The recipe is vendored from mat230 (its tree is retiring; taken from its committed gen_submission,
minimal form — the tagging project auto-drives luamml under `pdfstandard=ua-2`, so neither an explicit
`\usepackage{luamml}` nor a `,math` testphase key is needed, verified on this TeX Live):

    \DocumentMetadata{lang=en-US,pdfstandard=ua-2,testphase={phase-III}}   % MUST precede \documentclass
    \usepackage{unicode-math}

Pinned (mat230's validated set): TeX Live 2025, testphase=phase-III, veraPDF 1.30.2.  The luamml
auto-load is the TeX-Live-version-sensitive part; rnd-a11y-latex re-measures conformance so a future
TeX Live that breaks the auto-tagging is caught, not silently shipped untagged.

FONT FALLBACK (the paper uses δ ⟨ ⟩ · Δ Ξ as PROSE text, which Latin Modern Roman lacks → .notdef):
a luaotfload per-codepoint fallback keeps Latin Modern for the document's look and reaches a covering
font ONLY for the glyphs it lacks — surgical, not a whole-document font swap.  A .notdef in the
deliverable is a real defect (PDF/UA-2 clause 8.4.5.9), caught by the a11y check.

`\DocumentMetadata` must be the FIRST line, before `\documentclass` — so this does NOT use pandoc's
standalone LaTeX (whose preamble it cannot control); it renders the BODY with pandoc and assembles the
.tex itself with the metadata first.

    python3 checks/latex.py            # build the paper.md → tagged PDF/UA-2 deliverable, gate it
    python3 checks/latex.py --selftest # ⟨P,F,δ⟩ against a math fixture
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

# The fallback font: libre, embeddable, covers Greek + the mathematical angle brackets the paper's
# prose uses.  luaotfload routes to it ONLY for codepoints the main font lacks.
_FALLBACK_FONT = "DejaVu Sans"
# mat230's minimal, validated preamble (the tagging project auto-drives luamml under ua-2).
_METADATA = r"\DocumentMetadata{lang=en-US,pdfstandard=ua-2,testphase={phase-III}}"


def _deps_absent() -> str | None:
    import shutil
    for tool in ("lualatex", "pandoc"):
        if not shutil.which(tool):
            return tool
    for sty in ("unicode-math", "luaotfload"):
        if subprocess.run(["kpsewhich", sty + ".sty"], capture_output=True).returncode != 0:
            return sty + ".sty"
    if a11y._find_verapdf(None) is None:    # the UA-2 gate needs veraPDF; absent → cannot-run, not a crash
        return "verapdf"
    return None


import a11y          # owns _find_verapdf (portable veraPDF resolution — never a hardcoded absolute path)
import source        # the render graph's md node — the ONE resolved-source logic every format node shares
import ruler_inject  # apply ruler-sequence rules to every table by construction (WCAG 1.4.1, the latex route affords it)


def _assemble_tex(body: str, title: str, ruler_preamble: str = "") -> str:
    """Assemble the .tex with `\\DocumentMetadata` FIRST (it must precede `\\documentclass`, so
    pandoc's standalone preamble cannot carry it), the minimal mat230 tagging preamble, the
    per-codepoint font fallback, and the ruler-sequence nicematrix definitions (empty if the
    document has no rulable table)."""
    return "\n".join([
        _METADATA,                                           # first line — before \documentclass
        r"\documentclass{article}",
        r"\usepackage{unicode-math}",                        # math + the OpenType text stack
        r"\usepackage{luaotfload}",
        rf'\directlua{{luaotfload.add_fallback("pkfallback", {{"{_FALLBACK_FONT}:mode=harf;"}})}}',
        r"\setmainfont{Latin Modern Roman}[RawFeature={fallback=pkfallback}]",
        r"\usepackage{hyperref}",
        ruler_preamble,                                      # nicematrix + \Rule<k> custom-lines
        rf"\title{{{title}}}",
        r"\begin{document}",
        r"\maketitle",
        body,
        r"\end{document}",
        "",
    ])


def build(paper_md: Path, out_pdf: Path, work: Path) -> Path | None:
    """Render `paper_md` to a tagged PDF/UA-2 at `out_pdf`.  Returns the path, or None if a
    dependency is absent (loud) — so a box without the LaTeX stack does not fail the build, it
    reports it cannot produce this format."""
    if _deps_absent():
        print(f"latex: {_deps_absent()} absent — cannot build the LaTeX deliverable here",
              file=sys.stderr)
        return None
    split = source.cite_split(paper_md)
    title = source.title(paper_md)
    md = work / "p.md"
    md.write_text(split)
    body = subprocess.run(
        ["pandoc", str(md), "-t", "latex", "--citeproc",
         "--bibliography", str(paper_md.parent / "references.bib")],
        capture_output=True, text=True, check=True).stdout
    # by construction: rule every table with the ruler-sequence non-colour cue (WCAG 1.4.1), and
    # size the nicematrix preamble to the orders the document's tables actually reach.
    body, report = ruler_inject.inject(body)
    ruler_preamble = (ruler_inject.preamble_defs(ruler_inject.max_order_of(report))
                      if any(not t["excepted"] and t["rows"] >= 2 for t in report) else "")
    tex = work / "p.tex"
    tex.write_text(_assemble_tex(body, title, ruler_preamble))
    # twice: the first pass writes the .aux (refs, the struct tree); the second resolves them.
    for _ in range(2):
        subprocess.run(["lualatex", "-interaction=nonstopmode", "-output-directory", str(work),
                        str(tex)], capture_output=True, text=True)
    pdf = work / "p.pdf"
    if not (pdf.exists() and pdf.stat().st_size > 0):
        return None
    out_pdf.write_bytes(pdf.read_bytes())
    return out_pdf


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--selftest":
        return _selftest()
    absent = _deps_absent()
    if absent:
        print(f"latex: {absent} absent — CANNOT BUILD (not a pass)", file=sys.stderr)
        return 3                                            # cannot-run, not a green
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        pdf = build(Path("../paper/paper.md"), d / "paper.pdf", d)
        if pdf is None:
            print("latex: FAIL — no PDF deliverable produced", file=sys.stderr)
            return 1
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        tagged = bool(re.search(r"Tagged:\s+yes", info))
        pages = int((re.search(r"Pages:\s*(\d+)", info) or [0, 0])[1])
        # the paper's content is present (no dropped page) + it is tagged
        txt = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
        words = sorted(set(re.findall(r"[a-z]{4,}", Path("../paper/paper.md").read_text().lower())))
        seen = set(re.findall(r"[a-z]{4,}", txt.lower()))
        rate = sum(w in seen for w in words) / len(words)
        ok = tagged and pages >= 1 and rate >= 0.85
        print(f"latex: {'ok' if ok else 'FAIL'} — {pages}-page tagged={tagged} PDF/UA-2 deliverable, "
              f"{rate:.0%} of body content present")
        return 0 if ok else 1


def _selftest() -> int:
    """⟨P, F, δ⟩ — the LaTeX deliverable is a tagged PDF/UA-2 with associated MathML:
      P: a math fixture builds a Tagged PDF whose /Formula elements carry /AF (MathML), veraPDF ua2==0.
      F: the same fixture with the tagging metadata REMOVED is untagged and veraPDF ua2 fails.
      δ: the \\DocumentMetadata line — the whole tagged/UA-2 state hangs off it.
    SKIPS LOUD if the LaTeX stack is absent."""
    absent = _deps_absent()
    if absent:
        print(f"  -- {absent} absent; the LaTeX stack is unrunnable here.\n"
              "     LATEX SELFTEST: SKIP (loud) — the method is present but unrunnable on this box")
        return 0
    import pikepdf
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    def _ua2(pdf: Path) -> int:
        vera = a11y._find_verapdf(None)     # portable resolution (a11y.py owns it), never a hardcoded path
        if vera is None:
            return -1                       # unreachable — _deps_absent() gates veraPDF above → cannot-run
        v = subprocess.run([str(vera), "--flavour", "ua2", str(pdf)], capture_output=True, text=True)
        m = re.search(r'failedChecks="(\d+)"', v.stdout)
        return int(m.group(1)) if m else -1

    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        math = r"$\mathrm{eff}(c) = \min\{g(d)\}$ and $\mathrm{incr}(c) = \mathrm{fp}(c) \setminus \bigcup_d \mathrm{fp}(d)$."
        body = subprocess.run(["pandoc", "-t", "latex"], input=f"# Formulas\n\n{math}\n",
                              capture_output=True, text=True).stdout

        # P: with the tagging metadata → tagged, /AF MathML, ua2==0
        (d / "p.tex").write_text(_assemble_tex(body, "Fixture"))
        for _ in range(2):
            subprocess.run(["lualatex", "-interaction=nonstopmode", "-output-directory", str(d),
                            str(d / "p.tex")], capture_output=True, text=True)
        p_pdf = d / "p.pdf"
        af = 0
        if p_pdf.exists():
            doc = pikepdf.open(str(p_pdf))

            def walk(n, dep=0):
                nonlocal af
                if dep > 12 or not isinstance(n, pikepdf.Dictionary):
                    return
                if str(n.get("/S")) == "/Formula" and "/AF" in n:
                    af += 1
                k = n.get("/K")
                if k is not None:
                    for it in (k if isinstance(k, pikepdf.Array) else [k]):
                        if isinstance(it, pikepdf.Dictionary):
                            walk(it, dep + 1)
            r = doc.Root.get("/StructTreeRoot")
            if r:
                walk(r)
        check("P: the deliverable is PDF/UA-2 conformant (veraPDF failedChecks==0)",
              p_pdf.exists() and _ua2(p_pdf) == 0)
        check("P: each formula carries ASSOCIATED MathML (/AF) — recoverable math, not just /Alt",
              af >= 1)

        # F: strip \DocumentMetadata → untagged, ua2 fails
        f_tex = _assemble_tex(body, "Fixture").replace(_METADATA, "")
        (d / "f.tex").write_text(f_tex)
        for _ in range(2):
            subprocess.run(["lualatex", "-interaction=nonstopmode", "-output-directory", str(d),
                            str(d / "f.tex")], capture_output=True, text=True)
        f_pdf = d / "f.pdf"
        check("F: without \\DocumentMetadata the PDF is not UA-2 conformant (the tagging hangs off it)",
              f_pdf.exists() and _ua2(f_pdf) != 0)
        check("δ: the \\DocumentMetadata line is the discriminator (tagged/UA-2 vs not)",
              p_pdf.exists() and f_pdf.exists() and _ua2(p_pdf) == 0 and _ua2(f_pdf) != 0)

    if fails:
        print(f"LATEX SELFTEST: FAIL ({len(fails)})")
        return 1
    print("LATEX SELFTEST: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
