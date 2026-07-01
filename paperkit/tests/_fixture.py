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

import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
if str(ENGINE) not in sys.path:                  # Φ·spawn: the helpers import the engine IN-PROCESS
    sys.path.insert(0, str(ENGINE))              # (was: spawn by absolute path), so ENGINE is on path
                                                 # here — self-contained, not reliant on the caller's setup
# The engine CLI paths — for the few boundary suites that genuinely test CROSS-PROCESS behaviour
# (memoize: a Δ grade cached across processes) and so spawn a real process (under the standard
# boundaries gate, not the hermetic grid).  The fx helpers below run IN-PROCESS, not via these.
PROJECT, GATE, DISCRIMINATE = ENGINE / "project.py", ENGINE / "gate.py", ENGINE / "discriminate.py"


def entry(key, *, claim=None, emit=None, frm=None, rests=None, glue=None, join=None,
          move=None, check="file:w.bib", section="s", mem=None):
    """A valid multi-line bibliography entry.  The parser requires the closing
    brace on its own line, so this never silently fails to parse."""
    fs = [f"  section = {{{section}}}"]
    if frm:
        fs.append(f"  from = {{{frm}}}")
    if rests:
        fs.append(f"  rests-on = {{{rests}}}")
    if glue:
        fs.append(f"  glue = {{{glue}}}")
    if join is not None:
        fs.append(f"  join = {{{join}}}")
    if move:
        fs.append(f"  move = {{{move}}}")
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
        (proj / name).parent.mkdir(parents=True, exist_ok=True)   # subdir keys → e.g. a nested subproject
        (proj / name).write_text(content)
    return proj


def _call(main, argv, env=None):
    """Run an engine main(argv) IN-PROCESS (Φ·spawn — process spawning is Bazel's job, and a hermetic
    mutation cell can't spawn/ptrace faithfully), capturing (returncode, stdout, stderr).  os.environ
    is SAVED and RESTORED around every call: discriminate.main folds args into PAPERKIT_* env
    (config.apply_args, Ω·config) — process-isolated when spawned, but in-process it would LEAK into
    the witness and later calls (the recursive-check leak).  env=None inherits the current environment
    (saved/restored); env=<dict> replaces it for the call, as a subprocess env= would.  A main() that
    returns None or raises SystemExit yields its exit code.  The engine is imported LAZILY by each
    helper (not at module level) so a witness's def-closure isn't widened to discriminate's whole cone
    (Ξ·dag·eval incrementality) — closure.py maps fx.<helper> → its module from these imports."""
    o, e = io.StringIO(), io.StringIO()
    saved = os.environ.copy()
    if env is not None:
        os.environ.clear()
        os.environ.update(env)
    try:
        with contextlib.redirect_stdout(o), contextlib.redirect_stderr(e):
            rc = main(list(argv))
    except SystemExit as se:
        rc = se.code if isinstance(se.code, int) else (0 if se.code is None else 1)
    except Exception as ex:
        # A subprocess exits NONZERO on an engine crash; match that in-process.  The Ν·loud guards
        # RAISE (e.g. a def-resolution sweep with no engine in the sandbox — the def-engine-guard),
        # and witnesses assert that nonzero.  Record the crash on the captured stderr.
        e.write("%s: %s\n" % (type(ex).__name__, ex))
        rc = 1
    finally:
        os.environ.clear()
        os.environ.update(saved)
    return (rc or 0), o.getvalue(), e.getvalue()


def project_text(warrants, *, assets=None, rubric=(("s", "Sec"),),
                 title="t", numbered=False, references=False) -> str:
    import project
    with tempfile.TemporaryDirectory() as d:
        proj = _write(d, warrants, assets, rubric, title, numbered, references)
        return _call(project.main, ["-o", "-", str(proj)])[1]


def _projected(proj, out):
    if out is None:                       # faithful: out.md IS the projection
        import project
        _call(project.main, [str(proj)])
    else:                                 # caller controls out.md (e.g. citations)
        (proj / "out.md").write_text(out)


def gate(warrants, *flags, assets=None, out=None, rubric=(("s", "Sec"),),
         title="t", numbered=False, references=False):
    """(returncode, stderr).  Projects out.md before gating (or writes `out`)."""
    import gate as _gate
    with tempfile.TemporaryDirectory() as d:
        proj = _write(d, warrants, assets, rubric, title, numbered, references)
        _projected(proj, out)
        rc, _o, e = _call(_gate.main, [*flags, str(proj)])
        return rc, e


def discriminate(warrants, *flags, assets=None, out=None, rubric=(("s", "Sec"),),
                 title="t", numbered=False, references=False, env=None):
    """(returncode, stdout).  Projects out.md before grading (or writes `out`).
    `env` overrides the child environment for the grade run."""
    import discriminate as _disc
    with tempfile.TemporaryDirectory() as d:
        proj = _write(d, warrants, assets, rubric, title, numbered, references)
        _projected(proj, out)
        rc, o, _e = _call(_disc.main, [*flags, str(proj)], env=env)
        return rc, o


def discriminate_stderr(warrants, *flags, assets=None, rubric=(("s", "Sec"),), env=None):
    """The grade run's STDERR (the Δ·pulse heartbeat lives here)."""
    import discriminate as _disc
    with tempfile.TemporaryDirectory() as d:
        proj = _write(d, warrants, assets, rubric, "t", False, False)
        _projected(proj, None)
        return _call(_disc.main, [*flags, str(proj)], env=env)[2]


def gate_json(warrants, *flags, assets=None, out=None, rubric=(("s", "Sec"),),
              title="t", numbered=False, references=False):
    """(returncode, parsed gate --json dict).  Projects out.md first (or writes `out`)."""
    import gate as _gate
    with tempfile.TemporaryDirectory() as d:
        proj = _write(d, warrants, assets, rubric, title, numbered, references)
        _projected(proj, out)
        rc, o, _e = _call(_gate.main, ["--json", *flags, str(proj)])
        return rc, json.loads(o or "{}")
