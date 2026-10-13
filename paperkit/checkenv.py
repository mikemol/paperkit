"""checkenv -- the sanitized environment a check runs in, factored out of resolver.py (W63).

resolver.py is currently pycheck-dirty (59 findings) and refuses any edit, so this module is a
transitional EXTRACTION: it carries clean_env/spawn_declared's logic forward under a name that
can be edited, while resolver.py's own copies stay in place until W64 cuts its ~7 internal call
sites over to this module and drops the duplicates. Two copies of one mechanism is a known,
tracked risk (not an accident) -- see paths-forward.json W60/W63/W64.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import paperkit.config

if TYPE_CHECKING:
    from collections.abc import Mapping

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
