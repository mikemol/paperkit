"""The fixture MODEL — the capability-free kernel of the validated fixture builder
(Μ·kernel·fixture·split): build a minimal paperkit project and run an engine main()
in-process, with NO engine import (dag cone: ∅).

Every boundary suite used to build a project inline, and each slipped a different
detail (a single-line .bib entry that the parser won't match; gating without
projecting out.md first; no citation so nothing is gated).  This module encodes
those invariants once:

  entry()   a VALID multi-line .bib entry (closing brace on its own line)
  _write()  the minimal project directory (paper.toml / rubric / warrants / assets)
  _call()   run an engine main(argv) IN-PROCESS, os.environ saved/restored

The capability modules layer the engine-facing helpers on top — _fixture_project
(project_text/_projected), _fixture_gate (gate/gate_json), _fixture_delta
(discriminate/discriminate_stderr) — each importing its OWN engine module at module
top, so the import DAG (tools/imports.py → paperkit/dag.bzl) carries the honest
per-capability cone instead of one wide hub, and a witness stages exactly the
subsystem it exercises.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
if str(ENGINE) not in sys.path:                  # Φ·spawn: the helpers import the engine IN-PROCESS
    sys.path.insert(0, str(ENGINE))              # (was: spawn by absolute path), so ENGINE is on path
                                                 # here — self-contained, not reliant on the caller's setup
# The engine CLI paths — for the few boundary suites that genuinely test CROSS-PROCESS behaviour
# (memoize: a Δ grade cached across processes) and so spawn a real process (under the standard
# boundaries gate, not the hermetic grid).  The capability helpers run IN-PROCESS, not via these.
PROJECT, GATE, DISCRIMINATE = ENGINE / "project.py", ENGINE / "gate.py", ENGINE / "discriminate.py"


def entry(key, *, claim=None, emit=None, frm=None, rests=None, glue=None, join=None,
          move=None, check="file:w.bib", section="s", mem=None):
    """A valid multi-line bibliography entry.  The parser requires the closing
    brace on its own line, so this never silently fails to parse.  section=None
    omits the field — a SECTIONLESS node (grounding-only, reachable via rests-on)."""
    fs = [f"  section = {{{section}}}"] if section else []
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
    returns None or raises SystemExit yields its exit code."""
    o, e = io.StringIO(), io.StringIO()
    saved = os.environ.copy()
    if env is not None:
        os.environ.clear()
        os.environ.update(env)
    try:
        with contextlib.redirect_stdout(o), contextlib.redirect_stderr(e):
            rc = main(list(argv))
    except SystemExit as se:
        # CPython parity: sys.exit(None) → 0; sys.exit(int) → that code; sys.exit("msg") →
        # the message on stderr and exit 1 (so a refusal's CONTRACT message stays observable
        # in-process, e.g. the Ζ·ladder floor refusal).
        if se.code is not None and not isinstance(se.code, int):
            e.write(f"{se.code}\n")
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
