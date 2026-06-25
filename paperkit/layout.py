#!/usr/bin/env python3
"""Project file TOPOLOGY — the small shared foundation under both the cache and the grader:
which files Δ may read/corrupt, where the mutation sandbox is rooted, and which directories
are OTHER projects.  Factored out so neither the cache nor the grader has to own it (and so
each can be imported and tested without the other)."""
from __future__ import annotations

from pathlib import Path

MUTABLE_SUFFIXES = {".bib", ".tsv", ".toml", ".md", ".sh", ".py", ".txt"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "out"}
_ENGINE = Path(__file__).resolve().parent


def _sandbox_root(project_dir: Path) -> Path:
    """The dir to copy into the mutation sandbox: project_dir itself when the engine
    lives INSIDE it (a self-contained project — the README at the repo root, whose
    deps are paperkit/), else its parent (a project whose deps are a sibling — the
    paper's ../paperkit — or a self-contained fixture whose engine is elsewhere)."""
    return project_dir if _ENGINE.is_relative_to(project_dir) else project_dir.parent


def _nested_roots(base: Path) -> list:
    """Directories under `base` that are OTHER paperkit projects (each has its own
    paper.toml).  A root-level project (the README, whose project dir IS the repo)
    must not key on, or mutate, sibling projects' files — only its own + the engine."""
    return [t.parent for t in base.rglob("paper.toml") if t.parent != base]


def _mutable(f: Path) -> bool:
    """A text input Δ may corrupt: a known source suffix, or a versioned git hook
    (no suffix, but a checked artifact — the README's ci claim names it)."""
    return f.is_file() and (f.suffix in MUTABLE_SUFFIXES or ".githooks" in f.parts)
