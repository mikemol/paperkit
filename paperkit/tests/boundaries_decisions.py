#!/usr/bin/env python3
"""Μ·sweep·atom — the flip: cell is STRUCTURALLY barred from the sensitivity sweep, and the
decision-coverage axis it feeds is sound.

Two soundness invariants of the finer atom's NON-monotone half:

  (c) STRUCTURAL BAR — flip: sites are a distinct TYPE (FlipSite), not a string-prefix filter.  The
      sensitivity sweep and its atom (_apply) unpack a raise-kind site as `(file, node, label)`; a
      FlipSite is a 4-field NamedTuple, so handing one to _apply fails ON THE FIRST CALL (a
      ValueError/TypeError), not via a hand-authored selftest that could drift.  A value inversion can
      never enter a falsifiability sweep because the sweep's signature cannot receive it.

  (d) SOUND COVERAGE — decisions_unasserted flags a reached-but-unasserted decision, and does NOT
      false-positive on a fixture that only takes one arm.  The discriminator: BOTH sibling arms must
      be genuinely reached (per-arm flip_one, sibling-independent — group-testing correlates siblings,
      so `sens` membership alone is not reach), then an inversion that does not flip is unasserted.
      A check that asserts on the decision is NOT flagged; one that reaches both arms but never asserts
      IS; one that only takes one arm is excluded by the both-arms gate.

  The axis is NEVER a rung (like corroboration / content_sensitive): decisions_unasserted must not
  appear in RANK_C or STRENGTH — incompleteness is not a weaker grade.

    python3 paperkit/tests/boundaries_decisions.py     # exit 0 = the bar holds and the axis is sound
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))

import grade
import grader

_MOD = (
    "def classify(x):\n"
    "    if x > 0:\n"
    "        return 'pos'\n"
    "    else:\n"
    "        return 'neg'\n"
)


def _decisions(chk_src):
    """Grade a check over _MOD's classify() and return its unasserted-decision labels."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "decision_module.py").write_text(_MOD)
        (p / "check.py").write_text(chk_src)
        chk = "cmd:python3 check.py"
        _baseline, sens = grader.sensitivity(chk, p, {}, engine_dir=p)
        return grader.decisions_unasserted(chk, p, {}, p, sens)


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Μ·sweep·atom — flip: structurally barred; decision-coverage sound\n")

    # ── (c) the structural bar ───────────────────────────────────────────────────────────────────
    fs = grader.FlipSite(file=Path("x.py"), qualname="f", n=0, label="x.py::flip:f#0")
    try:
        grader._apply("cmd:x", Path(), {}, [fs])
        barred = False
    except (ValueError, TypeError):
        barred = True                                    # the sweep's `f, node, _ = …` cannot unpack it
    check("(c) a FlipSite handed to _apply FAILS structurally (not a silent no-op)", barred)
    check("(c) a FlipSite is a distinct 4-field type, not a (file, node, label) triple",
          len(grader.FlipSite._fields) == 4 and "node" not in grader.FlipSite._fields)

    # A flip: site is NEVER produced by _sites (the sweep's surface) — only by _flip_sites_of.
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "m.py").write_text("def f(x):\n    if x:\n        return 1\n    return 0\n")
        site_labels = [s[2] for s in grader._sites(p, p)]
        flip_labels = [f.label for f in grader._flip_sites_of(p, p)]
    check("(c) no flip: label appears in _sites (the sweep never sees a condition site)",
          not any("::flip:" in lbl for lbl in site_labels))
    check("(c) _flip_sites_of yields flip: sites separately",
          bool(flip_labels) and all("::flip:" in lbl for lbl in flip_labels))

    # ── (d) sound decision coverage ──────────────────────────────────────────────────────────────
    asserts_both = _decisions(
        "import sys; sys.path.insert(0, '.')\n"
        "from decision_module import classify\n"
        "assert classify(5) == 'pos'\n"
        "assert classify(-5) == 'neg'\n")
    check("(P) a check that ASSERTS the decision is NOT flagged unasserted", asserts_both == [])

    reaches_both = _decisions(
        "import sys; sys.path.insert(0, '.')\n"
        "from decision_module import classify\n"
        "classify(5)\n"
        "classify(-5)\n")
    check("(F) a check that REACHES both arms but never asserts IS flagged unasserted",
          reaches_both == ["decision_module.py::flip:classify#0"])

    one_arm = _decisions(
        "import sys; sys.path.insert(0, '.')\n"
        "from decision_module import classify\n"
        "assert classify(5) == 'pos'\n")
    check("(δ) a check that only exercises ONE arm is NOT flagged (both-arms gate rules out the "
          "fixture-coincidence false positive)", one_arm == [])

    # ── the axis is orthogonal, never a rung ─────────────────────────────────────────────────────
    check("decisions_unasserted is NOT a rung (absent from RANK_C — incompleteness is not a grade)",
          "decisions_unasserted" not in grade.RANK_C and "unasserted" not in grade.RANK_C)
    check("decisions_unasserted is NOT in STRENGTH (never gates min-strength)",
          "decisions_unasserted" not in grade.STRENGTH and "unasserted" not in grade.STRENGTH)
    check("DECISIONS_C declares the axis (unasserted < asserted), like CORRO_C",
          grade.DECISIONS_C == {"unasserted": 0, "asserted": 1})

    print()
    if fails:
        print(f"FAIL — {len(fails)} broken: {fails}")
        return 1
    print("ok — flip: is structurally barred from the sweep; decision-coverage is sound "
          "(both-arms-reached gate, no fixture-coincidence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
