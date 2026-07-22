#!/usr/bin/env python3
"""Μ·kernel·bounds — the engine's COMPONENT boundary (bnd-components).

⟨partition⟩   COMPONENTS (paperkit/components.bzl, the ONE owner) is a TOTAL, DISJOINT
              partition of the engine's real .py tree — set-EQUALITY against the files on
              disk, never a count or a non-emptiness (Λ·cardinality).
⟨dag⟩         DEPS is acyclic, and EVERY real import edge respects it: a module may import
              within its component or from a component its component declares.  Edges come
              from paperkit/dag.bzl (Ξ·dag, the committed build DAG) — and that copy is
              first verified FRESH against tools/imports.py, the tool that owns the
              derivation, so the discipline is never judged on a stale map.

Stdlib only, deliberately: this guard imports NO engine module, so it adds no edge to the
DAG it guards.  Run from anywhere; paths derive from __file__.
"""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENG = ROOT / "paperkit"


def _literal(path, name):
    """The pure-literal assignment `name = …` in a .bzl file (components.bzl / dag.bzl)."""
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit(f"bnd-components: no literal {name} in {path}")


def engine_files():
    return {p.relative_to(ENG).as_posix() for p in ENG.rglob("*.py") if "__pycache__" not in p.parts}


def totality(components, files):
    """What the partition misses and what it invents (both empty = total)."""
    covered = {f for fs in components.values() for f in fs}
    return sorted(files - covered), sorted(covered - files)


def duplicates(components):
    seen, dups = set(), []
    for fs in components.values():
        for f in fs:
            if f in seen:
                dups.append(f)
            else:
                seen.add(f)
    return dups


def cycle(deps):
    """A component on a DEPS cycle, or None (Kahn)."""
    remaining = {c: set(ds) for c, ds in deps.items()}
    while remaining:
        free = [c for c, ds in remaining.items() if not ds]
        if not free:
            return sorted(remaining)[0]
        for c in free:
            del remaining[c]
            for ds in remaining.values():
                ds.discard(c)
    return None


def violations(components, deps, edges):
    """Import edges that cross the architecture: (module, imported, its comp, needed comp)."""
    comp_of = {f: c for c, fs in components.items() for f in fs}
    by_stem = {Path(f).stem: f for fs in components.values() for f in fs}
    out = []
    for mod, stem in edges:
        dst = by_stem.get(stem)
        if mod not in comp_of or dst is None:
            out.append((mod, stem, "?", "?"))
            continue
        a, b = comp_of[mod], comp_of[dst]
        if a != b and b not in deps.get(a, []):
            out.append((mod, stem, a, b))
    return out


def fresh_edges(files):
    """The edges tools/imports.py (the owner) derives NOW — the reference arm for dag.bzl."""
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "imports.py")] + sorted(files),
                       cwd=ENG, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"bnd-components: imports.py failed — {r.stderr.strip()[-200:]}")
    return {tuple(line.split("\t")) for line in r.stdout.splitlines() if line.strip()}


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    components = _literal(ENG / "components.bzl", "COMPONENTS")
    deps = _literal(ENG / "components.bzl", "DEPS")
    imports = _literal(ENG / "dag.bzl", "IMPORTS")
    files = engine_files()
    committed = {(m, s) for m, ss in imports.items() for s in ss}

    print("Μ·bnd-components — the engine's component boundary\n")
    print("⟨partition⟩\n")
    missing, invented = totality(components, files)
    check(f"the partition is TOTAL over the real tree ({len(files)} files)", not missing and not invented)
    if missing or invented:
        print(f"      missing={missing} invented={invented}")
    check("the partition is DISJOINT (no file in two components)", not duplicates(components))
    check("DEPS names exactly the components", set(deps) == set(components))

    print("\n⟨dag⟩\n")
    check("DEPS is acyclic", cycle(deps) is None)
    live = fresh_edges(files)
    check(f"dag.bzl IMPORTS is FRESH against tools/imports.py ({len(live)} edges)", committed == live)
    if committed != live:
        print(f"      committed-only={sorted(committed - live)} live-only={sorted(live - committed)}")
    bad = violations(components, deps, committed)
    check("every import edge respects the component DAG", not bad)
    for mod, stem, a, b in bad[:6]:
        print(f"      {mod} ({a}) imports {stem} ({b}) — not in DEPS[{a}]")

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    f_total = {c: list(fs) for c, fs in components.items()}
    f_total["gate"] = []                                    # δ: drop one file from the partition
    f_dup = {c: list(fs) for c, fs in components.items()}
    f_dup["kernel"] = f_dup["kernel"] + ["gate.py"]         # δ: one file in two components
    f_edge = committed | {("config.py", "grader")}          # δ: one edge against the DAG's grain
    ok = (totality(components, files) == ([], [])
          and totality(f_total, files)[0] == ["gate.py"]
          and duplicates(f_dup) == ["gate.py"]
          and not violations(components, deps, committed)
          and violations(components, deps, f_edge) == [("config.py", "grader", "kernel", "delta")])
    fails.append("bounds-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}dropping a file, double-listing it, and one upward edge are each CAUGHT")
    print("      P (intact):  partition total+disjoint, every edge inside DEPS")
    print("      F (mutated): gate.py unplaced → totality; gate.py twice → disjointness;")
    print("                   config.py→grader → an edge kernel may not take")

    if fails:
        print(f"\nCOMPONENTS: FAIL ({len(fails)} boundary breaches)")
        return 1
    print(f"\nCOMPONENTS: PASS ({len(components)} components, {len(files)} files, {len(committed)} edges, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
