#!/usr/bin/env python3
"""Project file TOPOLOGY — the small shared foundation under both the cache and the grader:
which files Δ may read/corrupt, where the mutation sandbox is rooted, and which directories
are OTHER projects.  Factored out so neither the cache nor the grader has to own it (and so
each can be imported and tested without the other)."""
from __future__ import annotations

import os
import shutil
import tomllib
from pathlib import Path

MUTABLE_SUFFIXES = {".bib", ".tsv", ".toml", ".md", ".sh", ".py", ".txt"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "out"}
_ENGINE = Path(__file__).resolve().parent


def _root_override(project_dir: Path) -> Path | None:
    """An EXPLICIT sandbox root — for container pipelines and downstream projects whose parent
    is not a tidy repo.  Precedence: the PAPERKIT_ROOT environment variable (the --root CLI arg
    overrides it by SETTING it, so explicit-arg beats env), then the project's paper.toml
    ([paper] root, relative to the project dir).  Whichever is set must CONTAIN the project."""
    decl = os.environ.get("PAPERKIT_ROOT")
    if not decl:
        cfg = project_dir / "paper.toml"
        if cfg.is_file():
            try:
                decl = tomllib.loads(cfg.read_text()).get("paper", {}).get("root")
            except Exception:
                decl = None
    if not decl:
        return None
    root = Path(decl)
    root = (root if root.is_absolute() else project_dir / root).resolve()
    if not project_dir.resolve().is_relative_to(root):
        raise ValueError(f"paperkit root {root} does not contain the project {project_dir}")
    return root


def _sandbox_root(project_dir: Path) -> Path:
    """The dir to copy into the Δ mutation sandbox.  An EXPLICIT root wins (PAPERKIT_ROOT env /
    --root / paper.toml — see _root_override); else it is INFERRED: project_dir when the engine
    lives INSIDE it (a self-contained repo — the README at the repo root), else its parent (deps
    are a sibling, ../paperkit).

    The inferred parent is assumed to be a bounded repo.  If it is $HOME OR ABOVE — the case a
    downstream project (engine at ../paperkit, living directly in a home that also holds a
    multi-GB clone / package cache) hits — copying it whole would explode the disk, so we REFUSE
    and tell the user to DECLARE the root.  A clear instruction beats a filled disk."""
    override = _root_override(project_dir)
    if override is not None:
        return override
    inferred = project_dir if _ENGINE.is_relative_to(project_dir) else project_dir.parent
    home, r = Path.home().resolve(), inferred.resolve()
    if r == home or home.is_relative_to(r):
        raise SystemExit(
            f"paperkit: refusing to infer the Δ sandbox root as {r} (your home directory or "
            f"above) — copying it whole would explode the disk.  DECLARE the bounded root: set "
            f"PAPERKIT_ROOT=<dir> in the environment (container pipelines), pass --root <dir>, "
            f'or add [paper] root = "<rel>" to {project_dir.name}/paper.toml.')
    return inferred


def _nested_roots(base: Path) -> list:
    """Directories under `base` that are OTHER paperkit projects (each has its own
    paper.toml).  A root-level project (the README, whose project dir IS the repo)
    must not key on, or mutate, sibling projects' files — only its own + the engine."""
    return [t.parent for t in base.rglob("paper.toml") if t.parent != base]


def _mutable(f: Path) -> bool:
    """A text input Δ may corrupt: a known source suffix, or a versioned git hook
    (no suffix, but a checked artifact — the README's ci claim names it)."""
    return f.is_file() and (f.suffix in MUTABLE_SUFFIXES or ".githooks" in f.parts)


def _copy_sandbox(root: Path, dest: Path) -> None:
    """Copy the sandbox `root` whole into `dest` (SKIP_DIRS + *.pyc pruned as always).

    The root is GUARANTEED bounded by the time we get here — it is either DECLARED
    (PAPERKIT_ROOT / --root / paper.toml [paper] root) or inferred-and-guarded against being
    $HOME-or-above (_sandbox_root).  So a whole copy cannot escape into an unbounded home
    directory (a clone, a package cache): the bound lives on the ROOT, declared once, rather
    than in a lossy per-dir skip (which once dropped .githooks — a real input the paper reads)."""
    shutil.copytree(root, dest, ignore=shutil.ignore_patterns(*SKIP_DIRS, "*.pyc"), dirs_exist_ok=True)
