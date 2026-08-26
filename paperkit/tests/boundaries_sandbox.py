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
import pathlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import layout  # noqa: E402  (sandbox topology lives in the layout core)


def main() -> int:
    fails = []

    ran = []

    def check(desc, cond):
        # Λ·guard-must-not-copy — `ran` COUNTS the arms; the summary must not restate a number
        # authored beside the set it describes.  This suite printed a hardcoded "9 behaviors" while
        # 13 arms ran, and would have kept printing 9 however many were added or deleted: a reader
        # trusting that line would read a SHRINKING suite as an unchanged one.
        ran.append(desc)
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

    # ── Ζ·sandbox·copy·pin: the copy must give each file a FRESH INODE ────────────────────────
    # Δ mutates source files IN PLACE with write_text, which opens O_TRUNC and writes THROUGH the
    # inode.  That is safe only because copytree ALLOCATES new inodes, so the mutation cannot reach
    # the original — a property nobody chose for this reason and nothing asserted.  It matters now
    # that dedup is a real operation on this machine: 173 files in this repo are multiply-linked,
    # library/routes.py among them, sharing an inode with a DIFFERENT repo (gcalculus).  A
    # link-preserving copy (`cp -al`, or copytree(copy_function=os.link) — a plausible speed
    # optimisation nobody would flag as risky) would make a def-sweep write paperkit mutants into a
    # downstream consumer's checkout, transiently, hundreds of times per hook run, with git seeing
    # nothing because content is unchanged once the revert lands.
    #
    # The F arm below PERFORMS the regression rather than describing it (Λ·instrument-vs-gate: a
    # guard earns trust against the real failure, both directions), so this pins a property of the
    # ACT and would red the moment the copy strategy changed.
    with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as dt:
        root = Path(t) / "root"
        (root / "sub").mkdir(parents=True)
        src = root / "sub" / "mod.py"
        src.write_text("ORIGINAL\n")
        twin = Path(t) / "twin.py"          # the deduped state: a second link, outside the root
        os.link(src, twin)

        dest = Path(dt) / "sb"
        layout._copy_sandbox(root, dest)
        copied = dest / "sub" / "mod.py"
        check("P: the copy gets a FRESH inode (links back to 1)",
              copied.stat().st_nlink == 1 and copied.stat().st_ino != src.stat().st_ino)

        copied.write_text("MUTANT\n")       # exactly what the grader does to a sandbox file
        check("P: mutating the copy leaves the ORIGINAL untouched", src.read_text() == "ORIGINAL\n")
        check("P: ...and leaves its hardlinked twin untouched", twin.read_text() == "ORIGINAL\n")

        # F — the same copy made link-preserving: the mutation reaches both.
        linked = Path(dt) / "linked"
        shutil.copytree(root, linked, copy_function=os.link)
        lcopy = linked / "sub" / "mod.py"
        lcopy.write_text("MUTANT\n")
        check("F: a LINK-PRESERVING copy corrupts the original (the regression this pins)",
              src.read_text() == "MUTANT\n" and twin.read_text() == "MUTANT\n")
        print("     δ: copytree's copy_function — copy2 (fresh inode) vs os.link (shared inode).")

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
            ran.append("home-guard")
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
    # ---- Ζ·delta·tmpdir: sweep sandboxes are DISK-backed, not tmpfs ----
    # Each concurrent def-sweep copies the whole repo (measured on paperkit: 1.4-3.2GB per copy,
    # three concurrent = 7.2GB).  On a distro whose /tmp is tmpfs that is RAM — so the copies
    # compete with the page cache AND with the memory budget the sweep schedules against, one
    # resource counted once and spent twice.  Measured: a //:hook run filled a 7.7GB /tmp to 100%
    # and nothing on the box could write a temp file.
    import grader as G
    sd = G._scratch_dir()
    check("scratch: a disk-backed scratch dir is resolved by default", sd is not None)
    check("scratch: and it is NOT the tmpfs /tmp", not str(sd).startswith("/tmp"))
    old = os.environ.get("PAPERKIT_SCRATCH")
    try:
        os.environ["PAPERKIT_SCRATCH"] = "/tmp"
        check("scratch: PAPERKIT_SCRATCH overrides it — a box that WANTS tmpfs can say so",
              G._scratch_dir() == "/tmp")
    finally:
        os.environ.pop("PAPERKIT_SCRATCH", None)
        if old is not None:
            os.environ["PAPERKIT_SCRATCH"] = old

    # ---- Ζ·delta·leak: the reaper collects what a SIGKILL left ----
    # _grade_one's `finally: rmtree` is correct and runs on every normal exit.  It does NOT run
    # on SIGKILL, and a long sweep gets killed: three interrupted //:hook runs left 42 husks.
    d = pathlib.Path(tempfile.mkdtemp())
    try:
        os.environ["PAPERKIT_SCRATCH"] = str(d)
        husk = d / (G._SANDBOX_PREFIX + "husk")
        husk.mkdir()
        os.utime(husk, (0, 0))                        # backdate it well past the window
        live = d / (G._SANDBOX_PREFIX + "live")
        live.mkdir()                                  # fresh: a running sweep's copy
        n = G.reap_sandboxes(older_than_s=1800)
        check("reap: an OLD sandbox with no live sweep is collected", n == 1 and not husk.exists())
        check("reap: a FRESH one is left alone — a live sweep's copy is not a corpse",
              live.exists())
        check("reap: reaping an empty scratch is a no-op, not an error",
              G.reap_sandboxes(older_than_s=1800) == 0)
    finally:
        os.environ.pop("PAPERKIT_SCRATCH", None)
        if old is not None:
            os.environ["PAPERKIT_SCRATCH"] = old
        shutil.rmtree(d, ignore_errors=True)

    bad = len([b for b in ran if not b])
    if bad:
        print(f"BOUNDARIES: FAIL ({bad} of {len(ran)} behaviors drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, 2 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
