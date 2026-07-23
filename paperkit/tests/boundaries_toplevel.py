#!/usr/bin/env python3
"""Ζ·bnd·toplevel — a claim-WITNESS module's TOP LEVEL carries no engine-source reads.

The twice-bitten class (Μ·kernel·fixture·reads): a module-level convenience in a witness module
— a dead `import _fixture as fx`, a block of `X_SRC = (ENGINE / "x.py").read_text()` constants
four-fifths of which no witness used — becomes a staged input of EVERY grid row, so one engine
edit re-keys the whole grid regardless of what each witness actually inspects.  The sanctioned
form is the per-witness read (`_src("gate.py")` INSIDE the inspecting witness): closure.py's
per-witness walk scopes it to exactly the rows that inspect that source.

The OWNED set this guards: the modules closure.py analyzes — the EMERGE projects'
`[checks.claim]` scripts (only emerge projects generate grid rows, so only their witness
modules have this blast radius).  The project list derives from MODULE.bazel's
`emerge = True` tags (the owner, never a hand-list), and each such project's paper.toml
must be PRESENT — an under-staged project fails LOUD (add its reads token) instead of
silently narrowing the checked set.  The read semantics are DERIVED from the owner
(closure.py's `_reads` — a guard must not copy what it guards): a top-level statement
contributing any engine-module read root is the violation.

    python3 paperkit/tests/boundaries_toplevel.py     # exit 0 = every witness module clean
"""
from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
ROOT = ENGINE.parent
sys.path.insert(0, str(ROOT / "tools"))
from closure import _reads  # noqa: E402  (the owner of the read-root semantics)

from boundaries_components import _literal  # noqa: E402  (components.bzl literal reader)


def emerge_dirs():
    """The emerge projects' dirs, derived from MODULE.bazel's bib.project tags (the owner)."""
    out = []
    for line in (ROOT / "MODULE.bazel").read_text().splitlines():
        if "bib.project(" in line and "emerge = True" in line:
            m = re.search(r'project\s*=\s*"([^"]+)"', line)
            if m:
                out.append(m.group(1))
    return sorted(out)


def witness_modules():
    """{label: path} — the emerge projects' [checks.claim] scripts.  A missing paper.toml is a
    LOUD failure (the project is under-staged; add its reads token), never a silent skip."""
    out = {}
    for d in emerge_dirs():
        toml = ROOT / d / "paper.toml" if d != "." else ROOT / "paper.toml"
        if not toml.is_file():
            raise SystemExit(f"bnd-toplevel: emerge project {d!r}'s paper.toml is NOT STAGED — "
                             "add its token to the bnd-toplevel claim's reads")
        cmd = tomllib.loads(toml.read_text()).get("checks", {}).get("claim", {}).get("cmd", "")
        for tok in cmd.split():
            if tok.endswith(".py"):
                p = (toml.parent / tok).resolve()
                out[str(p.relative_to(ROOT))] = p
    return out


def toplevel_reads(text, names):
    """The engine-module read roots contributed by TOP-LEVEL statements (defs/classes excluded —
    a read inside a witness body is the sanctioned, per-witness-scoped form)."""
    found = set()
    for stmt in ast.parse(text).body:
        if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found |= _reads(stmt, names)
    return found


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    components = _literal(ENGINE / "components.bzl", "COMPONENTS")
    names = {f[:-len('.py')].rsplit("/", 1)[-1] for fs in components.values() for f in fs}
    mods = witness_modules()

    print("Ζ·bnd·toplevel — witness modules' top level is read-free\n")
    # Λ·cardinality — the derived set is PINNED to the named membership (anti-vacuity: a broken
    # derivation returning ∅ would otherwise pass everything).  A new emerge project with a
    # [checks.claim] extends this set — the guard fails LOUD until it does (fail-closed).
    check(f"witness modules derived from MODULE.bazel's emerge projects {emerge_dirs()}: "
          f"{', '.join(sorted(mods)) or 'none'}",
          set(mods) == {"checks/readme.py", "paper/checks/claims.py"})
    for rel, p in sorted(mods.items()):
        r = toplevel_reads(p.read_text(), names)
        check(f"{rel}: top-level engine-source reads == ∅"
              + (f" — found {sorted(r)}" if r else ""), not r)

    print("\n⟨P, F, δ⟩ minimum-delta pair (in-memory, never the tree)\n")
    f_text = 'from pathlib import Path\nSRC = (Path("x") / "gate.py").read_text()\n\ndef w():\n    pass\n'
    p_text = 'from pathlib import Path\n\ndef w():\n    src = (Path("x") / "gate.py").read_text()\n'
    ok = toplevel_reads(f_text, names) == {"gate"} and not toplevel_reads(p_text, names)
    fails.append("toplevel-delta") if not ok else None
    print(f"  {'ok ' if ok else 'XX '}a module-level source read is CAUGHT; the same read inside the witness is SANCTIONED")
    print("      P (in the witness):  src = …read_text() inside the def — scoped to its rows")
    print("      F (module level):    SRC = …read_text() at top level — a staged input of EVERY row")
    print("      δ (min delta): moving one read_text from the witness body to module level\n")

    if fails:
        print(f"TOPLEVEL: FAIL ({len(fails)} drifted)")
        return 1
    print(f"TOPLEVEL: PASS ({len(mods)} witness modules, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
