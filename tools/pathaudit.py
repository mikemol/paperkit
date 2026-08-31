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

# ⚑ Ζ·path·runtime — NOT EVERY SITE IS A BOOTSTRAP, AND A BULK SWEEP THAT ASSUMES SO BREAKS THREE
# THINGS.  Classified by reading each one (2026-08-31); they are three DIFFERENT kinds, which is
# why "the three runtime sites" was itself too coarse a description:
#
#   checkcache.py:188   RUNTIME, well-formed.  Loads an arbitrary witness by path and reads the
#                       sys.path THAT module established, to make a cache key's file set real
#                       rather than nominal.  Saves and restores sys.path in a `finally`.  ⚑ Its
#                       PURPOSE largely evaporates once Ζ·path·retire lands — with no mutations
#                       left to discover, the probe measures an empty set.
#   checkcache.py:248   MIXED, and unrestored.  Same dynamic-load shape, but the insert ALSO
#                       serves this module's own flat `import routes as R` — one statement doing a
#                       bootstrap and a runtime job at once — and there is no `finally`, so the
#                       process keeps the entry.  The bootstrap half retires; the runtime half
#                       needs the save/restore its sibling already has.
#   bibstruct.py:466    SEARCH, and dead here.  A borrowed tool locating a FOREIGN paperkit via
#                       $PAPERKIT / ~/github/paperkit — the search-instead-of-declare pattern
#                       pyproject.toml already names as the defect.  Inside paperkit the whole
#                       branch is unnecessary: `paperkit.bib` imports directly.
#
# A fourth kind is legitimate and now gone: `tools/shadowprobe.py` CONSTRUCTED a hostile sys.path
# as its experiment.  It was a one-shot instrument, its finding is recorded in paperkit/__init__.py
# where the claim it refuted lived, and it is deleted — a tool whose method is the practice being
# retired cannot stay in the tree doing it.
RUNTIME_SITES = {
    "paperkit/checkcache.py": (188, 248),
    "paperkit/tools/bibstruct.py": (466,),
}


def sites(tree: Path) -> list[tuple[str, int, str]]:
    """Find every module-level sys.path mutation as (file, line, the call source)."""
    out: list[tuple[str, int, str]] = []
    for p in sorted(tree.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        try:
            mod = ast.parse(p.read_text())
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(mod):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in ("insert", "append"):
                continue
            tgt = node.func.value
            if (isinstance(tgt, ast.Attribute) and tgt.attr == "path"
                    and isinstance(tgt.value, ast.Name) and tgt.value.id == "sys"):
                out.append((str(p.relative_to(ROOT)), node.lineno, ast.unparse(node)))
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
    found: list[tuple[str, int, str]] = []
    for t in TREES:
        d = ROOT / t
        if d.is_dir():
            found.extend(sites(d))

    by_file: dict[str, list[tuple[int, str]]] = {}
    for f, line, src in found:
        by_file.setdefault(f, []).append((line, src))

    runtime = 0
    for f in sorted(by_file):
        OUT.write(f"  {f}\n")
        for line, src in by_file[f]:
            known = line in RUNTIME_SITES.get(f, ())
            runtime += known
            OUT.write(f"      :{line}  {'[runtime] ' if known else ''}{src}\n")

    OUT.write(f"\n{len(by_file)} file(s) mutate sys.path · {len(found)} site(s)\n")
    OUT.write(f"  {runtime} classified RUNTIME (dynamic load / foreign-repo search) — see\n"
              f"  RUNTIME_SITES above; the other {len(found) - runtime} are bootstraps the\n"
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
