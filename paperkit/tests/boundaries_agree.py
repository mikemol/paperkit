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

    ran = []

    def check(desc, cond):
        # Λ·guard-must-not-copy — `ran` COUNTS the arms.  The summary line used to restate a
        # number authored beside the set it describes, and every one of the 26 suites carrying
        # such a line UNDERSTATED it (24 mismatched, none overstated): arms were added and the
        # literal never moved, so it tracked the suite's authoring history rather than its
        # content — and would have read a SHRINKING suite as an unchanged one.
        ran.append(desc)
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Δ·agree behaviors\n")
    check("two producers that concur pass", ag("printf 42 ||| printf 42").passed)
    check("two producers that disagree flag", not ag("printf 42 ||| printf 43").passed)
    check("three producers that all concur pass", ag("printf x ||| printf x ||| printf x").passed)
    check("three producers, one dissenting, flag", not ag("printf x ||| printf x ||| printf y").passed)
    check("a lone producer (no independence) flags", not ag("printf 42").passed)
    check("a producer that FAILS cannot concur", not ag("printf 42 ||| false").passed)
    check("agreement is on OUTPUT, not exit code alone", not ag("printf A ||| printf B").passed)
    # Ζ·tier·agree — a producer output is a whole DOCUMENT, not one line: two byte-identical MULTI-LINE
    # producers must concur (the render `agree:` producers are 19k-byte rendered documents).  This pins
    # BOTH agree implementations — the resolver CLI (here) and the bazel pk_agree/verdict.py path (below)
    # — on full-TEXT equality, not the line-collapse that reds identical multi-line documents.
    check("two identical MULTI-LINE producers concur", ag("printf 'a\\nb\\nc' ||| printf 'a\\nb\\nc'").passed)
    check("multi-line producers differing on one line flag", not ag("printf 'a\\nb\\nc' ||| printf 'a\\nX\\nc'").passed)

    # The bazel path is a SECOND implementation (tools/verdict.py agree) — gate it directly on the same
    # multi-line property, so the two agree oracles cannot diverge (they did: the CLI compared full text
    # while verdict.py collapsed to distinct LINES and red two identical multi-line documents).
    import subprocess, tempfile, json
    VER = str(ENG.parent / "tools" / "verdict.py")
    def vagree(*texts):
        with tempfile.TemporaryDirectory() as d:
            ps = []
            for i, t in enumerate(texts):
                p = f"{d}/p{i}"
                open(p, "w").write(t)
                ps.append(p)
            out = f"{d}/v.json"
            subprocess.run(["python3", VER, "agree", "agree", out, *ps], check=True)
            return json.load(open(out))["verdict"] == "pass"
    check("verdict.py agree: identical multi-line texts concur", vagree("a\nb\nc\n", "a\nb\nc\n"))
    check("verdict.py agree: differing multi-line texts flag", not vagree("a\nb\nc\n", "a\nX\nc\n"))
    check("verdict.py agree: a __FAIL__ producer flags", not vagree("__FAIL__\n", "__FAIL__\n"))

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    P, F = ag("printf 42 ||| printf 42"), ag("printf 42 ||| printf 43")
    ok = P.passed and not F.passed
    fails.append("one-byte-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}one byte of disagreement flips concurrence to dissent")
    print("      P (pass side): printf 42 ||| printf 42  — identical output, producers concur")
    print("      F (flag side): printf 42 ||| printf 43  — one digit differs")
    print("      δ (min delta): a single byte in one producer's output\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    bad = len([b for b in ran if not b])
    if bad:
        print(f"BOUNDARIES: FAIL ({bad} of {len(ran)} behaviors drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
