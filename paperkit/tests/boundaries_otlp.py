#!/usr/bin/env python3
"""Ρ·telemetry — the OTLP pusher's boundary (the PURE core, gated).

The wrapper-layer half (tools/otlp_push.py's push(): the live POST + counter settle-poll)
is observation and MUST NOT gate — a down endpoint can never block a commit, so it stays
best-effort in the pre-commit, never in //:hook.  But the PURE half — parse the concatenated-
JSON execlog, attribute each spawn to a project/check_type/target, aggregate into the cassian
schema — is deterministic, stdlib-only, and load-bearing for the instrument's HONESTY (a
mis-parse pushes wrongly-attributed rows the counter-guard cannot catch: the counter verifies
COUNT, not ATTRIBUTION — the substrate-not-contract lesson).  So the pure half is gated here,
exactly as bnd-hook-index gates hook_index.py's git-free core while its git call stays
pre-commit-only.  ⟨P,F,δ⟩ over the one semantic decision in metric_families: a spawn counts as
Δ (discriminate) work iff its mnemonic is in the owner's DELTA set — one spawn's mnemonic flips
whether discriminate_seconds sees it.

    python3 paperkit/tests/boundaries_otlp.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from otlp_push import (  # noqa: E402  (the OWNER of the parse/attribution/aggregation)
    DELTA, Spawn, duration_seconds, metric_families, parse_execlog, project_of, target_of)

# A concatenated-JSON execlog (NOT a JSON array — bazel writes one SpawnExec object per spawn):
# one Δ-grid action (PkEval) + one test wrapper (TestRunner) + one cross-project test.
EXECLOG = (
    '{"mnemonic":"PkEval","targetLabel":"@@+bib+paperkit_paper//:c__eval",'
    '"metrics":{"executionWallTime":"0.400s"}}\n'
    '{"mnemonic":"TestRunner","targetLabel":"@@+bib+paperkit_paper//:gate",'
    '"metrics":{"executionWallTime":"3.500s"}}\n'
    '{"mnemonic":"TestRunner","targetLabel":"//canary:canary",'
    '"metrics":{"executionWallTime":"1.000s"}}'
)


def _fam(fams, name):
    return next(f for f in fams if f["name"] == name)


def _point(fam, **attrs):
    """The value at the point whose attributes exactly match, or None."""
    for value, a in fam["points"]:
        if a == attrs:
            return value
    return None


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Ρ·telemetry — the OTLP pusher's pure core\n")

    spawns = parse_execlog(EXECLOG)
    check("parse_execlog reads CONCATENATED objects (not an array) — 3 spawns",
          len(spawns) == 3 and [s.mnemonic for s in spawns] == ["PkEval", "TestRunner", "TestRunner"])
    check("executionWallTime parses to float seconds off the spawn",
          [s.wall for s in spawns] == [0.4, 3.5, 1.0])
    check("project_of strips the @@+bib+paperkit_ repo prefix",
          project_of("@@+bib+paperkit_paper//:gate") == "paper")
    check("project_of on a local //pkg:target label",
          project_of("//canary:canary") == "canary" and project_of("//tools:sched-batch-bin") == "tools")
    check("target_of is the post-colon target name",
          target_of("@@+bib+paperkit_paper//:c__eval") == "c__eval" and target_of("//canary:canary") == "canary")
    check("duration_seconds: '6.904s'/'500ms'/None",
          duration_seconds("6.904s") == 6.904 and duration_seconds("500ms") == 0.5 and duration_seconds(None) == 0.0)

    fams = metric_families(spawns, build_seconds=41.0)
    gate = _fam(fams, "paperkit_gate_seconds")
    check("gate_seconds rolls up check_seconds per project (paper = 0.4 + 3.5)",
          _point(gate, project="paper") == 3.9 and _point(gate, project="canary") == 1.0)
    disc = _fam(fams, "paperkit_discriminate_seconds")
    check("discriminate_seconds is the Δ-mnemonic subset ONLY (paper=0.4; canary, a TestRunner, absent)",
          _point(disc, project="paper") == 0.4 and _point(disc, project="canary") is None)
    check("build_seconds passes through as one unlabeled point",
          _fam(fams, "paperkit_build_seconds")["points"] == [(41.0, {})])
    check("an empty execlog yields NO vacuous points (0 data points)",
          sum(len(f["points"]) for f in metric_families([])) == 0)
    check("DELTA is the OWNER's set, read not copied (PkEval ∈, TestRunner ∉)",
          "PkEval" in DELTA and "TestRunner" not in DELTA)

    print("\n⟨P, F, δ⟩ minimum-delta pair — the Δ-subset boundary\n")
    paper_eval = Spawn("PkEval", "@@+bib+paperkit_paper//:c__eval", 0.4)
    p = _point(_fam(metric_families([paper_eval]), "paperkit_discriminate_seconds"), project="paper")
    f = _point(_fam(metric_families([Spawn("TestRunner", "@@+bib+paperkit_paper//:c__eval", 0.4)]),
                    "paperkit_discriminate_seconds"), project="paper")
    ok = p == 0.4 and f is None
    fails.append("delta-subset") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}one spawn's mnemonic flips whether discriminate_seconds sees it")
    print("      P (PkEval ∈ DELTA):     discriminate_seconds{paper} = 0.4")
    print("      F (TestRunner ∉ DELTA): discriminate_seconds{paper} absent (gate/check still see it)")
    print("      δ (min delta): one spawn's mnemonic, DELTA-member vs not\n")

    if fails:
        print(f"OTLP-PARSE: FAIL ({len(fails)} drifted)")
        return 1
    print("OTLP-PARSE: PASS (11 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
