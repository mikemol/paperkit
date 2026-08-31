"""Ω·config — the ONE pipeline every paperkit configurable resolves through.

Each knob has TOTAL and EQUAL coverage along the same four sources, in the same precedence:

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
honest.  See the `config` project.

⚑ Ζ·config·typed — THE TYPES WERE MISSING, NOT WRONG, AND THE COST FELL ON THE CALLERS.  Bare
`tuple`/`dict`/`list` annotations and unannotated helpers made every read of a Param `Any`, and
`disallow_any_expr` then flagged the EXPRESSION at each use — so a boundary suite that merely
named `from paperkit import config` inherited 65 findings it did not create and could not land
its own two-line fix.  The debt was invisible while every consumer reached this module by
`sys.path.insert` plus a bare `import config`, which mypy cannot follow: the injection HID it
rather than causing it.  Typed here, at the owner, so naming the engine costs a caller nothing.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # ⚑ TYPE-ONLY, AND HONESTLY SO.  These three name nothing this module CALLS — they annotate
    # a callable default and two iterable parameters — so the block is not a dodge.  `graph.py`
    # earned a correct refusal for exactly this shape when the symbol WAS read at runtime; the
    # test is use, not convenience, and here none of the three is used at runtime.
    from collections.abc import Callable, Iterable, Sequence

# What a knob can resolve to.  A `default` may also be a CALLABLE producing one, which `resolve`
# invokes lazily — that is how a default can depend on the environment without being read at
# import time.
Value = str | bool | int | None

# ⚑ THE TUPLE FORM, NOT `str | bool | int`.  A PEP-604 union written inside `isinstance()` is an
# EXPRESSION evaluating to `UnionType`, which mypy types `Any` — so the narrowing guard would
# itself trip `disallow_any_expr`.  The tuple is the typed spelling of the same test.
_SCALARS = (str, bool, int)


@dataclass(frozen=True)
class Param:
    """One configurable: its CLI flag, env var, paper.toml key, default, choices, and flagness."""

    name: str
    env: str
    config: str | None = None
    default: Value | Callable[[], Value] = None
    choices: tuple[str, ...] | None = None
    flag: bool = False                          # a boolean switch (presence), not a value
    aliases: tuple[str, ...] = ()               # extra CLI spellings (e.g. --without-k)
    help: str = ""

    @property
    def cli(self) -> str:
        """The long-form flag this knob answers to."""
        return f"--{self.name}"


def _truthy(s: object) -> bool:
    """Read an env-shaped value as a boolean — anything but the explicit falsehoods is True."""
    return str(s).lower() not in ("", "0", "false", "no", "off")


def _argval(p: Param, argv: Sequence[str]) -> str | None:
    """Extract the value `argv` gives `p` — `--name VALUE` or `--name=VALUE` — or None."""
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
_ARGS: dict[str, str] = {}


def apply_args(argv: Sequence[str], registry: Iterable[Param]) -> None:
    """Capture this CLI invocation's args process-locally, so an explicit arg overrides the env.

    Call ONCE at a CLI entry, before resolving, with the entry's composed REGISTRY (the Params
    its import cone hosts).  Child checks do not inherit these.  REPLACES (not accumulates): a
    flag/value absent from argv is absent from _ARGS — so repeated IN-PROCESS invocations (a
    hermetic def-sweep cell, or a fixture helper calling gate.main then discriminate.main;
    Φ·spawn) each see only their own args, never a prior invocation's leaked --safe/--without-K.
    """
    _ARGS.clear()
    for p in registry:
        if p.flag:
            if p.cli in argv or any(a in argv for a in p.aliases):
                _ARGS[p.env] = "1"
        else:
            v = _argval(p, argv)
            if v is not None:
                _ARGS[p.env] = v


def resolve(p: Param, config: dict[str, object] | None = None) -> Value:
    """Resolve `p`: explicit ARG (this process) > ENV var > project CONFIG > default.

    Flags resolve to bool; values validate against p.choices.
    """
    cfg = config or {}
    raw = _ARGS.get(p.env, os.environ.get(p.env))      # arg (local) over env
    if p.flag:
        if raw is not None:
            return _truthy(raw)
        if p.config is not None and p.config in cfg:
            return bool(cfg[p.config])
        return bool(p.default)

    val: Value = raw
    if val is None and p.config is not None:
        # ⚑ paper.toml is UNTYPED DATA (tomllib yields object), so the narrowing happens HERE at
        # the seam rather than propagating an Any inward.  A config value of an unexpected shape
        # reads as absent and falls through to the default — the same outcome as omitting it.
        from_cfg = cfg.get(p.config)
        val = from_cfg if isinstance(from_cfg, _SCALARS) else None
    if val is None:
        d = p.default
        # ⚑ A CALLABLE DEFAULT IS NARROWED AT ITS CALL.  `Callable[[], Value]` returns Value, so
        # the result needs no cast; splitting the branch keeps the union out of the assignment
        # and off every downstream expression.
        val = d() if callable(d) else d
    if val is not None and p.choices is not None and val not in p.choices:
        msg = f"paperkit: {p.cli} must be one of {sorted(p.choices)} (got {val!r})"
        raise SystemExit(msg)
    return val


def positionals(argv: Sequence[str], registry: Iterable[Param]) -> list[str]:
    """Strip every registered flag and valued flag's value from argv, keeping the positionals.

    Uses the entry's composed REGISTRY so no CLI hand-maintains the skip list.
    """
    reg = list(registry)
    known = {p.cli for p in reg} | {a for p in reg for a in p.aliases}
    valued = {p.cli for p in reg if not p.flag}
    out: list[str] = []
    skip = False
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
