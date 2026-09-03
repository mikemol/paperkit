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
from _fixture_delta import discriminate
from _fixture_gate import gate, gate_json
from _fixture_model import entry

# a plain-target paper.toml (overrides the fixture default via assets)
#
# ⚑ Ζ·declare·resources — `root = "."` IS LOAD-BEARING, AND IS HERE BECAUSE THIS IS A SECOND
# AUTHORING SITE FOR paper.toml.  _fixture_model._write declares the Δ sandbox root in the
# paper.toml it writes; this asset then REWRITES that file wholesale to set `target = "plain"`,
# so every field the fixture declared has to be restated — and the one that was not restated
# was the only one whose absence is not a syntax error but a REFUSAL three frames deep in
# layout._sandbox_root, surfacing as an empty stdout and a JSONDecodeError in the caller.
#
# Measured: with the fixture fixed and this override not, six of the seven arms below stayed
# green (they call gate(), which does not sweep) and only the one Δ arm went red — the shape
# guard-must-not-copy names, one level over: a copy of a declaration drifts from its original
# the moment the original gains a field.
PLAIN = {"paper.toml": '[paper]\ntitle = "t"\nwarrants = ["w.bib"]\nrubric = "r.tsv"\n'
                       'out = "out.md"\nnumbered = false\nreferences = false\ntarget = "plain"\n'
                       'root = "."\n'}


def chain(leaf_check):
    """Apex (section-tagged, woven) → g (sectionless) → h (sectionless), two rests-on hops.
    Neither g nor h surfaces any marker in the rendered prose — only the closure reaches them.
    """
    return [entry("a", claim="apex", rests="g"),
            entry("g", claim="ground", section=None, check="file:w.bib", rests="h"),
            entry("h", claim="bedrock", section=None, check=leaf_check)]


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

    # SAID-SOMETHING (summit ask-degenerate-claim-passes) — a claim whose `claim` brace lands a
    # field late loses its text to bib.parse's brace-balanced regex; the projector then renders the
    # bare KEY as the paragraph and PROJECT/RESOLVE/COVERAGE all still hold.  The gate refuses a
    # section claim that would project as its key (no `claim`, no `title`).  δ = the closing brace.
    GOOD = entry("good", claim="a good claim")
    RUNAWAY = ("@misc{mute,\n  section = {s}, from = {good}, join = {. },\n"
               "  claim   = {this claim loses its closing brace and the next field swallows it,\n"
               "  check   = {cmd:true}\n}\n")
    CLOSED = ("@misc{mute,\n  section = {s}, from = {good}, join = {. },\n"
              "  claim   = {this claim closes its brace},\n  check   = {cmd:true}\n}\n")
    rc_mute, e_mute = gate([GOOD, RUNAWAY], assets=PLAIN)
    rc_said, _ = gate([GOOD, CLOSED], assets=PLAIN)
    # ⚑ Ζ·bib·wire — THE REFUSAL MOVED FROM THE PROJECTOR TO THE PARSER, and that is the point.
    # This arm used to assert the projector's "bare KEY" message: the old regex front end ended
    # an entry at the first line-initial `}`, so a runaway `claim` brace produced a record with a
    # MANGLED claim and no check, and the gate refused it downstream as a claim that says nothing.
    # That refusal was an ACCIDENT of the truncation — the parser had no opinion about the file
    # being broken, and two attempts to fix the front end (skip the entry; run to EOF) each moved
    # the behaviour again, because a scanner has no grammar to answer from.
    #
    # A real parser answers by position: a `{` that never closes is a SYNTAX ERROR where it
    # opened.  So the property this arm pins is unchanged — a runaway brace must not ship — while
    # the WHO and the WORDING both move.  Asserting the message text would re-pin the next
    # accident; asserting the refusal plus the named position is what the property actually is.
    check("a claim whose `claim` brace runs away is REFUSED — now by the parser, at a position",
          rc_mute != 0 and "mute" in e_mute
          and any(w in e_mute for w in ("unterminated", "expected", "SyntaxError")))
    check("the same claim with its brace closed says something — the gate PASSES", rc_said == 0)

    print("\n⟨P, F, δ⟩ minimum-delta pairs\n")
    ok = rc_p == 0 and rc_f == 1
    fails.append("grounding-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}the grounded leaf's check alone flips the gate")
    print("      P (pass side): h's check resolves (file:r.tsv present) → gate PASS")
    print("      F (flag side): h's check breaks (file:nope absent) → gate FAIL, [@h] named")
    print("      δ (min delta): one grounded (sectionless, uncited) claim's check target\n")

    ok2 = rc_mute == 1 and rc_said == 0
    fails.append("said-something-delta") if not ok2 else None
    print(f"  {'ok ' if ok2 else 'XX '}a claim that says nothing (projects as its key) flips the gate")
    print("      P (pass side): the `claim` brace closes → the paragraph carries prose → PASS")
    print("      F (flag side): the brace runs away → the paragraph is the bare KEY → FAIL")
    print("      δ (min delta): the claim's closing brace\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    bad = len([b for b in ran if not b])
    if bad:
        print(f"BOUNDARIES: FAIL ({bad} of {len(ran)} behaviors drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, 2 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
