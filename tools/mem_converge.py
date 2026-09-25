#!/usr/bin/env python3
"""Τ·mem·converge — has the reservation loop CONVERGED, or is it silently running on the floor?

The learning loop (observe → harvest → project → size) warms up: a first pass runs unsized and
deposits peaks, a later pass is sized from them.  Nothing said when that warm-up was DONE, so a
project could sit at the cold-start floor indefinitely and every board stayed green — measured
2026-08-25: library ran 55,447 grid cells at the 4MB floor because its manifest had no `def`
key, paying a 4-rung OOM climb per cell, and the only visible symptom was a climb counter nobody
was reading.  A loop that cannot say whether it has converged cannot be trusted to have.

CONVERGENCE, as a property of the artifacts rather than a feeling:

  a project that HAS a grid (pk_eval cells in its generated BUILD) must have a `def` bucket in
  its manifest, and every one of its cells must carry a reservation > 0.

⚑ ELIGIBILITY FIRST.  A project with no grid needs no `def` bucket, and counting it as a gap is
the census-over-the-wrong-population error this check exists to avoid: `mem = 0` is not "sized",
it is the floor sentinel, so "has a mem attr" is the wrong predicate and "carries a value" is the
right one.

    mem_converge.py <bazel-external-dir> [--check]

Prints one line per project with a grid.  --check exits 1 if any has not converged.


    ⚑ INSTRUMENT, NOT A GATE (Ζ·mem·unwired).  This file is referenced by no
    BUILD.bazel, no .bzl, no .githooks hook and no warrant — nothing runs it, so
    nothing would notice it breaking.  Re-verify its output at each use rather than
    trusting a past reading; an instrument earns trust per-use, a gate by proven
    soundness in both directions, and this has only ever been the former.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# ⚑ ONE CELL PER LINE, not a paren-bounded scan.  A site string can CONTAIN a `)` — measured:
# `content-:report/gen.py:_delta("paper")` — so `pk_eval\(name[^)]*` stops inside the site and
# never reaches the `mem` attr, reporting a correctly-sized cell as unsized.  (This checker's
# first run "found" exactly one such cell and the finding was its own regex.)
_EVAL = re.compile(r"^pk_eval\(name.*$", re.M)
_MEM = re.compile(r"mem = (\d+)")


# ⚑ Ζ·converge·path — A PROJECT'S NAME IS NOT ITS PATH, AND MODULE.bazel OWNS THE MAPPING.
#
# This built the manifest path as `"%s/mem.json" % proj` from the external repo's name
# (`+bib+paperkit_library` -> `library`), with a hand-written `if proj == "root"` special case for
# the one mismatch anyone had noticed.  MEASURED 2026-09-13: it reported `library` as
# `def=MISSING NOT CONVERGED` over 67,796 cells while `paperkit/library/mem.json` sits on disk
# carrying `"def": 64` — byte-identical in shape to paper's, which the same run called converged.
# The library moved (`library/` -> `paperkit/library/`) and this tool's copy of the mapping did not.
#
# The `if proj == "root"` case was the tell: MODULE.bazel already writes that mapping as
# `project = "."`, so the special case was a second copy of a fact with an owner.  Both the
# special case and the bug are the SAME defect — project PATH conflated with project NAME, which
# `tools/bibtex.bzl` was bitten by too (there it DROPPED a target rather than misreporting).
#
# So: ask the owner.  `bib.project(name = ..., project = ...)` is the declaration; parse it rather
# than re-deriving a path from a repo name that only coincidentally matches for most projects.
def _manifest_rel(root, proj):
    """<project path>/mem.json, resolved through MODULE.bazel's own name->path declaration."""
    mod = root / "MODULE.bazel"
    path = None
    if mod.is_file():
        try:
            for m in re.finditer(r'bib\.project\(([^)]*)\)', mod.read_text()):
                body = m.group(1)
                nm = re.search(r'name\s*=\s*"paperkit_([^"]+)"', body)
                pp = re.search(r'project\s*=\s*"([^"]+)"', body)
                if nm and pp and nm.group(1) == proj:
                    path = pp.group(1)
                    break
        except OSError:
            path = None
    if path is None:
        # ⚑ NAMED, never silently guessed: an undeclared project is a finding about the OWNER.
        print("mem-converge: %s is not declared in MODULE.bazel — falling back to its name as a "
              "path, which is the very conflation this function exists to avoid" % proj,
              file=sys.stderr)
        path = proj
    return "mem.json" if path == "." else "%s/mem.json" % path


def survey(external: Path, root: Path) -> list:
    """[(project, cells, floor_cells, def_bucket)] for every project with a grid."""
    out = []
    for d in sorted(external.glob("*paperkit_*")):
        build = d / "BUILD.bazel"
        if not build.is_file():
            continue
        proj = d.name.split("paperkit_")[-1]
        try:
            text = build.read_text()
        except OSError:
            continue
        cells = _EVAL.findall(text)
        if not cells:
            continue                                  # no grid → no def bucket owed
        # AT THE FLOOR = no `mem` attr at all, or `mem = 0` (calc.bzl's unmeasured sentinel).
        # Both fall back to the cold-start floor; only a positive value is a learned reservation.
        floor = 0
        for c in cells:
            m = _MEM.search(c)
            if m is None or m.group(1) == "0":
                floor += 1
        man = root / _manifest_rel(root, proj)
        bucket = None
        if man.is_file():
            import json
            try:
                bucket = json.loads(man.read_text()).get("def")
            except (OSError, ValueError):
                bucket = None
        out.append((proj, len(cells), floor, bucket))
    return out


def main(argv) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    rows = survey(Path(args[0]), Path(args[1]) if len(args) > 1 else Path.cwd())
    if not rows:
        print("mem-converge: no project has a grid — nothing to converge", file=sys.stderr)
        return 2
    bad = []
    for proj, cells, floor, bucket in rows:
        ok = bucket is not None and floor == 0
        print("  %-11s cells=%-7s at-floor=%-7s def=%-6s %s"
              % (proj, cells, floor, bucket if bucket is not None else "MISSING",
                 "converged" if ok else "NOT CONVERGED"))
        if not ok:
            bad.append(proj)
    if bad:
        print("mem-converge: %d of %d project(s) have NOT converged: %s — run an observe pass "
              "(--config=memobserve), then mem_harvest.py + mem_project.py, then refetch"
              % (len(bad), len(rows), ", ".join(bad)), file=sys.stderr)
        return 1
    print("mem-converge: all %d grid project(s) converged" % len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
