"""Ζ·hook·index — the worktree≡index precondition's boundary (the PURE core, gated).

The hook-layer half (tools/hook_index.py main(): the live `git status` + the refusal) cannot
run in the hermetic //:hook sandbox (no git) — like cotype-monotone it lives in the
pre-commit.  Its PURE core CAN be gated here: `divergent(porcelain, allow)` decides, from a
porcelain -z transcript alone, which paths make the worktree verdict differ from the index
verdict.  ⟨P,F,δ⟩ over porcelain fixtures: staged-only changes are equivalence-preserving;
one unstaged edit or one untracked file breaks it; the allowlist admits only the
ownership-justified prefix; a rename entry's two-field encoding parses (the NEW path is what
lands).

⚑ Φ·fixture·suite — `tools` IS NAMED, NOT INJECTED.  This opened with
`sys.path.insert(0, ROOT / "tools")` and a flat `from hook_index import …`.  `pyproject.toml`
claimed the editable install already covered `tools`; measured, it did not — the package resolved
by CWD and nowhere else, so mypy could not follow this edge from any file it checked out of tree.
Declaring `tools` in `packages` made the claim true and the insert unnecessary.

⚑⚑ AND THE SUMMARY MOVED TO THE SHARED RECORDER.  This suite had already fixed HALF the
counting defect by hand — `ran` and `deltas` accumulators feeding the tail — after mutation
proved the old literal "10 behaviors, 1 delta" could not fail however the suite changed.  The
per-file accumulator was the right idea and the wrong owner: `_boundary.Suite` is where it lives
for all 43 suites, so no file has a number to type.

    python3 paperkit/tests/boundaries_hook_index.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# ⚑ Ζ·engine·reach — the bib spells bare `python3`, which has no virtualenv and therefore no
# editable install.  Appending the repo root makes `paperkit` and `tools` importable as
# DIRECTORIES.  APPEND, not insert: it adds a namespace rather than shadowing one.
sys.path.append(str(Path(__file__).resolve().parents[2]))

from paperkit.tests._boundary import Suite
from tools.indexdiverge import ALLOW, divergent


def main() -> int:
    """Assert the pure worktree≡index core decides divergence from a porcelain transcript."""
    s = Suite("HOOK-INDEX", "Ζ·hook·index — worktree≡index, the pure core")

    s.check("a clean tree diverges nowhere", divergent("") == [])
    s.check("a fully-STAGED change is equivalence-preserving (M in the index column only)",
            divergent("M  paperkit/gate.py\0") == [])
    s.check("an UNSTAGED edit diverges (the worktree column is live)",
            divergent(" M paperkit/gate.py\0") == ["paperkit/gate.py"])
    s.check("a staged-then-re-edited file diverges (MM — the commit lands the FIRST version)",
            divergent("MM paperkit/gate.py\0") == ["paperkit/gate.py"])
    s.check("an untracked file diverges (?? — referenced-but-never-added is the whole hole)",
            divergent("?? paperkit/new.py\0") == ["paperkit/new.py"])
    s.check("a staged RENAME is equivalence-preserving and its origin field is consumed",
            divergent("R  paperkit/new.py\0paperkit/old.py\0") == [])
    s.check("a rename re-edited in the worktree diverges, naming the NEW path (what lands)",
            divergent("RM paperkit/new.py\0paperkit/old.py\0") == ["paperkit/new.py"])
    s.check("the allowlist admits its prefix (ownership-justified: bazel-invisible + index-gated)",
            divergent(" M cotype/ledger.md\0?? cotype/notes.md\0") == [])
    s.check("the allowlist is a PREFIX, not a grep (cotype2/ is not cotype/)",
            divergent(" M cotype2/x.md\0") == ["cotype2/x.md"])
    s.check(f"the allowlist is the declared owned set: {ALLOW}", ALLOW == ("cotype/",))

    s.section("P, F, δ minimum-delta pair")
    s.delta("one worktree-column bit flips the verdict",
            divergent("M  paperkit/grade.py\0") == [],
            divergent("MM paperkit/grade.py\0") == ["paperkit/grade.py"],
            p="M  → worktree ≡ index; the hook's verdict is the commit's",
            f="MM → the hook would gate bytes the commit does not land",
            d="one unstaged edit to one staged file")
    return s.finish()


if __name__ == "__main__":
    raise SystemExit(main())
