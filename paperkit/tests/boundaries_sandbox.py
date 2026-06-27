#!/usr/bin/env python3
"""Behavioral-boundary examples for Δ·sandbox — the Δ mutation sandbox's ROOT resolution and
whole copy (layout._sandbox_root / _copy_sandbox).

⟨P, F, δ⟩.  To grade a check, Δ copies the sandbox ROOT whole — the bound lives on the root,
DECLARED once (PAPERKIT_ROOT env, which a --root flag overrides, or paper.toml [paper] root),
not in a per-dir skip (which once dropped .githooks, a real input the paper reads).  When no
root is declared it is INFERRED as the parent — but inferring $HOME or above is REFUSED, since
a downstream project living in a home that also holds a clone/cache would explode the disk.

    python3 paperkit/tests/boundaries_sandbox.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import layout  # noqa: E402  (sandbox topology lives in the layout core)


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Δ·sandbox — root resolution + whole copy\n")

    # ── whole copy: the bounded root is copied entire; the bound is the ROOT, not a skip ──
    with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as dt:
        root = Path(t)
        (root / "proj").mkdir(); (root / "proj" / "paper.toml").write_text("x")
        (root / ".githooks").mkdir(); (root / ".githooks" / "pre-commit").write_text("#!/bin/sh")
        (root / "data").mkdir(); (root / "data" / "x.txt").write_text("d")   # not a project — still copied
        (root / ".git").mkdir(); (root / ".git" / "HEAD").write_text("ref")  # SKIP_DIRS
        (root / "bazel-out").mkdir(); (root / "bazel-out" / "huge").write_text("Z" * 9999)  # Ζ·skip: a bazel-* artifact
        dest = Path(dt) / "sb"
        layout._copy_sandbox(root, dest)
        check(".githooks (a real input the paper reads) is copied — not skipped", (dest / ".githooks" / "pre-commit").is_file())
        check("a non-project dir under the bounded root is copied too", (dest / "data" / "x.txt").is_file())
        check("SKIP_DIRS (.git) are still pruned", not (dest / ".git").exists())
        check("a bazel-* artifact is pruned (Ζ·skip — never copy the GB cache)", not (dest / "bazel-out").exists())

    # ── Ζ·skip: _nested_roots walks deep (finds a fixture) but skips SKIP_DIRS, never a bazel-* link ──
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        (root / "a" / "b").mkdir(parents=True); (root / "a" / "b" / "paper.toml").write_text("x")   # deep nested project
        (root / "bazel-out").mkdir(); (root / "bazel-out" / "paper.toml").write_text("x")            # a bazel artifact
        nested = {p.name for p in layout._nested_roots(root)}
        check("_nested_roots finds a DEEP nested project (paper.toml at any depth)", "b" in nested)
        check("_nested_roots skips a bazel-* dir (never descends the cache)", "bazel-out" not in nested)

    # ── root resolution: declarable; env overrides config; both beat inference ──
    saved = os.environ.get("PAPERKIT_ROOT")
    try:
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); proj = root / "proj"; proj.mkdir()
            os.environ.pop("PAPERKIT_ROOT", None)
            (proj / "paper.toml").write_text('[paper]\ntitle = "t"\n')
            check("nothing declared → root is INFERRED as the parent", layout._sandbox_root(proj) == root)
            (proj / "paper.toml").write_text('[paper]\ntitle = "t"\nroot = "."\n')
            check("paper.toml [paper] root pins the root over inference", layout._sandbox_root(proj) == proj)
            os.environ["PAPERKIT_ROOT"] = str(root)
            check("PAPERKIT_ROOT env overrides the paper.toml declaration", layout._sandbox_root(proj) == root)
    finally:
        os.environ.pop("PAPERKIT_ROOT", None) if saved is None else os.environ.__setitem__("PAPERKIT_ROOT", saved)

    print("\n⟨P, F, δ⟩ minimum-delta pair — the home-guard\n")
    saved_r, saved_h = os.environ.get("PAPERKIT_ROOT"), os.environ.get("HOME")
    os.environ.pop("PAPERKIT_ROOT", None)
    with tempfile.TemporaryDirectory() as home:
        # point $HOME at a tmpdir (Path.home() reads it) so a project DIRECTLY in "home" exercises
        # the guard WITHOUT writing to the real home — and so it works inside a hermetic sandbox.
        os.environ["HOME"] = home
        hp = Path(home) / "proj"; hp.mkdir()
        try:
            (hp / "paper.toml").write_text('[paper]\ntitle = "t"\n')
            refused = False
            try:
                layout._sandbox_root(hp)
            except SystemExit:
                refused = True
            (hp / "paper.toml").write_text('[paper]\ntitle = "t"\nroot = "."\n')   # declare → escapes the guard
            ok = refused and layout._sandbox_root(hp) == hp
            fails.append("home-guard") if not ok else None
            print(f"  {'ok ' if ok else 'XX '}declaring a root is the difference between refusal and a sandbox")
            print("      P (inferred ok): parent is a normal dir → root inferred (the cases above)")
            print("      F (refused):     parent is $HOME → SystemExit with guidance to declare a root")
            print("      δ (min delta): the inferred parent being $HOME-or-above (declare to escape)\n")
        finally:
            os.environ.pop("PAPERKIT_ROOT", None) if saved_r is None else os.environ.__setitem__("PAPERKIT_ROOT", saved_r)
            os.environ.pop("HOME", None) if saved_h is None else os.environ.__setitem__("HOME", saved_h)

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (9 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
