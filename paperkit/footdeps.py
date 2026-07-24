#!/usr/bin/env python3
"""Ζ·foot — project the per-claim dependency manifest (footprints.json) FROM the live Φ·footprints.

For each project's each checked claim, strace the check (scope = repo root) to see which files it
READS, and reduce them to the set of DEP TOKENS — the top-level units a Bazel target depends on:
`paperkit` (the engine), a sibling project dir, or `.` (a root file: .githooks, a root bib/rubric).
The check's OWN project + the engine are always needed (gate.py loads the bib; the witness lives in
one of them), so the manifest records only what is read BEYOND them — i.e. the cross-package deps
that `extra_data` used to declare by hand.  tools/bibtex.bzl reads this at fetch and emits each
check target's `data` from it; no strace at fetch (fast, deterministic).

    python3 paperkit/footdeps.py [PROJECT...]      # write footprints.json (default: the wired set)
    python3 paperkit/footdeps.py --check [PROJECT...]   # verify it is fresh, exit 1 if stale

A degraded footprint (strace absent/can't attach → None) records the sentinel ["*"] = "all
projects" (the repo rule over-declares), never a silent under-declaration.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bib  # noqa: E402  (the parser/data-model leaf — footdeps needs only the bib, not the projector)
import resolver  # noqa: E402

WIRED = ["boundaries", "config", "paper", "setup", "."]   # projects with per-claim Bazel graphs


_FILEGROUP_RE = re.compile(r'filegroup\(\s*name\s*=\s*"files"\s*,\s*srcs\s*=\s*\[(.*?)\]', re.S)


def _root_files(repo_root: Path) -> set:
    """Ξ·dag·reads — the repo-relative paths the root //:files filegroup STAGES (the `.` reads
    token).  DERIVED from BUILD.bazel (the owner, never a hardcoded copy) because //:files curates
    a CROSS-DIRECTORY set — it lists //report:gen.py, //tools:*.py, //paperkit:components.bzl, … —
    so which reads token stages a file is decided by its OWNING FILEGROUP, not its directory.  The
    project :files filegroups are own-directory-only, so //:files is the only cross-dir case."""
    m = _FILEGROUP_RE.search((repo_root / "BUILD.bazel").read_text())
    if not m:
        return set()
    return {(lit[2:].replace(":", "/", 1) if lit.startswith("//") else lit)
            for lit in re.findall(r'"([^"]+)"', m.group(1))}


def _covering(f: str, projects: set, root_files: set) -> set:
    """Ξ·dag·reads — the reads tokens that STAGE file f; ANY ONE suffices.  A file can be staged by
    SEVERAL sources, so this is a SET, not a single token: report/gen.py is in BOTH //report:files
    (`report`) and //:files (`.`), so a check declaring EITHER covers it."""
    top = f.split("/")[0]
    if top == "paperkit":
        # engine-adjacent — the .py modules AND the .bzl the build reads (components.bzl, dag.bzl),
        # incidentally opened by every engine-importing check; excluded like the engine (a genuine
        # need is caught by //:hook's own file-not-found on the unstaged file).
        return {"paperkit"}
    s = set()
    if top in projects:
        s.add(top)                       # under a project dir → coverable by @@//<proj>:files
    if f in root_files:
        s.add(".")                       # cross-listed in //:files → coverable by the `.` token
    return s or {"."}                    # a bare root file (.githooks/, a root bib/rubric/asset)


def _imported(project_dir: Path, repo_root: Path) -> set:
    """Repo-relative paths of the warrant bibs COMPOSED into a project from OTHER packages (root
    imports //paper:adequacy_pitch.bib).  Staged by the bib COMPOSITION, not a reads token, so a
    footprint read of one is already covered — derived from the same load_config the build uses."""
    out = set()
    for b in bib.load_config(project_dir)["bibs"]:
        try:
            out.add(str(Path(b).resolve().relative_to(repo_root)))
        except ValueError:               # a bib outside the repo — ignore
            continue
    return out


def _missing(fp: list, declared: set, projects: set, root_files: set, name: str, imported: set) -> list:
    """The reads tokens a check is MISSING: for each footprint file NOT already staged — by its own
    project, the engine, an imported warrant bib, or a DECLARED token's filegroup — the tokens that
    WOULD stage it (any one suffices).  [] iff every read is staged (the audit's soundness core)."""
    have = set(declared) | {name, "paperkit"}
    miss = set()
    for f in fp:
        if f in imported:
            continue                     # staged via warrant-imports composition, not reads=
        cov = _covering(f, projects, root_files)
        if not (cov & have):
            miss |= cov                  # any of these declared would cover f
    return sorted(miss)


def _engine(reads: list) -> list:
    """Ζ·mutant — the ENGINE MODULES a check reads (the def-mutable surface for footprints.json):
    paperkit/*.py.  sensitivity ⊆ footprint (Φ), so a claim's def-sweep need mutate only the
    def-sites in THESE modules — the scope tools/bibtex.bzl reads at fetch to bound the pk_mutate /
    pk_eval fanout.  CRITICAL for soundness: a check's subprocess imports modules from the BYTECODE
    cache, so strace sees `paperkit/__pycache__/bib.cpython-NN.pyc`, not `paperkit/bib.py` — map each
    such .pyc back to its source .py, else the scope silently OMITS a sensitive module (bib/config for
    `deterministic`) and sens ⊄ footprint."""
    mods = set()
    for r in reads:
        if not r.startswith("paperkit/"):
            continue
        p = Path(r)
        if p.suffix == ".py":
            mods.add(r)
        elif p.suffix == ".pyc" and p.parent.name == "__pycache__":
            # paperkit/[sub/]__pycache__/x.cpython-NN.pyc → paperkit/[sub/]x.py
            mods.add(str(p.parent.parent / (p.name.split(".")[0] + ".py")))
    return sorted(mods)


def build(repo_root: Path, names: list) -> dict:
    manifest = {}
    for name in names:
        pdir = repo_root if name == "." else repo_root / name
        raw = tomllib.loads((pdir / "paper.toml").read_text())
        custom = raw.get("checks", {})
        cfg = bib.load_config(pdir)
        F = {}
        for b in cfg["bibs"]:
            F.update(bib.parse(b))
        # A BOUNDARY-CROSSING check (resolver.CROSSING — result:, concept:) is an EDGE, not a leaf:
        # its footprint is never used, and stracing it would rerun a whole sibling gate or library
        # witness.  Skip by asking the VERB (crosses=True), never by re-listing the verbs here.
        # strace is I/O-bound, so trace the rest CONCURRENTLY.
        items = [(k, f["check"]) for k, f in sorted(F.items())
                 if f.get("check") and not f["check"].startswith(resolver.CROSSING)]

        def deps(chk):
            fp = resolver.footprint(chk, pdir, custom, scope=repo_root)
            return ["*"] if fp is None else fp

        with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4))) as ex:
            graded = list(ex.map(lambda kc: deps(kc[1]), items))
        manifest[name] = {k: d for (k, _), d in zip(items, graded)}
    return manifest


def _declared(pdir: Path) -> dict:
    """{claim: set(declared read tokens)} from each claim's `reads` field (the declare+audit
    source).  Routed through the canonical parser (paperkit.bib, via bib.parse) — `reads` is now
    a first-class field there, so no separate line scanner / no disagreement with the build."""
    F = {}
    for b in bib.load_config(pdir)["bibs"]:
        F.update(bib.parse(b))
    return {k: set(f.get("reads", [])) for k, f in F.items()}


def audit(repo_root: Path, names: list) -> list:
    """The AUDIT: each claim's live Φ·footprint (repo-scoped) must be COVERED by its declared
    `reads` (plus its own project + the engine).  Returns the under-declared [(proj, claim,
    missing, declared)] — an empty list means every declaration is sound."""
    live = build(repo_root, names)
    projects = {p.name for p in repo_root.iterdir() if (p / "paper.toml").is_file()}
    root_files = _root_files(repo_root)
    bad = []
    for name in names:
        pdir = repo_root if name == "." else repo_root / name
        declared = _declared(pdir)
        imported = _imported(pdir, repo_root)
        for k, fp in live.get(name, {}).items():
            if "*" in fp:                            # degraded footprint (e.g. strace blocked) — skip
                continue
            miss = _missing(fp, declared.get(k, set()), projects, root_files, name, imported)
            if miss:
                bad.append((name, k, miss, sorted(declared.get(k, set()))))
    return bad


def audit_one(proj: str, claim: str) -> dict:
    """Ζ·foot·act — the PER-CLAIM footprint-audit ORACLE: strace this one claim's check and report
    whether its live Φ·footprint is covered by its declared `reads` (+ own project + engine).  Bazel
    nests one of these per claim and pk_footaudit aggregates them — so the audit SWEEP is the build
    graph, not footdeps' ThreadPool loop (which stays for direct/on-demand use)."""
    project_dir = Path(proj).resolve()
    name = "." if proj == "." else project_dir.name
    repo_root = project_dir if proj == "." else project_dir.parent
    projects = {p.name for p in repo_root.iterdir() if (p / "paper.toml").is_file()}
    raw = tomllib.loads((project_dir / "paper.toml").read_text())
    custom = raw.get("checks", {})
    declared = _declared(project_dir).get(claim, set())
    F = {}
    for b in bib.load_config(project_dir)["bibs"]:
        F.update(bib.parse(b))
    f = F.get(claim)
    if not f or not f.get("check") or f["check"].startswith(resolver.CROSSING):
        return {"claim": claim, "ok": True, "skip": True}     # a crossing verb is an edge — no footprint
    fp = resolver.footprint(f["check"], project_dir, custom, scope=repo_root)
    if fp is None:
        return {"claim": claim, "ok": True, "degraded": True}  # strace blocked — over-declare, never fail
    missing = _missing(fp, declared, projects, _root_files(repo_root), name,
                       _imported(project_dir, repo_root))
    # `engine` = the def-mutable surface (the modules whose def-sites the Ζ·mutant fanout sweeps);
    # pk_foot_learn aggregates it across claims → footprints.json (the def-scope manifest).
    return {"claim": claim, "ok": not missing, "missing": missing, "engine": _engine(fp)}


def main(argv: list) -> int:
    if "--only" in argv:
        i = argv.index("--only")
        claim = argv[i + 1]
        rest = [a for a in argv[1:] if a != "--only" and a != claim and not a.startswith("-")]
        print(json.dumps(audit_one(rest[0] if rest else ".", claim)))
        return 0
    repo_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                    capture_output=True, text=True).stdout.strip())
    names = [a for a in argv[1:] if not a.startswith("-")] or WIRED
    bad = audit(repo_root, names)
    if bad:
        for proj, k, miss, decl in bad:
            print(f"paperkit-footdeps: {proj}:{k} footprint reads {miss} not in declared reads {decl} "
                  f"— add to the claim's `reads` field", file=sys.stderr)
        return 1
    print(f"paperkit-footdeps: every declared `reads` ⊇ its Φ·footprint ({len(names)} projects audited)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
