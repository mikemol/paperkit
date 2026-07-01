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

Ζ·mutant·struct·node-kinds — a perturbation TOGGLES an element's presence, and a FILE's presence is
togglable like an import's (one artifact-kind down).  When `--site` is a FILE spec (no module to
mutate) the counterfactual is delivered by toggling that path in the sandbox instead of swapping a
.pyc:
    file+:<path>   INJECT an absent file (create it) — falsifies a "X does not exist" assertion (the
                   contrapositive of rm-next's roadmap-pending claim: if cli.py ships, the check must
                   fail).  The NEGATIVE-existence polarity, the file analog of import+.
    file-:<path>   DROP a present file (remove it) — falsifies a "X exists" assertion.  The POSITIVE
                   polarity, the file analog of import-.
The path is sandbox-relative, aligned with the check's own Path(__file__).resolve() root (the
hermetic sandbox keeps both in the same tree).  A file cell needs no --module/--mutant (nothing is
recompiled); it still stages the check's engine .pyc closure and runs it.

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
    ap.add_argument("--module", default="", help="the mutated module's .py path, e.g. paperkit/bib.py (empty for a file cell)")
    ap.add_argument("--mutant-py", default="", help="the mutated module SOURCE (pk_mutate; identity for ∅; empty for a file cell)")
    ap.add_argument("--mutant-pyc", default="", help="the mutated module BYTECODE (pk_pyc of it; empty for a file cell)")
    ap.add_argument("--check", required=True, help="the check script, e.g. paper/checks/claims.py")
    ap.add_argument("--claim", required=True)
    ap.add_argument("--site", required=True, help="the def-site label, recorded in the result")
    ap.add_argument("--content-path", default="", help="a content cell's target file (its substring toggled)")
    ap.add_argument("--content-textfile", default="", help="the substring to drop/inject, delivered as a file (no shell escaping)")
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
    op, sep, arg = a.site.partition(":")
    if op == "file+":
        # Ζ·mutant·struct·node-kinds — INJECT an absent file: its mere existence is the counterfactual
        # (an empty file suffices; the assertion tests .exists(), not content), so no module is mutated.
        p = pathlib.Path(arg)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("")
    elif op == "file-":
        pathlib.Path(arg).unlink(missing_ok=True)      # DROP a present file — the counterfactual absence
    elif op in ("content-", "content+"):
        # Ζ·mutant·struct·node-kinds (content) — TOGGLE a substring's presence in a staged file: the
        # precise DAG-EDGE perturbation (drop `result:paper` from the README bib → the "does the README
        # import the paper" grep fails).  The substring arrives as a FILE (no shell-escaping of quotes/
        # colons).  Unlink-then-write: remove the sandbox hardlink, never the source inode.
        text = pathlib.Path(a.content_textfile).read_text()
        f = pathlib.Path(a.content_path)
        orig = f.read_text()
        f.unlink(missing_ok=True)
        f.write_text(orig.replace(text, "") if op == "content-" else orig + text)
    else:
        # … deliver the ONE mutated module on BOTH paths (∅ = identity = no-op): its .pyc (used when
        # the module is IMPORTED) AND its .py source (used when the module is run as a MAIN SCRIPT — a
        # main script's bytecode is never read from __pycache__, so an entry-point module like
        # project.py would otherwise escape the mutation).
        mod = pathlib.Path(a.module)
        mod.unlink(missing_ok=True)   # Ξ·dag·eval: D may lie outside its own check's closure .py (a
        shutil.copyfile(a.mutant_py, mod)   # non-sensitive cell) → not staged; deliver the mutant anyway
        shutil.copyfile(a.mutant_pyc, slot(mod))

    flipped = subprocess.run([sys.executable, a.check, a.claim],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
    pathlib.Path(a.out).write_text(
        json.dumps({"claim": a.claim, "site": a.site, "flipped": flipped}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
