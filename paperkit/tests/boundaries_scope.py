#!/usr/bin/env python3
"""Ξ·entails — the SCOPE axis's boundary: a declared shortfall must answer to its evidence.

`entails = {fragment}` is an author saying "this witness covers PART of what the sentence claims".
Every other axis in grade.py reads a MEASUREMENT; this one reads a DECLARATION, and that asymmetry
is the whole risk.  Two failure directions were live in the design and only one survives:

  * a scope that CLAMPED its own grade would be self-fulfilling — say `fragment`, get a smaller
    number, with nothing asking whether the shortfall was real.  An author's word standing in for
    a fact is the naming-not-entailment gap this axis exists to close, so it must not reappear
    inside the axis.  The scope therefore NEVER moves a grade.
  * a scope that was merely disclosed and never checked would be decoration: any word at all, and
    no evidence could contradict it.

So the axis discloses (`scope` on every record) and coherence's sixth face holds the disclosure to
the sweep.  What can be checked SOUNDLY is narrower than "is the fragment real" — `tests` records
which def-sites flip a check, never what proportion of a SENTENCE it covers — so the face judges
the one direction the evidence genuinely contradicts: `fragment` on a witness nothing flips.

    python3 paperkit/tests/boundaries_scope.py     # exit 0 = the axis discloses, never clamps
"""
from __future__ import annotations

import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))

import bib
import coherence
import grade

ran: list = []


def check(label: str, ok: bool) -> None:
    ran.append(ok)
    print(f"  {'ok ' if ok else 'XX '}{label}")


def _rec(key, gradeval, tests, entails=None, **kw):
    r = {"key": key, "grade": gradeval, "tests": list(tests), **kw}
    if entails is not None:
        r["entails"] = entails
    return r


def main() -> int:
    print(__doc__.strip().splitlines()[0] + "\n")

    # ── the axis is an axis: it does NOT move the grade ────────────────────────────────────
    print("scope never clamps\n")
    frag = grade.clamp([_rec("f", "behavioral", ["a.py:1"], entails="fragment")])[0]
    full = grade.clamp([_rec("g", "behavioral", ["a.py:1"])])[0]
    check("a `fragment` claim keeps its measured grade",
          frag["effective_grade"] == "behavioral" and frag["clamp"] == 0)
    check("...and is pinned by nothing (clamped_by stays for PREMISES)",
          frag["clamped_by"] is None)
    check("fragment and full grade identically — the axis is orthogonal",
          frag["effective_grade"] == full["effective_grade"])

    # a premise still clamps, so removing the scope-clamp did not disable clamping itself
    pair = grade.clamp([_rec("weak", "vacuous", []),
                        _rec("strong", "behavioral", ["a.py:1"],
                             entails="fragment", **{"rests-on": ["weak"]})])
    strong = [r for r in pair if r["key"] == "strong"][0]
    check("a real GROUNDING premise still clamps a fragment claim",
          strong["effective_grade"] == "vacuous" and strong["clamped_by"] == "weak")

    # ── the disclosure reaches the record ──────────────────────────────────────────────────
    print("\nscope is disclosed as a VALUE\n")
    check("`scope` is on the record for a fragment", frag["scope"] == "fragment")
    check("absence defaults to `full`, not missing", full["scope"] == "full")
    # ⚑ ONE owner, and the direction is load-bearing.  The parser must refuse a typo'd scope, and
    # bib.py (model) may not import grade.py (delta) to learn the legal set — the partition check
    # catches that edge, and did.  So bib._SCOPES owns the vocabulary and grade.SCOPE_C ranks it.
    # A second hand-written list in either place would drift in silence, and the direction that
    # drifts WORST is the parser's: it would accept a value the ranking cannot rank.
    check("bib._SCOPES owns the vocabulary; SCOPE_C derives its keys from it",
          set(grade.SCOPE_C) == set(bib._SCOPES))
    check("...and ranks them fragment < full (less coverage is the lower end)",
          grade.SCOPE_C["fragment"] < grade.SCOPE_C["full"])
    # ⚑ MEASURED, not source-scanned.  An eager `SCOPE_C = _scopes()` passed every local test
    # (python3 had both modules on sys.path) and then died in the sandbox: tools/read_grade.py
    # stages grade ALONE, and every Ζ·calc cell raised ModuleNotFoundError before running.  A
    # module-level CALL is a module-level dependency even when its `import` sits inside a
    # function — what matters is when it EXECUTES.  So import grade with bib UNREACHABLE, the
    # way the sandbox does, rather than grepping the source for an import statement.
    import shutil
    import subprocess
    import tempfile
    _d = tempfile.mkdtemp()
    try:
        shutil.copy(ENGINE / "grade.py", _d)
        rc = subprocess.run([sys.executable, "-c", "import grade"], cwd=_d,
                            env={"PYTHONPATH": _d, "PATH": "/usr/bin:/bin"},
                            capture_output=True).returncode
        check("grade imports with bib UNREACHABLE (read_grade.py stages it alone)", rc == 0)
    finally:
        shutil.rmtree(_d, ignore_errors=True)

    # ── the face holds the declaration to the evidence ─────────────────────────────────────
    print("\nthe sixth face judges the contradicted direction\n")
    honest = coherence.scope_residual(
        [_rec("a", "behavioral", ["x.py:1"], entails="fragment"), _rec("b", "behavioral", ["y.py:2"])])
    check("a fragment on a FALSIFIABLE witness is fine (that is the point of the axis)",
          honest["residual"] == 0 and honest["declared"] == 1 and honest["behavioral"] == 1)

    lying = coherence.scope_residual([_rec("a", "indeterminate", [], entails="fragment")])
    check("a fragment on a witness NOTHING flips is residual",
          lying["residual"] == 1 and lying["contradicted"] == ["a"])
    check("...and the face NAMES it, never just counts",
          "a" in lying["contradicted"])

    # Ζ·symdiff — a face reporting residual 0 over ZERO declarations measured nothing, and on a
    # corpus where no claim declares a scope (every project here, today) that is the reading a
    # consumer will actually get.  It must not render as a clean bill.
    silent = coherence.scope_residual([_rec("a", "behavioral", ["x.py:1"])])
    check("residual 0 over NO declarations reports measured=False, not a clean bill",
          silent["residual"] == 0 and silent["measured"] is False)
    check("...and residual 0 over a REAL declaration reports measured=True",
          honest["measured"] is True)

    # ── an unrecognized scope is refused, not defaulted ────────────────────────────────────
    print("\na typo'd scope fails CLOSED\n")
    d = Path(__file__).resolve().parent / "_scope_tmp.bib"
    try:
        d.write_text("@misc{k,\n  section = {s},\n  claim = {c},\n"
                     "  check = {cmd:true},\n  entails = {fragmnt}\n}\n")
        try:
            bib.parse(d)
            refused = False
        except SystemExit:
            refused = True
        check("`entails = {fragmnt}` is REFUSED (it would read as `full` and restore the rung)",
              refused)
    finally:
        d.unlink(missing_ok=True)

    # ── ⟨P, F, δ⟩ ──────────────────────────────────────────────────────────────────────────
    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    p_arm = coherence.scope_residual([_rec("c", "behavioral", ["x.py:1"], entails="fragment")])
    f_arm = coherence.scope_residual([_rec("c", "indeterminate", [], entails="fragment")])
    caught = p_arm["residual"] == 0 and f_arm["residual"] == 1
    check("the face's two arms differ on the EVIDENCE alone", caught)
    print("      P (arm):     entails=fragment + tests=['x.py:1'] → residual 0 (a real partial proof)")
    print("      F (arm):     entails=fragment + tests=[]         → residual 1 (partial proof of nothing)")
    print("      δ (min delta): the witness's measured reach — the declaration is byte-identical\n")

    bad = len([b for b in ran if not b])
    if bad:
        print(f"SCOPE BOUNDARIES: FAIL ({bad} of {len(ran)})")
        return 1
    print(f"SCOPE BOUNDARIES: PASS ({len(ran)} arms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
