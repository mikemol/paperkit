#!/usr/bin/env python3
"""Ρ·bnd-env-facts — the STANDING FIGURES this repo's prose quotes, re-derived from their owners.

⚑ WHY THIS EXISTS: FOUR OF FIVE WENT STALE UNNOTICED.  A tick-40 audit of the leverage ledger's
Environment section — the block every tick reads FIRST, before measuring anything — found:

  · "nine hook-set projects"      → TEN declare a root; MODULE.bazel wires THIRTEEN
  · "110 claims" in paper/        → 115
  · "exceeds 600s"                → exceeds 2700s, and mis-attributed to nine projects when
                                    `render` alone is the cost (Β-F3)
  · "~61s" for a Δ sweep          → that is a COLD sweep; a WARM one is ~0.1s

Three of those are COUNTS with a single owner in the tree, so they are re-derivable and belong in
a gate rather than in prose. This is `fresh-comments-are-hypotheses-too` applied to the numbers
rather than the sentences: a figure nothing re-derives is a claim nobody is checking, and this
repo's whole thesis is that such claims rot silently.

⚑ WHAT THIS DOES NOT DO.  It does not gate the ledger's PROSE — that is a working log, not a
projection, and claim-ifying 3,659 lines of narrative would be Λ-F1's error (measuring 316 words
against 27 KB). It gates the FIGURES, which is the part that actually drifted.

⚑ IT ALSO DOES NOT PIN THE NUMBERS.  A count that must never change is a different (and usually
wrong) claim. This asserts that the numbers the PROSE quotes MATCH what the tree says — so when a
project is added the gate reds, the prose is corrected, and the gate goes green again. The red is
the notification, not the verdict.
"""
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "cotype" / "leverage-ledger.md"


def wired_projects() -> int:
    return len(re.findall(r'bib\.project\(\s*name\s*=\s*"[^"]+"',
                          (ROOT / "MODULE.bazel").read_text()))


def rooted_projects() -> list:
    out = []
    for toml in sorted(ROOT.rglob("paper.toml")):
        if ".git" in toml.parts or "build" in toml.parts:
            continue
        try:
            p = tomllib.loads(toml.read_text()).get("paper", {})
        except Exception:                                    # noqa: BLE001
            continue
        if "root" in p:
            out.append(str(toml.parent.relative_to(ROOT)))
    return out


def paper_entries() -> int:
    cfg = tomllib.loads((ROOT / "paper" / "paper.toml").read_text())["paper"]
    return sum(len(re.findall(r"^@\w+\{", (ROOT / "paper" / b).read_text(), re.M))
               for b in cfg["warrants"])


def main() -> int:
    print("Ρ·bnd-env-facts — the standing figures, re-derived from their owners\n")
    bad = 0

    print("⟨each figure has ONE owner in the tree⟩\n")
    wired = wired_projects()
    rooted = rooted_projects()
    claims = paper_entries()
    print(f"  ok MODULE.bazel wires        {wired:>4} project(s)")
    print(f"  ok projects declaring a root {len(rooted):>4}  ({', '.join(rooted)})")
    print(f"  ok paper/ holds              {claims:>4} bib entries")

    if not LEDGER.exists():
        print("\n  ok the ledger is absent — nothing quotes these figures here", file=sys.stderr)
        return 0

    text = LEDGER.read_text()

    print("\n⟨the ledger's Environment section quotes them CORRECTLY⟩\n")
    # Only the Environment block: the tick log is an APPEND-ONLY history whose old rows are
    # SUPPOSED to record what was true then (rule 6), so scanning the whole file would red on
    # correct history.  This is the distinction between a stale FACT and a dated RECORD.
    m = re.search(r"^## Environment$(.*?)^## ", text, re.M | re.S)
    if not m:
        print("  XX no Environment section found — this witness cannot check what it exists for",
              file=sys.stderr)
        return 1
    env = m.group(1)

    for label, value, pattern in (
            # ⚑ `\s+`, NOT a space: markdown prose WRAPS, and "wires 13\n    projects" is the same
            # sentence.  The first version required them adjacent and reported the statement
            # MISSING — accusing the prose of a defect that was the pattern's blind spot, which is
            # Μ-F3's shape (a scan window guessing at layout instead of reading structure).
            ("wired projects", wired, r"wires (\d+)\s+projects"),
            ("root-declaring projects", len(rooted), r"\*\*(\w+)\*\* declare a root"),
            ("paper/ entries", claims, r"\*\*(\d+) entries\*\*")):
        found = re.search(pattern, env)
        if not found:
            print(f"  XX the Environment section no longer states the {label} — it was corrected "
                  f"at tick 40 and the statement has been removed or reworded", file=sys.stderr)
            bad += 1
            continue
        raw = found.group(1)
        words = {"TEN": 10, "NINE": 9, "ELEVEN": 11, "TWELVE": 12, "THIRTEEN": 13}
        got = words.get(raw.upper(), None) if not raw.isdigit() else int(raw)
        if got == value:
            print(f"  ok {label}: prose says {raw}, tree says {value}")
        else:
            print(f"  XX {label}: the prose says {raw!r}, the tree says {value} — correct the "
                  f"Environment section (this red IS the notification)", file=sys.stderr)
            bad += 1

    print("\n⟨P, F, δ⟩\n")
    print("      P: every figure the Environment block quotes equals what its owner reports")
    print("      F: a project is wired, or a claim added, and the prose keeps the old number")
    print("      δ (min delta): one bib.project tag, or one bib entry")

    if bad:
        print(f"\nbnd-env-facts: {bad} figure(s) DRIFTED. Four of five went stale unnoticed before "
              f"this gate existed; the repair is to correct the prose, never to relax the check.",
              file=sys.stderr)
        return 1
    print("\nBOUNDARIES: PASS (3 standing figures, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
