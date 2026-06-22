#!/usr/bin/env python3
"""Behavioral-boundary examples for gate --json (structured output).

⟨P, F, δ⟩ per the boundary practice.  gate --json emits a machine-readable result
(pass, project_ok, verified, sections, collapses, …) to stdout — the data the
report ingests instead of scraping.  This bounds that the structured fields TRACK
the gate's actual verdict.

    python3 paperkit/tests/boundaries_gate_json.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture import entry, gate_json, project_text  # noqa: E402

C = entry("c", claim="anchored")
DISTINCT = [entry("a", claim="alpha", check="file:w.bib"),
            entry("b", claim="beta", check="file:r.tsv", frm="a")]
SHARED = [entry("a", claim="alpha", check="file:w.bib"),
          entry("b", claim="beta", check="file:w.bib", frm="a")]


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    canonical = project_text([C])
    rc_ok, j_ok = gate_json([C], out=canonical)
    rc_bad, j_bad = gate_json([C], out=canonical + "\nDRIFT\n")
    _, j_distinct = gate_json(DISTINCT)
    _, j_shared = gate_json(SHARED)

    print("gate --json behaviors\n")
    check("pass=true, project_ok=true on a clean doc (matches exit 0)",
          j_ok["pass"] is True and j_ok["project_ok"] is True and rc_ok == 0)
    check("pass=false, project_ok=false on drifted prose (matches exit 1)",
          j_bad["pass"] is False and j_bad["project_ok"] is False and rc_bad == 1)
    check("collapses is empty when witnesses are distinct", j_distinct["collapses"] == {})
    check("collapses ENUMERATES the shared witness, not just a count",
          j_shared["collapses"].get("file:w.bib") == ["a", "b"])
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("pass field tracks the gate verdict", "a drift line appended to out.md",
         "clean → pass:true", j_ok["pass"] is True,
         "drift → pass:false", j_bad["pass"] is False),
        ("collapses enumerate shared witnesses",
         "the second claim's check (file:r.tsv → file:w.bib)",
         "distinct → {}", j_distinct["collapses"] == {},
         "shared   → {file:w.bib: [a, b]}", j_shared["collapses"] != {}),
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
    print("BOUNDARIES: PASS (4 behaviors, 2 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
