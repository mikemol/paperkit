#!/usr/bin/env python3
"""Λ·arch — the witnesses for ARCHITECTURE.md's structural claims.

⚑ A COUNT IN PROSE IS A CLAIM NOTHING RE-DERIVES.  ARCHITECTURE.md asserted "17 modules" and
"eight projects" (the latter THREE times).  Measured 2026-09-10: **26** non-test files and **12**
wired projects.  Every number was wrong, and nothing in the repo could say so — the document had no
`paper.toml`, no `.bib`, no build target.

⚑⚑ AND "EIGHT" IS THE COMPONENT COUNT.  `components.bzl` declares exactly eight components
(delta, gate, kernel, library_kernel, model, project, resolver, tests), so the prose had conflated
COMPONENTS with PROJECTS.  **A bare number-refresh from 8 to 12 would have preserved the category
error while looking correct** — which is why each witness below names WHICH count it asserts and
reads it from the manifest that OWNS that count, never from a second copy.

THE OWNERS, one per claim:
  components / modules → paperkit/components.bzl  (the partition `bnd-components` gates as TOTAL)
  wired projects       → MODULE.bazel bib.project (the wiring `hook_grid.py` gates)
  the two pk_grade     → tools/grade.bzl, tools/calc.bzl (§3.6, still TRUE)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _components():
    ns: dict = {}
    exec(compile((ROOT / "paperkit" / "components.bzl").read_text(),   # noqa: S102 — a data file
                 "components.bzl", "exec"), ns)
    return ns["COMPONENTS"], ns.get("DEPS", {})


def _wired():
    return re.findall(r'bib\.project\(\s*name\s*=\s*"([^"]+)"[^)]*?project\s*=\s*"([^"]+)"',
                      (ROOT / "MODULE.bazel").read_text())


def arch_components():
    # The engine is partitioned into COMPONENTS, and that number is not the project count.
    comps, deps = _components()
    assert len(comps) == 8, f"the component partition has {len(comps)} members, not 8"
    assert set(deps) == set(comps), "DEPS and COMPONENTS name different sets"


def arch_modules():
    # "modules" = the NON-TEST files in the partition.  Stated separately from the component count
    # precisely because the prose conflated the two.
    comps, _ = _components()
    files = [f for fs in comps.values() for f in fs]
    non_test = [f for f in files if not f.startswith("tests/")]
    assert len(non_test) == 26, (
        f"the engine has {len(non_test)} non-test modules, not 26 — update the claim, and note "
        f"that this count is NOT the component count ({len(comps)})")


def arch_projects():
    # WIRED projects — the ones MODULE.bazel declares, which is what "the repository is N projects"
    # can honestly mean.  `paper.toml` files on disk is a DIFFERENT number (fixtures, starters).
    # ⚑ 13, NOT 12 — and the number moved WITHIN the tick that wrote this witness.  The claim was
    # authored at 12, then wiring `arch/` itself made it 13 and this assertion caught it before the
    # gate did.  A prose count would have shipped stale on day one; that is the whole argument.
    wired = _wired()
    assert len(wired) == 13, f"MODULE.bazel wires {len(wired)} projects, not 13"
    # ⚑ Σ-F6 — THE SECOND HALF USED TO `rglob` THE WHOLE TREE, AND WAS UNVERIFIABLE BY
    # CONSTRUCTION.  It asserted `on_disk > wired` (fixtures and starters are projects nothing
    # wires).  True on the host; in the SANDBOX only the staged projects exist, so `on_disk` can
    # never exceed `wired` and the claim graded `baseline: false` — a check that CANNOT pass where
    # it is run is the `vacuous` shape this repo refuses, and no `reads` declaration fixes it,
    # because the missing files are the ones deliberately NOT staged.
    #
    # The distinction survives as an assertion about the DECLARATIONS, which is what MODULE.bazel
    # owns and what the sandbox actually stages: a wired project names a real directory, and the
    # roster is exactly the thing a reader would otherwise have to count by hand.
    for name, proj in wired:
        assert proj == "." or (ROOT / proj / "paper.toml").exists(), (
            f"MODULE.bazel wires {name!r} at {proj!r}, which carries no paper.toml — the wiring "
            f"names a project that is not there")


def arch_two_pk_grade():
    # §3.6's second bullet, still TRUE (verified 2026-09-10): two rules share one name.
    hits = [f for f in ("grade.bzl", "calc.bzl")
            if re.search(r'^pk_grade = rule\(', (ROOT / "tools" / f).read_text(), re.M)]
    assert hits == ["grade.bzl", "calc.bzl"], (
        f"the two `pk_grade` rules §3.6 records are now {hits} — if one was removed the tension is "
        f"RESOLVED and the bullet should go, not be relaxed")


def arch_tension_report_scope():
    # ⚑ §3.6's THIRD bullet is now FALSE, and this witness asserts the CORRECTION.
    # It read: "the committed REPORT.md/assets cover only paper/README/boundaries.  render, image,
    # config, setup are newer and unrepresented."  Α wired report+image; Β fixed the document
    # identity so the census names every project.  A tensions ledger whose entries go stale
    # SILENTLY is the defect claims exist to prevent — so the retirement is gated, not narrated.
    sys.path.insert(0, str(ROOT / "report"))
    import gen
    docs = {n for n, _ in gen._all_docs()}
    assert len(docs) >= 11, f"the report census covers {len(docs)} documents, not >= 11"
    for name in ("render", "config", "image", "setup"):
        assert name in docs, f"{name!r} is absent from the report census — the §3.6 tension is BACK"


def arch_tension_two_tiers():
    # ⚑ §3.6's FOURTH bullet is now FALSE too: "render/image/report are on-demand ... the hook does
    # not exercise the render/image/report claims."  Measured: _ondemand_names() is EMPTY.
    sys.path.insert(0, str(ROOT / "report"))
    import gen
    ondemand = gen._ondemand_names()
    assert not ondemand, (
        f"{sorted(ondemand)} are on-demand again — §3.6's two-tier tension has returned and the "
        f"claim retiring it must be withdrawn")
    assert "render" in gen._hook_names(), "render left //:hook — the tension has returned"


CHECKS = {
    "arch-components": arch_components,
    "arch-modules": arch_modules,
    "arch-projects": arch_projects,
    "arch-two-pk-grade": arch_two_pk_grade,
    "arch-report-scope": arch_tension_report_scope,
    "arch-two-tiers": arch_tension_two_tiers,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in CHECKS:
        print(f"usage: arch.py <{'|'.join(CHECKS)}>", file=sys.stderr)
        return 2
    CHECKS[argv[1]]()
    print(f"claim {argv[1]}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
