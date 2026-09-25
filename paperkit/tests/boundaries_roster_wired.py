#!/usr/bin/env python3
"""Ξ·bnd-roster-wired — THE ENUMERATED LABEL ROSTERS ARE GATED AGAINST THEIR OWNERS.

`arch/warrants.bib` enumerates paper.toml LABELS so its witnesses depend on the specific files they
open rather than on whole packages.  An enumeration with nothing checking it is a guard carrying its
own copy of the set it guards; an enumeration WITH a sync gate is a declaration.  Operator's
construction, verbatim: *"This is when you have a gate that verifies that two copies are in sync."*

TWO ROSTERS, TWO OWNERS:
  arch-projects      <- MODULE.bazel's `bib.project(... project = "X")` calls.  The WIRED set.
  arch-report-scope  <- the paper.toml files on disk.  The DISCOVERED set (report/gen.py's
                        `_all_docs()` does ROOT.rglob("paper.toml"), so the tree is the owner).

⚑ guide/assets/starter is EXCLUDED from the discovered set deliberately: no BUILD.bazel, because it
is a starter FIXTURE rather than a project, and gen.py's own filter drops it.  Stated here so the
exclusion is declared rather than silently absent.

⟨P, F, δ⟩:
  P: both enumerations match their owners exactly.
  F: a project wired in MODULE.bazel but missing from arch-projects' labels is NAMED (and the
     reverse); a paper.toml on disk but missing from arch-report-scope's labels is NAMED (and the
     reverse).
  δ: membership — the arms print the difference, never a count.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
# ⚑ NESTED FIXTURES ARE EXCLUDED BY THE CONSUMER'S OWN FILTER, and my first version of this
# roster derived the set from `git ls-files` without applying it.  report/gen.py's _all_docs()
# docstring: "EVERY document in the repository (a dir with a paper.toml), excluding nested fixtures
# and the report itself", implemented as
#     any(o not in (d, ROOT) and o in d.parents for o in tomls)
# — a dir NESTED UNDER another dir that has a paper.toml is dropped.  So paper/checks/fixture is
# not in the census this claim measures, and declaring its label made the warrant describe a set
# its consumer never sees.  Deriving the owner from the tree is not enough; the owner is the tree
# AS THE CONSUMER FILTERS IT.
FIXTURES = ("guide/assets/starter",)


def _nested(proj: str, all_projs: set) -> bool:
    """gen.py's filter: dropped when some OTHER project directory is an ancestor."""
    if proj == ".":
        return False
    parts = proj.split("/")
    return any("/".join(parts[:i]) in all_projs for i in range(1, len(parts)))


def _label(proj: str) -> str:
    return "@@//:paper.toml" if proj == "." else f"@@//{proj}:paper.toml"


def wired_owner() -> set:
    """MODULE.bazel's bib.project calls — the roster arch-projects counts.

    ⚑ The pattern accepts a SLASH.  Measured: `[a-z.]+` silently dropped `paperkit/library`, which
    would have gated a 13-project claim against a 12-label roster — the enumeration wrong in the
    instrument written to check enumerations."""
    t = (ROOT / "MODULE.bazel").read_text()
    return {_label(p) for p in re.findall(r'bib\.project\([^)]*project = "([^"]+)"', t)}


def disk_owner() -> set:
    """Every paper.toml THE CELL WAS GIVEN — the set report/gen.py's rglob discovers.

    ⚑ Ζ·roster·hermetic — THE FILESYSTEM, NOT GIT.  This shelled `git -C <ROOT> ls-files
    '*paper.toml'` and could not pass in a sandbox.  MEASURED in a live execroot:

        git -C execroot ls-files '*paper.toml'   ->  15 files
        find execroot -name paper.toml           ->   1 file

    `execroot/.git` is a SYMLINK to the live checkout, so git reads the REAL repository index while
    every file the suite stats is the sandbox's staged copy — **two different trees, disagreeing by
    construction**, and no amount of declaring fixes it.  Walking what the cell was GIVEN makes the
    declaration and the measurement one object: a project that reaches `builds` is visible here, and
    one that does not is not, which is exactly the property a roster gate needs.

    ⚑⚑ The operator's rule, which is the general form: build artifacts, not symlinks — and
    `--config=remote` to force these to the surface, because a remote executor has no workspace to
    fall back to.
    """
    projs = {str(q.parent.relative_to(ROOT)) if q.parent != ROOT else "."
             for q in ROOT.rglob("paper.toml")
             if ".git" not in q.parts and "bazel-" not in str(q) and "build" not in q.parts}
    return {_label(p) for p in projs
            if p not in FIXTURES and not _nested(p, projs)}


def declared(key: str) -> set:
    """The `builds` labels a warrant enumerates — parsed from the bib TEXT.

    Read as text on purpose: the point is to compare two AUTHORED lists.  Asking bazel would compare
    the bib against bazel's reading of the same bib, which is one source wearing two hats."""
    t = (ROOT / "arch" / "warrants.bib").read_text()
    i = t.index("@misc{" + key + ",")
    body = t[i:t.index("\n}", i)]
    m = re.search(r'^\s*builds\s*=\s*\{([^}]*)\}', body, re.M)
    return {x.strip() for x in m.group(1).split(",") if "paper.toml" in x} if m else set()


def main() -> int:
    fails = []

    def check(desc, cond):
        print(f"  {'ok ' if cond else 'XX '}{desc}")
        if not cond:
            fails.append(desc)

    w, d = wired_owner(), disk_owner()
    pw, pr = declared("arch-projects"), declared("arch-report-scope")

    check(f"P: the owners are non-empty and the readers are not vacuous -> wired={len(w)} disk={len(d)}",
          len(w) > 1 and len(d) > 1 and len(pw) > 1 and len(pr) > 1)
    check(f"F: no WIRED project is missing from arch-projects' labels -> {sorted(w - pw)}", not (w - pw))
    check(f"F: arch-projects declares no label that MODULE.bazel does not wire -> {sorted(pw - w)}",
          not (pw - w))
    check(f"F: no paper.toml ON DISK is missing from arch-report-scope's labels -> {sorted(d - pr)}",
          not (d - pr))
    check(f"F: arch-report-scope declares no paper.toml absent from disk -> {sorted(pr - d)}",
          not (pr - d))

    print(f"BOUNDARIES: {'PASS' if not fails else f'FAIL ({len(fails)})'} "
          f"({len(w)} wired, {len(d)} on disk, 2 rosters gated against their owners)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
