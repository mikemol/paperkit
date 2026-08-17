#!/usr/bin/env python3
r"""Ρ·render·wcag — the VPAT INT conformance report, a self-attesting projection.

The terminus of the regulatory arc: a public accessibility conformance report (a VPAT®/ACR, the
International edition — WCAG 2.2 with Section 508 and EN 301 549 mappings), generated as a paperkit
PROJECTION from the standards model (wcag_model.py) and the proven entailment verdicts
(wcag_entail.py), per delivery route.  Nothing here is authored — the report is a view of the model
and the proofs, so it cannot drift from them, and it cannot claim a conformance its warrants do not
prove: every "Supports" carries, in its Remarks, the warrant that ENTAILS it (an F-arm proving the
violation is caught, or the PDF/UA validator).  This is paperkit's own thesis — a document is a
projection of a verified claim-DAG — applied to the highest-stakes claim a document makes about
itself, so the conformance statement and its proof are one object, gated fresh.

Conservative by construction (a false "Supports" is a false regulatory claim): a criterion whose
entailment is unproven is Partially Supports, Does Not Support, Not Applicable, or Not Evaluated —
never Supports.  The version skew is disclosed, not hidden: a criterion new in WCAG 2.2 is out of
Section 508 scope (WCAG 2.0) and out of EN 301 549 V3.2.1 scope (WCAG 2.1) BY VERSION, and the
report says so rather than claiming or denying conformance a standard does not reach.

    python3 checks/wcag.py [--route docx|latex]   # print the VPAT for a route
    python3 checks/wcag.py --emit                 # write assets/wcag-vpat.md (both routes)
    python3 checks/wcag.py --check                # assert the emitted VPAT is the fresh projection
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wcag_entail as we
import wcag_model as wm

_OUT = Path(__file__).resolve().parent.parent / "assets" / "wcag-vpat.md"

# The VPAT conformance terms (ITI VPAT / Section 508 ACR vocabulary).
_TERMS = ("Supports", "Partially Supports", "Does Not Support", "Not Applicable", "Not Evaluated")


def _sc_sorted(level: str) -> list:
    return sorted((s for s in wm.SC if wm.level(s) == level),
                  key=lambda s: [int(x) for x in s.split(".")])


def _wcag_row(sc: str, route: str) -> str:
    v = we.entail(sc, route)
    return f"| {sc} {wm.SC[sc][0]} | {v['verdict']} | {v['remark']} |"


def _wcag_tables(route: str) -> list:
    """WCAG 2.2 report — one table per conformance level (VPAT Tables 1/2/3), tracking the A/AA/AAA
    gradation.  Each row is the SC, its entailment verdict, and the attesting remark."""
    out = []
    for level, title in (("A", "Table 1: Success Criteria, Level A"),
                         ("AA", "Table 2: Success Criteria, Level AA"),
                         ("AAA", "Table 3: Success Criteria, Level AAA")):
        out.append(f"### {title}\n")
        out.append("| Criteria | Conformance Level | Remarks and Explanations |")
        out.append("| --- | --- | --- |")
        for sc in _sc_sorted(level):
            out.append(_wcag_row(sc, route))
        out.append("")
    return out


def _section_508(route: str) -> list:
    """Revised Section 508 (WCAG 2.0 A+AA by incorporation).  The 508 report reads the WCAG verdicts
    for the criteria 508 incorporates; a WCAG-2.1-or-2.2-new criterion is OUT OF 508 SCOPE by version
    and disclosed as such, never given a 508 verdict it cannot bear."""
    out = ["## Revised Section 508 Report\n",
           "Section 508 incorporates WCAG 2.0 Level A and AA by reference. Criteria introduced after "
           "WCAG 2.0 are outside 508 scope by version (disclosed below, not scored as 508).\n",
           "| Criteria | Conformance Level | Remarks and Explanations |",
           "| --- | --- | --- |"]
    for sc in sorted(wm.SC, key=lambda s: [int(x) for x in s.split(".")]):
        if wm.sc_508_required(sc):
            v = we.entail(sc, route)
            out.append(f"| {sc} {wm.SC[sc][0]} ({wm.level(sc)}) | {v['verdict']} | {v['remark']} |")
    out.append("")
    return out


def _en_301_549(route: str) -> list:
    """EN 301 549 V3.2.1, Chapter 10 (Non-web documents).  Each adopted clause is 10.<SC>; a Void row
    is disclosed as Void (the standard adopts it Not Applicable to documents); a WCAG-2.2-new criterion
    has no clause in V3.2.1 and is disclosed as out of scope by version."""
    out = ["## EN 301 549 V3.2.1 Report (Chapter 10, Non-web Documents)\n",
           "EN 301 549 V3.2.1 references WCAG 2.1. Chapter 10 maps each adopted criterion to clause "
           "10.x; criteria new in WCAG 2.2 have no clause in this version (out of scope by version).\n",
           "| EN Clause | Criteria | Status | Remarks and Explanations |",
           "| --- | --- | --- | --- |"]
    for sc in sorted(wm.SC, key=lambda s: [int(x) for x in s.split(".")]):
        st = wm.en_status(sc)
        clause = wm.en_clause(sc) or "—"
        if st == "absent":
            out.append(f"| — | {sc} {wm.SC[sc][0]} | Out of scope (post-2.1) | not in EN 301 549 V3.2.1 |")
        elif st == "void":
            out.append(f"| {clause} | {sc} {wm.SC[sc][0]} | Void | not applicable to non-web documents per EN |")
        else:
            v = we.entail(sc, route)
            out.append(f"| {clause} | {sc} {wm.SC[sc][0]} | {v['verdict']} | {v['remark']} |")
    out.append("")
    return out


def _report(route: str) -> str:
    ua = we.ROUTE_FINAL[route][1]
    lines = [
        f"# Accessibility Conformance Report — {route} route",
        "",
        "International Edition (VPAT®-style ACR): WCAG 2.2, Revised Section 508, and EN 301 549.",
        "",
        f"**Deliverable / technologies relied upon:** paperkit's paper rendered through the {route} "
        f"route to a tagged PDF ({ua}). Conformance is stated per route because the routes differ "
        f"(the office route reaches PDF/UA-1, the LaTeX route PDF/UA-2).",
        "",
        "**Attestation basis:** this report is a paperkit projection of a verified claim-DAG. Each "
        "\"Supports\" is entailed by a warrant whose ⟨P,F,δ⟩ F-arm reds on the criterion's violation, "
        "or by veraPDF (the PDF/UA validator); an unproven criterion is never \"Supports\". The report "
        "is gated fresh, so the conformance claim and its machine-checked proof are one object.",
        "",
        "**Standards versions:** WCAG 2.2 (W3C Rec 2024-12-12); Revised Section 508 (WCAG 2.0 A/AA); "
        "EN 301 549 V3.2.1 (WCAG 2.1). The version skew is disclosed per report.",
        "",
        "## WCAG 2.2 Report",
        "",
    ]
    lines += _wcag_tables(route)
    lines += _section_508(route)
    lines += _en_301_549(route)
    # provenance footer — the sources every datum traces to
    lines.append("## Sources")
    lines.append("")
    for k in ("WCAG22", "508", "EN301549"):
        lines.append(f"- {wm.SOURCES[k]}")
    lines.append(f"- {we._UA_SOURCE}")
    lines.append("")
    return "\n".join(lines)


def emit() -> str:
    """The full VPAT INT: both routes, one document (a consumer picks their deliverable's section)."""
    parts = ["<!-- GENERATED by checks/wcag.py from wcag_model.py + wcag_entail.py — do not edit; "
             "regenerate: python3 checks/wcag.py --emit -->",
             "", "# paperkit — Accessibility Conformance Report (VPAT® International)", ""]
    for route in we.ROUTE_FINAL:
        parts.append(_report(route))
        parts.append("\n---\n")
    return "\n".join(parts).rstrip() + "\n"


def check() -> tuple[bool, list[str], list[str]]:
    """The emitted VPAT is the FRESH projection (project-don't-author, so it cannot drift), and the
    entailment gate underneath it holds (so no Supports is unproven).  Ζ·tier·exit — a farm F-arm that
    CANNOT RUN here (toolchain absent) is surfaced separately: the VPAT freshness + registry soundness
    still gate (they are pure), but the un-runnable F-arms yield cannot-run (exit 3), not a failure."""
    problems = []
    ok_e, probs_e, cannot_e = we.check()
    if not ok_e:
        problems += [f"entailment: {p}" for p in probs_e]
    if not _OUT.exists():
        problems.append(f"{_OUT.name} not emitted — run: python3 checks/wcag.py --emit")
    elif _OUT.read_text() != emit():
        problems.append(f"{_OUT.name} drifted from the projection — regenerate: python3 checks/wcag.py --emit")
    return (not problems), problems, [f"entailment: {c}" for c in cannot_e]


def main(argv: list[str]) -> int:
    if "--emit" in argv:
        _OUT.parent.mkdir(exist_ok=True)
        _OUT.write_text(emit())
        print(f"wcag: wrote {_OUT.relative_to(_OUT.parent.parent)} (VPAT INT, both routes)")
        return 0
    if "--check" in argv:
        ok, problems, cannot_run = check()
        if not ok:
            for p in problems:
                print(f"wcag --check: {p}", file=sys.stderr)
            return 1
        if cannot_run:                                  # Ζ·tier·exit — freshness+registry sound, but a farm could not run
            for c in cannot_run:
                print(f"wcag --check: {c}", file=sys.stderr)
            print("wcag --check: the VPAT projection is fresh and the registry is sound, but some F-arms "
                  "CANNOT RUN here (toolchain absent) — those SCs disclose Not Evaluated (conservative).",
                  file=sys.stderr)
            return 3                                    # cannot-run, not a failure
        print("wcag --check: the VPAT INT conformance report is the fresh projection of the standards "
              "model and the proven entailment verdicts — every Supports is warrant-attested, gated fresh")
        return 0
    route = argv[argv.index("--route") + 1] if "--route" in argv else "latex"
    print(_report(route))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
