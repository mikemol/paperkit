#!/usr/bin/env python3
"""Behavioral-boundary examples for gate --json (structured output).

⟨P, F, δ⟩ per the boundary practice.  gate --json emits a machine-readable result
(pass, project_ok, verified, sections, collapses, …) to stdout — the data the
report ingests instead of scraping.  This bounds that the structured fields TRACK
the gate's actual verdict.

    python3 paperkit/tests/boundaries_gate_json.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture_gate import gate_json  # noqa: E402
from _fixture_model import _call, entry  # noqa: E402
from _fixture_project import project_text  # noqa: E402
import gate as _gate  # noqa: E402  (the CANNOT-RUN path needs a dir with NO paper.toml)


def gate_json_raw(paper_toml=None, *flags):
    """(rc, parsed --json, stderr) over a temp dir with an ARBITRARY paper.toml (or none).
    The _fixture_gate helpers always _write a USABLE project; the CANNOT-RUN cases are exactly
    the projects those helpers cannot express — no paper.toml, a malformed / [paper]-less one,
    or one whose declared inputs do not exist."""
    with tempfile.TemporaryDirectory() as d:
        if paper_toml is not None:
            (Path(d) / "paper.toml").write_text(paper_toml)
        rc, o, e = _call(_gate.main, ["--json", *flags, d])
        return rc, json.loads(o or "{}"), e

C = entry("c", claim="anchored")
DISTINCT = [entry("a", claim="alpha", check="file:w.bib"),
            entry("b", claim="beta", check="file:r.tsv", frm="a")]
SHARED = [entry("a", claim="alpha", check="file:w.bib"),
          entry("b", claim="beta", check="file:w.bib", frm="a")]


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

    canonical = project_text([C])
    rc_ok, j_ok = gate_json([C], out=canonical)
    rc_bad, j_bad = gate_json([C], out=canonical + "\nDRIFT\n")
    _, j_distinct = gate_json(DISTINCT)
    _, j_shared = gate_json(SHARED)
    # Ζ·gate·exit — the CANNOT-RUN cases: the boundary is "assembles into a gateable project",
    # not "did tomllib raise".  All four must exit 3, and NONE may report the downstream
    # "not built — run paperkit-project" line (that would misdiagnose an unusable config as
    # staleness — A67 / summit friction-cannot-gate-guard-misses-unloadable-config).
    rc_norun, j_norun, _ = gate_json_raw(None)                       # no paper.toml
    rc_nobib, j_nobib, e_nobib = gate_json_raw("[other]\nx=1\n")     # parses, no [paper] table
    rc_titleonly, _, e_titleonly = gate_json_raw('[paper]\ntitle="t"\n')  # inputs default → absent
    rc_badw, _, e_badw = gate_json_raw(
        '[paper]\ntitle="t"\nwarrants=["nope.bib"]\nrubric="r.tsv"\nout="o.md"\n')  # warrant absent
    _misdiag = "not built"

    print("gate --json behaviors\n")
    check("pass=true, project_ok=true on a clean doc (matches exit 0)",
          j_ok["pass"] is True and j_ok["project_ok"] is True and rc_ok == 0)
    check("pass=false, project_ok=false on drifted prose (matches exit 1)",
          j_bad["pass"] is False and j_bad["project_ok"] is False and rc_bad == 1)
    check("collapses is empty when witnesses are distinct", j_distinct["collapses"] == {})
    check("collapses ENUMERATES the shared witness, not just a count",
          j_shared["collapses"].get("file:w.bib") == ["a", "b"])
    # Ζ·gate·exit — availability lives in the exit code (0/1 = ran; 3 = CANNOT RUN) AND in --json.
    check("available=true on a project that ran (pass or fail)",
          j_ok.get("available") is True and j_bad.get("available") is True)
    check("no paper.toml → exit 3 (CANNOT RUN), not 1 (ran-and-failed), no traceback",
          rc_norun == 3)
    check("CANNOT RUN → --json available:false, pass:false (not a fake pass, not a bare crash)",
          j_norun.get("available") is False and j_norun.get("pass") is False)
    check("a config that PARSES but is not gateable also CANNOT RUN (exit 3), not exit 1",
          rc_nobib == 3 and rc_titleonly == 3 and rc_badw == 3)
    check("no [paper] table → available:false (parses-but-unusable is on the cannot-run side)",
          j_nobib.get("available") is False)
    check("CANNOT RUN never MISDIAGNOSES an unusable config as 'not built' (A67)",
          _misdiag not in e_nobib and _misdiag not in e_titleonly and _misdiag not in e_badw)
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
        ("the exit code carries AVAILABILITY (ran-and-failed vs cannot-run)",
         "whether paper.toml exists to read",
         "present → ran, exit 1 on failure", rc_bad == 1,
         "absent  → CANNOT RUN, exit 3", rc_norun == 3),
        ("the boundary is 'gateable config', not merely 'valid TOML'",
         "a declared warrant that exists vs one that does not",
         "usable config → gates (exit 0/1)", rc_ok == 0,
         "warrant absent → CANNOT RUN, exit 3", rc_badw == 3),
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
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, 4 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
