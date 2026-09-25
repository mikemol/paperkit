"""Ζ·calc·venv — the ONE definition of how a cell reaches the engine.

⚑ THIS EXISTS BECAUSE THE SAME ANSWER WAS WRITTEN IN FOUR PLACES AND THEN FIXED IN ONE.
`_pypath` is defined separately in calc.bzl, verb.bzl, grade.bzl and witness.bzl — byte-identical,
loaded by nothing.  When Ζ·venv·install taught a cell to INSTALL the engine rather than point at
it, the change landed in verb.bzl's pk_cmd and the eight sweep sites in calc.bzl kept the old
prefix.  Measured: a check cell could `from paperkit import x`, a SWEEP cell could not, so the
witness failed to reach its engine and the sweep reported `sens: []` — a measurement of zero
rather than an unreachable baseline, which then graded a healthy claim `fail` and reddened six
of a downstream view's imports.  A duplicated definition does not drift by being edited; it
drifts by being IMPROVED in one copy.

So both spellings live here, together, and every rule loads them:

  cell_pypath(py)              — the hermetic interpreter on PATH, nothing more
  cell_venv(py, tool, whl)     — the interpreter PLUS the engine installed into a cell-local venv
"""

def cell_pypath(py):
    """The staged interpreter's directory on PATH, so a check's own `python3` resolves to it.

    NOT `python3` itself: a check's cmd is the PROJECT's string and spells `python3`, and a build
    action that re-spawns python needs sys.executable populated (see tools/eval.py).
    """
    return 'export PATH="$(cd "$(dirname ' + py.interpreter.path + ')" && pwd):$PATH"; '

def cell_builds_env(builds):
    """⚑ Ζ·builds·path — THE ARTIFACTS A WARRANT DECLARED, AS ABSOLUTE PATHS, FOR ANY CELL.

    A declared `builds` artifact is staged at its EXECROOT-relative path
    (`bazel-out/<cfg>/bin/...`) and a cell runs with cwd=<project>, so the check cannot find it by
    guessing a layout — `bazel-bin/` is a workspace convenience symlink that does not exist inside
    a sandbox.  This exports `basename=$PWD/<path>` pairs BEFORE the cd, the same idiom
    PAPERKIT_CONSUMED_RECORDS uses for records ("so the check finds each record regardless of
    cwd").  Empty string when the warrant declares no `builds`.

    ⚑⚑ IT LIVES HERE BECAUSE IT HAD TWO CALLERS AND SERVED ONE.  Ζ·builds·path landed in
    verb.bzl's `_cmd_impl` only; `calc.bzl` never mentioned the variable.  A claim renders BOTH —
    pk_cmd for the verdict, pk_calc for the grade — so `bnd-wheel` declared
    `builds = {@@//paperkit:wheel}`, the generator put it in the cell's `data` correctly, and the
    SWEEP cell still reported `CANNOT RUN — //paperkit:wheel is not staged` with the artifact
    present in its own cell.  Exactly the drift this module's own docstring describes one screen
    up: "the change landed in verb.bzl's pk_cmd and the eight sweep sites in calc.bzl kept the old
    prefix ... a duplicated definition drifts by being IMPROVED in one copy."
    """
    if not builds:
        return ""
    pairs = " ".join([f.basename + "=$PWD/" + f.path for f in builds])
    return 'export PAPERKIT_BUILT_ARTIFACTS="' + pairs + '"; '


def cell_venv(py, tool, whl, deps = []):
    """Install the engine WHEEL into a cell-local venv and put its bin/ first on PATH.

    The engine arrives as COPIED FILES in site-packages — not a path entry, not a .pth naming a
    root that resolves through a symlink back to the live tree (which is how an earlier form let a
    check read UNSTAGED sources and pass).  `whl` is a declared, content-addressed input, so the
    venv is a pure function of the action's inputs; the install is stdlib zipfile alone, ~0.077s.
    """
    extra = "".join([" " + f.path for f in deps])
    return ('"' + py.interpreter.path + '" ' + tool.path + ' install "$PWD/.cellvenv" ' +
            whl.path + extra + ' >/dev/null; export PATH="$PWD/.cellvenv/bin:$PATH"; ')
