#!/usr/bin/env python3
"""Τ·mem·harvest — collect whatever cell peaks EXIST and fold them into a project's manifest.

WHY THIS IS NOT A BAZEL ACTION.  The obvious wiring — have `mem_learn` depend on every cell whose
peak it wants — inverts the economics: paper's def grid is 52,584 pk_eval cells, so the manifest
that exists to make the sweep affordable would first require running the sweep UNSIZED (measured:
41,468 deps on one action).  A measurement must not cost what it is meant to save.

So the cells write their peaks as a SIDE EFFECT of work that runs anyway, and this is a reading
over the output tree afterwards.  The consequence is that the measurement WARMS UP rather than
being available up front:

    pass 1   the sweep runs on the cold-start floor, over-reserved, and deposits peaks
    harvest  those peaks fold into mem.json
    pass 2   the sweep is sized from measurement

A first pass may be mis-sized.  That is acceptable because it fails FAST and retries fast — far
cheaper than a barrier that cannot be crossed the first time at all, which is what the dependency
version would have been.

MERGE, NEVER REPLACE.  A harvest sees only the cells that happened to run: a warm build re-executes
few, an interrupted one fewer still.  Overwriting a manifest with a partial harvest would DELETE
measurements an earlier pass established — nearly shipped exactly that: a warm observe produced a
manifest with no `def` key, and a plain copy would have dropped a real `def: 256`.  So each key is
only ever raised into place, never removed by absence.

    mem_harvest.py <project-dir> [--out FILE] [--bazel-out DIR]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mem_learn import pow2 as pow2_bucket
from mem_learn import resolution


def peaks_for(project: str, tree: Path) -> dict:
    """{(resolution, claim): max_mb} over every readable .peak under `tree` for this project.

    MAX, not mean: a grid's cells run concurrently and each must fit, so the reservation a claim
    needs is its worst cell, not its typical one.
    """
    out: dict = {}
    for f in tree.rglob("*.peak"):
        if f"paperkit_{project}" not in str(f) and f"/{project}/" not in str(f):
            continue
        res, claim = resolution(f.stem)
        if res is None:
            continue
        try:
            raw = f.read_text().strip()
        except OSError:
            continue
        if not raw.isdigit():                 # "unavailable:*" or a clean 0 — carries no measurement
            continue
        mb = int(raw) / (1024 * 1024)
        if mb <= 0:
            continue
        # keyed by CELL: a def claim has many, and the store keeps each so the manifest's max
        # can be recomputed for a different bucket ladder without re-measuring.
        out[(res, claim, f.stem)] = max(out.get((res, claim, f.stem), 0), mb)
    return out


def deposit(db: Path, project: str, measured: dict, run: str = "") -> int:
    """Record observations in the store.  MONOTONICITY IS THE DATABASE'S JOB now.

    This used to be a hand-written merge over mem.json, and the hand-written version had the bug:
    a harvest sees only the cells that happened to run, and taking max over THAT harvest lowered
    library's manifest from 512/41-overrides to 256/2 on a narrow pass.  `ON CONFLICT ... SET
    bytes = max(bytes, excluded.bytes)` is the same rule as one clause the database enforces, and
    it cannot be got wrong the way the merge was.
    """
    import mem_db as D
    c = D.connect(db)
    rows = [(project, res, claim, cell, int(mb * 1024 * 1024))
            for (res, claim, cell), mb in measured.items()]
    return D.record(c, rows, run=run)


def main(argv: list) -> int:
    if not argv:
        print("usage: mem_harvest.py <project-dir> [--db FILE] [--bazel-out DIR] [--run ID]",
              file=sys.stderr)
        return 2
    proj_dir = Path(argv[0])
    project = "root" if proj_dir.resolve().name == "paperkit" else proj_dir.name
    def opt(n, d=None):
        return argv[argv.index(n) + 1] if n in argv and argv.index(n) + 1 < len(argv) else d
    repo = proj_dir.resolve() if project == "root" else proj_dir.resolve().parent
    tree = Path(opt("--bazel-out") or (repo / "bazel-out"))
    db = Path(opt("--db") or (repo / "mem.sqlite"))
    if not tree.exists():
        print(f"mem-harvest: no output tree at {tree} — nothing to harvest", file=sys.stderr)
        return 0
    measured = peaks_for(project, tree)
    if not measured:
        print(f"mem-harvest: {project}: no readable peaks (run under --config=memobserve first)",
              file=sys.stderr)
        return 0                              # absent measurement is not an error
    n = deposit(db, project, measured, run=opt("--run", ""))
    res = sorted({r for r, _, _ in measured})
    print(f"mem-harvest: {project}: {n} observation(s) over {res} → {db}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
