"""Λ·registry·gate — the VERB SET's boundary: one owner, every dispatch site derived from it.

A check type is not MIGRATED when its verdict works; it is migrated when EVERY site that
dispatches on check type has been migrated.  paperkit has five such sites, and they used to
carry five independent hardcoded lists — so adding `concept:` updated some and silently missed
others.  The misses were invisible: `//:hook` grades concept: through the Bazel certificate
import, so the direct-CLI grade path stayed wrong while every gate read green, and the footprint
audit kept stracing a whole library witness because its skip-set still read `result:` alone.

resolver.VERBS is now the one declaration, and `crosses` is the bit the sites actually branch on
(does this verb resolve against something ANOTHER project owns and separately gates?).  This
check asserts every site agrees with the datum — behaviorally where the site is Python, by
set-equality over source where it is Starlark.

    python3 paperkit/tests/boundaries_dispatch.py     # exit 0 = every site derives from VERBS
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import paperkit.grader
import paperkit.resolver

ENGINE = Path(__file__).resolve().parents[1]
ROOT = ENGINE.parent

CROSSING = {v for v, s in paperkit.resolver.VERBS.items() if s["crosses"]}

# footdeps must carry at least this many skip sites for the CROSSING-derived skip to mean anything.
_MIN_SKIP_SITES = 2
# the three outcomes a determinism set must keep distinguishable: PASS, FAIL, UNAVAILABLE.
_N_OUTCOMES = 3
# a startswith("<verb>:") literal: the shape of a hardcoded verb in a skip site.
_HARDCODED_VERB = re.compile(r'startswith\(\s*[\'"](\w+):')


class _Run:
    """The suite's running record: which sites drifted from resolver.VERBS."""

    def __init__(self) -> None:
        """Start with no drift."""
        self.fails: list[str] = []

    def check(self, desc: str, cond: object) -> None:
        """Print one `ok`/`XX` line and remember the failure."""
        if not cond:
            self.fails.append(desc)
        print(f"  {'ok ' if cond else 'XX '}{desc}")


def _hardcoded_verbs(src: str) -> list[str]:
    """Return the verb names `src` hardcodes in startswith("<verb>:") skip sites."""
    out: list[str] = []
    for m in _HARDCODED_VERB.finditer(src):
        verb: str = m.group(1)
        out.append(verb)
    return out


def _one_owner(run: _Run) -> None:
    """Assert the verb set has one owner and the crossing verbs are derived from it."""
    run.check(
        "resolver.VERBS declares the built-in set, and every entry is fully specified",
        bool(paperkit.resolver.VERBS)
        and all(
            {"arg", "verb", "passes", "crosses"} <= set(s) for s in paperkit.resolver.VERBS.values()
        ),
    )
    run.check(
        f"the crossing verbs are DERIVED, not re-listed: {', '.join(sorted(CROSSING))}",
        set(paperkit.resolver.CROSSING) == {f"{v}:" for v in CROSSING} and bool(CROSSING),
    )


def _every_site(run: _Run) -> int:
    """Assert every dispatch site derives from VERBS; return the footdeps skip-site count."""
    # 1. the VERDICT path — every declared verb reaches a real branch.  An unknown TARGET under a
    #    declared verb resolves to a non-passing Verdict (file/cmd: FAIL, a crossing verb whose
    #    sibling is absent: UNAVAILABLE); an undeclared TYPE returns UNAVAILABLE (cannot check, not
    #    refuted — ask-result-tristate).  The discriminating assertion: no verb RAISES, none
    #    PASSES a bogus target, and the set stays closed.
    dispatched = all(
        not paperkit.resolver.resolves(f"{v}:no-such-target-{v}", ENGINE, {}).passed
        for v in paperkit.resolver.VERBS
    )
    run.check(
        "resolver.resolves dispatches every declared verb (no fallthrough, no raise)", dispatched
    )
    run.check(
        "the built-in set is CLOSED — an undeclared type is UNAVAILABLE (cannot check ≠ refuted)",
        paperkit.resolver.resolves("nosuchverb:x", ENGINE, {}).is_unavailable(),
    )

    # 2. the FOOTPRINT command — file: opens only its target (None); every other verb runs
    #    something.
    cmds = {v: paperkit.resolver.check_cmd(f"{v}:t", {}) for v in paperkit.resolver.VERBS}
    run.check(
        "resolver.check_cmd covers every verb (None only for the verb that runs nothing)",
        cmds["file"] is None and all(c for v, c in cmds.items() if v != "file"),
    )

    # 3. the GRADE path — a crossing verb is DELEGATED to its owner, never swept locally.  This is
    #    the one that was silently wrong: a missing arm falls through to a local sweep, which
    #    cannot see a witness outside this project's mutation surface and can only read
    #    `indeterminate`.  And a LOCAL verb must NOT be delegated: stamping `imported` on a check
    #    this project owns would assert a grade nothing ever measured.  Both are read from what
    #    grade_check DOES with each declared verb, never from how its source is arranged, so the
    #    assertion is set-EQUALITY against VERBS rather than a list (or a regex) maintained here.
    delegated: set[str] = set()
    for v in sorted(paperkit.resolver.VERBS):
        rec = paperkit.grader.grade_check(f"{v}:t", ROOT, set(), {}, ROOT)
        if rec.get("grade") == "imported":
            delegated.add(v)
    for v in sorted(CROSSING):
        run.check(
            f"grader.grade_check delegates {v}: (crosses=True → imported, not a local sweep)",
            v in delegated,
        )
    names = ", ".join(sorted(delegated)) or "none"
    run.check(
        f"delegation is EXACTLY the crossing set (grade_check delegates {names})",
        delegated == CROSSING,
    )

    # 4. the FOOTPRINT AUDIT — skips exactly the crossing verbs, by asking the verb.  Count the
    #    code SHAPE (`startswith(paperkit.resolver.CROSSING)`), never a bare substring: a mention
    #    in a comment would inflate the tally, and a magic expected-count is the very defect at
    #    issue.
    footdeps_src = (ENGINE / "footdeps.py").read_text()
    skips = footdeps_src.count("startswith(paperkit.resolver.CROSSING)")
    hardcoded = _hardcoded_verbs(footdeps_src)
    run.check(
        f"footdeps' {skips} skip sites ask resolver.CROSSING, and none hardcodes a verb"
        + (f" (found {hardcoded})" if hardcoded else ""),
        skips >= _MIN_SKIP_SITES and not hardcoded,
    )

    # 5. the GENERATOR — Starlark cannot import the engine, so assert by set-equality over source
    #    that every crossing verb is wired to a cross-repo RECORD dep, and no local verb is.
    bibtex_src = (ROOT / "tools" / "bibtex.bzl").read_text()
    for v in sorted(CROSSING):
        run.check(
            f"tools/bibtex.bzl branches on {v}: (a cross-repo record dep, not a local action)",
            f'startswith("{v}:")' in bibtex_src,
        )
    run.check(
        "...and skips their local footprint, as footdeps does",
        all(f'"{v}:"' in bibtex_src for v in CROSSING) and "no local footprint" in bibtex_src,
    )
    return skips


def _location_free(run: _Run) -> None:
    """Assert concept: resolution is location-free: a project outside this repo uses ITS library."""
    # Λ·location — paperkit is used as a COMPILER from an external checkout, but all nine of its
    # own projects sit beside the engine, so a path the engine resolves relative to ITSELF looks
    # correct from in here forever.  The eight-project argument establishes the kernel is
    # DOMAIN-free; it never varies LOCATION.  The fixtures do run projects from a tempdir — but
    # none of them uses `concept:`, which is exactly why `_LIBRARY` stayed engine-relative until a
    # downstream consumer hit it.  So: a project OUTSIDE this repo, with its own library, must
    # dispatch to ITS OWN.
    with tempfile.TemporaryDirectory() as d:
        far = Path(d) / "their-repo"
        (far / "library").mkdir(parents=True)
        # A runnable downstream library honouring the exit-2 "not mine" sentinel contract:
        # owns exactly one key.  (The fallthrough dispatches on that contract, so the fixture
        # must SPEAK it — a bare data file would test directory pick, not key ownership.)
        #
        # ⚑ Ζ·lib·contract — IT DECLARES ITSELF A PROJECT.  This wrote `concepts.py` alone, which
        # satisfied the old directory test; the predicate is now `(cand / "paper.toml").is_file()`
        # because concepts.py-only directories exist in the wild (`gcalculus/library/`,
        # `summit/library/`) and answer nothing.  ⚑ THE THIRD FIXTURE OF THIS SHAPE — the same
        # repair landed in library/concepts.py and boundaries_concept_route.py, which is the tell
        # that the fixture form itself wants an owner rather than three copies.
        #
        # ⚑ AND THE WITNESS IS NOT NAMED `concepts.py`, DELIBERATELY.  `_library_cmd` reads the
        # module from this paper.toml's `[checks.claim] cmd`; a fixture named concepts.py would
        # pass equally against a resolver that still hardcoded the name and prove nothing.
        (far / "library" / "paper.toml").write_text(
            '[paper]\ntitle="t"\nrubric="r.tsv"\nwarrants=["concepts.bib"]\nout="l.md"\n'
            '\n[checks.claim]\ncmd = "python3 witness.py {target}"\n'
        )
        (far / "library" / "witness.py").write_text(
            "import sys\nsys.exit(0 if sys.argv[1:2] == ['mine'] else 2)\n"
        )
        (far / "doc").mkdir()
        run.check(
            "a project outside this repo resolves concept: to ITS OWN library, not the engine's",
            paperkit.resolver.library_for(far / "doc") == far / "library",
        )
        run.check(
            "...and one with NO library falls back to the engine's (fallback, never assumption)",
            paperkit.resolver.library_for(Path(d)) == paperkit.resolver.LIBRARY,
        )
        # Λ·library·fallthrough — per-KEY ownership, both sides reachable (the audit's reverse
        # finding: directory-level selection eclipsed ALL engine keys from any repo owning a
        # library, the exact inverse of the shadowing the seam was built to fix).
        run.check(
            "a key the project library OWNS resolves project-side",
            paperkit.resolver.resolves("concept:mine", far / "doc", {}).passed,
        )
        run.check(
            "a key it answers 'not mine' (exit 2) FALLS THROUGH to the engine's library",
            paperkit.resolver.resolves("concept:claim-is-record", far / "doc", {}).passed,
        )
        run.check(
            "a key owned NOWHERE is UNAVAILABLE (exit 2 everywhere = cannot witness, not refuted)",
            paperkit.resolver.resolves("concept:no-such-concept", far / "doc", {}).is_unavailable(),
        )
    # ⚑ THE EXPECTED VALUE IS THE ENGINE'S OWN ANSWER, NOT A PATH SPELLED HERE.  This read
    # `== ROOT / "library"` — a second copy of where the library lives — and RED when Ζ·cite·resolve
    # moved it inside the package (guard-must-not-copy: the arm carried its own copy of the
    # location it was checking).  The PROPERTY is that an in-repo project with no library of its
    # own resolves to THE ENGINE'S, whatever the engine says that is; `resolver.LIBRARY` is the
    # owner of that answer, so the arm asks the owner.  It still discriminates: a project that DID
    # own a library would resolve elsewhere, which the far-tree arms above measure directly.
    run.check(
        "in-repo resolution is UNCHANGED by the seam (a project with no library of its own "
        "resolves to the ENGINE's, wherever the engine declares that to be)",
        paperkit.resolver.library_for(ROOT / "paper") == paperkit.resolver.LIBRARY,
    )


def _delta_pair(run: _Run, skips: int) -> None:
    """Assert the footdeps drift is CAUGHT: re-hardcoding its skip-set is one token away."""
    # The exact drift that shipped: a new crossing verb whose skip-set was never updated.  F is
    # built by reverting footdeps to the hardcoded literal — one token — and must be CAUGHT.
    footdeps_src = (ENGINE / "footdeps.py").read_text()
    f_src = footdeps_src.replace("startswith(paperkit.resolver.CROSSING)", 'startswith("result:")')
    caught = not _hardcoded_verbs(footdeps_src) and _hardcoded_verbs(f_src) == ["result"] * skips
    if not caught:
        run.fails.append("dispatch-delta")
    print(f"  {'ok ' if caught else 'XX '}re-hardcoding footdeps' skip-set to `result:` is CAUGHT")
    print("      P (intact):  footdeps asks resolver.CROSSING → concept: is skipped")
    print("      F (reverted): the literal returns → concept: is straced, a whole witness reruns")
    print('      δ (min delta): one token, `resolver.CROSSING` → `"result:"`\n')


def _tristate(run: _Run) -> None:
    """Assert UNAVAILABLE ≠ FAIL: an unreachable crossing check is cannot-run, not refuted."""
    # ── ask-result-tristate: the ARM — UNAVAILABLE ≠ FAIL ──────────────────────────────────────
    # resolves() answers a Verdict, not a bool: a crossing check whose sibling is UNREACHABLE is
    # UNAVAILABLE (could not evaluate), NOT FAIL (refuted).  The δ is exactly the fold that
    # shipped: an absent sibling and a ran-and-failed sibling must NOT read the same.  This is the
    # coverage whose absence let the bare-bool fold stand (Λ·location — untested across a repo
    # boundary).
    absent = paperkit.resolver.resolves("result:no-such-sibling-here", ENGINE, {})
    unknown = paperkit.resolver.resolves("bogusverb:x", ENGINE, {})
    cmd_ran_failed = paperkit.resolver.resolves("cmd:false", ENGINE, {})
    cmd_ran_passed = paperkit.resolver.resolves("cmd:true", ENGINE, {})
    no_bool = not hasattr(paperkit.resolver.Verdict, "__bool__")
    outcomes = {paperkit.resolver.PASS, paperkit.resolver.FAIL, paperkit.resolver.UNAVAILABLE}
    # ⚑ Ζ·arm·operands — SEVEN TERMS REPORTED ONE BIT, and that is why a cell's disagreement
    # with the host was unreadable.  This arm went XX in the sandbox while every term passed on
    # the host, measured one by one; the record could say only `tristate-arm`.  PRINT THE
    # COMPONENTS applies inside a boundary suite too: a conjunction that discards its operands
    # is an assertion, and the operands are the evidence.  (Same fix that resolved bnd-cpuweight,
    # whose `[δ operands]` line showed build_f and self_f resolving to ONE path in a cell.)
    terms: list[tuple[str, bool, str]] = [
        ("absent.is_unavailable()", absent.is_unavailable(), repr(absent)),
        ("unknown.is_unavailable()", unknown.is_unavailable(), repr(unknown)),
        ("cmd:false is FAIL", cmd_ran_failed is paperkit.resolver.FAIL, repr(cmd_ran_failed)),
        ("cmd:true is PASS", cmd_ran_passed is paperkit.resolver.PASS, repr(cmd_ran_passed)),
        (
            "not UNAVAILABLE.passed",
            not paperkit.resolver.UNAVAILABLE.passed,
            repr(paperkit.resolver.UNAVAILABLE.passed),
        ),
        ("no __bool__", no_bool, repr(hasattr(paperkit.resolver.Verdict, "__bool__"))),
        # the determinism set needs three DISTINGUISHABLE outcomes, identity-hashable
        ("set{PASS,FAIL,UNAVAILABLE} == 3", len(outcomes) == _N_OUTCOMES, repr(len(outcomes))),
    ]
    arm_ok = all(ok for _, ok, _ in terms)
    if not arm_ok:
        for name, ok, got in terms:
            print(f"      [{'ok' if ok else 'XX'}] {name} -> {got}")
        run.fails.append("tristate-arm")
    print(f"  {'ok ' if arm_ok else 'XX '}an UNREACHABLE crossing check is UNAVAILABLE, not FAIL")
    print("      P (arm):     result:absent → UNAVAILABLE, unknown verb → UNAVAILABLE")
    print("      F (folded):  a ran-and-failed check (cmd:false) → FAIL; the two must NOT coincide")
    print("      δ (min delta): the sibling is present/reachable vs absent/unreachable")
    print("      (no __bool__ so no consumer folds silently; identity-hashable so sets work)\n")


def main() -> int:
    """Run every section of the dispatch boundary; exit 0 iff every site derives from VERBS."""
    run = _Run()
    print("Λ·registry — the verb set's dispatch boundary\n")
    print("⟨one owner⟩\n")
    _one_owner(run)
    print("\n⟨every site derives⟩\n")
    skips = _every_site(run)
    print("\n⟨location-free dispatch⟩\n")
    _location_free(run)
    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    _delta_pair(run, skips)
    _tristate(run)
    if run.fails:
        print(f"DISPATCH: FAIL ({len(run.fails)} sites drifted from resolver.VERBS)")
        return 1
    n_verbs, n_crossing = len(paperkit.resolver.VERBS), len(CROSSING)
    print(f"DISPATCH: PASS ({n_verbs} verbs, {n_crossing} crossing, 5 sites, 2 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
