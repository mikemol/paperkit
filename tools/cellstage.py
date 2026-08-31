#!/usr/bin/env python3
"""Ζ·mutant·eval (staging) — place the engine's bytecode and deliver ONE counterfactual.

Split out of `tools/eval.py` (Ζ·eval·split).  This module answers one question — *what does the
check see?* — and knows nothing about running it, timing it, or judging the result.

THE BYTECODE PLACEMENT.  The engine is compiled once (//paperkit:pyc, Ζ·pyc·engine) and staged as
`paperkit/<relpath>.pyc` beside the source `paperkit/<relpath>.py`.  `place_engine` moves each
precompiled .pyc to its real import location — `paperkit/<dir>/__pycache__/<stem>.<tag>.pyc` — so
Python runs the bytecode directly (UNCHECKED_HASH ⇒ the source is never rechecked; tools/pyc.py).
No import-time compilation: the def-sweep compiles the engine once, not per eval.

THE COUNTERFACTUAL.  `deliver` dispatches on the site's kind.  A perturbation TOGGLES an
element's presence, and the kinds are the artifact levels at which presence is togglable:

    <module>::<qualname>   swap ONE module's bytecode for its mutant (the def/branch/flip sweep)
    file+:<path>           INJECT an absent file — falsifies a "X does not exist" assertion
    file-:<path>           DROP a present file — falsifies a "X exists" assertion
    content-/content+      TOGGLE a substring in a staged file — the DAG-EDGE perturbation

⚑ THE OPERANDS TRAVEL AS A RECORD, NOT AS SEVEN PARAMETERS.  A first cut passed all of them to
`deliver` and ruff's PLR0913 refused it (7 > 5) — correctly, and for a reason worth keeping: only
two or three apply to any ONE kind, so a flat signature makes every caller supply the operands of
kinds it is not using.  `Site` carries what the cell was told; each deliverer reads the fields its
own kind defines.  Adding a fifth artifact level adds a field and a function, not a parameter to
everything.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
from dataclasses import dataclass

CacheTag = str


@dataclass(frozen=True)
class Site:
    """One cell's counterfactual: the site label plus whatever operands its kind needs."""

    label: str
    module: str = ""
    mutant_py: str = ""
    mutant_pyc: str = ""
    content_path: str = ""
    content_textfile: str = ""


def cache_tag() -> CacheTag:
    """Return this runtime's bytecode cache tag (e.g. `cpython-313`)."""
    return sys.implementation.cache_tag or ""


def slot(py_path: pathlib.Path, tag: CacheTag) -> pathlib.Path:
    """Return the __pycache__ slot a module's bytecode is imported from.

    `paperkit/x.py` → `paperkit/__pycache__/x.<tag>.pyc`, where `tag` matches THIS runtime.
    """
    d = py_path.parent / "__pycache__"
    d.mkdir(parents=True, exist_ok=True)
    return d / (py_path.stem + "." + tag + ".pyc")


def place_engine(engine_dir: str, tag: CacheTag) -> None:
    """Move every staged `.pyc` under `engine_dir` to its real import location."""
    for pyc in pathlib.Path(engine_dir).rglob("*.pyc"):
        if "__pycache__" in pyc.parts:
            continue
        shutil.move(str(pyc), str(slot(pyc.with_suffix(".py"), tag)))


def _inject_file(arg: str) -> None:
    """Create an absent file: its mere EXISTENCE is the counterfactual.

    An empty file suffices — the assertion under test calls `.exists()`, not a content read — so
    no module is mutated.  This is the file analog of an `import+` cell.
    """
    p = pathlib.Path(arg)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("")


def _drop_file(arg: str) -> None:
    """Remove a present file — the counterfactual ABSENCE, the file analog of `import-`."""
    pathlib.Path(arg).unlink(missing_ok=True)


def _toggle_content(op: str, site: Site) -> None:
    """Add or remove a substring in a staged file — the DAG-edge perturbation.

    Dropping `result:paper` from the README's bib makes the "does the README import the paper"
    grep fail.  The substring arrives as a FILE, never a shell argument, so quotes and colons in
    it need no escaping.  Unlink-then-write removes the sandbox HARDLINK rather than the source
    inode — writing in place would corrupt the real tree.
    """
    text = pathlib.Path(site.content_textfile).read_text()
    f = pathlib.Path(site.content_path)
    orig = f.read_text()
    f.unlink(missing_ok=True)
    f.write_text(orig.replace(text, "") if op == "content-" else orig + text)


def _swap_module(site: Site, tag: CacheTag) -> None:
    """Deliver the mutated module on BOTH paths — bytecode AND source.

    The .pyc is what an IMPORT reads; the .py is what a MAIN SCRIPT reads, because a main
    script's bytecode never comes from __pycache__.  Delivering only the .pyc would let an
    entry-point module (project.py) escape its own mutation.  The ∅ baseline passes the module's
    identity .pyc, a no-op swap.

    Unlink first: the mutated module may lie OUTSIDE its own check's closure (Ξ·dag·eval — a
    non-sensitive cell), so it is not staged, and the copy must create rather than overwrite.
    """
    mod = pathlib.Path(site.module)
    mod.unlink(missing_ok=True)
    shutil.copyfile(site.mutant_py, mod)
    shutil.copyfile(site.mutant_pyc, slot(mod, tag))


def deliver(site: Site, tag: CacheTag) -> None:
    """Apply the ONE counterfactual named by `site`.

    ⚑ THE EMPTY-MODULE GUARD IS NOT DEFENSIVE PADDING — IT IS A BUG THIS SPLIT SURFACED.  The
    `else` arm swaps a module, and with `module=""` that is `Path("")` → `.`, so the first call
    was `Path(".").unlink()`: `IsADirectoryError: Is a directory: '.'`.  The pre-split code had
    the same unguarded else and never hit it, because the GENERATOR always supplies a module for
    a non-file site — the guard was the caller's discipline rather than the callee's contract.

    Latent, not introduced: a probe that ran a ∅ baseline WITHOUT `--module` found it in the
    first minute.  A site with nothing to swap is a legitimate cell (a file/content cell reaches
    the same arm when its label is bare), and "the caller always passes it" is exactly the kind
    of invariant that holds until someone writes a new caller.
    """
    op, _, arg = site.label.partition(":")
    if op == "file+":
        _inject_file(arg)
    elif op == "file-":
        _drop_file(arg)
    elif op in ("content-", "content+"):
        _toggle_content(op, site)
    elif site.module:
        _swap_module(site, tag)
