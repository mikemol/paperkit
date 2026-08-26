#!/usr/bin/env python3
"""Ζ·pi·effective — the EFFECTIVE-grade reading over a project's assembled grade records.

A per-claim grade record (`pk_grade` → read_grade.py) is a claim's SELF grade: what its own
witness measures.  The effective grade is that clamped by everything the claim rests on, and —
since Λ·pi·carry — by whatever it delegates to.  `pk_grade` cannot compute it: the rule is
per-claim by design (one calc in, one grade out) so that editing one module invalidates one
cell.  Clamping needs the whole project at once, so it belongs HERE, one level up, as a reading
over the assembled records plus the bib's edges.

WHY THIS EXISTS (the defect it closes).  grade.clamp() takes `owner_grades` — the other side of
a delegation edge — and looks each up in a flat dict.  If that dict is populated from the
owners' SELF grades, the lookup is a TRUNCATION: an owner whose own premise is weak reports
strong upward, and the taint stops one hop short of the importer, silently.  Populating it with
EFFECTIVE grades makes the same flat lookup legitimate — not a base case, but a memoized unfold
the owner already performed in its own project.  The recursion continues through the owner
instead of stopping at it.

Today this is invisible on paperkit's own tree: 1 of 42 library concepts carries a `rests-on`,
so self ≈ effective almost everywhere.  It becomes load-bearing the moment a library grows
grounding structure — which is exactly when nobody would be looking for it.

    effective.py <project-dir> <grade.json>... [--owners <project>=<effective.json> ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "paperkit"))
import bib      # noqa: E402
import grade    # noqa: E402


def _delegation(check: str) -> dict | None:
    """The delegation edge a crossing check names, as (owner, claim) — or None.

    Mirrors grader.grade_check's `delegates_to`, derived from the SAME check string, so the two
    cannot drift apart on what an edge points at."""
    typ, _, target = check.partition(":")
    if typ == "concept":
        return {"owner": "library", "claim": target, "verb": "concept"}
    if typ == "result":
        proj, _, claim = target.partition("#")
        return {"owner": proj, "claim": claim or None, "verb": "result"}
    return None


def records(project_dir: Path, grade_files: list) -> list:
    """Assemble {key, grade, rests-on, delegates_to} — the grade records joined to the bib's
    edges.  The grade files carry the measurement; the bib carries the structure."""
    F = bib.parse_project(project_dir)
    out = []
    for gf in grade_files:
        d = json.loads(Path(gf).read_text())
        k = d["claim"]
        f = F.get(k, {})
        r = {"key": k, "grade": d["grade"], "rests-on": f.get("rests-on", [])}
        edge = _delegation(f.get("check", ""))
        if edge:
            r["delegates_to"] = edge
        out.append(r)
    return out


def owner_grades(specs: list) -> dict:
    """{(owner, claim): {"grade", "effective_grade", "clamped_by"}} from `<project>=<eff.json>`.

    A GRADE IS TWO-DIMENSIONAL and both components cross the boundary.  `grade` is what the
    owner's own witness measures; `effective_grade` is that clamped by what the owner rests on.
    Carrying only one collapses a distinction the importer needs:

        owner A: self=vacuous     effective=vacuous    (its WITNESS is weak)
        owner B: self=behavioral  effective=vacuous    (its PREMISE is weak)

    Both arrive as "vacuous" if effective alone crosses, and the importer cannot tell whether to
    distrust the owner's witness or to chase the owner's premise.  Carrying only `grade` is the
    truncation this module exists to close.  So the edge transports the PAIR — and `clamped_by`
    with it, since a clamp that names nothing on the far side is a dead end for the reader.

    Clamping uses the effective component (it is the bound); the self component travels for the
    reader, and so that a later reading can distinguish the two shapes above without re-crossing."""
    og = {}
    for spec in specs:
        proj, _, path = spec.partition("=")
        for r in json.loads(Path(path).read_text())["claims"]:
            og[(proj, r["key"])] = {"grade": r["grade"],
                                    "effective_grade": r["effective_grade"],
                                    "clamped_by": r.get("clamped_by")}
    return og


def main(argv: list) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    owners, rest = [], []
    it = iter(range(len(argv)))
    i = 0
    while i < len(argv):
        if argv[i] == "--owners":
            owners = argv[i + 1:]
            break
        rest.append(argv[i])
        i += 1
    project_dir, grade_files = Path(rest[0]), rest[1:]
    rs = grade.clamp(records(project_dir, grade_files), owner_grades(owners))
    print(json.dumps({"project": project_dir.name or str(project_dir),
                      "claims": [{"key": r["key"], "grade": r["grade"],
                                  "effective_grade": r["effective_grade"],
                                  "clamp": r["clamp"], "clamped_by": r["clamped_by"],
                                  "clamp_path": r["clamp_path"],
                                  "unresolved": r["unresolved"]}
                                 for r in sorted(rs, key=lambda r: r["key"])]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
