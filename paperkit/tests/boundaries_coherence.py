#!/usr/bin/env python3
"""Behavioral-boundary examples for coherence (∂²) — paperkit/coherence.py.

⟨P, F, δ⟩ per the boundary practice.  ∂² re-reads Δ records and reports three residuals:
STRUCTURE (where a claim's `from` and `rests-on` edges diverge), SENSITIVITY (where
name-distinct witnesses collapse to one sensitivity signature), and GROUNDING (where a
declared `rests-on` edge is disjoint from its premise's measured engine fingerprint).
Bounds: a coherent record set shows zero residual, an incoherent one surfaces it, and the
minimum delta is a single diverging edge / a single shared signature / a single disjoint
grounding edge.

    python3 paperkit/tests/boundaries_coherence.py
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import coherence as C


def rec(key, frm=(), rests=(), grade="behavioral", tests=(), section=None):
    return {"key": key, "from": list(frm), "rests-on": list(rests),
            "grade": grade, "tests": list(tests), "cited": True, "section": section}


# structure: a grounding edge to the immediate prose predecessor is CARRIED; to a
# non-adjacent claim it is a LONG edge owed a projected reference.
CARRIED = [rec("a", section="s"), rec("b", section="s", frm=["a"], rests=["a"])]   # b grounds on its predecessor
LONG = [rec("a", section="s"), rec("b", section="s", frm=["a"]),
        rec("c", section="s", frm=["b"], rests=["a"])]                              # c grounds on a, two back
DISTINCT = [rec("a", tests=["x.py"]), rec("b", tests=["y.py"])]  # different sensitivity
COLLAPSED = [rec("a", tests=["w.py"]), rec("b", tests=["w.py"])]  # same sensitivity
# grounding: b rests-on a; engine fingerprints overlap / disjoint-genuine / disjoint-rhetorical
GROUNDED = [rec("a", tests=["paperkit/gate.py::resolves"]),
            rec("b", rests=["a"], tests=["paperkit/gate.py::resolves", "paperkit/project.py::weave"])]
GENUINE = [rec("a", tests=["paperkit/gate.py::resolves"]),       # b tests engine capability, just not a's
           rec("b", rests=["a"], tests=["paperkit/rhetoric.py::kind_of"])]
RHETORICAL = [rec("a", tests=["paperkit/gate.py::resolves"]),    # b tests NO engine capability (empty)
              rec("b", rests=["a"], tests=["checks/claims.py::b"])]
SCAFFOLD = [rec("a", tests=["checks/claims.py::a"]),             # a measures no engine capability — no edge
            rec("b", rests=["a"], tests=["checks/claims.py::b"])]
# Ν·vac: the WHOLE measurement is vacuous iff NO claim tests any engine capability (every
# fingerprint empty — a degraded def-sweep).  One engine site anywhere makes it non-vacuous.
VAC = [rec("only", tests=["checks/claims.py::only"])]            # scaffolding only → measures nothing
LIVE = [rec("only", tests=["paperkit/gate.py::resolves"])]      # one engine site → a real measurement
# (c) the COMPUTED FRAME (Ζ·torsor) — `_engine_cap` quotients the sites EVERY cited claim trips
# (`_universal_sites`), because a site all witnesses share cannot DISCRIMINATE two claims and so
# makes any grounding overlap on it trivially true.  U is such a universal site; the ONLY grounding
# overlap between a and b is U, so the frame's quotient exposes the edge as the genuine miss it is —
# reflected WITHOUT the frame, a miss WITH it.  (The old frame hardcoded `paperkit/`-inclusion and
# never computed this, so the whole quotient was untested.)
U = "paperkit/bib.py::parse"
UNIVFRAME = [rec("a", tests=[U, "paperkit/gate.py::resolves"]),
             rec("b", rests=["a"], tests=[U, "paperkit/project.py::weave"])]
# (d) the UNMEASURED face (Ζ·symdiff) — a `rests-on` edge whose TARGET was never graded is invisible
# to grounding/emergence (both need a fingerprint at BOTH ends).  `pending` = target the bib declares
# but no grade covers yet; `dangling` = target no bib entry declares at all (a broken edge, not a
# thin grade).  Separating them keeps a partial reading from implying coverage it does not have.
PENDING = [rec("x", rests=["y"])]                    # y declared (∈ all_keys) but ungraded → pending
DANGLING = [rec("x", rests=["z"])]                   # z declared nowhere → dangling (broken edge)
MEASURED_TGT = [rec("y"), rec("x", rests=["y"])]     # y graded → the edge is seen, nothing pending


def main() -> int:
    fails = []

    ran = []

    def check(desc, cond):
        # Λ·guard-must-not-copy — `ran` COUNTS the arms.  The summary line used to restate a
        # number authored beside the set it describes, and every one of the 26 suites carrying
        # such a line UNDERSTATED it (24 mismatched, none overstated): arms were added and the
        # literal never moved, so it tracked the suite's authoring history rather than its
        # content — and would have read a SHRINKING suite as an unchanged one.
        ran.append(desc)
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("∂² residual behaviors\n")
    check("structure: a grounding edge to the immediate predecessor is CARRIED (0 owed)",
          C.structure_residual(CARRIED)["carried"] == 1 and C.structure_residual(CARRIED)["owed"] == 0)
    check("structure: a grounding edge two-back is a LONG edge owed a reference",
          C.structure_residual(LONG)["owed"] == 1 and C.structure_residual(LONG)["carried"] == 0)
    check("a long edge is un-acknowledged by default (advisory)",
          C.structure_residual(LONG)["undischarged"] == 1)
    check("a `link` footnote discharges the long edge (still drawn, not flagged)",
          C.structure_residual(LONG, discharged={"c"})["undischarged"] == 0
          and C.structure_residual(LONG, discharged={"c"})["owed"] == 1)
    check("sensitivity: distinct tests → 2 signatures, 0 collapse",
          C.sensitivity_residual(DISTINCT)["signatures"] == 2 and C.sensitivity_residual(DISTINCT)["collapse"] == 0)
    check("sensitivity: shared tests → 1 signature, 1 collapse (name-distinct, sensitivity-same)",
          C.sensitivity_residual(COLLAPSED)["signatures"] == 1 and C.sensitivity_residual(COLLAPSED)["collapse"] == 1)
    check("grounding: overlapping engine fingerprint → edge reflected, 0 residual",
          C.grounding_residual(GROUNDED)["reflected"] == 1 and C.grounding_residual(GROUNDED)["undischarged"] == 0)
    check("grounding: disjoint with a NON-empty fingerprint → genuine undischarged miss",
          C.grounding_residual(GENUINE)["undischarged"] == 1)
    check("grounding: an empty-fingerprint claim is vacuously disjoint → rhetorical, auto-discharged",
          C.grounding_residual(RHETORICAL)["rhetorical"] == 1 and C.grounding_residual(RHETORICAL)["undischarged"] == 0)
    check("grounding: a `link` discharges a genuine miss",
          C.grounding_residual(GENUINE, discharged={"b"})["undischarged"] == 0)
    check("grounding: shared scaffolding is not engine grounding (no edge counted)",
          C.grounding_residual(SCAFFOLD)["grounding_edges"] == 0)

    # Ζ·cohere·mute — the EXIT, not the computation.  Every check above proves the residual is
    # computed right; none proved anyone ever SEES it.  `--from-calcs` (the arm //:cohere runs)
    # returned 1 in silence, so a red gate said `fail` and discarded the named misses one field
    # away.  δ = the same fixtures, one edge apart: silence+0 vs the edge named on stderr.
    def _exit(recs, discharged=frozenset()):
        rep = C.report(recs, set(discharged), frozenset(r["key"] for r in recs))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = C._grounding_exit(rep)
        return rc, err.getvalue()

    p_rc, p_err = _exit(GROUNDED)
    check("exit (P): a reflected edge → 0, and SILENT (no residual to report)",
          p_rc == 0 and p_err == "")
    f_rc, f_err = _exit(GENUINE)
    check("exit (F): an undischarged edge → 1, and the edge is NAMED on stderr",
          f_rc == 1 and "[@b]" in f_err and "[@a]" in f_err)
    check("exit (δ): a `link` on the same fixture flips it back to silent+0",
          _exit(GENUINE, {"b"}) == (0, ""))
    check("vacuity (Ν·vac): no claim tests engine capability → report flags vacuous (refuse a verdict)",
          C.report(VAC)["vacuous"] is True)
    check("vacuity (Ν·vac): one engine site → NOT vacuous (a real verdict is possible)",
          C.report(LIVE)["vacuous"] is False)
    check("frame (c): _universal_sites is the intersection over cited fingerprints (≥2 claims)",
          C._universal_sites(UNIVFRAME) == frozenset({U}))
    check("frame (c): below two fingerprints the frame is undefined → identity quotient (empty)",
          C._universal_sites([rec("a", tests=[U, "paperkit/gate.py::resolves"])]) == frozenset())
    check("frame (c): un-quotiented, the shared universal site reflects the edge (undischarged 0)",
          C.grounding_residual(UNIVFRAME)["undischarged"] == 0)
    check("frame (c): report() quotients the universal site → the edge is a genuine miss (undischarged 1)",
          C.report(UNIVFRAME)["grounding"]["undischarged"] == 1)
    check("unmeasured (d): a rests-on to an ungraded-but-declared target is PENDING",
          C.unmeasured_edges(PENDING, all_keys=frozenset({"x", "y"}))["pending"] == [["x", "y"]])
    check("unmeasured (d): a rests-on to a target no bib entry declares is DANGLING (broken edge)",
          C.unmeasured_edges(DANGLING, all_keys=frozenset({"x"}))["dangling"] == [["x", "z"]])
    check("unmeasured (d): a graded target is seen by grounding → not counted",
          C.unmeasured_edges(MEASURED_TGT, all_keys=frozenset({"x", "y"}))["unmeasured"] == 0)
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("structure residual tracks the grounding edge's prose distance",
         "the dependent claim's grounding target (predecessor → two-back)",
         "adjacent → 0 owed", C.structure_residual(CARRIED)["owed"] == 0,
         "non-adjacent → 1 owed", C.structure_residual(LONG)["owed"] == 1),
        ("sensitivity collapse tracks signature sharing",
         "the second witness's tests (y.py → w.py)",
         "distinct → 0 collapse", C.sensitivity_residual(DISTINCT)["collapse"] == 0,
         "shared   → 1 collapse", C.sensitivity_residual(COLLAPSED)["collapse"] == 1),
        ("a `link` footnote discharges a long edge (advisory, not a gate)",
         "acknowledging claim c's link",
         "un-acknowledged → 1", C.structure_residual(LONG)["undischarged"] == 1,
         "footnoted → 0", C.structure_residual(LONG, discharged={"c"})["undischarged"] == 0),
        ("grounding: a disjoint edge is residual only when UN-explained",
         "why the edge is disjoint (empty fingerprint / link / neither)",
         "rhetorical OR linked → 0 residual",
         C.grounding_residual(RHETORICAL)["undischarged"] == 0
         and C.grounding_residual(GENUINE, discharged={"b"})["undischarged"] == 0,
         "genuine + unlinked → 1 residual", C.grounding_residual(GENUINE)["undischarged"] == 1),
        ("Ν·vac: a measurement is vacuous only when NO claim tests engine capability",
         "the lone claim's fingerprint (scaffolding-only → an engine site)",
         "engine site → not vacuous", C.report(LIVE)["vacuous"] is False,
         "scaffold only → vacuous", C.report(VAC)["vacuous"] is True),
        ("frame (c): the computed quotient turns a trivial universal overlap into the genuine miss",
         "whether _universal_sites is quotiented out (report frames; grounding_residual default does not)",
         "un-quotiented → 0 (U reflects)", C.grounding_residual(UNIVFRAME)["undischarged"] == 0,
         "quotiented → 1 (miss surfaces)", C.report(UNIVFRAME)["grounding"]["undischarged"] == 1),
        ("unmeasured (d): an edge's target is pending until it is graded",
         "whether the rests-on target has a record (ungraded → pending, graded → seen)",
         "target graded → 0 unmeasured",
         C.unmeasured_edges(MEASURED_TGT, all_keys=frozenset({"x", "y"}))["unmeasured"] == 0,
         "target ungraded → 1 pending",
         C.unmeasured_edges(PENDING, all_keys=frozenset({"x", "y"}))["unmeasured"] == 1),
    ]
    for name, axis, p_lbl, p_ok, f_lbl, f_ok in pairs:
        ok = p_ok and f_ok
        fails.append(name) if not ok else None
        print(f"  {'ok ' if ok else 'XX '}{name}")
        print(f"      P (pass side): {p_lbl}")
        print(f"      F (flag side): {f_lbl}")
        print(f"      δ (min delta): {axis}\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    bad = len([b for b in ran if not b])
    if bad:
        print(f"BOUNDARIES: FAIL ({bad} of {len(ran)} behaviors drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, 7 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
