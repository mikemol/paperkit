#!/usr/bin/env python3
"""Ξ·dag·eval — a claim WITNESS's engine-module CLOSURE ROOTS: the engine modules its check touches,
from which the build stages the transitive .pyc/.py closure (PycInfo, paperkit/dag.bzl) instead of
the flat engine.  Two AST-derived edge kinds (NEVER grep — a grep matches the name in prose/strings):

  IMPORT     — a bare `import X` / `from X import` (module-level, shared by every witness; and per
               witness body, de-lazied per Ξ·dag·check).  A per-capability fixture import
               (`from _fixture_gate import gate`, Μ·kernel·fixture·split) is an ordinary IMPORT
               root: the _fixture_* modules are engine modules whose module-top imports carry the
               honest capability cone, so no fx-facade special-casing exists here any more.
  READ       — a `"x.py"` string constant (claims.py reads gate/resolver/project sources via
               read_text at MODULE level) → that module must be staged as .py.

Intra-claims.py calls are followed (a witness calling the local _parse helper inherits its `import
project`).  Emits `claim<TAB>paperkit/<relpath>.py` per (claim, root); the codegen maps each root to
its //paperkit:<target> pk_pyc target and PycInfo expands the transitive cone.  The check module's
module-level roots are shared by every claim (claims.py imports _fixture_model + read_texts three
sources).

Usage: closure.py --check paper/checks/claims.py <engine.py>…"""
import argparse
import ast
import sys
from pathlib import Path

from imports import imports as _mod_imports


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


def _roots_of(node, names):
    return _imports(node, names) | _reads(node, names)


def _parents_prefix(node, parts):
    """The sandbox prefix of a `Path(__file__).resolve().parents[N]` expression (parts = the check's
    repo-relative path split), or None.  __file__ sits at the check's repo-relative path in the
    hermetic sandbox, so parents[N] is that path with N+1 trailing components dropped: for
    checks/readme.py parents[1] = "" (root); for paper/checks/claims.py parents[1] = "paper".  Handled
    both as a module/function const (ROOT = …parents[1]) AND inline inside a path expression (local_ci:
    …parents[2] / ".githooks" / "pre-commit")."""
    if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
            and node.value.attr == "parents" and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, int)
            and any(isinstance(x, ast.Name) and x.id == "__file__" for x in ast.walk(node))):
        return "/".join(parts[:-(node.slice.value + 1)])
    return None


def _dir_consts(relpath, stmts, pref=None):
    """Path DIR constants in `stmts` → their sandbox-relative prefix.  `Path(__file__)….parents[N]`
    (see _parents_prefix); NAME / "sub" extends a known prefix (ENGINE = ROOT / "paperkit" →
    "paperkit").  Called on the module body for the shared consts, then EXTENDED per witness with its
    function-local ones (project_dag binds `root` inside the function)."""
    parts = relpath.split("/")
    pref = dict(pref) if pref else {}
    for n in stmts:
        if not isinstance(n, ast.Assign) or not isinstance(n.targets[0], ast.Name):
            continue
        tgt, v = n.targets[0].id, n.value
        pp = _parents_prefix(v, parts)
        if pp is not None:
            pref[tgt] = pp
        elif (isinstance(v, ast.BinOp) and isinstance(v.op, ast.Div) and isinstance(v.left, ast.Name)
              and v.left.id in pref and isinstance(v.right, ast.Constant) and isinstance(v.right.value, str)):
            pref[tgt] = "/".join(p for p in (pref[v.left.id], v.right.value) if p)   # NAME / "sub"
    return pref


def _resolve_path(node, pref, parts):
    """A Path EXPRESSION built from dir constants and string literals → its sandbox path, or None.
    A `Path(__file__)….parents[N]` base (inline), a bare dir constant (Name in pref), or `<expr> /
    "sub"` (nested, e.g. root / "report" / "gen.py", or parents[2] / ".githooks" / "pre-commit")."""
    pp = _parents_prefix(node, parts)
    if pp is not None:
        return pp
    if isinstance(node, ast.Name):
        return pref.get(node.id)
    if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
            and isinstance(node.right, ast.Constant) and isinstance(node.right.value, str)):
        base = _resolve_path(node.left, pref, parts)
        return None if base is None else "/".join(p for p in (base, node.right.value) if p)
    return None


def _exists_paths(node, pref, parts):
    """Sandbox paths a witness tests via `(BASE / "leaf").exists()` — the EXISTS edges.  A claim
    asserting a file's presence/absence is falsifiable by TOGGLING that file (Ζ·mutant·struct·node-kinds):
    the file analog of the import+/- toggle.  Only plain-constant path leaves are resolved (not
    f-strings / loop vars)."""
    out = set()
    for c in ast.walk(node):
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "exists":
            p = _resolve_path(c.func.value, pref, parts)
            if p is not None:
                out.add(p)
    return out


def _content_edges(fn, pref, parts):
    """(sandbox path, substring) pairs a witness tests via `"S" in F.read_text()` — the CONTENT edges.
    A claim asserting a substring's presence in a file (project-dag: `result:paper` in the README bib,
    `_delta("paper")`/`--json` in the report generator) is falsifiable by TOGGLING that substring — the
    finest-grain content perturbation, a precise DAG-EDGE drop (not a whole-file corruption that flips
    every reader identically).  Resolves the comparator when it is an inline `F.read_text()` or a
    FUNCTION-LOCAL name bound to one (module-level SRC constants are a coarser, later rung)."""
    reads = {}                                           # local name → file path (bound to X.read_text())
    for n in ast.walk(fn):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                and n.value.func.attr == "read_text"):
            p = _resolve_path(n.value.func.value, pref, parts)
            if p is not None:
                reads[n.targets[0].id] = p
    out = set()
    for c in ast.walk(fn):
        if not (isinstance(c, ast.Compare) and len(c.ops) == 1 and isinstance(c.ops[0], ast.In)
                and isinstance(c.left, ast.Constant) and isinstance(c.left.value, str)):
            continue
        comp = c.comparators[0]
        p = None
        if isinstance(comp, ast.Call) and isinstance(comp.func, ast.Attribute) and comp.func.attr == "read_text":
            p = _resolve_path(comp.func.value, pref, parts)   # inline `"S" in (root / "x").read_text()`
        elif isinstance(comp, ast.Name):
            p = reads.get(comp.id)                         # `"S" in gen` (gen = F.read_text())
        if p is not None:
            out.add((p, c.left.value))
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", required=True, help="the check module, e.g. paper/checks/claims.py")
    ap.add_argument("--relpath", default="", help="the check's REPO-RELATIVE path (for parents[N] resolution); defaults to --check")
    ap.add_argument("engine", nargs="+", help="the engine module .py paths (the resolvable names)")
    a = ap.parse_args(argv)

    names = {Path(p).stem: p for p in a.engine}      # stem → relpath
    # Ξ·dag — the engine import graph (stem → direct engine imports), to expand a witness's closure
    # ROOTS to its full TRANSITIVE cone: the modules the check actually LOADS (PycInfo stages exactly
    # this cone), hence the modules whose def-drop can flip it.  Roots alone UNDER-scope — node-is-claim
    # roots {gate,project,resolver} but exercises bib.parse via project's `entries = bib.parse`, so bib
    # (transitively imported, not a root) must be in the perturbation surface or its flip is missed.
    igraph = {s: _mod_imports(Path(p).read_text(), set(names)) for s, p in names.items()}

    def _cone(seed):
        seen = set(seed)
        stack = list(seed)
        while stack:
            for imp in igraph.get(stack.pop(), ()):
                if imp not in seen:
                    seen.add(imp)
                    stack.append(imp)
        return seen

    tree = ast.parse(Path(a.check).read_text())

    funcs = {fn.name: fn for fn in tree.body if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))}

    # BASE — the module-level roots, run on EVERY witness (claims.py imports _fixture_model + read_texts
    # gate/resolver/project at import).  Top-level statements only (defs handled per-witness).
    base = set()
    for stmt in tree.body:
        if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            base |= _roots_of(stmt, names)

    def roots(fnname, seen):
        if fnname in seen or fnname not in funcs:
            return set()
        seen.add(fnname)
        fn = funcs[fnname]
        r = _roots_of(fn, names)
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
    relpath = a.relpath or a.check
    parts = relpath.split("/")
    mod_pref = _dir_consts(relpath, tree.body)           # the module-level dir constants (shared)

    for key in sorted(claims):
        fn = funcs[claims[key]]
        pref = _dir_consts(relpath, fn.body, mod_pref)   # extend with the witness's function-local ones
        for stem in sorted(_cone(base | roots(claims[key], set()))):
            print("{}\t{}".format(key, names[stem]))
        for path in sorted(_exists_paths(fn, pref, parts)):
            if Path(path).is_dir():
                continue                                 # a dir-existence is not a single-artifact toggle
            op = "file-" if Path(path).exists() else "file+"
            print("{}\t{}:{}".format(key, op, path))
        # Ζ·mutant·struct·node-kinds (BIB/content) — a CONTENT edge, emitted as `claim<TAB>op<TAB>path
        # <TAB>substring` (4 fields; op = content- drop / content+ inject).  Polarity = the TOGGLE of
        # the substring's CURRENT presence (checked here, cwd = repo root): present → drop it, absent →
        # inject it.  Single-line substrings only (the line/tab-delimited transport).
        for path, sub in sorted(_content_edges(fn, pref, parts)):
            here = Path(path).read_text() if Path(path).exists() else ""
            op = "content-" if sub in here else "content+"
            print("{}\t{}\t{}\t{}".format(key, op, path, sub))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
