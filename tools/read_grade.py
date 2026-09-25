#!/usr/bin/env python3
"""Ζ·calc·interp — the GRADE as a cheap READING over a calc record, not a re-measurement.
Reads a pk_calc record {claim, baseline, sens} and emits the grade via the pure interpreter
grade._grade_from_sens(baseline, sens).  No sweep — the expensive calculation already ran in
pk_calc; this is an instant function of its output.  Imports paperkit.grade, the LADDER LEAF
(Μ·grade), not the whole grader: a reading needs the interpretation, never the sweep.

⚑ Ψ·grade·carry — CONSTRUCT ONCE, READ MANY.  CARRY THE WHOLE READING, NOT JUST THE RUNG.

The CONSTRUCTION is pk_calc: the expensive measurement, {claim, baseline, sens}, run once per
claim in the build graph.  Several READINGS sit over that one artifact, and Ζ·calc·interp already
says so — "ONE cached sweep (pk_calc) feeds the verdict reading here (and the grade reading
below); the redundant verdict run + the adequacy re-sweep collapse into it."

  * grade      — this file: _grade_from_sens, pure, per-claim
  * coherence  — coherence._records_from_calcs + the ∂² faces, over a whole project's records
  * clamp      — a pure fold over the same assembled records (what _delta_section needs)

`_grade_from_sens` returns {grade, tests, baseline, why, not_higher, not_lower} — the rung AND the
justification for it.  This file read `["grade"]` and DISCARDED FIVE OF SIX FIELDS before writing,
so every `<claim>__grade.grade.json` in the build graph was a bare {claim, grade}.  That is a
READING throwing away what the CONSTRUCTION produced, and it is load-bearing twice:

  * report/gen.py's `_delta_section` renders exactly those justification columns, so it could not
    read the build graph's records and instead re-ran the whole def-resolution sweep IN-PROCESS,
    once per project, once per asset — measured at 33 minutes for ONE asset (Ψ), on the legacy
    serial path the ledger says never to run.
  * Δ-F9 recorded the Bazel grade records as carrying "no fingerprint" — `tests` IS the
    fingerprint, computed here and dropped.

The calculation already happened; this is a pure function of its output, so carrying the rest
costs only the bytes.  ⚑ `grade` stays FIRST and unchanged in the object, so every existing
consumer (pk_adequacy's `--field grade` aggregation, the adequacy assert) reads exactly what it
read before — ADDITIVE, not a shape change.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("paperkit")))
import grade

c = json.load(open(sys.argv[1]))
# ⚑ Ζ·broken·offaxis — READ THE TRISTATE.  `baseline` serializes UNREACHABLE and False both as 0
# (grader._Unreachable is an int subclass), so the record carries `reachable: false` beside it as a
# separate axis (discriminate.py, on the decisions_unasserted model).  Absent ⇒ reachable, which is
# the honest default for every record written before the axis existed and for every check that ran.
# Without this the reading defaults reachable=True and reports "repo is not green" about a check
# that merely could not RUN — the false statement grade.py:86-92 records as measured twice.
r = grade._grade_from_sens(c["baseline"], c["sens"], reachable=c.get("reachable", True))
print(json.dumps({"claim": c["claim"], "grade": r["grade"], "tests": r.get("tests", []),
                  "baseline": r.get("baseline", ""), "why": r.get("why", ""),
                  "not_higher": r.get("not_higher", ""), "not_lower": r.get("not_lower", "")}))
