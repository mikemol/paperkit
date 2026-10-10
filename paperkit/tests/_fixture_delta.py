"""Fixture DELTA capability (Μ·kernel·fixture·split) — the Δ-facing helpers:

  discriminate()         PROJECTS out.md, then runs Δ; (returncode, stdout)
  discriminate_stderr()  the grade run's STDERR (the Δ·pulse heartbeat lives here)

The `import discriminate` is MODULE-TOP and honest: tools/imports.py derives the dag
edge (dag cone: _fixture_model + _fixture_project + discriminate → the Δ subsystem),
so a witness importing this module stages the wide cone it genuinely exercises.
"""
from __future__ import annotations

import tempfile

import paperkit.tests._fixture_model  # the capability-free kernel (bootstraps sys.path)
import paperkit.tests._fixture_project
import paperkit.discriminate


def discriminate(warrants, *flags, assets=None, out=None, rubric=(("s", "Sec"),),
                 title="t", numbered=False, references=False, env=None):
    """(returncode, stdout).  Projects out.md before grading (or writes `out`).
    `env` overrides the child environment for the grade run."""
    with tempfile.TemporaryDirectory() as d:
        proj = paperkit.tests._fixture_model._write(d, warrants, assets, rubric, title, numbered, references)
        paperkit.tests._fixture_project._projected(proj, out)
        rc, o, _e = paperkit.tests._fixture_model._call(paperkit.discriminate.main, [*flags, str(proj)], env=env)
        return rc, o


def discriminate_stderr(warrants, *flags, assets=None, rubric=(("s", "Sec"),), env=None):
    """The grade run's STDERR (the Δ·pulse heartbeat lives here)."""
    with tempfile.TemporaryDirectory() as d:
        proj = paperkit.tests._fixture_model._write(d, warrants, assets, rubric, "t", False, False)
        paperkit.tests._fixture_project._projected(proj, None)
        return paperkit.tests._fixture_model._call(paperkit.discriminate.main, [*flags, str(proj)], env=env)[2]
