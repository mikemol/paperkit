#!/usr/bin/env python3
r"""Ρ·deck·emit — the render graph's SLIDE nodes: paper.md → .pptx → .odp.

Two format nodes in the render coalgebra (graph.py), walking the edges it declares: the md→pptx
morphism (pandoc) and the pptx→odp morphism (soffice, through lo.convert's isolated profile).  Both
produce from the ONE resolved source every node shares (source.py), exactly as docx.py and odf.py do.

    THE BOUND (rnd-deck-bound, and the reason this file is `emit` and not `observe`).

This walks a TRANSFORM chain over an ALREADY-LINEARIZED document.  `project()` is S → String — one
flat stream seeded by rubric-order × dep-order — and pandoc reflows that stream onto slides at its
`--slide-level` heading boundary.  The cut is therefore the PROSE's section structure, not a
segmentation of the claim-DAG.  A deck as a genuine OBSERVATION is S → List(Unit) indexed by
(target, genre) — one level, since slides.bib's recursive RoseTree is unbuilt (Ζ·observe·rosetree);
that is Ρ·deck·observe, it is not this, and `rnd-units` gates the difference, because why
the difference is worth keeping visible rather than collapsing.

So: what this delivers is the verified prose, in a slide container, gated to be a well-formed one.
It is NOT a deck whose cut means anything about the argument's structure.  `deck_bound.py` gates that
distinction; this producer must never make it red.

    pptx(paper_md, out) -> Path           # the md→pptx morphism
    odp(pptx_path, outdir) -> Path        # the pptx→odp morphism
    python3 checks/slides.py              # produce + gate both nodes
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph
import lo
import source

# The OOXML / ODF package members that make each container well-formed, and the ODF mimetype the
# presentation (not the text) document declares — the structural facts each node is gated on.
_PPTX_MARKER = "ppt/presentation.xml"
_ODP_MIME = b"application/vnd.oasis.opendocument.presentation"


def _slide_level(paper_md: Path) -> int:
    """The heading level the section boundary lives at, READ from the projection rather than
    assumed: the shallowest level that occurs more than once.  A projector that changed its
    heading scheme would move this with it instead of silently collapsing the deck."""
    levels = [len(m) for m in
              (line.split(" ")[0] for line in paper_md.read_text().splitlines())
              if m and set(m) == {"#"}]
    for lvl in sorted(set(levels)):
        if levels.count(lvl) > 1:
            return lvl
    return 1


def pptx(paper_md: Path, out_pptx: Path) -> Path:
    """The md→pptx morphism (graph.tool_for('md','pptx') = pandoc): cite_split the source, then
    pandoc it to a .pptx, cut at the DERIVED slide level (see _slide_level) — the PROSE's own
    section boundary, which is the finest cut this transform has available (see THE BOUND)."""
    assert graph.tool_for("md", "pptx") == "pandoc", \
        "the graph no longer declares md→pptx as a pandoc morphism — derive the tool, never hardcode"
    with tempfile.TemporaryDirectory() as t:
        md = Path(t) / "p.md"
        md.write_text(source.cite_split(paper_md))
        subprocess.run(["pandoc", str(md), f"--slide-level={_slide_level(paper_md)}", "--citeproc",
                        "--bibliography", str(paper_md.parent / "references.bib"),
                        "--metadata", f"title={source.title(paper_md)}", "-o", str(out_pptx)],
                       check=True)
    return out_pptx


def pptx_observed(project_dir: Path, out_pptx: Path, genre_name: str = "talk") -> Path:
    """Ρ·deck·route — the units→pptx morphism: the deck sourced from the OBSERVATION.

    `pptx()` above reflows an already-linearized document.  This one asks the projector for
    project.observe()'s units and emits one slide per unit, so the cut is the claim-DAG's
    segmentation rather than the prose's heading structure.  Same tool, different SOURCE object —
    which is the whole content of the distinction the render graph now names.

    Ρ·deck·materialize — a unit's claims are MATERIALIZED, not dumped: each carries the same
    verification marker the transform route earns through source.cite_split, derived from the
    claim's own check TYPE, so a slide sourced from the observation states its provenance exactly
    as the prose deliverable does.  Without it the observed deck would be the worse artifact of the
    two — undoing the point of sourcing it from the verified DAG in the first place.

    The unit's heading is its section plus its ordinal within that section, so a section split
    across several units reads as a sequence rather than as the same title repeated.
    """
    assert graph.tool_for("units", "pptx") == "pandoc", \
        "the graph no longer declares units→pptx as a pandoc morphism — derive the tool, never hardcode"
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "paperkit"))
    import project as P
    cfg = P.load_config(project_dir)
    units = P.observe(cfg, genre_name, project_dir)
    # the verification marker per claim, by check TYPE — the same table the prose route uses, read
    # from its owner rather than restated (source._MARK / the default for a machine-checked verb).
    F = {}
    for b in cfg["bibs"]:
        F.update(P.entries(b, cfg["consumer_fields"]))

    def marker(key):
        chk = (F.get(key, {}) or {}).get("check", "")
        verb = chk.split(":", 1)[0] if ":" in chk else ""
        return source._MARK.get(verb, "(machine-checked)" if verb else "")

    lines = [f"% {cfg['title']}", ""]
    seen: dict = {}
    for u in units:
        seen[u["section"]] = seen.get(u["section"], 0) + 1
        n = seen[u["section"]]
        lines.append(f"# {u['section']}" + (f" ({n})" if n > 1 else ""))
        for it in u.get("items") or [{"key": k, "claim": c}
                                     for k, c in zip(u["keys"], u["claims"])]:
            c = it.get("claim")
            if c:
                # depth nests the bullet as a proof step, exactly as the prose route indents it
                indent = "  " * (int(it.get("depth") or 0))
                lines.append(f"{indent}- {c} {marker(it['key'])}".rstrip())
                if it.get("link"):
                    # the expound rung: a sub-bullet, so the note travels with its claim
                    lines.append(f"{indent}  - *{it['link']}*")
            if it.get("emit"):
                # the PLACED ASSET, rendered by the projector's own emit_block — a table, image,
                # code block or raw include lands on the slide as a block, not as a dropped line.
                lines.append("")
                lines += it["emit"]["lines"]
                lines.append("")
        # Ρ·deck·notes — the unit's SPEAKER NOTES, from each claim's reserved `note` field, in a
        # pandoc `::: notes` fence so they become real notesSlides rather than visible body text.
        # One fence per SLIDE (notes belong to the slide, not to a bullet), claims in order.
        notes = [it["note"] for it in (u.get("items") or []) if it.get("note")]
        if notes:
            lines += ["", "::: notes", ""] + notes + ["", ":::"]
        lines.append("")
    with tempfile.TemporaryDirectory() as t:
        md = Path(t) / "u.md"
        md.write_text("\n\n".join(lines))
        # --resource-path is REQUIRED here and not in the prose route: that markdown sits beside
        # the project's assets, this one is assembled in a temp dir, so a relative `emit` path has
        # nothing to resolve against.  A placed FIGURE exposed it — the deck built fine for as long
        # as every placement happened to be text.
        subprocess.run(["pandoc", str(md), "--slide-level=1",
                        "--resource-path", f"{Path(project_dir).resolve()}:{t}",
                        "--metadata", f"title={cfg['title']}", "-o", str(out_pptx)], check=True)
    _repair_alt_text(out_pptx, units)
    return out_pptx, units


def _repair_alt_text(pptx_path: Path, units: list) -> None:
    """Ρ·talk·figures — restore each image's REAL alternative text into the OOXML.

    The projector renders an `as = image` placement as ![claim](path), so a figure is alt-texted
    BY CONSTRUCTION: the claim's own sentence is the description.  But pandoc's pptx writer puts
    the image PATH into <p:cNvPr descr=…> and discards the markdown alt-text, and the office edge
    faithfully carries that path through to svg:desc — so the deck arrived describing a diagram as
    "assets/two-edges.svg", which is present and useless to a screen reader.

    This is the same shape as the render project's existing linkalt/mathalt repairs: the toolchain
    drops an accessibility property the source had, so the pipeline restores it after the tool
    rather than pretending the tool preserved it.  Keyed by the emit PATH, which is what pandoc
    left behind, so each image gets ITS OWN claim rather than a shared description.
    """
    alt = {}
    for u in units:
        for it in (u.get("items") or []):
            em = it.get("emit")
            if em and (em.get("as") == "image" or str(em.get("path", "")).endswith(
                    (".svg", ".png", ".jpg", ".jpeg", ".gif"))):
                if it.get("claim"):
                    alt[str(em["path"])] = it["claim"]
    if not alt:
        return
    import shutil
    tmp = pptx_path.with_suffix(".tmp.pptx")
    with zipfile.ZipFile(pptx_path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if re.match(r"ppt/slides/slide\d+\.xml$", item.filename):
                x = data.decode("utf-8")
                for path, claim in alt.items():
                    esc = (claim.replace("&", "&amp;").replace("<", "&lt;")
                                .replace(">", "&gt;").replace('"', "&quot;"))
                    x = x.replace(f'descr="{path}"', f'descr="{esc}"')
                data = x.encode("utf-8")
            zout.writestr(item, data)
    shutil.move(str(tmp), str(pptx_path))


def odp(src_pptx: Path, outdir: Path) -> Path | None:
    """The pptx→odp morphism (graph.tool_for('pptx','odp') = soffice), through lo.convert so it
    gets the isolated ephemeral profile and the unlink-first provenance guarantee: a file at the
    path is BY CONSTRUCTION the conversion of the current input, never a stale survivor."""
    assert graph.tool_for("pptx", "odp") == "soffice", \
        "the graph no longer declares pptx→odp as a soffice morphism — derive the tool, never hardcode"
    return lo.convert(src_pptx, "odp", outdir)


def _slide_count(odp_path: Path) -> int:
    """Drawing pages in the ODP — the deliverable's own count of what it carries."""
    return zipfile.ZipFile(odp_path).read("content.xml").decode("utf-8", "replace").count("<draw:page ")


def main() -> int:
    paper_md = Path("../paper/paper.md")
    with tempfile.TemporaryDirectory() as t:
        work = Path(t)

        # ── node 1: pptx, a well-formed OOXML presentation package pandoc can read back ──
        p = pptx(paper_md, work / "paper.pptx")
        pz = zipfile.ZipFile(p)
        pptx_ok = _PPTX_MARKER in pz.namelist() and p.stat().st_size > 0
        # readable-back by the producing tool (the same round-trip bar rnd-docx holds)
        rt = subprocess.run(["pandoc", str(p), "-t", "plain"], capture_output=True, text=True)
        pptx_ok = pptx_ok and rt.returncode == 0

        # ── node 2: odp, a well-formed ODF PRESENTATION (not the text mimetype odf.py gates) ──
        o = odp(p, work)
        if o is None or not o.exists():
            print("slides: FAIL — the pptx→odp morphism produced no file (soffice did not convert)",
                  file=sys.stderr)
            return 1
        oz = zipfile.ZipFile(o)
        names = oz.namelist()
        odp_ok = ("content.xml" in names and "mimetype" in names
                  and oz.read("mimetype") == _ODP_MIME and o.stat().st_size > 0)

        # ── the CONTENT survived the chain: the deliverable carries the paper's own title, and
        # carries slides at all.  A structurally-valid but EMPTY container would otherwise pass
        # both package checks above — the degenerate-result trap.
        pages = _slide_count(o) if odp_ok else 0
        text = oz.read("content.xml").decode("utf-8", "replace") if odp_ok else ""
        title = source.title(paper_md)
        carried = bool(title) and title.split(":")[0][:24] in text

        # The deck must TRACK the document's own structure, not merely be nonempty.  `pages > 0`
        # alone let a collapsed cut pass: at the wrong slide level an 86-claim paper emitted FOUR
        # slides and this check went green.  So the floor is the section count the projection
        # actually carries — one slide per heading at the derived level, allowing overflow above.
        lvl = _slide_level(paper_md)
        headings = sum(1 for line in paper_md.read_text().splitlines()
                       if line.startswith("#" * lvl + " "))
        tracks = pages >= headings

        # ── node 3 (Ρ·deck·route): the OBSERVED route — slides sourced from the segmentation ──
        # The gate that matters here is CORRESPONDENCE: one slide per observed unit.  A deck whose
        # slide count did not track the units would be sourced from something other than the
        # observation, which is exactly the claim this route makes.
        op, units = pptx_observed(Path("../paper"), work / "obs.pptx", "talk")
        oo = odp(op, work)
        if oo is None or not oo.exists():
            print("slides: FAIL — the observed route's pptx→odp morphism produced no file",
                  file=sys.stderr)
            return 1
        obs_pages = _slide_count(oo)
        # pandoc emits a title slide from the metadata, so the deck carries units + 1.
        corresponds = obs_pages == len(units) + 1
        # Ρ·deck·materialize — the observed deck must carry VERIFICATION MARKERS, like the prose
        # route does.  Without this the deck sourced from the verified DAG would be the LESS
        # honest of the two artifacts, which inverts the reason for sourcing it there.
        otext = zipfile.ZipFile(oo).read("content.xml").decode("utf-8", "replace")
        marked = "(machine-checked)" in otext or "(verdict imported)" in otext

        # Ρ·deck·materialize — a PLACED ASSET must reach the deck.  A claim carrying `emit` renders
        # its table/image/code/raw block in the prose route; a deck that dropped it would be a
        # LOSSY view of the same carrier, and the render layer could not recover what the
        # projector discarded.  Checked against the asset's own text, not a count.
        placed, missing_asset = 0, []
        for u in units:
            for it in (u.get("items") or []):
                if it.get("emit"):
                    placed += 1
                    body = "\n".join(it["emit"]["lines"])
                    words = [w for w in re.findall(r"[A-Za-z]{4,}", body)][:3]
                    if words and not all(w in otext for w in words):
                        missing_asset.append(it["key"])
        assets_ok = not missing_asset

        # ── a11y (Ρ·render·matrix slide-structure): the deck must carry real SLIDE STRUCTURE —
        # a title placeholder per slide and its content as list structure — since that is what a
        # screen reader announces and walks.  Claimed in the capability grid, so it is checked
        # here rather than asserted there.
        titles = otext.count('presentation:class="title"')
        lists = otext.count("<text:list")
        structured = titles >= obs_pages - 1 and lists > 0
        # and the EXCEPTION is verified as an exception, not assumed: the grid says slide alt-text
        # is `excepted`, which is only honest while nothing on a slide NEEDS an alternative.  A
        # placed image would; if one ever appears without a description, the exception is a gap.
        # CONTENT images only.  LibreOffice emits a TablePreview*.svm beside every converted
        # table — a rendering thumbnail of the table sitting right next to it, not user content:
        # the accessible object is the <table:table> itself, and demanding alt-text for the
        # preview would be demanding a description of a picture of an accessible thing.  Counting
        # it would make the check red on a deck with no accessibility problem, which is the
        # measure-the-wrong-thing failure — so the exclusion is named, not silent.
        # PER-FRAME, not a count: ODF puts svg:desc inside the <draw:frame> wrapping the image, so
        # the honest question is "does THIS image's frame carry a description", never "are there at
        # least as many descriptions as images" — two images sharing one description would pass a
        # counting test while one of them ships undescribed.
        frames = re.findall(r"<draw:frame\b.*?</draw:frame>", otext, re.S)
        content_frames = [f for f in frames
                          if "<draw:image" in f and "TablePreview" not in f]

        def _quality(desc: str) -> bool:
            """Ρ·render·alt·odp·live — the deck's descriptions measured on the ARTIFACT, held to
            the SAME bar the PDF route applies to its links (linkalt._is_marker).  paperkit
            alt-texts a figure by construction — the claim IS the description — but construction-
            time guarantees are exactly what the pptx writer destroyed silently when it replaced
            the alt-text with the image PATH.  One predicate, both deliverables, no self-exemption.
            """
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import linkalt
            return not linkalt._is_marker(desc)

        def _described(fr):
            """A frame is described only by a REAL sentence, not by its own filename.

            Measured failure: pandoc's pptx writer puts the image PATH into the OOXML `descr`
            attribute and discards the markdown alt-text, so the deck arrived carrying
            "assets/two-edges.svg" as its description — present, and useless to a screen reader.
            A presence test passed it.  So the test is CONTENT: a description must not be the
            href, and must read as prose (several words) rather than a token.
            """
            m = re.search(r"<svg:desc[^>]*>([^<]*)</svg:desc>", fr)
            if not m:
                return False
            desc = m.group(1).strip()
            href = re.search(r'xlink:href="([^"]*)"', fr)
            if href and (desc == href.group(1) or desc.endswith(Path(href.group(1)).name)):
                return False                      # the filename is not a description
            return _quality(desc) and len(desc.split()) >= 4

        undescribed = [f for f in content_frames if not _described(f)]
        alt_ok = not undescribed
        imgs, descs = len(content_frames), len(content_frames) - len(undescribed)

        # Ρ·deck·notes — a claim's reserved `note` must reach the deck as a real SPEAKER NOTE, not
        # as visible body text and not dropped.  Checked structurally (a notes page per unit that
        # has one) rather than by substring, since the office export smart-quotes the prose and a
        # phrase-match would fail on an apostrophe while the note was perfectly present.
        # Counting notes PAGES is not enough: the office export creates an empty notes page per
        # slide whether or not anything was written, so `pages >= noted units` passes trivially on
        # a deck with zero notes.  Count pages carrying TEXT instead — the presence of the
        # scaffolding says nothing about whether the author's words survived.
        want_notes = sum(1 for u in units if any(i.get("note") for i in (u.get("items") or [])))
        note_pages = re.findall(r'presentation:class="notes".*?</draw:frame>', otext, re.S)
        got_notes = sum(1 for pg in note_pages
                        if len(re.sub(r"<[^>]+>", "", pg).split()) > 3)
        notes_ok = got_notes >= want_notes

        # Ρ·talk·colour·render — WCAG 1.4.1 at the DELIVERABLE, not just at the source.  The
        # figures are audited for meaning-hues in their SVG, but that guarantee stopped at the file
        # boundary: the office suite could recolour on import, and a deck theme ships a palette of
        # its own.  Measured: the theme's greens/reds/ambers live in styles.xml and NONE reaches
        # content.xml — so the test is CONTENT-APPLIED colour, since a palette nothing uses carries
        # no meaning and failing on its presence would be measuring the wrong thing.
        # TEXT colour, not every fill: 1.4.1 is about colour carrying INFORMATION, and a table's
        # banded row fill is decoration — the table's own structure carries what the banding
        # suggests, so a reader who cannot see the stripe loses nothing.  Measured on paper/: the
        # three fills flagged by a fill-inclusive test were all table-cell striping applied by the
        # converter, which would have made the check red on a deck with no accessibility problem.
        applied = {x.lower() for x in re.findall(r'fo:color="(#[0-9a-fA-F]{6})"', otext)}
        neutral = {"#000000", "#ffffff", "#eeeeee", "#808080", "#8b8b8b", "#333333", "#111111"}
        meaning_hues = sorted(applied - neutral)
        colour_ok = not meaning_hues

        # and the observed cut must DIFFER from the prose cut — else the route is decorative and
        # the distinction the graph draws would be a name without a referent.
        differs = obs_pages != pages

        ok = pptx_ok and odp_ok and carried and tracks and corresponds and differs and marked and assets_ok and structured and alt_ok and notes_ok and colour_ok
        print(f"slides: {'ok' if ok else 'FAIL'} — paper.md → .pptx "
              f"({'valid OOXML, pandoc reads it back' if pptx_ok else 'INVALID pptx'}) → .odp "
              f"({'valid ODF presentation' if odp_ok else 'INVALID odp'}, {pages} slides for "
              f"{headings} level-{lvl} sections{'' if tracks else ' — CUT COLLAPSED'}, "
              f"title {'carried' if carried else 'LOST'}); observed route: {obs_pages} slides "
              f"for {len(units)} units"
              f"{'' if corresponds else ' — DOES NOT CORRESPOND'}"
              f"{'' if differs else ' — SAME AS THE PROSE CUT, the route is decorative'}"
              f"{'' if marked else ' — NO VERIFICATION MARKERS, less honest than the prose route'}"
              f", {placed} placed asset(s), {titles} slide titles / {lists} lists"
              f", {got_notes} speaker-note page(s) for {want_notes} noted unit(s)"
              f"{'' if notes_ok else ' — NOTES DROPPED'}"
              f"{'' if colour_ok else ' — MEANING COLOUR APPLIED TO CONTENT: ' + str(meaning_hues)}"
              f"{'' if structured else ' — NO SLIDE STRUCTURE for a screen reader'}"
              f"{'' if alt_ok else f' — {imgs} image(s), only {descs} description(s)'}"
              f"{'' if assets_ok else ' — DROPPED: ' + str(missing_asset)}")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
