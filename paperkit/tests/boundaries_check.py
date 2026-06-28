#!/usr/bin/env python3
"""Behavioral-boundary examples for Ζ·starlark's recursive check graph (Β·bnd-check).

The build graph is ONE mechanism (not per-project bespoke rules), and the local CI is COMPLETE:

  ⟨one mechanism⟩ every project is wired by the SAME bib.project extension tag, and //:hook is a
                  single test_suite whose members are uniform @proj//:{gate,adequacy,cohere} targets
                  — the recursive collapse, in the graph: a gate IS a check, one shape parameterized.
  ⟨hook complete⟩ //:hook contains, for every project GRADED in the hook (adequacy = True in
                  MODULE.bazel), BOTH its gate AND its adequacy, AND for every project whose ∂²
                  faces are gated (emerge = True), its cohere — so `bazel test //:hook` gates,
                  grades AND checks the emergence of every document.  This is the guarantee local-ci
                  delegates to the hook for: its witness asserts the pre-commit RUNS //:hook; THIS
                  asserts //:hook is complete.

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
    m = re.search(r'test_suite\(\s*name\s*=\s*"hook".*?tests\s*=\s*\[(.*?)\]', build, re.S)
    return set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()


def projects(module: str) -> dict:
    """{repo name: {graded, emerge}} — every bib.project tag and its hook-membership flags
    (adequacy = True ⇒ graded; emerge = True ⇒ its ∂² faces are gated)."""
    out = {}
    for line in module.splitlines():
        if "bib.project(" in line:
            n = re.search(r'name\s*=\s*"([^"]+)"', line)
            if n:
                out[n.group(1)] = {"graded": "adequacy = True" in line, "emerge": "emerge = True" in line}
    return out


def required(module: str) -> list:
    """Every target //:hook MUST carry: gate+adequacy per GRADED project, cohere per EMERGE project."""
    req = []
    for name, flags in projects(module).items():
        if flags["graded"]:
            req += [f"@{name}//:gate", f"@{name}//:adequacy"]
        if flags["emerge"]:
            req.append(f"@{name}//:cohere")
    return req


def incomplete(build: str, module: str) -> list:
    """The required targets MISSING from //:hook (empty = complete)."""
    hook = hook_tests(build)
    return [t for t in required(module) if t not in hook]


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    projs = projects(MODULE)
    hook = hook_tests(BUILD)

    print("Β·bnd-check — the recursive check graph's boundary\n")
    print("⟨one mechanism⟩\n")
    check("every project is wired by the SAME bib.project tag (no bespoke per-project rule)",
          len(projs) >= 4 and MODULE.count("bib.project(") == len(projs))
    check("//:hook is a SINGLE test_suite", BUILD.count('name = "hook"') == 1)
    check("the hook's members are uniform @proj//:{gate,adequacy,cohere} targets (one shape)",
          bool(hook) and all(re.match(r"@\w+//:(gate|adequacy|cohere)$", t) for t in hook))

    print("\n⟨hook complete⟩\n")
    graded = [n for n, f in projs.items() if f["graded"]]
    emerge = [n for n, f in projs.items() if f["emerge"]]
    miss = incomplete(BUILD, MODULE)
    check(f"hook-graded projects discoverable from MODULE (adequacy=True): {', '.join(graded) or 'none'}", bool(graded))
    check("//:hook contains each graded project's gate AND adequacy",
          not [t for t in miss if t.endswith((":gate", ":adequacy"))])
    check(f"//:hook contains each emerge project's cohere (the ∂² gate): {', '.join(emerge) or 'none'}",
          bool(emerge) and not [t for t in miss if t.endswith(":cohere")])

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    victim = f"@{graded[0]}//:adequacy"
    f_build = BUILD.replace(f'"{victim}",', "", 1).replace(f'"{victim}"', "", 1)
    ok = (not incomplete(BUILD, MODULE)) and (victim in incomplete(f_build, MODULE))
    fails.append("hook-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}dropping {victim} from //:hook is CAUGHT as an incomplete local CI")
    print(f"      P (intact):  //:hook lists every graded project's gate + adequacy → complete")
    print(f"      F (dropped): {victim} removed → completeness flags the gap")
    print(f"      δ (min delta): one adequacy target in the //:hook test_suite\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (6 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
