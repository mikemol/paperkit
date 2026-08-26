#!/usr/bin/env python3
"""The Δ grade CACHE — content hashing and the on-disk cache file, factored out of the
grader/CLI so it can be tested on its own.  A Δ grade is a pure function of the content a
check reads, so it is cached PER CHECK on its read footprint (Φ) over a global engine
EPOCH; content_key is the coarse soundness basis the per-check key refines."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import durable
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


def _def_index(text: str) -> dict:
    """{qualname: body-source} for a .py source — the DEFINITION granularity Δ already mutates at."""
    import mutate
    lines = text.splitlines(keepends=True)
    out = {}
    for qual, node in mutate._def_sites(text):
        out[qual] = "".join(lines[node.body[0].lineno - 1:node.end_lineno])
    return out


def footprint_hash(project_dir: Path, files: list, sensitive: list | None = None) -> str:
    """A hash of the current content of a check's recorded footprint — the per-check cache key.

    Δ·grain — keyed at DEFINITION granularity when the grade supplies one, because the file is
    far too coarse a unit to invalidate on.  Measured on a 124-claim consumer: editing
    `concepts.py` invalidated 100 of 124 checks and editing `routes.py` invalidated all 124,
    because the modules every witness reads are exactly the modules an author edits.  The
    invalidation RULE was already right — re-grade a check iff what it reads changed — but it
    was applied at a grain the project has almost no diversity in, so every commit discarded the
    whole cache and a full def-resolution sweep had to start from zero.

    The finer key needs no new measurement.  A def-resolution grade already records, per
    DEFINITION in the read surface, whether mutating it flips the check: that is `tests`.  So:

        added / removed / renamed defs   caught by hashing each read file's sorted QUALNAME set
        a def the check IS sensitive to  caught by hashing that definition's body
        anything else in a read file     comments, docstrings, and definitions the check does
                                         not depend on — deliberately NOT hashed
        non-.py reads (bibs, data)       hashed whole, as before

    SOUNDNESS, and its limit, stated plainly.  This is STRICTLY WEAKER than hashing whole files.
    It holds exactly as far as Δ's own mutation-adequacy assumption does: a definition absent
    from `tests` is one whose body→raise did NOT flip the check, so the check does not exercise
    it, so editing it cannot change the verdict.  A check that CATCHES the injected exception
    would be recorded insensitive while still depending on the definition, and such a check
    would now reuse a stale grade.  That is the same blind spot the grade itself has — the cache
    is no more trusting than the measurement it caches — but it is a real one, so the finer key
    is used ONLY where the sensitivity is DEF-GRANULAR: a `behavioral` grade whose `tests` name
    definitions (`file::qual`).  A FILE-granular set keeps the WHOLE-file key — a file-resolution
    grade (where the whole file is the mutation unit, so a .py names no definition), or an
    indeterminate/vacuous grade with no measured surface: surface-only there would MISS a def-body
    edit the file-level grade is genuinely sensitive to, and a check nothing flipped today may be
    flipped by tomorrow's edit.  So `fine` must be NON-EMPTY (a real def-granular test to key on),
    not merely present, before a .py is hashed at definition granularity."""
    h = hashlib.sha256()
    fine = {}
    if sensitive:
        for t in sensitive:
            rel, _, qual = t.partition("::")
            if qual:
                fine.setdefault(rel, set()).add(qual)
    for rel in sorted(files):
        f = project_dir / rel
        h.update(rel.encode())
        h.update(b"\0")
        if fine and rel.endswith(".py") and f.is_file():
            try:
                idx = _def_index(f.read_text())
            except Exception:
                idx = None
            if idx is not None:
                h.update("|".join(sorted(idx)).encode())      # the SURFACE: add/remove/rename
                h.update(b"\0")
                for q in sorted(fine.get(rel, ())):           # only what this check depends on
                    h.update(q.encode())
                    h.update(idx.get(q, "\0GONE\0").encode())
                h.update(b"\n")
                continue
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
        durable.write_atomic(project_dir / ".delta-cache.json", json.dumps(data))
    except Exception:
        pass
