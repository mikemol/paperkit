#!/usr/bin/env python3
"""Ζ·calc·interp — the GRADE as a cheap READING over a calc record, not a re-measurement.
Reads a pk_calc record {claim, baseline, sens} and emits the grade via the pure interpreter
grader._grade_from_sens(baseline, sens).  No sweep — the expensive calculation already ran in
pk_calc; this is an instant function of its output."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("paperkit")))
import grader  # noqa: E402

c = json.load(open(sys.argv[1]))
g = grader._grade_from_sens(c["baseline"], c["sens"])["grade"]
print(json.dumps({"claim": c["claim"], "grade": g}))
