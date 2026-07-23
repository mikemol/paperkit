#!/usr/bin/env python3
"""Ζ·hook·index — the worktree≡index precondition's boundary (the PURE core, gated).

The hook-layer half (tools/hook_index.py main(): the live `git status` + the refusal) cannot
run in the hermetic //:hook sandbox (no git) — like cotype-monotone it lives in the
pre-commit.  Its PURE core CAN be gated here: `divergent(porcelain, allow)` decides, from a
porcelain -z transcript alone, which paths make the worktree verdict differ from the index
verdict.  ⟨P,F,δ⟩ over porcelain fixtures: staged-only changes are equivalence-preserving;
one unstaged edit or one untracked file breaks it; the allowlist admits only the
ownership-justified prefix; a rename entry's two-field encoding parses (the NEW path is what
lands).

    python3 paperkit/tests/boundaries_hook_index.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from hook_index import ALLOW, divergent  # noqa: E402  (the owner of the equivalence predicate)


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Ζ·hook·index — worktree≡index, the pure core\n")
    check("a clean tree diverges nowhere", divergent("") == [])
    check("a fully-STAGED change is equivalence-preserving (M in the index column only)",
          divergent("M  paperkit/gate.py\0") == [])
    check("an UNSTAGED edit diverges (the worktree column is live)",
          divergent(" M paperkit/gate.py\0") == ["paperkit/gate.py"])
    check("a staged-then-re-edited file diverges (MM — the commit lands the FIRST version)",
          divergent("MM paperkit/gate.py\0") == ["paperkit/gate.py"])
    check("an untracked file diverges (?? — referenced-but-never-added is the whole hole: no globs)",
          divergent("?? paperkit/new.py\0") == ["paperkit/new.py"])
    check("a staged RENAME is equivalence-preserving and its origin field is consumed",
          divergent("R  paperkit/new.py\0paperkit/old.py\0") == [])
    check("a rename re-edited in the worktree diverges, naming the NEW path (what lands)",
          divergent("RM paperkit/new.py\0paperkit/old.py\0") == ["paperkit/new.py"])
    check("the allowlist admits its prefix (ownership-justified: bazel-invisible + index-gated)",
          divergent(" M cotype/ledger.md\0?? cotype/notes.md\0") == [])
    check("the allowlist is a PREFIX, not a grep (cotype2/ is not cotype/)",
          divergent(" M cotype2/x.md\0") == ["cotype2/x.md"])
    check(f"the allowlist is the declared owned set: {ALLOW}", ALLOW == ("cotype/",))

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    p = divergent("M  paperkit/grade.py\0")
    f = divergent("MM paperkit/grade.py\0")
    ok = p == [] and f == ["paperkit/grade.py"]
    fails.append("index-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}one worktree-column bit flips the verdict")
    print("      P (staged):    M  → worktree ≡ index; the hook's verdict is the commit's")
    print("      F (re-edited): MM → the hook would gate bytes the commit does not land")
    print("      δ (min delta): one unstaged edit to one staged file\n")

    if fails:
        print(f"HOOK-INDEX: FAIL ({len(fails)} drifted)")
        return 1
    print("HOOK-INDEX: PASS (10 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
