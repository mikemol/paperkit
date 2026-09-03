#!/usr/bin/env python3
"""paperkit/checkcache.py — Λ·cache·slice: a persistent check cache keyed on WHAT EACH CHECK REACHES.

A gate re-runs every witness on every invocation, so its cost grows with the library while the edit
per round stays constant.  Keying a cache on the whole module would invalidate everything on every
edit — the module is one file.  The sound key is the SLICE a check can reach: its own witness
function, the transitive closure of the module-level names that function references, and THE FILES
those names live in.

If nothing in that slice changed, the check cannot have changed, so its verdict is reusable.  If the
slice cannot be computed, THE CHECK RUNS — a cache that guesses is worse than none, being exactly the
stale-but-parses failure a gate exists to prevent.

    python3 checkcache.py            # run all routes, using and updating the cache
    python3 checkcache.py --stats    # report hit rate and slice sizes only
    python3 checkcache.py --clear    # drop the cache

WHAT THIS PORT CHANGES, AND WHY — the upstream slice was NAME-keyed within one file, which left a
measured FAIL-OPEN.  `slice_names` inspects only `ast.Name`, so a witness reaching code through a
FUNCTION-LOCAL import binds a local alias that is not a module-level name of the file being indexed:

    def some_witness(which):
        import labelmap as LM          # <- invisible to a name-only slice
        assert LM.lookup(...) == ...

Edits to that imported module then do NOT invalidate the dependent routes, and the cache serves a
stale PASS.  This is not hypothetical: it was live for three route families upstream.  So the key
here is a FILE SET as well as a name set — every module the slice can reach is hashed by content,
and the local-import edge is followed.  A cache whose whole purpose is soundness cannot ship with a
known hole in it.

THE FAIL-CLOSED DISCIPLINE (kept verbatim, and it is the load-bearing half):
  * an unresolvable slice   → no key → the check RUNS, every time
  * only `True` is a hit    → a FAILING check is never cached, so it re-runs until it passes
  * a corrupt cache file    → read as empty → everything runs
  * exit 2 is NOT failure   → "not mine" is a resolution outcome, not a verdict to cache

BOUNDS, STATED HONESTLY.  The slice sees module-level names and imported files.  It does NOT see:
attribute reach into objects obtained non-nominally, data read from non-Python files (a .bib, a
rubric) unless declared, network or environment state, or a witness that mutates module globals
another witness reads (order-dependence defeats any verdict cache).  For `concept:` keys in
particular the engine reports NO local footprint by design — the verb is CROSSING (resolver.py) —
so a concept's invalidation basis is the owning library's certificate, not a file list here.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SRC = HERE / "concepts.py"
DEFAULT_CACHE = HERE / ".checkcache.json"


# ── the slice ─────────────────────────────────────────────────────────────────────────────────

def module_index(src: str):
    """Module-level definitions and assigned names, with their source segments, plus the module's
    own import bindings (alias -> module name) so the slice can follow them to a FILE.

    The returned `bodies` map holds BOTH functions and assignments, keyed by the name they bind:
    the walk in `slice_of` traverses through either, because a constant that names other
    definitions is an edge in the dependency graph exactly as a call is.
    """
    tree = ast.parse(src)
    fns, names, segs, imports = {}, set(), {}, {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fns[node.name] = node
            names.add(node.name)
            segs[node.name] = ast.get_source_segment(src, node) or ""
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
                    segs[t.id] = ast.get_source_segment(src, node) or ""
                    # A CONSTANT'S BODY IS A BODY.  It is indexed alongside the functions so the
                    # walk can traverse THROUGH it: a dispatch table, an operator registry, or any
                    # literal holding references is a real edge in the dependency graph, and
                    # stopping at the constant's own name loses everything it names.  (Measured:
                    # a lifted library's NAND/IMP/CON/XNOR were reachable only through a `BINARY`
                    # dict literal, so a slice that stopped at `BINARY` never saw them — an edit
                    # to the operator would not have invalidated its dependants.)
                    fns[t.id] = node
        elif isinstance(node, ast.Import):
            for a in node.names:
                imports[a.asname or a.name.split(".")[0]] = a.name
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                for a in node.names:
                    imports[a.asname or a.name] = node.module
    return tree, fns, names, segs, imports


def _local_imports(node) -> dict:
    """Import bindings made INSIDE a function body — the edge a name-only slice cannot see.

    This is the fail-open closer.  `import labelmap as LM` inside a witness binds a LOCAL name, so
    it never appears in the module-level name set, and the module it names never enters the hash.
    """
    out = {}
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for a in n.names:
                out[a.asname or a.name.split(".")[0]] = a.name
        elif isinstance(n, ast.ImportFrom):
            if n.module and n.level == 0:
                for a in n.names:
                    out[a.asname or a.name] = n.module
    return out


def slice_of(fn: str, fns, names, imports):
    """(names, modules) reachable from FN: the transitive closure of module-level names, and every
    module reached by an import binding — at module level OR inside any body in the closure.

    THROUGH CONSTANTS, NOT UP TO THEM.  `fns` holds every top-level body, assignments included, so
    a name reached only via a literal (a dispatch table, an operator registry) is still reached.
    Stopping at the constant's own name is a FAIL-OPEN: its contents change, the hash does not.

    Returns None when FN is not a module-level definition; the caller must then RUN the check.
    """
    if fn not in fns:
        return None
    seen, mods, frontier = {fn}, set(), {fn}
    while frontier:
        nxt = set()
        for f in frontier:
            if f not in fns:
                continue
            body = fns[f]
            local = _local_imports(body)
            for node in ast.walk(body):
                if isinstance(node, ast.Name):
                    if node.id in local:
                        mods.add(local[node.id])           # function-local import — the closed hole
                    elif node.id in imports:
                        mods.add(imports[node.id])         # module-level import
                    elif node.id in names and node.id not in seen:
                        seen.add(node.id)
                        nxt.add(node.id)
            # an alias used only as `LM.thing` still reaches the module, even if the bare Name
            # node was consumed as an attribute value — record every local binding outright.
            mods.update(local.values())
        frontier = nxt
    return seen, mods


def _spec_file(mod: str) -> Path | None:
    """Resolve MOD to a file by ASKING THE IMPORT SYSTEM, with no sys.path mutation of our own.

    Ζ·checkcache·keys — this is the arm that must survive Ζ·path·retire.  The directory search
    below it can only find what some caller already put on sys.path; `find_spec` finds what the
    module name actually DENOTES in this interpreter, which is the same question the witness's own
    `import` will answer at run time.  It therefore works identically whether the engine is reached
    flat (`import routes`, today's script route) or as a package (`import paperkit.routes`, after
    the retirement) — MEASURED: both spellings resolve to the same paperkit/routes.py, so the
    CONTENT entering the key is identical across the flip and only the recorded `mod:` NAME differs.
    That name change invalidates every entry once, at the flip, by design; it never serves a stale
    PASS, because a differing name can only ever ADD a miss.

    find_spec must be prosecuted defensively: it returns None for an unknown top-level name but
    RAISES ModuleNotFoundError when an intermediate parent package is missing, and it IMPORTS those
    parent packages as a side effect.  Any failure degrades to None, which the caller reads as
    "record by name only" — the fail-closed direction is the caller's `_owned` gate, not this.
    """
    try:
        spec = importlib.util.find_spec(mod)
    except (ImportError, AttributeError, ValueError):
        return None
    if spec is None:
        return None
    # `origin` is typed `str | None` on ModuleSpec, so read it directly rather than through
    # getattr — getattr's result is Any, and an Any here would reach the key's hash input
    # unchecked, which is the narrowing-at-the-edge this repo's mypy bar exists to force.
    origin: str | None = spec.origin
    if origin is None or origin in ("built-in", "frozen"):
        return None
    p = Path(origin)
    return p if p.is_file() else None


def _module_file(mod: str, search: list[Path]) -> Path | None:
    """Resolve a slice's module name to a FILE: declared search dirs first, then the import system.

    The explicit `search` list is tried first because it is the CALLER'S declaration — a fixture
    naming the temp directory its modules live in must not be answered by a same-named module that
    happens to be installed.  `_spec_file` is the general answer for everything else, and it is what
    makes the engine's own modules resolvable without anyone having mutated sys.path.
    """
    for d in search:
        for cand in (d / f"{mod.replace('.', '/')}.py", d / mod.replace(".", "/") / "__init__.py"):
            if cand.is_file():
                return cand
    return _spec_file(mod)


def _owned(f: Path) -> bool:
    """Is this file the PROJECT's own source, rather than the interpreter's or a dependency's?
    Anything under a stdlib/site-packages/venv directory is somebody else's to version.
    """
    s = str(f)
    return not any(seg in s for seg in ("/site-packages/", "/dist-packages/",
                                        "/lib/python", "/.venv/", "/installs/python/"))


def search_path(src_path: Path) -> list[Path]:
    """Name the directories a slice's modules may live in: the source's own, and nothing more.

    ⚑ Ζ·checkcache·keys — THIS USED TO EXECUTE THE WITNESS AND READ THE sys.path IT ESTABLISHED,
    and that was a stale-green waiting for Ζ·path·retire.  The probe measured the mutations a
    bootstrap happened to leave behind, so with the mutations gone it would have measured the EMPTY
    SET — every engine module unresolvable, every one degraded from a content hash to a bare
    `mod:<name>`, and an edit to an engine module no longer invalidating the witnesses that read it.
    A key that stops tracking content while still looking like a key is exactly the false PASS this
    cache exists to refuse, and it would have arrived silently, as a speed-up.

    The reach is not lost, it MOVED to where it is answerable by construction: `_module_file` now
    asks the import system (`_spec_file`) what a module name denotes, which is the same question the
    witness's own `import` answers, and needs nobody to have mutated anything.  So this function is
    reduced to what it can honestly compute without side effects — the caller's declared directory,
    for modules that are NOT importable by name (a fixture's temp dir).  It no longer imports the
    witness, no longer touches sys.path, and no longer needs a save/restore, because it makes no
    mutation to restore.
    """
    return [src_path.parent]


def slice_key(fn: str, route: str, fns, names, segs, imports, search: list[Path]) -> str | None:
    """A hash of everything the check can reach — its name slice, its route, AND the content of
    every reachable local module file — or None when the slice cannot be computed.

    The ROUTE is part of the key because one witness serves several claims by branching on its
    argument: two routes into the same function are two checks over one slice.

    Third-party and stdlib modules are recorded BY NAME only (they are not resolved under `search`),
    so upgrading a dependency does not invalidate — that is a declared bound, not an oversight: this
    cache's unit is the library's own source.
    """
    sl = slice_of(fn, fns, names, imports)
    if sl is None:
        return None
    reach, mods = sl
    body = "\n".join(f"{n}:{segs.get(n, '')}" for n in sorted(reach))
    parts = [route, body]
    for m in sorted(mods):
        f = _module_file(m, search)
        # Hash only what the PROJECT owns.  Stdlib and site-packages resolve under the search path
        # too, but hashing them would make an interpreter or dependency upgrade invalidate every
        # entry — churn that buys nothing, since this cache's unit is the library's own source.
        # They are recorded BY NAME, so gaining or losing an import still changes the key.
        if f is None or not _owned(f):
            parts.append(f"mod:{m}")
        else:
            parts.append(f"mod:{m}:{hashlib.sha256(f.read_bytes()).hexdigest()}")
    return hashlib.sha256("\x00".join(parts).encode()).hexdigest()


# ── the dispatch table ────────────────────────────────────────────────────────────────────────

def routes_and_owners(src_path: Path) -> dict[str, str]:
    """Map each route to the module-level function that serves it.

    Read by EXECUTION, not by parsing: a route table is typically built with comprehensions and
    post-hoc mutation, so a static read would miss most entries.  Enumeration goes through
    routes.leaves() — the ONE recursive leaf-walk — rather than a hand-rolled loop, so this cannot
    disagree with the resolver about how deep a table goes.  (Upstream had a 2-level loop here
    beside a depth-agnostic resolver: a grade-3 family would resolve for the gate and VANISH from
    the cache's driver, so those checks silently stopped running.)

    ⚑ Ζ·checkcache·keys — THE INSERT HERE WAS ONE STATEMENT DOING TWO JOBS, AND WAS NEVER RESTORED.
    It served this module's own `import routes as R` (a BOOTSTRAP, which the package declaration
    covers and which retires with Ζ·path·retire) and the by-path load of an arbitrary witness (a
    RUNTIME need, which does not).  Fused and unrestored, the process kept the entry forever, so a
    later unrelated import in the same interpreter could resolve out of whatever directory the last
    call happened to pass — a caller-order-dependent import, which is the shape of a heisenbug.

    Split, and NEITHER HALF ADDS A NEW MODULE-LEVEL MUTATION: `routes` is imported function-locally
    (the edge paperkit/dag.bzl already declares), so this file gains no top-level sys.path line for
    Ζ·path·retire to have to remove again; and the runtime half is scoped to the load that needs it
    and undone in a `finally` — the discipline `search_path`'s sibling site already had.
    """
    # ⚑ DELIBERATELY FUNCTION-LOCAL (ruff PLC0415 is accepted here, not suppressed).  A top-level
    # `import routes` resolves only through the flat bootstrap this arc is retiring, so hoisting it
    # would mean adding a module-level sys.path line for Ζ·path·retire to delete again — trading
    # one retirement item for another.  Local, it rides the caller's already-established path and
    # converts to `from paperkit import routes` in one line when the package form lands.
    import routes

    spec = importlib.util.spec_from_file_location("_concepts_probe", src_path)
    if spec is None or spec.loader is None:
        return {}
    mod = importlib.util.module_from_spec(spec)
    before = list(sys.path)
    try:
        sys.path.insert(0, str(src_path.parent))
        sys.modules["_concepts_probe"] = mod
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = before
    out: dict[str, str] = {}
    for path, target in routes.leaves(mod.ROUTES):
        fn = getattr(target[0] if isinstance(target, tuple) else target, "__name__", None)
        if fn:
            out["/".join(path)] = fn
    return out


# ── the run ───────────────────────────────────────────────────────────────────────────────────

def load_cache(cache_path: Path) -> dict:
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except Exception:
            return {}                                      # unreadable → everything runs
    return {}


def run_check(route: str, src_path: Path) -> bool | None:
    """True = certified, False = FAILED, None = exit 2 'not mine'.

    The three-way return is the exit-code protocol (routes.py), and collapsing it is a real bug:
    reading exit 2 as failure reports a route that merely fell through as a broken check.
    """
    r = subprocess.run([sys.executable, src_path.name, route], cwd=src_path.parent,
                       capture_output=True, text=True, timeout=900)
    if r.returncode == 2:
        return None
    return r.returncode == 0


def _key_mode(argv) -> int:
    """Ζ·checkcache·cli — emit ONE slice key for `--key <witness.py> <fn> <route>`, or `-` if the
    slice cannot be computed.  The module's key derivation, reachable as a PROGRAM.

    ⚑ WHY A CLI AND NOT AN IMPORT, WHICH IS THE WHOLE POINT.  `components.bzl` partitions the
    engine and `boundaries_components` enforces the DAG over it.  `checkcache.py` is in
    `library_kernel`; the boundary suites are in `tests`; the two are SIBLINGS with identical
    dependency sets and NEITHER depends on the other.  So a suite that `import checkcache` draws
    an edge SIDEWAYS between peers — measured 2026-09-02, the first such crossing in 45 suites,
    and the guard reddened on it.  Widening `DEPS["tests"]` would license all 45 to reach the
    concept-library kernel to serve one; that is how `vendored: []`'s enforced-property discipline
    erodes, one locally-reasonable addition at a time.

    ⚑⚑ THE TREE ALREADY HAD THE ANSWER.  `boundaries_prove.py` tests `prove.py` — also
    `library_kernel` — and imports NOTHING from it: stdlib plus `subprocess`.  It exercises its
    subject AS A PROGRAM.  That is how the boundary held for 45 suites, and the missing piece was
    never the guard: it was that this module had no entry point to exercise (its `main()` targets
    a `concepts.py` that does not exist, so nothing here was reachable as a program at all).  The
    component guard did not obstruct the test; it named a gap in this module's own surface.

    The caller declares the search path via PYTHONPATH — the same thing a real witness gets — so
    the subprocess measures module resolution as the import system performs it, not as this
    process happens to have been bootstrapped.
    """
    i = argv.index("--key")
    try:
        src, fn, route = argv[i + 1], argv[i + 2], argv[i + 3]
    except IndexError:
        sys.stderr.write("checkcache: --key needs <witness.py> <fn> <route>\n")
        return 2
    p = Path(src)
    if not p.is_file():
        sys.stderr.write(f"checkcache: --key: no such witness source: {src}\n")
        return 2
    _tree, fns, names, segs, imports = module_index(p.read_text())
    k = slice_key(fn, route, fns, names, segs, imports, search_path(p))
    print(k if k is not None else "-")
    return 0


def main(argv, src_path: Path = DEFAULT_SRC, cache_path: Path = DEFAULT_CACHE) -> int:
    if "--key" in argv:
        return _key_mode(argv)
    if "--clear" in argv:
        cache_path.unlink(missing_ok=True)
        print("cache cleared")
        return 0
    src = src_path.read_text()
    _tree, fns, names, segs, imports = module_index(src)
    search = search_path(src_path)
    table = routes_and_owners(src_path)
    cache = load_cache(cache_path)

    keys, uncacheable = {}, []
    for route, fn in table.items():
        k = slice_key(fn, route, fns, names, segs, imports, search)
        (uncacheable.append(route) if k is None else keys.__setitem__(route, k))

    hits = [r for r, k in keys.items() if cache.get(k) is True]
    misses = [r for r in table if r not in hits]

    print(f"routes           : {len(table)}")
    print(f"cacheable        : {len(keys)}   uncacheable: {len(uncacheable)}")
    print(f"cache entries    : {len(cache)}")
    print(f"HITS             : {len(hits)}   MISSES: {len(misses)}")
    if table:
        print(f"hit rate         : {100 * len(hits) // len(table)}%")
    if "--stats" in argv:
        sizes, filecounts = [], []
        for fn in set(table.values()):
            sl = slice_of(fn, fns, names, imports)
            if sl:
                sizes.append(len(sl[0]))
                filecounts.append(len(sl[1]))
        if sizes:
            print(f"slice size       : mean {sum(sizes)/len(sizes):.1f} names, max {max(sizes)}; "
                  f"modules reached mean {sum(filecounts)/len(filecounts):.1f}, max {max(filecounts)}")
        return 0

    t0 = time.time()
    failed, skipped = [], []
    for route in misses:
        ok = run_check(route, src_path)
        if ok is None:
            skipped.append(route)                          # exit 2 — not this library's; never cached
            continue
        if ok and route in keys:
            cache[keys[route]] = True                      # only a PASS is ever recorded
        if not ok:
            failed.append(route)
    # Ζ·write·atomic — replace the PATH, not the inode's contents: a hardlinked twin (a dedup
    # pass, an editor snapshot) must not see this write, and a crash must not leave a torn cache.
    _tmp = cache_path.with_name(f".{cache_path.name}.tmp")
    _tmp.write_text(json.dumps(cache))
    os.replace(_tmp, cache_path)
    print(f"ran {len(misses)} check(s) in {time.time() - t0:.1f}s "
          f"({'all pass' if not failed else f'{len(failed)} FAILED'}"
          f"{f', {len(skipped)} not-mine' if skipped else ''})")
    for f in failed[:10]:
        print(f"   FAILED: {f}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
