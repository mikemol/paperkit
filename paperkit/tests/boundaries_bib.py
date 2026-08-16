#!/usr/bin/env python3
"""Behavioral-boundary examples for the bib PARSER — paperkit/bib.py.

⟨P, F, δ⟩ per the boundary practice.  The parser carries the known fields (_SCALAR, _LIST) and
NAMES any OTHER field loudly rather than dropping it in silence — a field paperkit does not
consume is otherwise a silent drop (a downstream author's `points` vanished on 14 entries).  It
stays quiet only on standard BibTeX metadata a `references.bib` citation is expected to carry.
The top-level field scan tracks brace depth, so an `=` inside a value is not mistaken for a field.

    python3 paperkit/tests/boundaries_bib.py
"""
from __future__ import annotations

import io
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bib  # noqa: E402


def _warns(body: str) -> str:
    """Parse a one-entry bib with this body; return the parser's stderr."""
    bib._WARNED.clear()                          # the dedup is per build, not per probe
    p = Path(tempfile.mkdtemp()) / "t.bib"
    p.write_text("@misc{k,\n" + body + "\n}\n")
    err = io.StringIO()
    with redirect_stderr(err):
        parsed = bib.parse(p)
    return err.getvalue(), parsed["k"]


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("bib parser behaviors\n")
    check("_top_fields finds the top-level fields",
          bib._top_fields("claim = {a}, check = {cmd:true}") == ["claim", "check"])
    check("_top_fields ignores an `=` INSIDE a value (set notation is not a field)",
          bib._top_fields("claim = {x = {1,2}}, check = {cmd:true}") == ["claim", "check"])
    known_err, known = _warns("  claim = {a claim},\n  check = {cmd:true}")
    check("a known field is carried (claim + check parsed)",
          known.get("claim") == "a claim" and known.get("check") == "cmd:true")
    check("a known-field entry warns about nothing", known_err == "")
    pts_err, pts = _warns("  claim = {c},\n  points = {q, r},\n  check = {cmd:true}")
    check("an unknown field is NAMED loud on stderr (not silently dropped)",
          "points" in pts_err and "DROPPED" in pts_err)
    check("the unknown field is still absent from the parsed record (dropped, as said)",
          "points" not in pts)
    bibtex_err, _ = _warns("  title = {T},\n  author = {A},\n  journal = {J},\n  year = {2020}")
    check("standard BibTeX metadata a reference carries is tolerated — no warning",
          bibtex_err == "")
    # A claim carrying inline math extracts INTACT: the value is brace-counted to arbitrary depth
    # (a set-builder \min\{ … \mathrm{eff}(d) : … \} nests deeper than one level) and LaTeX-escaped
    # braces \{ \} are literal CONTENT, not structure — the one-level regex this replaced stopped
    # at the first inner `}` and returned a truncated/empty claim (the projector then fell back to
    # the bare key — the degenerate-claim class one layer down).
    _, math = _warns(r"  claim = {clamp: $\mathrm{eff}(c) = \min\{\, \mathrm{grade}(c)\,\} \cup \{\, \mathrm{eff}(d) : d \in S\,\}$ holds},"
                     "\n  check = {cmd:true}")
    check("a claim with DEEP-nested inline math extracts intact (not truncated to empty)",
          math.get("claim", "").startswith("clamp:") and math["claim"].endswith("holds")
          and "$" in math["claim"])
    check("_scalar_value counts to arbitrary depth (nested \\mathrm{} inside \\{ \\})",
          bib._scalar_value(r"claim = {a \min\{\mathrm{x}\} b}", "claim") == r"a \min\{\mathrm{x}\} b")
    check("_top_fields ignores escaped braces in math (they are not structural depth)",
          bib._top_fields(r"claim = {$\{x\}$ text}, check = {cmd:true}") == ["claim", "check"])
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("the parser names a dropped field only when it is not a paperkit or BibTeX field",
         "the field NAME on the entry (`journal` → tolerated, `points` → named)",
         "BibTeX metadata → silent", _warns("  journal = {J}")[0] == "",
         "unknown field  → named", "points" in _warns("  points = {q}")[0]),
        ("a top-level field is named, an `=` inside a value is not (brace depth)",
         "whether the `= {` sits at brace depth 0 or inside a value",
         "top level → a field", bib._top_fields("points = {q}") == ["points"],
         "inside a value → not", bib._top_fields("claim = {a points = {q} b}") == ["claim"]),
        ("a claim's value is brace-counted, and an escaped brace is content not structure",
         "whether a `}` is a real closing brace or a LaTeX-escaped literal `\\}`",
         "unescaped } closes the value",
         bib._scalar_value(r"claim = {a {b} c}", "claim") == "a {b} c",
         "escaped \\} does NOT close it early",
         bib._scalar_value(r"claim = {a \} b}", "claim") == r"a \} b"),
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
    print("BOUNDARIES: PASS (10 behaviors, 3 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
