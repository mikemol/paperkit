#!/usr/bin/env python3
r"""Ρ·render·wcag-entail — the ENTAILMENT layer: a "Supports SC X" is admissible only if a warrant
PROVES the SC's requirement is met, not merely NAMES the SC.

This is the conservative core of a regulatory conformance claim, and it closes the warrant-adequacy
gap at the regulatory tier: a report row must not say "Supports 1.3.1" because a warrant carries the
number 1.3.1 — it must say so because a check demonstrably FAILS when 1.3.1 is violated.  Two
admissible forms of entailment, and nothing else earns "Supports":

  FARM  — the warrant's check ships a ⟨P,F,δ⟩ selftest whose F-arm reds on the criterion's violation.
          The F-arm IS the entailment: it proves the check catches the failure the SC forbids.  The
          selftest is machine-run here, so the entailment is verified, not asserted.
  ORACLE— the warrant's check delegates to the STANDARD'S OWN validator (veraPDF for PDF/UA).  A
          zero-failure UA verdict from the authoritative validator entails the SCs that PDF/UA's
          tagging requirements cover — the oracle is external and authoritative, so no synthetic
          F-arm is needed.

CONSERVATIVE, always: a criterion whose entailment we cannot prove is NEVER "Supports".  It is
Partially Supports (reached but not fully), Does Not Support (claimable for this content but no
entailing warrant), Not Applicable (does not apply to a static print PDF), or Not Evaluated (we
cannot yet prove it).  Under-claim by construction — a false "Supports" is a false regulatory claim.

THE PDF/UA ↔ WCAG BRIDGE (where overclaiming lives, so it is explicit and narrow): PDF/UA (ISO
14289) is a TECHNICAL TAGGING standard, not WCAG.  A UA-conformant PDF satisfies several WCAG SCs
through its tagging requirements, but "UA=0 ⟹ Supports WCAG X" is a real claim per X.  PDFUA_TO_WCAG
lists ONLY the well-documented correspondences (the tagged structure tree → info-and-relationships,
reading order, roles; a described link → link purpose; a tagged formula with MathML → non-text
content for math).  Where the correspondence is not clean, the SC is left to a direct warrant or to
Does Not Support — never inferred from UA alone.

    python3 checks/wcag_entail.py [--route docx|latex]   # the per-SC entailment verdict for a route
    python3 checks/wcag_entail.py --check                # every Supports has verified entailment
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matrix
import wcag_model as wm

# Ρ·wcag·oracle-edge — the oracle warrants' verdict records, consumed as records-as-deps (memoized):
# PAPERKIT_CONSUMED_RECORDS is set by the pk_cmd rule to space-separated `key=abspath` pairs (the
# sibling warrant ran ONCE under bazel; its verdict.json is a declared input here).  So the oracle
# entailment READS veraPDF's cached verdict rather than re-running a11y_own.py (37s) — closing the data
# edge the adversary found (a red rnd-a11y record now drops the Supports) with no redundant re-run.
_CONSUMED = {}
for _pair in os.environ.get("PAPERKIT_CONSUMED_RECORDS", "").split():
    if "=" in _pair:
        _k, _p = _pair.split("=", 1)
        _CONSUMED[_k] = _p


def _consumed_verdict(warrant: str) -> str | None:
    """The pass/fail/cannot-run verdict of a consumed sibling record, or None if not staged here (the
    check was run standalone, outside bazel — the record dep is only present in the //:hook action).
    """
    path = _CONSUMED.get(warrant)
    if not path or not Path(path).exists():
        return None
    try:
        return json.loads(Path(path).read_text()).get("verdict")
    except (OSError, ValueError):
        return None

# The route → its final delivered format (matrix format names) + PDF/UA version.
ROUTE_FINAL = {"docx": ("pdf-office", "UA-1"), "latex": ("pdf-latex", "UA-2")}

# Per-warrant ENTAILMENT: (form, cmd, scope).
#   form  — "farm" (a ⟨P,F,δ⟩ selftest proves the violation is caught, verified by running it) or
#           "oracle" (the check delegates to veraPDF, the PDF/UA validator, authoritative).
#   cmd   — the selftest command for a farm (None for an oracle).
#   scope — "full" (the warrant entails the WHOLE criterion) or "fragment" (it entails only a
#           SUB-PART of the criterion — a table-scoped check does not cover document-wide colour use;
#           a formula-alt check does not cover figures).  A FRAGMENT can only ever yield "Partially
#           Supports", NEVER "Supports": a warrant that proves a sub-part of an SC does not entail the
#           SC, and claiming it does is the naming-not-entailment gap this whole layer exists to close.
#           (The adversary caught three such fragment-as-full overclaims; scope is the fix.)
# A warrant not listed here has NO proven entailment → its cells cannot yield "Supports".
ENTAILMENT = {
    # ruler + use-of-colour prove 1.4.1 only within TABLES; 1.4.1 is document-wide → fragment.
    "rnd-ruler":     ("farm",   ["python3", "checks/ruler.py"],                    "fragment"),
    "rnd-colour":    ("farm",   ["python3", "checks/use_of_colour.py"],            "fragment"),
    # math-alt proves alt text for FORMULAS only; 1.1.1 covers all non-text (figures too) → fragment.
    "rnd-math-alt":  ("farm",   ["python3", "checks/mathalt.py", "--selftest"],    "fragment"),
    # link-alt proves a /Contents STRING exists; 2.4.4 needs the PURPOSE determinable → fragment.
    "rnd-link-alt":  ("farm",   ["python3", "checks/linkalt.py", "--selftest"],    "fragment"),
    # widen proves a wide table cell is sized to fit — it entails no WCAG criterion fully, so
    # "fragment" (defensive: it carries no WCAG tag today, but if it ever did, a column-widening check
    # must not grant a full Supports).
    "rnd-widen":     ("farm",   ["python3", "checks/widen_tables.py", "--selftest"], "fragment"),
    # the veraPDF oracle validates the WHOLE deliverable against PDF/UA → full for the SCs UA covers.
    "rnd-a11y":      ("oracle", None,                                              "full"),
    "rnd-a11y-latex":("oracle", None,                                              "full"),
    # rnd-wf / rnd-fidelity / rnd-fig-legible / rnd-fig-vector validate against the real artifact but
    # carry no synthetic F-arm and are not the UA oracle; their SCs are entailed (if at all) through
    # the PDF/UA oracle below, not through these warrants directly.  Left UNPROVEN here on purpose.
}

# PDF/UA (ISO 14289) zero-fail → the WCAG SCs its tagging requirements DOCUMENTABLY entail.  Narrow
# and conservative: only correspondences that the tagged-structure requirement directly establishes.
# A UA-conformant PDF has a tagged structure tree with correct reading order and role mapping, a
# document title and language, and (UA) alternate text on non-text content.
# Each entry: (scope, remark).  veraPDF verifies the MACHINE-checkable half of PDF/UA (the Matterhorn
# Protocol splits into machine-checkable AND human-verifiable checkpoints) — tag well-formedness, the
# PRESENCE of alt text / title / language, role-mapping validity.  It does NOT verify tag COMPLETENESS
# against the visual layout: that EVERY visual relationship or heading was actually tagged.  So a clean
# veraPDF run entails a criterion FULLY only where the criterion is a presence/absence fact veraPDF
# checks directly; where the criterion needs completeness (all relationships captured, the reading
# order CORRECT against the visual sequence), UA establishes valid MACHINERY but not the full criterion
# → "fragment" (→ Partially Supports).  The adversary drove this per-SC distinction.
PDFUA_TO_WCAG = {
    # presence/absence facts veraPDF checks directly.  1.1.1 is ROUTE-DEPENDENT (a per-route scope dict,
    # resolved by _eff_scope): veraPDF confirms /Alt is PRESENT on both routes, but presence is not
    # equivalence.  On the docx route the math /Alt is the RAW LATEX SOURCE (mathalt.py stamps
    # `\mathrm{fp}(c)\cap\mathrm{fp}(d)=\emptyset`) — a screen reader speaks it token-by-token, NOT the
    # "equivalent purpose" 1.1.1 requires → fragment.  On the latex route the math is a tagged Formula
    # with an ASSOCIATED MathML file (/AF) — recoverable structure a screen reader reads (latex.py) →
    # full.  The adversary caught the docx-route overclaim; the route split is the fix.
    "1.1.1": ({"docx": "fragment", "latex": "full"},
              "veraPDF confirms /Alt PRESENT; on docx it is the raw-LaTeX source (not an equivalent a "
              "screen reader can speak) → fragment, on latex it is recoverable MathML (/AF) → full"),
    # 2.4.2 is presence-not-completeness like 1.3.1/2.4.6: veraPDF checks a title EXISTS (+ DisplayDocTitle),
    # NOT that it DESCRIBES topic or purpose (the SC's actual bar) — a generic "Untitled" passes veraPDF
    # yet fails 2.4.2.  So UA establishes the machinery, not the criterion → fragment (the adversary's find).
    "2.4.2": ("fragment", "UA validates a title EXISTS and DisplayDocTitle, but veraPDF cannot confirm it "
                          "DESCRIBES topic/purpose (the SC's bar) — presence is not descriptiveness"),
    "3.1.1": ("full", "UA requires (and veraPDF checks) the document's primary language be set"),
    # valid tagging MACHINERY, but completeness-against-layout is a human checkpoint → fragment
    "1.3.1": ("fragment", "UA validates the structure tree, but veraPDF cannot confirm EVERY visual "
                          "relationship was tagged (completeness is a human PDF/UA checkpoint)"),
    "1.3.2": ("fragment", "UA validates a reading order exists, but not that it matches the visual "
                          "sequence (correctness is a human checkpoint)"),
    "2.4.6": ("fragment", "UA validates tagged headings, but not that EVERY visual heading was tagged "
                          "as one (completeness is a human checkpoint)"),
    # 4.1.2 Name, Role, Value is DELIBERATELY OMITTED.  UA tags STATIC structure roles, but 4.1.2
    # normatively covers the name/role/VALUE and change-notification of interactive components; the
    # paper's citation links are interactive annotations, and a tagged role does not establish their
    # name/value are exposed.  The ISO-14289 → 4.1.2 correspondence is plausible-but-incomplete on that
    # surface, so it is not claimed here (conservative — the adversary flagged it UNCERTAIN).
}
_UA_SOURCE = ("ISO 14289 (PDF/UA) tagging requirements ↔ WCAG, per the PDF/UA-WCAG correspondence "
              "(Matterhorn Protocol / PDF Association guidance); only the directly-established "
              "correspondences are claimed here")

# WCAG SCs that do NOT apply to a static, non-interactive print PDF deliverable — Not Applicable.
# Each with the reason it cannot apply (no media, no interaction, no viewport reflow, no forms).
NOT_APPLICABLE = {
    # time-based media — none in a static document
    "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5", "1.2.6", "1.2.7", "1.2.8", "1.2.9",
    "1.4.2", "1.4.7",
    # orientation / input-purpose / reflow / spacing / hover — viewport or input properties
    "1.3.4", "1.3.5", "1.4.4", "1.4.10", "1.4.12", "1.4.13",
    # keyboard / pointer / motion / timing / navigation — no interaction in a static PDF
    "2.1.1", "2.1.2", "2.1.3", "2.1.4", "2.2.1", "2.2.2", "2.2.3", "2.2.4", "2.2.5", "2.2.6",
    "2.3.1", "2.3.2", "2.3.3", "2.4.1", "2.4.3", "2.4.5", "2.4.7", "2.4.8", "2.4.11", "2.4.12", "2.4.13",
    "2.5.1", "2.5.2", "2.5.3", "2.5.4", "2.5.5", "2.5.6", "2.5.7", "2.5.8",
    # predictable / input assistance / forms — no forms or dynamic behaviour
    "3.2.1", "3.2.2", "3.2.3", "3.2.4", "3.2.5", "3.2.6",
    "3.3.1", "3.3.2", "3.3.3", "3.3.4", "3.3.5", "3.3.6", "3.3.7", "3.3.8", "3.3.9",
    # status messages — no live region
    "4.1.3",
    # language of parts — single-language document
    "3.1.2",
}


# PDF/UA clause numbers a capability may carry (matrix.py tags e.g. 7.7 math, 7.18 links) → the WCAG
# SC that clause SATISFIES.  This is a bridge like PDFUA_TO_WCAG but for a DIRECT warrant (not the UA
# oracle): a clause-tagged warrant entails its WCAG SC only to the extent the warrant proves — the
# scope in ENTAILMENT decides full vs fragment, so a link-alt warrant tagged 7.18 maps to 2.4.4 but,
# being scope="fragment", can only yield Partially Supports (proving a /Contents exists ≠ purpose).
CLAUSE_TO_WCAG = {"7.7": "1.1.1", "7.18": "2.4.4"}


# Ρ·wcag·scope-fixture — the DECLARED emit-path disclosure: every non-NA (SC, route) → the verdict the
# VPAT emits (entail(run_farm=False)).  This is the golden claim _selftest pins the DERIVED value against,
# so a data-:/dflip: mutation of a scope leaf (PDFUA_TO_WCAG / ENTAILMENT) makes derived ≠ declared and reds
# the gate — turning an atomic authored scope label into a mutation-graded def-site (the enforcement
# adversary's un-swept-scope-data finding, closed).  Authored INDEPENDENTLY of PDFUA_TO_WCAG (a wrong label
# moves only the derived side) so the check is non-vacuous.  A scope correction updates this table in the
# SAME commit (the corrected label + its pinned verdict together — no drift).
SCOPE_EMIT = {
    ("1.1.1", "docx"):  "Partially Supports",  ("1.1.1", "latex"): "Supports",
    ("1.3.1", "docx"):  "Partially Supports",  ("1.3.1", "latex"): "Partially Supports",
    ("1.3.2", "docx"):  "Partially Supports",  ("1.3.2", "latex"): "Partially Supports",
    ("1.3.3", "docx"):  "Does Not Support",    ("1.3.3", "latex"): "Does Not Support",
    ("1.3.6", "docx"):  "Does Not Support",    ("1.3.6", "latex"): "Does Not Support",
    ("1.4.1", "docx"):  "Does Not Support",    ("1.4.1", "latex"): "Partially Supports",
    ("1.4.3", "docx"):  "Does Not Support",    ("1.4.3", "latex"): "Does Not Support",
    ("1.4.5", "docx"):  "Partially Supports",  ("1.4.5", "latex"): "Does Not Support",
    ("1.4.6", "docx"):  "Does Not Support",    ("1.4.6", "latex"): "Does Not Support",
    ("1.4.8", "docx"):  "Does Not Support",    ("1.4.8", "latex"): "Does Not Support",
    ("1.4.9", "docx"):  "Does Not Support",    ("1.4.9", "latex"): "Does Not Support",
    ("1.4.11", "docx"): "Does Not Support",    ("1.4.11", "latex"): "Does Not Support",
    ("2.4.2", "docx"):  "Partially Supports",  ("2.4.2", "latex"): "Partially Supports",
    ("2.4.4", "docx"):  "Partially Supports",  ("2.4.4", "latex"): "Does Not Support",
    ("2.4.6", "docx"):  "Partially Supports",  ("2.4.6", "latex"): "Partially Supports",
    ("2.4.9", "docx"):  "Does Not Support",    ("2.4.9", "latex"): "Does Not Support",
    ("2.4.10", "docx"): "Does Not Support",    ("2.4.10", "latex"): "Does Not Support",
    ("3.1.1", "docx"):  "Supports",            ("3.1.1", "latex"): "Supports",
    ("3.1.3", "docx"):  "Does Not Support",    ("3.1.3", "latex"): "Does Not Support",
    ("3.1.4", "docx"):  "Does Not Support",    ("3.1.4", "latex"): "Does Not Support",
    ("3.1.5", "docx"):  "Does Not Support",    ("3.1.5", "latex"): "Does Not Support",
    ("3.1.6", "docx"):  "Does Not Support",    ("3.1.6", "latex"): "Does Not Support",
    ("4.1.2", "docx"):  "Does Not Support",    ("4.1.2", "latex"): "Does Not Support",
}


def _warrants_tagging(sc: str, fmt: str) -> list:
    """Warrants whose matrix cell (afforded native/post on `fmt`) tags this SC — directly via the
    capability's wcag clause, via a PDF/UA clause (CLAUSE_TO_WCAG), or via the UA oracle
    (PDFUA_TO_WCAG when the capability is pdf-ua).
    """
    out = []
    for cap, spec in matrix.CAPABILITIES.items():
        st, warrant = spec["cells"].get(fmt, (None, None))
        if st not in ("native", "post"):
            continue
        tag = spec.get("wcag", "")
        direct = (tag == sc)
        via_ua = (cap == "pdf-ua" and sc in PDFUA_TO_WCAG)
        via_clause = (CLAUSE_TO_WCAG.get(tag) == sc)
        if direct or via_ua or via_clause:
            out.append(warrant)
    return out


def _scope(warrant: str) -> str:
    """A warrant's entailment scope: 'full' (entails the whole SC) or 'fragment' (a sub-part only)."""
    e = ENTAILMENT.get(warrant)
    return e[2] if e else "fragment"


def _proven(warrant: str, run_farm: bool) -> str | None:
    """The entailment form of a warrant if PROVEN, else None (unproven) or "cannot-run" (the entailment
    could not be verified HERE — a THIRD state distinct from a failed proof).

    Ζ·tier·exit + Ρ·wcag·oracle-edge — farm and oracle both VERIFY by consuming a validator's result,
    never by asserting the warrant is named here:
      FARM   — run the ⟨P,F,δ⟩ selftest, read its TYPED exit: 0 → proven, 3 (_REFUSE) → cannot-run
               (its toolchain is absent), other nonzero → None (the F-arm FAILED, a real defect).
      ORACLE — read the sibling veraPDF warrant's CONSUMED verdict record (records-as-deps, memoized —
               veraPDF ran once in rnd-a11y): "pass" → proven, "fail" → None (a red veraPDF cannot back
               a Supports — the false-green the adversary found, closed), "cannot-run"/absent →
               cannot-run (the record was not staged — standalone run, or the oracle's toolchain absent).
    run_farm=False (report projection) returns the form unverified — the report SHOWS the verdict; check()
    is what VERIFIES it (run_farm=True), exactly as the farm SCs work.
    """
    form = ENTAILMENT.get(warrant)
    if form is None:
        return None
    kind, cmd, _scope_ = form
    if not run_farm:
        return kind
    if kind == "farm":
        rc = subprocess.run(cmd, capture_output=True,
                            cwd=Path(__file__).resolve().parent.parent).returncode
        if rc == 0:
            return "farm"           # F-arm proven → entails
        if rc == 3:
            return "cannot-run"     # toolchain absent → not verifiable here (not a fail)
        return None                 # a farm whose selftest FAILED does NOT entail (a real defect)
    if kind == "oracle":
        v = _consumed_verdict(warrant)
        if v == "pass":
            return "oracle"         # veraPDF passed (consumed record) → entails
        if v == "fail":
            return None             # veraPDF FAILED → does NOT entail (false-green closed)
        return "cannot-run"         # record not staged (standalone) or cannot-run → not verifiable here
    return None


def entail(sc: str, route: str, run_farm: bool = False) -> dict:
    """The entailment verdict for one SC on one route.  Conservative: Supports only when a proven
    warrant entails the WHOLE criterion; a warrant that proves only a FRAGMENT of the criterion yields
    Partially Supports, never Supports (proving a sub-part does not entail the SC).  Else Partially /
    Does Not Support / Not Applicable.
    """
    fmt, _ua = ROUTE_FINAL[route]
    if sc in NOT_APPLICABLE:
        return {"verdict": "Not Applicable", "warrant": None, "form": None,
                "remark": "does not apply to a static, non-interactive print PDF"}
    warrants = _warrants_tagging(sc, fmt)

    def _eff_scope(w: str) -> tuple:
        """The EFFECTIVE scope of warrant w for THIS sc, and the attesting remark.  For the veraPDF
        oracle on a UA-bridge SC, the scope is the bridge's PER-SC scope (some UA correspondences are
        full, some fragment); otherwise the warrant's own scope.
        """
        if w in ("rnd-a11y", "rnd-a11y-latex") and sc in PDFUA_TO_WCAG:
            sc_scope, why = PDFUA_TO_WCAG[sc]
            # a route-dependent SC (1.1.1) carries a {route: scope} dict; resolve it for THIS route.
            if isinstance(sc_scope, dict):
                sc_scope = sc_scope.get(route, "fragment")   # unknown route → conservative fragment
            return sc_scope, f"{w} (veraPDF): {why}"
        return _scope(w), f"{w} entails this"

    proven = [(w, _proven(w, run_farm)) for w in warrants]
    # Ζ·tier·exit — "cannot-run" is a proof STATE, not a proof: it must not read as truthy `form`
    # (which would grant Supports on an unverified proof), and it must not fall through to "Does Not
    # Support" (asserting a gap we did NOT verify absent is the OPPOSITE overclaim).  A criterion whose
    # only would-be proof could not run is Not Evaluated.
    def _is_proof(form: str | None) -> bool:
        return form in ("farm", "oracle")
    # a proven, FULL-scope warrant → Supports.  Scan for one before settling for a fragment.
    for w, form in proven:
        if _is_proof(form) and _eff_scope(w)[0] == "full":
            return {"verdict": "Supports", "warrant": w, "form": form,
                    "remark": f"{_eff_scope(w)[1]} ({form})"}
    # a proven FRAGMENT-scope warrant → Partially Supports (it proves a sub-part, not the whole SC).
    for w, form in proven:
        if _is_proof(form) and _eff_scope(w)[0] == "fragment":
            return {"verdict": "Partially Supports", "warrant": w, "form": form,
                    "remark": f"{_eff_scope(w)[1]} — only part of the criterion is proven ({form}), "
                              f"not the whole; a full claim needs coverage the tool cannot confirm"}
    # tagged but no proven entailment (a "post"/"excepted" cell present but unproven) → Partially.
    if warrants:
        return {"verdict": "Partially Supports", "warrant": warrants[0], "form": None,
                "remark": f"{warrants[0]} addresses this but its entailment is not proven for a full claim"}
    # the only would-be entailment could not RUN here (toolchain absent / record not staged) → Not
    # Evaluated, conservatively: neither claim Supports (unverified) nor a gap (not verified absent).
    if any(form == "cannot-run" for _w, form in proven):
        w = next(w for w, form in proven if form == "cannot-run")
        return {"verdict": "Not Evaluated", "warrant": w, "form": "cannot-run",
                "remark": f"{w}'s entailment could not be verified here — not claimed either way "
                          f"(conservative under a missing validator or an unstaged consumed record)"}
    # claimable for this content but no entailing warrant → Does Not Support (honest gap)
    return {"verdict": "Does Not Support", "warrant": None, "form": None,
            "remark": "no warrant entails this criterion for this deliverable (a known gap)"}


def check() -> tuple[bool, list[str], list[str]]:
    """Every "Supports" a route yields must resolve to a warrant with PROVEN entailment.  The farm
    warrants' selftests are RUN; the oracle warrants' CONSUMED veraPDF records are read (Ρ·wcag·oracle-
    edge — a Supports backed by the oracle is admissible only when veraPDF actually PASSED, read from
    rnd-a11y's memoized verdict record, not asserted by registry membership).  The regulatory soundness
    gate: no Supports without proof.  Returns (ok, problems, cannot_run): Ζ·tier·exit — a validator that
    could not run here (a farm selftest exiting 3, or an oracle record that is fail-absent/cannot-run) is
    NOT a problem — it is recorded separately so the gate reports CANNOT-RUN (exit 3), not a false
    failure, on a toolchain-less box or a standalone (out-of-bazel) run.
    """
    problems, cannot_run = [], []
    # the entailment registry must name real warrants (in warrants.bib) and real check commands.
    # (this half is PURE — no toolchain — the sandbox-gradeable core; see Ρ·wcag·entail-sweep.)
    bib = (Path(__file__).resolve().parent.parent / "warrants.bib").read_text()
    for w, (kind, cmd, _sc) in ENTAILMENT.items():
        if f"@misc{{{w}," not in bib and f"@misc{{{w} ," not in bib:
            problems.append(f"entailment names warrant {w!r} absent from warrants.bib")
        if kind not in ("farm", "oracle"):
            problems.append(f"{w}: entailment form {kind!r} is not farm/oracle")
    # every farm selftest / oracle record must not FAIL (a Supports backed by a red F-arm or a red
    # veraPDF is a false claim) — UNLESS it could not run here (rc=3 / cannot-run), recorded separately.
    for w, (kind, cmd, _sc) in ENTAILMENT.items():
        form = _proven(w, run_farm=True)
        what = "⟨P,F,δ⟩ selftest" if kind == "farm" else "veraPDF validator (consumed record)"
        if form == "cannot-run":
            cannot_run.append(f"{w}: its {what} CANNOT RUN here (toolchain absent / record not staged)")
        elif form is None:                              # ran-and-failed (a red validator)
            problems.append(f"{w}: its {what} FAILS — cannot back a Supports")
    # every SC a route marks Supports must, on re-derivation with proofs RUN, still be Supports — UNLESS
    # its would-be full-scope proof CANNOT RUN (toolchain absent / consumed record not staged), which
    # legitimately downgrades it (to Not Evaluated, or Partially if a fragment warrant remains).  A
    # downgrade is a PROBLEM only when the backing proof genuinely FAILED (_proven → None), not when it
    # could not run (_proven → cannot-run).  Ζ·tier·exit: cannot-run is not a false Supports.
    for route in ROUTE_FINAL:
        for sc in wm.SC:
            v = entail(sc, route, run_farm=False)
            if v["verdict"] == "Supports":
                backer = v["warrant"]
                vr = entail(sc, route, run_farm=True)
                if vr["verdict"] == "Supports":
                    continue
                if _proven(backer, run_farm=True) == "cannot-run":
                    continue                            # its proof could not run — an honest downgrade
                problems.append(f"{sc} × {route}: Supports without a passing entailment proof")
    return (not problems), problems, cannot_run


def _selftest() -> int:
    """⟨P, F, δ⟩ for Ρ·wcag·oracle-edge — the oracle Supports is admissible ONLY when the CONSUMED
    veraPDF record reads pass; a fail record drops it (the false-green the adversary found, closed).
    Stubs _CONSUMED in-memory (no bazel, no 37s veraPDF), so it gates the record-consumption logic
    cheaply.  δ = the consumed record's verdict (pass vs fail) flips 3.1.1 (a full UA-bridge SC — /Lang presence IS its bar) between Supports and not.
    """
    import tempfile
    fails = []

    def _with_record(verdict: str, sc: str = "3.1.1", route: str = "docx") -> str:
        with tempfile.TemporaryDirectory() as d:
            for w in ("rnd-a11y", "rnd-a11y-latex"):
                p = Path(d) / f"{w}.verdict.json"
                p.write_text(f'{{"verb":"cmd","verdict":"{verdict}"}}')
                _CONSUMED[w] = str(p)
            try:
                return entail(sc, route, run_farm=True)["verdict"]
            finally:
                for w in ("rnd-a11y", "rnd-a11y-latex"):
                    _CONSUMED.pop(w, None)

    def check(desc, cond):
        print(f"  {'ok ' if cond else 'XX '}{desc}")
        if not cond:
            fails.append(desc)

    print("Ρ·wcag·oracle-edge — the oracle Supports is proof-backed by the consumed record\n")
    # P: a consumed record that reads PASS backs a full Supports (3.1.1 = /Lang presence, a full UA-bridge SC).
    check("consumed record = pass → 3.1.1 Supports (reads the cached veraPDF, no re-run)",
          _with_record("pass") == "Supports")
    # F: a consumed record that reads FAIL drops the Supports — the adversary's counterexample, closed.
    check("consumed record = fail → 3.1.1 NOT Supports (a red veraPDF cannot back a Supports)",
          _with_record("fail") != "Supports")
    # cannot-run: an absent/cannot-run record is Not-Evaluated-conservative, never a false Supports.
    check("consumed record = cannot-run → 3.1.1 NOT Supports (unverified, conservative)",
          _with_record("cannot-run") != "Supports")
    # standalone (no record staged) → the oracle is cannot-run, never a false-asserted Supports.
    check("no consumed record staged → 3.1.1 NOT Supports (standalone cannot assert the oracle)",
          entail("3.1.1", "docx", run_farm=True)["verdict"] != "Supports")

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    P, F = _with_record("pass"), _with_record("fail")
    ok = P == "Supports" and F != "Supports"
    fails.append("record-verdict-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}the consumed record's verdict flips 3.1.1 Supports on/off")
    print("      P (pass side): consumed rnd-a11y record reads pass — 3.1.1 Supports (veraPDF passed)")
    print("      F (flag side): consumed rnd-a11y record reads fail — 3.1.1 not Supports (veraPDF failed)")
    print("      δ (min delta): the single verdict field pass→fail in the consumed record\n")

    # ── Ρ·wcag·scope-fixture ──────────────────────────────────────────────────────────────────────
    # The oracle-edge fixture above drives ONE SC (3.1.1 docx), so it reaches only the record-consumption
    # DISPATCH — never the SCOPE DATA (PDFUA_TO_WCAG / ENTAILMENT scope labels) that decides WHICH SC gets
    # Supports.  A wrong scope label (the reproduced 1.1.1 docx fragment→full overclaim) slips straight
    # through it (the enforcement adversary's finding).  A scope label is ATOMIC AUTHORED INPUT — a reading
    # of WCAG normative text, not derivable — so this fixture does NOT verify a label is RIGHT.  It gives the
    # two guarantees that ARE achievable, and that the data atom (data-:/dflip:) makes gradable:
    #   (1) BEHAVIORAL — the label is not inert: SCOPE_EMIT is the DECLARED emit-path disclosure (authored
    #       from the normative reading); entail(run_farm=False) is the DERIVED value read THROUGH the mutable
    #       PDFUA_TO_WCAG.  A data-: drop or dflip: perturb of a scope leaf makes derived ≠ declared → this
    #       reds → the label is a mutation-graded def-site, not un-swept data (fix-#3's gap, closed).
    #   (2) NO SILENT DISCONNECT — the verdict a regulator READS (emit path, run_farm=False) is pinned, so a
    #       future refactor cannot decouple the emitted VPAT from the entailment logic without reddening here.
    # NON-VACUOUS by construction: SCOPE_EMIT is authored independently of PDFUA_TO_WCAG (a golden-file test,
    # like wcag_model's completeness arithmetic), so a wrong label moves the DERIVED side only → mismatch.
    # A (scope==full)==(Supports) invariant would be VACUOUS (both sides read the same dict) — verified.
    print("\nΡ·wcag·scope-fixture — every disclosed verdict pinned; a scope-label mutation flips one\n")
    scope_fails = []
    # COMPLETENESS (Ζ·bnd·toplevel / guard-must-not-copy): the CONTENT loop below iterates SCOPE_EMIT
    # itself, so a data-: DROP of a golden entry would just SHRINK the loop — the dropped verdict would
    # vanish silently rather than mismatch (the enforcement adversary's finding).  Pin the DOMAIN first,
    # against an INDEPENDENT source (wm.SC minus NOT_APPLICABLE, both routes — NOT SCOPE_EMIT), so a drop
    # breaks domain-equality here even though the content loop can't see it.  This is the completeness
    # arithmetic wcag_model uses, applied to the golden table's key set: the guard must not derive its
    # own domain from the thing it guards.
    expected_domain = {(sc, route) for sc in (set(wm.SC) - NOT_APPLICABLE) for route in ("docx", "latex")}
    got_domain = set(SCOPE_EMIT)
    missing = sorted(expected_domain - got_domain)
    extra = sorted(got_domain - expected_domain)
    if missing:
        scope_fails.append(f"SCOPE_EMIT is MISSING {len(missing)} disclosed (SC×route) entries: {missing[:6]}")
        print(f"  XX SCOPE_EMIT domain incomplete — {len(missing)} non-NA (SC×route) unpinned: {missing[:6]}")
    if extra:
        scope_fails.append(f"SCOPE_EMIT pins {len(extra)} (SC×route) that are Not Applicable: {extra[:6]}")
        print(f"  XX SCOPE_EMIT pins {len(extra)} NA (SC×route): {extra[:6]}")
    if not missing and not extra:
        print(f"  ok SCOPE_EMIT domain == the {len(expected_domain)} non-NA (SC×route) — independently derived "
              f"from wm.SC − NOT_APPLICABLE (a drop cannot hide)")
    for (sc, route), expected in sorted(SCOPE_EMIT.items()):
        got = entail(sc, route, run_farm=False)["verdict"]
        ok = got == expected
        if not ok:
            scope_fails.append(f"{sc}×{route}: emit={got} ≠ declared={expected}")
        # print only mismatches + a per-route roll-up (full enumeration is the committed SCOPE_EMIT)
        if not ok:
            print(f"  XX {sc:8} {route:6} emit={got!r} declared={expected!r}")
    print(f"  {'ok ' if not scope_fails else 'XX '}{len(SCOPE_EMIT)} disclosed (SC×route) verdicts match "
          f"the declared emit table ({len(scope_fails)} drifted)")
    fails.extend(scope_fails)

    if fails:
        print(f"SELFTEST: FAIL ({len(fails)} drifted)")
        return 1
    print("SELFTEST: PASS")
    return 0


def summary(route: str, run_farm: bool = False) -> dict:
    tally = {}
    for sc in wm.SC:
        v = entail(sc, route, run_farm)["verdict"]
        tally[v] = tally.get(v, 0) + 1
    return tally


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    if "--check" in argv:
        ok, problems, cannot_run = check()
        if not ok:
            for p in problems:
                print(f"wcag-entail --check: {p}", file=sys.stderr)
            return 1                                    # a real defect (a red validator) — RAN-AND-FAILED
        if cannot_run:                                  # Ζ·tier·exit — no defect, but a validator could not run
            for c in cannot_run:
                print(f"wcag-entail --check: {c}", file=sys.stderr)
            print("wcag-entail --check: registry is sound; some validators CANNOT RUN here (toolchain "
                  "absent / consumed record not staged — a standalone run) — those SCs disclose Not "
                  "Evaluated, not Supports (conservative).", file=sys.stderr)
            return 3                                    # cannot-run, not a failure
        parts = []
        for route in ROUTE_FINAL:
            t = summary(route, run_farm=False)
            parts.append(f"{route} {ROUTE_FINAL[route][1]}: " +
                         ", ".join(f"{t.get(v,0)} {v}" for v in
                                   ("Supports", "Partially Supports", "Does Not Support",
                                    "Not Applicable", "Not Evaluated") if t.get(v)))
        print("wcag-entail --check: every Supports has proven entailment (farm selftests pass, "
              "oracle = consumed veraPDF record); conservative — no Supports without proof.")
        for p in parts:
            print("  " + p)
        return 0
    route = argv[argv.index("--route") + 1] if "--route" in argv else "latex"
    print(f"WCAG 2.2 entailment verdicts — {route} route ({ROUTE_FINAL[route][1]}):\n")
    for sc in sorted(wm.SC, key=lambda s: [int(x) for x in s.split(".")]):
        v = entail(sc, route, run_farm=False)
        if v["verdict"] not in ("Not Applicable",):
            print(f"  {sc:8} {wm.SC[sc][0]:40.40} {wm.level(sc):3} {v['verdict']:20} {v['remark']}")
    print(f"\n  summary: {summary(route)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
