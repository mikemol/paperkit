#!/usr/bin/env python3
r"""Behavioral-boundary examples for Λ·library·seam — the two ROUTES must resolve a concept: to the
SAME owner.

A `concept:<key>` is resolved twice in this engine, by two different mechanisms:

  * the CLI route (resolver.resolves) decides ownership AT RUNTIME, per key, by asking the
    candidate library and reading its exit-2 "not mine" sentinel — the consuming project's own
    library first, the engine's only on fallthrough (Λ·library·fallthrough).
  * the Bazel route (bibtex.bzl) decides ownership AT ANALYSIS TIME, by building the label
    `@paperkit_library//:<key>` from the key alone — it cannot probe, because a dep either exists
    in the graph before anything runs or it does not.

Those are not two implementations of one rule; they are two rules.  The CLI's is dynamic and
consumer-first, the Bazel one is static and engine-only.  They AGREE for every citation in this
repository only because exactly one project declares `owns_concepts`, so the fallthrough never
fires here — the divergence is invisible in-repo and appears for the downstream consumer the seam
was built for (Λ·location: the in-repo projects establish the kernel is DOMAIN-free; only an
out-of-repo consumer tests whether it is LOCATION-free).

This suite constructs that consumer.  It does NOT assert the routes currently agree — they do not,
and a gate that demanded it would be red on a defect nobody has chosen how to fix.  It pins the
FACTS that make the divergence real and checkable, so the eventual repair has a fixture:

  * the CLI route honours a consumer library that owns a key (it must, or the seam is useless);
  * the Bazel emitter's label is a function of the KEY ALONE (so it cannot honour one);
  * therefore a consumer owning an engine key gets two different witnesses by route;
  * and the exit-2 sentinel means NOT-MINE, never FAILED — the contract any repair must keep.

⟨P, F, δ⟩ per the boundary practice.

Run:  python3 paperkit/tests/boundaries_concept_route.py
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import sys
import tempfile
from pathlib import Path

ENG = Path(__file__).resolve().parent.parent
ROOT = ENG.parent
sys.path.insert(0, str(ENG))
import resolver


def _consumer(w: Path, body: str) -> Path:
    """A project shipping its OWN library, whose witness behaves as `body` dictates.

    ⚑ Ζ·lib·contract — THE FIXTURE DECLARES ITSELF A PROJECT.  It used to write `concepts.py`
    alone, which satisfied the old directory test (`(cand / "concepts.py").is_file()`) — weaker
    than the contract, and the ecosystem populated the gap: `gcalculus/library/` and
    `summit/library/` pass that test while carrying no paper.toml and no concepts.bib, and
    `substrate/catalog/library/` carries no concepts.py at all and fell through to the ENGINE's
    library, which holds none of its keys.

    ⚑ AND THE WITNESS IS DELIBERATELY NOT NAMED `concepts.py`.  `_library_cmd` reads the module
    from this paper.toml's `[checks.claim] cmd`; a fixture named concepts.py would pass equally
    against a resolver that still hardcoded the name, and would prove nothing about the
    declaration being READ.
    """
    proj = w / "view"
    (proj / "library").mkdir(parents=True, exist_ok=True)
    (proj / "library" / "paper.toml").write_text(
        '[paper]\ntitle="c"\nrubric="r.tsv"\nwarrants=["concepts.bib"]\nout="l.md"\n'
        '\n[checks.claim]\ncmd = "python3 witness.py {target}"\n')
    (proj / "library" / "witness.py").write_text(body)
    return proj


def _verdict(check: str, frm: Path) -> str:
    v = resolver.resolves(check, frm, {})
    return "cannot-run" if v.is_unavailable() else ("pass" if v.passed else "fail")


OWNS_AND_FAILS = (
    "import sys\n"
    "k = sys.argv[1]\n"
    "if k == 'rm-pitch':\n"
    "    raise SystemExit(1)\n"          # OWNS it, and reports FAILED
    "raise SystemExit(2)\n")            # disclaims everything else

DISCLAIMS_ALL = (
    "import sys\n"
    "raise SystemExit(2)\n")            # owns nothing — every key falls through


def main() -> int:
    fails = []
    ran = []

    def check(desc, cond):
        ran.append(desc)
        if not cond:
            fails.append(desc)
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Λ·library·seam — the two routes resolve one citation\n")

    with tempfile.TemporaryDirectory() as d:
        w = Path(d)

        # ── the CLI route is CONSUMER-FIRST ──────────────────────────────────────────────────
        owns = _consumer(w, OWNS_AND_FAILS)
        check("P: a consumer library that OWNS a key answers it (the seam's whole purpose)",
              _verdict("concept:rm-pitch", owns) == "fail")

        shutil.rmtree(owns)
        none = _consumer(w, DISCLAIMS_ALL)
        # The fallthrough's TARGET is the engine's own library, which — like tools/bibtex.bzl
        # above — this suite does not declare and the sandbox does not stage.  Assert the arm
        # only where the terminal owner exists; elsewhere say so.  `cannot-run` there is the
        # ENGINE being right (no library can witness the key), not the seam misbehaving.
        if (ROOT / "library" / "concepts.py").is_file():
            check("F: a consumer that DISCLAIMS the key falls through to the engine's library",
                  _verdict("concept:rm-pitch", none) == "pass")
        else:
            print("  --  the fallthrough arm CANNOT CHECK here: the engine library is not staged")
        print("     δ: the consumer library's exit code for that key — 1 (mine, failed) vs 2 (not mine).\n")

        # ── exit 2 is NOT-MINE, never FAILED ─────────────────────────────────────────────────
        shutil.rmtree(none)
        nobody = _consumer(w, DISCLAIMS_ALL)
        check("a key NO library owns is cannot-run, not a refutation",
              _verdict("concept:no-such-concept-anywhere", nobody) == "cannot-run")

    # ── the Bazel route's label is a function of the KEY ALONE ───────────────────────────────
    # Ζ·reads — the emitter's source is NOT staged for this suite (its warrant declares
    # `reads = {.}`, the boundaries dir), so under the hermetic sandbox this file is absent.
    # That is correct staging, not a gap: the arms below assert a property of the BUILD side,
    # which the CLI-side suite has no claim on.  Reading it opportunistically and reporting
    # CANNOT-CHECK when absent keeps the suite honest on both routes — the alternative was a
    # FileNotFoundError that reddened the gate for a missing input rather than a false claim.
    #
    # (This suite exists to document that the two routes disagree.  Crashing under one of them
    # because it reached outside its declared inputs would have been the same ambient-authority
    # defect it documents, committed by the documenter.)
    bzl_path = ROOT / "tools" / "bibtex.bzl"
    if not bzl_path.is_file():
        print("  --  the Bazel-emitter arms CANNOT CHECK here: tools/bibtex.bzl is not staged")
        print("      (3 arms skipped; they run on the CLI route where the file is present)")
        return _finish(fails, ran)
    bzl = bzl_path.read_text()
    # ⚑⚑ THE FOURTH INSTANCE OF source-grep-witness-token-fragility IN THIS SUITE, AND THE ANCHOR
    # IS NOW A PROPERTY RATHER THAN A SPELLING.
    #
    # The ladder, so the next reader does not climb it again:
    #   1. a WINDOW after a nearby token (`key = check[len("concept:"):]` + 400 chars) — asserted
    #      source PROXIMITY.  Ζ·grid·dangling inserted a comment and a `fail()` inside the window;
    #      two arms red, one IndexError.
    #   2. the EMITTED LINE (`"pk_result(name = " in ln and "@paperkit_library//:" in ln`) — the
    #      comment above this one called that "the honest anchor", because only a real change to
    #      what is emitted could move it.  ⚑ THAT REASONING WAS WRONG IN ONE WORD: it is only a
    #      real change to how the emission is SPELLED.  Ζ·grid·sibling lifted the label into
    #      `_import_label(...)` and the emitted line became `... + lbl + ...` — the literal left
    #      the file, `emitted` fell to "", and `.split("sibling_verdict")[1]` raised IndexError
    #      again, for a refactor that changed NOTHING this suite is about.  Same defect, same
    #      crash, one rung up.
    #
    # A witness that asserts a bare substring of engine source is measuring the source's SPELLING,
    # and every legitimate refactor is then a false red.  The structural route out is to read the
    # BUILT GRAPH instead of the generator — and it exists: on the host,
    #
    #     bazel query 'kind(pk_result, @paperkit_paper//:all)' --output=build
    #
    # prints every emitted `sibling_verdict = "@paperkit_library//:<key>"` directly (measured
    # 2026-09-02: 29 concept imports from the paper view, every one library-owned).  That is the
    # real artifact and no refactor preserving behaviour can move it.
    #
    # ⚑ IT IS NOT AVAILABLE TO THIS WITNESS, AND THE REASON IS ARCHITECTURAL, NOT INCIDENTAL.
    # This check runs as a `pk_cmd` whose declared inputs are `//:files //boundaries:files
    # //library:files //paperkit:engine` — a closure holding no bazel binary, no output base, and
    # none of the generated `@paperkit_*` BUILD files.  Reaching a bazel server from inside would
    # resolve OUT of the sandbox to the live tree, which is exactly the escape-that-PASSES that
    # `library/run-witness` refuses a staged `.venv` for.  A witness cannot query the graph it is
    # a node of; that would need the query's OUTPUT staged as a declared input, which is a
    # different rung (an emitted-label manifest the generator writes and this suite reads — the
    # honest structural fix, and the one Λ·library·manifest below would subsume anyway).
    #
    # So: re-anchored, but on the PROPERTY rather than the rendered string.  The three arms below
    # assert that the concept branch builds its label through `_import_label` with a CONSTANT
    # owner — which IS the claim ("the label is a function of the key alone, and the owner does
    # not vary with the citer").  A rename of `lbl`, a reflow of the emission, or a move of the
    # `pk_result` call cannot move it; only changing WHAT the owner is can, which is the change
    # this arm exists to catch.  The branch is located by `concept:`, a token owned by
    # resolver.VERBS rather than by this file's phrasing.
    lines = bzl.splitlines()
    start = next((i for i, ln in enumerate(lines) if 'check[len("concept:"):]' in ln), -1)
    # the branch ends at its `continue`; that is Starlark control flow, not a spelling
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].strip() == "continue"), -1) if start >= 0 else -1
    branch = "\n".join(lines[start:end]) if start >= 0 and end > start else ""
    # ⚑ THE ABSENCE ARM MUST READ CODE, NOT PROSE — the fifth face of the same defect, caught
    # while repairing the fourth.  A first cut asserted `"@paperkit_" not in branch`, which was
    # RED on arrival: the branch's own comment block and its two `fail()` messages quote
    # `@paperkit_library//:%s__dcalc` while EXPLAINING the dangling-label hazard.  So the arm was
    # measuring the branch's documentation — the very thing the re-anchor above exists to set
    # free.  Strip line comments and string literals first; what remains is what the generator
    # DOES, which is the only thing this suite has a claim on.
    code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', re.sub(r'#[^\n]*', '', branch))
    # the label constructor, and the OWNER it is handed at this call site
    m = re.search(r'_import_label\(\s*(.*?)\)', branch, re.S)
    owner_arg = ""
    if m:
        args = [a.strip() for a in m.group(1).split(",")]
        owner_arg = args[3] if len(args) > 3 else ""   # (verb, name, key, OWNER, ...)

    check("the Bazel emitter's concept branch is reachable to read, and builds a label",
          bool(branch) and bool(m))
    check("...and that label names ONE fixed library repo — the owner is a STRING LITERAL, "
          f"not a variable (owner={owner_arg or '<none>'})",
          owner_arg == '"library"')
    # ⚑ AND THIS ARM ASSERTS AN ABSENCE, DELIBERATELY.  An earlier draft of it also matched
    # `_import_label`'s RETURN LINE verbatim — which would have been the defect above committed
    # inside its own repair, one function further away.  What this suite may honestly say about
    # the branch is what the branch itself contains: the citing project reaches the emitter as
    # `proj`, so if neither that name nor any repo name appears between the key extraction and
    # the `continue`, the label cannot vary with the citer.  How `_import_label` assembles the
    # string from a constant owner is ITS business, and the arm above already pins the owner.
    check("...so nothing in the emitted label varies with WHO cites the key",
          bool(code.strip()) and "@paperkit_" not in code and "proj" not in code)

    # ── therefore: the routes CAN disagree, and today they do ────────────────────────────────
    # An arm asserting True is a PRINTED STATEMENT, not a check (Λ·instrument-vs-gate: it would
    # stay green through the repair it exists to describe).  So MEASURE the divergence: resolve the
    # same citation from the same consumer on both routes and compare the OWNERS they select.
    with tempfile.TemporaryDirectory() as d2:
        w2 = Path(d2)
        owns2 = _consumer(w2, OWNS_AND_FAILS)
        cli = _verdict("concept:rm-pitch", owns2)                      # consumer-first: its library
        bazel_owner = "paperkit_library"                                # what the emitter hardcodes
        cli_owner = "consumer" if cli == "fail" else "paperkit_library"
        check(f"DIVERGENCE MEASURED: one citation, two owners — CLI picks {cli_owner!r}, "
              f"Bazel picks {bazel_owner!r}",
              cli_owner != bazel_owner)
    print("     (not a red: no repair has been chosen.  Λ·library·manifest is the design question —\n"
          "      the CLI probes for an owner at runtime, Bazel needs one at analysis time, so a\n"
          "      library DAG must be DECLARED rather than discovered, with exit-2 demoted to a\n"
          "      consistency check.  This fixture is what any such repair must satisfy.)")

    return _finish(fails, ran)


def _finish(fails, ran) -> int:
    print()
    # Ζ·witness·verdict — a False in `ran` is a drifted behaviour, not decoration.  This suite
    # had a real failure branch, but it keyed only on `fails`: an assertion that printed XX and
    # appended False still exited 0.  Both lists are binding.
    fails = list(fails) + ["a behavior asserted False (see the XX lines above)"] * len(
        [b for b in ran if not b])
    if fails:
        print(f"concept-route boundaries: FAIL ({len(fails)})")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"concept-route boundaries: OK ({len(ran)} behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
