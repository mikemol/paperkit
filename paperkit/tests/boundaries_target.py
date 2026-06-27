#!/usr/bin/env python3
"""Behavioral-boundary examples for the render TARGET — per-target citation rendering
(paperkit/project.py, Ρ·render·web).

⟨P, F, δ⟩.  The SAME grounding edge (rests-on DATA) materializes per target: a pandoc [@key]
citation, or — for the web target — an intra-page HYPERLINK to the grounded claim's ANCHOR.
One common projector, the target a config knob; no new authoring syntax, no edge in the prose.

    python3 paperkit/tests/boundaries_target.py
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import project as Pr  # noqa: E402

R, S = Pr.references, Pr.sentence


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("render target — per-target citation rendering\n")
    pos = {"x": 2, "y": 0}
    check("pandoc: a cross-reference is a [@key] citation", R("x", ["y"], pos) == " (grounded above in [@y])")
    check("web: the SAME cross-reference is an intra-page hyperlink to the anchor",
          R("x", ["y"], pos, "web") == " (grounded above in [y](#y))")
    check("web: a multi-word key becomes a readable link label",
          R("x", ["foo-bar"], {"x": 2, "foo-bar": 0}, "web") == " (grounded above in [foo bar](#foo-bar))")
    f = {"claim": "a claim", "_src": "w.bib"}
    check("pandoc: a claim ends with its own [@key]", S("k", f, "w.bib") == "a claim [@k]")
    check("web: a claim carries an ANCHOR others link to", S("k", f, "w.bib", "web") == '<a id="k"></a>a claim')

    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "paper.toml").write_text('[paper]\ntitle = "T"\nwarrants = ["w.bib"]\nrubric = "r.tsv"\nout = "o.md"\n')
        (d / "r.tsv").write_text("s\tSec\n")
        (d / "w.bib").write_text("@misc{c1,\n  section = {s}, claim = {one}\n}\n"
                                 "@misc{c2,\n  section = {s}, from = {c1}, claim = {two}\n}\n"
                                 "@misc{c3,\n  section = {s}, from = {c2}, rests-on = {c1}, claim = {three}\n}\n")
        cfg = Pr.load_config(d)
        web, pan = Pr.project(cfg, "web"), Pr.project(cfg, "pandoc")
        check("web output leaves NO bare [@key] citation", "[@" not in web)
        check("pandoc output uses [@key] citations", "[@c1]" in pan)
        targets = set(re.findall(r"\]\(#([\w.:-]+)\)", web))
        anchors = set(re.findall(r'id="([\w.:-]+)"', web))
        check("every web hyperlink resolves to an anchor present in the document (no dangling)",
              bool(targets) and targets <= anchors)

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    P, F = R("x", ["y"], pos, "web"), R("x", ["y"], pos)
    ok = "(#y)" in P and "[@y]" in F
    fails.append("target-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}the same grounding edge renders [@y] for pandoc, a #y hyperlink for web")
    print("      P (web):    (grounded above in [y](#y))   — an intra-page link to the anchor")
    print("      F (pandoc): (grounded above in [@y])      — a citeproc citation")
    print("      δ (min delta): the render target (a config knob), the edge unchanged\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (8 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
