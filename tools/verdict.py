#!/usr/bin/env python3
"""Ζ·calc·interp — the VERDICT reading of a calc record: pass iff the measured baseline holds.  A
cheap PURE read over the cached {baseline, sens} record (no re-sweep).  Parses the JSON (vs grepping
the text — `"baseline": true` could appear nested or reformatted), so the reading tracks the record's
structure, not its byte layout."""
import json
import pathlib
import sys


def main(argv):
    calc, out = argv
    rec = json.loads(pathlib.Path(calc).read_text())
    pathlib.Path(out).write_text(
        json.dumps({"verb": "verdict", "verdict": "pass" if rec.get("baseline") else "fail"}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
