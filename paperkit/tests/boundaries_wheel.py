#!/usr/bin/env python3
"""Behavioral-boundary examples for Ζ·wheel·library — WHAT THE BUILT DISTRIBUTION CONTAINS.

⟨P, F, δ⟩.  `pyproject.toml` makes three assertions about the wheel, in prose, and until this
suite existed NOTHING checked any of them:

    "THE WHEEL MUST NOT CARRY `tools`"      — and it carries 48 modules
    "an installed paperkit resolves no concept at all"   — the library is absent
    "Ζ·wheel·library is the test that catches it if this drifts"  — the test did not exist

⚑ THE COMMENT NAMED A MECHANISM THAT CANNOT EXPRESS ITS OWN INTENT.  `packages = ["paperkit",
"tools"]` is what BOTH the editable install exposes and the wheel ships, so listing `tools`
ships it; `[tool.setuptools.exclude-package-data]` excludes non-Python DATA files and has no
effect on a package's modules.  The file says the two views "disagree BY CONSTRUCTION" — they
agree, and the artifact was never read to notice.  That is why this suite reads the ARTIFACT and
never the declaration: a claim about a build output, verified against the output.

⚑⚑ THE PROMISED TEST IS THE POINT, NOT THE COUNT.  This suite deliberately does NOT hardcode
"48 tools modules" or "26 engine modules" — a guard carrying its own copy of the set it guards
certifies a tautology (guard-must-not-copy).  It asserts STRUCTURE: which top-level names appear,
and whether a `concept:` key can resolve from the installed tree.

⚑⚑⚑ AND IT MUST BE ABLE TO FAIL.  Written while the wheel was WRONG, so the F arm is today's
artifact rather than a synthetic one: `tools/` present is a real, measured failure, not a
hypothetical the suite was shaped around after the fix.

    python3 paperkit/tests/boundaries_wheel.py
"""
from __future__ import annotations

import importlib.util
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
# ⚑ THE PRECONDITION IS THE BACKEND, NOT `uv` (Ζ·wheel·backend).  This gated on `shutil.which("uv")`
# back when tools/wheel.py shelled out to it; the builder now calls the DECLARED PEP 517 backend, so
# uv's absence says nothing and gating on it would report cannot-run on a box that builds fine.
# What the build genuinely cannot proceed without is setuptools — so that is what is asked.
_BACKEND = importlib.util.find_spec("setuptools") is not None
_CANNOT_RUN = 3         # engine-aligned (gate.py _REFUSE): "could not verify", not "failed"


def built_wheel() -> Path | None:
    """Return the wheel THE BUILD MADE, staged as a declared input (`reads = {., wheel}`).

    ⚑ READ THE ARTIFACT, DO NOT MAKE ONE.  This built its own wheel — first by shelling out to
    `uv`, then through the declared PEP 517 backend — which meant the CHECK needed a build
    toolchain of its own and reported cannot-run without it.  The build already produces
    //paperkit:wheel, content-addressed and declared; a claim about "what a consumer receives"
    should be asserted against THAT, not against a second wheel the test made for itself under
    conditions the real build does not share.  Exactly the false green this arc found: the
    library was in the artifact only because the test's builder ran unsandboxed.
    """
    # ⚑ Ζ·wheel·stage — SEARCH THE STAGED PATH, NOT THE CONVENIENCE SYMLINK.  `reads = {wheel}`
    # makes Bazel stage //paperkit:wheel as a declared input, and a declared input lands at its
    # EXECROOT-RELATIVE path (`bazel-out/<cfg>/bin/paperkit/wheel.whl`).  `bazel-bin/` is a
    # convenience symlink in the WORKSPACE; it does not exist inside a hermetic sandbox, so every
    # candidate below was a workspace path and the check reported cannot-run WITH THE ARTIFACT
    # PRESENT IN ITS OWN CELL.  MEASURED 2026-09-06: `bnd-wheel` cannot-run while
    # bazel-bin/paperkit/wheel.whl was 413,635 bytes on disk — the check was looking outside the
    # sandbox for a file the sandbox had already handed it.
    #
    # The glob is over `bazel-out` because the configuration segment (`k8-fastbuild`) is not the
    # check's to know: naming it would hardcode a value the build owns.
    # ⚑ Ζ·builds·path — READ THE PATH THE BUILD HANDED US, before guessing any layout.
    #
    # PAPERKIT_BUILT_ARTIFACTS carries `basename=$PWD/<execroot-relative path>` for every `builds`
    # label, exported before the cd — the same idiom PAPERKIT_CONSUMED_RECORDS uses for records,
    # whose comment states the property this check needs: "so the check finds each record REGARDLESS
    # OF CWD".  Every fallback below is a WORKSPACE-relative guess, and a cell runs with
    # cwd=<project> where neither `bazel-out` nor `bazel-bin` exists; this check learned that once
    # (the bazel-bin note above) and then globbed `bazel-out`, which is the same mistake one layer
    # in.  Operator: "you want build artifacts, not symlinks."
    for pair in os.environ.get("PAPERKIT_BUILT_ARTIFACTS", "").split():
        key, _, val = pair.partition("=")
        if key == "wheel.whl" and Path(val).is_file():
            return Path(val)
    # ⚑⚑ THE FALLBACK LADDER IS GONE, AND ITS ABSENCE IS THE FIX.  It was:
    #     bazel-out/*/bin/paperkit/wheel.whl        workspace-relative
    #     bazel-bin/paperkit/wheel.whl              workspace symlink
    #     ROOT/bazel-bin/paperkit/wheel.whl         ⚑ SCRIPT-relative, so it reached the REAL
    #                                                 CHECKOUT FROM ANY CWD
    #     Path().rglob("wheel.whl")                 whatever happened to be under cwd
    #
    # MEASURED: from a bare temp directory with no workspace anywhere above it, the suite still
    # PASSED — `ROOT` is `Path(__file__).resolve().parent.parent.parent`, so the third rung walked
    # out to /home/.../paperkit/bazel-bin and read the artifact from OUTSIDE any cell.  That is a
    # check "green by accident of location rather than by declaration", which is the exact false
    # green this file's own docstring says bnd-wheel exists to prevent — reintroduced in the very
    # function that finds the artifact.
    #
    # ⚑ It also made the defect undiagnosable: the suite passed on the host, passed from the
    # execroot, and redded only in a sandbox, where the staged copy makes ROOT the sandbox and the
    # rungs finally fail.  Three attempts were spent refuting hypotheses because the instrument
    # could not tell "I was handed the artifact" from "I walked to the checkout and found one".
    #
    # Now: the build hands the path, or the check reports CANNOT-RUN.  No layout is guessed.
    return None


def tops(whl: Path) -> dict[str, int]:
    """Top-level name -> entry count, read from the ARTIFACT rather than from any declaration."""
    with zipfile.ZipFile(whl) as z:
        names = z.namelist()
    out: dict[str, int] = {}
    for n in names:
        out[n.split("/")[0]] = out.get(n.split("/")[0], 0) + 1
    return out


def main() -> int:
    """Build the wheel and assert its top-level contents; 3 if uv is absent."""
    whl = built_wheel()
    if whl is None:
        print("Ζ·wheel·library: CANNOT RUN — //paperkit:wheel is not staged (reads = {., wheel})")
        return _CANNOT_RUN

    fails: list[str] = []
    ran: list[str] = []

    def check(desc: str, cond: bool) -> None:
        # guard-must-not-copy — `ran` COUNTS the arms; no authored total to drift.
        ran.append(desc)
        if not cond:
            fails.append(desc)
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Ζ·wheel·library — what the BUILT distribution contains\n")

    t = tops(whl)
    dist = [k for k in t if k.endswith(".dist-info")]

    check(f"the wheel ships the engine package (paperkit: {t.get('paperkit', 0)} entries)",
          t.get("paperkit", 0) > 0)
    check("the wheel carries exactly one .dist-info", len(dist) == 1)
    # ⚑ THE ARM THAT FAILS TODAY.  pyproject.toml: "THE WHEEL MUST NOT CARRY `tools`".
    check(f"the wheel does NOT carry `tools` (found: {t.get('tools', 0)} entries)",
          "tools" not in t)
    # ⚑ AND SUBPACKAGES ARE PART OF THE SURFACE, which the top-level read alone cannot see.
    # Measured while fixing Ζ·wheel·tools: `include = ["paperkit*"]` is a GLOB, and it swept
    # `paperkit/tests/` — the boundary suites — into a consumer's install.  A top-level-only
    # arm passes that, so the arm that catches it reads one level down.  The dev-facing
    # subpackages are named as the set they are (tests, tools), not counted.
    with zipfile.ZipFile(whl) as z:
        subs = sorted({n.split("/")[1] for n in z.namelist()
                       if n.startswith("paperkit/") and n.count("/") > 1})
    # ⚑ AND THE ARM THAT USED TO SIT HERE ASSERTED THE OPPOSITE, WRONGLY.  It refused `tests`
    # as dev-only — reasoning about a consumer's install without asking who IMPORTS it — and
    # removing it broke five checks with `No module named 'paperkit.tests'`, because the cells
    # run those suites out of this very wheel.  What the surface must exclude is `tools` (the
    # sweep's cell runner, which nothing in the engine imports as a package); what it must
    # INCLUDE is the recorder five suites depend on.  Both directions are asserted, so neither
    # can be restored by accident.
    check(f"the wheel ships the suites' shared recorder (paperkit.tests: {'tests' in subs})",
          "tests" in subs)
    check(f"the wheel ships no `tools` subpackage (found: {'tools' in subs})",
          "tools" not in subs)

    # Ζ·cite·resolve — the library is the terminal owner of the per-key `concept:` fallthrough,
    # and it lives OUTSIDE the package (resolver._LIBRARY walks up), so a wheel omits it and an
    # installed paperkit resolves no concept.  Asserted here so the gap is a RED, not a comment.
    # ⚑ INSIDE THE PACKAGE, NOT BESIDE IT (Ζ·cite·resolve).  This counted a TOP-LEVEL `library` key
    # — the pre-move layout — so it stayed RED after the move that fixed the very gap it was written
    # for.  A generic top-level `library/` in every consumer's site-packages is what the move
    # avoided (the same namespace capture that keeps `tools` out), so the arm asks for the library
    # where it now lives: package data under paperkit/.
    with zipfile.ZipFile(whl) as _z:
        libn = sum(1 for n in _z.namelist() if n.startswith("paperkit/library/"))
    check(f"the wheel carries the concept library as package data (paperkit/library: {libn})",
          libn > 0)

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    # The delta is one line of pyproject.toml: whether `packages` names `tools`.  P reads the
    # engine's own top-level set from the artifact; F is what that set becomes with the extra
    # package declared — which is TODAY's wheel, so the F arm is measured, not synthesized.
    shipped = sorted(k for k in t if not k.endswith(".dist-info"))
    print(f"  {'XX ' if 'tools' in shipped else 'ok '}the wheel's top-level names are the "
          "DISTRIBUTION's surface, not the dev environment's")
    print("      P (intended):  ['library', 'paperkit']")
    print(f"      F (measured):  {shipped}")
    print("      δ (min delta): one name in pyproject.toml's `packages`\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
