#!/usr/bin/env python3
"""Μ·sweep·atom (DATA) — the grader consumes data sites: a dict a witness reads is now GRADED.

The pure atom (bnd-data-atom) makes structured data MUTATABLE; this gates that the GRADER actually
sweeps it — the wall the last arc hit (a decision dict was un-swept, so its sens set was empty) is
breached:

  - a data-: DROP of a key a witness READS appears in `sens` (the monotone drop feeds the
    sensitivity grade); a key it does NOT read does not — precise, per-key.
  - a DflipSite (the non-monotone value perturb) handed to _apply FAILS structurally (5 fields
    against the sweep's 3-field unpack) — the value swap can never enter the falsifiability sweep,
    the DATA analog of the FlipSite bar.
  - decisions_unasserted flags a dict VALUE a witness reads but never asserts on (its sibling
    data-: DROP flips ⇒ the key is read; perturbing the value to a valid sibling does NOT flip ⇒
    the value is unasserted), and does NOT flag a value the witness asserts.

    python3 paperkit/tests/boundaries_data_grade.py     # exit 0 = structured data is graded, soundly
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))

import grader  # noqa: E402

_MOD = 'SCOPE = {"x": "full", "y": "fragment", "z": "full"}\ndef s(k):\n    return SCOPE[k]\n'


def _sens_of(check_src):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "m.py").write_text(_MOD)
        (p / "check.py").write_text(check_src)
        chk = "cmd:python3 check.py"
        _b, sens = grader.sensitivity(chk, p, {}, engine_dir=p)
        return sens


def _decisions_of(check_src):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "m.py").write_text(_MOD)
        (p / "check.py").write_text(check_src)
        chk = "cmd:python3 check.py"
        _b, sens = grader.sensitivity(chk, p, {}, engine_dir=p)
        return [u for u in grader.decisions_unasserted(chk, p, {}, p, sens) if "dflip:" in u]


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Μ·sweep·atom (DATA) — the grader sweeps structured data\n")

    # ── data-: is a monotone site the sweep consumes (the wall breached) ─────────────────────────
    sens = _sens_of(
        "import sys; sys.path.insert(0, '.')\n"
        "from m import s\n"
        "assert s('x') == 'full'\n")                      # reads only key "x" (#0)
    data_sens = [x for x in sens if "data-:" in x]
    check("a data-: DROP of a READ key appears in sens (structured data is now swept)",
          any("::data-:SCOPE#0" in x for x in data_sens))
    check("a data-: DROP of an UNREAD key does NOT appear in sens (precise, per-key)",
          not any("::data-:SCOPE#1" in x for x in data_sens))

    # ── the DflipSite structural bar ─────────────────────────────────────────────────────────────
    ds = grader.DflipSite(file=Path("x.py"), qualname="D", n=0, kind="dict", label="x.py::dflip:D#0")
    try:
        grader._apply("cmd:x", Path("."), {}, [ds])
        barred = False
    except (ValueError, TypeError):
        barred = True                                    # 5 fields vs the sweep's `f, node, _ =`
    check("a DflipSite handed to _apply FAILS structurally (the value-perturb bar)", barred)
    check("a DflipSite is a distinct 5-field type, not a (file, node, label) triple",
          len(grader.DflipSite._fields) == 5 and "node" not in grader.DflipSite._fields)
    # a dflip: label is never in _sites (the sweep surface); only _dflip_sites_of yields it.
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "m.py").write_text(_MOD)
        site_labels = [x[2] for x in grader._sites(p, p)]
        dflip_labels = [x.label for x in grader._dflip_sites_of(p, p)]
    check("no dflip: label appears in _sites (the sweep never sees a value-perturb)",
          not any("::dflip:" in lbl for lbl in site_labels))
    check("data-: labels DO appear in _sites (the monotone drop is a swept site)",
          any("::data-:SCOPE#" in lbl for lbl in site_labels))
    check("_dflip_sites_of yields dflip: sites separately",
          bool(dflip_labels) and all("::dflip:" in lbl for lbl in dflip_labels))

    # ── decisions_unasserted, the DATA path ──────────────────────────────────────────────────────
    asserts = _decisions_of(
        "import sys; sys.path.insert(0, '.')\n"
        "from m import s\n"
        "assert s('x') == 'full'\n")                      # ASSERTS the value
    check("(P) a check that ASSERTS a dict value is NOT flagged unasserted", asserts == [])

    reads = _decisions_of(
        "import sys; sys.path.insert(0, '.')\n"
        "from m import s\n"
        "s('x')\n")                                       # READS but never asserts the value
    check("(F) a check that READS a dict value but never asserts it IS flagged unasserted",
          reads == ["m.py::dflip:SCOPE#0"])

    print()
    if fails:
        print(f"FAIL — {len(fails)} broken: {fails}")
        return 1
    print("ok — the grader sweeps structured data: data-: monotone-in-sens, DflipSite barred, "
          "decisions_unasserted names an unasserted dict value")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
