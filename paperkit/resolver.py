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
    Just Works on identity)."""
    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "_name", name)

    @property
    def passed(self) -> bool:
        return self is PASS

    def __repr__(self) -> str:
        return f"Verdict.{self._name}"


PASS = Verdict("PASS")
FAIL = Verdict("FAIL")
UNAVAILABLE = Verdict("UNAVAILABLE")


def _pf(ok: bool) -> Verdict:
    """A check that RAN and decided: True → PASS, False → FAIL.  (Never UNAVAILABLE — that is the
    could-not-evaluate seam, returned explicitly at each such site.)"""
    return PASS if ok else FAIL


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
    live instance: they could never cite an engine concept even where it was the honest import."""
    if project_dir is not None:
        p = Path(project_dir).resolve()
        for base in (p, p.parent):                    # the project's own, then its repo root's
            cand = base / "library"
            if (cand / "concepts.py").is_file():
                return cand
    return _LIBRARY


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
    "result":  {"arg": "<project>",   "verb": "parses",  "crosses": True,
                "passes": "the sibling project's gate verdict parses green"},
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

# Ω·config — the knob this module RESOLVES, declared here (place-by-ownership; the kernel hosts
# the mechanism only).
PATH = config.Param("path", "PAPERKIT_PATH",
                    help="pin tool resolution to these absolute dirs (colon-separated) instead of the host PATH — reproducibility, and dropping user-writable shadow dirs")


def clean_env(env: dict | None = None) -> dict:
    """A sanitized environment for running a check: the controlled allow-list only, so
    no LD_PRELOAD/IFS/BASH_ENV/PYTHONPATH and the like reach the command.  PATH's relative
    and empty entries are dropped (Τ·path) — they would resolve a tool to the cwd (the
    project dir being gated), so a document could shadow a tool by planting it beside itself."""
    src = os.environ if env is None else env
    out = {k: v for k, v in src.items()
           if (k in _ENV_KEEP or k.startswith(_ENV_KEEP_PREFIX)) and k not in _ENV_DROP}
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
    by WORK DONE, not wall time."""
    def _set():
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds + 3))
    return _set


def run_ok(cmd: str, cwd: Path) -> Verdict:
    """Run a shell command: it RAN and exited 0 → PASS, ran and exited non-zero (or exceeded its CPU
    budget / the wall backstop) → FAIL, could not be SPAWNED at all → UNAVAILABLE.  The last arm is the
    same could-not-evaluate seam as the crossing verbs, one verb down: an un-spawnable cmd is not a
    refuted claim, it is an unchecked one, and folding it into FAIL would be the exact bug this change
    removes for the most-used verb.  A cmd that BURNS its CPU budget (a mutation-induced busy loop), by
    contrast, IS a fail — a check that never answers has not passed, and the hang is a real behavioural
    flip the sweep must see; measuring CPU not wall keeps a lease-queued check from a false FAIL."""
    import os
    import signal
    cpu = int(os.environ.get("PAPERKIT_CHECK_CPU", CHECK_CPU))
    wall = int(os.environ.get("PAPERKIT_CHECK_TIMEOUT", CHECK_TIMEOUT))
    # start_new_session so a hang kills the WHOLE process group — a `shell=True` timeout otherwise
    # reaps only the shell and orphans the real child (the hanging witness), which then spins on.
    try:
        p = subprocess.Popen(cmd, shell=True, cwd=cwd, env=clean_env(),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True, preexec_fn=_cpu_rlimit(cpu))
        try:
            rc = p.wait(timeout=wall)
            # SIGXCPU (‑signal 24) / SIGKILL from the CPU rlimit ⇒ negative returncode ⇒ FAIL, not PASS.
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
        try:
            argv = [sys.executable, str(_GATE), "--json", "--safe", "--without-K", target]
            r = subprocess.run(argv, cwd=project_dir, env=clean_env(),
                               capture_output=True, text=True)
            rec = json.loads(r.stdout or "{}")
            if rec.get("available") is False:         # the sibling's own cannot-run
                return UNAVAILABLE
            return _pf(bool(rec.get("pass")))
        except Exception:                             # the sibling is unreachable
            return UNAVAILABLE
    if typ == "concept":
        # Λ·witness — a concept: check IMPORTS a concept authored and GRADED once in the library.
        # For the LIVE verdict (the direct-CLI gate path; the Bazel //:hook path reads the library's
        # records via pk_result/pk_grade), RUN the library witness by ABSOLUTE path — the concept is
        # OWNED and separately gated by the library, so this is COMPOSITION (like result:), not
        # re-authoring.  The witness resolves its own engine via __file__, so the importing view needs
        # nothing staged; its adequacy is the imported certificate (verdict + engine fingerprint).
        try:
            lib = _library_for(project_dir)
            r = subprocess.run([sys.executable, str(lib / "concepts.py"), target],
                               cwd=lib, env=clean_env(), capture_output=True)
            # Λ·library·fallthrough — per-KEY, not per-directory: exit 2 is the library's own
            # "not mine" sentinel, so a project library lacking the key falls through to the
            # engine's (the true owner answers); any other exit is the OWNING library's verdict.
            # The owning case runs ONCE; only a fallthrough pays the cheap rc-2 probe first.
            if r.returncode == 2 and lib != _LIBRARY:
                r = subprocess.run([sys.executable, str(_LIBRARY / "concepts.py"), target],
                                   cwd=_LIBRARY, env=clean_env(), capture_output=True)
            # exit 2 from the FINAL owner = "nobody owns this key": the concept is UNAVAILABLE (no
            # library can witness it), NOT refuted.  Any other exit is the owning library's verdict.
            if r.returncode == 2:
                return UNAVAILABLE
            return _pf(r.returncode == 0)
        except Exception:                             # the library is unreachable
            return UNAVAILABLE
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
        return UNAVAILABLE
    return run_ok(cmd, project_dir)


def _check_cmd(check: str, custom: dict, project_dir: Path | None = None) -> str | None:
    """The shell command a check RUNS — or None for file:, which opens only its target.
    The single source of the command behind cmd:/custom/result:, so footprint() traces
    exactly what resolves() runs."""
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
        return f"{sys.executable} {_GATE} --json --safe --without-K {shlex.quote(target)}"
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
    (strace never attached — the Φ·degrade sentinel; [] would falsely mean 'reads nothing')."""
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
    (project-relative) is the Δ cache's key, which must stay project-scoped."""
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
