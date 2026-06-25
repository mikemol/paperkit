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
    paperkit-discriminate --state F --budget S [DIR]   resumable grading (pump-witness):
                                                 grade under an S-second budget, persist the
                                                 token to F, exit 2 if not done — re-run to
                                                 resume.  A slow grade resumes, never dies.
    paperkit-discriminate --no-cache [DIR]       ignore the content-addressed cache

Grades are memoized PER CHECK (Δ·footprint-cache): each check's grade is keyed on the
content of the files it actually READS (Φ·footprint) plus a global engine epoch, so a
commit re-grades only the checks whose footprint the diff touched — not the whole
project.  (.delta-cache.json, git-ignored.  content_key below is the coarse soundness
basis the per-check key refines: a grade is a pure function of project+engine content.)

DIR defaults to the current directory and must contain paper.toml.
"""
from __future__ import annotations

import json
import os
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project as P  # noqa: E402
import gate as G  # noqa: E402  (cited_keys + footprint, re-exported from resolver)
import driver as D  # noqa: E402  (pump/parse liveness driver — resumable grading)

# This file is the Δ CLI + report.  The grade CACHE, project TOPOLOGY, and the GRADER (the
# mutation sweep + the grade ladder) are their own modules now; imported under the names the
# CLI uses, and re-exported so discriminate.content_key / .grade_check callers keep working.
from cache import (content_key, engine_hash as _engine_hash,  # noqa: E402,F401
                   footprint_hash as _footprint_hash, load as _load_cache, save as _save_cache)
from grader import (presupposed_inputs, sensitivity, grade_check, GradeWitness,  # noqa: E402,F401
                    _grade_parallel, _sandbox_root, STRENGTH, ORDER, RANK_C, GRADE_C, CORRO_C)


def main(argv: list) -> int:
    flags = [a for a in argv if a.startswith("-")]
    args = [a for a in argv if not a.startswith("-")]

    def optval(name):
        return argv[argv.index(name) + 1] if name in argv else None

    def opt_or_env(name, env):
        # Container pipelines: every value-arg also reads a PAPERKIT_* env var, and an
        # EXPLICIT flag OVERRIDES the env var.  So a Containerfile sets defaults via env and
        # an ad-hoc run overrides on the command line — one rule for every knob.
        v = optval(name)
        return v if v is not None else os.environ.get(env)

    # --root pins the Δ sandbox's bounded universe (the grader's _sandbox_root reads it deep,
    # via PAPERKIT_ROOT).  Setting the env from the flag IS the "explicit arg overrides env":
    # one resolved value reaches the grader whether it came from the flag or the container env.
    if optval("--root") is not None:
        os.environ["PAPERKIT_ROOT"] = optval("--root")

    min_strength = opt_or_env("--min-strength", "PAPERKIT_MIN_STRENGTH")
    if min_strength is not None and min_strength not in ORDER:
        sys.exit(f"paperkit-discriminate: --min-strength must be one of {sorted(ORDER)}")
    # --min-corroboration: the SECOND, ORTHOGONAL gate (Ε·agree·grade) — independent of
    # --min-strength.  You can require falsifiability, corroboration, either, or both; they
    # are different axes, not one scalar.  Today only `independent` is a meaningful floor.
    min_corro = opt_or_env("--min-corroboration", "PAPERKIT_MIN_CORROBORATION")
    if min_corro is not None and min_corro not in CORRO_C:
        sys.exit(f"paperkit-discriminate: --min-corroboration must be one of {sorted(CORRO_C)}")
    state_file = opt_or_env("--state", "PAPERKIT_STATE")    # resumable grading: persist the token here
    budget_str = opt_or_env("--budget", "PAPERKIT_BUDGET")  # seconds per invocation (<=0 = run to done)
    budget = float(budget_str) if budget_str else 0.0
    consider_all = "--all" in flags
    as_json = "--json" in flags

    resolution = opt_or_env("--resolution", "PAPERKIT_RESOLUTION") or "file"  # threaded into the grader
    if resolution not in ("file", "def"):
        sys.exit("paperkit-discriminate: --resolution must be 'file' or 'def'")

    consumed = {x for x in (optval("--min-strength"), optval("--min-corroboration"), optval("--state"),
                            optval("--budget"), optval("--resolution"), optval("--root"))
                if x is not None}
    pos = [a for a in args if a not in consumed]
    project_dir = Path(pos[0]).resolve() if pos else Path.cwd()
    _sandbox_root(project_dir)   # resolve+validate the sandbox root up front (home-guard) — a clean exit before any sweep
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

    if "--footprint" in flags:
        # Φ·footprint: each considered check's READ footprint (the project files it opens),
        # the SOUND per-check key a footprint cache invalidates on — a diff touching none of
        # a check's footprint cannot change its verdict.  Reads ⊇ Δ's sensitivity `tests`.
        print(json.dumps({c: G.footprint(c, project_dir, custom) for c in sorted(share)}, indent=2))
        return 0

    # Δ·footprint-cache: a Δ grade is a pure function of its inputs, so cache it PER CHECK,
    # keyed on the content of the files it actually READS (Φ·footprint) plus the engine
    # EPOCH (_engine_hash).  A commit then re-grades only the checks whose footprint the diff
    # touched — where the old whole-project content_key cache invalidated EVERY check on any
    # edit.  Reuse a check while its footprint files (and the engine) are unchanged.
    no_cache = "--no-cache" in flags
    engine = _engine_hash()
    cached = {} if no_cache else _load_cache(project_dir)
    valid = cached.get("engine") == engine and cached.get("resolution") == resolution
    entries = cached.get("checks", {}) if valid else {}

    reuse, stale = {}, []
    for c in share:
        e = entries.get(c)
        if e and _footprint_hash(project_dir, e["footprint"]) == e["fp"]:
            reuse[c] = e
        else:
            stale.append(c)

    fresh, fresh_grader = {}, None
    if stale and state_file is None and budget_str is None:
        # Batch grade — the default.  Test the RAW flag (budget_str): an absent --budget
        # coerces to 0.0 ("run to done"), so `budget is None` would never hold and would
        # leave this path dead (the Σ·flat·gate guard-fix).  Only the STALE checks are swept.
        fresh_grader = "_grade_parallel"
        fresh = _grade_parallel(project_dir, stale, custom, presupposed, resolution)
    elif stale:
        # Resumable path: grade the stale checks as a pump-witness under an optional budget
        # (--state/--budget make a long grade resume across short calls — pump-ask liveness).
        witness = GradeWitness(project_dir, stale, custom, presupposed, resolution)
        meaning, steps, done = D.drive(witness, state_path=state_file, budget=budget)
        if not done:
            print(f"paperkit-discriminate: graded {meaning['progress']} in {steps} increment(s) — "
                  f"not done; state persisted to {state_file}, re-run to resume", file=sys.stderr)
            return 2
        fresh = meaning["graded"]
        fresh_grader = "GradeWitness"

    # assemble grades + a PER-CHECK grader, and refresh the cache entry of each graded check
    # with its fresh footprint (Σ·flat·witness: a reused grade reports grader "cache").
    graded, grader_of, new_entries = {}, {}, dict(reuse)
    for c, e in reuse.items():
        graded[c], grader_of[c] = e["grade"], "cache"
    for c in stale:
        fp = fresh[c].pop("_footprint", [])   # computed once during grading (scoping + cache); strip from the record
        graded[c], grader_of[c] = fresh[c], fresh_grader
        new_entries[c] = {"grade": fresh[c], "footprint": fp, "fp": _footprint_hash(project_dir, fp)}

    if not no_cache:
        _save_cache(project_dir, {"engine": engine, "resolution": resolution, "checks": new_entries})

    if stale:
        print(f"paperkit-discriminate: graded by {fresh_grader} "
              f"({len(stale)} graded, {len(reuse)} reused from footprint cache)", file=sys.stderr)
    else:
        print(f"paperkit-discriminate: all {len(reuse)} grade(s) reused from footprint cache", file=sys.stderr)
    records = []
    for k in keys:
        chk = F[k]["check"]
        g = dict(graded[chk])
        g.update(key=k, check=chk, cited=k in cited, section=F[k].get("section"),
                 shared_with=[o for o in share[chk] if o != k])
        g["from"] = F[k].get("from", [])
        g["rests-on"] = F[k].get("rests-on", [])     # grounding edges (for clamping)
        g["grader"] = grader_of[chk]
        records.append(g)

    # content inputs = the files a check must touch to discriminate the paper's
    # CONTENT (not merely its config/engine); a behavioral check sensitive only
    # to paper.toml or the engine can-fail by CRASH, but does not test content.
    content = {p.name for p in cfg["bibs"]} | {cfg["rubric"].name, cfg["out"].name}
    for r in records:
        if r["grade"] == "behavioral":
            r["content_sensitive"] = any(Path(t).name in content for t in r["tests"])

    # EFFECTIVE grade — clamp by entailment: a claim is no better grounded than the
    # weakest premise it (transitively) depends on.  `clamp` = rungs dropped from the
    # self-contained grade; `clamped_by` = the premise that pins it.
    rby = {r["key"]: r for r in records}
    effc: dict = {}

    def eff(k, stack=()):
        if k in effc:
            return effc[k]
        r = rby.get(k)
        if r is None:
            return (RANK_C["behavioral"], None)   # not in scope: impose no constraint
        best, by = RANK_C.get(r["grade"], 0), None
        for d in r.get("rests-on", []):              # clamp over GROUNDING edges
            if d in rby and d not in stack and d != k:
                de, _ = eff(d, stack + (k,))
                if de < best:
                    best, by = de, d
        effc[k] = (best, by)
        return effc[k]

    for r in records:
        e, by = eff(r["key"])
        r["effective_grade"] = GRADE_C[e]
        r["clamp"] = RANK_C.get(r["grade"], 0) - e
        r["clamped_by"] = by

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
    if min_corro is not None:
        floor = CORRO_C[min_corro]
        weak = [r for r in records if CORRO_C.get(r.get("corroboration", "single"), 0) < floor]
        if weak:
            print(f"\npaperkit-discriminate: {len(weak)} warrant(s) below "
                  f"corroboration '{min_corro}':", file=sys.stderr)
            for r in weak:
                print(f"  [@{r['key']}] {r.get('corroboration', 'single')} — {r['check']}", file=sys.stderr)
            rc = 1
        else:
            print(f"\npaperkit-discriminate: all {len(records)} warrant(s) "
                  f"meet corroboration '{min_corro}'")
    return rc


def report(records, share, graded, n_cited, n_checked, consider_all):
    scope = "all checked" if consider_all else f"of {n_cited} cited"
    print(f"paperkit-discriminate (Δ): {n_checked} {scope} warrant(s) carry a "
          f"check, {len(share)} distinct check(s)\n")
    order = {"broken": 0, "vacuous": 1, "indeterminate": 2, "existence": 3,
             "behavioral": 4, "imported": 5}
    for r in sorted(records, key=lambda r: (order.get(r["grade"], 9), r["key"])):
        share_n = len(r["shared_with"]) + 1
        dil = f"  (shared by {share_n} claims)" if share_n > 1 else ""
        crash = (r["grade"] == "behavioral" and not r.get("content_sensitive"))
        tag = "  ⚠ config/crash-sensitive only" if crash else ""
        corro = f"  + {r['corroboration']} ({r.get('producers','?')} producers)" if r.get("corroboration") == "independent" else ""
        print(f"  {r['grade']:13} [@{r['key']}]{dil}{tag}{corro}")
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
    print(f"  summary (self-grade): {summary}")
    eff_counts: dict[str, int] = {}
    for r in records:
        eff_counts[r.get("effective_grade", r["grade"])] = \
            eff_counts.get(r.get("effective_grade", r["grade"]), 0) + 1
    print(f"  summary (effective):  {', '.join(f'{n} {g}' for g, n in sorted(eff_counts.items()))}")
    clamped = [r for r in records if r.get("clamp", 0) > 0]
    vac = counts.get("vacuous", 0)
    if vac:
        print(f"  ⚠ {vac} cited claim(s) rest on a check that PROVABLY cannot fail.")
    if clamped:
        print(f"  ⚠ {len(clamped)} cited claim(s) are CLAMPED below their self grade by "
              f"weaker premises (effective < self).")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
