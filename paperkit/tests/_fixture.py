"""Validated fixture builder for paperkit tests — the one place that knows how to
construct a minimal paperkit project correctly.

Every boundary suite used to build a project inline, and each slipped a different
detail (a single-line .bib entry that the parser won't match; gating without
projecting out.md first; no citation so nothing is gated).  This module encodes
those invariants once:

  entry()         a VALID multi-line .bib entry (closing brace on its own line)
  project_text()  the projection, as text (project -o -)
  gate()          PROJECTS out.md, then gates  (out=… overrides the projection,
                  for tests that need to control citations directly)
  discriminate()  PROJECTS out.md, then runs Δ

All three manage their own tempdir and return plain values.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
PROJECT, GATE, DISCRIMINATE = ENGINE / "project.py", ENGINE / "gate.py", ENGINE / "discriminate.py"


def entry(key, *, claim=None, emit=None, frm=None, rests=None, glue=None, check="file:w.bib", section="s", mem=None):
    """A valid multi-line bibliography entry.  The parser requires the closing
    brace on its own line, so this never silently fails to parse."""
    fs = [f"  section = {{{section}}}"]
    if frm:
        fs.append(f"  from = {{{frm}}}")
    if rests:
        fs.append(f"  rests-on = {{{rests}}}")
    if glue:
        fs.append(f"  glue = {{{glue}}}")
    if claim:
        fs.append(f"  claim = {{{claim}}}")
    if emit:
        fs.append(f"  emit = {{{emit}}}")
    fs.append(f"  check = {{{check}}}")
    if mem:
        fs.append(f"  mem = {{{mem}}}")
    return "@misc{%s,\n%s\n}\n" % (key, ",\n".join(fs))


def _write(d, warrants, assets, rubric, title, numbered, references):
    proj = Path(d) / "proj"
    proj.mkdir(parents=True, exist_ok=True)
    flags = f"numbered = {'true' if numbered else 'false'}\nreferences = {'true' if references else 'false'}\n"
    (proj / "paper.toml").write_text(
        f'[paper]\ntitle = "{title}"\nwarrants = ["w.bib"]\nrubric = "r.tsv"\nout = "out.md"\n' + flags)
    (proj / "r.tsv").write_text("".join(f"{k}\t{t}\n" for k, t in rubric))
    (proj / "w.bib").write_text("".join(warrants))
    for name, content in (assets or {}).items():
        (proj / name).write_text(content)
    return proj


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def project_text(warrants, *, assets=None, rubric=(("s", "Sec"),),
                 title="t", numbered=False, references=False) -> str:
    with tempfile.TemporaryDirectory() as d:
        proj = _write(d, warrants, assets, rubric, title, numbered, references)
        return _run([sys.executable, str(PROJECT), "-o", "-", str(proj)]).stdout


def _projected(proj, out):
    if out is None:                       # faithful: out.md IS the projection
        _run([sys.executable, str(PROJECT), str(proj)])
    else:                                 # caller controls out.md (e.g. citations)
        (proj / "out.md").write_text(out)


def gate(warrants, *flags, assets=None, out=None, rubric=(("s", "Sec"),),
         title="t", numbered=False, references=False):
    """(returncode, stderr).  Projects out.md before gating (or writes `out`)."""
    with tempfile.TemporaryDirectory() as d:
        proj = _write(d, warrants, assets, rubric, title, numbered, references)
        _projected(proj, out)
        r = _run([sys.executable, str(GATE), *flags, str(proj)])
        return r.returncode, r.stderr


def discriminate(warrants, *flags, assets=None, out=None, rubric=(("s", "Sec"),),
                 title="t", numbered=False, references=False):
    """(returncode, stdout).  Projects out.md before grading (or writes `out`)."""
    with tempfile.TemporaryDirectory() as d:
        proj = _write(d, warrants, assets, rubric, title, numbered, references)
        _projected(proj, out)
        r = _run([sys.executable, str(DISCRIMINATE), *flags, str(proj)])
        return r.returncode, r.stdout


def gate_json(warrants, *flags, assets=None, out=None, rubric=(("s", "Sec"),),
              title="t", numbered=False, references=False):
    """(returncode, parsed gate --json dict).  Projects out.md first (or writes `out`)."""
    with tempfile.TemporaryDirectory() as d:
        proj = _write(d, warrants, assets, rubric, title, numbered, references)
        _projected(proj, out)
        r = _run([sys.executable, str(GATE), "--json", *flags, str(proj)])
        return r.returncode, json.loads(r.stdout or "{}")
