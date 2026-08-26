#!/usr/bin/env python3
r"""Behavioral-boundary examples for Ζ·dag·regen — the generator that OWNS dag.bzl can write it.

paperkit/dag.bzl carries "REGENERATE (never hand-edit)" in its own header and bnd-components gates
it FRESH against tools/imports.py.  Both were true and the loop was still open: the generator
emitted edges to stdout and had no writer, so the only way past a stale-dag red was to hand-edit
the file whose header forbids hand-editing.  A generator built and left unwired.

What is pinned is the ROUND TRIP, not the flag's existence: add a real import edge and --check must
red naming its repair without mutating anything; --write must fix it; remove the edge, regenerate,
and dag.bzl must return BYTE-IDENTICAL.  That last arm is what makes --write a repair rather than a
rewriter — a regenerator that does not round-trip quietly rewrites history on every run.

HERMETIC BY CONSTRUCTION.  The probe mutates a COPY of the engine, never the live tree.  The first
draft mutated paperkit/genre.py in place and restored it in a finally; it passed alone and broke
boundaries_memoize when run concurrently, because that suite keys grades on an ENGINE EPOCH and a
sibling touching any engine file invalidates its fixture mid-run.  A restore-in-a-finally bounds
damage in TIME and does nothing for a concurrent reader — and the gate resolves checks in a thread
pool, so "restored afterwards" is not "never observed changed".

(Four probe defects in this session came from an edit that never landed, so the arms ASSERT the
mutation is present before drawing any conclusion from it.)

⟨P, F, δ⟩ per the boundary practice.

Run:  python3 paperkit/tests/boundaries_dag_regen.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ENG = Path(__file__).resolve().parent.parent
ROOT = ENG.parent
ANCHOR = "import sys\n"
EDGE = "import sys\nimport durable  # boundaries_dag_regen probe\n"


def main() -> int:
    fails = []

    def check(desc, cond):
        print(f"  {'ok ' if cond else 'XX '}{desc}")
        if not cond:
            fails.append(desc)

    print("Ζ·dag·regen — the generator writes what it owns\n")

    live_before = (ENG / "genre.py").read_bytes()
    live_dag_before = (ENG / "dag.bzl").read_bytes()

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        ign = shutil.ignore_patterns("__pycache__", "*.pyc")
        shutil.copytree(ENG, work / "paperkit", ignore=ign)
        shutil.copytree(ROOT / "tools", work / "tools", ignore=ign)
        eng = work / "paperkit"
        imports_py = str(work / "tools" / "imports.py")
        dag, probe = eng / "dag.bzl", eng / "genre.py"

        def run(*args):
            r = subprocess.run([sys.executable, imports_py, *args],
                               capture_output=True, text=True)   # Λ·separate-filehandles
            return r.returncode, (r.stdout + r.stderr)

        pristine_dag = dag.read_text()
        pristine_probe = probe.read_text()
        if ANCHOR not in pristine_probe:
            print(f"  XX fixture anchor {ANCHOR!r} absent from {probe.name}")
            return 1

        rc, _ = run("--check")
        check("P: --check is GREEN on a fresh tree", rc == 0)

        # δ — one real import edge, nothing else changed.
        probe.write_text(pristine_probe.replace(ANCHOR, EDGE, 1))
        check("the probe edit LANDED (assert the fixture, never assume it)",
              "boundaries_dag_regen probe" in probe.read_text())

        rc, out = run("--check")
        check("F: --check REDS on a stale dag.bzl", rc == 1)
        check("   ...and names the repair, not only the breach", "--write" in out)
        check("   ...without writing anything (a check must not mutate)",
              dag.read_text() == pristine_dag)

        rc, _ = run("--write")
        check("--write repairs it", rc == 0)
        check("   ...and the new edge is actually IN the file",
              '"genre.py": ["durable"]' in dag.read_text())
        rc, _ = run("--check")
        check("   ...so --check is green again", rc == 0)

        probe.write_text(pristine_probe)
        run("--write")
        check("ROUND TRIP: dag.bzl returns BYTE-IDENTICAL once the edge is removed",
              dag.read_text() == pristine_dag)

        rc, out = run("--write")
        check("--write is IDEMPOTENT (a no-op run says so and changes nothing)",
              rc == 0 and "already fresh" in out and dag.read_text() == pristine_dag)

    # No restore arm and no finally: the mutated tree was a temp copy, now discarded.
    check("the LIVE engine module was never modified",
          (ENG / "genre.py").read_bytes() == live_before)
    check("the LIVE dag.bzl was never modified",
          (ENG / "dag.bzl").read_bytes() == live_dag_before)

    print()
    if fails:
        print(f"dag-regen boundaries: FAIL ({len(fails)})")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("dag-regen boundaries: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
