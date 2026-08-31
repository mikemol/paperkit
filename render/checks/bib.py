#!/usr/bin/env python3
r"""Ρ·render·bib — the paper's TWO kinds of citation both resolve in the render.

A [@warrant] is an INTERNAL verified claim (warrants.bib); a [@source] is an EXTERNAL paper
(references.bib).  Like mat260's cite_split: inline each warrant as a verification marker BEFORE
pandoc, then `--citeproc` renders the external sources author-date with a References list.  No
[@key] is left literal.  Render-time projection — the gated paper.md is untouched.  cwd = render/.

⚑ Ζ·witness·component — the body was module-level, so importing this file ran pandoc.

⚑⚑ AND THIS IS THE MODULE THAT MADE `paperkit/gate.py` INJECT ITS OWN DIRECTORY.  That insert's
comment records the measurement: removing it *"reddened seven talk claims with 'cannot import
name dep_order from bib (render/checks/bib.py)'"* — because a witness that put its own directory
first made THIS file shadow the engine's `paperkit/bib.py`.  The comment calls it *a PRIORITY
claim, not a reachability fix*, which was exactly right about a flat namespace.

As `render.checks.bib` the collision cannot occur: `paperkit.bib` and `render.checks.bib` are
different names.  The priority claim DISSOLVES rather than being preserved — but only once both
sides are packages, which is why the engine's insert must stay until paperkit/ is converted too.

⚑ THE `re` BOUNDARY IS AN Any BOUNDARY, AND THIS FILE IS MOSTLY `re`.  `Match.group()` and
`Pattern.findall()` are typed `Any` / `list[Any]` in typeshed, so an inline lambda in `re.sub`
poisons the substituted text and a bare `findall` poisons every list derived from it.  Both are
narrowed at the seam here (`_marked`'s named `sub`, `_literals`' annotated comprehension) rather
than suppressed — the remedy `disallow_any_expr` exists to force, in the file that most needed it.

⚑⚑ Ζ·re·structural — THE BIB PARSING IS THE ENGINE'S NOW, AND THE `re` LEFT HERE IS THE HONEST
KIND.  This file used to carry `@\w+\{\s*([^,\s]+)\s*,(.*?)\n\}` inline — one of SEVEN copies of
that pattern in this tree, four byte-identical.  Operator: *regex is almost always a textual
answer to a structural problem.*  Parsing a `.bib` is structural and paperkit ships the parser;
matching `[@key]` in prose is genuinely textual and stays a regex.

The copies were not merely redundant, they were WRONG: all seven counted braces to depth ONE
against a corpus that goes to two, so `paper/model.bib`'s `edge-rests-grounds` lost its `claim`
field entirely and the value's own tail was read as a NEW FIELD NAME.  `bibfidelity` counts
properly — measured over 38 bibs: gained 3 fields, lost 0, changed 0.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from paperkit import bibfidelity

# marker per warrant = its verification, from the check TYPE (the field the gate runs)
MARK = {"file": "(present)", "result": "(verdict imported)"}
CITE = re.compile(r"\[@([A-Za-z][\w:.+-]*)\]")
LITERAL = re.compile(r"\[@[A-Za-z][\w:.+-]*\]")
SOURCES = ("Knuth", "Donoho", "Mokhov")
SAMPLE = 5


def _markers() -> dict[str, str]:
    """Map each internal warrant key to its inline verification marker.

    Bib-list-aware: the paper's warrants may be authored across modules (the concept library), so
    every ../paper/*.bib is read.  References carry no `check`, so they are excluded here rather
    than by a second rule — only internal warrants become inline markers.

    ⚑ THE CHECK *TYPE* IS THE FIRST SEGMENT OF THE `check` FIELD (`file:`, `result:`, `cmd:`…),
    read off the parsed field rather than re-found with a second regex.  One parse, one authority.
    """
    text = "".join(p.read_text() for p in sorted(Path("../paper").glob("*.bib")))
    out: dict[str, str] = {}
    for key, fields in bibfidelity.entries(text).items():
        chk = fields.get("check", "")
        if chk:
            out[key] = MARK.get(chk.split(":", 1)[0], "(machine-checked)")
    return out


def _marked(src: str, markers: dict[str, str]) -> str:
    """Replace each [@key] with its verification marker, leaving unknown keys literal."""
    def sub(m: re.Match[str]) -> str:
        key: str = m.group(1)
        whole: str = m.group(0)
        return markers.get(key, whole)
    return CITE.sub(sub, src)


def _literals(txt: str) -> list[str]:
    """Every [@key] that survived the render un-substituted."""
    found: list[str] = LITERAL.findall(txt)
    return found


def _render(split: str) -> str:
    """Run pandoc over the marker-substituted source and return the plain-text render."""
    with tempfile.TemporaryDirectory() as d:
        md = Path(d) / "p.md"
        md.write_text(split)
        argv = ["pandoc", str(md), "--citeproc",
                "--bibliography", "../paper/references.bib", "-t", "plain"]
        # ⚑ S603: argv is a LITERAL list — no shell, and the one interpolated element is a path
        # this function just created inside its own TemporaryDirectory.  The directive was
        # stripped by a RUF100 sweep run with only that rule enabled, where every noqa reads as
        # unused; restored with its reason so the next narrow run cannot silently drop it again.
        out: str = subprocess.run(argv, capture_output=True,  # noqa: S603
                                  text=True, check=True).stdout
        return out


def check() -> int:
    """Return 0 iff both citation kinds resolve and no [@key] survives literal."""
    src = Path("../paper/paper.md").read_text()
    txt = _render(_marked(src, _markers()))

    leftover = _literals(txt)
    if leftover:
        sys.stderr.write(f"citations left LITERAL (unresolved) in the render: "
                         f"{leftover[:SAMPLE]}\n")
        return 1
    if "machine-checked" not in txt:
        sys.stderr.write("no warrant rendered inline as a verification marker\n")
        return 1
    missing = [a for a in SOURCES if a not in txt]
    if missing:
        sys.stderr.write(f"external sources did not render into the References list: {missing}\n")
        return 1
    sys.stdout.write("bib ok: warrants inline (machine-checked), external sources author-date "
                     "+ References, no literal [@key]\n")
    return 0


if __name__ == "__main__":
    if __package__:
        raise SystemExit(check())
    import runpy

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    runpy.run_module("render.checks.bib", run_name="__main__", alter_sys=True)
