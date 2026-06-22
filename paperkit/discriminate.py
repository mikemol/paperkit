#!/usr/bin/env python3
"""paperkit discriminate (Δ) — grade each warrant's check by whether it can FAIL.

A check earns a claim only to the extent it is sensitive to the world: a check
that passes no matter what the project says verifies nothing.  The gate enforces
that every sentence NAMES a passing check; Δ asks the next question — could that
check ever have failed?  It grades every warrant's `check` on a computable
discrimination ladder, and for runnable (cmd/custom) checks it empirically
discovers the check's SENSITIVITY SET — the input files whose corruption flips
the check red — by single-file mutation in a throwaway sandbox.

Grades (this is also the `strength` field that Γ — graded thresholds — will read):

  vacuous     PROVABLY cannot fail: a file: check whose target is a required
              project input or engine source, so its existence is presupposed by
              the build itself.  Tests presence of something that must be there
              anyway — 0 bits about the claim.
  existence   file: of a CONTINGENT artifact (a build output, a figure) — its
              absence is a real failure, so it discriminates "the artifact was
              produced", but nothing about the artifact's content.
  behavioral  PROVEN falsifiable: some single-file mutation flips this cmd/custom
              check red.  It runs, and it can go red — the sensitivity set names
              exactly which inputs it actually tests.
  indeterminate  a cmd/custom check that no generic mutation could flip.  Either
              genuinely vacuous OR a NEGATIVE-ASSERTION check (one that passes
              precisely when the system correctly rejects bad input, e.g. a
              drift-rejection test — garbage input keeps the rejection true).
              Δ refuses to guess: falsifiability is not demonstrated.  Closing
              this needs a targeted counter-fixture (a Π task), not a verdict.

Δ does NOT judge whether a behavioral check's sensitivity set actually concerns
the CLAIM's content — a check sensitive to the right files for the wrong claim is
the launder case, left to Λ.  Δ reports the set; Λ judges relevance.

Binding dilution: a check shared by N cited claims supplies one verdict for N
sentences — reported as `shared_with`, the per-claim signal being the per-check
signal split N ways.

    paperkit-discriminate [DIR]                  report (exit 0)
    paperkit-discriminate --min-strength L [DIR] gate: exit 1 if any considered
                                                 warrant grades below L
                                                 (L = existence | behavioral)
    paperkit-discriminate --all [DIR]            grade every checked warrant, not
                                                 just those cited in the prose
    paperkit-discriminate --json [DIR]           machine output (feeds Γ / Π)

DIR defaults to the current directory and must contain paper.toml.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project as P  # noqa: E402
import gate as G  # noqa: E402

CORRUPT = b"\x00\x00DELTA-CORRUPTION\x00\x00\n"
MUTABLE_SUFFIXES = {".bib", ".tsv", ".toml", ".md", ".sh", ".py"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "out"}

STRENGTH = {"vacuous": 0, "existence": 1, "indeterminate": 1, "behavioral": 2}
ORDER = {"existence": 1, "behavioral": 2}  # valid --min-strength thresholds


def presupposed_inputs(project_dir: Path, cfg: dict) -> set:
    """Resolved paths whose existence the build already presupposes — a file:
    check naming one of these is redundant with the project being runnable, so
    it is provably vacuous.  The declared bibs / rubric / config / output, plus
    the engine scripts the checks invoke via ../paperkit."""
    req = set(cfg["bibs"]) | {cfg["rubric"], cfg["out"], project_dir / "paper.toml"}
    engine = Path(__file__).resolve().parent
    req |= set(engine.glob("*.py"))
    return {p.resolve() for p in req}


def sandbox_files(sandbox_project: Path, exclude_scripts: set) -> list:
    """Mutable text inputs under the sandboxed project (the verifier scripts
    themselves are excluded — corrupting a check's own script is a trivial,
    uninformative self-break)."""
    out = []
    for f in sorted(sandbox_project.rglob("*")):
        if not f.is_file() or f.suffix not in MUTABLE_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        if f.suffix == ".sh" and "checks" in f.parts:
            continue  # a verifier script; its corruption tests itself, not the claim
        out.append(f)
    return out


def sensitivity(chk: str, sandbox_project: Path, custom: dict) -> tuple[bool, list]:
    """Run chk against single-file corruptions of the sandbox; return
    (baseline_passes, sensitivity_set) where the set is the relative paths whose
    corruption flips chk from pass to fail."""
    baseline = G.resolves(chk, sandbox_project, custom)
    sens: list[str] = []
    if not baseline:
        return False, sens
    for f in sandbox_files(sandbox_project, set()):
        orig = f.read_bytes()
        f.write_bytes(CORRUPT)
        try:
            flipped = not G.resolves(chk, sandbox_project, custom)
        finally:
            f.write_bytes(orig)
        if flipped:
            sens.append(str(f.relative_to(sandbox_project)))
    return True, sens


def grade_check(chk: str, project_dir: Path, presupposed: set,
                custom: dict, sandbox_project: Path) -> dict:
    typ, _, target = chk.partition(":")
    if typ == "file":
        resolved = (project_dir / target).resolve()
        if resolved in presupposed:
            return {"grade": "vacuous", "tests": [target],
                    "why": "existence of a required project/engine source — presupposed by the build",
                    "not_higher": "to rise: give it a check that can FAIL — a file: of a presupposed input is removed by no real change",
                    "not_lower": "vacuous is the floor"}
        return {"grade": "existence", "tests": [target],
                "why": "existence of a contingent artifact — presence only, not content",
                "not_higher": "to rise: test the artifact's CONTENT, not just its presence (a content-sensitive cmd:)",
                "not_lower": "not vacuous: the artifact is contingent, not a presupposed build input, so its absence is a real failure"}
    # cmd: / custom — empirically probe falsifiability
    baseline, sens = sensitivity(chk, sandbox_project, custom)
    if not baseline:
        return {"grade": "broken", "tests": [],
                "why": "check does not pass in a pristine sandbox — repo is not green",
                "not_higher": "—", "not_lower": "—"}
    if sens:
        return {"grade": "behavioral", "tests": sens,
                "why": f"falsifiable — corrupting {len(sens)} input(s) flips it red",
                "not_higher": "behavioral is the top tier; a proof-grade (total, postulate-free witness) tier is not yet defined",
                "not_lower": f"not indeterminate/vacuous: a mutation DOES flip it (sensitive to {len(sens)} input(s))"}
    return {"grade": "indeterminate", "tests": [],
            "why": "no generic mutation flips it — vacuous OR a negative-assertion check; needs a targeted counter-fixture (Π)",
            "not_higher": "to rise: a targeted counter-fixture (a positive mutation) would prove it behavioral",
            "not_lower": "not provably vacuous: it runs a cmd:, not a presupposed file:"}


def main(argv: list) -> int:
    flags = [a for a in argv if a.startswith("-")]
    args = [a for a in argv if not a.startswith("-")]
    min_strength = None
    if "--min-strength" in argv:
        min_strength = argv[argv.index("--min-strength") + 1]
        if min_strength not in ORDER:
            sys.exit(f"paperkit-discriminate: --min-strength must be one of {sorted(ORDER)}")
    consider_all = "--all" in flags
    as_json = "--json" in flags

    pos = [a for a in args if a != min_strength]
    project_dir = Path(pos[0]).resolve() if pos else Path.cwd()
    cfg = P.load_config(project_dir)
    custom = tomllib.loads((project_dir / "paper.toml").read_text()).get("checks", {})
    presupposed = presupposed_inputs(project_dir, cfg)

    F = {}
    for b in cfg["bibs"]:
        F.update(P.entries(b))

    out = cfg["out"]
    cited = G.cited_keys(out.read_text()) if out.exists() else set()

    # which warrants to grade
    keys = [k for k, f in F.items() if f.get("check")
            and (consider_all or k in cited)]

    # share counts: how many CONSIDERED warrants lean on each distinct check
    share: dict[str, list] = {}
    for k in keys:
        share.setdefault(F[k]["check"], []).append(k)

    # one sandbox, reused (checks never mutate it; each probe restores its file)
    tmp = Path(tempfile.mkdtemp(prefix="paperkit-delta-"))
    graded: dict[str, dict] = {}
    try:
        shutil.copytree(project_dir.parent, tmp / project_dir.parent.name,
                        ignore=shutil.ignore_patterns(*SKIP_DIRS, "*.pyc"),
                        dirs_exist_ok=True)
        sandbox_project = tmp / project_dir.parent.name / project_dir.name
        for chk in share:
            graded[chk] = grade_check(chk, project_dir, presupposed, custom, sandbox_project)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    records = []
    for k in keys:
        chk = F[k]["check"]
        g = dict(graded[chk])
        g.update(key=k, check=chk, cited=k in cited, section=F[k].get("section"),
                 shared_with=[o for o in share[chk] if o != k])
        records.append(g)

    # content inputs = the files a check must touch to discriminate the paper's
    # CONTENT (not merely its config/engine); a behavioral check sensitive only
    # to paper.toml or the engine can-fail by CRASH, but does not test content.
    content = {p.name for p in cfg["bibs"]} | {cfg["rubric"].name, cfg["out"].name}
    for r in records:
        if r["grade"] == "behavioral":
            r["content_sensitive"] = any(Path(t).name in content for t in r["tests"])

    if as_json:
        print(json.dumps(records, indent=2))
    else:
        report(records, share, graded, len(cited), len(keys), consider_all)

    rc = 0
    if min_strength is not None:
        floor = ORDER[min_strength]
        weak = [r for r in records if STRENGTH.get(r["grade"], 0) < floor]
        if weak:
            print(f"\npaperkit-discriminate: {len(weak)} warrant(s) below "
                  f"strength '{min_strength}':", file=sys.stderr)
            for r in weak:
                print(f"  [@{r['key']}] {r['grade']} — {r['check']}", file=sys.stderr)
            rc = 1
        else:
            print(f"\npaperkit-discriminate: all {len(records)} warrant(s) "
                  f"meet strength '{min_strength}'")
    return rc


def report(records, share, graded, n_cited, n_checked, consider_all):
    scope = "all checked" if consider_all else f"of {n_cited} cited"
    print(f"paperkit-discriminate (Δ): {n_checked} {scope} warrant(s) carry a "
          f"check, {len(share)} distinct check(s)\n")
    order = {"broken": 0, "vacuous": 1, "indeterminate": 2, "existence": 3, "behavioral": 4}
    for r in sorted(records, key=lambda r: (order.get(r["grade"], 9), r["key"])):
        share_n = len(r["shared_with"]) + 1
        dil = f"  (shared by {share_n} claims)" if share_n > 1 else ""
        crash = (r["grade"] == "behavioral" and not r.get("content_sensitive"))
        tag = "  ⚠ config/crash-sensitive only" if crash else ""
        print(f"  {r['grade']:13} [@{r['key']}]{dil}{tag}")
        print(f"  {'':13} check: {r['check']}")
        if r["tests"]:
            shown = ", ".join(r["tests"][:6]) + ("…" if len(r["tests"]) > 6 else "")
            print(f"  {'':13} sensitive to: {shown}")
        why = r["why"]
        if crash:
            why += " — but touches no content input (warrants/rubric/prose); flips only by crashing on malformed config"
        print(f"  {'':13} {why}\n")
    counts: dict[str, int] = {}
    for r in records:
        counts[r["grade"]] = counts.get(r["grade"], 0) + 1
    summary = ", ".join(f"{n} {g}" for g, n in sorted(counts.items()))
    print(f"  summary: {summary}")
    vac = counts.get("vacuous", 0)
    if vac:
        print(f"  ⚠ {vac} cited claim(s) rest on a check that PROVABLY cannot fail.")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
