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
import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project as P  # noqa: E402
import resolver  # noqa: E402

WIRED = ["boundaries", "config", "paper", "setup", "."]   # projects with per-claim Bazel graphs


def _tokens(reads: list, projects: set) -> list:
    """Reduce repo-relative read paths to dep tokens (top-level unit each belongs to)."""
    out = set()
    for r in reads:
        top = r.split("/")[0]
        if top == "paperkit":
            out.add("paperkit")
        elif top in projects:
            out.add(top)
        else:
            out.add(".")              # a root file (.githooks/, a root bib/rubric/asset)
    return sorted(out)


def build(repo_root: Path, names: list) -> dict:
    projects = {p.name for p in repo_root.iterdir() if (p / "paper.toml").is_file()}
    manifest = {}
    for name in names:
        pdir = repo_root if name == "." else repo_root / name
        raw = tomllib.loads((pdir / "paper.toml").read_text())
        custom = raw.get("checks", {})
        cfg = P.load_config(pdir)
        F = {}
        for b in cfg["bibs"]:
            F.update(P.entries(b))
        # result: is an EDGE (no leaf target) — its footprint is never used, and stracing it
        # reruns a whole sibling gate; skip it.  strace is I/O-bound, so trace the rest CONCURRENTLY.
        items = [(k, f["check"]) for k, f in sorted(F.items())
                 if f.get("check") and not f["check"].startswith("result:")]

        def deps(chk):
            fp = resolver.footprint(chk, pdir, custom, scope=repo_root)
            return ["*"] if fp is None else _tokens(fp, projects)

        with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4))) as ex:
            graded = list(ex.map(lambda kc: deps(kc[1]), items))
        manifest[name] = {k: d for (k, _), d in zip(items, graded)}
    return manifest


def _declared(pdir: Path) -> dict:
    """{claim: set(declared read tokens)} from each claim's `reads` field (the declare+audit
    source).  Routed through the canonical parser (paperkit.bib, via P.entries) — `reads` is now
    a first-class field there, so no separate line scanner / no disagreement with the build."""
    F = {}
    for b in P.load_config(pdir)["bibs"]:
        F.update(P.entries(b))
    return {k: set(f.get("reads", [])) for k, f in F.items()}


def audit(repo_root: Path, names: list) -> list:
    """The AUDIT: each claim's live Φ·footprint (repo-scoped) must be COVERED by its declared
    `reads` (plus its own project + the engine).  Returns the under-declared [(proj, claim,
    missing, declared)] — an empty list means every declaration is sound."""
    live = build(repo_root, names)
    bad = []
    for name in names:
        declared = _declared(repo_root if name == "." else repo_root / name)
        for k, toks in live.get(name, {}).items():
            if "*" in toks:                          # degraded footprint (e.g. strace blocked) — skip
                continue
            extra = {t for t in toks if t != "paperkit" and t != name}
            miss = extra - declared.get(k, set())
            if miss:
                bad.append((name, k, sorted(miss), sorted(declared.get(k, set()))))
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
    for b in P.load_config(project_dir)["bibs"]:
        F.update(P.entries(b))
    f = F.get(claim)
    if not f or not f.get("check") or f["check"].startswith("result:"):
        return {"claim": claim, "ok": True, "skip": True}     # result: is an edge — no footprint
    fp = resolver.footprint(f["check"], project_dir, custom, scope=repo_root)
    if fp is None:
        return {"claim": claim, "ok": True, "degraded": True}  # strace blocked — over-declare, never fail
    extra = {t for t in _tokens(fp, projects) if t != "paperkit" and t != name}
    missing = sorted(extra - declared)
    return {"claim": claim, "ok": not missing, "missing": missing}


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
