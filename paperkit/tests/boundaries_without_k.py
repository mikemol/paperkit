#!/usr/bin/env python3
"""Behavioral-boundary examples for the gate's --without-K proof-relevance mode.

⟨P, F, δ⟩ per the boundary practice.  --without-K drops the gate's proof-irrelevance
(Axiom K / UIP): it forbids identifying distinct cited claims that share one witness,
so every cited claim must carry a DISTINCT check.  Opt-in, like agda --without-K —
this boundary test runs in CI; `gate --without-K` on the real documents does not
(both still lean on shared witnesses, the honest diagnostic this mode surfaces).

    python3 paperkit/tests/boundaries_without_k.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture import entry, gate  # noqa: E402

# Two cited claims; DISTINCT witnesses vs a SHARED one (both files exist in the proj).
DISTINCT = [entry("a", claim="alpha", check="file:w.bib"),
            entry("b", claim="beta", check="file:r.tsv", frm="a")]
SHARED = [entry("a", claim="alpha", check="file:w.bib"),
          entry("b", claim="beta", check="file:w.bib", frm="a")]
SINGLE = [entry("a", claim="alpha", check="file:w.bib")]


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("--without-K behaviors\n")
    check("distinct witnesses pass --without-K", gate(DISTINCT, "--without-K")[0] == 0)
    check("shared witness fails --without-K", gate(SHARED, "--without-K")[0] == 1)
    check("shared witness passes by DEFAULT (Axiom K is the default)", gate(SHARED)[0] == 0)
    check("a lone cited claim is trivially distinct", gate(SINGLE, "--without-K")[0] == 0)
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("witness distinctness (--without-K verdict)",
         "the second claim's check (file:r.tsv → file:w.bib)",
         "distinct → exit 0", gate(DISTINCT, "--without-K")[0] == 0,
         "shared   → exit 1", gate(SHARED, "--without-K")[0] == 1),
        ("--without-K is opt-in (same shared-witness document)",
         "the --without-K flag",
         "default      → exit 0", gate(SHARED)[0] == 0,
         "--without-K  → exit 1", gate(SHARED, "--without-K")[0] == 1),
    ]
    for name, axis, p_lbl, p_ok, f_lbl, f_ok in pairs:
        ok = p_ok and f_ok
        fails.append(name) if not ok else None
        print(f"  {'ok ' if ok else 'XX '}{name}")
        print(f"      P (pass side): {p_lbl}")
        print(f"      F (flag side): {f_lbl}")
        print(f"      δ (min delta): {axis}\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (4 behaviors, 2 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
