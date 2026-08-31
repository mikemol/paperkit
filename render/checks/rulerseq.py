#!/usr/bin/env python3
r"""Ρ·render·rulerseq — accessible table rules that encode a row-enumeration's binary structure
in the rule PATTERN (WCAG 2.2 SC 1.4.1, Use of Colour), non-parametrically capped nowhere.

In any row enumeration counted in binary — a truth table, a K-map listing, a binary counter, any
lexicographic bit-tuple sweep — the horizontal rule drawn between two adjacent rows can be CHOSEN
BY THE STRUCTURE rather than drawn uniformly.  The rule at row-boundary `i` is governed by the
CYCLE ORDER of that boundary: `cycle_order(i)` = the 2-adic valuation of `i` (its trailing-zero
count) = which bit rolls over there.  Rendered as a self-similar dot/dash (Morse) motif, the
rule's PATTERN — not its colour, not its thickness — carries the counting structure.  So a reader
who cannot perceive colour, or a screen reader over a tagged PDF, still recovers WHICH bit each
boundary flips: a redundant, non-colour structural cue.  No standard tool checks for this.

THE OWNED OBJECT is the ruler sequence itself (2-adic valuation, OEIS A007814) carried into
typography.  The down-column sequence of rule orders for an m-row table IS, by construction, the
binary encoding of the row numbers read as a column — and this holds for ARBITRARY m, not only a
power of two.  `cycle_order(i)` is total on i>=1, so an m that is not 2ⁿ simply gets a faithful
PREFIX of the ruler sequence (every order that has appeared by row m, at its correct multiplicity);
the 2ⁿ case is only where the encoding is COMPLETE (every order 0..n-1 present with full count).
So the capability encodes any unsigned integer's binary structure, not just a full 2ⁿ enumeration.
The render forms — a nicematrix `.tex` reading, an arydshln `md` reading — are two PROJECTIONS of
that one generator, neither hardcoded and NEITHER CAPPED:

  motif family F: order k PREFIXES order k+1  (·, ·--, ·--····, ·--····--------, …),
  len(F(B)) == value(B),  F injective.

This is vendored from mat230's `counting_rules.py` (its `cycle_order`/`emit_f`/`morse_motif`
capture the generator cleanly) but RE-DERIVED FULLY PARAMETRIC: mat230's reified `.tex` form
capped rule-command names at order 7 (`_ORD` word-list), fixed `nicematrix_defs(max_order=5)` and
the dash geometry as magic numbers, and — the load-bearing regression — its `md` fallback carried
only orders 0–2 (a 3-entry dict) and rendered order 3+ as a plain `\hline`, COLLAPSING the
self-similar structure exactly where a 2⁴+ table needs it.  Here the motif family, the rule names,
and both readings generate to arbitrary order, and the `md` reading carries the structure past
order 2 instead of flattening it.

    cycle_order(i)              # 2-adic valuation of the boundary index
    morse_motif(k)              # the order-k self-similar dot/dash motif (the generator)
    rule(i, target="tex"|"md")  # the rule at boundary i, projected to a render form
    nicematrix_defs(n)          # the \Rule<k> custom-line preamble for an n-variable table
"""
from __future__ import annotations

_DOT, _DASH = "·", "-"


def cycle_order(i: int) -> int:
    """Cycle order at row-boundary `i` = trailing-zero count of `i` (its 2-adic valuation): the
    order of the highest-index input that flips at that boundary.  (i=0 is the header rule; callers
    skip it.)  Defined for i>=1; cycle_order(0) is undefined (0 has no lowest set bit).
    """
    if i < 1:
        raise ValueError(f"cycle_order is defined on row-boundaries i>=1; got {i}")
    return (i & -i).bit_length() - 1


def emit_f(bits: list[int], i: int = 0, s: str = _DOT) -> str:
    """F over a binary tuple (LSB-first): ε if i≥n; F(i+1,s) if bit_i=0;
    s^(2^i) ∥ F(i+1, s̄) if bit_i=1.  len(F(B)) == value(B); F injective (the ruler-sequence
    motif family — order k prefixes order k+1).
    """
    if i >= len(bits):
        return ""
    if bits[i] == 0:
        return emit_f(bits, i + 1, s)
    return s * (2 ** i) + emit_f(bits, i + 1, _DASH if s == _DOT else _DOT)


def morse_motif(k: int) -> str:
    """The cycle-order-k motif = F over the all-ones tuple up to bit k — the self-similar family,
    parametric in k with NO cap (mat230 capped the reified names at 7; the generator does not).
    """
    return emit_f([1] * (k + 1))


def _rule_name(k: int) -> str:
    """A nicematrix custom-line command name for cycle order k, generated (not word-listed): the
    Morse motif rendered in TeX-safe letters, so \\RuleXoXX... is unique per order and uncapped
    (· → o, - → X — a bijection into [A-Za-z], the only chars nicematrix accepts in a command).
    """
    return "Rule" + "".join("o" if c == _DOT else "X" for c in morse_motif(k))


def dash_pattern(k: int, dot: float = 0.5, dash: float = 2.2, gap: float = 1.1) -> str:
    """A TikZ dash-pattern spec rendering the order-k Morse motif (· → short-on, - → long-on).
    The geometry (dot/dash/gap lengths in pt) is exposed, not baked.
    """
    return "dash pattern=" + " ".join(
        f"on {dot if c == _DOT else dash}pt off {gap}pt" for c in morse_motif(k))


def nicematrix_defs(n_vars: int, line_width: float = 0.5) -> str:
    """One `\\Rule<k>` nicematrix custom-line per cycle order an n-variable (2ⁿ-row) table uses,
    for the .tex preamble.  An n-variable table has boundaries of orders 0..n-1, so max_order is
    DERIVED from the table (n_vars-1), not a fixed 5 (mat230's cap).
    """
    return "\n".join(
        r"\NiceMatrixOptions{custom-line={command=\\" + _rule_name(k)
        + r", tikz={line width=" + f"{line_width}" + r"pt, " + dash_pattern(k) + r"}}}"
        for k in range(max(n_vars, 1)))


# The `md` reading: an arydshln \hdashline[on/off] whose ON/OFF lengths ENCODE the order — carrying
# the structure to ARBITRARY order (mat230 flattened order 3+ to \hline, losing the encoding).  The
# on-length doubles with the order (mirroring the motif's 2^k self-similar growth), so each order is
# visually distinct and monotone; MathJax-inert, projection-stable.
def _md_dash(k: int) -> str:
    on = 0.5 * (2 ** k)      # order 0 → 0.5pt dots; doubles each order (2-adic self-similarity)
    off = 1.5
    return rf"\hdashline[{on:g}pt/{off:g}pt]"


# The `html`/CSS reading — because ruler-sequence rules are NOT a LaTeX-only thing, they are a thing
# ANY render target that can express a per-row rule pattern can do, and HTML+CSS can: a repeating
# linear gradient painted as the row's bottom border-image carries the exact Morse motif (dot → a
# short opaque segment, dash → a long one), so the same generator drives a CSS reading uncapped.
def _css_stops(k: int, dot: float = 2.0, dash: float = 8.0, gap: float = 4.0) -> str:
    """A CSS repeating-linear-gradient stop list rendering the order-k Morse motif (· → short opaque
    run, - → long opaque run, transparent gaps).  Lengths in px, exposed not baked.
    """
    stops, pos = [], 0.0
    for c in morse_motif(k):
        on = dot if c == _DOT else dash
        stops.append(f"currentColor {pos:g}px {pos + on:g}px")
        pos += on
        stops.append(f"transparent {pos:g}px {pos + gap:g}px")
        pos += gap
    return f"repeating-linear-gradient(90deg, {', '.join(stops)})"


def _css_rule(k: int) -> str:
    """The CSS declarations for a boundary of cycle order k: a bottom border-image painting the
    motif.  The PATTERN (the gradient's run lengths) carries the structure — never colour (it uses
    currentColor) nor thickness.
    """
    return ("border-bottom: 2px solid transparent; "
            f"border-image: {_css_stops(k)} 2; border-image-slice: 2;")


def css_defs(n_orders: int, prefix: str = "rs") -> str:
    """One CSS class `.<prefix>-<k>` per cycle order a table uses, for a <style> block or stylesheet.
    n_orders DERIVED from the table (its max cycle order + 1), not a fixed cap.
    """
    return "\n".join(f".{prefix}-{k} {{ {_css_rule(k)} }}" for k in range(max(n_orders, 1)))


def rule(i: int, target: str = "tex") -> str:
    """The rule at row-boundary `i`.  PATTERN (not thickness/colour) carries the structure
    (WCAG 1.4.1) on EVERY target that affords per-row rules — the capability is target-independent.
    tex → nicematrix `\\Rule<k>` Morse custom-line (infinitely scalable);
    html → a CSS class `.rs-<k>` whose border-image gradient paints the motif;
    md  → arydshln `\\hdashline[on/off]` whose lengths encode the order, uncapped.
    """
    k = cycle_order(i)
    if target == "tex":
        return "\\" + _rule_name(k)
    if target == "html":
        return f"rs-{k}"                 # the CSS class the row's boundary carries
    if target == "md":
        return _md_dash(k)
    raise ValueError(f"unknown target {target!r} (expected 'tex' or 'md')")


def column_encoding(n_rows: int) -> list[int]:
    """The down-column sequence of rule orders for an n_rows table (n_rows a power of two): by
    construction the binary encoding of the row numbers read as a column.  boundaries 1..n_rows-1.
    """
    return [cycle_order(i) for i in range(1, n_rows)]


def main() -> int:
    # ⟨P,F,δ⟩ — the generator and its two uncapped readings.
    ok = 0
    # P: the ruler sequence is correct and F is length-faithful past mat230's order-7 cap.
    #   cycle_order(1..8) = valuations 0,1,0,2,0,1,0,3
    if column_encoding(9) != [0, 1, 0, 2, 0, 1, 0, 3]:
        ok = 1
    #   ARBITRARY m, not just 2ⁿ: an m-row table's encoding is a faithful PREFIX of A007814 — the
    #   generator is total on i>=1, so a non-power-of-two table (here 13 rows) still encodes.
    _A007814 = [cycle_order(i) for i in range(1, 64)]           # the full ruler sequence
    if column_encoding(13) != _A007814[:12]:                    # 13 rows → boundaries 1..12, a prefix
        ok = 1
    #   len(F(B)) == value(B) for every 8-bit tuple (F length-faithful) — well past order 2.
    for v in range(256):
        bits = [(v >> b) & 1 for b in range(8)]
        if len(emit_f(bits)) != v:
            ok = 1
            break
    #   the motif family: order k is a PREFIX of order k+1, to arbitrary depth (order 10 > mat230's 7).
    for k in range(10):
        if not morse_motif(k + 1).startswith(morse_motif(k)):
            ok = 1
            break
    # F (the regression mat230's md form had): order 3+ must STILL carry a distinct structural cue,
    #   never collapse to one undifferentiated rule.  Distinct md dashes for orders 0..5.
    md = [rule(1 << k, "md") for k in range(6)]   # boundaries 1,2,4,8,16,32 → orders 0..5
    if len(set(md)) != 6:                          # all distinct — the encoding survives past order 2
        ok = 1
    # F: the tex rule names are unique per order and uncapped (order 8, past mat230's word-list).
    names = [_rule_name(k) for k in range(9)]
    if len(set(names)) != 9:
        ok = 1
    # TARGET-INDEPENDENCE: the capability is not LaTeX-only — every target that affords per-row rules
    #   carries the SAME order structure.  html (CSS) reads distinct classes per order, and its motif
    #   run-count matches the tex motif (both projections of the one generator).
    if [rule(1 << k, "html") for k in range(6)] != [f"rs-{k}" for k in range(6)]:
        ok = 1
    for k in range(6):
        # the CSS gradient paints one opaque run per motif char — same count as the tex motif
        if _css_stops(k).count("currentColor") != len(morse_motif(k)):
            ok = 1
            break
    if len({css_defs(k + 1) for k in range(6)}) != 6:   # distinct stylesheets per table order-depth
        ok = 1
    # δ: the one cue is the PATTERN (name/dash lengths differ by order), never colour or thickness.
    if ok == 0:
        print("rulerseq: ok — ruler-sequence rules encode binary row structure in the PATTERN, uncapped")
        print("  P: cycle_order = 2-adic valuation; len(F(B))==value(B) (256 tuples); "
              "encodes ARBITRARY m (13 rows, not just 2ⁿ) as a faithful A007814 prefix")
        print("  F: md fallback carries orders 0..5 as DISTINCT rules (mat230 flattened 3+ to \\hline)")
        print("  target-independent: tex (nicematrix), html (CSS border-image), md (arydshln) — three "
              "readings of the ONE generator, not a LaTeX-only feature")
        print("  δ: the cue is the rule PATTERN alone — never colour, never thickness (WCAG 1.4.1)")
        return 0
    print("rulerseq: FAIL — the ruler-sequence encoding or one of its render readings is wrong",
          file=__import__("sys").stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
