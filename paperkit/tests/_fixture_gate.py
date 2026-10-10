"""Fixture GATE capability (Μ·kernel·fixture·split) — the gate-facing helpers:

  gate()       PROJECTS out.md, then gates (out=… overrides the projection,
               for tests that need to control citations directly)
  gate_json()  the same, parsing gate --json's machine verdict

The `import gate` is MODULE-TOP and honest: tools/imports.py derives the dag edge
(dag cone: _fixture_model + _fixture_project + gate → bib, config, project,
resolver, rhetoric, grade), so a witness importing this module stages exactly the
gate's subsystem cone.
"""
from __future__ import annotations

import json
import tempfile

import paperkit.tests._fixture_model  # the capability-free kernel (bootstraps sys.path)
import paperkit.tests._fixture_project
import paperkit.gate


def gate(warrants, *flags, assets=None, out=None, rubric=(("s", "Sec"),),
         title="t", numbered=False, references=False):
    """(returncode, stderr).  Projects out.md before gating (or writes `out`)."""
    with tempfile.TemporaryDirectory() as d:
        proj = paperkit.tests._fixture_model._write(d, warrants, assets, rubric, title, numbered, references)
        paperkit.tests._fixture_project._projected(proj, out)
        rc, _o, e = paperkit.tests._fixture_model._call(paperkit.gate.main, [*flags, str(proj)])
        return rc, e


def gate_json(warrants, *flags, assets=None, out=None, rubric=(("s", "Sec"),),
              title="t", numbered=False, references=False):
    """(returncode, parsed gate --json dict).  Projects out.md first (or writes `out`)."""
    with tempfile.TemporaryDirectory() as d:
        proj = paperkit.tests._fixture_model._write(d, warrants, assets, rubric, title, numbered, references)
        paperkit.tests._fixture_project._projected(proj, out)
        rc, o, _e = paperkit.tests._fixture_model._call(paperkit.gate.main, ["--json", *flags, str(proj)])
        return rc, json.loads(o or "{}")
