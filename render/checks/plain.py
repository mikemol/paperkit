#!/usr/bin/env python3
"""Ρ·render·plain — the `plain` target surfaces NO citation marker at all.

The projector renders a claim's citations for a chosen render TARGET.  `plain` is the clean
SUBMISSION view: the reader sees the prose with the machinery removed, while the claim-DAG stays
the author-side gate.  Contrast `pandoc`, which emits an inline [@key].  Both surface the SAME
prose — only the marker differs.  cwd = render/ ; .. = repo root.

⚑ Ζ·witness·component — the comparison ran at module level, so importing this file spawned two
projector subprocesses.  It is now a callable.  ⚑ AND THE `assert` INSIDE `_project` BECAME A
RETURNED COMPLAINT: an assert in a component is a crash where the framework wants a verdict, and
under `python -O` it is deleted entirely — the failure mode gcalculus measured across 2,839 of
them.  A witness that cannot fail is worse than one that fails loudly.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "paperkit"
PROJ = ENGINE / "project.py"
BIB = "@misc{a,\n  section = {s},\n  claim = {a projected claim},\n  check = {cmd:true}\n}\n"


def _project(target: str, d: str) -> tuple[str, str]:
    """Project a one-claim fixture for `target`; return (output, complaint)."""
    p = Path(d)
    (p / "paper.toml").write_text(
        '[paper]\ntitle = "t"\nwarrants = ["w.bib"]\nrubric = "r.tsv"\nout = "out.md"\n')
    (p / "r.tsv").write_text("s\tSec\n")
    (p / "w.bib").write_text(BIB)
    env = dict(os.environ, PAPERKIT_TARGET=target)   # Ω·config: env selects the render target
    r = subprocess.run([sys.executable, str(PROJ), "-o", "-", str(p)],
                       capture_output=True, text=True, env=env, check=False)
    if r.returncode != 0:
        return "", f"projector failed for target={target}: {r.stderr}"
    return r.stdout, ""


def _compare(pandoc: str, plain: str) -> str:
    """Return "" iff pandoc marks the citation and plain surfaces the prose without one."""
    if "[@a]" not in pandoc:
        return "the pandoc target did not surface an inline [@key] citation"
    if "[@" in plain or "[^" in plain:
        return f"the plain target LEAKED a citation marker (should surface none): {plain!r}"
    if "projected claim" not in plain:
        return ("the plain target dropped the claim prose — it must surface the SAME content, "
                "only without the marker")
    return ""


def check() -> int:
    """Return 0 iff `plain` surfaces the prose with no citation marker."""
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        pandoc, complaint = _project("pandoc", d1)
        if complaint:
            sys.stderr.write(complaint + "\n")
            return 1
        plain, complaint = _project("plain", d2)
        if complaint:
            sys.stderr.write(complaint + "\n")
            return 1
    complaint = _compare(pandoc, plain)
    if complaint:
        sys.stderr.write(complaint + "\n")
        return 1
    sys.stdout.write("plain ok: pandoc surfaces [@a]; plain surfaces the same prose with NO "
                     "citation marker (a clean submission view — the claim-DAG stays the "
                     "author-side gate)\n")
    return 0


if __name__ == "__main__":
    if __package__:
        raise SystemExit(check())
    import runpy

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    runpy.run_module("render.checks.plain", run_name="__main__", alter_sys=True)
