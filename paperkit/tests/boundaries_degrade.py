#!/usr/bin/env python3
"""Behavioral-boundary examples for Φ·degrade — resolver.footprint when strace is unavailable.

⟨P, F, δ⟩.  The footprint needs strace.  When strace is ABSENT (not installed) or CANNOT ATTACH
(no ptrace capability — a hardened container, an empty trace), footprint must return the SENTINEL
None, never []: None ⇒ don't-cache + full-surface sweep; [] would hash STABLE (the cache would
over-reuse a grade whose inputs were never traced) and scope the sweep to nothing.  A real check
that reads nothing under the project is legitimately [].

    python3 paperkit/tests/boundaries_degrade.py
"""
from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import resolver  # noqa: E402


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Φ·degrade — footprint when strace is unavailable\n")
    real_run = resolver.subprocess.run
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "a.txt").write_text("FOO\n")
        check("with strace, a cmd: footprint is the file it reads", resolver.footprint("cmd:grep -q FOO a.txt", d, {}) == ["a.txt"])
        check("file: needs no strace — always its target", resolver.footprint("file:a.txt", d, {}) == ["a.txt"])
        check("a check that reads nothing under the project is legitimately [] (cacheable)", resolver.footprint("cmd:true", d, {}) == [])
        try:
            resolver.subprocess.run = lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("strace"))
            absent = resolver.footprint("cmd:grep -q FOO a.txt", d, {})

            def empty_trace(argv, **k):
                Path(argv[argv.index("-o") + 1]).write_text("")   # strace attached to nothing
                return types.SimpleNamespace(returncode=1)
            resolver.subprocess.run = empty_trace
            no_ptrace = resolver.footprint("cmd:grep -q FOO a.txt", d, {})
        finally:
            resolver.subprocess.run = real_run
        check("strace ABSENT (FileNotFoundError) → footprint degrades to None, not a crash", absent is None)
        check("strace cannot ATTACH (empty trace) → None, not []", no_ptrace is None)
        check("the live engine is restored after the test", resolver.footprint("file:a.txt", d, {}) == ["a.txt"])

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    from cache import footprint_hash
    with tempfile.TemporaryDirectory() as t:
        d = Path(t); (d / "a.txt").write_text("FOO\n")
        # [] hashes the SAME no matter the project content — a stored [] entry would ALWAYS cache-hit
        h1 = footprint_hash(d, [])
        (d / "a.txt").write_text("CHANGED\n")
        h2 = footprint_hash(d, [])
        stable = h1 == h2
        fails.append("empty-hashes-stable") if not stable else None
        print(f"  {'ok ' if stable else 'XX '}the empty footprint [] hashes STABLE across an edit — so it must NOT hold an untraceable grade")
        print("      P (unknown):  None  — uncacheable; re-grade every run, sweep the FULL surface")
        print("      F (empty):    []    — content-independent hash; a genuine reads-nothing, cacheable")
        print("      δ (min delta): None vs [] — collapsing them caches a grade whose inputs were never traced\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (7 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
