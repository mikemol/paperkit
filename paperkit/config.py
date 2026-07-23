#!/usr/bin/env python3
"""Ω·config — the ONE pipeline every paperkit configurable resolves through, so each has
TOTAL and EQUAL coverage along the same four sources, in the same precedence:

    explicit ARG  >  ENV var (PAPERKIT_*)  >  project CONFIG (paper.toml [paper])  >  default

The trick that makes it uniform: a CLI entry folds its args into the matching PAPERKIT_* env
(apply_args) — so an explicit flag OVERRIDES the env, and the resolved value reaches the deep
resolvers (the grader, the spawned checks) through the env they already read.  After that ONE
fold, every site — CLI or deep — calls resolve(p, config) reading env > config > default.  No
argv threading; container pipelines set the env; an ad-hoc run overrides on the command line.

And because each knob is DECLARED as data (a Param) in the module that RESOLVES it
(place-by-ownership — this kernel module hosts the MECHANISM only, no Param of its own;
Μ·kernel·shrink·registry), the union stays enumerable by INTROSPECTION over the engine's
modules — so each configurable can be PROJECTED as a claim (its sources, its default, and
that resolve() honours the precedence).  Each CLI entry composes its REGISTRY from the
Params its import cone hosts; the bnd-config completeness guard holds that composition
honest.  See the `config` project."""
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


def apply_args(argv, registry) -> None:
    """Capture this CLI invocation's args (process-local, not env), so an explicit arg OVERRIDES
    the env.  Call ONCE at a CLI entry, before resolving, with the entry's composed REGISTRY (the
    Params its import cone hosts).  Child checks do not inherit these.  REPLACES
    (not accumulates): a flag/value absent from argv is absent from _ARGS — so repeated IN-PROCESS
    invocations (a hermetic def-sweep cell, or a fixture helper calling gate.main then discriminate.main; Φ·spawn)
    each see only their own args, never a prior invocation's leaked --safe/--without-K."""
    _ARGS.clear()
    for p in registry:
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


def positionals(argv, registry) -> list:
    """The non-option tokens of argv — every registered flag, every valued flag's value, and
    any --x=… removed, using the entry's composed REGISTRY so no CLI hand-maintains the skip list."""
    known = {p.cli for p in registry} | {a for p in registry for a in p.aliases}
    valued = {p.cli for p in registry if not p.flag}
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
