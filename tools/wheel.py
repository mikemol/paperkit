"""Ζ·venv·install — build the engine's WHEEL, the artifact a cell installs the engine FROM.

The engine is already a DECLARED, content-hashed input to every cell (`_data()` adds
`@@//paperkit:engine` unconditionally, so a source edit invalidates the action).  What a cell
could not do is NAME those staged files as a package: `from paperkit import x` needs an
importable `paperkit`, and staged loose files are not one.

⚑ AND THE ANSWER IS INSTALLATION, NOT A DECLARATION POINTING AT THE TREE.  A `.pth` — however
relative — names a ROOT and lets `site.py` resolve it, so it inherits whatever that root turns
out to be; measured, the execroot's `paperkit/` is a SYMLINK to the live working tree, and
`Path(root).resolve()` follows it, so the cell imported unstaged sources.  Installing COPIES:
site-packages holds real files, there is no root to resolve, no symlink to follow, and the
import works from any cwd.  That is what `pip install <wheel>` does and what `-e` does not.

MEASURED:
  * `uv build --offline --wheel`      -> 78 entries: 26 paperkit/ + 47 tools/ + 5 dist-info
  * extraction into a venv            -> 0.077s, STDLIB ONLY (a wheel is a zip)
  * `from paperkit import x` from `/`  -> resolves to site-packages, 0 symlinks in the tree
  * `dependencies = []` (stdlib-only) is WHY this is sound: nothing to resolve, so extracting
    the zip IS a complete install — no pip, no backend, no network in the cell.

⚑⚑ THE WHEEL IS BUILT ONCE, HERE, AND INSTALLED MANY TIMES.  `uv` is a host binary, so keeping
it out of the cell is the point of the split: this action needs it, a cell needs only the
interpreter Bazel already stages plus this declared .whl.

⚑⚑⚑ `library/` IS NOT IN THE WHEEL, and this tool does not put it there.  `resolver._LIBRARY`
walks UP out of the package, so a `concept:` check still needs the library staged as data — the
open Ζ·cite·resolve arc, which pyproject.toml states at length.  Folding it in here would decide
a placement question that comment deliberately refuses.

Usage:  wheel.py build <out.whl> <pyproject.toml>     (needs the DECLARED setuptools backend)
        wheel.py install <venv-dir> <wheel>           (cell side; stdlib only)
"""

import os
import pathlib
import shutil
import sys
import tempfile
import zipfile

_ARGC_BUILD = 4


def _only(matches: list[pathlib.Path], what: str) -> pathlib.Path:
    """Return the ONE match, refusing zero or many.

    A glob that takes `next()` picks the first and discards the rest SILENTLY — the shape that let
    `include = ["paperkit*"]` sweep paperkit/tests into the distribution unnoticed.  A glob is a
    query, and its CARDINALITY is part of the answer.
    """
    if len(matches) != 1:
        msg = f"expected exactly one {what}, found {len(matches)}: {matches}"
        raise SystemExit(msg)
    return matches[0]


def build(out: str, pyproject: str) -> None:
    """Build the wheel from the project rooted at `pyproject`'s directory, into `out`.

    ⚑ THROUGH THE DECLARED BACKEND, NOT THROUGH `uv` (Ζ·wheel·backend).  This shelled out to a
    HOST `uv` at ~/.local/bin, which no sandbox stages — so the action ran no-sandbox, and even
    staged it would not have been hermetic: uv materializes `requires = ["setuptools>=68"]` from
    its own cache (~/.cache/uv/builds-v0), an input nothing declared.  The one thing uv gave us
    was the backend, so the backend is declared instead (MODULE.bazel `pip.parse`, pinned + hashed)
    and called directly through PEP 517.  No host binary, no host cache, no exemption — and the
    action becomes one the remote executor can run, which matters because `uv` is MISSING from the
    executor image (measured).
    """
    from setuptools import build_meta  # noqa: PLC0415 — the declared backend, staged by Bazel

    root = pathlib.Path(pyproject).resolve().parent
    # setuptools REUSES `build/lib`, so a wheel built after `packages` shrank still carries the
    # package that was removed — measured, and it made a real fix look ineffective for two rounds.
    # It is also a second importable `paperkit` that bnd-package-shadow refuses.  Ours at both ends.
    shutil.rmtree(root / "build", ignore_errors=True)
    cwd = os.getcwd()
    try:
        os.chdir(root)                      # PEP 517 builds the project rooted at the CWD
        with tempfile.TemporaryDirectory() as td:
            name = build_meta.build_wheel(td)
            shutil.copyfile(pathlib.Path(td) / name, out)
    finally:
        os.chdir(cwd)
        shutil.rmtree(root / "build", ignore_errors=True)


def install(venv_dir: str, wheel: str, *extra: str) -> str:
    """Create the venv and INSTALL the wheel into it — copies, not a pointer.  Stdlib only."""
    import venv  # noqa: PLC0415 — only the cell side needs it; `build` runs where uv lives

    vd = pathlib.Path(venv_dir).resolve()
    # ⚑ Ζ·cellvenv·race — BUILD TO A PRIVATE PATH, THEN CLAIM THE SHARED NAME ATOMICALLY.
    # `clear=True` on the shared path was a RACE: sandboxed cells share an execroot, so several
    # run `install "$PWD/.cellvenv"` concurrently and one clears the tree another is walking.
    # MEASURED (//:hook, 2026-09-05): four `FileNotFoundError: .../.cellvenv/lib` tracebacks out
    # of venv's own `clear_directory` -> `shutil.rmtree` -> `os.rmdir`, from four different cells.
    # An already-built venv is REUSED rather than rebuilt: this function is content-determined
    # (same wheel + same deps -> same tree), so a present marker means the work is already done —
    # which is [[bazel-action-idempotency]] applied to the action's own scratch space.
    marker = vd / ".pk-complete"
    if not marker.exists():
        tmp = vd.with_name(vd.name + f".{os.getpid()}.tmp")
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        # --symlinks, NOT --copies: measured, `--copies` copies the interpreter binary but NOT
        # libpython3.13.so, and the venv dies with "error while loading shared libraries".  This
        # is the ONE outward symlink, and it points at the interpreter Bazel itself staged.
        venv.EnvBuilder(with_pip=False, symlinks=True, clear=True).create(tmp)
        _populate(tmp, wheel, extra)
        (tmp / ".pk-complete").write_text("")
        try:
            os.rename(tmp, vd)                    # atomic when the name is free
        except OSError:
            # A peer won the race and the shared name now exists, complete.  Its content equals
            # ours by construction, so DISCARD OURS rather than clobbering a venv in use.
            shutil.rmtree(tmp, ignore_errors=True)
    return str(vd / "bin" / "python")


def _populate(vd: pathlib.Path, wheel: str, extra: tuple) -> None:
    """Extract the engine wheel and name the dep roots.  Split out of `install` so the build
    happens at a private path — see Ζ·cellvenv·race above."""
    sp = _only(sorted(vd.glob("lib/python*/site-packages")), "site-packages dir")
    # A wheel IS a zip, and this project's `dependencies = []` means extraction is a COMPLETE
    # install: no dependency resolution to run, so no pip and no uv are needed in the cell.
    # ⚑ Ζ·render·pydeps — N WHEELS, NOT ONE.  `wheel` is the engine; anything after it is a
    # DECLARED project dependency (render's pikepdf / pillow / python-docx and their closure),
    # staged by Bazel from a pinned, hashed lock.  Extracting them into the same site-packages is
    # what stops a check reaching for whatever the host happened to have — MEASURED before
    # declaring: pikepdf and PIL resolved under bare python3 and NOT under the repo venv, so a
    # verdict depended on which interpreter its tier handed it.
    with zipfile.ZipFile(wheel) as z:
        z.extractall(sp)

    # ⚑ THE DEPS ARE NOT WHEELS — THEY ARE ALREADY-EXTRACTED site-packages TREES.  rules_python's
    # `@hub//<pkg>:pkg` stages the unpacked distribution (MEASURED: 44 files under
    # `.../pk_render_313_pikepdf/site-packages/`), so `zipfile.ZipFile` on one raises BadZipFile.
    # The first cut of this function unzipped every argument and died exactly there.  What the
    # venv needs from them is their ROOT on its path, and a .pth in site-packages is how a venv
    # names an additional root — the same mechanism, used correctly this time: a .pth naming a
    # STAGED ABSOLUTE root inside the execroot, not one resolving out of the sandbox.
    roots = []
    for d in extra:
        marker = "/site-packages/"
        if marker in d:
            r = d.split(marker)[0] + "/site-packages"
            if r not in roots:
                roots.append(r)
    if roots:
        (sp / "_pydeps.pth").write_text(
            "\n".join(str(pathlib.Path(r).resolve()) for r in roots) + "\n")


if __name__ == "__main__":
    if sys.argv[1] == "build":
        if len(sys.argv) != _ARGC_BUILD:
            raise SystemExit(__doc__)
        build(sys.argv[2], sys.argv[3])
    else:
        sys.stdout.write(install(sys.argv[2], sys.argv[3], *sys.argv[4:]) + "\n")
