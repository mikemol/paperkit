#!/usr/bin/env python3
"""paperkit.bib — the ONE parser + data model for a warrants `.bib` (the claim-DAG).

A `.bib` entry is a claim: `@type{key, field = {value}, ...}`.  This module is the
single source of truth for that grammar and the small data-model over it (config
load, rubric, dependency order, placement).  It was previously three parsers —
the projector's field-whitelist `entries`, footdeps' line scanner for `reads`,
and coherence's line scanner for `rests-on` — each re-deriving the format and
disagreeing on which fields survive (the whitelist dropped `reads`).  Now there is
one: `parse()` returns the FULL record per claim and every consumer projects the
fields it wants.

Scalar fields are carried verbatim (LaTeX un-expanded — the projector cleans on
render); the edge/token fields (`from`, `rests-on`, `reads`) are lists.
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import re

# scalar fields carried verbatim (the projector + checks read these)
_SCALAR = ("title", "author", "year", "note", "section", "claim",
           "check", "glue", "join", "move", "emit", "mem", "link", "depth")
# list-valued fields.  `from` = prose-order edge (dep_order + glue); `rests-on` =
# grounding/entailment edge (adequacy clamping, NOT prose) — the two are often
# reversed (prose runs general→specific, grounding specific→general); `reads` =
# the declared cross-package footprint (the declare+audit source, Ζ·foot).
_LIST = ("from", "rests-on", "reads")


def parse(path: Path) -> dict:
    """{key: {field: value, _src}} for one .bib (a missing file → {})."""
    out = {}
    path = Path(path)
    if path.exists():
        for m in re.finditer(r"@\w+\{\s*([^,\s]+)\s*,(.*?)\n\}", path.read_text(), re.S):
            key, body = m.group(1), m.group(2)
            f = {"_src": path.name}
            for name in _SCALAR:
                fm = re.search(r"\b" + name + r"\s*=\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", body)
                if fm:
                    f[name] = fm.group(1)
            for name in _LIST:
                fr = re.search(r"\b" + name + r"\s*=\s*\{([^}]*)\}", body)
                f[name] = [a for a in re.split(r"[,\s]+", fr.group(1)) if a] if fr else []
            out[key] = f
    return out


def _bibpath(project: Path, b: str) -> Path:
    """Resolve a warrants token to a path.  A bare basename is relative to the project dir; a Bazel
    LABEL (//pkg:file, //:path/file, @repo//…) is a bib imported from the concept library, resolved
    repo-root-relative — correct when the importer IS the root project (project == repo root, the
    README-import case).  Mirrors the generator's label branch so ONE warrants list drives both."""
    if b.startswith("//") or ":" in b or b.startswith("@"):
        pkg, _, name = b.split("//", 1)[1].partition(":")
        return project / (f"{pkg}/{name}" if pkg else name)
    return project / b


def load_config(project: Path) -> dict:
    cfg = project / "paper.toml"
    if not cfg.exists():
        sys.exit(f"paperkit: no paper.toml in {project}")
    p = tomllib.loads(cfg.read_text()).get("paper", {})
    return {
        "title": p.get("title", "Untitled"),
        "subtitle": p.get("subtitle", ""),
        "rubric": project / p.get("rubric", "rubric.tsv"),
        "bibs": [_bibpath(project, b) for b in p.get("warrants", ["warrants.bib"])],
        "out": project / p.get("out", "paper.md"),
        "numbered": p.get("numbered", True),
        "references": p.get("references", True),
        "adequacy": p.get("adequacy", False),   # Ζ·project: emit a Δ-adequacy Bazel test for this project
    }


def rubric(path: Path) -> list:
    out = []
    for ln in path.read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "\t" in ln:
            # key <TAB> title [<TAB> scheme …]; the title is the 2nd column only.
            # A 3rd column (rhetorical scheme) is read by rhetoric.py, not here.
            parts = ln.split("\t")
            out.append((parts[0].strip(), parts[1].strip()))
    return out


def dep_order(keys: list, F: dict) -> list:
    seen, out = set(), []

    def visit(k):
        if k in seen or k not in keys:
            return
        seen.add(k)
        for a in F.get(k, {}).get("from", []):
            visit(a)
        out.append(k)

    for k in keys:
        visit(k)
    return out


def is_placed(f: dict) -> bool:
    """A warrant projected as a block (emit:) or a figure — placed verbatim, not
    woven into prose, and so covered by its placement rather than a citation."""
    return bool(f.get("emit")) or f.get("check", "").startswith("figure:")


def rests_closure(seed: set, F: dict) -> tuple:
    """The transitive closure of `seed` under `rests-on` (grounding) edges.

    A cited/placed claim's grounding premises are part of the argument whether or
    not a marker for them survives in the rendered prose (plain/footnote render no
    [@key]; adjacent and cross-scope edges render nothing on ANY target) — so the
    verified set must include every claim REACHABLE from the seed along rests-on,
    recursively.  Cycles are handled (each key is visited once).  Returns
    (reachable, dangling): reachable ⊇ seed ∩ F; dangling is the set of
    (claim, target) edges whose target is defined in no bib — a broken grounding.
    """
    seen, dangling = set(), set()
    stack = [k for k in seed if k in F]
    while stack:
        k = stack.pop()
        if k in seen:
            continue
        seen.add(k)
        for y in F[k].get("rests-on", []):
            if y not in F:
                dangling.add((k, y))
            elif y not in seen:
                stack.append(y)
    return seen, dangling
