"""checkenv -- the sanitized environment a check runs in, and the ONE place a check is spawned.

Factored out of resolver.py (W63/W64).  clean_env is the default-deny environment; the spawn
functions below are the only callers of subprocess in the resolver's path, each running under
clean_env, so "what environment did that check see" has one answer and "who may start a process"
has one place to read.  paperkit runs PATH programs and shell-string `cmd:` values BY DESIGN (the
execution surface is declared, not hidden), which is why the spawn rules (S602 shell=True, S603
untrusted argv, PLW1509 preexec_fn) are scoped to this file in pyproject.toml and nowhere else.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import resource
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import paperkit.config

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

_ENV_KEEP = {
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "SHELL",
    "TERM",
    "TZ",
    "TMPDIR",
    "LANG",
    "LANGUAGE",
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
}
_ENV_KEEP_PREFIX = ("LC_", "PAPERKIT_")
_ENV_DROP = {"PAPERKIT_ROOT"}

PATH = paperkit.config.Param(
    "path",
    "PAPERKIT_PATH",
    help="pin tool resolution to these absolute dirs (colon-separated) instead "
    "of the host PATH -- reproducibility, and dropping user-writable "
    "shadow dirs",
)

ENGINE_PATH = paperkit.config.Param(
    "engine-path",
    "PAPERKIT_PYTHONPATH",
    help="the directory `paperkit` is importable from, exported to every check as "
    "PAPERKIT_PYTHONPATH -- a DECLARED passthrough across clean_env's default-deny",
)


def _dist_roots() -> list[str]:
    """Return every directory the `mikemol` namespace is importable from, first-found first.

    ⚑ AND THE DISTS THE ENGINE IMPORTS (W317).  `mikemol.atomicwrite` is a third-party dist, so
    a check's bare python3 cannot find it from the checkout alone; the directory it is importable
    from is DERIVED from where this process found it, never copied, and appended after the
    engine.  EVERY location of the namespace: an installed venv has one, but wheels delivered as
    zips on PYTHONPATH (a Bazel cell, tools/cell.bzl cell_dists) contribute one each.
    """
    spec = importlib.util.find_spec("mikemol")
    if spec is None or not spec.submodule_search_locations:
        return []
    roots: list[str] = []
    for loc in spec.submodule_search_locations:
        parent = str(Path(loc).parent)
        if parent not in roots:
            roots.append(parent)
    return roots


def clean_env(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build a sanitized environment for running a check: the controlled allow-list only."""
    src = os.environ if env is None else env
    out = {
        k: v
        for k, v in src.items()
        if (k in _ENV_KEEP or k.startswith(_ENV_KEEP_PREFIX)) and k not in _ENV_DROP
    }
    out["PYTHONOPTIMIZE"] = "0"
    # BUGFIX (found by W64's boundary test): checkenv.py sits at paperkit/checkenv.py, the SAME
    # depth resolver.py did -- one .parent reaches the paperkit/ package dir, not the repo root
    # a caller needs on sys.path to `import paperkit`. Two .parent, matching resolver.py's
    # original `Path(__file__).resolve().parent.parent`.
    declared = paperkit.config.resolve(ENGINE_PATH)
    engine_path = (
        declared
        if isinstance(declared, str) and declared
        else str(Path(__file__).resolve().parent.parent)
    )
    out["PAPERKIT_PYTHONPATH"] = engine_path
    # ⚑ AND THE SAME DIRECTORY AS PYTHONPATH, SET BY THE ENGINE AND NEVER INHERITED (paperkit:W297).
    # Consumers import the engine as the package it is (`import paperkit.bib`), which needs it
    # importable the way an install would make it; the PAPERKIT_PYTHONPATH hint alone asked every
    # check to put it on sys.path itself, which is the bootstrap being retired. The checkout,
    # never `paperkit/paperkit`: that directory's `config`, `layout` and `bib` would shadow
    # whatever a check imports under those names.
    out["PYTHONPATH"] = os.pathsep.join([engine_path, *_dist_roots()])
    pinned = paperkit.config.resolve(PATH)
    if isinstance(pinned, str):
        raw = [p for p in pinned.split(os.pathsep) if Path(p).is_dir()]
    elif "PATH" in out:
        raw = out["PATH"].split(os.pathsep)
    else:
        return out
    root = Path(__file__).resolve().parent.parent  # the repo root -- see the engine_path note above
    seen: set[str] = set()
    dirs: list[str] = []
    for p in raw:
        if not (p and Path(p).is_absolute() and p not in seen):
            continue
        rp = Path(p).resolve()
        if rp == root or root in rp.parents:
            continue
        seen.add(p)
        dirs.append(p)
    out["PATH"] = os.pathsep.join(dirs)
    return out


def spawn_declared(
    cmd: str, cwd: Path, payload: str, records: list[dict[str, object]] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a project-declared command as a gated check."""
    env = clean_env()
    fd, name = tempfile.mkstemp(suffix=".jsonl", prefix="pk-genre-records-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out_fh:
            for rec in records or ():
                out_fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        env["PAPERKIT_GENRE_RECORDS"] = name
        return subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            input=payload,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
    finally:
        with contextlib.suppress(OSError):
            Path(name).unlink()


def run_argv_text(argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run `argv` (no shell) in `cwd`, sanitized environment, streams captured as text."""
    return subprocess.run(
        list(argv), cwd=cwd, env=clean_env(), capture_output=True, text=True, check=False
    )


def run_argv_bytes(argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[bytes]:
    """Run `argv` (no shell) in `cwd`, sanitized environment, streams captured as bytes."""
    return subprocess.run(list(argv), cwd=cwd, env=clean_env(), capture_output=True, check=False)


def run_shell_text(cmd: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the shell string `cmd` in `cwd`, sanitized environment, streams captured as text."""
    return subprocess.run(
        cmd, shell=True, cwd=cwd, env=clean_env(), capture_output=True, text=True, check=False
    )


class Capped(NamedTuple):
    """The outcome of a CPU-capped run: the exit code (None when the wall backstop killed it)."""

    rc: int | None
    out: bytes
    err: bytes


def _cpu_rlimit(seconds: int) -> Callable[[], None]:
    """Return a preexec_fn that caps the child's (and its tree's) CPU time.

    SIGKILL at `seconds` (soft == hard since W42, so no SIGXCPU and no coredump record for an
    expected cap kill).  Runs in the forked child before exec, so the whole check subprocess is
    bounded by WORK DONE, not wall time.
    """

    def _set() -> None:
        # W78/W127 — setrlimit can LOWER but never RAISE a hard limit, so a NESTED invocation
        # (already running under a tighter parent-imposed hard limit, e.g. inside a mutant sweep
        # executor) must clamp to the inherited hard limit rather than assume `seconds` is
        # reachable.
        _, inherited_hard = resource.getrlimit(resource.RLIMIT_CPU)
        cap = seconds if inherited_hard == resource.RLIM_INFINITY else min(seconds, inherited_hard)
        # W42 — soft == hard: the first action is SIGKILL, so an expected CPU-cap kill leaves no
        # coredump record (soft < hard sent SIGXCPU first, which systemd-coredump logs as a crash).
        resource.setrlimit(resource.RLIMIT_CPU, (cap, cap))
        # Ζ·core·off — SIGXCPU's default action dumps core; the verdict reads the exit, never a
        # core.
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    return _set


def run_capped(cmd: str, cwd: Path, cpu: int, wall: int) -> Capped:
    """Run the shell string `cmd`, bounded by `cpu` seconds of CPU time and `wall` seconds of wall.

    A check must TERMINATE to pass.  start_new_session so a hang kills the WHOLE process group —
    a `shell=True` timeout otherwise reaps only the shell and orphans the real child (the hanging
    witness), which then spins on.  Both streams are PIPEs on their OWN handles, never merged
    ([[separate-filehandles]]).

    ⚑ communicate(), NEVER wait() — a PIPE that nothing drains DEADLOCKS the child the moment it
    writes past the 64KB pipe buffer: the check blocks in anon_pipe_write, this process blocks in
    do_wait, and neither ever moves.  Measured 2026-08-26: a def-sweep cell for edge-formulas sat
    at 0.0% CPU for 11+ minutes.  communicate() drains and waits in one call, so the timeout still
    bounds the run.

    Returns Capped(rc=None, ...) when the wall backstop fired and the tree was killed.
    """
    p = subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        env=clean_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        preexec_fn=_cpu_rlimit(cpu),
    )
    try:
        out, err = p.communicate(timeout=wall)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)  # kill the whole tree, no orphans
        p.wait()
        return Capped(None, b"", b"")
    return Capped(p.returncode, out, err)
