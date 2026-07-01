#!/usr/bin/env python3
"""Ξ·dag·eval — a claim WITNESS's engine-module CLOSURE ROOTS: the engine modules its check touches,
from which the build stages the transitive .pyc/.py closure (PycInfo, paperkit/dag.bzl) instead of
the flat engine.  Two AST-derived edge kinds (NEVER grep — a grep matches the name in prose/strings):

  IMPORT     — a bare `import X` / `from X import` (module-level, shared by every witness; and per
               witness body, de-lazied per Ξ·dag·check).
  SUBPROCESS — an `fx.<helper>(...)` call → the CLI entrypoint _fixture spawns (project/gate/
               discriminate).  The helper→CLI map is DERIVED from _fixture.py (its property, not
               hardcoded here): the module-level NAME = ENGINE / "x.py" constants, then which of
               those each helper references.
  READ       — a `"x.py"` string constant (claims.py reads gate/resolver/project sources via
               read_text at MODULE level) → that module must be staged as .py.

Intra-claims.py calls are followed (a witness calling the local _parse helper inherits its `import
project`).  Emits `claim<TAB>paperkit/<relpath>.py` per (claim, root); the codegen maps each root to
its //paperkit:<target> pk_pyc target and PycInfo expands the transitive cone.  The check module's
module-level roots are shared by every claim (claims.py imports _fixture + read_texts three sources).

Usage: closure.py --check paper/checks/claims.py --fixture paperkit/tests/_fixture.py <engine.py>…"""
import argparse
import ast
import sys
from pathlib import Path


def _fx_cli(fixture_text, names):
    """helper name → {engine module stem it runs}, DERIVED from _fixture.py: its engine IMPORTS
    (Φ·spawn — gate.main/project.main run in-process) UNION the engine .py PATH-CONSTANTS it references
    (the grade helpers still SPAWN discriminate by its DISCRIMINATE = ENGINE/"discriminate.py" path —
    Φ·spawn·sweep).  Follows intra-fixture calls (gate() → _projected() → project)."""
    tree = ast.parse(fixture_text)
    const = {}  # NAME → stem, from module-level PROJECT/GATE/DISCRIMINATE = ENGINE / "x.py"
    for n in tree.body:
        if isinstance(n, ast.Assign):
            tgts = n.targets[0].elts if isinstance(n.targets[0], ast.Tuple) else [n.targets[0]]
            vals = n.value.elts if isinstance(n.value, ast.Tuple) else [n.value]
            for t, v in zip(tgts, vals):
                if not isinstance(t, ast.Name):
                    continue
                for s in ast.walk(v):
                    if isinstance(s, ast.Constant) and isinstance(s.value, str) and s.value.endswith(".py"):
                        stem = Path(s.value).stem
                        if stem in names:
                            const[t.id] = stem
    funcs = {fn.name: fn for fn in tree.body if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))}

    def roots(name, seen):
        if name in seen or name not in funcs:
            return set()
        seen.add(name)
        fn = funcs[name]
        r = _imports(fn, names)
        r |= {const[x.id] for x in ast.walk(fn) if isinstance(x, ast.Name) and x.id in const}
        for c in ast.walk(fn):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id in funcs:
                r |= roots(c.func.id, seen)
        return r

    return {name: roots(name, set()) for name in funcs}


def _imports(node, names):
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names if a.name in names}
        elif isinstance(n, ast.ImportFrom) and n.module in names:
            out.add(n.module)
    return out


def _reads(node, names):
    return {Path(n.value).stem for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value.endswith(".py") and Path(n.value).stem in names}


def _fx_calls(node, cli):
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "fx":
            out |= cli.get(n.attr, set())
    return out


def _roots_of(node, names, cli):
    return _imports(node, names) | _reads(node, names) | _fx_calls(node, cli)


def _dir_consts(relpath, tree):
    """Module-level Path DIR constants → their sandbox-relative prefix.  The check runs with __file__
    at its REPO-RELATIVE path in the hermetic sandbox, so `Path(__file__).resolve().parents[N]` is that
    path with N+1 trailing components dropped: for checks/readme.py, parents[1] = "" (root); for
    paper/checks/claims.py, parents[1] = "paper".  NAME / "sub" extends a known prefix (ENGINE =
    ROOT / "paperkit" → "paperkit").  A file toggle must hit exactly these sandbox paths."""
    parts = relpath.split("/")
    pref = {}
    for n in tree.body:
        if not isinstance(n, ast.Assign) or not isinstance(n.targets[0], ast.Name):
            continue
        tgt, v = n.targets[0].id, n.value
        if (isinstance(v, ast.Subscript) and isinstance(v.value, ast.Attribute)
                and v.value.attr == "parents" and isinstance(v.slice, ast.Constant)
                and isinstance(v.slice.value, int)
                and any(isinstance(x, ast.Name) and x.id == "__file__" for x in ast.walk(v))):
            pref[tgt] = "/".join(parts[:-(v.slice.value + 1)])       # Path(__file__)….parents[N]
        elif (isinstance(v, ast.BinOp) and isinstance(v.op, ast.Div) and isinstance(v.left, ast.Name)
              and v.left.id in pref and isinstance(v.right, ast.Constant) and isinstance(v.right.value, str)):
            pref[tgt] = "/".join(p for p in (pref[v.left.id], v.right.value) if p)   # NAME / "sub"
    return pref


def _exists_paths(node, pref):
    """Sandbox paths a witness tests via `(BASE / "leaf").exists()` (BASE a known dir constant) — the
    EXISTS edges.  A claim asserting a file's presence/absence is falsifiable by TOGGLING that file
    (Ζ·mutant·struct·node-kinds): the file analog of the import+/- toggle.  Only plain string leaves
    (not f-strings / loop vars) are resolved here."""
    out = set()
    for c in ast.walk(node):
        if not (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "exists"):
            continue
        r = c.func.value
        if (isinstance(r, ast.BinOp) and isinstance(r.op, ast.Div) and isinstance(r.left, ast.Name)
                and r.left.id in pref and isinstance(r.right, ast.Constant) and isinstance(r.right.value, str)):
            out.add((pref[r.left.id] + "/" + r.right.value).lstrip("/"))
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", required=True, help="the check module, e.g. paper/checks/claims.py")
    ap.add_argument("--fixture", required=True, help="the fixture module, e.g. paperkit/tests/_fixture.py")
    ap.add_argument("--relpath", default="", help="the check's REPO-RELATIVE path (for parents[N] resolution); defaults to --check")
    ap.add_argument("engine", nargs="+", help="the engine module .py paths (the resolvable names)")
    a = ap.parse_args(argv)

    names = {Path(p).stem: p for p in a.engine}      # stem → relpath
    cli = _fx_cli(Path(a.fixture).read_text(), names)
    tree = ast.parse(Path(a.check).read_text())

    funcs = {fn.name: fn for fn in tree.body if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))}

    # BASE — the module-level roots, run on EVERY witness (claims.py imports _fixture + read_texts
    # gate/resolver/project at import).  Top-level statements only (defs handled per-witness).
    base = set()
    for stmt in tree.body:
        if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            base |= _roots_of(stmt, names, cli)

    def roots(fnname, seen):
        if fnname in seen or fnname not in funcs:
            return set()
        seen.add(fnname)
        fn = funcs[fnname]
        r = _roots_of(fn, names, cli)
        for c in ast.walk(fn):        # follow intra-claims.py calls (a witness → local _parse helper)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id in funcs:
                r |= roots(c.func.id, seen)
        return r

    # CLAIMS = {key: fn} — the registry; emit per (claim key, root module).
    claims = {}
    for n in tree.body:
        if (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CLAIMS" for t in n.targets)
                and isinstance(n.value, ast.Dict)):
            for k, v in zip(n.value.keys, n.value.values):
                if isinstance(k, ast.Constant) and isinstance(v, ast.Name):
                    claims[k.value] = v.id

    # Ζ·mutant·struct·node-kinds — per-claim FILE toggle sites, from the witness's own .exists() tests
    # (an EXISTS edge, alongside the .py closure roots).  The falsifier is the TOGGLE of the artifact's
    # CURRENT state (checked here at analysis time, cwd = repo root): an absent file → file+ (inject
    # it, falsifying "X does not exist" — rm-next's cli.py); a present file → file- (drop it, falsifying
    # "X exists").  No `not`-parsing needed: the counterfactual is simply the opposite of what is.
    pref = _dir_consts(a.relpath or a.check, tree)

    for key in sorted(claims):
        for stem in sorted(base | roots(claims[key], set())):
            print("{}\t{}".format(key, names[stem]))
        for path in sorted(_exists_paths(funcs[claims[key]], pref)):
            op = "file-" if Path(path).exists() else "file+"
            print("{}\t{}:{}".format(key, op, path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
