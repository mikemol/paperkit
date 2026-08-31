#!/usr/bin/env python3
"""Behavioral-boundary examples for the memory observation store — tools/mem_db.py.

⟨P, F, δ⟩ per the boundary practice.  The store keeps one row per OBSERVATION and derives the
reservation manifest as a query, so a bucket can say what it rests on.  Bounds: a manifest
reproduces from recorded cells, a narrower re-measure never lowers a reservation, and the minimum
delta is one cell's peak crossing a pow2 boundary.

    python3 paperkit/tests/boundaries_mem_db.py
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "tools"))
import mem_db as D

_fails = []
MB = 1048576


def check(desc, ok):
    print(f"  {'ok' if ok else 'XX'} {desc}")
    if not ok:
        _fails.append(desc)


def main() -> int:
    print("MEM-DB BOUNDARIES ⟨P, F, δ⟩")
    d = pathlib.Path(tempfile.mkdtemp())
    try:
        c = D.connect(d / "m.db")

        # ---- P: a manifest is a QUERY over observations ----
        D.record(c, [("lib", "file", "a", "a__calc", 200 * MB),
                     ("lib", "file", "b", "b__calc", 100 * MB)], run="r1")
        m = D.manifest(c, "lib")
        check("P: the resolution default is the pow2 of the WORST cell",
              m["file"] == 256)
        check("P: a claim below that default is recorded as an override",
              m["claims"] == {"b": 128})
        check("P: a claim AT the default is not an override (no redundant rows)",
              "a" not in m["claims"])

        # ---- the property JSON could not provide ----
        p = D.provenance(c, "lib")
        check("P: the bucket carries its EVIDENCE — cell count and the measured range",
              p["cells"] == 2 and p["min_mb"] == 100.0 and p["max_mb"] == 200.0)

        # ---- F: monotone. A narrower re-measure must not erode a reservation ----
        # A harvest sees only the cells that happened to run; a smaller reading is evidence of a
        # narrower measurement, never that a cell got cheaper.  Enforced by the upsert's `max`,
        # not by a hand-written merge — which is where the bug landed when it WAS hand-written.
        D.record(c, [("lib", "file", "a", "a__calc", 10 * MB)], run="r2-narrow")
        check("F: a LOWER reading for the same cell leaves the reservation unchanged",
              D.manifest(c, "lib")["file"] == 256)
        D.record(c, [("lib", "file", "a", "a__calc", 900 * MB)], run="r3-bigger")
        check("F: a HIGHER reading RAISES it — the rule is monotone, not frozen",
              D.manifest(c, "lib")["file"] == 1024)

        # ---- δ: one cell crossing a pow2 boundary is the whole difference ----
        c2 = D.connect(d / "n.db")
        D.record(c2, [("x", "def", "k", "k__c1", 256 * MB)])
        lo = D.manifest(c2, "x")["def"]
        D.record(c2, [("x", "def", "k", "k__c2", 257 * MB)])
        hi = D.manifest(c2, "x")["def"]
        check("δ: 256MB → 256; one more MB in a sibling cell → 512",
              (lo, hi) == (256, 512))

        # ---- P: a claim's reservation is the MAX over its cells (a def grid runs concurrently) ----
        check("P: a def claim's many cells reduce to their worst, not their mean",
              D.manifest(c2, "x")["def"] == 512)

        # ---- F: an unmeasured project yields an empty manifest, not a wrong one ----
        check("F: a project with no observations yields {} — absence is not a measurement",
              D.manifest(c, "never-measured") == {"claims": {}})
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print(f"MEM-DB BOUNDARIES: {'PASS' if not _fails else 'FAIL'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
