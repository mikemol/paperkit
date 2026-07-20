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
import subprocess
import sys
import tempfile
from pathlib import Path

import config

_GATE = Path(__file__).resolve().parent / "gate.py"   # invoked as a subprocess for result:
_LIBRARY = Path(__file__).resolve().parent.parent / "library"  # the concept-witness library (concept:)


# Λ·registry — THE built-in verb set.  This dict OWNS the enumeration: `resolves` dispatches one
# branch per key, and no other file may re-declare the set — docs render it, witnesses assert
# set-EQUALITY against it, and prose that would name a COUNT ("four verbs") or an ORDINAL ("the
# third verb") says neither, because both hardcode a set's size into a place that cannot see it.
# `arg` is the target's shape, `verb` the one word for what resolution MEANS, `passes` the
# condition — together exactly the columns of the README's resolver table, which is why that
# table can be checked against this and not maintained beside it.
VERBS = {
    "file":    {"arg": "<path>",      "verb": "exists",
                "passes": "the artifact exists"},
    "cmd":     {"arg": "<script>",    "verb": "execs",
                "passes": "the script exits `0`"},
    "result":  {"arg": "<project>",   "verb": "parses",
                "passes": "the sibling project's gate verdict parses green"},
    "agree":   {"arg": "<p>|||<q>",   "verb": "concurs",
                "passes": "the independent producers all exit `0` and emit identical output"},
    "concept": {"arg": "<key>",       "verb": "imports",
                "passes": "the concept library's certificate for that key reads pass"},
}


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


def clean_env(env: dict | None = None) -> dict:
    """A sanitized environment for running a check: the controlled allow-list only, so
    no LD_PRELOAD/IFS/BASH_ENV/PYTHONPATH and the like reach the command.  PATH's relative
    and empty entries are dropped (Τ·path) — they would resolve a tool to the cwd (the
    project dir being gated), so a document could shadow a tool by planting it beside itself."""
    src = os.environ if env is None else env
    out = {k: v for k, v in src.items()
           if (k in _ENV_KEEP or k.startswith(_ENV_KEEP_PREFIX)) and k not in _ENV_DROP}
    pinned = config.resolve(config.PATH)
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


def run_ok(cmd: str, cwd: Path) -> bool:
    try:
        return subprocess.run(cmd, shell=True, cwd=cwd, env=clean_env(),
                              capture_output=True).returncode == 0
    except Exception:
        return False


def resolves(check: str, project_dir: Path, custom: dict) -> bool:
    typ, _, target = check.partition(":")
    if typ == "file":
        return (project_dir / target).exists()        # EXISTS — no subprocess → no lease
    if typ == "result":
        # Ξ·seam — result PARSES (VERBS names every verb; no ordinal here, an ordinal would
        # hardcode the set's size).  It imports a sibling project's gate VERDICT (gate --json) and
        # PARSES it — green iff the parsed verdict reports pass — rather than re-deriving
        # what the sibling owns and separately gates.  cwd = this project's dir, so the
        # target is the sibling's path relative to it.  Δ grades it "imported" (run once),
        # never mutation-sweeping a whole sub-gate.
        try:
            argv = [sys.executable, str(_GATE), "--json", "--safe", "--without-K", target]
            r = subprocess.run(argv, cwd=project_dir, env=clean_env(),
                               capture_output=True, text=True)
            return bool(json.loads(r.stdout or "{}").get("pass"))
        except Exception:
            return False
    if typ == "concept":
        # Λ·witness — a concept: check IMPORTS a concept authored and GRADED once in the library.
        # For the LIVE verdict (the direct-CLI gate path; the Bazel //:hook path reads the library's
        # records via pk_result/pk_grade), RUN the library witness by ABSOLUTE path — the concept is
        # OWNED and separately gated by the library, so this is COMPOSITION (like result:), not
        # re-authoring.  The witness resolves its own engine via __file__, so the importing view needs
        # nothing staged; its adequacy is the imported certificate (verdict + engine fingerprint).
        try:
            argv = [sys.executable, str(_LIBRARY / "concepts.py"), target]
            return subprocess.run(argv, cwd=_LIBRARY, env=clean_env(),
                                  capture_output=True).returncode == 0
        except Exception:
            return False
    if typ == "agree":
        # Δ·agree (Ε·agree) — agree CONCURS (see VERBS; no ordinal, no count).
        # The SAME fact established by N INDEPENDENT producers (split on |||) that
        # must AGREE — every one exits 0 AND emits identical output.  Where cmd: trusts one
        # implementation, agreement across independent producers rules out a shared bug a
        # single check cannot catch: stronger evidence, a distinct KIND.
        producers = [p.strip() for p in target.split("|||") if p.strip()]
        if len(producers) < 2:
            return False                              # agreement needs ≥2 independent producers
        outs = set()
        for prod in producers:
            try:
                r = subprocess.run(prod, shell=True, cwd=project_dir, env=clean_env(),
                                   capture_output=True, text=True)
            except Exception:
                return False
            if r.returncode != 0:
                return False                          # a producer that fails cannot concur
            outs.add(r.stdout.rstrip())
        return len(outs) == 1                         # green iff every producer agreed
    if typ == "cmd":
        cmd = target
    elif typ in custom:
        cmd = custom[typ]["cmd"].replace("{target}", target)
    else:
        return False
    return run_ok(cmd, project_dir)


def _check_cmd(check: str, custom: dict) -> str | None:
    """The shell command a check RUNS — or None for file:, which opens only its target.
    The single source of the command behind cmd:/custom/result:, so footprint() traces
    exactly what resolves() runs."""
    typ, _, target = check.partition(":")
    if typ == "file":
        return None
    if typ == "result":
        return f"{sys.executable} {_GATE} --json --safe --without-K {target}"
    if typ == "concept":
        return f"{sys.executable} {_LIBRARY / 'concepts.py'} {target}"
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
    cmd = _check_cmd(check, custom)
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
