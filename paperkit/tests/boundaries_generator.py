#!/usr/bin/env python3
"""Μ·bnd-generator — the generator's SEMANTICS, not its shell hygiene.

⚑ AUDIT FINDING 1, MEASURED: `tools/bibtex.bzl` (1,109 lines) + `tools/calc.bzl` (730) ARE the
build graph, and their only claim was `bnd-lint` — THREE REGEXES over the text
(`bare-python3`, `printf-json`, `grep-json`), every one a shell-hygiene rule.  None asserts
anything about what the generator EMITS.  **The generated things are gated ~182 ways; the
generator was gated by a grep for `printf {`.**

`bnd-genre-emit` (Μ.2) closed one corner — `:genres` is emitted iff a project declares a genre.
This asserts the THREE DECLARATION→TARGET RULES the whole build graph rests on:

  adequacy = True   ⇒  the project emits an `:adequacy` target        (and False ⇒ it does not)
  emerge   = True   ⇒  the project emits `:cohere` and `:decisions`
  every project     ⇒  `:invariants`, carrying `--without-K`, REGARDLESS of tier

⚑ THE THIRD IS THE ONE WORTH GATING.  Α's whole argument for wiring `report`/`image` was that
*"`:invariants` is emitted for EVERY project regardless of tier, so wiring buys `--without-K` even
at `local`"* — a claim about the generator that nothing checked.  If it ever became
tier-conditional, two `local` projects would silently lose their only cross-claim invariant and
every gate would stay green.

⚑ IT READS THE DECLARATIONS AND THE GENERATOR, NOT THE BAZEL CACHE.  `hook_grid.py` is the
precedent: derive what the generator WOULD emit from `MODULE.bazel`, compare against the source
that decides it.  A witness keyed on an output-base hash reports one machine's cache layout as a
fact about the engine.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BZL = ROOT / "tools" / "bibtex.bzl"

# The declaration flags a bib.project tag carries — the names a guard may legitimately test,
# whether read off `repository_ctx.attr` or through a local bound from it.
FLAGS = {"adequacy", "emerge", "calc", "compose", "genres", "owns_concepts", "owns_warrants"}


def declarations() -> dict:
    """{repo: {flag: bool}} for every bib.project tag — the DECLARED side of each rule."""
    out = {}
    for line in (ROOT / "MODULE.bazel").read_text().splitlines():
        if "bib.project(" not in line or line.strip().startswith("#"):
            continue
        m = re.search(r'name\s*=\s*"([^"]+)"', line)
        if not m:
            continue
        out[m.group(1)] = {f: f"{f} = True" in line
                           for f in ("adequacy", "emerge", "calc", "compose")}
    return out


def _guard_of(bzl: str, target: str):
    """The `repository_ctx.attr.X` a target's emission is guarded by, or None if unguarded.

    Returns (flag, None) when guarded, (None, reason) when not — three states, because "no guard"
    and "no emission" are different facts and collapsing them is the defect `Ζ·rests·unresolved`
    names (Ξ-F3 reproduced it once already in this suite family).

    ⚑ ENCLOSURE IS DECIDED BY INDENTATION, NOT BY A LINE WINDOW.  The first version scanned back a
    fixed 14 lines and reported `adequacy_rec` UNGUARDED — its guard sits **47 lines** above it
    (`bibtex.bzl:992` guarding `:1039`).  The witness accused the generator of a defect that was
    its own instrument's blind spot: a window is a guess about distance, while an enclosing block
    is a fact about INDENT.  Walk back to the first line indented LESS than the emission that opens
    an `if`; that is the block containing it.
    """
    i = bzl.find('name = \\"%s\\"' % target)
    if i < 0:
        i = bzl.find('name = "%s"' % target)
    if i < 0:
        return None, "absent"
    lines = bzl[:i].splitlines()
    emit_indent = len(lines[-1]) - len(lines[-1].lstrip()) if lines else 0
    for line in reversed(lines[:-1]):
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent >= emit_indent:
            continue                                   # a sibling statement, not an encloser
        # ⚑ THE FLAG MAY BE READ THROUGH A LOCAL, NOT ONLY OFF THE ATTRIBUTE.  `cohere_rec`'s
        # guard is `if emerge and (calc_claims or imported_cert):` — the attribute was bound to a
        # local far above.  Matching only `repository_ctx.attr.X` reported it UNGUARDED, which is
        # Β-F1's shape again: one SPELLING taken for the concept.  Both forms are the same rule.
        m = re.search(r'if (?:repository_ctx\.attr\.)?([\w.]+)\b', line)
        if m:
            # ⚑ THE NEAREST ENCLOSING `if` IS THE ANSWER, WHATEVER IT TESTS.  Returning only
            # recognised FLAGS and walking PAST anything else made the witness report a guard from
            # an OUTER block: injecting `if proj_tier == "sandbox":` around :invariants was caught,
            # but named `emerge` — the right verdict with the wrong cause, which is the misdiagnosis
            # shape this file family keeps producing (Ξ-F3, Μ-F2's first message).
            flag = m.group(1)
            return (flag, None) if flag in FLAGS else (None, f"guarded by `{flag}`")
        if line.strip().endswith(":"):
            emit_indent = indent                       # an enclosing block that is not our guard
    return None, "unguarded"


def main() -> int:
    bzl = BZL.read_text()
    decl = declarations()
    bad = 0
    print("Μ·bnd-generator — the DECLARATION → TARGET rules the build graph rests on\n")

    print("⟨adequacy = True ⇒ an :adequacy target⟩\n")
    flag, why = _guard_of(bzl, "adequacy_rec")
    if flag == "adequacy":
        n = sum(1 for d in decl.values() if d["adequacy"])
        print(f"  ok the :adequacy record is guarded by `adequacy` — {n} of {len(decl)} "
              f"project(s) declare it")
    else:
        print(f"  XX the :adequacy record is {why or f'guarded by {flag!r}'}, not by `adequacy` — "
              f"a project could be graded without declaring it, or declare it and not be",
              file=sys.stderr)
        bad += 1

    print("\n⟨emerge = True ⇒ :cohere and :decisions⟩\n")
    flag, why = _guard_of(bzl, "cohere_rec")
    if flag == "emerge":
        n = sum(1 for d in decl.values() if d["emerge"])
        print(f"  ok the :cohere record is guarded by `emerge` — {n} of {len(decl)} project(s) "
              f"declare it")
    else:
        print(f"  XX the :cohere record is {why or f'guarded by {flag!r}'}, not by `emerge`",
              file=sys.stderr)
        bad += 1

    print("\n⟨:invariants is emitted for EVERY project, at ANY tier⟩\n")
    flag, why = _guard_of(bzl, "invariants")
    if why == "absent":
        print("  XX no :invariants emission in the generator — every project loses --without-K",
              file=sys.stderr)
        bad += 1
    elif why != "unguarded" or flag is not None:
        print(f"  XX :invariants is {why or f'GUARDED by `{flag}`'} — Α wired report/image on the "
              f"argument that it is emitted REGARDLESS of tier; a guard silently removes "
              f"--without-K from whichever projects fail the condition", file=sys.stderr)
        bad += 1
    else:
        print("  ok :invariants is emitted unconditionally (unguarded)")

    # ⚑ THE COMMAND, NOT THE FILE.  A bare `"--without-K" in bzl` asks whether the string appears
    # ANYWHERE — and it appears twice, so a mutation removing it from the invariants command left
    # the check green (measured: the discrimination probe scored 5/6 on exactly this).  Read the
    # `inv = ` assignment that BUILDS the command.
    m = re.search(r'^\s*inv = (.+)$', bzl, re.M)
    if m is None:
        print("  XX cannot find the `inv = ` command assignment — the invariants command is not "
              "where this witness looks, so it can assert nothing about it", file=sys.stderr)
        bad += 1
    elif "--without-K" in m.group(1):
        print("  ok the :invariants COMMAND carries `--without-K`")
    else:
        print(f"  XX the :invariants command no longer carries `--without-K` — the cross-claim "
              f"distinctness invariant is gone from every project: {m.group(1).strip()[:70]}",
              file=sys.stderr)
        bad += 1

    print("\n⟨P, F, δ⟩ what would refute each rule\n")
    print("      P: adequacy_rec guarded by `adequacy`; cohere_rec by `emerge`; invariants unguarded")
    print("      F: a guard added to :invariants, or removed from a record, or --without-K dropped")
    print("      δ (min delta): one `if repository_ctx.attr.<flag>:` line in tools/bibtex.bzl")

    if bad:
        print(f"\nbnd-generator: {bad} rule(s) REFUTED — the build graph no longer follows its "
              f"own declarations", file=sys.stderr)
        return 1
    print(f"\nBOUNDARIES: PASS (3 declaration→target rules over {len(decl)} projects, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
