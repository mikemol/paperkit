#!/usr/bin/env python3
"""The Δ grade CACHE — content hashing and the on-disk cache file, factored out of the
grader/CLI so it can be tested on its own.  A Δ grade is a pure function of the content a
check reads, so it is cached PER CHECK on its read footprint (Φ) over a global engine
EPOCH; content_key is the coarse soundness basis the per-check key refines."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from layout import SKIP_DIRS, _ENGINE, _mutable, _nested_roots


def content_key(project_dir: Path) -> str:
    """A hash of every file a check in this project could read — the project's own files
    plus the engine.  A Δ grade is a pure function of these (the mutation probe only ever
    reads them): the SOUNDNESS BASIS of caching.  The cache itself keys finer — per check,
    on its read footprint plus the engine epoch (see _footprint_hash / _engine_hash) — so
    this whole-project key is no longer the cache key, but the invariant it expresses is
    what makes the finer key sound (a footprint ⊆ this content)."""
    parts = []
    for tag, base in (("proj", project_dir), ("engine", _ENGINE)):
        nested = _nested_roots(base) if tag == "proj" else []
        for f in sorted(base.rglob("*")):
            if (_mutable(f) and not any(p in SKIP_DIRS for p in f.parts)
                    and not any(nr in f.parents for nr in nested)):
                parts.append(f"{tag}/{f.relative_to(base)}:{hashlib.sha256(f.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(sorted(parts)).encode()).hexdigest()


def engine_hash() -> str:
    """A hash of the engine alone — its own global cache EPOCH.  The engine is a universal
    dependency (every check runs through the gate), and footprint() reports only files under
    a project (the engine usually sits OUTSIDE it at ../paperkit), so the read footprint is
    completed by this: an engine edit invalidates every check; a project edit invalidates
    only the checks whose footprint touched it."""
    parts = [f"{f.relative_to(_ENGINE)}:{hashlib.sha256(f.read_bytes()).hexdigest()}"
             for f in sorted(_ENGINE.rglob("*"))
             if _mutable(f) and not any(p in SKIP_DIRS for p in f.parts)]
    return hashlib.sha256("\n".join(sorted(parts)).encode()).hexdigest()


def footprint_hash(project_dir: Path, files: list) -> str:
    """A hash of the current content of a check's recorded footprint files — the per-check
    cache key.  Unchanged ⇒ the check reads the same project inputs ⇒ same verdict ⇒ same
    grade (sound: a check is a pure function of its inputs; the engine is held by engine_hash)."""
    h = hashlib.sha256()
    for rel in sorted(files):
        f = project_dir / rel
        h.update(rel.encode())
        h.update(b"\0")
        h.update(f.read_bytes() if f.is_file() else b"\0MISSING\0")
        h.update(b"\n")
    return h.hexdigest()


def load(project_dir: Path) -> dict:
    p = project_dir / ".delta-cache.json"
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}


def save(project_dir: Path, data: dict) -> None:
    try:
        (project_dir / ".delta-cache.json").write_text(json.dumps(data))
    except Exception:
        pass
