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
from _fixture import discriminate, discriminate_stderr, entry, project_text  # noqa: E402

TOKEN = "WARRANT-TOKEN-A1B2"


def W(check):
    return [entry("w", claim=f"a claim that mentions {TOKEN}", check=check)]


def grade_of(check, assets=None):
    _, out = discriminate(W(check), "--all", "--json", assets=assets)
    return json.loads(out)[0]


def grader_of(check, resumable=False):
    # Σ·flat·witness: read the recorded grader identity.  --budget selects the
    # resumable pump-witness (GradeWitness); the default is the batch grader
    # (_grade_parallel).  That the grader is RECORDED, not inferred, is the point.
    flags = ("--all", "--json") + (("--budget", "0") if resumable else ())
    _, out = discriminate(W(check), *flags)
    return json.loads(out)[0]["grader"]


def determinism_of(check):
    # Δ·det: grade with the determinism guard ON (PAPERKIT_DELTA_REPEAT=2) and report
    # "flaky" if the pristine baseline disagreed across runs, else the ordinary grade.
    env = {**os.environ, "PAPERKIT_DELTA_REPEAT": "2"}
    _, out = discriminate(W(check), "--all", "--json", env=env)
    r = json.loads(out)[0]
    return r.get("determinism") or r["grade"]


# a check whose verdict is NOT a function of project content: it toggles a stored
# bit every run, so consecutive baselines disagree (the cleanest provable flake).
FLAKY = "cmd:sh -c 'if [ -f det.flag ]; then rm det.flag; false; else touch det.flag; true; fi'"


def grades_via(warrants, resumable=False):
    # Σ·flat·agree: the whole grade-set produced by one grader, keyed by check.
    flags = ("--all", "--json") + (("--budget", "0") if resumable else ())
    _, out = discriminate(warrants, *flags)
    return {r["check"]: r["grade"] for r in json.loads(out)}


def pulse_lines(warrants, off=False):
    # Δ·pulse: count the liveness heartbeat lines ("graded N/total") in the grade's stderr.
    env = {**os.environ, "PAPERKIT_DELTA_PULSE": "0"} if off else None
    err = discriminate_stderr(warrants, "--all", "--json", env=env)
    return sum(1 for ln in err.splitlines() if "graded " in ln and "/" in ln)


# A deliberately MIXED-grade project: vacuous (presupposed file), behavioral
# (content-sensitive cmd), indeterminate (corruption-blind cmd) — so grader
# equivalence is checked on a discriminating set, not a degenerate all-same one.
MIXED = [
    entry("v", claim="a presupposed input", check="file:w.bib"),
    entry("b", claim=f"content that mentions {TOKEN}", check=f"cmd:grep -q {TOKEN} w.bib"),
    entry("i", claim="a check blind to the project", check="cmd:true"),
]


def compose_sub(green=True):
    # Ξ·seam: assets for a nested sibling project 'g' that GATES GREEN (a passing file:
    # check) or RED (a failing cmd:false) — the verdict a `result:g` import imports.  The
    # paper.toml/rubric/title MUST match _fixture's so g/out.md == project(g) (prose≡proj).
    w = entry("c", claim="a sibling claim", check=("file:w.bib" if green else "cmd:false"))
    toml = ('[paper]\ntitle = "t"\nwarrants = ["w.bib"]\nrubric = "r.tsv"\n'
            'out = "out.md"\nnumbered = false\nreferences = false\n')
    return {"g/paper.toml": toml, "g/r.tsv": "s\tSec\n", "g/w.bib": w,
            "g/out.md": project_text([w])}


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
    ("imported",      "result:g",
     "Ξ·seam — adequacy DELEGATED to a separately-gated sibling that gates green; run once, never swept",
     compose_sub(True)),
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
    {"name": "Δ grader provenance: _grade_parallel → GradeWitness  (Σ·flat·witness)",
     "axis": "whether grading is resumable (--budget selects the pump-witness, RECORDED not inferred)",
     "P": ("_grade_parallel", f"cmd:grep -q {TOKEN} w.bib", False),
     "F": ("GradeWitness", f"cmd:grep -q {TOKEN} w.bib", True),
     "delta": "flags: (none)  →  --budget 0", "kind": "grader"},
    {"name": "Δ vacuity-source: behavioral → total  (corruption-blind, Δ·vacuity-source)",
     "axis": "whether the check reads a corruptible PROJECT input at all",
     "P": ("behavioral", f"cmd:grep -q {TOKEN} w.bib"),
     "F": ("total", "cmd:true"),
     "delta": f"check: cmd:grep -q {TOKEN} w.bib  →  cmd:true", "kind": "vacuity"},
    {"name": "Δ determinism: gradable → flaky  (Δ·det, PAPERKIT_DELTA_REPEAT=2)",
     "axis": "whether the verdict is a function of project content (stable across baseline runs)",
     "P": ("indeterminate", "cmd:true"),
     "F": ("flaky", FLAKY),
     "delta": "the check toggles a stored bit each run (its verdict depends on hidden state)",
     "kind": "determinism"},
    {"name": "Δ pulse: heartbeat → silent  (Δ·pulse)",
     "axis": "PAPERKIT_DELTA_PULSE — a slow grade must read as LIVE, not stalled",
     "P": ("heartbeat emitted", "default"),
     "F": ("silenced", "PAPERKIT_DELTA_PULSE=0"),
     "delta": "env: (default ~2s) → PAPERKIT_DELTA_PULSE=0", "kind": "pulse"},
    {"name": "Δ compose: imported → broken  (Ξ·seam verdict-import)",
     "axis": "whether the imported sibling project gates green",
     "P": ("imported", "result:g"), "F": ("broken", "result:g"),
     "delta": "sibling g's check: file:w.bib (green) → cmd:false (red)", "kind": "compose"},
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
        elif d["kind"] == "vacuity":
            (p_want, p_chk), (f_want, f_chk) = d["P"], d["F"]
            pr, fr = grade_of(p_chk), grade_of(f_chk)
            p_got, f_got = pr["grade"], fr.get("vacuity")
            ok = (p_got == p_want) and (f_got == f_want) and (pr["grade"] != fr["grade"])
            pside, fside = f"grade={p_got}", f"vacuity={f_got}"
        elif d["kind"] == "determinism":
            (p_want, p_chk), (f_want, f_chk) = d["P"], d["F"]
            p_got, f_got = determinism_of(p_chk), determinism_of(f_chk)
            ok = (p_got == p_want) and (f_got == f_want) and (p_got != f_got)
            pside, fside = f"{p_got}", f"{f_got}"
        elif d["kind"] == "pulse":
            on, off = pulse_lines(MIXED) > 0, pulse_lines(MIXED, off=True) > 0
            ok = on and not off
            pside, fside = f"pulse={'yes' if on else 'NO'}", f"pulse={'yes' if off else 'no'}"
        elif d["kind"] == "compose":
            p_want, f_want = d["P"][0], d["F"][0]
            p_got = grade_of("result:g", compose_sub(green=True))["grade"]
            f_got = grade_of("result:g", compose_sub(green=False))["grade"]
            ok = (p_got == p_want) and (f_got == f_want) and (p_got != f_got)
            pside, fside = f"grade={p_got}", f"grade={f_got}"
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

    # ── Σ·flat·agree: the batch (_grade_parallel) and resumable (GradeWitness)
    # graders must produce IDENTICAL grades — verified on the MIXED project above,
    # not a degenerate all-same one (the gap the Σ·flat·gate guard-fix left).
    print("Δ grader equivalence — Σ·flat·agree\n")
    par, wit = grades_via(MIXED, resumable=False), grades_via(MIXED, resumable=True)
    distinct = sorted(set(par.values()))
    mixed_ok = len(distinct) >= 3                       # genuinely discriminating, not degenerate
    agree_ok = par == wit
    if not (mixed_ok and agree_ok):
        fails.append(("agree", par, wit))
    print(f"  {'ok ' if mixed_ok and agree_ok else 'XX '}batch (_grade_parallel) ≡ resumable (GradeWitness)")
    print(f"      parallel: {par}")
    print(f"      witness : {wit}")
    print(f"      distinct grades: {distinct}  ({'mixed' if mixed_ok else 'DEGENERATE — proves nothing'})\n")

    # ── Ξ·seam adequacy-composes: --min-strength behavioral ACCEPTS an imported verdict
    # (delegated to a separately-gated sibling) but REJECTS a vacuous file: — the gate-mode
    # proof that composition meets the behavioral floor without re-deriving the sibling.
    print("Δ adequacy-composes — Ξ·seam\n")
    imp_rc, _ = discriminate(W("result:g"), "--min-strength", "behavioral", assets=compose_sub(True))
    vac_rc, _ = discriminate(W("file:w.bib"), "--min-strength", "behavioral")
    compose_ok = imp_rc == 0 and vac_rc == 1
    if not compose_ok:
        fails.append(("adequacy-composes", imp_rc, vac_rc))
    print(f"  {'ok ' if compose_ok else 'XX '}--min-strength behavioral: imported PASSES, vacuous FAILS")
    print(f"      P (pass side): result:g (imported) → exit {imp_rc}")
    print(f"      F (flag side): file:w.bib (vacuous) → exit {vac_rc}")
    print(f"      δ (min delta): the check's grade meets the behavioral floor by DELEGATION, not derivation\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} case(s) drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(GRADE_CASES)} grades, {len(DELTA_CASES)} deltas, "
          f"1 grader-equivalence, 1 adequacy-composes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
