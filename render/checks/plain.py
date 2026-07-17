#!/usr/bin/env python3
# Ρ·render·plain — the projector renders a claim's citations for a chosen render TARGET, and the
# `plain` target surfaces NO citation marker at all: a clean SUBMISSION view where the reader sees
# the prose with the machinery removed, while the claim-DAG stays the author-side gate.  Contrast
# `pandoc`, which emits an inline [@key].  Both surface the SAME prose — only the marker differs.
# cwd = render/ ; .. = repo root.
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "paperkit"
PROJ = ENGINE / "project.py"
BIB = "@misc{a,\n  section = {s},\n  claim = {a projected claim},\n  check = {cmd:true}\n}\n"


def _project(target: str, d: str) -> str:
    p = Path(d)
    (p / "paper.toml").write_text(
        '[paper]\ntitle = "t"\nwarrants = ["w.bib"]\nrubric = "r.tsv"\nout = "out.md"\n')
    (p / "r.tsv").write_text("s\tSec\n")
    (p / "w.bib").write_text(BIB)
    env = dict(os.environ, PAPERKIT_TARGET=target)   # Ω·config: env selects the render target
    r = subprocess.run([sys.executable, str(PROJ), "-o", "-", str(p)],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, f"projector failed for target={target}: {r.stderr}"
    return r.stdout


with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
    pandoc = _project("pandoc", d1)
    plain = _project("plain", d2)

assert "[@a]" in pandoc, "the pandoc target did not surface an inline [@key] citation"
assert "[@" not in plain and "[^" not in plain, \
    f"the plain target LEAKED a citation marker (should surface none): {plain!r}"
assert "projected claim" in plain, \
    "the plain target dropped the claim prose — it must surface the SAME content, only without the marker"
print("plain ok: pandoc surfaces [@a]; plain surfaces the same prose with NO citation marker "
      "(a clean submission view — the claim-DAG stays the author-side gate)")
