#!/usr/bin/env python3
"""Ξ·bnd-genre-pure — `PK-GENRE-PURE`, as a GATED claim rather than a ledger note.

⚑ WHY A BLOCKED VERDICT NEEDS A WITNESS.  Four residual genres were recorded BLOCKED on three
obstacle keys.  Two of those keys turned out to be FALSE — `PK-GENRE-BLIND` was retired by Κ, and
`PK-BIB-PROVENANCE` was never true at all (`_src` had been on every record since parse time,
Ξ-F1).  Both survived as long as they did because a verdict living only in prose is re-read, never
re-derived: `fresh-comments-are-hypotheses-too`.

So the surviving obstacle gets the treatment the plan's Phase F specifies — a claim whose check
WITNESSES the obstacle, and which therefore **goes RED the day the obstacle is removed**.  A
BLOCKED genre that cannot notice being unblocked is a stall wearing a verdict's clothes.

WHAT `PK-GENRE-PURE` ASSERTS.  A genre is a pure function of the grouping (plus the records), so
troubleshooting's ordering — *which observation to make NEXT* — is inexpressible, because that is a
function of the CURRENT FAILURE STATE and no such state reaches a genre.

TWO INDEPENDENT HALVES, both checked, because either alone is weak:

  1. ⚑ NO RECORD FIELD CARRIES A VERDICT.  `check` is present on nearly every record and is the
     DECLARED VERIFIER STRING (`cmd:python3 …`, `claim:<key>`) — what WOULD verify the claim, never
     whether it passes.  A genre can read what a claim's verifier IS; it cannot ask what is failing.

  2. ⚑ `observe` CANNOT COMPUTE ONE, BY THE COMPONENT LATTICE.  `components.bzl` declares
     `"delta": ["gate", "project", …]` — the grader DEPENDS ON the projector.  So `project.py`
     importing `grader`/`discriminate` would be an UPWARD edge, which `bnd-components` refuses
     ("every import edge respects the component DAG").  The obstacle is therefore structural, not
     an oversight someone forgot to fix.

⚑ THIS CHECK IS DESIGNED TO FAIL LOUDLY IF THE OBSTACLE IS LIFTED.  If a verdict field ever appears
on a record, or the lattice is rearranged so project may read the grader, this reds — and the
correct response is to DELETE it and build troubleshooting, not to relax it.  That is what makes a
BLOCKED verdict falsifiable rather than permanent.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paperkit"))

# The words a VERDICT would be spelled with, as opposed to a declared verifier.  `check` is
# deliberately NOT here: carrying the verifier's NAME is what a record legitimately does.
VERDICT_FIELDS = {"verdict", "passed", "failed", "status", "result", "grade", "outcome", "state"}


def engine_vocabulary() -> set:
    """The engine's OWN field vocabulary — `bib._SCALAR | bib._LIST`.

    ⚑ THIS READS THE VOCABULARY, NOT A PARSED CORPUS, AND THE FIRST VERSION READ THE CORPUS.
    That was vacuous: `parse` PROJECTS each entry onto `_SCALAR + consumer_fields` and loud-drops
    everything else (`bib.py:~240`), so a `verdict = {pass}` written into a .bib never reaches a
    record — the check could not fail no matter what a bib said.  Measured: a falsifiability probe
    added exactly that field and this suite stayed green.

    An unfalsifiable check asserting an obstacle is the same defect as an unfalsifiable claim, and
    is precisely what retired `PK-BIB-PROVENANCE` (Ξ-F1) so slowly.  So the assertion is about the
    ENGINE's vocabulary — the thing that would have to change for a verdict to become expressible
    — and a project's `consumer_fields` are checked separately, since those CARRY verbatim.
    """
    import bib
    return set(bib._SCALAR) | set(bib._LIST)


def declared_consumer_fields() -> set:
    """Every `consumer_fields` name any project declares — the other route onto a record."""
    import tomllib
    # ⚑ Ζ·genre·pure·vacuous — THE POPULATION COMES FROM ITS OWNER, NOT FROM A GLOB.
    #
    # This globbed `*/paper.toml` and skipped what it could not open.  Three defects in one line:
    #
    #   1. THE SKIP WAS UNREACHABLE.  `Path.glob` only yields paths that EXIST, so
    #      `if not toml.exists(): continue` could never fire — the guard read like a safety net
    #      and was dead code.
    #   2. THE GLOB IS WRONG IN BOTH DIRECTIONS.  Measured: it matches
    #      `bazel-paperkit/paper.toml` (a convenience symlink into the output base, not a project)
    #      and MISSES `paperkit/library/paper.toml` (nested one level deeper than `*/` reaches).
    #      13 projects declared, 12 globbed, 11 correct.
    #   3. AND IN A CELL IT FINDS WHAT WAS STAGED.  The result feeds an ABSENCE arm
    #      (`leaked = VERDICT_FIELDS & (vocab | consumer)`), so an empty `consumer` only SHRINKS
    #      the intersection: the arm goes green having checked nothing.  The warrant declares only
    #      `@@//paperkit:components.bzl`, so a cell stages no toml and the arm prints
    #      "nor in 0 declared consumer_field(s)" and passes.  The other three witnesses in this
    #      class failed LOUDLY when their globs came up short; this one could not surface itself.
    #
    # MODULE.bazel is the owner of WHICH PROJECTS EXIST (`bib.project(project = "...")`), so the
    # roster is read from there and every named toml must be readable — an absent one is a
    # CANNOT-RUN, because an absence computed over a short population is not evidence.
    import re
    roster = re.findall(r'bib\.project\([^)]*project = "([^"]+)"',
                        (ROOT / "MODULE.bazel").read_text())
    if len(roster) < 2:
        raise SystemExit(
            "bnd-genre-pure: CANNOT RUN — MODULE.bazel names fewer than two projects, so the "
            "consumer_fields population cannot be derived (is it staged?)")
    out = set()
    for proj in roster:
        toml = (ROOT if proj == "." else ROOT / proj) / "paper.toml"
        if not toml.is_file():
            raise SystemExit(
                f"bnd-genre-pure: CANNOT RUN — {toml} is not staged, so the consumer_fields "
                f"{proj!r} may declare are unreadable and the absence below would be vacuous "
                f"(declare the project paper.tomls in the warrant's `builds`)")
        try:
            p_ = tomllib.loads(toml.read_text()).get("paper", {})
        except Exception:                                # noqa: BLE001 — a probe reports
            continue
        out |= set(p_.get("consumer_fields", ()))
    return out


def lattice_forbids_grader() -> tuple:
    """(forbidden, why) — does the component DAG bar `project` from importing the grader?"""
    ns: dict = {}
    exec(compile((ROOT / "paperkit" / "components.bzl").read_text(),
                 "components.bzl", "exec"), ns)          # noqa: S102 — a data file, by design
    deps = ns.get("DEPS") or {}
    comps = ns.get("COMPONENTS") or {}
    if not deps or not comps:
        return False, "could not read DEPS/COMPONENTS from components.bzl"
    # the grader lives in `delta`; does `delta` depend on `project`?
    if "project" not in deps.get("delta", []):
        return False, "`delta` does not depend on `project` — the lattice would permit the import"
    # ...and project must NOT list delta (that would be the cycle)
    if "delta" in deps.get("project", []):
        return False, "`project` declares a dep on `delta` — the lattice permits it"
    return True, ("`delta` depends on `project`, so a project→delta import is an UPWARD edge "
                  "bnd-components refuses")


def main() -> int:
    print("Ξ·bnd-genre-pure — troubleshooting is BLOCKED, and the block is falsifiable\n")
    bad = 0

    print("⟨no verdict is EXPRESSIBLE on a record⟩\n")
    vocab = engine_vocabulary()
    consumer = declared_consumer_fields()
    leaked = sorted(VERDICT_FIELDS & (vocab | consumer))
    if leaked:
        where = "the engine vocabulary" if VERDICT_FIELDS & vocab else "a project's consumer_fields"
        print(f"  XX {leaked} is carried by {where} — a genre CAN see failure state",
              file=sys.stderr)
        bad += 1
    else:
        print(f"  ok no verdict-shaped name in the engine's {len(vocab)} field(s) "
              f"nor in {len(consumer)} declared consumer_field(s)")
    if "check" in vocab:
        print("  ok `check` IS in the vocabulary — the DECLARED VERIFIER, never its result")
    else:
        print("  XX `check` absent from the vocabulary — the claim cannot be exercised",
              file=sys.stderr)
        bad += 1

    print("\n⟨the projector cannot compute one⟩\n")
    forbidden, why = lattice_forbids_grader()
    print(f"  {'ok' if forbidden else 'XX'} {why}")
    if not forbidden:
        bad += 1

    print("\n⟨P, F, δ⟩ what would REFUTE this\n")
    print("      P (blocked):  no verdict field + project may not import delta")
    print("      F (unblocked): either a verdict-shaped field on a record, OR a lattice")
    print("                     permitting project→delta")
    print("      δ (min delta): one field name, or one DEPS edge")

    if bad:
        print(f"\nbnd-genre-pure: {bad} half/halves REFUTED — the obstacle is GONE.  Delete this "
              f"check and build troubleshooting; do NOT relax it.", file=sys.stderr)
        return 1
    print("\nBOUNDARIES: PASS (2 independent halves, 1 delta) — PK-GENRE-PURE stands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
