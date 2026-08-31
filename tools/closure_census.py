r"""Ζ·closure·census — which witnesses reach the engine through a SUBPROCESS the closure cannot see.

⚑ THE QUESTION IS NARROWER THAN "CAN closure.py SEE SUBPROCESSES", AND ASKING IT WIDE WOULD HAVE
BOUGHT THE WRONG FIX.  `closure.py` ALREADY carries a subprocess edge (Ξ·dag·concept, its lines
236-263), added after the identical failure: *"an AST import-walk cannot see across that boundary,
so the caller staged a cone sized for its OWN imports and the callee's first import died — nine
modules short"*.  It follows `concept:KEY` constants into the resolved witness's cone,
transitively.

What it does NOT follow is a witness that shells out to a GENERATOR SCRIPT — `checks/gen_*.py`,
run as a subprocess, which does its own `sys.path.insert` + flat `import bib`.  That is how
edge-formulas came to stage ONE root (`_fixture_model.py`) where its bib-touching siblings stage
nine, and why its baseline died with `ModuleNotFoundError: No module named 'bibparse'` the moment
`bib.py` grew a dependency.

⚑⚑ SO THE CENSUS COUNTS THE POPULATION OF THAT SPECIFIC GAP, and it counts it by asking the
OWNER — `closure.py` itself — what roots each claim gets, rather than by grepping for `subprocess`.
A witness is FLAGGED when it names a sibling script that imports engine modules the claim's own
declared closure does not contain.  That difference is the under-declaration, in modules, and it is
exactly what a build stages too few of.

    python3 tools/closure_census.py                      # every project with a checks/ dir
    python3 tools/closure_census.py paper                # one project
"""
from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from tools import dagderive, dagnames

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "paperkit"
OUT = sys.stdout

DISPATCH = ("CLAIMS", "CONCEPTS", "WITNESSES")
FIELDS = 2


@dataclass
class Gap:
    """One witness whose subprocess-reached script needs engine modules its closure omits."""

    claim: str
    script: str
    missing: list[str] = field(default_factory=list)


def engine_modules() -> list[str]:
    """List the engine .py paths closure.py resolves names against, from the partition."""
    comps = dagnames.literal(ENGINE / "components.bzl", "COMPONENTS")
    return sorted(f"paperkit/{f}" for fs in comps.values() for f in fs)


def declared(check: str, mods: list[str]) -> dict[str, set[str]]:
    """Ask closure.py for each claim's declared IMPORT roots, as module stems.

    ⚑ THE OWNER IS ASKED, NOT REIMPLEMENTED.  A census that re-derived the roots would be a second
    body of closure.py's rules and would drift from them — and a consumer re-deriving what an owner
    already computes is the very defect class being counted here.
    """
    r = subprocess.run(  # noqa: S603
        [sys.executable or "python3", str(ROOT / "tools" / "closure.py"),
         "--check", check, *mods],
        cwd=ROOT, capture_output=True, text=True, check=False,
        env={"PYTHONPATH": str(ROOT / "tools"), "PATH": "/usr/bin:/bin"},
    )
    out: dict[str, set[str]] = {}
    for ln in r.stdout.splitlines():
        parts = ln.split("\t")
        if len(parts) < FIELDS or ":" in parts[1]:   # skip read:/file±/content± rows — imports only
            continue
        out.setdefault(parts[0], set()).add(Path(parts[1]).stem)
    return out


def dispatch_table(tree: ast.Module) -> dict[str, str]:
    """Read the witness module's claim-key → function-name registry."""
    out: dict[str, str] = {}
    for n in tree.body:
        if not (isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict)):
            continue
        if not any(isinstance(t, ast.Name) and t.id in DISPATCH for t in n.targets):
            continue
        for k, v in zip(n.value.keys, n.value.values, strict=False):
            if isinstance(k, ast.Constant) and isinstance(v, ast.Name):
                out[str(k.value)] = v.id
    return out


def scripts_named(fn: ast.AST, sibling: set[str]) -> set[str]:
    """Collect sibling script basenames a witness names as a string constant."""
    return {n.value.rsplit("/", 1)[-1] for n in ast.walk(fn)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value.rsplit("/", 1)[-1] in sibling}


def script_imports(path: Path, names: set[str]) -> set[str]:
    """Collect engine module stems a script imports at module level — its own cone seed."""
    out: set[str] = set()
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return out
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names if a.name in names}
        elif isinstance(n, ast.ImportFrom) and n.module in names:
            out.add(str(n.module))
    return out


def cone(seeds: set[str], mods: list[str]) -> set[str]:
    """Expand `seeds` to the transitive engine cone the build would have to stage."""
    paths = [m[len("paperkit/"):] for m in mods]
    edges: dict[str, list[str]] = {}
    for m, i in dagderive.edges(ENGINE, paths):
        edges.setdefault(m, []).append(i)
    by_stem = {Path(p).stem: p for p in paths}
    seen: set[str] = set()
    for s in seeds:
        if s in by_stem:
            seen |= {Path(p).stem for p in dagderive.cone(by_stem[s], edges)}
    return seen


def witness_modules(project: Path) -> list[Path]:
    """List the project's witness modules — EVERY `checks/*.py` a bib `cmd:` actually names.

    ⚑ I GUESSED THIS THREE TIMES AND WAS WRONG THREE TIMES, WHILE AN OWNER HELD THE ANSWER.

      * A NAME LIST (`claims.py`, then `concepts.py`) skipped `config/`, whose witness is
        `registry.py`, and printed `0 under-declared` for it: a filter reported as a population
        (Λ·declared-partial), clearing a project without opening a file in it.
      * SCRAPING THE BIB for `cmd:python3 checks/<w>.py` then skipped `paper/` — where the defect
        actually lives — because `paper` uses the `claim:KEY` verb and never names its script.
      * A NAME LIST AS FALLBACK for that verb then skipped the ROOT project, whose witness is
        `readme.py`: a THIRD spelling.

    The mapping is DECLARED, in each project's `paper.toml`:

        [checks.claim]
        cmd = "python3 checks/readme.py {target}"

    So it is read from there — place-by-ownership — plus whatever a bib `cmd:` names directly.
    A project inventing a fourth spelling is covered by construction rather than by editing a
    list here, which is what the three misses above all were.
    """
    checks = project / "checks"
    if not checks.is_dir():
        return []
    named: set[str] = set()
    for bib in sorted(project.glob("*.bib")):
        for tok in bib.read_text().split():
            leaf = tok.strip("{},").rsplit("/", 1)[-1]
            if leaf.endswith(".py") and (checks / leaf).exists():
                named.add(leaf)
    toml = project / "paper.toml"
    if toml.exists():                       # the declared verb→script templates
        for tok in toml.read_text().split():
            leaf = tok.strip("\"'{},").rsplit("/", 1)[-1]
            if leaf.endswith(".py") and (checks / leaf).exists():
                named.add(leaf)
    return sorted(checks / n for n in named)


def audit_witness(witness: Path, project: Path, mods: list[str]) -> list[Gap]:
    """Report each claim in one witness module naming a script it does not stage the cone for."""
    checks = witness.parent
    sibling = {p.name for p in checks.glob("*.py") if p.name not in {witness.name, "__init__.py"}}
    if not sibling:
        return []

    names = {Path(m).stem for m in mods}
    # ⚑ A WITNESS OUTSIDE THE REPO IS A LEGITIMATE INPUT, AND `relative_to` RAISED ON IT.  The
    # boundary suite builds a SYNTHETIC project in a tmpdir to prove this census can actually
    # flag a gap it has never seen — and the assumption that every witness lives under ROOT made
    # the tool untestable on a fixture, which is precisely how an alarm stays uncalibrated
    # (Λ·instrument-vs-gate).  closure.py takes an absolute --check, so pass one when the witness
    # is out of tree; --relpath still carries the repo-relative form for parents[N] resolution.
    rel = str(witness.relative_to(ROOT)) if witness.is_relative_to(ROOT) else str(witness)
    have = declared(rel, mods)
    tree = ast.parse(witness.read_text())
    funcs = {f.name: f for f in tree.body if isinstance(f, ast.FunctionDef)}

    gaps: list[Gap] = []
    for key, fname in sorted(dispatch_table(tree).items()):
        fn = funcs.get(fname)
        if fn is None:
            continue
        for script in sorted(scripts_named(fn, sibling)):
            missing = sorted(cone(script_imports(checks / script, names), mods)
                             - have.get(key, set()))
            if missing:
                gaps.append(Gap(claim=key, script=f"{project.name}/checks/{script}",
                                missing=missing))
    return gaps


def audit(project: Path, mods: list[str]) -> list[Gap]:
    """Report every under-declared witness in a project, across all its witness modules."""
    return [g for w in witness_modules(project) for g in audit_witness(w, project, mods)]


def main(argv: list[str]) -> int:
    """Report every claim whose subprocess-reached script out-runs its declared closure."""
    mods = engine_modules()
    wanted = set(argv)
    # ⚑ THE ROOT PROJECT IS ONE OF THEM, AND `*/checks` DOES NOT MATCH IT.  paperkit's own root
    # project keeps its witnesses at `checks/`, not `<name>/checks/`, so a glob over subdirectories
    # examined 33 modules and silently omitted `checks/gen_fields.py` — which carries the SAME
    # `sys.path.insert` + flat `import bib` shape as the generator that broke the build.  Third
    # instance of one defect in this tool: a population defined by a pattern that cannot express
    # the whole population (Λ·declared-partial).
    projects = sorted({p.parent for p in ROOT.glob("*/checks") if p.is_dir()}
                      | ({ROOT} if (ROOT / "checks").is_dir() else set()))

    gaps: list[Gap] = []
    examined: list[str] = []
    skipped: list[str] = []
    for proj in projects:
        label = "(root)" if proj == ROOT else proj.name
        if wanted and label not in wanted and proj.name not in wanted:
            continue
        mods_seen = witness_modules(proj)
        if not mods_seen:
            skipped.append(label)
            continue
        examined.extend(f"{label}/checks/{w.name}" for w in mods_seen)
        gaps.extend(audit(proj, mods))

    for g in gaps:
        OUT.write(f"  ⚑ {g.claim}\n")
        OUT.write(f"      shells out to : {g.script}\n")
        OUT.write(f"      NOT staged    : {', '.join(g.missing)}\n")

    # ⚑ SAY WHAT WAS EXAMINED, NOT ONLY WHAT WAS FOUND.  A count of findings over an unstated
    # population is the shape that reported config as `0 under-declared` while never opening it.
    OUT.write(f"\nexamined {len(examined)} witness module(s):\n")
    for e in sorted(examined):
        OUT.write(f"    {e}\n")
    if skipped:
        OUT.write(f"  ⚑ NO bib-named witness found in: {', '.join(sorted(skipped))}\n")
    OUT.write(f"\n{len(gaps)} under-declared witness(es)\n")
    if gaps:
        OUT.write("  ⚑ each stages a cone too small for the script it runs —\n"
                  "    a ModuleNotFoundError waiting for a module to gain a dependency.\n")
    return 1 if gaps else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
