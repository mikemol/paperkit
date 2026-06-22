#!/usr/bin/env python3
"""Behavioral-boundary examples for Δ (paperkit/discriminate.py).

Every paperkit tool ships its boundaries as the triple ⟨P, F, δ⟩:
  P  — a minimal input the tool PASSES (the verdict on the good side)
  F  — a minimal input the tool FLAGS (the verdict on the bad side)
  δ  — the MINIMUM DELTA between them: the single smallest change that flips
       the verdict.  The boundary IS δ; P and F are the two sides of it.

This file is both documentation (read it to see exactly where Δ's lines fall)
and a test (run it; exit 0 iff every boundary holds).  It is the linting layer
for Δ — the prototype is paper/checks/drift-caught.sh, which is the same triple
for the GATE: minimal fixture, append one drift line (δ), assert pass→fail.

    python3 paperkit/tests/boundaries_discriminate.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent          # paperkit/
DELTA = ENGINE / "discriminate.py"
TOKEN = "WARRANT-TOKEN-A1B2"

PAPER_TOML = '[paper]\ntitle = "boundary fixture"\nwarrants = ["warrants.bib"]\n' \
             'rubric = "rubric.tsv"\nout = "paper.md"\n'
RUBRIC = "s\tThe Section\n"


def warrant(check: str) -> str:
    return ("@misc{w,\n  section = {s},\n"
            f"  claim   = {{a claim that mentions {TOKEN}}},\n"
            f"  check   = {{{check}}}\n}}\n")


def make_proj(root: Path, check: str, extra: dict | None = None, cite: bool = True) -> Path:
    """A minimal one-warrant paper project under root/proj (root is the parent
    Δ will copy).  cite=True writes a paper.md that cites [@w] — Δ's gate mode
    considers only CITED warrants, so the projection controls gate scope."""
    proj = root / "proj"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "paper.toml").write_text(PAPER_TOML)
    (proj / "rubric.tsv").write_text(RUBRIC)
    (proj / "warrants.bib").write_text(warrant(check))
    (proj / "paper.md").write_text("the claim [@w]\n" if cite else "no citation here\n")
    for name, body in (extra or {}).items():
        (proj / name).write_text(body)
    return proj


def grade_of(check: str, extra: dict | None = None) -> dict:
    with tempfile.TemporaryDirectory() as t:
        proj = make_proj(Path(t), check, extra)
        out = subprocess.run([sys.executable, str(DELTA), "--all", "--json", str(proj)],
                             capture_output=True, text=True)
        return json.loads(out.stdout)[0]


def gate_exit(check: str, cite: bool = True) -> int:
    with tempfile.TemporaryDirectory() as t:
        proj = make_proj(Path(t), check, cite=cite)
        return subprocess.run([sys.executable, str(DELTA), "--min-strength", "behavioral",
                              str(proj)], capture_output=True, text=True).returncode


# ── ⟨grade⟩ examples: one minimal warrant per grade Δ can assign ──────────────
GRADE_CASES = [
    ("vacuous",       "file:warrants.bib",
     "presupposed input — exists because the build requires it"),
    ("existence",     "file:fig.svg",
     "contingent artifact — its absence is a real failure, but content is untested",
     {"fig.svg": "<svg/>\n"}),
    ("behavioral",    f"cmd:grep -q {TOKEN} warrants.bib",
     "content-sensitive — flips when the cited token leaves warrants.bib"),
    ("indeterminate", "cmd:true",
     "always passes; no mutation flips it (vacuous OR negative-assertion)"),
]

# ── ⟨P, F, δ⟩ pairs: the minimum delta that flips a verdict ───────────────────
# Each: a passing side, a failing side, and the single field that differs.
DELTA_CASES = [
    {
        "name": "Δ-grade flip: vacuous → behavioral",
        "axis": "the check field of one warrant",
        "P": ("behavioral", f"cmd:grep -q {TOKEN} warrants.bib"),
        "F": ("vacuous",    "file:warrants.bib"),
        "delta": f"check: file:warrants.bib  →  cmd:grep -q {TOKEN} warrants.bib",
        "kind": "grade",
    },
    {
        "name": "Δ gate flip: exit 0 → exit 1  (--min-strength behavioral)",
        "axis": "the check field of one cited warrant",
        "P": (0, f"cmd:grep -q {TOKEN} warrants.bib", True),
        "F": (1, "file:warrants.bib", True),
        "delta": f"check: cmd:grep -q {TOKEN} warrants.bib  →  file:warrants.bib",
        "kind": "gate",
    },
    {
        "name": "Δ gate scope: exit 0 → exit 1  (same vacuous check, citation toggled)",
        "axis": "whether the projection cites the warrant",
        "P": (0, "file:warrants.bib", False),   # uncited: a vacuous check that never ships is not gated
        "F": (1, "file:warrants.bib", True),     # cited: the shipped sentence is now subject to Δ
        "delta": "paper.md: (no citation)  →  …the claim [@w]",
        "kind": "gate",
    },
]


def main() -> int:
    fails = []
    print("Δ behavioral boundaries — ⟨grade⟩ examples\n")
    for case in GRADE_CASES:
        want, check = case[0], case[1]
        why = case[2]
        extra = case[3] if len(case) > 3 else None
        r = grade_of(check, extra)
        got = r["grade"]
        ok = got == want
        fails.append(case) if not ok else None
        sens = ", ".join(r.get("tests", [])) or "—"
        mark = "ok " if ok else "XX "
        print(f"  {mark}{want:13} {check}")
        print(f"      {why}")
        print(f"      → Δ says: {got}; sensitive to: {sens}")
        if want == "behavioral":
            cs = r.get("content_sensitive")
            print(f"      → content_sensitive: {cs}")
        if not ok:
            print(f"      !! expected {want}, got {got}")
        print()

    print("Δ behavioral boundaries — ⟨P, F, δ⟩ minimum-delta pairs\n")
    for d in DELTA_CASES:
        if d["kind"] == "grade":
            p_want, p_check = d["P"]; f_want, f_check = d["F"]
            p_got = grade_of(p_check)["grade"]; f_got = grade_of(f_check)["grade"]
            ok = (p_got == p_want) and (f_got == f_want) and (p_got != f_got)
            pside, fside = f"grade={p_got}", f"grade={f_got}"
        else:
            p_want, p_check, p_cite = d["P"]; f_want, f_check, f_cite = d["F"]
            p_got = gate_exit(p_check, p_cite); f_got = gate_exit(f_check, f_cite)
            ok = (p_got == p_want) and (f_got == f_want) and (p_got != f_got)
            pside, fside = f"exit={p_got}", f"exit={f_got}"
        if not ok:
            fails.append(d)
        mark = "ok " if ok else "XX "
        print(f"  {mark}{d['name']}")
        print(f"      P (pass side): {pside}   ←  {p_check}")
        print(f"      F (flag side): {fside}   ←  {f_check}")
        print(f"      δ (min delta over {d['axis']}):")
        print(f"          {d['delta']}")
        print()

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} case(s) drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(GRADE_CASES)} grades, {len(DELTA_CASES)} deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
