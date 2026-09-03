#!/usr/bin/env python3
"""The check RESOLVER — paperkit's check-resolution core, factored out of the gate so it
can be imported and tested with a SMALL blast radius (no projector, no parallel gate loop,
no config/CLI).  A verifier is named `type:target`; this module is the registry that
dispatches it, one branch per VERB.

The built-in verb SET is not written in this docstring: it is the DATA in VERBS below, the one
place paperkit declares it.  Every consumer — the README's resolver table, the gate's --help,
the Bazel verb rules, the prose, the witnesses — DERIVES from VERBS or is gated against it,
because an enumeration re-declared beside its owner drifts.  A witness that re-declares the set
it guards is the worst case: it certifies a tautology and stays green through exactly the drift
it exists to catch (Λ·registry).  A `<custom>:<target>` type is declared per-project instead, in
paper.toml as `[checks.<custom>] cmd = "…"`, and resolves as a cmd template.

It also sanitizes the environment a check runs in (clean_env, sshd-style default-deny) and
traces a check's READ footprint (footprint, Φ — the files it opens, the sound key to cache a
grade on).  Deps: only the stdlib + two of paperkit's own scripts as subprocesses (gate.py for
result:, the library's concepts.py for concept:), never the rest of the engine.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import config

_GATE = Path(__file__).resolve().parent / "gate.py"   # invoked as a subprocess for result:
_LIBRARY = Path(__file__).resolve().parent.parent / "library"  # the ENGINE's own concept library


class Verdict:
    """Ω·verdict — `resolves()` answers a TRISTATE, not a bool (ask-result-tristate).

    PASS / FAIL are the two real outcomes; UNAVAILABLE is the third state: the check could not be
    EVALUATED — a crossing sibling gate that would not run (its own cannot-run, `--json.available`
    false since the typed-gate-exit work), an UNREACHABLE sibling (an exception), or a verb this
    engine does not have.  Across a repo boundary that must NOT read as a REFUTATION: an absent or
    mid-refactor sibling is "I cannot tell", not "the claim is false".  In-repo UNAVAILABLE never
    fires (all nine projects are siblings that are always present) — which is the point; it only
    bites across repos, the case paperkit itself records as untested (Λ·location).

    It is a LIFT of paperkit's own typed alphabet, NOT a substitution: `discriminate`'s `3 REFUSE`
    means "you asked WRONG" (an internal caller bug); UNAVAILABLE means "I could not REACH the
    thing to ask" (external).  Folding one onto the other is the very fold this type removes.

    Deliberately NO `__bool__`: an implicit truth-test is the fold the ask exists to delete, so
    every consumer must say `.passed` OUT LOUD (a named local collapse, never a hidden one).
    Hashable + equatable BY IDENTITY (three singletons, default object semantics) so a determinism
    SET over reps has well-defined cardinality: {UNAVAILABLE, PASS} across reps is a REAL
    non-determinism, which `.passed`-collapse would hide as a stable fail.

    Owner-agnostic on purpose (the ARM, not the Π INDEX): a consumer needs "your thing could not
    run", not "which of the sibling / library / tool / unknown-verb owners couldn't".  If a
    downstream consumer ever measures a need to route on the owner, UNAVAILABLE widens to carry one
    (an `owner` slot + factory) WITHOUT touching PASS/FAIL or `.passed` — a non-breaking widening,
    precisely because `__eq__`/`__hash__` are not overridden here (interning per-owner variants then
    Just Works on identity).

    Ζ·unavailable·why — and UNAVAILABLE now CARRIES its reason, which is the widening this
    docstring anticipated above.  A cannot-run is not a verdict about the claim; it is a report
    about the WORLD, and the world's shortfalls are usually solvable — a missing veraPDF, an
    unstaged record, a sibling mid-refactor.  Collapsing every one of them to a single interned
    sentinel discarded the direction of the fix at the moment it was known: the delegate had
    computed "its veraPDF validator CANNOT RUN here (toolchain absent)" and the seam printed
    "could not evaluate (unreachable delegate or unknown verb)" — a disjunction of everything it
    might have been, naming nothing.  Do not report a sum type; report the incomplete Π and point
    at what would complete it.

    `.passed` and identity semantics are untouched: PASS/FAIL stay interned singletons, a bare
    UNAVAILABLE stays the module-level one, and `is UNAVAILABLE` keeps working because
    `__eq__`/`__hash__` are still not overridden — a REASONED unavailable is a distinct object
    that compares unequal, so callers testing identity must use `is_unavailable()`.
    """

    __slots__ = ("_name", "_owner", "_why")

    def __init__(self, name: str, why: str = "", owner: str = "") -> None:
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_why", why)
        object.__setattr__(self, "_owner", owner)

    @property
    def passed(self) -> bool:
        return self is PASS

    @property
    def why(self) -> str:
        """The delegate's own account of what is missing — '' when none was carried."""
        return self._why

    @property
    def owner(self) -> str:
        """WHO could not run: the sibling project or library that reported it."""
        return self._owner

    def is_unavailable(self) -> bool:
        """Identity-independent test: a reasoned UNAVAILABLE is a distinct object."""
        return self._name == "UNAVAILABLE"

    def __repr__(self) -> str:
        if self._why:
            return f"Verdict.{self._name}({self._owner or '?'}: {self._why})"
        return f"Verdict.{self._name}"


# Ζ·tier·exit — the exit a check uses to say "I could not run here" (engine-aligned: gate.py's
# _REFUSE, discriminate's REFUSE, pk_cmd's cannot-run arm).  Named once, read by run_ok.
_CANNOT_RUN = 3

PASS = Verdict("PASS")
FAIL = Verdict("FAIL")
UNAVAILABLE = Verdict("UNAVAILABLE")


def unavailable(why: str = "", owner: str = "") -> Verdict:
    """A cannot-run that CARRIES what would fix it.  Bare (no reason) returns the interned
    singleton, so existing `is UNAVAILABLE` checks keep holding for the reasonless case.
    """
    return Verdict("UNAVAILABLE", why, owner) if (why or owner) else UNAVAILABLE


def _pf(ok: bool) -> Verdict:
    """A check that RAN and decided: True → PASS, False → FAIL.  (Never UNAVAILABLE — that is the
    could-not-evaluate seam, returned explicitly at each such site.)
    """
    return PASS if ok else FAIL


def _sibling_for(project_dir: Path | None, name: str) -> Path:
    """Ζ·result·seam — WHERE is the sibling project a `result:<name>` names?

    The two paths disagreed about what the target STRING is.  Under Bazel it is a project NAME:
    bibtex.bzl turns `result:render#rnd-graph` into a dep on `@paperkit_render//:rnd-graph`,
    resolved in the repo namespace with no filesystem involved.  On the CLI it was a PATH,
    appended verbatim as the gate's directory argument with cwd set to the CITING project — so
    `result:render` from talk/ looked for `talk/render/paper.toml` and every one of talk's five
    delegations came back UNAVAILABLE.  Same bib, same string, two meanings.

    So the CLI now reads it as a NAME too, and resolves it the way `_library_for` resolves a
    library: the consumer's own neighbourhood first, the repo root next, the engine's only as a
    FALLBACK.  Λ·location — engine-relative alone is the mistake documented below: it is
    invisible in this repo (every project sits beside the engine) and fatal outside it, where a
    downstream `result:theirproject` would resolve into THIS repo. A name that resolves nowhere
    is returned unchanged, so the gate reports its own cannot-run rather than this layer
    inventing a diagnosis for it.
    """
    cands = []
    if project_dir is not None:
        p = Path(project_dir).resolve()
        cands += [p / name, p.parent / name]           # a nested sub-project, then a true sibling
    cands.append(_LIBRARY.parent / name)               # the engine's own tree, by FALLBACK
    for c in cands:
        if (c / "paper.toml").is_file():
            return c
    return Path(name)


def _library_for(project_dir: Path | None) -> Path:
    """Λ·library·seam — WHOSE concept library resolves a `concept:<key>`?  The CONSUMING project's,
    if it has one; only then the engine's.

    This was engine-relative alone, which is invisible from inside this repo (every project here
    happens to sit beside the engine) and fatal outside it: paperkit is used as a COMPILER from an
    external checkout, and a downstream `concept:` then ran THIS repo's library, which has none of
    their keys.  `concept:` is a builtin, so it dispatches ahead of a project's `[checks.concept]` —
    their override was silently shadowed, and the verb built to REMOVE per-citation sweep cost was
    unusable by exactly the consumers who need it (they fall back to a custom type that re-RUNS the
    witness instead of importing its certificate).  An absent project library must resolve to the
    engine's BY FALLBACK, never by assumption.  Λ·location: the eight in-repo projects establish the
    kernel is DOMAIN-free; only an out-of-repo consumer tests whether it is LOCATION-free.

    Λ·library·fallthrough — this function picks the CANDIDATE library (a directory); ownership
    of a KEY is decided at resolution: a project library that answers exit 2 ("not mine", the
    sentinel contract concepts.py declares) must not ECLIPSE the engine's concepts, so
    resolves() falls through to the engine's library per key.  Directory-level selection alone
    made every engine key unreachable from any repo owning a library — the downstream audit's
    live instance: they could never cite an engine concept even where it was the honest import.
    """
    # Ζ·lib·contract / Ζ·cite·resolve — A LIBRARY IS A PROJECT, AND A PROJECT IS A `paper.toml`.
    #
    # This tested `(cand / "concepts.py").is_file()` — a WEAKER predicate than the contract, and
    # measured across the ecosystem the gap is populated: `gcalculus/library/` holds concepts.py
    # ALONE (no paper.toml, no concepts.bib), `summit/library/` holds concepts.py + witnesses/,
    # and `substrate/catalog/library/` has no concepts.py at all and fell through to THIS repo's
    # library — the exact failure the docstring above says was fixed ("a downstream `concept:` then
    # ran THIS repo's library, which has none of their keys"), live in-tree, because
    # directory-shaped evidence is not project-shaped.
    #
    # ⚑ AN EARLIER DRAFT OF THIS COMMENT SAID THOSE LIBRARIES "cannot answer".  THAT WAS FALSE, and
    # both consumers disproved it by RUNNING theirs: summit measured `library/concepts.py
    # ask/tristate` → exit 0, and gcalculus's `paths.py --check` passes standalone.  They answer
    # fine; the tightened predicate stopped ASKING them.  A capability-absence claim written from a
    # directory listing instead of an invocation — in the comment justifying a change that broke
    # exactly those consumers.
    #
    # ⚑ AND `concepts.py` WAS THE SECOND HARDCODED NAME.  The library's own paper.toml already
    # declares BOTH facts the resolver was reconstructing — `warrants = ["concepts.bib"]` and
    # `[checks.claim] cmd = "python3 concepts.py {target}"`.  Keying on `paper.toml` and reading
    # the declared command is Λ·registry applied to resolution: the owner declares, the consumer
    # reads, and renaming the witness module stops being a silent break in a file that never
    # mentions it.  `_sibling_for` two functions up ALREADY tests `paper.toml`; this was the
    # outlier, not the pattern.
    #
    # The directory name stays `library` — that is a search key for a CANDIDATE, and the honest
    # scope of this fix: WHICH directory is still conventional, but WHETHER it is a library is now
    # a declaration.  Naming the library by citation rather than by directory is the rest of
    # Ζ·cite·resolve, and it needs a place for a consumer to write the name.
    # ⚑ Ζ·lib·fallback — THE TIGHTENING MUST BE SOFT, AND `_library_cmd` BELOW ALREADY KNEW THAT.
    #
    # Keying on paper.toml alone was a HARD break for every library that predates the contract.
    # It reddened TWO downstream consumers within hours — summit's board (three concepts it owns,
    # reported UNRESOLVABLE) and gcalculus's nested `paths/` project (~40).  Both were correct
    # invocations against libraries that answer.
    #
    # The asymmetry is the bug, not the predicate.  `_library_cmd`, the very next function, reads
    # `[checks.claim] cmd` from paper.toml and FALLS BACK to the historical `python3 concepts.py
    # {target}` spelling when the declaration is absent — its docstring calls that "the
    # compatibility path, not the contract".  I wrote the soft landing one function down and not
    # this one, so the same tightening was graceful there and abrupt here.
    #
    # So: paper.toml is the CONTRACT and settles ambiguity; a directory that answers the witness
    # contract (a `concepts.py` to run) still resolves, and `_library_cmd`'s fallback then invokes
    # it exactly as before.  A library declaring paper.toml WINS over a bare concepts.py at the
    # same level — the declaration is more specific than the convention — which is what keeps this
    # a compatibility path rather than a rollback.
    #
    # ⚑ AND THE DIAGNOSIS GAP IS WORTH RECORDING, because it is not about libraries at all.
    # gcalculus asked every question their tooling knows how to ask — `git log` on this file (last
    # change predated their green board), `git show` on the day's two commits (docstring-only),
    # `git log` on their own invocation (unchanged 17 days) — all TRUE, none sufficient, because
    # the cause was UNCOMMITTED in this tree and invisible to a peer.  Their finding, filed as
    # `a-consumers-reach-stops-at-the-peers-last-commit`: every diagnostic question a consumer can
    # ask about a peer is a question about COMMITTED state.  A text search would also have said
    # "unchanged" — this comment block carries BOTH spellings, the old one in narration and the new
    # one in the test.
    if project_dir is not None:
        p = Path(project_dir).resolve()
        for base in (p, p.parent):                    # the project's own, then its repo root's
            cand = base / "library"
            if (cand / "paper.toml").is_file():
                return cand
        for base in (p, p.parent):                    # compatibility: a pre-contract library
            cand = base / "library"
            if (cand / "concepts.py").is_file():
                return cand
    return _LIBRARY


def _library_cmd(lib: Path, target: str) -> list:
    """The argv that asks `lib` to witness `target` — READ from the library's own declaration.

    Ζ·cite·resolve — `[checks.claim] cmd` in the library's paper.toml is what the gate itself runs
    for that project's claims, so it is the one authority on how to invoke its witness.  The
    resolver used to hardcode `python3 <lib>/concepts.py <target>`, a second copy of that
    declaration living in the consumer — the shape Λ·registry names (an enumeration re-declared
    beside its owner drifts, and this one could drift into a SILENT break: rename the module,
    paper.toml stays correct, `concept:` stops resolving).

    Falls back to the historical spelling when the declaration is absent or unreadable, so a
    library that predates this still answers; the fallback is the compatibility path, not the
    contract.
    """
    fallback = [sys.executable, str(lib / "concepts.py"), target]
    try:
        import tomllib
        cfg = tomllib.loads((lib / "paper.toml").read_text())
        cmd = ((cfg.get("checks") or {}).get("claim") or {}).get("cmd")
        if not cmd:
            return fallback
        # `{target}` is the declared substitution point (the same one bib/gate use for a custom
        # verb).  Split as a shell word list, then resolve the module RELATIVE TO THE LIBRARY —
        # the declaration is written from the project's own directory, which is why the run below
        # sets cwd=lib.
        parts = shlex.split(cmd.replace("{target}", target))
        return [str(lib / a) if a.endswith(".py") and not Path(a).is_absolute() else a
                for a in parts]
    except Exception:
        return fallback


# Λ·registry — THE built-in verb set.  This dict OWNS the enumeration: `resolves` dispatches one
# branch per key, and no other file may re-declare the set — docs render it, witnesses assert
# set-EQUALITY against it, and prose that would name a COUNT ("four verbs") or an ORDINAL ("the
# third verb") says neither, because both hardcode a set's size into a place that cannot see it.
# `arg` is the target's shape, `verb` the one word for what resolution MEANS, `passes` the
# condition — together exactly the columns of the README's resolver table, which is why that
# table can be checked against this and not maintained beside it.
#
# `crosses` is the STRUCTURAL bit, and the reason this is data rather than prose: it says the verb
# resolves against something ANOTHER project owns and separately gates.  Three sites downstream
# must agree about that — Δ delegates the grade instead of sweeping locally (grader.grade_check),
# the footprint audit skips it rather than stracing a whole sibling gate (footdeps), and the
# generator wires it to a cross-repo RECORD dep instead of a local action (bibtex.bzl).  Before
# this field each site carried its own hardcoded list, and adding `concept:` updated two of the
# three — the footprint audit still read `result:` alone.  Now they ask the verb.
VERBS = {
    "file":    {"arg": "<path>",      "verb": "exists",  "crosses": False,
                "passes": "the artifact exists"},
    "cmd":     {"arg": "<script>",    "verb": "execs",   "crosses": False,
                "passes": "the script exits `0`"},
    "result":  {"arg": "<project>[#<claim>]", "verb": "parses", "crosses": True,
                "passes": "the sibling project's gate verdict parses green --- for the whole project, or for the ONE named warrant"},
    "agree":   {"arg": "<p>|||<q>",   "verb": "concurs", "crosses": False,
                "passes": "the independent producers all exit `0` and emit identical output"},
    "concept": {"arg": "<key>",       "verb": "imports", "crosses": True,
                "passes": "the project's concept library --- else the engine's --- certifies that key"},
}

# The `type:` prefixes of the boundary-crossing verbs — startswith()-ready, DERIVED so a consumer
# never re-lists them.  A new crossing verb reaches every site by declaring crosses=True above.
CROSSING = tuple(f"{v}:" for v, spec in VERBS.items() if spec["crosses"])


# A check is arbitrary code (cmd: is the universal escape hatch), so it must not run in
# whatever ambient environment the gate happened to inherit — that is both an injection
# surface (LD_PRELOAD, IFS, BASH_ENV, PYTHONPATH, …) and a reproducibility leak (the
# verdict would depend on the caller's shell).  Like sshd, we DON'T inherit: we build a
# controlled environment, default-deny, keeping only what a check legitimately needs.  PATH
# is kept so tools resolve, but its RELATIVE entries are dropped (Τ·path): a check runs with
# cwd = the project dir, so an empty/"." PATH component would resolve a tool to the project
# being gated — letting a document plant a tool beside itself.  Which ABSOLUTE dir resolves a
# tool stays the host's trust (the reproducibility leak above); pinning per-tool is further.
_ENV_KEEP = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "TERM", "TZ", "TMPDIR",
             "LANG", "LANGUAGE", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"}
_ENV_KEEP_PREFIX = ("LC_", "PAPERKIT_")        # locale + paperkit's own knobs
# ...except the Δ grader's SANDBOX ROOT, which is grader-internal and must NOT reach a check: a
# check being graded reruns in the grader's sandbox, and a META-grading check (one that runs its
# own grader on a fixture) would otherwise inherit the OUTER root and reject its fixture ("root
# does not contain the project").  Recursive-check env leak (cf. Ω·config args-process-local).
_ENV_DROP = {"PAPERKIT_ROOT"}

# Ω·config — the knobs this module RESOLVES, declared here (place-by-ownership; the kernel hosts
# the mechanism only).
PATH = config.Param("path", "PAPERKIT_PATH",
                    help="pin tool resolution to these absolute dirs (colon-separated) instead of the host PATH — reproducibility, and dropping user-writable shadow dirs")

# ⚑ Ζ·dispatch·pythonpath — THE DECLARED PASSTHROUGH FOR "WHERE IS THE ENGINE IMPORTABLE FROM".
#
# Two correct mechanisms collided, and neither side was wrong.  `library/run-witness` detects a
# hermetic cell by testing `[ -d "$PYTHONPATH/paperkit" ]` — correct, and the only way it can know
# not to build a `.venv` full of host absolute paths inside a sandbox.  `clean_env` above DROPS
# `PYTHONPATH` by default-deny — also correct, and named in its own comment as an injection
# surface (LD_PRELOAD, IFS, BASH_ENV, PYTHONPATH).  So a check spawned through this resolver saw
# no PYTHONPATH, found no `.venv`, found no `uv`, and the witness could not run.  On the DEV HOST
# it passed anyway, because a `.venv` happens to exist there — the failure was invisible in-repo
# and fired only under the hermetic cell, which is the regime the sandbox exists to model.
#
# The seam already existed: `_ENV_KEEP_PREFIX` keeps `PAPERKIT_*`, so an OWNER-DECLARED knob
# crosses `clean_env` without widening the allowlist by one entry.  That is the whole point of a
# declared passthrough versus a wider allowlist: the value is one this engine CHOSE to export,
# resolved through Ω·config's one pipeline (arg > env > config > default), not whatever the
# ambient shell happened to be carrying.  `PYTHONPATH` itself stays denied.
#
# ⚑ THE DEFAULT IS `None`, AND THE FALLBACK LIVES AT THE USE SITE — design-for-portability.
#
# The obvious spelling is `default=lambda: str(Path(__file__).resolve().parent.parent)`, and it is
# wrong for a reason the `config` project caught immediately: that project PROJECTS the knob union
# as a committed table (assets/knobs.md, gated fresh by byte-diff), and `gen_knobs.py` INVOKES a
# callable default to render it.  So this knob's default row read `/home/mikemol/github/paperkit`
# — one machine's absolute path, frozen into a document every other machine would regenerate
# differently, reddening the freshness check for everyone but its author.  A default that varies
# with WHERE THE ENGINE IS CHECKED OUT has no portable literal, so it must not be rendered as one.
#
# `None` is also the more honest resolution: it means "nothing configured this", which is exactly
# true — the engine's own location is not a CONFIGURED value, it is a fact `clean_env` reads from
# `__file__` at the moment it builds the environment.  The knob keeps its full override power
# (arg > env > paper.toml), and the table renders `—` like every other unset knob.
ENGINE_PATH = config.Param(
    "engine-path", "PAPERKIT_PYTHONPATH",
    help="the directory `paperkit` is importable from, exported to every check as PAPERKIT_PYTHONPATH — a DECLARED passthrough across clean_env's default-deny, which drops the ambient PYTHONPATH (unset: the engine's own location)")


def clean_env(env: dict | None = None) -> dict:
    """A sanitized environment for running a check: the controlled allow-list only, so
    no LD_PRELOAD/IFS/BASH_ENV/PYTHONPATH and the like reach the command.  PATH's relative
    and empty entries are dropped (Τ·path) — they would resolve a tool to the cwd (the
    project dir being gated), so a document could shadow a tool by planting it beside itself.
    """
    src = os.environ if env is None else env
    out = {k: v for k, v in src.items()
           if (k in _ENV_KEEP or k.startswith(_ENV_KEEP_PREFIX)) and k not in _ENV_DROP}
    # ⚑ Ζ·check·debug — GUARANTEE `__debug__` TO THE CHECK, POSITIVELY.
    #
    # Under `-O` / PYTHONOPTIMIZE, python DELETES every `assert`.  A witness built on asserts then
    # exits 0 having verified NOTHING, and this gate reports it as passing — a check that cannot
    # fail, certified by the engine whose whole claim is that a green gate means the evidence RAN.
    # It is the same condition adequacy grading already refuses downstream (an unfalsifiable check
    # grades `vacuous`, below the floor); a runner able to silently create it is a hole in the
    # thing paperkit is FOR.
    #
    # ⚑ THE ALLOWLIST ABOVE ALREADY EXCLUDED PYTHONOPTIMIZE — BY ACCIDENT, AND THAT IS THE POINT.
    # `_ENV_KEEP` was built against injection and reproducibility; nobody left PYTHONOPTIMIZE out
    # *because of asserts*, nothing tested that it stayed out, and an accidental invariant with no
    # witness is one refactor from gone — silently, since the failure mode is a GREEN gate.
    # Setting it to "0" here makes the guarantee POSITIVE rather than a side effect of an omission:
    # a future edit that widened the allowlist would now be overridden instead of quietly fatal.
    #
    # ⚑ AND IT DOES NOT COVER argv, WHICH IS STATED RATHER THAN HIDDEN.  `python -O script.py` in a
    # `[checks.X] cmd` template is a FLAG, not an environment variable, and no environment
    # sanitisation can strip it.  That surface is a project's own paper.toml — data this engine
    # executes but does not author.  Closing it needs the CHILD to refuse, which is a separate rung
    # (the witness contract), and the two are not substitutes: this closes the route an operator
    # can trip from a shell profile, which is the one that travels between repos.
    #
    # Reported by gcalculus, whose entire evidence base is 2,839 asserts and whose own census then
    # found the entrypoint THIS runner spawns (`library/concepts.py`) is the one their guard misses
    # — so a per-consumer guard requires every consumer to notice first, and one demonstrably did
    # not.  place-by-ownership-not-need: the claim "this check passed" is made HERE.
    out["PYTHONOPTIMIZE"] = "0"
    # ⚑ Ζ·dispatch·pythonpath — EXPORT THE ENGINE'S LOCATION POSITIVELY, for the same reason
    # PYTHONOPTIMIZE is set rather than merely omitted.  The allowlist DENIES `PYTHONPATH` (an
    # injection surface), which is right; but a check that must import the engine then had no way
    # to be told where it is, and `library/run-witness` fell through to a host `.venv` — present
    # on the dev box, absent in a hermetic cell.  This is the DECLARED replacement: resolved
    # through Ω·config (so a caller can override it by arg, env, or paper.toml), carried under the
    # `PAPERKIT_` prefix the allowlist already keeps, and set by the ENGINE rather than inherited.
    # A check reads PAPERKIT_PYTHONPATH; nothing reads the ambient PYTHONPATH, which stays dropped.
    # Unset (the normal case) means the engine's OWN location — read from `__file__` here rather
    # than declared as the Param's default, because that value is per-checkout and the config
    # project renders declared defaults into a committed table (see ENGINE_PATH above).  Under
    # Bazel this resolves to the STAGED tree, since `__file__` is itself inside the sandbox.
    engine_path = config.resolve(ENGINE_PATH) or str(Path(__file__).resolve().parent.parent)
    out["PAPERKIT_PYTHONPATH"] = str(engine_path)
    pinned = config.resolve(PATH)
    if pinned is not None:
        # Τ·path: PIN tool resolution to a DECLARED set of absolute, existing dirs —
        # reproducibility (the same `grep`/`pandoc` on any host) and defence-in-depth (the host
        # PATH here is dup-laden and full of user-writable dirs ~/bin, ~/.local/bin, .cargo/bin
        # that could shadow a system tool).  The ambient host PATH is dropped entirely.
        raw = [p for p in pinned.split(os.pathsep) if os.path.isdir(p)]
    elif "PATH" in out:
        raw = out["PATH"].split(os.pathsep)
    else:
        return out
    # keep ABSOLUTE entries only (a relative/empty one resolves a tool to the gated cwd), and
    # DEDUPE keeping the first occurrence (first-match resolution is unchanged; the host PATH
    # carries the same dir many times — ~/.lmstudio/bin six times here).
    seen, dirs = set(), []
    for p in raw:
        if p and os.path.isabs(p) and p not in seen:
            seen.add(p)
            dirs.append(p)
    out["PATH"] = os.pathsep.join(dirs)
    return out


# A check must TERMINATE to pass.  A mutation can make a witness non-terminating — a flip: inverting a
# `while` condition (bib._unescaped_braces' escaped-backslash loop is the live example), a branch: that
# removes a loop's exit — and without a bound the sweep spins forever on that one cell instead of
# recording the flip.  So a check that does not finish reads FAIL (the mutation changed behaviour — the
# pristine check terminates, the mutant does not, which IS the sensitivity the sweep measures).
#
# The bound is CPU TIME, not wall clock — this is the honest measure under paperkit's own scheduling.
# A mutation-induced hang is a BUSY loop at 100% CPU, so it trips a CPU limit almost immediately; a
# check that is merely SLOW because it is lease-QUEUED (the membudget semaphore) or descheduled under
# load burns little CPU and is NOT false-failed, which a wall-clock timeout would do (it was descheduled,
# not looping).  RLIMIT_CPU is kernel-enforced (SIGXCPU at the soft limit, SIGKILL at the hard) and
# INHERITED by the child tree, set in a preexec_fn before exec.  A generous WALL BACKSTOP still catches
# the rare stuck-WAITING process that burns no CPU (a deadlocked I/O wait a CPU limit would never trip).
# Ample for any single real check (a def-sweep's minutes are MANY checks, not one CPU-heavy one);
# PAPERKIT_CHECK_CPU / PAPERKIT_CHECK_TIMEOUT override.
CHECK_CPU = 60          # seconds of CPU time — a busy hang trips this; a lease-queued check does not
CHECK_TIMEOUT = 600     # wall-clock BACKSTOP for a stuck-waiting (zero-CPU) process


def _cpu_rlimit(seconds: int):
    """A preexec_fn that caps the child's (and its tree's) CPU time — SIGXCPU at `seconds`, SIGKILL a
    few seconds later.  Runs in the forked child before exec, so the whole check subprocess is bounded
    by WORK DONE, not wall time.
    """
    def _set():
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds + 3))
    return _set


def run_ok(cmd: str, cwd: Path, owner: str = "") -> Verdict:
    """Run a shell command: it RAN and exited 0 → PASS, ran and exited non-zero (or exceeded its CPU
    budget / the wall backstop) → FAIL, could not be SPAWNED at all → UNAVAILABLE.  The last arm is the
    same could-not-evaluate seam as the crossing verbs, one verb down: an un-spawnable cmd is not a
    refuted claim, it is an unchecked one, and folding it into FAIL would be the exact bug this change
    removes for the most-used verb.  A cmd that BURNS its CPU budget (a mutation-induced busy loop), by
    contrast, IS a fail — a check that never answers has not passed, and the hang is a real behavioural
    flip the sweep must see; measuring CPU not wall keeps a lease-queued check from a false FAIL.
    """
    import os
    import signal
    cpu = int(os.environ.get("PAPERKIT_CHECK_CPU", CHECK_CPU))
    wall = int(os.environ.get("PAPERKIT_CHECK_TIMEOUT", CHECK_TIMEOUT))
    # start_new_session so a hang kills the WHOLE process group — a `shell=True` timeout otherwise
    # reaps only the shell and orphans the real child (the hanging witness), which then spins on.
    try:
        # Ζ·unavailable·why — CAPTURE stderr (stdout stays muted: a check's stdout is its own
        # chatter and nothing parses it).  A check that exits 3 has just explained WHAT it needs
        # ("its veraPDF validator CANNOT RUN here (toolchain absent)"); with both streams to
        # DEVNULL that account was destroyed at the moment of execution and the seam three layers
        # up printed a disjunction naming nothing.  Kept on its OWN handle, never merged
        # ([[separate-filehandles]]), and read ONLY on the cannot-run arm.
        p = subprocess.Popen(cmd, shell=True, cwd=cwd, env=clean_env(),
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                             start_new_session=True, preexec_fn=_cpu_rlimit(cpu))
        try:
            # ⚑ communicate(), NEVER wait() — a PIPE that nothing drains DEADLOCKS the child the
            # moment it writes past the 64KB pipe buffer: the check blocks in anon_pipe_write, this
            # process blocks in do_wait, and neither ever moves.  Measured 2026-08-26: a def-sweep
            # cell for edge-formulas sat at 0.0% CPU for 11+ minutes, the whole `cohere` build
            # stalled on its last action, and `wchan` named both halves of the deadlock.  The
            # stderr capture (Ζ·unavailable·why) is right and the wait() paired with it was not;
            # communicate() drains and waits in one call, so the timeout still bounds the run.
            _out, _err = p.communicate(timeout=wall)   # stdout is DEVNULL; _out is None
            rc = p.returncode
            # SIGXCPU (‑signal 24) / SIGKILL from the CPU rlimit ⇒ negative returncode ⇒ FAIL, not PASS.
            #
            # Ζ·tier·exit — rc 3 is CANNOT-RUN, not a failure.  pk_cmd (verb.bzl) has typed the exit
            # this way since the tier work ("rc 0 → pass · rc 3 → cannot-run · any other nonzero →
            # fail"), and the render checks return 3 exactly when their host toolchain is absent.
            # The CLI path never got that arm, so ONE check answered two different verdicts
            # depending on which path ran it: cannot-run under Bazel, FAIL under `gate.py`.  That is
            # the false-red the tier work closed, still open on the other route.
            #
            # This does NOT fold discriminate's `3 REFUSE` onto UNAVAILABLE — the distinction the
            # Verdict docstring protects.  A REFUSE is the ENGINE telling an internal caller it
            # asked wrong; this rc comes from an EXTERNAL check process reporting it could not reach
            # its toolchain, which is the "could not evaluate" arm by definition.  The two share a
            # number across a process boundary, not a meaning.
            if rc == _CANNOT_RUN:
                # the check's own last words are the direction of the fix
                err = (_err.decode("utf-8", "replace").strip() if _err else "")
                last = err.splitlines()[-1].strip() if err else ""
                return unavailable(last[:400], owner)
            return _pf(rc == 0)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)   # kill the whole tree, no orphans
            except ProcessLookupError:
                pass
            p.wait()
            return _pf(False)                            # did not terminate → FAIL (the mutation flipped it)
    except Exception:
        return UNAVAILABLE


def resolves(check: str, project_dir: Path, custom: dict) -> Verdict:
    typ, _, target = check.partition(":")
    if typ == "file":
        return _pf((project_dir / target).exists())   # EXISTS — no subprocess → no lease; absent = FAIL
    if typ == "result":
        # Ξ·seam — result PARSES (VERBS names every verb; no ordinal here, an ordinal would
        # hardcode the set's size).  It imports a sibling project's gate VERDICT (gate --json) and
        # PARSES it — green iff the parsed verdict reports pass — rather than re-deriving
        # what the sibling owns and separately gates.  cwd = this project's dir, so the
        # target is the sibling's path relative to it.  Δ grades it "imported" (run once),
        # never mutation-sweeping a whole sub-gate.
        #
        # TWO unavailables (ask-result-tristate): the sibling gate RAN but reports it could not set
        # ITSELF up (`--json.available` false, since the typed-gate-exit work) → UNAVAILABLE; and the
        # subprocess could not run at all (sibling UNREACHABLE — absent path, mid-refactor) → also
        # UNAVAILABLE.  Neither is a REFUTATION of the importing claim; only a sibling that RAN and
        # reported not-pass is FAIL.
        #
        # Λ·reduce — `project#claim` addresses ONE of the sibling's warrants.  Bare `project` keeps
        # whole-project semantics unchanged.  The finer form exists because a claim that names a
        # SPECIFIC sibling guarantee ("render gates PDF/UA") cannot honestly check the sibling's
        # whole gate: result:render would be green only when EVERY render warrant holds, asserting
        # far more than the importing claim needs, and red for a failure in an unrelated warrant.
        # Both directions are overclaims.  The sibling's gate already had the address (--only, the
        # Ζ·starlark leaf); it simply did not ANSWER in machine-readable form until now.
        proj, _, claim = target.partition("#")
        try:
            argv = [sys.executable, str(_GATE), "--json", "--safe", "--without-K"]
            if claim:
                argv += ["--only", claim]
            argv.append(str(_sibling_for(project_dir, proj)))
            r = subprocess.run(argv, cwd=project_dir, env=clean_env(),
                               capture_output=True, text=True)
            rec = json.loads(r.stdout or "{}")
            if rec.get("available") is False:         # the sibling's own cannot-run
                # Ζ·unavailable·why — carry the DELEGATE'S OWN account.  It already computed one
                # ("its veraPDF validator CANNOT RUN here (toolchain absent)") and returns it in
                # --json.reason; dropping it here left the citing gate printing a disjunction of
                # everything the failure might have been.  A missing dependency is a solvable
                # problem, and the delegate is the only party that knows WHICH one.
                return unavailable(rec.get("reason") or "the delegate reported it cannot run",
                                   target)
            return _pf(bool(rec.get("pass")))
        except Exception as e:
            # ⚑ Ζ·result·owner — THE UNREACHABLE PATH NAMES ITS OWNER TOO.  The widening above
            # carried a reason only when the sibling RAN and reported its own cannot-run; a
            # sibling that could not be reached AT ALL returned the bare interned singleton, so
            # gate.py's `f"{v.owner}: {v.why}"` fell through to the disjunction its own comment
            # says it replaced ("unreachable delegate or unknown verb" — everything it might have
            # been and nothing it was).  Two cannot-runs, one attributable and one mute, and the
            # mute one is the case a downstream consumer hits FIRST (an absent path, a sibling
            # mid-refactor, a repo not checked out beside this one).
            #
            # The owner is the CITED TARGET, matching the arm above — a consumer reading a
            # cannot-run learns which delegation failed, not merely that one did.
            return unavailable(f"the sibling could not be reached: {type(e).__name__}: {e}"[:400],
                               target)
    if typ == "concept":
        # Λ·witness — a concept: check IMPORTS a concept authored and GRADED once in the library.
        # For the LIVE verdict (the direct-CLI gate path; the Bazel //:hook path reads the library's
        # records via pk_result/pk_grade), RUN the library witness by ABSOLUTE path — the concept is
        # OWNED and separately gated by the library, so this is COMPOSITION (like result:), not
        # re-authoring.  The witness resolves its own engine via __file__, so the importing view needs
        # nothing staged; its adequacy is the imported certificate (verdict + engine fingerprint).
        try:
            lib = _library_for(project_dir)
            r = subprocess.run(_library_cmd(lib, target),
                               cwd=lib, env=clean_env(), capture_output=True)
            # Λ·library·fallthrough — per-KEY, not per-directory: exit 2 is the library's own
            # "not mine" sentinel, so a project library lacking the key falls through to the
            # engine's (the true owner answers); any other exit is the OWNING library's verdict.
            # The owning case runs ONCE; only a fallthrough pays the cheap rc-2 probe first.
            if r.returncode == 2 and lib != _LIBRARY:
                r = subprocess.run(_library_cmd(_LIBRARY, target),
                                   cwd=_LIBRARY, env=clean_env(), capture_output=True)
            # exit 2 from the FINAL owner = "nobody owns this key": the concept is UNAVAILABLE (no
            # library can witness it), NOT refuted.  Any other exit is the owning library's verdict.
            if r.returncode == 2:
                # ⚑ Ζ·result·owner — NAME THE LIBRARY THAT DISCLAIMED IT.  This returned the bare
                # singleton, so "nobody owns this key" reached the citing gate without saying WHO
                # was asked — and the consumer-first ladder means the answer is genuinely useful:
                # a key the author believes their own library owns, disclaimed by the ENGINE's,
                # says the ladder picked a different library than they think.  concepts.py already
                # prints which library answered (Λ·doc·concept) and then throws it away here.
                return unavailable(
                    f"no library owns concept {target!r} — asked {lib}"
                    + (f", then the engine's {_LIBRARY}" if lib != _LIBRARY else ""),
                    str(lib))
            # ⚑ Ζ·dispatch·pythonpath / Ε·fold — rc 3 IS CANNOT-RUN HERE TOO, and this was the
            # THIRD face of the fold.  `run_ok` took the arm at the tier work and `agree:` took it
            # at Ε·fold; `concept:` never did, so a library that RAN but could not establish its
            # own environment (no engine on the path, no interpreter it could use) was scored a
            # REFUTATION of the concept.  That is the worst direction for this verb to be wrong in:
            # a concept is authored and graded ONCE in the library and IMPORTED everywhere, so one
            # cannot-run propagates as a false refutation to every citing view at once.
            #
            # A witness that CANNOT RUN is not a witness that REFUTES — the distinction the Verdict
            # docstring exists to protect, arriving here from an EXTERNAL process reporting it
            # could not reach its toolchain, not from the engine being asked wrong.
            if r.returncode == _CANNOT_RUN:
                last = (r.stderr or b"").decode("utf-8", "replace").strip().splitlines()
                return unavailable((last[-1].strip()[:400] if last else
                                    "the concept library reported it cannot run"), str(lib))
            return _pf(r.returncode == 0)
        except Exception as e:
            # The library is unreachable — the concept analogue of the sibling case above.
            return unavailable(f"the concept library could not be run: {type(e).__name__}: {e}"[:400],
                               target)
    if typ == "agree":
        # Δ·agree (Ε·agree) — agree CONCURS (see VERBS; no ordinal, no count).
        # The SAME fact established by N INDEPENDENT producers (split on |||) that
        # must AGREE — every one exits 0 AND emits identical output.  Where cmd: trusts one
        # implementation, agreement across independent producers rules out a shared bug a
        # single check cannot catch: stronger evidence, a distinct KIND.
        producers = [p.strip() for p in target.split("|||") if p.strip()]
        if len(producers) < 2:
            return FAIL                               # agreement needs ≥2 producers — a real defect, not unavailable
        outs = set()
        for prod in producers:
            try:
                r = subprocess.run(prod, shell=True, cwd=project_dir, env=clean_env(),
                                   capture_output=True, text=True)
            except Exception:
                return UNAVAILABLE                    # a producer could not be SPAWNED — cannot evaluate
            # ⚑ Ε·fold — rc 3 IS CANNOT-RUN HERE TOO, and `!= 0` was scoring it as a refutation.
            # `run_ok` has carried this arm since the tier work ("rc 0 → pass · rc 3 → cannot-run ·
            # any other nonzero → fail"), and its comment names the exact hazard: ONE check
            # answering two different verdicts depending on which path ran it.  `agree:` is the
            # path that never got the arm — so a producer whose TOOLCHAIN IS ABSENT (a veraPDF, a
            # pandoc) was reported as DISAGREEING with its peers, which is a false red in the verb
            # whose entire purpose is evidential strength.  A producer that could not run has not
            # dissented; it has not spoken.
            #
            # The distinction is the one the Verdict docstring protects: `_CANNOT_RUN` from an
            # EXTERNAL producer means it could not reach its toolchain, not that the engine asked
            # wrong.  Its last line is the direction of the fix, so it rides along — the same
            # Ζ·unavailable·why widening result: takes, at the verb that most needs it (a
            # disagreement report must say WHICH producer, and why).
            if r.returncode == _CANNOT_RUN:
                last = (r.stderr or "").strip().splitlines()
                return unavailable((last[-1].strip()[:400] if last else
                                    "a producer reported it cannot run"), prod[:120])
            if r.returncode != 0:
                return FAIL                           # a producer that RAN and failed cannot concur
            outs.add(r.stdout.rstrip())
        return _pf(len(outs) == 1)                    # green iff every producer agreed
    if typ == "cmd":
        cmd = target
    elif typ in custom:
        cmd = custom[typ]["cmd"].replace("{target}", target)
    else:
        # A verb this engine does not have (not a builtin, not a project [checks.<type>]) is
        # UNAVAILABLE, not FAIL: an engine that lacks a verb a bib names has not REFUTED the claim,
        # it CANNOT CHECK it — so a bib written for a newer engine does not read as silently refuted
        # on an older one (the version-skew-as-silent-refutation hazard, ask-result-tristate).
        return unavailable(f"this engine has no `{typ}:` verb — a bib written for a newer "
                           f"engine, or a project [checks.{typ}] this project does not declare",
                           typ)
    return run_ok(cmd, project_dir, Path(project_dir).name)


def _check_cmd(check: str, custom: dict, project_dir: Path | None = None) -> str | None:
    """The shell command a check RUNS — or None for file:, which opens only its target.
    The single source of the command behind cmd:/custom/result:, so footprint() traces
    exactly what resolves() runs.
    """
    typ, _, target = check.partition(":")
    if typ == "file":
        return None
    # Λ·trace·quote — result:/concept: build a SHELL string (footprint() runs it under strace),
    # and the target comes from the bib, so it is interpolated with shlex.quote.  resolves()
    # runs these two verbs through an argv LIST, never a shell, so the trace was the one place
    # a target reached `sh -c` unquoted — a divergence between what runs and what is traced, on
    # top of the injection seam.  Λ·key·graded (a key may carry `/`) does not itself break
    # quoting, but it widens the charset a bib key can hold, so the latent seam gets closed
    # rather than left resting on "no key has ever contained a metacharacter".
    if typ == "result":
        proj, _, claim = target.partition("#")
        only = f"--only {shlex.quote(claim)} " if claim else ""
        return (f"{sys.executable} {_GATE} --json --safe --without-K {only}"
                f"{shlex.quote(str(_sibling_for(project_dir, proj)))}")
    if typ == "concept":
        # The CANDIDATE library's command (the project's own first).  In the per-key fallthrough
        # case (Λ·library·fallthrough — the project library answers exit 2 and resolves() retries
        # the engine's) this traces the rc-2 probe, not the engine run: a bounded imprecision —
        # concept: carries no local footprint engine-side (bibtex.bzl skips it), and a downstream
        # fallthrough's footprint would need a run to discover, which a trace-string must not do.
        return (f"{sys.executable} {shlex.quote(str(_library_for(project_dir) / 'concepts.py'))} "
                f"{shlex.quote(target)}")
    if typ == "agree":   # trace every producer's reads — the footprint is their union
        return "; ".join(p.strip() for p in target.split("|||") if p.strip())
    if typ == "cmd":
        return target
    if typ in custom:
        return custom[typ]["cmd"].replace("{target}", target)
    return None


# strace open/openat line: open[at](… "PATH", FLAGS[, MODE]) = RC   (RC<0 ⇒ failed open)
_OPEN_RE = re.compile(
    r'open(?:at)?\((?:AT_FDCWD, )?"(?P<path>(?:[^"\\]|\\.)*)", (?P<flags>[^),]*)[^)]*\)'
    r'\s*=\s*(?P<rc>-?\d+)')


def parse_reads(trace_text: str, project_dir: Path, scope: Path) -> "list | None":
    """Φ·footprint PARSE (pure) — the READ files in an strace openat/open trace, `scope`-relative:
    a successful open (rc≥0) that is not write-only, of a real file under `scope`.  SPLIT from the
    CAPTURE (the strace subprocess — a process op = Bazel's job, Φ·spawn·foot), so the parse (the
    paperkit-owned logic: which opens count as inputs) is testable IN-PROCESS over a canned trace,
    not by running strace.  Returns the sorted read set; None if the trace shows NO opens at all
    (strace never attached — the Φ·degrade sentinel; [] would falsely mean 'reads nothing').
    """
    reads, traced = set(), False
    for line in trace_text.splitlines():
        m = _OPEN_RE.search(line)
        if not m:
            continue                                  # unparsed line
        traced = True                                 # an open logged — strace DID attach (any real process opens libc)
        if m.group("rc").startswith("-") or "O_WRONLY" in m.group("flags"):
            continue                                  # failed open, or write-only = output, not an input
        raw = m.group("path")
        p = (Path(raw) if raw.startswith("/") else project_dir / raw).resolve()
        if not p.is_file():
            continue                                  # directories (O_DIRECTORY), /dev nodes, gone — not a hashable input
        try:
            reads.add(str(p.relative_to(scope)))
        except ValueError:
            continue                                  # outside the scope — not an input we track
    return sorted(reads) if traced else None


def producer_footprints(check: str, project_dir: Path, custom: dict,
                        scope: "Path | None" = None) -> "dict | None":
    """Ε·corro·phi — Φ per PRODUCER, for an `agree:` check.  {producer: [reads]}, or None.

    `footprint()` traces the whole check and returns ONE list; for `agree:` the traced command is
    the producers `; `-joined, so their reads are UNIONED and the partition — the only thing that
    could say whether they share ground — is discarded at that join.  This traces each producer
    separately and keeps them apart.

    ⚑ WHY THIS IS THE RIGHT INSTRUMENT AND A STRING COMPARISON IS NOT.  Corroboration asks
    whether two producers are DECORRELATED, and `set()` over their command strings answers only
    whether they were SPELLED differently.  Two producers with DISJOINT read footprints provably
    share no input — a sound certificate, not a heuristic.  Two that overlap share at least those
    files, and the intersection does not merely suggest shared premises, it NAMES them.

    Measured on the tree's only live agree:, whose two producers both run
    `python3 checks/prose.py < ../paper/paper.md` and both use pandoc: the intersection is the
    shared normalizer and the shared source, so a bug in either is invisible to that check BY
    CONSTRUCTION — while the string test called it `independent`.

    None (never {}) when the trace is unavailable, matching footprint()'s Φ·degrade contract: an
    unmeasurable footprint must not read as a measured-empty one.  A non-`agree:` check gets None
    too — it has no producers to partition.
    """
    typ, _, target = check.partition(":")
    if typ != "agree":
        return None
    project_dir = Path(project_dir).resolve()
    scope = Path(scope).resolve() if scope else project_dir
    out = {}
    for prod in (x.strip() for x in target.split("|||")):
        if not prod:
            continue
        reads = footprint("cmd:" + prod, project_dir, custom, scope)
        if reads is None:                      # Φ·degrade on ANY producer ⇒ no partition at all
            return None
        out[prod] = reads
    return out or None


def corroboration_of(check: str, project_dir: Path, custom: dict,
                     scope: "Path | None" = None) -> "tuple | None":
    """Ε·corro·phi — the CORROBORATION verdict for an `agree:`, from measured footprints.

    Returns (value, shared) where value is `independent` (pairwise-disjoint reads — no shared
    input, certified) or `correlated` (some pair overlaps), and `shared` names the intersection
    that made it correlated.  None when the footprints could not be measured, which the caller
    must render as `distinct` — the honest "≥2 producers, sharing NOT measured" state — rather
    than as either verdict.
    """
    fps = producer_footprints(check, project_dir, custom, scope)
    if not fps or len(fps) < 2:
        return None
    sets = [set(v) for v in fps.values()]
    shared = set()
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            shared |= sets[i] & sets[j]
    return ("correlated", sorted(shared)) if shared else ("independent", [])


def footprint(check: str, project_dir: Path, custom: dict, scope: "Path | None" = None) -> list:
    """Φ·footprint — the READ footprint: the files this check OPENS for reading when it runs
    (traced with strace), relative to `scope` (default the project dir).  A SOUND basis for
    caching: a check is a pure function of its inputs, so if a diff touches none of these the
    verdict cannot change.  Distinct from the SENSITIVITY footprint (Δ's `tests` = files a single
    mutation flips) — a negative-assertion check reads inputs no corruption flips, so reads ⊇
    sensitivity, and only reads is safe to cache on.  Best-effort: needs strace, and resolves
    openat with AT_FDCWD or absolute paths.

    scope=repo_root captures CROSS-PACKAGE reads (.githooks, sibling projects, the engine) as
    repo-relative paths — the basis Ζ·foot maps to each check target's Bazel deps; the default
    (project-relative) is the Δ cache's key, which must stay project-scoped.
    """
    project_dir = Path(project_dir).resolve()
    scope = Path(scope).resolve() if scope else project_dir
    typ, _, target = check.partition(":")
    if typ == "file":
        return [target] if (project_dir / target).exists() else []   # opens only its target
    cmd = _check_cmd(check, custom, project_dir)
    if cmd is None:
        return []
    with tempfile.NamedTemporaryFile("w+", suffix=".strace", delete=False) as tf:
        trace = Path(tf.name)
    try:
        try:
            subprocess.run(["strace", "-f", "-qq", "-e", "trace=openat,open", "-o", str(trace),
                            "sh", "-c", cmd], cwd=project_dir, env=clean_env(), capture_output=True)
        except FileNotFoundError:
            return None                                   # Φ·degrade: strace not installed
        # Φ·degrade: when strace cannot trace — absent (above) or unable to ATTACH (no ptrace, e.g. a
        # hardened container → an EMPTY trace) — parse_reads returns None, never [].  [] means "reads
        # nothing": it hashes stable (the cache would over-reuse a grade whose inputs we never saw) and
        # scopes the sweep to nothing (a wrong vacuous grade).  None ⇒ don't-cache + full-surface sweep.
        return parse_reads(trace.read_text(errors="replace"), project_dir, scope)
    finally:
        trace.unlink(missing_ok=True)
