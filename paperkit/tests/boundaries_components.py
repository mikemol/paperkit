r"""Μ·kernel·bounds — the engine's COMPONENT boundary (bnd-components).

⟨partition⟩   COMPONENTS (paperkit/components.bzl, the ONE owner) is a TOTAL, DISJOINT
              partition of the engine's real .py tree — set-EQUALITY against the files on
              disk, never a count or a non-emptiness (Λ·cardinality).
⟨dag⟩         DEPS is acyclic, and EVERY real import edge respects it: a module may import
              within its component or from a component its component declares.  Edges come
              from paperkit/dag.bzl (Ξ·dag, the committed build DAG) — and that copy is
              first verified FRESH against the derivation's owner, so the discipline is never
              judged on a stale map.

⚑ Ξ·dag·dotted — AN EDGE'S VALUE IS A MODULE PATH, AND THAT DELETED A SECOND STEM MAP.  `violations`
used to carry its own `by_stem = {Path(f).stem: f for …}` to re-resolve a bare import name against
the partition's paths — a private copy of exactly the translation `paperkit/BUILD.bazel` was doing
with `_STEM_TO_TARGET`, in the guard that exists to catch duplicated structure.  With both sides of
an edge naming paths, the lookup IS the identity and the map is gone.

⚑⚑ AND THE REFERENCE ARM IS NOW AN IMPORT, NOT A SUBPROCESS.  `fresh_edges` shelled out to the
generator and parsed its stdout, so the guard and the generator agreed only if two output formats
stayed in step — and the stdout mode emitted STEMS while dag.bzl held paths, which is precisely the
disagreement that would have gone unnoticed.  Calling `dagderive.edges` makes the guard's reference
arm the SAME CODE the artifact is rendered from; a drift between them is now unrepresentable
rather than merely unlikely.

Stdlib plus the derivation module, deliberately: this guard imports NO engine module, so it adds
no edge to the DAG it guards.  Run from anywhere; paths derive from __file__.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

# ⚑ Ζ·engine·reach — THE BIB SPELLS BARE `python3`, WHICH HAS NO VIRTUALENV.  The editable
# install that makes `paperkit` and `tools` importable lives in `.venv`; the gate's interpreter is
# the mise one and sees neither.  Appending the repo root makes both importable as DIRECTORIES,
# needing no install — the same line `render/checks/matrix.py` carries, and the reason that
# witness passed the sweep `render/checks/bib.py` failed.
#
# ⚑⚑ APPEND, NOT INSERT.  This adds a namespace at the END of the search path rather than
# shadowing one; `insert(0, <own dir>)` is the retired form, and its harm is recorded one tree
# over where `render/checks/bib.py` shadowed `paperkit/bib.py` and reddened seven talk claims.
# It retires when the interpreter question is settled — does the bib name the venv, or is
# paperkit installed where bare python3 can see it? — and not before.
sys.path.append(str(Path(__file__).resolve().parents[2]))

from paperkit.tests._boundary import Suite
from tools import dagderive

ROOT = Path(__file__).resolve().parents[2]
ENG = ROOT / "paperkit"
SHOWN = 6


def _literal(path: Path, name: str) -> dict[str, list[str]]:
    """Read the pure-literal assignment `name = …` from a .bzl file (components.bzl / dag.bzl)."""
    for node in ast.parse(path.read_text()).body:
        # ⚑ `isinstance(t, ast.Name)` rather than `getattr(t, "id", None)` — a getattr on an AST
        # node returns Any and poisons the comparison; the narrow form says what a target IS.
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            val: object = ast.literal_eval(node.value)
            if not isinstance(val, dict):
                break
            out: dict[str, list[str]] = {}
            for k, v in val.items():
                if isinstance(v, list):
                    out[str(k)] = [str(x) for x in v]
            return out
    msg = f"bnd-components: no literal {name} in {path}"
    raise SystemExit(msg)


def engine_files() -> set[str]:
    """Collect every real .py file under the engine, engine-relative."""
    return {p.relative_to(ENG).as_posix()
            for p in ENG.rglob("*.py") if "__pycache__" not in p.parts}


def totality(components: dict[str, list[str]], files: set[str]) -> tuple[list[str], list[str]]:
    """Report what the partition misses and what it invents (both empty = total)."""
    covered = {f for fs in components.values() for f in fs}
    return sorted(files - covered), sorted(covered - files)


def duplicates(components: dict[str, list[str]]) -> list[str]:
    """List every file placed in more than one component."""
    seen: set[str] = set()
    dups: list[str] = []
    for fs in components.values():
        for f in fs:
            if f in seen:
                dups.append(f)
            else:
                seen.add(f)
    return dups


def cycle(deps: dict[str, list[str]]) -> str | None:
    """Name a component on a DEPS cycle, or None (Kahn)."""
    remaining = {c: set(ds) for c, ds in deps.items()}
    while remaining:
        free = [c for c, ds in remaining.items() if not ds]
        if not free:
            return min(remaining)
        for c in free:
            del remaining[c]
            for ds in remaining.values():
                ds.discard(c)
    return None


def violations(components: dict[str, list[str]], deps: dict[str, list[str]],
               edges: set[tuple[str, str]]) -> list[tuple[str, str, str, str]]:
    """Find import edges that cross the architecture: (module, imported, its comp, needed comp).

    ⚑ BOTH SIDES ARE PATHS, SO THE PARTITION IS INDEXED DIRECTLY.  This carried a private
    `by_stem` map to translate a bare import name into a partition path — the same translation
    BUILD.bazel did, duplicated inside the guard whose job is to catch duplicated structure.
    """
    comp_of = {f: c for c, fs in components.items() for f in fs}
    out: list[tuple[str, str, str, str]] = []
    for mod, dst in sorted(edges):
        if mod not in comp_of or dst not in comp_of:
            out.append((mod, dst, "?", "?"))
            continue
        a, b = comp_of[mod], comp_of[dst]
        if a != b and b not in deps.get(a, []):
            out.append((mod, dst, a, b))
    return out


def main() -> int:
    """Assert the partition is total and disjoint, and that every import edge respects DEPS."""
    # ⚑ Ζ·suite·count — the SHARED recorder owns the summary, so this suite has no count to type.
    s = Suite("COMPONENTS", "Μ·bnd-components — the engine's component boundary")

    components = _literal(ENG / "components.bzl", "COMPONENTS")
    deps = _literal(ENG / "components.bzl", "DEPS")
    imports = _literal(ENG / "dag.bzl", "IMPORTS")
    files = engine_files()
    committed = {(m, dst) for m, dsts in imports.items() for dst in dsts}

    s.section("partition")
    missing, invented = totality(components, files)
    s.check(f"the partition is TOTAL over the real tree ({len(files)} files)",
            not missing and not invented)
    if missing or invented:
        sys.stdout.write(f"      missing={missing} invented={invented}\n")
    s.check("the partition is DISJOINT (no file in two components)", not duplicates(components))
    s.check("DEPS names exactly the components", set(deps) == set(components))

    s.section("dag")
    s.check("DEPS is acyclic", cycle(deps) is None)
    live = set(dagderive.edges(ENG, sorted(files)))
    s.check(f"dag.bzl IMPORTS is FRESH against tools/dagderive.py ({len(live)} edges)",
            committed == live)
    if committed != live:
        sys.stdout.write(f"      committed-only={sorted(committed - live)[:SHOWN]}\n")
        sys.stdout.write(f"      live-only={sorted(live - committed)[:SHOWN]}\n")
        # Ζ·dag·regen — name the REPAIR, not just the breach.  dag.bzl says "REGENERATE (never
        # hand-edit)" and for a long time nothing could: the generator emitted edges to stdout and
        # had no writer, so the only way past this red was to hand-edit the file its own header
        # forbids hand-editing.  `--write` closes that, and saying so here is the difference
        # between a check that reports a fact and one a reader can act on.
        sys.stdout.write("      repair: python3 tools/dagbzl.py --write\n")
    bad = violations(components, deps, committed)
    s.check("every import edge respects the component DAG", not bad)
    for mod, dst, a, b in bad[:SHOWN]:
        sys.stdout.write(f"      {mod} ({a}) imports {dst} ({b}) — not in DEPS[{a}]\n")

    f_total = {c: list(fs) for c, fs in components.items()}
    f_total["gate"] = []                                    # δ: drop one file from the partition
    f_dup = {c: list(fs) for c, fs in components.items()}
    f_dup["kernel"] = [*f_dup["kernel"], "gate.py"]         # δ: one file in two components
    f_edge = committed | {("config.py", "grader.py")}       # δ: one edge against the DAG's grain
    s.delta("dropping a file, double-listing it, and one upward edge are each CAUGHT",
            totality(components, files) == ([], []) and not violations(components, deps,
                                                                       committed),
            (totality(f_total, files)[0] == ["gate.py"]
             and duplicates(f_dup) == ["gate.py"]
             and violations(components, deps, f_edge)
             == [("config.py", "grader.py", "kernel", "delta")]),
            ("partition total+disjoint, every edge inside DEPS",
             ("gate.py unplaced → totality; gate.py twice → disjointness; "
              "config.py→grader.py → an edge kernel may not take"),
             "one file, one duplicate, one edge"))
    return s.finish()


if __name__ == "__main__":
    raise SystemExit(main())
