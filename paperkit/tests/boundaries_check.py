#!/usr/bin/env python3
"""Behavioral-boundary examples for Ζ·starlark's recursive check graph (Β·bnd-check).

The build graph is ONE mechanism (not per-project bespoke rules), and the local CI is COMPLETE:

  ⟨one mechanism⟩ every project is wired by the SAME bib.project extension tag, and //:hook is a
                  single test_suite whose members are uniform @proj//:{gate,adequacy,cohere} targets —
                  the recursive collapse, in the graph: a gate IS a check, one shape parameterized.
  ⟨hook complete⟩ //:hook contains, for every project GRADED in the hook (adequacy = True in
                  MODULE.bazel), BOTH its gate AND its adequacy; and for every EMERGE project
                  (emerge = True), its cohere — the ∂² coherence gate over the def-sweep grid (the
                  Ξ·dag·eval closure cells).  So `bazel test //:hook` gates, grades, AND coheres every
                  document.  This is the guarantee local-ci delegates to the hook for: its witness
                  asserts the pre-commit RUNS //:hook; THIS asserts //:hook is complete.
  ⟨harness sound⟩ //:hook carries the ONE harness canary (//canary:canary, Ζ·canary) — the
                  positive control that fails LOUD when the mutation harness degrades.  The
                  member-shape check names the canary as the exact non-project residual
                  (set-equality, Λ·cardinality — never a bare "extra members allowed").

    python3 paperkit/tests/boundaries_check.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = (ROOT / "BUILD.bazel").read_text()
MODULE = (ROOT / "MODULE.bazel").read_text()


def hook_tests(build: str) -> set:
    """The //:hook member list.

    ⚑ THIS USED A NON-GREEDY `\\[(.*?)\\]` AND SILENTLY LOST A MEMBER.  The member list's own
    comments carry wiki-style refs — `[[place-by-ownership-not-need]]` at BUILD.bazel:191 — so the
    first `]` a non-greedy match finds is INSIDE a comment, four lines above the real close of the
    list.  MEASURED 2026-09-09: that scrape captured 24 members while `bazel query tests(//:hook)`
    reported 25, dropping `@paperkit_library//:decisions` (BUILD.bazel:194) — the very member whose
    earlier omission the surrounding comment was written to narrate.  So this suite's completeness
    proof ran over 24 of 25 members and reported PASS: a green that measured the scrape.

    Found by writing tools/hook_grid.py, which copied the regex and inherited the bug.

    The slice is now BRACKET-COUNTED from `tests = [` to its matching close, and only then scanned
    for quoted LABELS (`@repo//:target` or `//pkg:target`) — a bracketed wiki-ref carries no quotes,
    but the slice has to be right before that matters.
    """
    i = build.find("tests = [", build.find('name = "hook"'))
    if i < 0:
        return set()
    i = build.index("[", i)
    depth = 0
    for j in range(i, len(build)):
        if build[j] == "[":
            depth += 1
        elif build[j] == "]":
            depth -= 1
            if depth == 0:
                break
    return {t for t in re.findall(r'"([^"]+)"', build[i + 1:j])
            if t.startswith("@") or t.startswith("//")}


def projects(module: str) -> dict:
    """{repo name: {graded, emerge}} — every bib.project tag, and whether it declares adequacy = True
    (hook-graded) and/or emerge = True (contributes the ∂² coherence gate over the def-sweep grid).
    """
    out = {}
    for line in module.splitlines():
        if "bib.project(" in line:
            n = re.search(r'name\s*=\s*"([^"]+)"', line)
            if n:
                out[n.group(1)] = {"graded": "adequacy = True" in line, "emerge": "emerge = True" in line}
    return out


def incomplete(build: str, module: str) -> list:
    """The targets a project is MISSING from //:hook (empty = complete): a GRADED project owes its
    gate AND adequacy; an EMERGE project owes its cohere (the def-sweep coherence gate).
    """
    hook = hook_tests(build)
    miss = []
    for name, p in projects(module).items():
        if p["graded"]:
            miss += [f"@{name}//:{suf}" for suf in ("gate", "adequacy") if f"@{name}//:{suf}" not in hook]
        if p["emerge"] and f"@{name}//:cohere" not in hook:
            miss.append(f"@{name}//:cohere")
    return miss


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

    projs = projects(MODULE)
    hook = hook_tests(BUILD)

    print("Β·bnd-check — the recursive check graph's boundary\n")
    print("⟨one mechanism⟩\n")
    check("every project is wired by the SAME bib.project tag (no bespoke per-project rule)",
          len(projs) >= 4 and MODULE.count("bib.project(") == len(projs))
    check("//:hook is a SINGLE test_suite", BUILD.count('name = "hook"') == 1)
    # Λ·cardinality — the non-project residual is the OWNED set {//canary:canary}, asserted by
    # set-EQUALITY (a bare "project-shaped or not" filter would silently admit any stray member).
    # `decisions` (Μ·sweep·atom) is a fourth per-project member KIND, emerge-only like cohere: the
    # decision-coverage grid summary, built every commit so the grid twin is not emitted-but-inert.
    check("the hook's members are uniform @proj//:{gate,adequacy,cohere,decisions} targets plus exactly the harness canary",
          bool(hook) and {t for t in hook if not re.match(r"@\w+//:(gate|adequacy|cohere|decisions)$", t)} == {"//canary:canary"})

    print("\n⟨harness sound⟩\n")
    check("//:hook carries the harness canary (Ζ·canary — a degraded sandbox fails LOUD, not silently green)",
          "//canary:canary" in hook)

    print("\n⟨hook complete⟩\n")
    graded = [n for n, p in projs.items() if p["graded"]]
    emerge = [n for n, p in projs.items() if p["emerge"]]
    check(f"hook-graded projects discoverable from MODULE (adequacy=True): {', '.join(graded) or 'none'}", bool(graded))
    check(f"emerge projects discoverable from MODULE (emerge=True): {', '.join(emerge) or 'none'}", bool(emerge))
    check("//:hook contains each graded project's gate+adequacy AND each emerge project's cohere", not incomplete(BUILD, MODULE))

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    victim = f"@{graded[0]}//:adequacy"
    f_build = BUILD.replace(f'"{victim}",', "", 1).replace(f'"{victim}"', "", 1)
    ok = (not incomplete(BUILD, MODULE)) and (victim in incomplete(f_build, MODULE))
    fails.append("hook-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}dropping {victim} from //:hook is CAUGHT as an incomplete local CI")
    print("      P (intact):  //:hook lists every graded project's gate + adequacy → complete")
    print(f"      F (dropped): {victim} removed → completeness flags the gap")
    print("      δ (min delta): one adequacy target in the //:hook test_suite\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    bad = len([b for b in ran if not b])
    if bad:
        print(f"BOUNDARIES: FAIL ({bad} of {len(ran)} behaviors drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
