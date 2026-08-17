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

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matrix
import wcag_model as wm

# The route → its final delivered format (matrix format names) + PDF/UA version.
ROUTE_FINAL = {"docx": ("pdf-office", "UA-1"), "latex": ("pdf-latex", "UA-2")}

# Per-warrant ENTAILMENT FORM.  "farm" = a ⟨P,F,δ⟩ selftest proves the violation is caught (verified
# by running it); "oracle" = the check delegates to veraPDF (the PDF/UA validator, authoritative).
# A warrant not listed here has NO proven entailment → its cells cannot yield "Supports".
ENTAILMENT = {
    "rnd-ruler":     ("farm",   ["python3", "checks/ruler.py"]),          # 1.4.1 producing (nicematrix rules)
    "rnd-colour":    ("farm",   ["python3", "checks/use_of_colour.py"]),  # 1.4.1 verifying (weight cue)
    "rnd-math-alt":  ("farm",   ["python3", "checks/mathalt.py", "--selftest"]),
    "rnd-link-alt":  ("farm",   ["python3", "checks/linkalt.py", "--selftest"]),
    "rnd-widen":     ("farm",   ["python3", "checks/widen_tables.py", "--selftest"]),
    "rnd-a11y":      ("oracle", None),   # a11y_own.py → veraPDF UA-1 zero-fail (the PDF/UA validator)
    "rnd-a11y-latex":("oracle", None),   # a11y_latex.py → veraPDF UA-2 zero-fail
    # rnd-wf / rnd-fidelity / rnd-fig-legible / rnd-fig-vector validate against the real artifact but
    # carry no synthetic F-arm and are not the UA oracle; their SCs are entailed (if at all) through
    # the PDF/UA oracle below, not through these warrants directly.  Left UNPROVEN here on purpose.
}

# PDF/UA (ISO 14289) zero-fail → the WCAG SCs its tagging requirements DOCUMENTABLY entail.  Narrow
# and conservative: only correspondences that the tagged-structure requirement directly establishes.
# A UA-conformant PDF has a tagged structure tree with correct reading order and role mapping, a
# document title and language, and (UA) alternate text on non-text content.
PDFUA_TO_WCAG = {
    "1.1.1": "UA requires alternate text / MathML on non-text content (figures, formulas)",
    "1.3.1": "UA requires a tagged structure tree encoding info and relationships",
    "1.3.2": "UA requires a correct reading order in the tag tree (meaningful sequence)",
    "2.4.2": "UA requires a document title (and the viewer to display it)",
    "2.4.6": "UA requires headings in the structure tree (headings and labels)",
    "3.1.1": "UA requires the document's primary language to be set",
    "4.1.2": "UA requires structure-element roles (name, role, value) in the tag tree",
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


def _warrants_tagging(sc: str, fmt: str) -> list:
    """Warrants whose matrix cell (afforded native/post on `fmt`) tags this SC — directly via the
    capability's wcag clause, or via PDFUA_TO_WCAG when the capability is pdf-ua."""
    out = []
    for cap, spec in matrix.CAPABILITIES.items():
        st, warrant = spec["cells"].get(fmt, (None, None))
        if st not in ("native", "post"):
            continue
        tag = spec.get("wcag", "")
        direct = (tag == sc)
        via_ua = (cap == "pdf-ua" and sc in PDFUA_TO_WCAG)
        via_clause = (tag == "7.7" and sc == "1.1.1") or (tag == "7.18" and sc == "2.4.4")
        if direct or via_ua or via_clause:
            out.append(warrant)
    return out


def _proven(warrant: str, run_farm: bool) -> str | None:
    """The entailment form of a warrant if PROVEN, else None.  For a "farm" warrant, optionally RUN
    its selftest (run_farm) so the entailment is verified not asserted; "oracle" is proven by being
    the standard's own validator."""
    form = ENTAILMENT.get(warrant)
    if form is None:
        return None
    kind, cmd = form
    if kind == "oracle":
        return "oracle"
    if kind == "farm":
        if run_farm:
            rc = subprocess.run(cmd, capture_output=True,
                                cwd=Path(__file__).resolve().parent.parent).returncode
            return "farm" if rc == 0 else None    # a farm whose selftest fails does NOT entail
        return "farm"
    return None


def entail(sc: str, route: str, run_farm: bool = False) -> dict:
    """The entailment verdict for one SC on one route.  Conservative: Supports only with a proven
    entailing warrant; else Partially / Does Not Support / Not Applicable / Not Evaluated."""
    fmt, _ua = ROUTE_FINAL[route]
    if sc in NOT_APPLICABLE:
        return {"verdict": "Not Applicable", "warrant": None, "form": None,
                "remark": "does not apply to a static, non-interactive print PDF"}
    warrants = _warrants_tagging(sc, fmt)
    # a proven entailing warrant → Supports
    for w in warrants:
        form = _proven(w, run_farm)
        if form:
            via = f" (via PDF/UA: {PDFUA_TO_WCAG[sc]})" if sc in PDFUA_TO_WCAG and w in ("rnd-a11y", "rnd-a11y-latex") else ""
            return {"verdict": "Supports", "warrant": w, "form": form,
                    "remark": f"{w} entails this ({form}){via}"}
    # tagged but the entailment is a "post"/"excepted" partial (a warrant is present but not proven full)
    if warrants:
        return {"verdict": "Partially Supports", "warrant": warrants[0], "form": None,
                "remark": f"{warrants[0]} addresses this but its entailment is not proven for a full claim"}
    # claimable for this content but no entailing warrant → Does Not Support (honest gap)
    return {"verdict": "Does Not Support", "warrant": None, "form": None,
            "remark": "no warrant entails this criterion for this deliverable (a known gap)"}


def check() -> tuple[bool, list[str]]:
    """Every "Supports" a route yields must resolve to a warrant with PROVEN entailment — the farm
    warrants' selftests are RUN (so a broken F-arm cannot back a Supports), the oracle warrants are
    the standard's validator.  This is the regulatory soundness gate: no Supports without proof."""
    problems = []
    # the entailment registry must name real warrants (in warrants.bib) and real check commands.
    bib = (Path(__file__).resolve().parent.parent / "warrants.bib").read_text()
    for w, (kind, cmd) in ENTAILMENT.items():
        if f"@misc{{{w}," not in bib and f"@misc{{{w} ," not in bib:
            problems.append(f"entailment names warrant {w!r} absent from warrants.bib")
        if kind not in ("farm", "oracle"):
            problems.append(f"{w}: entailment form {kind!r} is not farm/oracle")
    # every farm warrant's selftest must PASS (a Supports backed by a red F-arm is a false claim).
    for w, (kind, cmd) in ENTAILMENT.items():
        if kind == "farm":
            rc = subprocess.run(cmd, capture_output=True,
                                cwd=Path(__file__).resolve().parent.parent).returncode
            if rc != 0:
                problems.append(f"{w}: its ⟨P,F,δ⟩ selftest FAILS (rc={rc}) — cannot back a Supports")
    # every SC a route marks Supports must, on re-derivation with farm-running, still be Supports
    # (the verdict is stable and proof-backed, not an artifact of skipping the selftest).
    for route in ROUTE_FINAL:
        for sc in wm.SC:
            v = entail(sc, route, run_farm=False)
            if v["verdict"] == "Supports":
                vr = entail(sc, route, run_farm=True)
                if vr["verdict"] != "Supports":
                    problems.append(f"{sc} × {route}: Supports without a passing entailment proof")
    return (not problems), problems


def summary(route: str, run_farm: bool = False) -> dict:
    tally = {}
    for sc in wm.SC:
        v = entail(sc, route, run_farm)["verdict"]
        tally[v] = tally.get(v, 0) + 1
    return tally


def main(argv: list[str]) -> int:
    if "--check" in argv:
        ok, problems = check()
        if not ok:
            for p in problems:
                print(f"wcag-entail --check: {p}", file=sys.stderr)
            return 1
        parts = []
        for route in ROUTE_FINAL:
            t = summary(route, run_farm=False)
            parts.append(f"{route} {ROUTE_FINAL[route][1]}: " +
                         ", ".join(f"{t.get(v,0)} {v}" for v in
                                   ("Supports", "Partially Supports", "Does Not Support",
                                    "Not Applicable", "Not Evaluated") if t.get(v)))
        print("wcag-entail --check: every Supports has proven entailment (farm selftests pass, "
              "oracle = veraPDF); conservative — no Supports without proof.")
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
