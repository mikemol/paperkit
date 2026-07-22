#!/usr/bin/env python3
"""Behavioral-boundary examples for the gate's GROUNDING closure (rests-on).

⟨P, F, δ⟩ per the boundary practice.  The gate's resolved set is the TRANSITIVE
CLOSURE of the cited/placed set under `rests-on`: a cited claim's grounding
premises are load-bearing whether or not a citation marker for them survives in
the rendered prose (plain/footnote render none; adjacent and cross-scope edges
render none on ANY target).  So a SECTIONLESS node reachable via rests-on is
gated and graded — and its check FAILING fails the gate — while an UNREACHABLE
sectionless node's check stays un-gated.  A rests-on edge to an undefined key is
a broken grounding: it fails the gate like an undefined citation.

    python3 paperkit/tests/boundaries_grounding.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture_delta import discriminate  # noqa: E402
from _fixture_gate import gate, gate_json  # noqa: E402
from _fixture_model import entry  # noqa: E402

# a plain-target paper.toml (overrides the fixture default via assets)
PLAIN = {"paper.toml": '[paper]\ntitle = "t"\nwarrants = ["w.bib"]\nrubric = "r.tsv"\n'
                       'out = "out.md"\nnumbered = false\nreferences = false\ntarget = "plain"\n'}


def chain(leaf_check):
    """apex (section-tagged, woven) → g (sectionless) → h (sectionless), two rests-on hops.
    Neither g nor h surfaces any marker in the rendered prose — only the closure reaches them."""
    return [entry("a", claim="apex", rests="g"),
            entry("g", claim="ground", section=None, check="file:w.bib", rests="h"),
            entry("h", claim="bedrock", section=None, check=leaf_check)]


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("grounding closure — the gate resolves the rests-on cone of the cited/placed set\n")

    rc_p, j_p = gate_json(chain("file:r.tsv"), assets=PLAIN)
    rc_f, e_f = gate(chain("file:nope"), assets=PLAIN)
    check("plain: a sectionless rests-on cone all passing → gate PASS", rc_p == 0)
    check("plain: BOTH sectionless grounding nodes are in the resolved count (verified=3)",
          j_p.get("verified") == 3)
    check("plain: a sectionless node TWO rests-on hops away with a FAILING check fails the gate",
          rc_f == 1 and "[@h]" in e_f)

    rc_u, _e = gate([entry("a", claim="apex"),
                     entry("z", claim="stray", section=None, check="file:nope")], assets=PLAIN)
    check("plain: an UNREACHABLE sectionless node's failing check stays un-gated (PASS)", rc_u == 0)

    rc_c, _e = gate([entry("a", claim="apex", rests="g"),
                     entry("g", claim="ground", section=None, check="file:w.bib", rests="h"),
                     entry("h", claim="bedrock", section=None, check="file:r.tsv", rests="g")],
                    assets=PLAIN)
    check("plain: a rests-on CYCLE terminates (each node visited once) and gates its checks", rc_c == 0)

    rc_d, e_d = gate([entry("a", claim="apex", rests="ghost")], assets=PLAIN)
    check("a rests-on edge to an UNDEFINED key is a broken grounding — gate FAILS",
          rc_d == 1 and "dangling rests-on" in e_d and "ghost" in e_d)

    # the closure is target-independent: pandoc renders no marker for a cross-scope
    # (sectionless) grounding edge either, yet the cone is still gated.
    rc_pd, e_pd = gate(chain("file:nope"))
    check("pandoc: the same failing grounding cone fails the gate (closure on every target)",
          rc_pd == 1 and "[@h]" in e_pd)

    rc_g, o_g = discriminate(chain("file:r.tsv"), "--json", assets=PLAIN)
    keys = {r["key"] for r in json.loads(o_g or "[]")}
    check("Δ grades the sectionless grounding nodes too (they appear in the records)",
          {"g", "h"} <= keys)

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    ok = rc_p == 0 and rc_f == 1
    fails.append("grounding-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}the grounded leaf's check alone flips the gate")
    print("      P (pass side): h's check resolves (file:r.tsv present) → gate PASS")
    print("      F (flag side): h's check breaks (file:nope absent) → gate FAIL, [@h] named")
    print("      δ (min delta): one grounded (sectionless, uncited) claim's check target\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (8 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
