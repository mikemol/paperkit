#!/usr/bin/env python3
"""paperkit.grade — the GRADE LADDER + interpretation (Μ·grade).

The PURE half of the Δ grader: the falsifiability rungs, the clamp/strength/corroboration
orders, and how a measured flip-set becomes a grade.  Separated from grader.py (the SWEEP —
sandbox, AST mutation, sensitivity) so the CALCULATION (the expensive measurement) and the
INTERPRETATION (this cheap reading over it) are distinct modules — Ζ·calc·interp in code.

A LEAF: pure data + one pure function, no engine imports.  So a READING of a grade
(tools/read_grade.py) imports the ladder, not the sweep; and a claim about the ladder
exercises only this, not the whole grader.
"""
from __future__ import annotations

from pathlib import Path

STRENGTH = {"vacuous": 0, "existence": 1, "indeterminate": 1, "behavioral": 2, "imported": 3}
ORDER = {"existence": 1, "behavioral": 2}  # valid --min-strength thresholds

# Total order for clamping (effective grade = min over self + premises).  Conservative:
# vacuous < indeterminate (runs, falsifiability unproven) < existence (presence proven)
# < behavioral (falsifiability proven) < imported (Ξ·seam: verified whole in a separately-
# gated sibling — a delegated premise never weakens what rests on it, so it ranks at top).
RANK_C = {"broken": -1, "vacuous": 0, "indeterminate": 1, "existence": 2, "behavioral": 3,
          "imported": 4}
GRADE_C = {v: k for k, v in RANK_C.items()}

# Corroboration — a SECOND, ORTHOGONAL evidence axis (Ε·agree·grade), NOT another rung on
# RANK_C above.  The grade above asks "does a mutation flip this check" (FALSIFIABILITY);
# this asks "is the verdict confirmed by INDEPENDENT producers" (CORROBORATION).  A check's
# strength is the PAIR (falsifiability, corroboration), never one collapsed scalar: a lone
# behavioral witness and a behaviorally-agreeing oracle share a GRADE but differ HERE.  An
# agree: verdict that passes with ≥2 textually-distinct producers is `independent`; one
# witness — or identical producers concurring trivially — is `single`.  single < independent.
CORRO_C = {"single": 0, "independent": 1}

# Decision-coverage — a THIRD, ORTHOGONAL axis (Μ·sweep·atom), again NOT a rung on RANK_C.  The
# grade asks "does a mutation flip this check" (FALSIFIABILITY, over the raise-monotone branch:/def:
# atom); this asks "of the decisions a check REACHES, how many does it ASSERT on".  A finer,
# NON-monotone flip: cell inverts one condition — and is read soundly only when BOTH sibling arms are
# GENUINELY reached (proven per-arm by flip_one, not by the group-correlated sens set): with both
# outcomes provably exercised, an inversion that does NOT flip the check is an UNASSERTED decision (the
# check runs both arms but is indifferent to which selected them), with no fixture-coincidence left to
# confuse it.  `unasserted` < `asserted`; it NEVER lowers a grade (incompleteness is not a weaker rung,
# the same discipline as corroboration and content_sensitive), only names the gap.  Absent field ⇒ the
# check has no reached-both-arms decision it fails to assert (the common case).
DECISIONS_C = {"unasserted": 0, "asserted": 1}

# Resolution — a FOURTH, ORTHOGONAL axis (Ζ·pi·unresolved), again NOT a rung on RANK_C.  The
# grade asks "how strong is this claim's evidence"; this asks "did the unfold that produced it
# actually REACH everything it delegates to".  An unresolved delegation is a TRUNCATED
# observation, not a weaker one: the owner may be strong or weak and we do not hold the record
# that would say.  So, on the same discipline as corroboration and decision-coverage, it NEVER
# lowers a grade — it NAMES THE GAP.  `truncated` < `resolved`.
#
# The distinction it preserves is the one a bare grade cannot carry: `imported` sits at the TOP
# of RANK_C precisely so a RESOLVED delegation to a healthy owner imposes no clamp — which makes
# "resolved, imposed nothing" and "never resolved, imposed nothing" numerically identical while
# meaning opposite things.  Two peers named the same failure independently: substrate inverted
# five zero-tolerance gates by reading an EMPTY baseline as ABSENT, and linux-sources' reader
# says "UNAVAILABLE at this version — NOT a claim it does not exist" while imposing no
# constraint.  paperkit's own verdicts are tristate for exactly this reason (a check that cannot
# be evaluated returns 2, never 0 and never 1); the unfold needed the same third state.
RESOLUTION_C = {"truncated": 0, "resolved": 1}

# Ζ·broken·offaxis — the FOURTH instance of the same distinction, and the one the engine was
# still losing.  `broken` is not a weak rung: `_grade_from_sens` emits it on `not baseline`,
# i.e. the check never ESTABLISHED anything.  But a baseline can fail for two categorically
# different reasons, and the resolver already separates them — a FAIL ("the claim is false")
# from an UNAVAILABLE ("I could not REACH the thing", exit 3, the tristate routes.py's protocol
# calls not-mine).  `grader.sensitivity` read `.passed`, a bool, and both arrived as False.  So
# a check killed by its memory cap graded `broken` with "repo is not green" — about a green
# repo.  Measured: that exact false statement, twice, on 2026-08-26.
#
# The fix is NOT a rung below `broken` (the ladder is a positive cone: `vacuous` is the unit and
# nothing sits under a real verdict) and NOT a rank for a non-verdict.  It is this axis, on the
# same discipline as the three above: it NEVER lowers a grade, it names WHY no grade was
# established.  `unreachable` is not worse than `refuted` — it is a different kind of statement.
BASELINE_C = {"unreachable": 0, "refuted": 1, "established": 2}


# Ζ·ladder — the two DERIVATIONS every consumer needs, so none re-declares the rungs.  A ladder
# re-listed downstream drifts silently and in the WORST direction: a display order that omits a
# rung SILENTLY DROPS claims from its own total (report/gen.py counted 79 of 80), and an adequacy
# gate written as a BLACKLIST of failing grades PASSES any rung added after it was written — the
# gate fails open, which is the one direction a gate must never fail.  Both are stated here as a
# function of RANK_C instead, so a new rung reaches every consumer by being added ONCE, above.

def rungs(descending: bool = True) -> list:
    """Every grade the ladder defines, in rank order — the display order for any summary.  Listing
    rungs by hand is how a report comes to omit one and quietly under-count its own population."""
    return sorted(RANK_C, key=lambda g: RANK_C[g], reverse=descending)


def below(floor: str) -> list:
    """The grades that FAIL a `floor` — derived, so the adequacy gate fails CLOSED.  Stated as a
    blacklist it would admit every future rung by default; stated as `rank < rank(floor)` a new
    rung is judged the moment it exists.  `floor` must be a defined rung (KeyError if it is not —
    a typo'd floor must not silently grade everything green)."""
    return [g for g in rungs(descending=False) if RANK_C[g] < RANK_C[floor]]


def _grade_from_sens(baseline: bool, sens: list, reachable: bool = True) -> dict:
    """The cmd/custom verdict as a pure function of (baseline-passes, flip-set) — shared
    by the per-check path (grade_check → sensitivity) and the flat work-queue grader.

    Ζ·broken·offaxis — `reachable` carries the resolver's tristate the last hop.  A caller that
    reads `.passed` collapses UNAVAILABLE onto FAIL and both arrive here as `baseline=False`;
    passing `reachable=False` says WHICH, so the record stops asserting "repo is not green"
    about a repo whose check merely could not run.  The GRADE is unchanged either way — the
    axis names the gap, it does not move the rung (see BASELINE_C)."""
    if not baseline:
        return {"grade": "broken", "tests": [],
                "baseline": "unreachable" if not reachable else "refuted",
                "why": ("check could not be REACHED in a pristine sandbox — its toolchain or a "
                        "resource it needs was unavailable, so nothing was established about "
                        "the claim (this is NOT a statement that the repo is red)")
                       if not reachable else
                       "check does not pass in a pristine sandbox — repo is not green",
                "not_higher": "—", "not_lower": "—"}
    if sens:
        return {"grade": "behavioral", "tests": sens, "baseline": "established",
                "why": f"falsifiable — corrupting {len(sens)} input(s) flips it red",
                "not_higher": "behavioral is the top tier; a proof-grade (total, postulate-free witness) tier is not yet defined",
                "not_lower": f"not indeterminate/vacuous: a mutation DOES flip it (sensitive to {len(sens)} input(s))"}
    return {"grade": "indeterminate", "tests": [],
            "why": "no generic mutation flips it — vacuous OR a negative-assertion check; needs a targeted counter-fixture (Π)",
            "not_higher": "to rise: a targeted counter-fixture (a positive mutation) would prove it behavioral",
            "not_lower": "not provably vacuous: it runs a cmd:, not a presupposed file:"}


def mark_content_sensitive(records: list, content: set) -> list:
    """Mark each behavioral check content_sensitive iff a flipped test file is the document's
    OWN content (bib/rubric/out), not merely config/engine: a behavioral check sensitive only
    to config or the engine can-fail by CRASH but does not test the document's content.  A pure
    reading over the grade records + the document's content-file names."""
    for r in records:
        if r["grade"] == "behavioral":
            r["content_sensitive"] = any(Path(t).name in content for t in r["tests"])
    return records


def clamp(records: list, owner_grades: dict | None = None,
          keys: set | None = None) -> list:
    """Effective grade — clamp by entailment: a claim is no better grounded than the weakest
    premise it (transitively) depends on along rests-on.  Annotates each record with
    effective_grade, clamp (rungs dropped from the self-contained grade), and clamped_by (the
    premise that pins it).  A pure reading over the grade records + the RANK ladder.

    Λ·pi·carry — `owner_grades` optionally supplies the OTHER SIDE of a delegation edge:
    {(owner, claim): grade} from the owning project's own grade records.  A record carrying
    `delegates_to` then clamps against the owner's REAL grade instead of the flat `imported`
    tag, so a weak imported premise weakens what rests on it — transitively, since the owner's
    grade is itself already clamped in its own project.

    Why this is a parameter and not a lookup: certificates are BUILD ARTIFACTS.  Re-deriving an
    owner's grade in the importing view is the cost bomb the delegation exists to avoid, and it
    is structurally blind besides (the owner's witness is outside this project's mutation
    surface).  So the caller supplies what it holds; absent it, the ladder behaves exactly as
    before and `imported` stays at the top.  The rank is the DEFAULT for an unresolved edge,
    never a claim about delegated strength."""
    rby = {r["key"]: r for r in records}
    og = owner_grades or {}
    effc: dict = {}

    def _delegated(r):
        """The owner's EFFECTIVE rank for a delegation edge, or None if we do not hold it.

        A grade is TWO-DIMENSIONAL — (self, effective) — and an owner entry may carry the pair
        as a dict or, for a caller that holds only one number, a bare grade string.  The bound
        is the EFFECTIVE component: what the owner's own project already clamped it to.  Reading
        `grade` here instead would truncate the unfold at the boundary, letting an owner whose
        premise is weak report strong upward.

        Ζ·pi·unresolved — an edge we cannot resolve is marked UNRESOLVED, a third state distinct
        from both "clamps" and "does not clamp".  "No constraint recorded" and "constraint
        recorded as: none" render identically once collapsed, and that collapse has already been
        paid for elsewhere in this ecosystem (substrate inverted five zero-tolerance gates by
        reading an EMPTY baseline as ABSENT).  Paperkit's own tristate verdict exists for the
        same reason: a check that cannot be evaluated returns 2, never 0 and never 1, because a
        finding nobody can check must not read as either closed or open.  The same argument
        applies one level up, to an unfold that stopped early."""
        d = r.get("delegates_to")
        if not d:
            return None
        g = og.get((d.get("owner"), d.get("claim")))
        if g is None:
            r["unresolved"] = [f"{d.get('owner')}#{d.get('claim')}"]
            return None
        if isinstance(g, dict):
            r["delegated"] = g                   # carry the owner's pair for the reader
            g = g.get("effective_grade", g.get("grade"))
        else:
            r["delegated"] = {"grade": g, "effective_grade": g, "clamped_by": None}
        return RANK_C.get(g) if g is not None else None

    def eff(k, stack=()):
        """(rank, pin, path) — the effective rank, the premise that pins it, and the WHOLE
        chain from here to that premise.

        Λ·pi·path — the pin alone is the LAST step; the path is the prefix.  An importer asking
        "do I distrust this witness or chase its premise" is answerable from the chain and only
        sometimes from the final name (substrate's `take n` vs its last CF digit).  Carrying it
        costs one list per claim and turns a dead-end pin into a followable trace."""
        if k in effc:
            return effc[k]
        r = rby.get(k)
        if r is None:
            # Ζ·rests·unresolved — "not in scope" is TWO cases and this constant is only right
            # for one.  A key with no record is either genuinely outside this argument (another
            # project's key: imposing nothing is correct) or IN the argument and simply never
            # graded — excluded by tier/nonmechanical, or a grading that did not finish.  The
            # second is an unfold that stopped, and reading it as `behavioral` does not merely
            # fail to clamp: rung 3 of 5 ASSERTS the premise is falsifiable, and verify_hop's
            # monotonicity bound then certifies against a value nothing measured.
            #
            # `keys` (the bib's own key set) is what tells them apart, so the caller supplies it;
            # absent, behaviour is exactly as before.  The truncation is surfaced through the
            # EXISTING axis rather than a new one: RESOLUTION_C already means "the unfold did not
            # reach everything", _bracket already widens on `unresolved`, and Λ·reduce says use
            # the structure that is there.  Same treatment the delegation seam already gets.
            return (RANK_C["behavioral"], None, [])   # not in scope: impose no constraint
        best, by, path = RANK_C.get(r["grade"], 0), None, []
        de = _delegated(r)                           # resolve the delegation edge, if we can
        if de is not None and de < best:
            d = r["delegates_to"]
            owner = f"{d['owner']}#{d['claim']}"
            best, by = de, owner
            # the owner's own pin continues the chain across the boundary
            og_pin = (r.get("delegated") or {}).get("clamped_by")
            path = [owner] + ([og_pin] if og_pin else [])
        for d in r.get("rests-on", []):              # clamp over GROUNDING edges
            # Ζ·rests·unresolved — a premise with NO record is skipped here, and silence about
            # that is indistinguishable from an edge that resolved to no constraint.  Two cases
            # hide in the skip: genuinely outside this argument (another project's key — imposing
            # nothing is right), or IN the argument and never graded (excluded by tier/
            # nonmechanical, or a grading that did not finish).  The second is an unfold that
            # STOPPED, and reading it as no-constraint lets `behavioral` — rung 3 of 5 — stand as
            # if measured, with verify_hop's monotonicity bound then certifying against it.
            # `keys` (the bib's own key set) separates them; absent, behaviour is exactly as
            # before.  Surfaced through the EXISTING axis: RESOLUTION_C already means "the unfold
            # did not reach everything", and _bracket already widens on `unresolved` (Λ·reduce —
            # the delegation seam gets this treatment already; grounding edges did not).
            if d not in rby and keys is not None and d in keys:
                r.setdefault("unresolved", []).append(d)
            if d in rby and d not in stack and d != k:
                dg, _, dpath = eff(d, stack + (k,))
                if dg < best:
                    best, by, path = dg, d, [d] + dpath
        effc[k] = (best, by, path)
        return effc[k]

    for r in records:
        e, by, path = eff(r["key"])
        r["effective_grade"] = GRADE_C[e]
        r["clamp"] = RANK_C.get(r["grade"], 0) - e
        r["clamped_by"] = by
        r["clamp_path"] = path                   # Λ·pi·path — the prefix, not just the last step
        # Ζ·pi·unresolved — surface the truncation as a VALUE.  An edge we could not resolve
        # imposed no constraint, and silence about that is indistinguishable from an edge that
        # resolved to no constraint.  Both peers independently named this as the first move.
        r.setdefault("unresolved", [])
        # the axis VALUE, not merely the evidence for it — a consumer reads `resolution`, the
        # way it reads `corroboration`, without having to know that [] means "resolved".
        r["resolution"] = "truncated" if r["unresolved"] else "resolved"
    # resolution is TRANSITIVE, like the clamp: a claim resting on a truncated premise has a
    # truncated reading too, even though its OWN edges all resolved.  Reporting it as `resolved`
    # would say "I unfolded everything beneath this" of a subtree that stops short — the same
    # silent-truncation error one level up.  (The interval already widens correctly; this makes
    # the axis agree with it.)
    def _reaches_truncation(k, stack=()):
        """Whether ANY claim in k's grounding cone has an unresolved edge.

        Walked over rests-on rather than read off `clamp_path`: the path records what CLAMPED,
        and a truncated premise that clamps nothing leaves it empty — precisely the case this
        must catch."""
        r = rby.get(k)
        if r is None or k in stack:
            return False
        if r.get("unresolved"):
            return True
        return any(_reaches_truncation(y, stack + (k,)) for y in r.get("rests-on", []))

    for r in records:
        if r["resolution"] == "resolved" and _reaches_truncation(r["key"]):
            r["resolution"] = "truncated"
    return _bracket(records, rby, og)


def verify_hop(record: dict, premises: dict, owner_grades: dict | None = None) -> tuple:
    """Λ·pi·fold — recompute ONE hop's effective grade from its own data plus its premises'
    RESULTS.  Returns (ok, expected, why).

    A chain that merely RECORDS its steps asks the reader to trust the computation that produced
    it.  A chain that CERTIFIES them gives the reader a per-hop obligation they can discharge
    alone: given this hop's self grade, its delegation, and the effective grades of the claims
    directly beneath it, this function reproduces the hop — consulting nothing above it.  That
    is the whole content of "verifiable without trusting the links above".

    The step is total and the fold over it is unique: any function agreeing on the base case (a
    claim with no premises: effective = self) and on this step IS this fold, so an independent
    reimplementation is forced to agree.  That is what makes the chain a chain rather than a log.

    THE BOUND THAT MAKES A HOP CHECKABLE AT ALL.  substrate's `recon-bounded-unique` pins a
    wedge only under `r < b` — without the bound, two different steps reconstruct the same value
    and the chain records without certifying.  The analogue here is that the clamp is a MIN, so
    `eff(k) <= eff(d)` for every premise d: a hop can only ever LOWER, never raise, and by no
    more than its weakest premise.  A recorded hop violating that monotonicity is detectable
    locally, with no reference to the rest of the chain."""
    self_rank = RANK_C.get(record.get("grade"), 0)
    best, why = self_rank, "self"
    og = owner_grades or {}
    d = record.get("delegates_to")
    if d:
        g = og.get((d.get("owner"), d.get("claim")))
        if isinstance(g, dict):
            g = g.get("effective_grade", g.get("grade"))
        if g is not None and RANK_C.get(g, 0) < best:
            best, why = RANK_C[g], f"{d['owner']}#{d['claim']}"
    for k, pg in premises.items():
        if RANK_C.get(pg, 0) < best:
            best, why = RANK_C[pg], k
    expected = GRADE_C[best]
    got = record.get("effective_grade")
    if got != expected:
        return (False, expected, f"hop recomputes to {expected} (via {why}), record says {got}")
    # the bound: a hop may only LOWER, and never below its weakest premise
    for k, pg in premises.items():
        if RANK_C.get(got, 0) > RANK_C.get(pg, 0):
            return (False, expected,
                    f"monotonicity violated: {got} exceeds premise {k}'s {pg}")
    return (True, expected, why)


def _bracket(records: list, rby: dict, og: dict) -> list:
    """Ζ·pi·interval — the ADMISSIBLE INTERVAL an unresolved unfold leaves behind.

    `effective_grade` is the OPTIMISTIC endpoint: an unresolved delegation imposes no
    constraint, so the reading assumes the best about what it never looked at.  That is the
    unsound direction on its own — a truncation that silently reads as strength.

    The fix is not a bound on the EDGE (an error bound on a step you should not take licenses
    taking it — linux-sources retracted exactly that as a method: "an error bound on an
    unreachable state is not a bound, it is an invitation").  It is a PAIR of bounds on the
    RESULT, computed by the same operator over the same ladder:

        effective_min   every unresolved premise at the ladder's FLOOR   (pessimistic)
        effective_max   every unresolved premise imposing nothing        (= effective_grade)

    The true grade lies inside, and WHERE it lies is exactly the unresolved edge.  The interval's
    WIDTH is the cost of not having unfolded — in the same units as the answer, monotone, and
    shrinking to zero as edges resolve.  A truncation stops vanishing and starts widening a
    bracket you can see.

    It also separates the two owner shapes a single number cannot: an owner whose WITNESS is weak
    has both endpoints low; an owner whose PREMISE is unresolved has a WIDE interval.  Different
    shapes, not one collapsed scalar."""
    FLOOR = min(RANK_C.values())
    pess: dict = {}

    def lo(k, stack=()):
        if k in pess:
            return pess[k]
        r = rby.get(k)
        if r is None:
            return RANK_C["behavioral"]           # not in scope: impose no constraint (as above)
        best = RANK_C.get(r["grade"], 0)
        if r.get("unresolved"):                   # the pessimistic reading of a truncation
            best = min(best, FLOOR)
        d = r.get("delegates_to")
        if d and not r.get("unresolved"):
            g = (r.get("delegated") or {}).get("effective_grade")
            if g is not None:
                best = min(best, RANK_C.get(g, 0))
        for y in r.get("rests-on", []):
            if y in rby and y not in stack and y != k:
                best = min(best, lo(y, stack + (k,)))
        pess[k] = best
        return best

    for r in records:
        e_lo = lo(r["key"])
        r["effective_min"] = GRADE_C[e_lo]
        r["effective_max"] = r["effective_grade"]
        r["interval_width"] = RANK_C[r["effective_max"]] - e_lo
    return records
