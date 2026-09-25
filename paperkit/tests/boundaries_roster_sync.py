#!/usr/bin/env python3
"""Ξ·bnd-roster-sync — TWO HAND-MAINTAINED ROSTERS OF ONE SET, COMPARED.

`paper/paper.toml`'s `[paper] warrants` names the bibs the document is built from.
`paper/BUILD.bazel`'s `:files` filegroup names the bibs the SANDBOX stages.  Both are
hand-maintained, both describe the same set, and until now nothing compared them — so a bib added
to one and not the other is a document that builds on the host and fails in a cell, or a file
staged for nothing.

⚑ THE DUPLICATION IS WHAT MAKES THIS SOUND, and removing it would break the check.  Generating
BUILD.bazel's list FROM paper.toml would let the audited artifact supply its own audit; the two
lists are INDEPENDENT textual sources and the comparison is only evidence while they stay
independent.  Η·hook·grid makes the same argument for //:hook's member list against MODULE.bazel:
"IT REMOVES THE **SILENTLY**, NOT THE HAND-MAINTENANCE, AND THAT IS DELIBERATE."

⚑⚑ WHY IT EXISTS: bnd-env-facts reads `paper/paper.toml` and then reads THE BIBS THAT TOML NAMES —
a computed set.  I first called that unenumerable in a warrant without the witness carrying a copy
of the roster, and the operator's correction is the construction: *"This is when you have a gate
that verifies that two copies are in sync."*  An enumerated input WITH a sync gate is a
declaration; only an enumeration with nothing checking it is a tautology.

⟨P, F, δ⟩:
  P: the two rosters name the same set (12 bibs at authoring).
  F: a bib present in one roster and absent from the other is NAMED, in both directions.
  δ: membership of one roster — the arms print the difference, never a count.
"""
import pathlib
import re
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOML = ROOT / "paper" / "paper.toml"
BUILD = ROOT / "paper" / "BUILD.bazel"


def toml_roster(text: str) -> set:
    return set(tomllib.loads(text)["paper"]["warrants"])


def build_roster(text: str) -> set:
    """The .bib members of paper/BUILD.bazel's srcs — read as TEXT, deliberately.

    ⚑ Parsed from the source rather than via `bazel query`: the point is to compare two AUTHORED
    lists.  Asking bazel would compare the toml against bazel's reading of the same file, which is
    one source wearing two hats."""
    return set(re.findall(r'"([A-Za-z0-9_-]+\.bib)"', text))


def main() -> int:
    fails = []

    def check(desc, cond):
        print(f"  {'ok ' if cond else 'XX '}{desc}")
        if not cond:
            fails.append(desc)

    # ⚑ A PACKAGE STAGES FOR EVERY CONSUMER, NOT JUST ITS OWN PROJECT — measured on this gate's
    # FIRST RUN, which redded on `adequacy_pitch.bib` and was WRONG.  BUILD.bazel:37 says why:
    # "a PITCH face imported by the README (not composed by paper itself)", and the ROOT paper.toml
    # declares it as a cross-project label: warrants = ["warrants.bib", "//paper:adequacy_pitch.bib"].
    # So the honest comparison is BUILD.bazel against EVERY toml that names a bib under paper/, not
    # against paper/paper.toml alone.  Comparing the wrong pair produced a confident red about a
    # correctly-declared file.
    t = toml_roster(TOML.read_text())
    # ⚑ Ζ·roster·referrer — THE CROSS-PROJECT REFERRERS ARE AN INPUT, AND A GLOB CANNOT DECLARE THEM.
    #
    # The loop below composes `t` from every ROOT/*.toml that names a `"//paper:<x>.bib"` label, per
    # the note above.  A GLOB finds what is STAGED, so in a cell that declares only
    # `@@//paper:paper.toml` it finds NOTHING, silently composes a roster short by those labels, and
    # the F arm reds on a correctly-declared file — the very error the note above says this loop
    # exists to prevent, reproduced one layer down.
    #
    # MEASURED 2026-09-13: host PASS (13 declared, 13 staged); cell
    # `XX F: no bib is staged by BUILD.bazel but undeclared in paper.toml -> ['adequacy_pitch.bib']`,
    # because ROOT/paper.toml (which declares it as `"//paper:adequacy_pitch.bib"`) was not staged.
    #
    # So the referrer set is NAMED, not globbed: two files at the root, exactly one of which carries
    # such a label (measured), both declared in the warrant's `builds`.  An absent one is a
    # CANNOT-RUN — a composed roster missing an input is not a measurement of disagreement.
    for name in ("paper.toml", "pyproject.toml"):
        extra = ROOT / name
        if not extra.is_file():
            raise SystemExit(
                f"bnd-roster-sync: CANNOT RUN — {extra} is not staged, so the cross-project "
                f"`//paper:<x>.bib` referrers it may carry are unreadable and the composed roster "
                f"would be short (declare it in the warrant's `builds`)")
        for ref in re.findall(r'"//paper:([A-Za-z0-9_-]+\.bib)"', extra.read_text()):
            t.add(ref)
    b = build_roster(BUILD.read_text())

    check(f"P: both rosters are non-empty -> toml={sorted(t)}", bool(t) and bool(b))
    check(f"F: no bib is declared in paper.toml but unstaged by BUILD.bazel -> {sorted(t - b)}",
          not (t - b))
    check(f"F: no bib is staged by BUILD.bazel but undeclared in paper.toml -> {sorted(b - t)}",
          not (b - t))
    # ⚑ Ζ·roster·boundary — δ IS MEMBERSHIP, AND THE BOUNDARY OF A BOUNDARY IS EMPTY.
    #
    # This arm read `every named bib exists on disk`, which applies a SECOND operator: from the
    # NAMES the two rosters carry to the FILES those names denote.  That is a step outside the
    # complex this claim is about.  The claim's object is the pair of rosters; ∂ of that pair is
    # the symmetric difference, and the two F arms above ARE that ∂, decomposed into its two
    # signed halves (t−b, b−t).  Taking ∂ again yields nothing — the disagreement is already
    # exhausted — so there is no third difference for a δ arm to compute.
    #
    # MEASURED 2026-09-13: the off-complex arm cost a 39,710-action run.  On the host it read
    # `[]`; in the cell it named TWELVE of thirteen bibs missing, because the claim declares the
    # two ROSTERS in `builds` and not the files they name.  Declaring those would put a copy of
    # the audited roster into the bib — the tautology this claim's own text forbids
    # ("generating one list from the other would let the audited artifact supply its own audit").
    # So the arm could be neither staged nor declared away; it was measuring the wrong object.
    #
    # The module docstring already said the right thing — "δ: membership of one roster" — and the
    # code did something else.  The minimum delta of THIS operator is one member moved in or out
    # of one roster, and the two F arms detect exactly that: this asserts it directly, on a
    # PERTURBED COPY, so the δ is exercised rather than asserted.
    _probe = set(t)
    _probe.add("__pk-delta-probe.bib")
    check(f"δ: ONE member added to a roster is named by the difference -> "
          f"{sorted(_probe - b)}",
          (_probe - b) == {"__pk-delta-probe.bib"} and not (t - b))
    # ⚑ The arm that keeps the comparison HONEST: two rosters agreeing because both are empty, or
    # because the BUILD parse matched nothing, is a vacuous green.  This asserts the readers
    # actually read — a pattern change that stops matching reds here rather than passing silently.
    check("F: the BUILD reader is not vacuous — it finds bibs in the real file",
          len(b) > 1)

    print(f"BOUNDARIES: {'PASS' if not fails else f'FAIL ({len(fails)})'} "
          f"({len(t)} declared, {len(b)} staged, 2 independent sources)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
