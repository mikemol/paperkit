#!/usr/bin/env python3
"""Τ·mem·db — the OBSERVATION store behind the reservation ladder.

WHY A TABLE AND NOT A JSON OF BUCKETS.  `mem.json` stores the CONCLUSION (`{"file": 256}`) and
discards the evidence, so it cannot answer the question its own numbers provoke: where did 256
come from, over how many cells, measured when, and which cell was the outlier?  That gap cost a
real half hour — a manifest read `file: 512, 41 overrides` and later `file: 256, 2`, and with no
provenance there was no way to tell a regression from a better measurement.  (It was the latter:
a cold run measured 163 cells, max 216MB, so 256 is right and 512 was never justified.  I spent
that half hour reporting destroyed data that was never real.)

The store keeps one row per OBSERVATION.  A manifest is then a QUERY over it, which makes the
bucketing a projection rather than a baked-in loss: re-bucketing for a different _RS ladder or a
different safety factor is a different SELECT, not a re-measurement.

WHY SQLITE AND NOT dbm.  They are the same thing now — CPython 3.13 ships `dbm.sqlite3` and this
box has no `dbm.gnu`, so "dbm" IS sqlite with a key-value shape imposed on top.  Measured at our
corpus size (163 entries): dbm 12,288 bytes, a real table 16,384.  The 4KB buys the columns
(project, resolution, claim, cell, bytes, run, at); with dbm that structure would have to be
encoded into key strings, which is the JSON problem wearing a different hat.

CONCURRENCY IS THE OTHER REASON.  Warm-up means many cells depositing peaks as a side effect of
work that runs anyway.  `INSERT ... ON CONFLICT DO UPDATE SET bytes = max(...)` is one statement
the database serialises; the JSON equivalent is a read-modify-write across concurrent writers,
and hand-rolling its "raise, never lower" rule is exactly where a bug already landed.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mem_learn import pow2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS peak (
  project    TEXT NOT NULL,
  resolution TEXT NOT NULL,          -- 'file' | 'def'
  claim      TEXT NOT NULL,
  cell       TEXT NOT NULL,          -- the action name; a def claim has many
  bytes      INTEGER NOT NULL,
  run        TEXT NOT NULL DEFAULT '',
  at         INTEGER NOT NULL,
  PRIMARY KEY (project, resolution, claim, cell)
);
CREATE INDEX IF NOT EXISTS peak_by_claim ON peak (project, resolution, claim);
"""


def connect(db: Path) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(db), timeout=30)
    c.execute("PRAGMA journal_mode=WAL")          # concurrent readers during a harvest
    c.executescript(_SCHEMA)
    return c


def record(c: sqlite3.Connection, rows: list, run: str = "") -> int:
    """Insert observations. MONOTONE per cell: a re-measure may RAISE a peak, never lower it.

    A harvest sees only the cells that happened to run, and a smaller reading is not evidence a
    cell got cheaper — it is evidence of a different (often narrower) measurement.  The `max` in
    the upsert is that rule, enforced by the database rather than by a hand-written merge.
    """
    now = int(time.time())
    c.executemany(
        "INSERT INTO peak (project,resolution,claim,cell,bytes,run,at) VALUES (?,?,?,?,?,?,?) "
        "ON CONFLICT(project,resolution,claim,cell) DO UPDATE SET "
        "  bytes = max(bytes, excluded.bytes), run = excluded.run, at = excluded.at "
        "WHERE excluded.bytes > peak.bytes",
        [(p, r, cl, ce, b, run, now) for p, r, cl, ce, b in rows])
    c.commit()
    return len(rows)


def manifest(c: sqlite3.Connection, project: str) -> dict:
    """The reservation manifest as a QUERY — the same shape mem.json always had.

    A claim's reservation is the MAX over its cells: a def grid's cells run concurrently and each
    must fit, so the worst cell is the number, not the typical one.
    """
    out: dict = {"claims": {}}
    per_claim = c.execute(
        "SELECT resolution, claim, max(bytes) FROM peak WHERE project=? GROUP BY resolution, claim",
        (project,)).fetchall()
    if not per_claim:
        return out
    by_res: dict = {}
    for res, claim, b in per_claim:
        by_res.setdefault(res, []).append((claim, pow2(b / (1024 * 1024))))
    for res, rows in by_res.items():
        out[res] = max(b for _, b in rows)
        for claim, b in rows:
            if b != out[res]:
                out["claims"][claim] = b
    return out


def provenance(c: sqlite3.Connection, project: str) -> dict:
    """What a bucket RESTS ON — the question a JSON of conclusions cannot answer."""
    row = c.execute(
        "SELECT count(*), min(bytes), max(bytes), max(at), count(DISTINCT run) "
        "FROM peak WHERE project=?", (project,)).fetchone()
    n, lo, hi, at, runs = row
    return {"cells": n, "min_mb": round((lo or 0) / 1048576, 1),
            "max_mb": round((hi or 0) / 1048576, 1),
            "measured_at": at, "runs": runs}


def main(argv: list) -> int:
    if not argv:
        print("usage: mem_db.py <db> {manifest|provenance} <project>", file=sys.stderr)
        return 2
    db, verb, project = Path(argv[0]), argv[1], argv[2]
    c = connect(db)
    print(json.dumps(manifest(c, project) if verb == "manifest" else provenance(c, project),
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
