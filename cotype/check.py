#!/usr/bin/env python3
"""cotype-monotone — the cotype's own gate (Σ·cotype step 2): ledger entries never VANISH.

The declared contract (cotype/README.md): append-only, retirement-logged.  Its constructible
form is ENTRY-KEY monotonicity — the unit is the entry (a `- **key** …` bullet), not the line,
because the sanctioned moves all preserve the key:
  * add an entry            → a new key appears (fine)
  * change status in place  → the key persists, the line changes (fine)
  * retire with RETIRED:    → "the entry stays, the reason is logged" — the key persists (fine)
  * DELETE an entry         → its key vanishes — the one forbidden move, caught here.

A commit-DELTA property: its truth-maker is HEAD's ledger vs the staged one, which only the
pre-commit can see (the hermetic //:hook sandbox has no git history) — so this gate lives
beside the ONE bazel target in .githooks/pre-commit, invoked as a real tool (never an inline
script).  Coverage bound, stated honestly: `git commit --no-verify` skips it, as it skips all
local CI.

Every run also proves its own ⟨P,F,δ⟩ on in-memory mutated copies (never the tree):
  P = the real old⊆new comparison;  F = the first entry dropped from a copy → CAUGHT;
  δ = one entry bullet.

    python3 cotype/check.py <old-ledger> <new-ledger>     # exit 0 = monotone
"""
import re
import sys
from pathlib import Path

# An entry is a `- **key** …` bullet (top-level or a thread sub-bullet).  The KEY is the first
# whitespace-delimited token of the bold text — status glyphs (✅ …) and bracketed status live
# OUTSIDE the key, so a status flip never reads as a deletion.
_ENTRY = re.compile(r"^\s*- \*\*([^*\s]+)", re.M)


def keys(text):
    return set(_ENTRY.findall(text))


def missing(old_text, new_text):
    return sorted(keys(old_text) - keys(new_text))


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    old, new = Path(argv[1]).read_text(), Path(argv[2]).read_text()

    gone = missing(old, new)
    if gone:
        print("cotype-monotone: FAIL — ledger entries VANISHED (append-only, retirement-logged: "
              "an entry is retired with a RETIRED: note and STAYS; it is never deleted):", file=sys.stderr)
        for k in gone:
            print(f"  - **{k}**", file=sys.stderr)
        return 1

    # ⟨P,F,δ⟩ self-proof on in-memory copies (Λ·probe-isolation — never the tree): dropping one
    # entry from a copy of the OLD ledger must be caught against the old itself.
    m = _ENTRY.search(old)
    if m:
        dropped = old.replace(m.group(0), "- (entry deleted)", 1)
        if not missing(old, dropped):
            print("cotype-monotone: SELF-PROOF FAIL — deleting an entry from a copy went "
                  "uncaught; the gate is unsound, refusing to pass.", file=sys.stderr)
            return 1

    print(f"cotype-monotone: OK ({len(keys(new))} entries, {len(keys(new) - keys(old))} new; "
          "F-arm: one dropped entry is caught)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
