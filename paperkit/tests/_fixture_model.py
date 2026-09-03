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


def entry(key, *, claim=None, emit=None, as_=None, frm=None, rests=None, glue=None,
          join=None, move=None, check="file:w.bib", section="s", mem=None):
    """A valid multi-line bibliography entry.  The parser requires the closing
    brace on its own line, so this never silently fails to parse.  section=None
    omits the field — a SECTIONLESS node (grounding-only, reachable via rests-on).
    """
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
    if as_:
        fs.append(f"  as = {{{as_}}}")
    fs.append(f"  check = {{{check}}}")
    if mem:
        fs.append(f"  mem = {{{mem}}}")
    return "@misc{%s,\n%s\n}\n" % (key, ",\n".join(fs))


#: The files `_write` AUTHORS.  An `assets` key equal to one of these REPLACES the fixture's
#: own declaration rather than extending it — the drift shape documented on `_write`.  Kept as
#: data so a caller (or a later refusal, once every call site can express `paper=`) can name it.
_AUTHORED = ("paper.toml", "r.tsv", "w.bib")


def _write(d, warrants, assets, rubric, title, numbered, references, paper=None):
    """Write the minimal project.  `paper` names EXTRA [paper] FIELDS (e.g. {"target": "plain"})
    — the additive channel for varying the config.

    ⚑ WHY A FIELD CHANNEL AND NOT AN ASSET.  `assets` is keyed by FILENAME and written after
    this function's own files, so a key of "paper.toml" silently overwrote the declaration
    below — the caller restating every field by hand, and thereby pinning the fixture's
    paper.toml to the shape it had ON THE DAY THE CALLER WAS WRITTEN.  That is exactly what
    happened: `root = "."` was added here, the copy in boundaries_grounding.PLAIN did not
    gain it, and six of seven arms stayed GREEN because only the one Δ arm sweeps.
    guard-must-not-copy, one level over.  Naming a FIELD cannot drift, because the fields the
    caller does NOT name are still authored here; an override written this way is impossible
    to write partially.

    ⚑ THE CHANNEL IS OPEN, THE OLD ONE IS NOT YET CLOSED.  The asset-key spelling still wins
    (assets are written last), so this only makes the correct form AVAILABLE.  Closing it —
    refusing a key in _AUTHORED — requires the three capability helpers (_fixture_gate,
    _fixture_project, _fixture_delta) to forward `paper=` and boundaries_grounding.PLAIN to
    move onto it; until then a refusal would red the tree with no path to green.
    """
    proj = Path(d) / "proj"
    proj.mkdir(parents=True, exist_ok=True)
    flags = f"numbered = {'true' if numbered else 'false'}\nreferences = {'true' if references else 'false'}\n"
    flags += "".join(f'{k} = "{v}"\n' for k, v in (paper or {}).items())
    # Ζ·declare·resources — the fixture DECLARES its Δ sandbox root, because it is the owner of
    # this project and the only party that can answer the ownership question.
    #
    # ⚑ IT USED TO BE INFERRED, AND THE INFERENCE WAS UNSOUND.  layout._sandbox_root returned
    # `project_dir.parent` whenever the engine was a SIBLING rather than inside the project, which
    # is exactly this fixture's shape: the project is a fresh tempfile.mkdtemp() and the engine
    # lives in the checkout.  The inferred root was therefore $TMPDIR — every other temporary
    # directory on the machine, including the OTHER fixtures a parallel suite is building — and
    # the Δ sweep is entitled to MUTATE its root, so the measured surface silently included
    # unrelated tests' fixtures.  layout.py now REFUSES to guess (Λ·registry: the owner declares,
    # the engine reads), and this line is that declaration.
    #
    # `root = "."` is the honest answer and not merely the one that makes the refusal go away: the
    # fixture project IS the bounded tree.  Everything Δ may legitimately corrupt for these
    # suites — w.bib, r.tsv, paper.toml, the assets — is written below, inside `proj`; nothing
    # above it belongs to the fixture, and a sweep reaching above it would be measuring the
    # machine rather than the project.
    (proj / "paper.toml").write_text(
        f'[paper]\ntitle = "{title}"\nwarrants = ["w.bib"]\nrubric = "r.tsv"\nout = "out.md"\n'
        'root = "."\n' + flags)
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
    returns None or raises SystemExit yields its exit code.
    """
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
