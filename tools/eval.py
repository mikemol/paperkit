#!/usr/bin/env python3
"""Ζ·mutant·eval — run a claim's check against the engine RUN OFF ITS .pyc BUILD ARTIFACTS, with ONE
module's bytecode swapped for its mutant, and report whether the mutation FLIPS the check.

The engine is compiled once (//paperkit:pyc, Ζ·pyc·engine) and staged as `paperkit/<relpath>.pyc`
beside the source `paperkit/<relpath>.py`.  This tool places each precompiled .pyc at its real
import location — `paperkit/<dir>/__pycache__/<stem>.<cache-tag>.pyc` — so Python runs the bytecode
directly (UNCHECKED_HASH ⇒ the source is never rechecked; see tools/pyc.py).  The counterfactual is
delivered by overwriting the ONE mutated module's __pycache__ slot with its mutant .pyc — the .py
stays original (only for findability + __file__).  The ∅ baseline passes the module's own identity
.pyc, a no-op swap.  No import-time compilation: the def-sweep compiles the engine once, not per eval.

Idempotency: invoke this tool by an ABSOLUTE interpreter path so sys.executable is populated — the
check re-spawns the projector as [sys.executable, …] (see the history of the '' spurious-flip bug)."""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine-dir", required=True, help="the staged engine dir, e.g. paperkit")
    ap.add_argument("--module", required=True, help="the mutated module's .py path, e.g. paperkit/bib.py")
    ap.add_argument("--mutant-py", required=True, help="the mutated module SOURCE (pk_mutate; identity for ∅)")
    ap.add_argument("--mutant-pyc", required=True, help="the mutated module BYTECODE (pk_pyc of it)")
    ap.add_argument("--check", required=True, help="the check script, e.g. paper/checks/claims.py")
    ap.add_argument("--claim", required=True)
    ap.add_argument("--site", required=True, help="the def-site label, recorded in the result")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    tag = sys.implementation.cache_tag                       # e.g. cpython-313 — matches THIS runtime

    def slot(py_path):                                       # paperkit/x.py → paperkit/__pycache__/x.<tag>.pyc
        p = pathlib.Path(py_path)
        d = p.parent / "__pycache__"
        d.mkdir(parents=True, exist_ok=True)
        return d / (p.stem + "." + tag + ".pyc")

    # place every precompiled engine .pyc (staged as paperkit/<relpath>.pyc) at its import location
    for pyc in pathlib.Path(a.engine_dir).rglob("*.pyc"):
        if "__pycache__" in pyc.parts:
            continue
        shutil.move(str(pyc), str(slot(pyc.with_suffix(".py"))))
    # … then deliver the ONE mutated module on BOTH paths (∅ = identity = no-op): its .pyc (used when
    # the module is IMPORTED) AND its .py source (used when the module is run as a MAIN SCRIPT — a
    # main script's bytecode is never read from __pycache__, so an entry-point module like project.py
    # would otherwise escape the mutation).
    mod = pathlib.Path(a.module)
    mod.unlink()
    shutil.copyfile(a.mutant_py, mod)
    shutil.copyfile(a.mutant_pyc, slot(mod))

    flipped = subprocess.run([sys.executable, a.check, a.claim],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
    pathlib.Path(a.out).write_text(
        json.dumps({"claim": a.claim, "site": a.site, "flipped": flipped}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
