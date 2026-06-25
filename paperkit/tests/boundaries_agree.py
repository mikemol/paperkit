#!/usr/bin/env python3
"""Behavioral-boundary examples for Δ·agree — the agree: resolver verb (Ε·agree).

⟨P, F, δ⟩ per the boundary practice.  agree:<p1> ||| <p2> ... resolves green iff ≥2
INDEPENDENT producers ALL exit 0 and emit IDENTICAL output — the same fact corroborated
across implementations, ruling out a shared bug a single check cannot catch.  Bounds:
  - P: producers that concur pass; F: a single byte of disagreement flags.
  - independence is required: a lone producer, or one that fails, cannot concur.

    python3 paperkit/tests/boundaries_agree.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import resolver  # noqa: E402  (the agree verb lives in the resolver core — small blast radius)

ENG = Path(resolver.__file__).resolve().parent


def ag(target):
    return resolver.resolves(f"agree:{target}", ENG, {})


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Δ·agree behaviors\n")
    check("two producers that concur pass", ag("printf 42 ||| printf 42") is True)
    check("two producers that disagree flag", ag("printf 42 ||| printf 43") is False)
    check("three producers that all concur pass", ag("printf x ||| printf x ||| printf x") is True)
    check("three producers, one dissenting, flag", ag("printf x ||| printf x ||| printf y") is False)
    check("a lone producer (no independence) flags", ag("printf 42") is False)
    check("a producer that FAILS cannot concur", ag("printf 42 ||| false") is False)
    check("agreement is on OUTPUT, not exit code alone", ag("printf A ||| printf B") is False)

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    P, F = ag("printf 42 ||| printf 42"), ag("printf 42 ||| printf 43")
    ok = P is True and F is False
    fails.append("one-byte-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}one byte of disagreement flips concurrence to dissent")
    print("      P (pass side): printf 42 ||| printf 42  — identical output, producers concur")
    print("      F (flag side): printf 42 ||| printf 43  — one digit differs")
    print("      δ (min delta): a single byte in one producer's output\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (7 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
