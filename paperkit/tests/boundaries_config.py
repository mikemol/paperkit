#!/usr/bin/env python3
"""Behavioral-boundary examples for Ω·config — the ONE configurable-resolution pipeline
(config.resolve / apply_args / positionals) — and the ENTRY-REGISTRY completeness boundary
(Μ·kernel·shrink·registry).

⟨P, F, δ⟩.  Every knob resolves the same way: explicit ARG > ENV var > project CONFIG
(paper.toml [paper]) > default.  apply_args captures args PROCESS-LOCALLY (not os.environ), so
a check the grader spawns never inherits the grader's own flags and re-grades under them.

The MECHANISM is exercised on SYNTHETIC Params (the kernel hosts no Param of its own — that
is itself asserted below), so the mechanism tests couple to no specific knob.  The knobs are
DECLARED in the modules that RESOLVE them; each CLI entry composes its REGISTRY from the
Params its import cone hosts.  The completeness guard derives the expected set from dag.bzl
(the owner of the import DAG) + Param introspection — a cone-resolved Param missing from an
entry's composed registry would be a SILENTLY IGNORED flag (green under the wrong config),
which is exactly the failure the guard makes loud.

    python3 paperkit/tests/boundaries_config.py
"""
from __future__ import annotations

import ast
import importlib
import os
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
import config as C  # noqa: E402

# Synthetic Params — the mechanism's specimens (no coupling to any real knob).
VAL = C.Param("syn-val", "PAPERKIT_SYN_VAL", config="syn_val", default="file", choices=("file", "def"))
FLAG = C.Param("syn-flag", "PAPERKIT_SYN_FLAG", config="syn_flag", flag=True, aliases=("--syn-alias",))
SYN = [VAL, FLAG]


def reset(p):
    C._ARGS.clear()
    os.environ.pop(p.env, None)


def _literal(path, name):
    """The value of assignment `name = <literal>` in a .bzl/.py file (ast, never exec)."""
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit(f"bnd-config: no literal {name} in {path}")


def _cone(stem, imports):
    """Transitive import closure of a module STEM over dag.bzl's IMPORTS (keys are paths)."""
    seen, todo = set(), [stem]
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        todo += imports.get(m + ".py", [])
    return seen


def _hosted(mod):
    """The Params a module HOSTS (declares module-level) — introspected, never hand-listed."""
    return {n: v for n, v in vars(mod).items() if isinstance(v, C.Param)}


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Ω·config — arg > env > config > default, one rule for every knob (synthetic specimens)\n")
    p = VAL
    reset(p)
    check("default when nothing is set", C.resolve(p) == "file")
    check("project config (paper.toml [paper]) overrides the default", C.resolve(p, {"syn_val": "def"}) == "def")
    os.environ[p.env] = "file"
    check("env overrides project config", C.resolve(p, {"syn_val": "def"}) == "file")
    C.apply_args(["--syn-val", "def"], SYN)
    check("an explicit arg overrides the env", C.resolve(p, {"syn_val": "def"}) == "def")
    check("apply_args is PROCESS-LOCAL — it does NOT mutate os.environ (a spawned check won't "
          "inherit the grader's flags)", os.environ.get(p.env) == "file")
    reset(p)

    check("a flag is False by default", C.resolve(FLAG) is False)
    C.apply_args(["--syn-flag"], SYN); check("a flag set by its arg is True", C.resolve(FLAG) is True)
    C._ARGS.clear()
    check("a flag set by [paper] config is True", C.resolve(FLAG, {"syn_flag": True}) is True)
    C.apply_args(["--syn-alias"], SYN); check("a flag honours its alias", C.resolve(FLAG) is True)
    C._ARGS.clear()

    os.environ[p.env] = "bogus"
    raised = False
    try:
        C.resolve(p)
    except SystemExit:
        raised = True
    os.environ.pop(p.env, None)
    check("a value outside the param's choices is REFUSED", raised)
    check("positionals strips flags + valued options, keeps the project dir",
          C.positionals(["--syn-val", "def", "--syn-flag", "myproj"], SYN) == ["myproj"])

    # ── Μ·kernel·shrink·registry — the entry-registry completeness boundary ──────────────
    # Expected set DERIVED from the owners: dag.bzl (import DAG) + vars() introspection
    # (hosted Params) — never a hand-list (a guard must not copy what it guards).
    print("\n⟨entry-registry completeness⟩ — Μ·kernel·shrink·registry\n")
    imports = _literal(ENGINE / "dag.bzl", "IMPORTS")
    components = _literal(ENGINE / "components.bzl", "COMPONENTS")
    engine_stems = [f[:-3] for c, fs in components.items() if c != "tests" for f in fs]
    mods = {s: importlib.import_module(s) for s in engine_stems}

    check("the kernel hosts ZERO Params (config.py is the mechanism alone)",
          not _hosted(mods["config"]))
    hosts = {s: _hosted(m) for s, m in mods.items()}
    all_params = [(s, n, p_) for s, h in hosts.items() for n, p_ in h.items()]
    check(f"every Param has exactly ONE host module ({len(all_params)} params)",
          len({id(p_) for _, _, p_ in all_params}) == len(all_params))
    names = [p_.name for _, _, p_ in all_params]
    envs = [p_.env for _, _, p_ in all_params]
    check("knob names are globally unique across all hosts", len(names) == len(set(names)))
    check("env vars are globally unique across all hosts", len(envs) == len(set(envs)))

    def expected(entry_stem):
        return {id(p_): p_.name for s in _cone(entry_stem, imports) if s in hosts
                for p_ in hosts[s].values()}

    entries = {s: mods[s] for s in ("gate", "discriminate", "project")}
    for stem, mod in entries.items():
        exp = expected(stem)
        got = {id(p_): p_.name for p_ in mod.REGISTRY}
        missing = sorted(n for i, n in exp.items() if i not in got)
        extra = sorted(n for i, n in got.items() if i not in exp)
        check(f"{stem}.REGISTRY == the Params its import cone hosts ({len(exp)})"
              + (f" — missing={missing} extra={extra}" if missing or extra else ""),
              not missing and not extra)

    print("\n⟨P, F, δ⟩ minimum-delta pairs\n")
    reset(p); os.environ[p.env] = "file"
    F = C.resolve(p)
    C.apply_args(["--syn-val", "def"], SYN); P_ = C.resolve(p)
    ok = F == "file" and P_ == "def"
    fails.append("arg-over-env") if not ok else None
    reset(p)
    print(f"  {'ok ' if ok else 'XX '}the same knob: an explicit arg flips the resolved value; the env alone does not")
    print("      P (arg given):  resolve == 'def'   (--syn-val def)")
    print("      F (env only):   resolve == 'file'  (PAPERKIT_SYN_VAL=file)")
    print("      δ (min delta): the presence of the explicit arg, which overrides the env\n")

    # F-arm for completeness: drop ONE element from an entry's registry (in-memory, never
    # the tree) → the silently-ignored-flag hole opens and the predicate catches it.
    exp = expected("gate")
    dropped = [p_ for p_ in entries["gate"].REGISTRY][1:]
    caught = {id(p_) for p_ in dropped} != set(exp)
    fails.append("completeness-delta") if not caught else None
    print(f"  {'ok ' if caught else 'XX '}omitting ONE Param from a composed registry is CAUGHT")
    print("      P (intact):  gate.REGISTRY == its cone's hosted Params — every cone flag captured")
    print("      F (dropped): one element removed → that flag would be SILENTLY ignored (green under defaults)")
    print("      δ (min delta): one element of one composed registry list\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print(f"BOUNDARIES: PASS (11 behaviors, {4 + len(entries)} registry invariants, 2 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
