r"""Ζ·path·retire — every `sys.path` mutation in the tree, and whether it is still load-bearing.

⚑ THE OPERATOR HAS INSISTED ON THIS REPEATEDLY, AND THE TREE KEEPS GROWING NEW ONES.  *"stop
playing stupid path games and let the pyproject.toml be explicit about where to find things"*,
then *"this is why we have venvs"*, then — after `sortaudit.py` was built to guard the fallout —
*"This is why I KEEP INSISTING WE STOP MODIFYING sys.path."*

The mutation is not a style preference.  It causes, measured in this repo:

  * ORDER-DEPENDENT IMPORTS.  A module reached only after an insert must be imported after it, so
    `ruff --select I001 --fix` (alphabetical, order-blind) moved a load-bearing import above its
    bootstrap FIVE times.  `tools/sortaudit.py` exists solely to find that, and it is scaffolding
    for a defect that should not exist — remove the mutation and I001 becomes as mechanical as
    E501.
  * UNCHECKABLE EDGES.  A flat `import x` behind an insert is unresolvable to mypy, so `x` types
    as Any and every derived expression inherits it — `tools/flatorder.py` measures 66 files and
    2,497 findings downstream of exactly this.
  * AMBIGUOUS NAMES.  Two directories named `tools` (repo root and paperkit/tools) resolve by
    whichever bound first; measured, a probe reported 29/29 green while its consumer died on the
    same name.

⚑⚑ AND THE DECLARATION ALREADY EXISTS.  `pyproject.toml` says `packages = ["paperkit", "tools"]`,
so under the project venv BOTH are importable with no mutation at all.  The inserts survive for
the bare-`python3` route the bibs used to spell — which the venv answers.  This tool reports which
files still carry one so the retirement is a worked list rather than a grep in a turn.

    python3 tools/pathaudit.py             # every site, grouped by what it reaches for
    python3 tools/pathaudit.py --probe     # and whether the target imports WITHOUT the mutation
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = sys.stdout
TREES = ("paperkit", "tools", "checks", "render", "config", "paper", "library", "demo", "talk")
PROBES = ("paperkit", "tools", "paperkit.bib", "paperkit.tests", "tools.closure")

# ⚑ Ζ·path·runtime — NOT EVERY SITE IS A BOOTSTRAP, AND A BULK SWEEP THAT ASSUMES SO BREAKS THINGS.
# The kinds, classified by reading each one (2026-08-31, restated 2026-10-10):
#
#   a BOOTSTRAP is a MODULE-LEVEL mutation: it runs at import so the file's own flat imports
#   resolve.  The package declaration covers it, and it retires.
#   a RUNTIME site is a mutation INSIDE A FUNCTION: it exists to load or locate something at a call
#   (checkcache's by-path load of an arbitrary witness, which saves and restores sys.path in a
#   `finally`; bibstruct's search for a foreign paperkit).  The two are told apart STRUCTURALLY, by
#   whether the call sits inside a def, never by a table of line numbers: the table this replaced
#   named lines 188/248/466, the files were edited, and the audit reported "0 runtime" while the
#   sites it meant had moved to 303 and 477 — a classification keyed on position rots on the first
#   edit above it.
#
# A kind that is legitimate and now gone: `tools/shadowprobe.py` CONSTRUCTED a hostile sys.path
# as its experiment.  It was a one-shot instrument, its finding is recorded in
# paperkit/__init__.py where the claim it refuted lived, and it is deleted — a tool whose method
# is the practice being retired cannot stay in the tree doing it.


def _function_lines(mod: ast.Module) -> set[int]:
    """Return every line number that sits inside a function body."""
    lines: set[int] = set()
    for node in ast.walk(mod):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return lines


def sites(tree: Path) -> list[tuple[str, int, str, bool]]:
    """Find every sys.path mutation as (file, line, the call source, inside a function)."""
    out: list[tuple[str, int, str, bool]] = []
    for p in sorted(tree.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        try:
            mod = ast.parse(p.read_text())
        except (OSError, SyntaxError):
            continue
        in_function = _function_lines(mod)
        for node in ast.walk(mod):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in ("insert", "append"):
                continue
            tgt = node.func.value
            if (isinstance(tgt, ast.Attribute) and tgt.attr == "path"
                    and isinstance(tgt.value, ast.Name) and tgt.value.id == "sys"):
                out.append((str(p.relative_to(ROOT)), node.lineno, ast.unparse(node),
                            node.lineno in in_function))
    return out


def importable(name: str) -> tuple[bool, str]:
    """Report whether `name` imports under the project venv with NO path mutation, and why not.

    ⚑ RUN FROM A DIRECTORY THAT IS NOT THE REPO ROOT, deliberately.  `packages` in pyproject
    declares what the editable install exposes, but a package also resolves by CWD — so a probe
    run at the root cannot tell a real declaration from an accident of where it stood.  Same
    self-inclusion error as Λ·probe·self, one layer over.

    ⚑⚑ AND THE REASON IS RETURNED, NOT JUST THE VERDICT.  A bare yes/no invites the reader to
    re-derive the cause in a shell, which is the judgement-in-the-turn this repo's guards refuse.
    The distinction that matters here is between "the PACKAGE is unreachable" (a declaration
    problem) and "the package is fine but the MODULE fails at import" (a flat-import problem
    inside it) — those have different owners and different fixes, and a boolean conflates them.
    """
    exe = str(ROOT / ".venv" / "bin" / "python3")
    r = subprocess.run([exe, "-c", f"import {name}"],  # noqa: S603
                       cwd=str(ROOT.parent), capture_output=True, text=True, check=False)
    if r.returncode == 0:
        return (True, "")
    tail = [ln for ln in r.stderr.splitlines() if ln.strip()]
    return (False, tail[-1][:88] if tail else "")


def main(argv: list[str]) -> int:
    """Report every sys.path mutation, and optionally whether its target needs one."""
    found: list[tuple[str, int, str, bool]] = []
    for t in TREES:
        d = ROOT / t
        if d.is_dir():
            found.extend(sites(d))

    by_file: dict[str, list[tuple[int, str, bool]]] = {}
    for f, line, src, in_function in found:
        by_file.setdefault(f, []).append((line, src, in_function))

    runtime = 0
    for f in sorted(by_file):
        OUT.write(f"  {f}\n")
        for line, src, in_function in by_file[f]:
            runtime += in_function
            OUT.write(f"      :{line}  {'[runtime] ' if in_function else ''}{src}\n")

    OUT.write(f"\n{len(by_file)} file(s) mutate sys.path · {len(found)} site(s)\n")
    OUT.write(f"  {runtime} classified RUNTIME (inside a function: a dynamic load or a search at\n"
              f"  call time); the other {len(found) - runtime} are module-level bootstraps the\n"
              "  package declaration already covers.\n")

    if "--probe" in argv:
        OUT.write("\nreachable WITHOUT any mutation (venv, cwd outside the repo):\n")
        for name in PROBES:
            ok, why = importable(name)
            OUT.write(f"    {name:<20} {'yes' if ok else 'NO ':<4}{why}\n")
        OUT.write("  ⚑ a `yes` is a mutation with nothing left to do — pyproject already declares\n"
                  "    the package.  A `NO` naming a MISSING MODULE is a flat import inside an\n"
                  "    otherwise-reachable package: the package resolves, the module's own\n"
                  "    `import x` does not, which is Ζ·flat rather than a declaration gap.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
