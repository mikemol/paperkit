#!/usr/bin/env python3
"""Μ·sweep·atom (DATA) — module-level structured DATA is mutatable: the Klein four-group completes.

The mutation atom mutates CODE (function bodies → raise; branch arms; condition flips).  A wrong
value in an authored DECISION TABLE (a dict/list literal like a grade ladder or a WCAG scope map) was
STRUCTURALLY un-swept — module-level Assign is never a mutation site.  The data atom adds the two
remaining cells of the group (axis code↔data × drop↔perturb):

  data-:<qn>#<n>  — DROP one key/element of a module-level dict/list/set/tuple literal.  MONOTONE (a
                    reader flips: membership False, or KeyError on bare subscript), feeds the sweep.
  dflip:<qn>#<n>  — PERTURB one value to a valid same-position sibling (grades CORRECTNESS, not
                    identity), else a distinct marker.  NON-monotone, feeds decisions_unasserted.

Three soundness invariants this boundary gates:
  (a) the SWALLOW precondition — a dict read ONLY via `.get(k, DEFAULT)` / `except KeyError` is
      REFUSED (the default hides a dropped key → non-monotone, the DATA analog of branch:'s
      BaseException-enclosure).  ⟨P,F,δ⟩: a bare-subscript/`in` dict IS a site; the same dict read
      via `.get(k, DEFAULT)` is not; δ = the default argument.
  (b) BYTE-MINIMAL drop/perturb — the edit changes ONLY the dropped/perturbed span, not the whole
      literal (an ast.unparse rebuild would reflow the literal and spuriously flip a source-grep
      witness — the source-grep-token-fragility class).
  (c) POSITION-AWARE valid-enum perturb — the counterfactual is a sibling value at the SAME
      structural position (a scope's siblings are other scopes, never the keys or remarks), so a
      dflip: grades whether the check asserts the CORRECT value, not merely a changed identity.

    python3 paperkit/tests/boundaries_data_atom.py     # exit 0 = data is mutatable, soundly
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

    print("Μ·sweep·atom (DATA) — the Klein four-group completes\n")

    SRC = (
        'SCOPE = {"1.1.1": ("full", "why1"), "2.4.2": ("fragment", "why2"), "3.1.1": ("full", "why3")}\n'
        'COLORS = ["red", "green", "blue"]\n'
        'SWALLOWED = {"a": 1, "b": 2}\n'
        'def read_swallowed(k):\n'
        '    return SWALLOWED.get(k, 0)\n'          # .get-with-default → SWALLOWED refused
        'def read_scope(sc):\n'
        '    return SCOPE[sc]\n'                     # bare subscript → SCOPE monotone
    )

    # ── (a) the swallow precondition ─────────────────────────────────────────────────────────────
    names = {s[0] for s in mutate._data_sites(SRC)}
    check("(P) a dict read via bare subscript / membership IS a data site (SCOPE)", "SCOPE" in names)
    check("(P) a list literal IS a data site (COLORS)", "COLORS" in names)
    check("(F) a dict read ONLY via `.get(k, DEFAULT)` is REFUSED (SWALLOWED — the drop would be "
          "swallowed)", "SWALLOWED" not in names)
    # δ: the same dict WITHOUT the default becomes a site.
    NODEF = SRC.replace("SWALLOWED.get(k, 0)", "SWALLOWED[k]")
    check("(δ) removing the `.get` default makes SWALLOWED a site (the default was the swallow)",
          "SWALLOWED" in {s[0] for s in mutate._data_sites(NODEF)})
    # except-KeyError also swallows.
    KEYERR = (
        'D = {"a": 1}\n'
        'def r(k):\n'
        '    try:\n'
        '        return D[k]\n'
        '    except KeyError:\n'
        '        return 0\n'
    )
    check("a dict read under `except KeyError` is REFUSED (the handler swallows the drop)",
          "D" not in {s[0] for s in mutate._data_sites(KEYERR)})

    # ── data-: monotone drop, parseable, byte-minimal ────────────────────────────────────────────
    d = mutate.emit_mutant(SRC, "data-:SCOPE#1")            # drop "2.4.2"
    check("data-: drops one key ('2.4.2' gone, '1.1.1' kept)",
          '"2.4.2"' not in d and '"1.1.1"' in d)
    check("the data-: drop still parses (module importable)", _parses(d))
    # (b) byte-minimal: only the SCOPE line changed.
    orig, dl = SRC.splitlines(), d.splitlines()
    changed = [i for i in range(len(orig)) if i >= len(dl) or orig[i] != dl[i]]
    check("(b) the drop changes ONLY the dropped key's line (byte-minimal, no literal reflow)",
          changed == [0])
    # drop the LAST element — no dangling comma.
    dlast = mutate.emit_mutant(SRC, "data-:COLORS#2")       # drop "blue"
    check("data-: dropping the last element leaves no dangling comma (parseable)",
          _parses(dlast) and '"blue"' not in dlast and '"red"' in dlast)

    # ── (c) dflip: position-aware valid-enum perturb ─────────────────────────────────────────────
    p = mutate.emit_mutant(SRC, "dflip:SCOPE#0")            # perturb 1.1.1's "full"
    check("dflip: perturbs the value to a VALID same-position sibling ('full' → 'fragment'), not a "
          "key or remark",
          ("'fragment'" in p or '"fragment"' in p) and _parses(p))
    check("(c) dflip: does NOT pick a key as the counterfactual (position-aware domain)",
          "('1.1.1'" not in p and "(\"1.1.1\"" not in p)
    # a value with NO finite same-position domain → a distinct marker (grades presence).
    LONE = 'X = {"only": "sole"}\n'
    pl = mutate.emit_mutant(LONE, "dflip:X#0")
    check("dflip: with no sibling domain falls back to a distinct marker (grades presence)",
          "sole" in pl and pl != LONE and _parses(pl))

    # ── Ν·loud on a non-existent site ────────────────────────────────────────────────────────────
    check("Ν·loud on a non-existent data-: site", _raises(SRC, "data-:SCOPE#99"))
    check("Ν·loud on a non-existent dflip: site", _raises(SRC, "dflip:NOPE#0"))

    print()
    if fails:
        print(f"FAIL — {len(fails)} broken: {fails}")
        return 1
    print("ok — structured data is mutatable: data-: monotone (swallow-refused, byte-minimal), "
          "dflip: position-aware valid-enum perturb")
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
