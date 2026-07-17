#!/usr/bin/env python3
r"""numfmt.py — ISO 80000-1 §7.3 / NIST SP 811 digit grouping (an opt-in render helper).

STANDARD (ISO 80000-1 §7.3, restated NIST SP 811): an integer with MORE THAN FOUR digits has
its digits grouped in threes counting FROM THE RIGHT, groups separated by a THIN SPACE — LaTeX
`\,` — never a comma or a period.  An integer of exactly four digits (or fewer) is left
ungrouped.

RENDER-ONLY, EXACT.  This operates on the exact decimal string (`str(x)`, no float, no
`limit_denominator`, no int round-trip beyond str()), so an arbitrarily long exact answer keeps
every digit — `ungroup(group_digits(n)) == str(n)` for every int.  Keep bare ints as the source
of truth; grouping happens only where a number is EMITTED to LaTeX / markdown math.

  group_digits(3628800)                    -> r"3\,628\,800"
  group_digits(20736)                      -> r"20\,736"
  group_digits(3125)                       -> "3125"          (four digits: untouched)
  group_digits(5**125)                     -> r"2\,350\,988\,…\,125"   (many groups)
  group_digits(3628800, allowbreak=True)   -> r"3\,\allowbreak 628\,\allowbreak 800"

`allowbreak=True` inserts `\allowbreak` after each thin space so a very long numeral may WRAP
inside inline math in real LaTeX.  MathJax / pandoc math do NOT support the `\allowbreak`
primitive, so a MARKDOWN emit path should use `allowbreak=False` — a plain `\,` thin space,
which MathJax renders.

OPT-IN: this is a standalone helper, not wired into the projector's `clean()` (a deliberately
minimal common floor).  Import it where a project chooses to group emitted integers.
"""
from __future__ import annotations

_THIN = r"\,"
_THIN_BREAK = r"\,\allowbreak "


def group_digits(x: object, allowbreak: bool = False) -> str:
    r"""Group the digits of an integer (or its exact decimal string) per ISO 80000-1 §7.3.

    A leading '+'/'-' sign is preserved.  Numbers with ≤4 digits are returned unchanged.
    """
    s = str(x)
    sign = ""
    if s[:1] in ("+", "-"):
        sign, s = s[0], s[1:]
    if not s.isdigit():
        raise ValueError(f"group_digits: not a decimal integer: {x!r}")
    if len(s) <= 4:                       # ≤4 digits: ungrouped, per the standard's threshold
        return sign + s
    head = len(s) % 3 or 3                # 1..3 leading digits, then exact groups of three
    groups = [s[:head]] + [s[i:i + 3] for i in range(head, len(s), 3)]
    sep = _THIN_BREAK if allowbreak else _THIN
    return sign + sep.join(groups)


def ungroup(s: str) -> str:
    r"""Inverse used by the exactness gate: strip every `\allowbreak`, thin space `\,`, and
    ASCII space, recovering the bare sign+digits.  ungroup(group_digits(n, …)) == str(n)."""
    return s.replace(r"\allowbreak", "").replace(r"\,", "").replace(" ", "")


if __name__ == "__main__":
    # self-test: exactness recovery on a spread of magnitudes incl. a very long integer.
    import sys
    cases = [0, 7, 495, 3125, 20736, 1814400, 3628800, 93963542400, 5 ** 125, -1814400]
    bad = 0
    for n in cases:
        for ab in (False, True):
            g = group_digits(n, allowbreak=ab)
            if ungroup(g) != str(n):
                print(f"  ✗ ungroup(group_digits({n}, allowbreak={ab})) = {ungroup(g)!r} ≠ {n}")
                bad = 1
    # threshold: exactly-4-digit numbers stay bare; 5-digit gets one thin space
    assert group_digits(3125) == "3125"
    assert group_digits(20736) == r"20\,736"
    assert group_digits(3628800) == r"3\,628\,800"
    print("numfmt self-test:", "FAIL" if bad else "PASS")
    sys.exit(bad)
