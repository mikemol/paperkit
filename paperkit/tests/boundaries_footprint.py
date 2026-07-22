#!/usr/bin/env python3
"""Behavioral-boundary examples for Φ·footprint — resolver.footprint (the READ footprint).

⟨P, F, δ⟩ per the boundary practice.  footprint(check) is the set of project files the
check OPENS for reading when it runs (traced with strace) — the SOUND key a footprint
cache invalidates on: a check is a pure function of its inputs, so a diff touching none
of its footprint cannot change its verdict.  Bounds:
  - file: opens only its target; a tool reads exactly the files it touches.
  - reads ⊇ Δ's sensitivity `tests` — a corruption-blind check READS inputs that no single
    mutation FLIPS, so only the read footprint is safe to cache on.  That gap is the point.

    python3 paperkit/tests/boundaries_footprint.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import resolver  # noqa: E402  (footprint lives in the resolver core — small blast radius, no gate loop)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture_delta import discriminate  # noqa: E402
from _fixture_model import entry  # noqa: E402


def fp(check):
    # the read footprint of a check, in a dir shipping a.txt and b.txt
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "a.txt").write_text("FOO\n")
        (p / "b.txt").write_text("BAR\n")
        (p / "w.bib").write_text("x\n")
        return resolver.footprint(check, p, {})


def sens(check):
    # Δ's sensitivity `tests` for the same check, over a fixture shipping a.txt
    _, out = discriminate([entry("w", claim="c", check=check)], "--all", "--json",
                          assets={"a.txt": "FOO\n"})
    return json.loads(out)[0].get("tests", [])


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Φ·footprint behaviors\n")
    check("file: footprint is exactly its target", fp("file:w.bib") == ["w.bib"])
    check("cmd: footprint is the file the tool reads", fp("cmd:grep -q ZZZ a.txt") == ["a.txt"])
    check("a check reading nothing under the project has an empty footprint", fp("cmd:true") == [])

    # a check OPENS directories too (python imports scandir; ls opens the dir) — only
    # regular files are hashable cache inputs, so directories are excluded.  (The case the
    # footprint-cache consumer surfaced: hashing a directory path raised IsADirectoryError.)
    with tempfile.TemporaryDirectory() as dd:
        pp = Path(dd)
        (pp / "sub").mkdir()
        (pp / "sub" / "x.txt").write_text("y\n")
        dir_fp = resolver.footprint("cmd:ls sub", pp, {})
    check("a directory a check opens is NOT in the footprint (regular files only)", dir_fp == [])

    print("\n⟨P, F, δ⟩ minimum-delta pairs\n")
    p1, f1 = fp("cmd:grep -q ZZZ a.txt"), fp("cmd:grep -q ZZZ a.txt b.txt")
    ok1 = p1 == ["a.txt"] and f1 == ["a.txt", "b.txt"]
    fails.append("read-one-more") if not ok1 else None
    print(f"  {'ok ' if ok1 else 'XX '}footprint grows by exactly the file the check reads")
    print(f"      P (pass side): {p1}")
    print(f"      F (flag side): {f1}")
    print("      δ (min delta): the check greps one more file (b.txt)\n")

    # the keystone delta: read footprint ⊋ sensitivity — sound to cache on where `tests` is not
    blind = "cmd:cat a.txt >/dev/null 2>&1; true"   # READS a.txt; always exits 0 (corruption-blind)
    fblind, sblind = fp(blind), sens(blind)
    ok2 = fblind == ["a.txt"] and "a.txt" not in sblind
    fails.append("reads-superset-sensitivity") if not ok2 else None
    print(f"  {'ok ' if ok2 else 'XX '}read footprint ⊋ Δ sensitivity (the gap that makes reads the sound cache key)")
    print(f"      P (footprint):   {fblind}  — the check READS a.txt")
    print(f"      F (sensitivity): {sblind}  — no single corruption FLIPS it (corruption-blind)")
    print("      δ (min delta): a check can read an input that its sensitivity set misses\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (4 behaviors, 2 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
