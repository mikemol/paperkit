#!/usr/bin/env python3
"""Ζ·report·records — a project's Δ table, ASSEMBLED FROM THE BUILD GRAPH'S OWN GRADE RECORDS.

    grades_rec.py <meta.json> <claim__grade.grade.json ...>   → JSON list on stdout

`meta.json` is written by the bib extension (tools/bibtex.bzl) at generation: one entry per claim
with a check and a section, IN BIB ORDER — {key, check, section, rests-on, tier}.  The grade
records are the per-claim `<claim>__grade` outputs that pk_adequacy already aggregates for //:hook.

⚑ WHY NOT `discriminate.py --json <project>` IN ONE CELL.  That was the first construction, and a
single cell cannot answer it: its cross-project checks (concept:/result:) are UNRESOLVABLE there
and its toolchain checks run in the wrong pool — measured 2026-09-25, 29 unresolvable for paper
alone while //:hook was green.  In the graph each claim has its own cell; this reads THOSE results.

⚑ WHAT CHANGES, STATED.  These are the grades the adequacy gate enforces, not a second in-process
grading: witness claims are graded from the __dcalc grid, so `tests` and the counts inside `why`
can differ from discriminate's own file sweep.  A claim with NO grade record (tier local /
toolchain, or a non-mechanical check — gated, never swept) is listed as NOT Δ-GRADED and kept OUT
of the clamp: an unknown rung would otherwise rank lowest and drag its dependents down.

The clamp is the engine's own fold (paperkit/grade.py `clamp`), never re-implemented here.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("paperkit")))
import grade  # noqa: E402

meta = json.loads(Path(sys.argv[1]).read_text())
recs = {}
for p in sys.argv[2:]:
    # ⚑ KEY BY THE TARGET, NOT BY THE RECORD'S `claim`.  A `concept:` claim's grade reads the
    # library's IMPORTED certificate, and read_grade.py writes THAT certificate's claim name
    # (`graded-key`), not the view's key (`key-graded`) — keyed on `claim`, all five of paper's
    # concept claims read as ungraded.  The file is `<view key>__grade.grade.json` by construction.
    recs[Path(p).name.split("__grade")[0]] = json.loads(Path(p).read_text())

graded, out = [], []
for m in meta:
    k = m["key"]
    base = {"key": k, "check": m["check"], "section": m["section"], "rests-on": m["rests-on"]}
    if k in recs:
        r = recs[k]
        base.update(grade=r["grade"], tests=r.get("tests", []), baseline=r.get("baseline", ""),
                    why=r.get("why", ""), not_higher=r.get("not_higher", ""),
                    not_lower=r.get("not_lower", ""))
        graded.append(base)
    else:
        base.update(grade="not graded", why=f"gated, not Δ-graded (no grade record; {m['tier']} tier)",
                    not_higher="", not_lower="")
    out.append(base)

by_check = {}
for r in out:
    by_check.setdefault(r["check"], []).append(r["key"])
for r in out:
    r["shared_with"] = [o for o in by_check[r["check"]] if o != r["key"]]

grade.clamp(graded, keys={m["key"] for m in meta})   # mutates the graded records in place
print(json.dumps(out))
