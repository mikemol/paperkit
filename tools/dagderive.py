r"""Ξ·dag·dotted — derive the engine's import DAG with BOTH sides of every edge in ONE namespace.

⚑ THE OLD DERIVATION EMITTED TWO NAMESPACES AND THE BUILD PAID FOR IT.  `tools/imports.py`
recorded an edge as a path-shaped KEY against a bare-stem VALUE —
`"tests/_fixture_delta.py": ["_fixture_model"]` — so `paperkit/BUILD.bazel` had to translate one
into the other before it could name a target:

    _STEM_TO_TARGET = {m.rsplit("/", 1)[-1][:-len(".py")]: m[:-len(".py")] for m in ENGINE_SRCS}
    # IMPORTS keys stems by bare name; a tests/ module's target is tests/<stem>, so map every
    # imported stem back to its owning pk_pyc target name.

⚑⚑ THAT MAP IS A DICT COMPREHENSION KEYED ON BARE STEM, WHICH IS SILENTLY LAST-WINS.  Measured
over the live tree: 79 sources, 79 distinct stems, THREE directories (`.`, `tests`, `tools`)
flattened into one key space — no collision today, and nothing that would refuse one.  A second
`bib.py` under `tests/` would collapse onto `paperkit/bib.py`'s key and the loser's `.pyc` would
simply never be staged for anything importing it.  The failure surfaces as a ModuleNotFoundError
inside a sandboxed cell, which is the shape `components.bzl` records costing four batch runs when
a module went undeclared.  A naming convention with no owner is `guard-must-not-copy` at the
build layer.

Bazel targets are ALREADY path-shaped (`//paperkit:tests/boundaries_jobs`), so recording the
imported module's PATH puts both sides of every edge in the target namespace and
`_STEM_TO_TARGET` becomes an identity.

⚑ RESOLUTION IS BY STEM AND STAYS THAT WAY, because the SOURCES still say `import bib`.
Converting them to `from paperkit import bib` is a separate rung of Ζ·path·retire; what changes
here is only what an edge is RECORDED as.  The resolution is proven total rather than assumed —
measured against the live tree, every import name resolves to exactly one source, 114 edges,
bijective with the flat form — and an ambiguous stem now REFUSES instead of silently picking one.

⚑ AST, NEVER GREP.  A grep matches the name in comments and strings; the project↔rhetoric
"cycle" was such a phantom.
"""
from __future__ import annotations

import ast
from pathlib import Path


def imports(text: str, names: set[str], pkg: str = "paperkit") -> set[str]:
    """Collect the engine-internal module names `text` imports, restricted to `names`.

    ⚑ BOTH SPELLINGS RECORD THE SAME EDGE, AND READING ONLY THE FLAT ONE ERASES THE DAG.
    `import bibparse` and `from paperkit import bibparse` are the same dependency written two
    ways.  This read only the first: an `ImportFrom` matched when `n.module` was itself an engine
    stem (the `from _fixture_model import X` form), so for `from paperkit import bibparse`
    `n.module` is `"paperkit"` — not a stem — and the imported name in `n.names` was never
    inspected.

    MEASURED 2026-08-31.  Converting `paperkit/bib.py`'s ONE import to the package spelling and
    regenerating dag.bzl DELETED the edge:

        -    "bib.py": ["bibparse.py"],

    The dependency still existed; only its spelling had changed.  dag.bzl is what Bazel stages
    each cell's .pyc closure from, so a bulk conversion would have under-staged cells one edge at
    a time — the ModuleNotFoundError-inside-a-sandbox class that components.bzl records costing
    four batch runs, and that Ξ·dag·script fixed for subprocess edges the day before.  Caught by
    `bnd-components`' freshness arm, which named the missing edge exactly.

    ⚑⚑ THREE FORMS, ONE EDGE.  `pkg` names the engine's own package so a subpackage import is
    resolved to the same STEM the flat form yields — callers key on stems (`edges()` maps them
    through `stem_index`), so returning a dotted name here would silently drop the edge instead.

        import bibparse                      -> bibparse      (flat)
        from paperkit import bibparse        -> bibparse      (package)
        from paperkit.tools import vfs       -> vfs           (subpackage)
        from _fixture_model import fx        -> _fixture_model (flat from-import, unchanged)
    """
    out: set[str] = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names if a.name in names}
        elif isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            if mod in names:                       # `from _fixture_model import fx`
                out.add(mod)
            elif mod == pkg or mod.startswith(pkg + "."):
                # `from paperkit[.sub] import X` — X is the module, not the package
                out |= {a.name for a in n.names if a.name in names}
    return out


def stem_index(paths: list[str]) -> dict[str, str]:
    """Map each module's bare stem to its engine-relative path, REFUSING an ambiguous stem.

    ⚑ THE REFUSAL IS THE POINT, AND IT FIRED ON ITS FIRST REAL INPUT.  `_STEM_TO_TARGET` built
    the same index as a dict comprehension, where a duplicate stem silently overwrites and the
    loser vanishes from the build graph.  Adding `paperkit/tests/__init__.py` (Φ·fixture·path)
    created exactly that collision — `__init__` naming two files — and this raised instead of
    picking one.  Under the old map the second `__init__.py` would have quietly displaced the
    engine's own in the target lookup.

    ⚑⚑ A PACKAGE MARKER IS EXEMPT, AND THAT IS A PROPERTY OF THE LANGUAGE, NOT A WAIVER.
    `__init__.py` is never the target of an `import __init__`; it is reached as the PACKAGE's
    name, one per directory by construction.  So it cannot be the ambiguous referent of any
    import edge, and excluding it narrows the index to exactly the names an edge can name.
    Every other duplicate stem stays a hard error.
    """
    by_stem: dict[str, list[str]] = {}
    for p in paths:
        stem = Path(p).stem
        if stem == "__init__":
            continue
        by_stem.setdefault(stem, []).append(p)
    dupes = {s: ms for s, ms in by_stem.items() if len(ms) > 1}
    if dupes:
        msg = (f"two engine modules share a bare stem, so an import naming it is ambiguous: "
               f"{dupes}.  The flat map silently kept one; this refuses instead.")
        raise ValueError(msg)
    return {s: ms[0] for s, ms in by_stem.items()}


def edges(eng: Path, paths: list[str]) -> list[tuple[str, str]]:
    """Return every engine-internal import edge as (importer path, imported PATH)."""
    index = stem_index(paths)
    out: list[tuple[str, str]] = []
    for p in paths:
        stem = Path(p).stem
        out.extend((p, index[imp])
                   for imp in sorted(imports((eng / p).read_text(), set(index)) - {stem}))
    return out


def cone(start: str, edges_by_mod: dict[str, list[str]]) -> set[str]:
    """Return the transitive import closure of one module, as engine-relative PATHS.

    ⚑ THE READER FOR `dag.bzl` LIVES WITH THE DERIVATION, BECAUSE THREE PRIVATE COPIES DID NOT.
    `IMPORTS` had no owning reader, so every consumer wrote its own walk and its own translation
    between the key namespace and the value namespace:

        paperkit/BUILD.bazel          `_STEM_TO_TARGET`, a stem→path dict comprehension
        boundaries_components         `by_stem`, the same map inverted
        boundaries_config._cone       `imports.get(m + ".py")`, appending the suffix per hop

    Ξ·dag·dotted deleted the first two by making both sides of an edge one namespace — and BROKE
    the third, which silently stopped after one hop (`"bib.py" + ".py"` matches nothing) and
    reported `gate.REGISTRY == 6` where the real cone hosts 12.  A guard that under-derives its
    expected set passes a registry MISSING six knobs, each of which would then be silently
    ignored at the CLI.  That is the shape the guard exists to catch, committed by the guard.

    ⚑⚑ SO THE WALK IS OWNED HERE.  `start` is an engine-relative path (`"gate.py"`,
    `"tests/_fixture_model.py"`) and so is every element of the result, including `start` itself.
    A consumer that wants stems takes them; a consumer that wants targets strips `.py`.  Nothing
    reconstructs a key from a value.
    """
    seen: set[str] = set()
    todo = [start]
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        todo.extend(edges_by_mod.get(m, []))
    return seen
