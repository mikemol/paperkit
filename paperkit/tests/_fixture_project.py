"""Fixture PROJECT capability (Μ·kernel·fixture·split) — the projector-facing helpers:

  project_text()  the projection, as text (project -o -)
  _projected()    write out.md as the faithful projection (or the caller's override)

The `import project` is MODULE-TOP and honest: tools/imports.py derives the dag edge
(dag cone: _fixture_model + project → bib, config, rhetoric, grade), so a witness
importing this module stages exactly the projector's subsystem cone.
"""

from __future__ import annotations

import tempfile

import paperkit.tests._fixture_model  # the capability-free kernel (bootstraps sys.path)
import paperkit.project


def project_text(
    warrants, *, assets=None, rubric=(("s", "Sec"),), title="t", numbered=False, references=False
) -> str:
    with tempfile.TemporaryDirectory() as d:
        proj = paperkit.tests._fixture_model._write(
            d, warrants, assets, rubric, title, numbered, references
        )
        return paperkit.tests._fixture_model._call(paperkit.project.main, ["-o", "-", str(proj)])[1]


def _projected(proj, out):
    if out is None:  # faithful: out.md IS the projection
        paperkit.tests._fixture_model._call(paperkit.project.main, [str(proj)])
    else:  # caller controls out.md (e.g. citations)
        (proj / "out.md").write_text(out)
