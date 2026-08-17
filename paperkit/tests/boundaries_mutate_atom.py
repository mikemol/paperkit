#!/usr/bin/env python3
"""Μ·sweep·atom — the finer mutation atom (branch:/flip:) is MONOTONE and ADDITIVE by construction.

The def-sweep's atom drops a whole def BODY → an uncatchable `raise BaseException` (monotone: no
`except Exception` swallows it).  Μ·sweep·atom adds a FINER, still-monotone `branch:<qn>#<n>` (drop
one arm's body → the same raise) and a NON-monotone `flip:<qn>#<n>` (invert one condition).  Two
soundness invariants this boundary gates, both against the false-green the raise-monotone atom exists
to prevent:

  (a) PRECONDITION — a branch arm inside a region a `except BaseException` / bare `except:` handler
      would CATCH is REFUSED: a raise planted there is swallowed → the arm reads non-flip → a
      reached-but-unfalsifiable arm graded covered (false-green).  ⟨P,F,δ⟩: the arm is a site OUTSIDE
      such a handler, is NOT a site inside one, and adding/removing the handler flips membership.
  (b) ADDITIVE, not replacement — def: dispatch is byte-identical to before Μ·sweep·atom (the bare
      qualname and `def:<qn>` paths are unchanged), so def: grid cells keep their labels (cache hits,
      no cold regrade) and the coarse behavioral grade survives.  branch: is a NEW spec string,
      appended, never a replacement.

    python3 paperkit/tests/boundaries_mutate_atom.py     # exit 0 = the atom is monotone + additive
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))

import mutate  # noqa: E402


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Μ·sweep·atom — monotone finer atom, additive to def:\n")

    # ── (a) the BaseException-enclosure precondition ─────────────────────────────────────────────
    # The constructed counterexample: an arm inside a `try` body a BaseException handler catches.  A
    # `raise BaseException` there is SWALLOWED (verified by execution below), so it must never be a
    # branch: site.  The SAME arm outside the handler MUST be a site.  δ = the enclosing handler.
    SAFE = (
        "def f(x):\n"
        "    if x:\n"
        "        return work()\n"
    )
    REFUSED = (
        "def f(x):\n"
        "    try:\n"
        "        if x:\n"
        "            return work()\n"     # the protected arm — swallowed if mutated
        "    except BaseException:\n"
        "        return fallback()\n"
    )
    NARROW = (
        "def f(x):\n"
        "    try:\n"
        "        if x:\n"
        "            return work()\n"     # only `except Exception` — BaseException ESCAPES it
        "    except Exception:\n"
        "        return None\n"
    )
    BARE = (
        "def f(x):\n"
        "    try:\n"
        "        return work()\n"         # bare `except:` catches BaseException too — refused
        "    except:\n"
        "        return None\n"
    )

    def reaches_arm(src):
        """The if-then arm `return work()` is a branch: site iff its exact line is enumerated."""
        want = "        return work()" if src is SAFE else "            return work()"
        for _, _, (b0, bl) in mutate._branch_sites(src):
            if src.splitlines()[b0.lineno - 1] == want and b0.lineno == bl.end_lineno:
                return True
        return False

    # Ground truth: prove the swallowing the precondition guards against actually happens.
    ns: dict = {}
    exec("def g():\n"
         "    try:\n"
         "        raise BaseException('MUT')\n"
         "    except BaseException:\n"
         "        return 'swallowed'\n"
         "    return 'end'\n", ns)
    check("a raise in a BaseException-caught region IS swallowed (the hazard is real)",
          ns["g"]() == "swallowed")

    check("(P) the if-then arm outside any handler IS a branch: site", reaches_arm(SAFE))
    check("(F) the same arm inside `except BaseException` is REFUSED", not reaches_arm(REFUSED))
    # BARE's protected try-body is `return work()` at line 3; a bare `except:` catches BaseException,
    # so that line must NOT be a branch: site (only the handler body at line 5 is safe to mutate).
    check("(F) the protected body under a bare `except:` is REFUSED",
          all(b0.lineno != 3 for _, _, (b0, _bl) in mutate._branch_sites(BARE)))
    check("(δ) `except Exception` does NOT refuse it (BaseException escapes Exception)",
          reaches_arm(NARROW))

    # ── (b) additive: def: dispatch byte-identical, branch: is a new appended spec ────────────────
    SRC = (
        "def classify(x):\n"
        "    if x > 0:\n"
        "        return 'pos'\n"
        "    else:\n"
        "        return 'neg'\n"
    )
    check("(b) `def:classify` == bare `classify` (legacy dispatch unchanged, byte-identical)",
          mutate.emit_mutant(SRC, "def:classify") == mutate.emit_mutant(SRC, "classify"))
    check("(b) the ∅ identity is byte-identical to the source",
          mutate.emit_mutant(SRC, "") == SRC)
    branch = mutate.emit_mutant(SRC, "branch:classify#0")
    check("branch: drops one arm's body → the SAME uncatchable raise (monotone)",
          "raise BaseException('PAPERKIT_MUT')" in branch and branch != SRC)
    check("the branch: mutant still parses (module stays importable — a witness flips only if it "
          "reaches the arm)",
          _parses(branch))
    # def: is UNTOUCHED by the branch: mutation — a coarse cell survives alongside the finer one.
    check("(b) `def:classify` and `branch:classify#0` are DISTINCT mutants (additive, not a "
          "replacement)",
          mutate.emit_mutant(SRC, "def:classify") != branch)

    # ── flip: is a distinct, NON-monotone op (a value inversion, never a raise) ───────────────────
    flip = mutate.emit_mutant(SRC, "flip:classify#0")
    check("flip: inverts the condition (`x > 0` → `not (x > 0)`), never a raise",
          "not (x > 0)" in flip and "raise BaseException" not in flip.replace(SRC, ""))
    check("the flip: mutant still parses", _parses(flip))

    # ── Ν·loud: a spec that names no such site raises, never a silent no-op ───────────────────────
    check("Ν·loud on a non-existent branch: site", _raises(SRC, "branch:classify#99"))
    check("Ν·loud on a non-existent flip: site", _raises(SRC, "flip:nope#0"))

    print()
    if fails:
        print(f"FAIL — {len(fails)} broken: {fails}")
        return 1
    print("ok — Μ·sweep·atom is monotone (BaseException-enclosure refused) and additive (def: "
          "byte-identical, branch: appended)")
    return 0


def _parses(text: str) -> bool:
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False


def _raises(src: str, spec: str) -> bool:
    try:
        mutate.emit_mutant(src, spec)
        return False
    except KeyError:
        return True


if __name__ == "__main__":
    raise SystemExit(main())
