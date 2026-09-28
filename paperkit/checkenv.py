"""checkenv -- the sanitized environment a check runs in, factored out of resolver.py (W63).

resolver.py is currently pycheck-dirty (59 findings) and refuses any edit, so this module is a
transitional EXTRACTION: it carries clean_env/spawn_declared's logic forward under a name that
can be edited, while resolver.py's own copies stay in place until W64 cuts its ~7 internal call
sites over to this module and drops the duplicates. Two copies of one mechanism is a known,
tracked risk (not an accident) -- see paths-forward.json W60/W63/W64.
"""
from __future__ import annotations

import contextlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import config

_ENV_KEEP = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "TERM", "TZ", "TMPDIR",
             "LANG", "LANGUAGE", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"}
_ENV_KEEP_PREFIX = ("LC_", "PAPERKIT_")
_ENV_DROP = {"PAPERKIT_ROOT"}

PATH = config.Param("path", "PAPERKIT_PATH",
                    help="pin tool resolution to these absolute dirs (colon-separated) instead "
                         "of the host PATH -- reproducibility, and dropping user-writable "
                         "shadow dirs")

ENGINE_PATH = config.Param(
    "engine-path", "PAPERKIT_PYTHONPATH",
    help="the directory `paperkit` is importable from, exported to every check as "
         "PAPERKIT_PYTHONPATH -- a DECLARED passthrough across clean_env's default-deny")


def clean_env(env: dict | None = None) -> dict:
    """Build a sanitized environment for running a check: the controlled allow-list only."""
    src = os.environ if env is None else env
    out = {k: v for k, v in src.items()
           if (k in _ENV_KEEP or k.startswith(_ENV_KEEP_PREFIX)) and k not in _ENV_DROP}
    out["PYTHONOPTIMIZE"] = "0"
    engine_path = config.resolve(ENGINE_PATH) or str(Path(__file__).resolve().parent)
    out["PAPERKIT_PYTHONPATH"] = str(engine_path)
    pinned = config.resolve(PATH)
    if pinned is not None:
        raw = [p for p in pinned.split(os.pathsep) if Path(p).is_dir()]
    elif "PATH" in out:
        raw = out["PATH"].split(os.pathsep)
    else:
        return out
    root = Path(__file__).resolve().parent
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


def spawn_declared(cmd: str, cwd: Path, payload: str,
                   records: list[dict] | None = None) -> subprocess.CompletedProcess[str]:
    """Run a project-declared command as a gated check."""
    env = clean_env()
    fd, name = tempfile.mkstemp(suffix=".jsonl", prefix="pk-genre-records-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out_fh:
            for rec in (records or ()):
                out_fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        env["PAPERKIT_GENRE_RECORDS"] = name
        return subprocess.run(cmd, shell=True, cwd=cwd, input=payload,   # noqa: S602
                              capture_output=True, text=True, env=env, check=False)
    finally:
        with contextlib.suppress(OSError):
            Path(name).unlink()
