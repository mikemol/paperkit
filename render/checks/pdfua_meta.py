#!/usr/bin/env python3
r"""Ρ·render·pdfua-meta — stamp the PDF/UA identification metadata the office export omits.

The companion to `linkalt.py` on the pandoc→LibreOffice route.  LibreOffice's headless export
produces a Tagged PDF that is otherwise nearly PDF/UA-1 conformant, but veraPDF flags three
identification-metadata clauses it never emits:

  - 7.1 test 9  — the document has no `dc:title` in its XMP.
  - 7.1 test 10 — `ViewerPreferences /DisplayDocTitle` is not set true (so a reader shows the file
                  NAME in the title bar, not the document's title).
  - 5 test 1    — the PDF carries no `pdfuaid` identification schema declaring the part it conforms
                  to, so a consumer cannot know it is PDF/UA at all.

None of these is content; all three are a post-export stamp.  The title is READ from the project's
`paper.toml` (the owner of the document's title) — never hardcoded here, so the stamp cannot drift
from the paper's own declared title.

    python3 checks/pdfua_meta.py DELIVERABLE.pdf [--toml ../paper/paper.toml]   # stamp + assert
    python3 checks/pdfua_meta.py --selftest                                     # ⟨P,F,δ⟩

`stamp(pdf, title) -> None` does the write, for pdf.py to call in the render pipeline.
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pikepdf


def _title(toml: Path) -> str:
    """The document title from paper.toml's [paper] title — the owner, read not hardcoded."""
    return tomllib.loads(toml.read_text()).get("paper", {}).get("title", "")


def stamp(pdf: Path, title: str) -> None:
    """Write dc:title (XMP), pdfuaid:part=1 (the PDF/UA identification schema), and
    ViewerPreferences/DisplayDocTitle=true.  Saves in place."""
    doc = pikepdf.open(str(pdf), allow_overwriting_input=True)
    with doc.open_metadata() as meta:
        meta["dc:title"] = title
        meta["pdfuaid:part"] = "1"
    doc.Root.ViewerPreferences = pikepdf.Dictionary(DisplayDocTitle=True)
    doc.save(str(pdf))


def _has_metadata(pdf: Path) -> tuple[bool, bool, bool]:
    """(dc:title present, pdfuaid:part present, DisplayDocTitle true) — the three stamped facts."""
    doc = pikepdf.open(str(pdf))
    meta = doc.open_metadata()
    title = bool(meta.get("dc:title"))
    uaid = bool(meta.get("pdfuaid:part"))
    vp = doc.Root.get("/ViewerPreferences")
    ddt = bool(vp and vp.get("/DisplayDocTitle"))
    return title, uaid, ddt


def _selftest() -> int:
    """⟨P, F, δ⟩ — a blank PDF with no PDF/UA metadata:
      P: after stamp, all three (dc:title, pdfuaid:part, DisplayDocTitle) are present.
      F: before the stamp, dc:title is absent (7.1/9 would fail).
      δ: the stamp write — dc:title absent before, present after."""
    import tempfile
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    with tempfile.TemporaryDirectory() as d:
        pdf = Path(d) / "blank.pdf"
        doc = pikepdf.Pdf.new()
        doc.add_blank_page(page_size=(200, 100))
        doc.save(str(pdf))
        before = _has_metadata(pdf)
        stamp(pdf, "A Measured Title")
        after = _has_metadata(pdf)
        check("F: an un-stamped PDF has no dc:title (7.1/9 would fail)", not before[0])
        check("P: after the stamp, dc:title / pdfuaid:part / DisplayDocTitle all present",
              all(after))
        check("δ: the stamp is what added dc:title (absent → present)", not before[0] and after[0])
        check("title read from the argument, not hardcoded", _title_roundtrip(pdf) == "A Measured Title")

    if fails:
        print(f"PDFUA-META SELFTEST: FAIL ({len(fails)})")
        return 1
    print("PDFUA-META SELFTEST: PASS")
    return 0


def _title_roundtrip(pdf: Path) -> str:
    return str(pikepdf.open(str(pdf)).open_metadata().get("dc:title", ""))


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--selftest":
        return _selftest()
    if not argv:
        print("usage: pdfua_meta.py DELIVERABLE.pdf [--toml PATH] | --selftest", file=sys.stderr)
        return 2
    pdf = Path(argv[0])
    toml = Path(argv[argv.index("--toml") + 1]) if "--toml" in argv else Path("../paper/paper.toml")
    if not pdf.exists():
        print(f"pdfua_meta: PDF not found at {pdf} — build the deliverable first", file=sys.stderr)
        return 1
    title = _title(toml)
    if not title:
        print(f"pdfua_meta: no [paper] title in {toml} — cannot stamp dc:title", file=sys.stderr)
        return 1
    stamp(pdf, title)
    t, u, d = _has_metadata(pdf)
    print(f"pdfua_meta: stamped dc:title={t} pdfuaid:part={u} DisplayDocTitle={d}  (title={title!r})")
    if not (t and u and d):
        print("pdfua_meta: FAIL — a PDF/UA identification field did not take", file=sys.stderr)
        return 1
    print("pdfua_meta: ok — PDF/UA identification metadata present (ISO 14289-1 §5, 7.1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
