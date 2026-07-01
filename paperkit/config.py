#!/usr/bin/env python3
"""Ω·config — the ONE pipeline every paperkit configurable resolves through, so each has
TOTAL and EQUAL coverage along the same four sources, in the same precedence:

    explicit ARG  >  ENV var (PAPERKIT_*)  >  project CONFIG (paper.toml [paper])  >  default

The trick that makes it uniform: a CLI entry folds its args into the matching PAPERKIT_* env
(apply_args) — so an explicit flag OVERRIDES the env, and the resolved value reaches the deep
resolvers (the grader, the spawned checks) through the env they already read.  After that ONE
fold, every site — CLI or deep — calls resolve(p, config) reading env > config > default.  No
argv threading; container pipelines set the env; an ad-hoc run overrides on the command line.

And because the knobs are DECLARED here as data (not scattered through argv parsing), the
REGISTRY is enumerable — so each configurable can be PROJECTED as a claim (its sources, its
default, and that resolve() honours the precedence).  See the `config` project."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Param:
    """One configurable: its CLI flag (--name), its PAPERKIT_* env var, an optional paper.toml
    [paper] key, a default, optional validation choices, and whether it is a boolean flag."""
    name: str
    env: str
    config: str | None = None
    default: object = None
    choices: tuple | None = None
    flag: bool = False                 # a boolean switch (presence), not a value
    aliases: tuple = ()                # extra CLI spellings (e.g. --without-k)
    help: str = ""

    @property
    def cli(self) -> str:
        return f"--{self.name}"


def _truthy(s) -> bool:
    return str(s).lower() not in ("", "0", "false", "no", "off")


def _argval(p: Param, argv) -> str | None:
    # --name VALUE  or  --name=VALUE
    for i, a in enumerate(argv):
        if a == p.cli and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(p.cli + "="):
            return a.split("=", 1)[1]
    return None


# THIS process's CLI args, captured by apply_args.  Deliberately NOT os.environ: an env var is
# inherited by every child a check spawns, so folding args into the environment would leak the
# grader's own --min-strength into a check that runs the engine recursively (it would re-grade
# under the wrong floor).  Args are invocation-local; ENV is what a container sets to propagate.
_ARGS: dict = {}


def apply_args(argv) -> None:
    """Capture this CLI invocation's args (process-local, not env), so an explicit arg OVERRIDES
    the env.  Call ONCE at a CLI entry, before resolving.  Child checks do not inherit these.  REPLACES
    (not accumulates): a flag/value absent from argv is absent from _ARGS — so repeated IN-PROCESS
    invocations (a hermetic def-sweep cell, or fx calling gate.main then discriminate.main; Φ·spawn)
    each see only their own args, never a prior invocation's leaked --safe/--without-K."""
    _ARGS.clear()
    for p in REGISTRY:
        if p.flag:
            if p.cli in argv or any(a in argv for a in p.aliases):
                _ARGS[p.env] = "1"
        else:
            v = _argval(p, argv)
            if v is not None:
                _ARGS[p.env] = v


def resolve(p: Param, config: dict | None = None):
    """The value of `p`: explicit ARG (this process) > ENV var > project CONFIG (paper.toml
    [paper]) > default.  Flags resolve to bool; values validate against p.choices."""
    config = config or {}
    raw = _ARGS.get(p.env, os.environ.get(p.env))      # arg (local) over env
    if p.flag:
        if raw is not None:
            return _truthy(raw)
        if p.config is not None and p.config in config:
            return bool(config[p.config])
        return bool(p.default)
    val = raw
    if val is None and p.config is not None:
        val = config.get(p.config)
    if val is None:
        val = p.default() if callable(p.default) else p.default
    if val is not None and p.choices is not None and val not in p.choices:
        raise SystemExit(f"paperkit: {p.cli} must be one of {sorted(p.choices)} (got {val!r})")
    return val


# ── the registry: every configurable, declared once as data ──────────────────────────────
ROOT = Param("root", "PAPERKIT_ROOT", config="root",
             help="the Δ sandbox's bounded universe (the dir copied to mutate); else inferred, $HOME refused")
PATH = Param("path", "PAPERKIT_PATH",
             help="pin tool resolution to these absolute dirs (colon-separated) instead of the host PATH — reproducibility, and dropping user-writable shadow dirs")
SAFE = Param("safe", "PAPERKIT_SAFE", config="safe", flag=True,
             help="zero-postulate: an uncited placement FAILS the gate, not merely advises")
WITHOUT_K = Param("without-K", "PAPERKIT_WITHOUT_K", config="without_k", flag=True, aliases=("--without-k",),
                  help="forbid two cited claims sharing a single witness")
JOBS = Param("jobs", "PAPERKIT_JOBS", config="jobs",
             help="gate worker count (default all cores; 1 = serial)")
JSON = Param("json", "PAPERKIT_JSON", flag=True,
             help="emit structured results to stdout (human lines suppressed)")
MIN_STRENGTH = Param("min-strength", "PAPERKIT_MIN_STRENGTH", config="min_strength",
                     choices=("existence", "behavioral"), help="Δ adequacy floor on the FALSIFIABILITY axis")
MIN_CORRO = Param("min-corroboration", "PAPERKIT_MIN_CORROBORATION", config="min_corroboration",
                  choices=("single", "independent"), help="Δ floor on the orthogonal CORROBORATION axis")
RESOLUTION = Param("resolution", "PAPERKIT_RESOLUTION", config="resolution", default="file",
                   choices=("file", "def"), help="Δ mutation surface: file (project only) or def (+ engine)")
TARGET = Param("target", "PAPERKIT_TARGET", config="target", default="pandoc", choices=("pandoc", "web"),
               help="citation render target: pandoc ([@key] for citeproc/PDF) or web (intra-page hyperlinks + anchors, for a blog)")
STATE = Param("state", "PAPERKIT_STATE",
              help="resumable grading: the resumption-token file (persisted between calls)")
BUDGET = Param("budget", "PAPERKIT_BUDGET",
               help="seconds per Δ invocation (<=0 = run to completion; unset = batch grade)")
ALL = Param("all", "PAPERKIT_ALL", flag=True,
            help="Δ grades every checked warrant, not only cited ones")
FOOTPRINT = Param("footprint", "PAPERKIT_FOOTPRINT", flag=True,
                  help="print each check's READ footprint and exit")
NO_CACHE = Param("no-cache", "PAPERKIT_NO_CACHE", flag=True,
                 help="ignore the Δ footprint-cache (re-grade every check)")
DELTA_REPEAT = Param("delta-repeat", "PAPERKIT_DELTA_REPEAT", default="1",
                     help="re-run the pristine baseline N times to detect a flaky (non-deterministic) check")
DELTA_PULSE = Param("delta-pulse", "PAPERKIT_DELTA_PULSE", default="2",
                    help="min seconds between Δ progress pulses to a log (0 = silent)")
CHECK = Param("check", "PAPERKIT_CHECK", flag=True,
              help="project: verify the projection round-trips against the bib, then exit")
ONLY = Param("only", "PAPERKIT_ONLY",
             help="gate: resolve ONLY this one claim's check (the leaf of the recursive check target, Ζ·starlark) and exit")
MUTANT = Param("mutant", "PAPERKIT_MUTANT",
               help="Ζ·mutant: with --only, probe ONE def-site (path or path::qualname) — mutate it, report whether it flips the check, exit (the sweep's atom, for a pk_mutant action)")
INVARIANTS = Param("invariants", "PAPERKIT_INVARIANTS", flag=True,
                   help="gate: verify only the whole-project invariants (PROJECT/COVERAGE/--without-K), not per-check resolution — the NODE of the recursive check, the leaves resolve the checks")

REGISTRY = [ROOT, PATH, SAFE, WITHOUT_K, JOBS, JSON, MIN_STRENGTH, MIN_CORRO, RESOLUTION, TARGET,
            STATE, BUDGET, ALL, FOOTPRINT, NO_CACHE, DELTA_REPEAT, DELTA_PULSE, CHECK, ONLY, INVARIANTS, MUTANT]
BY_NAME = {p.name: p for p in REGISTRY}


def positionals(argv) -> list:
    """The non-option tokens of argv — every registered flag, every valued flag's value, and
    any --x=… removed, using the REGISTRY so no CLI hand-maintains the skip list."""
    known = {p.cli for p in REGISTRY} | {a for p in REGISTRY for a in p.aliases}
    valued = {p.cli for p in REGISTRY if not p.flag}
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False
            continue
        if a in known:
            skip = a in valued          # the next token is this flag's value
            continue
        if a.startswith("-"):
            continue                     # an --x=… or an unknown option — never positional
        out.append(a)
    return out
