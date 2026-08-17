#!/usr/bin/env python3
r"""Ρ·render·wcag-model — the accessibility standards as sourced, versioned DATA.

The foundation of a regulatory conformance claim: the standards themselves, modeled as owned data
with provenance, so a downstream conformance report (a VPAT/ACR projection) rests on a verified model
of the law rather than a hand-guessed one.  Three standards, three DIFFERENT WCAG baselines — the
version skew is load-bearing and modeled explicitly, because a criterion in scope for one standard is
out of scope for another BY VERSION, not by choice, and a conformance claim must say so:

  WCAG 2.2            (W3C Recommendation, 2024-12-12) — 87 success criteria, the report's own baseline.
  Revised Section 508 (US, 2017, 36 CFR Part 1194)    — incorporates WCAG 2.0 Level A+AA by reference.
  EN 301 549 V3.2.1   (ETSI, 2021-03)                 — Chapter 10 (non-web docs) references WCAG 2.1.

So a WCAG-2.2-new criterion (e.g. 2.4.11) is out of 508 scope (post-2.0) AND has no EN clause (post-2.1)
— three honest "not covered by THIS standard at THIS version" states, distinct from "fails the criterion".

DERIVATION, stated so a wrong inference is traceable (a regulatory mapping error is worse than a
flagged gap):
  - 508 required ⟺ the SC is in WCAG 2.0 at Level A or AA.  508 publishes NO per-SC crosswalk (it is
    incorporation-by-reference), so this column is DERIVED, marked accordingly, not asserted from a
    published table.  The 2.0 boundary is the set below minus WCAG21_NEW and WCAG22_NEW.
  - EN 301 549 §10 clause = "10." + the SC number, a pure function, for every ADOPTED row; the only
    stored data are the EXCEPTIONS — EN_VOID (adopted-standard marks it Void: AAA, or web-only N/A to a
    document) and the post-2.1 SCs (no clause in V3.2.1).  This is verbatim from the ETSI text, not
    inferred.

    python3 checks/wcag_model.py            # print the standards model (counts + skew)
    python3 checks/wcag_model.py --check     # completeness: 87 SCs, 32/24/31 by level, mappings sourced
"""
from __future__ import annotations

import sys

# — Provenance: every datum below traces to one of these primary sources. —
SOURCES = {
    "WCAG22": "W3C Recommendation, Web Content Accessibility Guidelines (WCAG) 2.2, 2024-12-12 "
              "(https://www.w3.org/TR/WCAG22/)",
    "508": "Revised Section 508 Standards, US Access Board 2017, 36 CFR Part 1194 — incorporates "
           "WCAG 2.0 Level A and AA by reference (E207); no published per-SC crosswalk (column DERIVED)",
    "EN301549": "ETSI EN 301 549 V3.2.1 (2021-03), Chapter 10 (Non-web documents) — references "
                "WCAG 2.1; clause = 10.<SC> for adopted rows, Void/absent as recorded "
                "(https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_60/en_301549v030201p.pdf)",
}

# The WCAG version each standard references (the skew — a criterion is out of scope BY VERSION).
STANDARD_WCAG_VERSION = {"WCAG22": "2.2", "508": "2.0", "EN301549": "2.1"}

# The 87 WCAG 2.2 success criteria: number → (name, level).  4.1.1 Parsing was REMOVED in 2.2 and is
# absent by construction.  Transcribed from the W3C Recommendation (SOURCES["WCAG22"]).
SC = {
    "1.1.1": ("Non-text Content", "A"),
    "1.2.1": ("Audio-only and Video-only (Prerecorded)", "A"),
    "1.2.2": ("Captions (Prerecorded)", "A"),
    "1.2.3": ("Audio Description or Media Alternative (Prerecorded)", "A"),
    "1.2.4": ("Captions (Live)", "AA"),
    "1.2.5": ("Audio Description (Prerecorded)", "AA"),
    "1.2.6": ("Sign Language (Prerecorded)", "AAA"),
    "1.2.7": ("Extended Audio Description (Prerecorded)", "AAA"),
    "1.2.8": ("Media Alternative (Prerecorded)", "AAA"),
    "1.2.9": ("Audio-only (Live)", "AAA"),
    "1.3.1": ("Info and Relationships", "A"),
    "1.3.2": ("Meaningful Sequence", "A"),
    "1.3.3": ("Sensory Characteristics", "A"),
    "1.3.4": ("Orientation", "AA"),
    "1.3.5": ("Identify Input Purpose", "AA"),
    "1.3.6": ("Identify Purpose", "AAA"),
    "1.4.1": ("Use of Color", "A"),
    "1.4.2": ("Audio Control", "A"),
    "1.4.3": ("Contrast (Minimum)", "AA"),
    "1.4.4": ("Resize Text", "AA"),
    "1.4.5": ("Images of Text", "AA"),
    "1.4.6": ("Contrast (Enhanced)", "AAA"),
    "1.4.7": ("Low or No Background Audio", "AAA"),
    "1.4.8": ("Visual Presentation", "AAA"),
    "1.4.9": ("Images of Text (No Exception)", "AAA"),
    "1.4.10": ("Reflow", "AA"),
    "1.4.11": ("Non-text Contrast", "AA"),
    "1.4.12": ("Text Spacing", "AA"),
    "1.4.13": ("Content on Hover or Focus", "AA"),
    "2.1.1": ("Keyboard", "A"),
    "2.1.2": ("No Keyboard Trap", "A"),
    "2.1.3": ("Keyboard (No Exception)", "AAA"),
    "2.1.4": ("Character Key Shortcuts", "A"),
    "2.2.1": ("Timing Adjustable", "A"),
    "2.2.2": ("Pause, Stop, Hide", "A"),
    "2.2.3": ("No Timing", "AAA"),
    "2.2.4": ("Interruptions", "AAA"),
    "2.2.5": ("Re-authenticating", "AAA"),
    "2.2.6": ("Timeouts", "AAA"),
    "2.3.1": ("Three Flashes or Below Threshold", "A"),
    "2.3.2": ("Three Flashes", "AAA"),
    "2.3.3": ("Animation from Interactions", "AAA"),
    "2.4.1": ("Bypass Blocks", "A"),
    "2.4.2": ("Page Titled", "A"),
    "2.4.3": ("Focus Order", "A"),
    "2.4.4": ("Link Purpose (In Context)", "A"),
    "2.4.5": ("Multiple Ways", "AA"),
    "2.4.6": ("Headings and Labels", "AA"),
    "2.4.7": ("Focus Visible", "AA"),
    "2.4.8": ("Location", "AAA"),
    "2.4.9": ("Link Purpose (Link Only)", "AAA"),
    "2.4.10": ("Section Headings", "AAA"),
    "2.4.11": ("Focus Not Obscured (Minimum)", "AA"),
    "2.4.12": ("Focus Not Obscured (Enhanced)", "AAA"),
    "2.4.13": ("Focus Appearance", "AAA"),
    "2.5.1": ("Pointer Gestures", "A"),
    "2.5.2": ("Pointer Cancellation", "A"),
    "2.5.3": ("Label in Name", "A"),
    "2.5.4": ("Motion Actuation", "A"),
    "2.5.5": ("Target Size (Enhanced)", "AAA"),
    "2.5.6": ("Concurrent Input Mechanisms", "AAA"),
    "2.5.7": ("Dragging Movements", "AA"),
    "2.5.8": ("Target Size (Minimum)", "AA"),
    "3.1.1": ("Language of Page", "A"),
    "3.1.2": ("Language of Parts", "AA"),
    "3.1.3": ("Unusual Words", "AAA"),
    "3.1.4": ("Abbreviations", "AAA"),
    "3.1.5": ("Reading Level", "AAA"),
    "3.1.6": ("Pronunciation", "AAA"),
    "3.2.1": ("On Focus", "A"),
    "3.2.2": ("On Input", "A"),
    "3.2.3": ("Consistent Navigation", "AA"),
    "3.2.4": ("Consistent Identification", "AA"),
    "3.2.5": ("Change on Request", "AAA"),
    "3.2.6": ("Consistent Help", "A"),
    "3.3.1": ("Error Identification", "A"),
    "3.3.2": ("Labels or Instructions", "A"),
    "3.3.3": ("Error Suggestion", "AA"),
    "3.3.4": ("Error Prevention (Legal, Financial, Data)", "AA"),
    "3.3.5": ("Help", "AAA"),
    "3.3.6": ("Error Prevention (All)", "AAA"),
    "3.3.7": ("Redundant Entry", "A"),
    "3.3.8": ("Accessible Authentication (Minimum)", "AA"),
    "3.3.9": ("Accessible Authentication (Enhanced)", "AAA"),
    "4.1.2": ("Name, Role, Value", "A"),
    "4.1.3": ("Status Messages", "AA"),
}

# SCs first introduced in WCAG 2.1 (out of 508's WCAG-2.0 scope; present in EN's WCAG-2.1 scope).
WCAG21_NEW = frozenset({
    "1.3.4", "1.3.5", "1.4.10", "1.4.11", "1.4.12", "1.4.13", "2.1.4",
    "2.5.1", "2.5.2", "2.5.3", "2.5.4", "4.1.3",
})
# SCs first introduced in WCAG 2.2 (out of 508 AND out of EN V3.2.1 scope — no clause exists yet).
WCAG22_NEW = frozenset({
    "2.4.11", "2.4.12", "2.4.13", "2.5.7", "2.5.8", "3.2.6", "3.3.7", "3.3.8", "3.3.9",
})

# EN 301 549 V3.2.1 §10 EXCEPTIONS (the only stored EN data; every other adopted row is "10."+SC).
# "Void" = the standard adopts the clause number but marks it not-applicable to a document (AAA, or a
# web-only criterion N/A to non-web docs).  A post-2.1 SC has NO clause and is handled via WCAG22_NEW.
EN_VOID = frozenset({
    # AAA criteria — Void in EN's non-web chapter
    "1.2.6", "1.2.7", "1.2.8", "1.2.9", "1.3.6", "1.4.6", "1.4.7", "1.4.8", "1.4.9",
    "2.1.3", "2.2.3", "2.2.4", "2.2.5", "2.2.6", "2.3.2", "2.3.3", "2.4.8", "2.4.9",
    "2.4.10", "2.5.5", "2.5.6", "3.1.3", "3.1.4", "3.1.5", "3.1.6", "3.2.5", "3.3.5", "3.3.6",
    # web-only criteria — Void because N/A to a non-web document
    "2.4.1", "2.4.5", "3.2.3", "3.2.4",
})

# WCAG SCs REMOVED in 2.2 (kept for provenance; NOT an active criterion — never scored).
REMOVED_IN_22 = {"4.1.1": ("Parsing", "removed in WCAG 2.2; was 508-required under 2.0")}


def level(sc: str) -> str:
    return SC[sc][1]


def sc_508_required(sc: str) -> bool:
    """DERIVED: 508 incorporates WCAG 2.0 A+AA, so a SC is 508-required iff it is a 2.0-origin A/AA
    criterion — i.e. Level A or AA and NOT introduced in 2.1 or 2.2."""
    return level(sc) in ("A", "AA") and sc not in WCAG21_NEW and sc not in WCAG22_NEW


def en_clause(sc: str) -> str | None:
    """EN 301 549 V3.2.1 §10 (non-web) clause for a SC, or None where V3.2.1 has no clause (a
    post-2.1 SC).  A Void row DOES have a clause number but the standard marks it not-applicable —
    represented as the clause with a Void flag via en_status()."""
    if sc in WCAG22_NEW:
        return None                      # no clause in V3.2.1 (post-2.1)
    return "10." + sc                    # the pure-function clause for every 2.0/2.1 row (incl. Void)


def en_status(sc: str) -> str:
    """The SC's status under EN 301 549 V3.2.1 non-web: 'clause' (adopted, applies), 'void' (clause
    exists but marked N/A to documents), or 'absent' (no clause — post-2.1)."""
    if sc in WCAG22_NEW:
        return "absent"
    return "void" if sc in EN_VOID else "clause"


def counts() -> dict:
    c = {"A": 0, "AA": 0, "AAA": 0}
    for sc in SC:
        c[level(sc)] += 1
    return c


def check() -> tuple[bool, list[str]]:
    """Completeness + internal consistency of the model, against the published counts.  A missing or
    extra SC would make a conformance report claim it evaluated a set it did not — so the count is
    gated against the W3C Recommendation's own totals (32 A + 24 AA + 31 AAA = 87)."""
    problems = []
    c = counts()
    # WCAG 2.2 as PUBLISHED = 86 criteria, DERIVED and checkable: WCAG 2.1 has 78 SCs; 2.2 adds the 9
    # in WCAG22_NEW and REMOVES 4.1.1 Parsing (a Level-A criterion).  78 + 9 − 1 = 86.  (Widely-cited
    # "87" figures either predate the 4.1.1 removal or omit the −1.)  Removing the Level-A 4.1.1 from a
    # 2.1-era "32 A" gives 31 A, so the post-removal breakdown is 31 A / 24 AA / 31 AAA = 86.
    WCAG21_TOTAL = 78
    want_total = WCAG21_TOTAL + len(WCAG22_NEW) - len(REMOVED_IN_22)   # 78 + 9 − 1 = 86, checkable
    want = {"A": 31, "AA": 24, "AAA": 31}
    if c != want:
        problems.append(f"level counts {c} != WCAG 2.2 published {want} (a criterion is missing or extra)")
    if len(SC) != want_total:
        problems.append(f"{len(SC)} success criteria, WCAG 2.2 has {want_total} "
                        f"(WCAG 2.1's {WCAG21_TOTAL} + {len(WCAG22_NEW)} new − {len(REMOVED_IN_22)} removed)")
    if "4.1.1" in SC:
        problems.append("4.1.1 Parsing is present but was REMOVED in WCAG 2.2 — it must not be an active SC")
    # every level is one of A/AA/AAA
    for sc, (_, lv) in SC.items():
        if lv not in ("A", "AA", "AAA"):
            problems.append(f"{sc}: level {lv!r} is not A/AA/AAA")
    # the 2.1/2.2-new sets are disjoint and all name real SCs
    for s in WCAG21_NEW | WCAG22_NEW:
        if s not in SC:
            problems.append(f"version-new set names {s}, absent from the SC list")
    if WCAG21_NEW & WCAG22_NEW:
        problems.append(f"a SC is marked both 2.1-new and 2.2-new: {sorted(WCAG21_NEW & WCAG22_NEW)}")
    # EN_VOID rows are real 2.0/2.1 SCs (a post-2.1 SC has no clause to void)
    for s in EN_VOID:
        if s not in SC:
            problems.append(f"EN_VOID names {s}, absent from the SC list")
        elif s in WCAG22_NEW:
            problems.append(f"EN_VOID names {s} which is 2.2-new (no EN clause exists to be Void)")
    # every mapping datum traces to a source
    for key in ("WCAG22", "508", "EN301549"):
        if key not in SOURCES:
            problems.append(f"standard {key} has no SOURCES provenance")
    return (not problems), problems


def main(argv: list[str]) -> int:
    if "--check" in argv:
        ok, problems = check()
        if not ok:
            for p in problems:
                print(f"wcag-model --check: {p}", file=sys.stderr)
            return 1
        c = counts()
        n508 = sum(1 for sc in SC if sc_508_required(sc))
        nen = sum(1 for sc in SC if en_status(sc) == "clause")
        print(f"wcag-model --check: WCAG 2.2 complete — {len(SC)} SCs "
              f"({c['A']} A, {c['AA']} AA, {c['AAA']} AAA = 78+9−1, 4.1.1 Parsing removed); "
              f"{n508} 508-required (WCAG 2.0 A/AA, derived); {nen} EN 301 549 V3.2.1 non-web clauses; "
              f"version skew modeled (2.2/2.0/2.1); all sourced")
        return 0
    print("accessibility standards model — WCAG 2.2 with 508 + EN 301 549 mappings\n")
    print("version skew (the WCAG baseline each standard references):")
    for k, v in STANDARD_WCAG_VERSION.items():
        print(f"  {k:10} → WCAG {v}")
    print(f"\nWCAG 2.2: {len(SC)} success criteria — {counts()}")
    print(f"508-required (derived, WCAG 2.0 A/AA): {sum(1 for sc in SC if sc_508_required(sc))}")
    print(f"EN 301 549 V3.2.1 non-web: "
          f"{sum(1 for sc in SC if en_status(sc)=='clause')} clause, "
          f"{sum(1 for sc in SC if en_status(sc)=='void')} void, "
          f"{sum(1 for sc in SC if en_status(sc)=='absent')} absent (post-2.1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
