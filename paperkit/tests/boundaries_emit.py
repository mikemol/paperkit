#!/usr/bin/env python3
"""Behavioral-boundary examples for emit: placement and the --safe postulate gate.

⟨P, F, δ⟩ per the boundary practice.  Bounds the README-as-projection engine surface:
emit places a verbatim asset (fence inferred from extension), additive to a claim so
the example stays CITED; an uncited placement is a postulate — advised against by
default, rejected under --safe.  Both documentation and a test (exit 0 iff all hold).

    python3 paperkit/tests/boundaries_emit.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture_gate import gate  # noqa: E402
from _fixture_model import entry  # noqa: E402
from _fixture_project import project_text  # noqa: E402
import bib  # noqa: E402  (the owner of emit_anchors/emit_path — the two-anchor resolver)

C = entry("c", claim="a cited claim")                                       # base prose
P_CITE = entry("p", claim="an example", emit="x.sh", frm="c", check="file:x.sh")  # derived term
P_POST = entry("p", emit="x.sh", frm="c", check="file:x.sh")                # postulate (no claim)
P_MD = entry("p", claim="an example", emit="x.md", frm="c", check="file:x.md")
SH = {"x.sh": "echo hi\n"}
MD = {"x.md": "| a | b |\n| - | - |\n"}

# The renderer is DECLARED by `as`, not inferred from the filename.  A `table`
# asset carries DATA and the engine builds the markup, so a cell cannot inject
# document syntax; a `raw` asset IS markup, so it is shielded from cited_keys the
# way a fence already shields code.
P_TAB = entry("p", claim="a table", emit="t.tsv", as_="table", frm="c", check="file:t.tsv")
P_RAWTAB = entry("p", claim="a table", emit="t.tsv", frm="c", check="file:t.tsv")
TAB = {"t.tsv": "metric\tvalue\nsee [@forged]\t1|2\n"}


def main() -> int:
    fails = []

    ran = []

    def check(desc, cond):
        # Λ·guard-must-not-copy — `ran` COUNTS the arms.  The summary line used to restate a
        # number authored beside the set it describes, and every one of the 26 suites carrying
        # such a line UNDERSTATED it (24 mismatched, none overstated): arms were added and the
        # literal never moved, so it tracked the suite's authoring history rather than its
        # content — and would have read a SHRINKING suite as an unchanged one.
        ran.append(desc)
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("emit / --safe behaviors\n")
    proj_sh = project_text([C, P_CITE], assets=SH)
    proj_md = project_text([C, P_MD], assets=MD)
    rc_default, err_default = gate([C, P_POST], assets=SH)
    check("emit places a fenced block, fence from extension (.sh)",
          "```sh" in proj_sh and "echo hi" in proj_sh)
    check("additive: the example is CITED ([@p] in prose)", "[@p]" in proj_sh)
    check(".md asset is a raw include (no code fence)",
          "| a | b |" in proj_md and "```" not in proj_md)
    proj_tab = project_text([C, P_TAB], assets=TAB)
    check("as=table builds the markup from data (header + delimiter row)",
          "| metric | value |" in proj_tab and "| --- | --- |" in proj_tab)
    check("as=table escapes cells, so an asset cannot forge a citation or a pipe",
          r"\[@forged\]" in proj_tab and r"1\|2" in proj_tab
          and "[@forged]" not in proj_tab)
    check("a raw placement is bracketed, so cited_keys cannot read markers inside it",
          "<!-- paperkit:raw -->" in proj_md and "<!-- /paperkit:raw -->" in proj_md)
    proj_svg = project_text([entry("a", claim="a cited claim"),
                             entry("p", claim="a figure", emit="fig.svg", frm="a", check="file:fig.svg")],
                            assets={"fig.svg": "<svg/>\n"})
    check("image asset renders as a markdown image, not a fenced block",
          "![a figure](fig.svg)" in proj_svg and "```" not in proj_svg)
    check("uncited placement passes by default but raises a postulate advisory",
          rc_default == 0 and "postulate" in err_default)

    # Ζ·emit·fallback — a placement asset resolves against BOTH legitimate anchors: project_dir
    # (beside the warrants) FIRST, then out.parent (beside the output).  A project whose `out`
    # points outside itself keeps its assets by the project dir; the MIRROR layout keeps them
    # beside `out`.  629af60 keyed on project_dir alone (a dead `or out.parent`) and broke the
    # mirror layout — this is the coverage whose absence let that land green.  Both distinct
    # anchors holding it is AMBIGUOUS (the gate names it; the projector reads the first).
    root = Path(tempfile.mkdtemp())
    proj, docs = root / "proj", root / "docs"
    proj.mkdir(); docs.mkdir()
    OUT = {"project_dir": proj, "out": docs / "p.md"}     # out OUTSIDE the project (out.parent ≠ proj)
    IN = {"project_dir": proj, "out": proj / "README.md"}  # in-repo — the two anchors coincide
    (proj / "byw.tsv").write_text("by-warrants")           # only beside the warrants
    (docs / "beo.tsv").write_text("beside-out")            # only beside the output (mirror)
    (proj / "both.tsv").write_text("X"); (docs / "both.tsv").write_text("Y")   # at both (ambiguous)
    r_byw = bib.emit_path(OUT, "byw.tsv") == proj / "byw.tsv"
    r_beo = bib.emit_path(OUT, "beo.tsv") == docs / "beo.tsv"
    r_absent = bib.emit_path(OUT, "nope.tsv") is None
    r_ambig = len(bib.emit_anchors(OUT, "both.tsv")) == 2
    r_inrepo = len(bib.emit_anchors(IN, "byw.tsv")) == 1
    shutil.rmtree(root, ignore_errors=True)
    check("emit·fallback: out-outside, asset beside the WARRANTS → resolves via project_dir", r_byw)
    check("emit·fallback: the MIRROR layout, asset beside OUT → resolves via out.parent (629af60's break)", r_beo)
    check("emit·fallback: at NEITHER anchor → ABSENT (None)", r_absent)
    check("emit·fallback: at BOTH distinct anchors → AMBIGUOUS (2 anchors; the gate names it)", r_ambig)
    check("emit·fallback: in-repo (anchors coincide) → ONE hit, never ambiguous", r_inrepo)
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("postulate vs derived term (gate --safe)", "the claim field on the emit warrant",
         "claim+emit → exit 0", gate([C, P_CITE], "--safe", assets=SH)[0] == 0,
         "emit only  → exit 1", gate([C, P_POST], "--safe", assets=SH)[0] == 1),
        ("--safe toggles the postulate (same uncited placement)", "the --safe flag",
         "default → exit 0", gate([C, P_POST], assets=SH)[0] == 0,
         "--safe  → exit 1", gate([C, P_POST], "--safe", assets=SH)[0] == 1),
        ("fence inferred from the asset extension", "the emit target extension (.sh → .md)",
         ".sh → ```sh fence", "```sh" in project_text([C, P_CITE], assets=SH),
         ".md → raw, no fence", "```sh" not in project_text([C, P_MD], assets=MD)),
        ("declared renderer overrides the suffix inference", "the as= field on the emit warrant",
         "as=table → engine-built markup", "| --- | --- |" in project_text([C, P_TAB], assets=TAB),
         "absent  → inferred, verbatim", "| --- | --- |" not in project_text([C, P_RAWTAB], assets=TAB)),
        ("an asset can forge a citation only when it is NOT engine-rendered",
         "the as= field on the same asset",
         "as=table → escaped, inert", "[@forged]" not in project_text([C, P_TAB], assets=TAB),
         "inferred → verbatim in prose", "[@forged]" in project_text([C, P_RAWTAB], assets=TAB)),
        ("emit·fallback resolves against project_dir first, then out.parent (both layouts served)",
         "which anchor holds the asset — the mirror layout 629af60 regressed",
         "asset beside the warrants → project_dir", r_byw,
         "asset beside the output   → out.parent", r_beo),
    ]
    for name, axis, p_lbl, p_ok, f_lbl, f_ok in pairs:
        ok = p_ok and f_ok
        fails.append(name) if not ok else None
        print(f"  {'ok ' if ok else 'XX '}{name}")
        print(f"      P (pass side): {p_lbl}")
        print(f"      F (flag side): {f_lbl}")
        print(f"      δ (min delta): {axis}\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    bad = len([b for b in ran if not b])
    if bad:
        print(f"BOUNDARIES: FAIL ({bad} of {len(ran)} behaviors drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, 6 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
