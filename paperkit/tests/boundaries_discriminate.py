#!/usr/bin/env python3
"""Behavioral-boundary examples for Δ (paperkit/discriminate.py).

Every paperkit tool ships its boundaries as the triple ⟨P, F, δ⟩:
  P  — a minimal input the tool PASSES (the verdict on the good side)
  F  — a minimal input the tool FLAGS (the verdict on the bad side)
  δ  — the MINIMUM DELTA between them: the single smallest change that flips it.

Both documentation (read it to see exactly where Δ's lines fall) and a test (run
it; exit 0 iff every boundary holds).  The prototype is paper/checks/drift-caught.sh,
the same triple for the GATE: minimal fixture, append one drift line (δ), pass→fail.

    python3 paperkit/tests/boundaries_discriminate.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture import discriminate, entry  # noqa: E402

TOKEN = "WARRANT-TOKEN-A1B2"


def W(check):
    return [entry("w", claim=f"a claim that mentions {TOKEN}", check=check)]


def grade_of(check, assets=None):
    _, out = discriminate(W(check), "--all", "--json", assets=assets)
    return json.loads(out)[0]


def grader_of(check, flat=False):
    # Σ·flat·witness: read the recorded grader identity.  flat=True selects the
    # opt-in flat grader via the env var (the δ of the provenance boundary).
    env = {**os.environ, "PAPERKIT_DELTA_FLAT": "1"} if flat else None
    _, out = discriminate(W(check), "--all", "--json", env=env)
    return json.loads(out)[0]["grader"]


def gate_exit(check, cited):
    # cited-only gating: control whether [@w] appears in the projection directly
    out = "the claim [@w]\n" if cited else "no citation here\n"
    rc, _ = discriminate(W(check), "--min-strength", "behavioral", out=out)
    return rc


# ── ⟨grade⟩ examples: one minimal warrant per grade Δ can assign ──────────────
GRADE_CASES = [
    ("vacuous",       "file:w.bib",
     "presupposed input — exists because the build requires it"),
    ("existence",     "file:fig.svg",
     "contingent artifact — its absence is a real failure, but content is untested",
     {"fig.svg": "<svg/>\n"}),
    ("behavioral",    f"cmd:grep -q {TOKEN} w.bib",
     "content-sensitive — flips when the cited token leaves w.bib"),
    ("indeterminate", "cmd:true",
     "always passes; no mutation flips it (vacuous OR negative-assertion)"),
]

# ── ⟨P, F, δ⟩ pairs: the minimum delta that flips a verdict ───────────────────
DELTA_CASES = [
    {"name": "Δ-grade flip: vacuous → behavioral",
     "axis": "the check field of one warrant",
     "P": ("behavioral", f"cmd:grep -q {TOKEN} w.bib"), "F": ("vacuous", "file:w.bib"),
     "delta": f"check: file:w.bib  →  cmd:grep -q {TOKEN} w.bib", "kind": "grade"},
    {"name": "Δ gate flip: exit 0 → exit 1  (--min-strength behavioral)",
     "axis": "the check field of one cited warrant",
     "P": (0, f"cmd:grep -q {TOKEN} w.bib", True), "F": (1, "file:w.bib", True),
     "delta": f"check: cmd:grep -q {TOKEN} w.bib  →  file:w.bib", "kind": "gate"},
    {"name": "Δ gate scope: exit 0 → exit 1  (same vacuous check, citation toggled)",
     "axis": "whether the projection cites the warrant",
     "P": (0, "file:w.bib", False), "F": (1, "file:w.bib", True),
     "delta": "out.md: (no citation)  →  …the claim [@w]", "kind": "gate"},
    {"name": "Δ grader provenance: _grade_parallel → _grade_flat  (Σ·flat·witness)",
     "axis": "the PAPERKIT_DELTA_FLAT env var (which grader ran is RECORDED, not inferred)",
     "P": ("_grade_parallel", f"cmd:grep -q {TOKEN} w.bib", False),
     "F": ("_grade_flat", f"cmd:grep -q {TOKEN} w.bib", True),
     "delta": "env: (unset)  →  PAPERKIT_DELTA_FLAT=1", "kind": "grader"},
]


def main() -> int:
    fails = []
    print("Δ behavioral boundaries — ⟨grade⟩ examples\n")
    for case in GRADE_CASES:
        want, chk, why = case[0], case[1], case[2]
        assets = case[3] if len(case) > 3 else None
        r = grade_of(chk, assets)
        got = r["grade"]
        ok = got == want
        fails.append(case) if not ok else None
        sens = ", ".join(r.get("tests", [])) or "—"
        print(f"  {'ok ' if ok else 'XX '}{want:13} {chk}")
        print(f"      {why}")
        print(f"      → Δ says: {got}; sensitive to: {sens}")
        if want == "behavioral":
            print(f"      → content_sensitive: {r.get('content_sensitive')}")
        if not ok:
            print(f"      !! expected {want}, got {got}")
        print()

    print("Δ behavioral boundaries — ⟨P, F, δ⟩ minimum-delta pairs\n")
    for d in DELTA_CASES:
        if d["kind"] == "grade":
            (p_want, p_chk), (f_want, f_chk) = d["P"], d["F"]
            p_got, f_got = grade_of(p_chk)["grade"], grade_of(f_chk)["grade"]
            ok = (p_got == p_want) and (f_got == f_want) and (p_got != f_got)
            pside, fside = f"grade={p_got}", f"grade={f_got}"
        elif d["kind"] == "grader":
            (p_want, p_chk, p_flat), (f_want, f_chk, f_flat) = d["P"], d["F"]
            p_got, f_got = grader_of(p_chk, p_flat), grader_of(f_chk, f_flat)
            ok = (p_got == p_want) and (f_got == f_want) and (p_got != f_got)
            pside, fside = f"grader={p_got}", f"grader={f_got}"
        else:
            (p_want, p_chk, p_cite), (f_want, f_chk, f_cite) = d["P"], d["F"]
            p_got, f_got = gate_exit(p_chk, p_cite), gate_exit(f_chk, f_cite)
            ok = (p_got == p_want) and (f_got == f_want) and (p_got != f_got)
            pside, fside = f"exit={p_got}", f"exit={f_got}"
        if not ok:
            fails.append(d)
        print(f"  {'ok ' if ok else 'XX '}{d['name']}")
        print(f"      P (pass side): {pside}   ←  {d['P'][1]}")
        print(f"      F (flag side): {fside}   ←  {d['F'][1]}")
        print(f"      δ (min delta over {d['axis']}):")
        print(f"          {d['delta']}\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} case(s) drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(GRADE_CASES)} grades, {len(DELTA_CASES)} deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
