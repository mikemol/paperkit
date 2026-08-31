#!/usr/bin/env python3
"""Project file TOPOLOGY — the small shared foundation under both the cache and the grader:
which files Δ may read/corrupt, where the mutation sandbox is rooted, and which directories
are OTHER projects.  Factored out so neither the cache nor the grader has to own it (and so
each can be imported and tested without the other).
"""
from __future__ import annotations

import fnmatch
import os
import shutil
import tempfile
import tomllib
from pathlib import Path

import config

# Ζ·surface·admit — the suffixes Δ may corrupt.  This is a PROXY for the real property ("could
# this file's content change a claim's truth"), and every proxy carries an error term: a file the
# proxy excludes is unfalsifiable BY CONSTRUCTION, however precisely the claim names it.  `.json`
# and `.bzl` were absent, which the unmeasured-reads axis (Ζ·surface·kind) then MEASURED as two
# live gaps: `setup/reference.json`, whose project prose asserts "Δ can corrupt it and flip the
# verdict" while Δ could not, and `tools/grade.bzl`, which bnd-ladder makes assertions about and
# could not falsify.  Admitted deliberately, off a measurement, rather than guessed.
# `.pm`, `.yaml`/`.yml` and `.conf` were the next live gaps, measured the same way: a paper written
# ABOUT A SERVICE rather than about paperkit grounds its code-facts in that service's sources, and
# every such check read a suffix the sweep could not corrupt.  Twelve checks in one such project
# graded `indeterminate` while being plainly falsifiable in fact — edit the Perl and they go red —
# so the grade was measuring the sweep's reach, not the check's strength.  Admitted off that
# measurement.  The set is TEXT SOURCES a claim can be grounded in; binary and archive formats
# (`.gz`, images) stay out, and a check reading only those is honestly reported as unmeasured.
MUTABLE_SUFFIXES = {".bib", ".tsv", ".toml", ".md", ".sh", ".py", ".txt", ".json", ".bzl",
                    ".pm", ".pl", ".yaml", ".yml", ".conf"}
# ...except DERIVED files, which are outputs rather than inputs.  A .pyc is excluded by SKIP_DIRS
# (it lives in __pycache__); a Δ cache is not in any skip dir, so it is named here.  Corrupting an
# output cannot falsify a claim — it only makes the sweep measure its own bookkeeping (and a cache
# entering the surface the moment `.json` was admitted is exactly the kind of quiet coupling the
# admission had to be measured for).  See [[pyc-is-a-build-artifact]]: a derived file is a BUILD
# ARTIFACT, and the input is its source.
DERIVED_NAMES = {".delta-cache.json"}
# `bazel-*` are convenience symlinks into the multi-GB Bazel cache; a glob (ignore_patterns
# is fnmatch) keeps _copy_sandbox from following them and exploding the Δ sandbox (Ζ·skip).
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules", "out", "bazel-*"}
_ENGINE = Path(__file__).resolve().parent

# Ω·config — the knob this module RESOLVES, declared here (place-by-ownership; the kernel hosts
# the mechanism only).  NOTE: resolver._ENV_DROP names "PAPERKIT_ROOT" as a string LITERAL (it
# cannot import layout upward) — keep the two in sync.
ROOT = config.Param("root", "PAPERKIT_ROOT", config="root",
                    help="the Δ sandbox's bounded universe (the dir copied to mutate); else inferred, $HOME refused")


def _root_override(project_dir: Path) -> Path | None:
    """An EXPLICIT sandbox root — for container pipelines and downstream projects whose parent
    is not a tidy repo.  Resolved through the ONE config pipeline (Ω·config): PAPERKIT_ROOT env
    (a --root flag overrode it by setting it) > paper.toml [paper] root > none.  Whichever is
    set must CONTAIN the project.
    """
    paper = {}
    cfg = project_dir / "paper.toml"
    if cfg.is_file():
        try:
            paper = tomllib.loads(cfg.read_text()).get("paper", {})
        except Exception:
            paper = {}
    decl = config.resolve(ROOT, paper)
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
    and tell the user to DECLARE the root.  A clear instruction beats a filled disk.
    """
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
    """Directories under `base` that are OTHER paperkit projects (each has its own paper.toml,
    at ANY depth — e.g. paper/checks/fixture).  A root-level project (the README, whose dir IS
    the repo) must not key on or mutate sibling projects' files — only its own + the engine.
    Walks with SKIP_DIRS PRUNED and symlinks NOT followed (os.walk default), so a bazel-* link
    into the GB cache is never traversed (Ζ·skip).
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames
                       if not any(fnmatch.fnmatch(d, s) for s in SKIP_DIRS)]
        if "paper.toml" in filenames and Path(dirpath) != base:
            out.append(Path(dirpath))
    return out


def _suffixless_text(f: Path) -> bool:
    """A file with NO suffix that decodes as text — the CLASS of extensionless versioned commands
    (`scripts/summit`, `scripts/check`, `bin/pk`, a `.githooks/` hook, a `Containerfile`): a witness
    reads it and mutating its content can change a claim, so Δ must be able to corrupt it.  This
    generalizes the old one-off `.githooks` exception to the class it belonged to (summit's
    ask-delta-extensionless): the exception was drawn around ONE artifact, not the property.  Keyed
    on CONTENT (a NUL byte ⇒ binary, so a compiled command is excluded)
    because the Δ sandbox is a copy without `.git` and mode is not reliable there — content is the
    only signal always present.  MUTABLE_SUFFIXES still owns the SUFFIXED text files; this owns the
    suffixless ones, and together they are a closer proxy for "could this file's content change a
    claim's truth" than suffix alone (Ζ·surface·admit).
    """
    if f.suffix != "":
        return False
    try:
        head = f.read_bytes()[:4096]
    except OSError:
        return False
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _mutable(f: Path) -> bool:
    """A text input Δ may corrupt: a known source suffix, or a suffixless text command (a versioned
    executable a witness reads — `scripts/*`, `bin/pk`, `.githooks/` hooks; the CLASS, not the one
    `.githooks` artifact the exception used to name — ask-delta-extensionless).
    """
    return (f.is_file() and f.name not in DERIVED_NAMES
            and (f.suffix in MUTABLE_SUFFIXES or _suffixless_text(f)))


def _copy_sandbox(root: Path, dest: Path) -> None:
    """Copy the sandbox `root` whole into `dest` (SKIP_DIRS + *.pyc pruned as always).

    The root is GUARANTEED bounded by the time we get here — it is either DECLARED
    (PAPERKIT_ROOT / --root / paper.toml [paper] root) or inferred-and-guarded against being
    $HOME-or-above (_sandbox_root).  So a whole copy cannot escape into an unbounded home
    directory (a clone, a package cache): the bound lives on the ROOT, declared once, rather
    than in a lossy per-dir skip (which once dropped .githooks — a real input the paper reads).
    """
    shutil.copytree(root, dest, ignore=shutil.ignore_patterns(*SKIP_DIRS, "*.pyc"), dirs_exist_ok=True)
