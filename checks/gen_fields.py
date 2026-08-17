#!/usr/bin/env python3
# Ρ·surface·project — emit the bibliography-field + [paper]-key tables FROM the parser's own
# declarations (bib._SCALAR, bib._LIST, and the keys bib.load_config reads), so the documentation
# CANNOT drift from the code.  The GLOSSES are authored here (this is the README project, which
# DOCUMENTS the engine); the field SET is DERIVED from the owner (paperkit/bib.py).  A field added
# to _SCALAR with no gloss below fails the coverage assert, so a new surface cannot ship
# undocumented — the same guarantee gen_knobs.py gives the knob table (project, don't author).
# cwd = repo root ; paperkit/ = engine.
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "paperkit"))
import bib  # noqa: E402  — the OWNER of _SCALAR / _LIST / load_config; never re-listed here

# What the ENGINE does with each entry field — the gloss is authored, the KEY SET is bib's.
# Kind: `warrant` (a claim), `reference` (a bibliography citation), `both`, or an INERT marker.
_FIELD_DOC = {
    "title":    ("a reference's title, used as its citation text (or, on a warrant, its sentence)", "reference"),
    "author":   ("a reference's short author, in its citation parenthetical", "reference"),
    "year":     ("a reference's year, in its citation parenthetical", "reference"),
    "note":     ("parsed but consumed nowhere — reserved, engine-inert", "inert"),
    "section":  ("the rubric section this claim belongs to (grouping; a placed postulate marker)", "warrant"),
    "claim":    ("the assertion's prose — projected as the claim's sentence", "warrant"),
    "check":    ("the machine verifier (type:target) the gate resolves and Δ grades", "warrant"),
    "glue":     ("a connective added across a `from` prose edge (legacy weave override)", "warrant"),
    "join":     ("the full inter-clause connector to the previous claim (overrides glue/move)", "warrant"),
    "move":     ("a typed rhetorical move: its default connector, gated against the section scheme", "warrant"),
    "emit":     ("an on-disk asset placed as a block instead of a sentence", "warrant"),
    "as":       ("the renderer for `emit` — table, image, code, or raw (else inferred from the suffix)", "warrant"),
    "mem":      ("engine-inert; projected to a Bazel memory reservation for the check", "warrant"),
    "link":     ("an expound-rung footnote (a technical name, or a ∂² long-edge discharge)", "warrant"),
    "depth":    ("renders the claim as a nested (indented) proof-step list item", "warrant"),
    "tier":     ("the check's enforcement tier (Ζ·tier) — sandbox (hermetic, mutation-swept; default), "
                 "local (host-coupled, uncached), or toolchain (host toolchain, cached + stamped with "
                 "the toolchain fingerprint); a non-sandbox check is gated but not swept", "warrant"),
    "from":     ("prose-order edge: topological ordering + glue adjacency (general→specific)", "warrant"),
    "rests-on": ("grounding edge: effective-grade clamping + citation provenance (NOT prose order)", "warrant"),
    "reads":    ("the check's declared cross-package footprint — staging + audit tokens (Ζ·foot)", "warrant"),
    "consumes": ("sibling warrant keys whose verdict RECORD this check reads (records-as-deps: the "
                 "sibling runs once and is memoized; its verdict.json is a declared bazel input, "
                 "exported in PAPERKIT_CONSUMED_RECORDS as key=path — Ρ·wcag·oracle-edge)", "warrant"),
}

# What each [paper] key controls.  The KEY SET is derived below from load_config's own source.
_PAPER_KEY_DOC = {
    "title":      "the document H1 heading",
    "subtitle":   "an italic subtitle line under the title",
    "rubric":     "path to rubric.tsv (section keys → titles → optional scheme)",
    "warrants":   "the list of `.bib` claim-DAG files to parse",
    "out":        "the output markdown path written",
    "numbered":   "number the section headings (`## 1. …`)",
    "paragraph":  "`claim` = one paragraph per claim; `woven` (default) = join a section into prose",
    "references": "emit the trailing References section",
    "adequacy":   "engine-inert; emits a Bazel Δ-adequacy test for the project",
    "consumer_fields": "extra bib scalar fields this project's downstream consumer owns — carried "
                       "verbatim, consumed by no engine invariant (a declared field is quiet in the "
                       "unknown-field warning; an undeclared one is still named)",
}


def _paper_keys() -> list:
    """The [paper] keys load_config actually reads — parsed from its OWN source (the owner),
    so a new `p.get("k", …)` cannot be documented-or-not by hand.  Deduped, first-seen order."""
    src = inspect.getsource(bib.load_config)
    seen, out = set(), []
    for k in re.findall(r'p\.get\(\s*"([^"]+)"', src):
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def render() -> str:
    fields = list(bib._SCALAR) + list(bib._LIST)          # the SET + order come from the owner
    missing = [f for f in fields if f not in _FIELD_DOC]
    if missing:                                           # a new field shipped without a gloss
        raise SystemExit(f"gen_fields: undocumented bibliography field(s) {missing} — add a gloss "
                         f"to _FIELD_DOC (project, don't author: the set is bib._SCALAR/_LIST)")
    keys = _paper_keys()
    missing_k = [k for k in keys if k not in _PAPER_KEY_DOC]
    if missing_k:
        raise SystemExit(f"gen_fields: undocumented [paper] key(s) {missing_k} — add a gloss to "
                         f"_PAPER_KEY_DOC (the set is load_config's own p.get calls)")
    extra_k = [k for k in _PAPER_KEY_DOC if k not in keys]
    if extra_k:                                           # a documented key load_config no longer reads
        raise SystemExit(f"gen_fields: _PAPER_KEY_DOC documents {extra_k}, which load_config does "
                         f"not read — remove the stale gloss")

    lines = ["A bibliography entry (a warrant, or a `references.bib` citation) may carry these "
             "fields. Generated from the parser's own field set, so it cannot drift from the code.",
             "", "| field | what the engine does with it | kind |", "| --- | --- | --- |"]
    for f in fields:
        gloss, kind = _FIELD_DOC[f]
        lines.append(f"| `{f}` | {gloss} | {kind} |")
    lines += ["", "A project's `paper.toml` `[paper]` table may set these keys. Generated from the "
              "keys `load_config` reads.", "", "| key | what it controls |", "| --- | --- |"]
    for k in keys:
        lines.append(f"| `{k}` | {_PAPER_KEY_DOC[k]} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.stdout.write(render())
