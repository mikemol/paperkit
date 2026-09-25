#!/usr/bin/env python3
# Ρ·report·grounding — rpt-dag's DISCRIMINATING witness: the DAG the figure plots actually exists.
#
# ⚑ WHY NOT `fresh:dag.svg`.  rpt-dag opens the dag section and claims the paper's GROUNDING DAG
# (rests-on, distinct from prose order) can be walked from foundational atoms to the theses they
# support, with each claim's adequacy grade plotting against its grounding depth.  That is a
# proposition about the DATA.  `fresh:dag.svg` asserts the committed figure matches its generator
# — a proposition about the FILE — and rpt-dag-fig and rpt-fig-data already carry it, so reusing
# it here would put three claims on one witness: the collapse this project was just split to fix.
#
# The distinction is load-bearing rather than pedantic.  dag_svg() renders whatever _delta("paper")
# returns; if the paper lost every rests-on edge the figure would still regenerate, still match its
# committed copy, and `fresh:dag.svg` would still be green — while rpt-dag's claim had become
# false.  A witness that cannot fail when the proposition is false is not a witness for it.
#
# It reads the SAME records dag_svg() plots (_delta("paper"), i.e. discriminate --json) rather than
# re-parsing the bib: the claim is about what the figure shows, so the witness and the figure must
# not be able to disagree about their input.
#
# What this asserts, each independently falsifiable:
#   1. the paper HAS grounding edges among graded claims (the claim's parenthetical: it is the one
#      document that does)
#   2. the graph is ACYCLIC, so "grounding depth" is well-defined and the walk terminates
#   3. there are foundational atoms (depth 0) AND claims above them — a walk to plot
#   4. the clamp relation rpt-clamp describes is present: every record carries an effective grade
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen  # noqa: E402


def main() -> int:
    try:
        records = gen._delta("paper")
    except (gen.CannotGrade, subprocess.SubprocessError) as e:
        # ⚑ NOT a refutation — a grader that could not RUN says nothing about the claim.  Since
        # Γ, _delta RAISES this rather than returning [], so a cannot-run and an ungraded corpus
        # are finally distinguishable here.  Exit 3 = resolver._CANNOT_RUN.
        print(f"could not grade the paper: {e}\nNot evaluated; this is NOT a refutation of "
              "rpt-dag.", file=sys.stderr)
        return 3

    if not records:
        # Now unambiguous: the grader RAN and graded nothing.  A paper whose cited set is empty
        # has no grounding DAG to walk, which IS a refutation of rpt-dag's claim.
        print("discriminate --json paper graded NO claims — there is no grounding DAG to walk, "
              "so rpt-dag's claim is not merely unwitnessed but false", file=sys.stderr)
        return 1

    by_key = {d["key"]: d for d in records}
    edges = {k: [p for p in (d.get("rests-on") or []) if p in by_key]
             for k, d in by_key.items()}
    n_edges = sum(len(v) for v in edges.values())
    if not n_edges:
        print(f"the paper's {len(by_key)} graded claims declare NO rests-on edges among "
              "themselves — rpt-dag claims it is the one document with a grounding DAG, and "
              "there is no DAG to walk", file=sys.stderr)
        return 1

    # depth = longest path to a foundational atom; a cycle makes "grounding depth" meaningless
    depth: dict[str, int] = {}
    WALKING = -1

    def walk(k: str) -> int:
        seen = depth.get(k)
        if seen is not None:
            if seen == WALKING:
                raise ValueError(k)
            return seen
        depth[k] = WALKING
        d = 1 + max((walk(p) for p in edges.get(k, [])), default=-1)
        depth[k] = d
        return d

    try:
        for k in edges:
            walk(k)
    except ValueError as e:
        print(f"the grounding graph has a CYCLE through `{e}` — it is not a DAG, so grounding "
              "depth is undefined and the walk rpt-dag describes does not terminate",
              file=sys.stderr)
        return 1

    atoms = [k for k, d in depth.items() if d == 0]
    above = [k for k, d in depth.items() if d > 0]
    if not atoms or not above:
        print(f"the grounding graph is flat ({len(atoms)} atom(s), {len(above)} above) — there "
              "is no foundational-to-thesis walk to plot", file=sys.stderr)
        return 1

    ungraded = [k for k, d in by_key.items() if not d.get("effective_grade")]
    if ungraded:
        print(f"{len(ungraded)} claim(s) carry no effective grade "
              f"({', '.join(sorted(ungraded)[:5])}…) — rpt-dag plots grade against depth, and a "
              "claim without one cannot be placed on the vertical axis", file=sys.stderr)
        return 1

    print(f"paper's grounding DAG: {len(by_key)} graded claims, {n_edges} rests-on edges, "
          f"{len(atoms)} foundational atom(s), depth 0..{max(depth.values())}, acyclic; "
          "every claim carries an effective (clamped) grade")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
