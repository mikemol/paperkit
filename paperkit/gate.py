#!/usr/bin/env python3
"""paperkit gate — verify the paper.

Three invariants, all from the warrant set:
  RESOLVE   every [@key] cited in the prose resolves — a claim whose `check`
            passes, or a reference (no `check`) that is at least defined.  The
            resolved set is CLOSED under `rests-on`: a cited/placed claim's
            grounding premises must resolve too, transitively (a marker for them
            need not survive in the rendered prose), and a rests-on edge to an
            undefined key fails the gate.
  COVERAGE  every rubric section appears in the prose, and every claim tagged
            for a section is cited within it.  A PLACEMENT (emit:/figure) tagged
            to a section but cited by no prose is a postulate — advised against by
            default, and rejected under --safe (a zero-postulate document).
  --without-K  opt-in proof-relevance: every cited claim must carry a DISTINCT
            witness.  The gate's check→bool is proof-irrelevant (Axiom K / UIP), so
            it would otherwise identify distinct claims that share one check.
  PROJECT   the committed prose equals the projection (paperkit-project --check).

A claim's verifier is `<type>:<target>`.  The built-in types (no config needed) are declared
ONCE, as data, in resolver.VERBS — one verb per resolution kind — and are not re-listed here:
this text would drift, and did (it named two verbs long after there were five).
Custom types come from paper.toml as `[checks.<type>] cmd = "... {target} ..."`,
run from the project dir, exit 0 = pass.  `cmd:` is the universal escape hatch
every check reduces to; the registry just gives recurring ones a name.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402  (Ω·config — the one configurable-resolution pipeline)
import bib  # noqa: E402  (the parser/data-model leaf)
import project as P  # noqa: E402  (the PROJECTOR — gate's only genuine need for project, the PROJECT invariant)


# The check-RESOLUTION core lives in resolver.py — a small, standalone module (no projector,
# no parallel gate loop, no config/CLI) so it can be imported and tested with a small blast
# radius.  Re-exported here so callers reaching gate.resolves / gate.clean_env / gate.footprint
# keep working; the gate itself uses resolves below.
from resolver import (  # noqa: E402,F401
    clean_env, run_ok, resolves, footprint, _check_cmd,
    _ENV_KEEP, _ENV_KEEP_PREFIX)
import resolver  # noqa: E402  (the module binding — resolver.PATH joins the composed registry below)

# Ω·config — the knobs this module RESOLVES, declared here (place-by-ownership; the kernel
# hosts the mechanism only).  JSON and ONLY are also resolved by discriminate — it references
# gate's (the lowest common component in the DEPS lattice owns them).
SAFE = config.Param("safe", "PAPERKIT_SAFE", config="safe", flag=True,
                    help="zero-postulate: an uncited placement FAILS the gate, not merely advises")
WITHOUT_K = config.Param("without-K", "PAPERKIT_WITHOUT_K", config="without_k", flag=True, aliases=("--without-k",),
                         help="forbid two cited claims sharing a single witness")
JOBS = config.Param("jobs", "PAPERKIT_JOBS", config="jobs",
                    help="gate worker count (default all cores; 1 = serial)")
JSON = config.Param("json", "PAPERKIT_JSON", flag=True,
                    help="emit structured results to stdout (human lines suppressed)")
ONLY = config.Param("only", "PAPERKIT_ONLY",
                    help="gate: resolve ONLY this one claim's check (the leaf of the recursive check target, Ζ·starlark) and exit")
INVARIANTS = config.Param("invariants", "PAPERKIT_INVARIANTS", flag=True,
                          help="gate: verify only the whole-project invariants (PROJECT/COVERAGE/--without-K), not per-check resolution — the NODE of the recursive check, the leaves resolve the checks")
# The gate CLI's composed registry: exactly the Params its import cone hosts (own 6 +
# project's + resolver's; bnd-config asserts this completeness).
REGISTRY = [SAFE, WITHOUT_K, JOBS, JSON, ONLY, INVARIANTS, P.TARGET, P.CHECK, resolver.PATH]


def cited_keys(prose: str) -> set:
    # Citations live in prose, not in emitted code blocks — strip fenced blocks so
    # an example containing `@misc{…}` is not misread as a citation [@misc].
    prose = re.sub(r"```.*?```", "", prose, flags=re.S)
    # A citation materializes as a pandoc/web [@key] OR a footnote-target [^key] marker
    # (its document-end [^key]: definition names the same key) — count both as cited.
    return (set(re.findall(r"@([A-Za-z0-9][\w.:-]*)", prose))
            | set(re.findall(r"\[\^([A-Za-z0-9][\w.:-]*)\]", prose)))


def main(argv: list) -> int:
    config.apply_args(argv, REGISTRY)     # Ω·config: capture args (arg overrides env), process-local
    pos = config.positionals(argv, REGISTRY)
    project_dir = Path(pos[0]).resolve() if pos else Path.cwd()
    raw = tomllib.loads((project_dir / "paper.toml").read_text())
    pol, custom = raw.get("paper", {}), raw.get("checks", {})   # project policy + custom check types
    safe = config.resolve(SAFE, pol)                 # zero-postulate: uncited placements FAIL
    without_k = config.resolve(WITHOUT_K, pol)       # forbid two cited claims sharing a witness
    inv_only = config.resolve(INVARIANTS)            # Ζ·starlark: the invariants NODE (no per-check resolve)
    as_json = config.resolve(JSON)                   # structured stdout (human lines suppressed)
    # The bib IS the makefile: a project's distinct checks are independent targets, so the gate
    # runs them concurrently (default = all cores; jobs=1 forces serial).
    jobs = int(config.resolve(JOBS) or (os.cpu_count() or 4))

    def info(msg):              # human success lines — suppressed under --json
        if not as_json:
            print(msg)
    cfg = bib.load_config(project_dir)

    F, primary = {}, cfg["bibs"][0].name
    for b in cfg["bibs"]:
        F.update(bib.parse(b))

    # Ζ·starlark — the LEAF of the recursive check target: resolve ONE claim's check and exit.
    # A project's gate (the node) is this over every claim ∧ the project invariants; a Bazel
    # check target is exactly this leaf, so the bib's claim-DAG runs as the build graph.
    only = config.resolve(ONLY)
    if only:
        if only not in F or not F[only].get("check"):
            print(f"paperkit-gate: no check for claim {only!r}", file=sys.stderr)
            return 2
        ok = resolves(F[only]["check"], project_dir, custom)
        info(f"paperkit-gate: {only} {'ok' if ok else 'FAIL'} — {F[only]['check']}")
        return 0 if ok else 1

    out = cfg["out"]
    if not out.exists():
        print(f"paperkit-gate: {out.name} not built — run paperkit-project", file=sys.stderr)
        return 1
    prose = out.read_text()
    target = config.resolve(P.TARGET, pol)
    cited = cited_keys(prose)
    if target == "plain":
        # plain surfaces NO citation marker, but the projection WEAVES every section-tagged claim — each is
        # placed-in-prose by construction. Treat them as cited so RESOLVE + COVERAGE still bite (identical
        # verification to footnote, which marked every claim; only the rendered marker is gone).
        cited |= {k for k, f in F.items() if f.get("section")}
    rc = 0

    # PROJECT — committed prose is the projection (for the project's declared render target)
    proj_ok = prose == P.project(cfg, target)
    if not proj_ok:
        print(f"paperkit-gate: {out.name} ≠ projection — regenerate (paperkit-project)", file=sys.stderr)
        rc = 1
    else:
        info(f"paperkit-gate: {out.name} ≡ projection")

    # RESOLVE — every cited claim's check passes; references at least defined.
    # Placed warrants (emit:/figure) carry no citation but ARE in the document by
    # construction, so their checks must pass too.  And a claim's GROUNDING
    # (rests-on) premises are load-bearing whether or not any citation marker for
    # them survives in the rendered prose (plain/footnote render none; adjacent and
    # cross-scope edges render none on any target) — so the verified set is the
    # TRANSITIVE CLOSURE of cited|placed under rests-on.  A rests-on edge to an
    # undefined key is a broken grounding: it fails the gate like an undefined
    # citation does.
    warrants = {k for k, f in F.items() if f.get("check")}
    placed = {k for k, f in F.items() if bib.is_placed(f)}
    grounded, dangling = bib.rests_closure((cited & set(F)) | placed, F)
    to_verify = (cited | placed | grounded) & warrants
    undefined = sorted(cited - set(F))
    # Resolve each DISTINCT check exactly once (shared witnesses run one time), concurrently.
    # A memory-heavy check declares `mem` in the bib — the makefile's resource manifest, which
    # Ζ·starlark projects to a Bazel resource reservation so the SCHEDULER bounds concurrent
    # memory (membudget retired: Bazel IS the semaphore — per-machine, no cross-repo flock).
    if inv_only:
        # Ζ·starlark — the invariants NODE.  Per-check resolution is the LEAVES' job (the
        # generated check targets), so the node skips it and verifies only the whole-project
        # invariants (PROJECT above, plus COVERAGE and --without-K below).
        bad: list = []
    else:
        distinct = sorted({F[k]["check"] for k in to_verify})

        def resolve1(c: str) -> bool:
            return resolves(c, project_dir, custom)

        if len(distinct) > 1 and jobs > 1:
            with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
                cache = dict(zip(distinct, ex.map(resolve1, distinct)))
        else:
            cache = {c: resolve1(c) for c in distinct}

        bad = sorted(k for k in to_verify if not cache[F[k]["check"]])
    if undefined:
        print(f"paperkit-gate: undefined citations: {', '.join(undefined)}", file=sys.stderr)
        rc = 1
    if dangling:
        for k, y in sorted(dangling):
            print(f"paperkit-gate: dangling rests-on: [@{k}] rests on undefined [@{y}]",
                  file=sys.stderr)
        rc = 1
    if bad:
        for k in bad:
            print(f"paperkit-gate: check FAILED for [@{k}]: {F[k]['check']}", file=sys.stderr)
        rc = 1
    if inv_only:
        info(f"paperkit-gate: invariants node — {len(to_verify)} claim check(s) deferred to the leaf targets")
    elif not undefined and not bad and not dangling:
        info(f"paperkit-gate: {len(to_verify)} cited/placed/grounded claim(s) all resolve to passing checks")

    # WITHOUT-K — proof-relevance.  The gate reduces each check to a boolean, so it
    # silently identifies distinct cited claims that share one witness (Axiom K /
    # UIP).  --without-K drops that: every cited claim must carry a DISTINCT witness.
    # (collapses are computed always, for --json; they only FAIL the gate under --without-K.)
    by_check: dict = {}
    for k in sorted(cited & warrants):
        by_check.setdefault(F[k]["check"], []).append(k)
    collapses = {c: ks for c, ks in by_check.items() if len(ks) > 1}
    if without_k:
        if collapses:
            for c, ks in sorted(collapses.items()):
                print(f"paperkit-gate: --without-K — {len(ks)} cited claims collapse onto "
                      f"one witness {c}: {', '.join(ks)}", file=sys.stderr)
            rc = 1
        else:
            info(f"paperkit-gate: --without-K — {len(cited & warrants)} cited claim(s) "
                 f"each carry a distinct witness")

    # COVERAGE — sections present, section-tagged claims cited
    headings = "\n".join(ln for ln in prose.splitlines() if ln.startswith("## "))
    gaps = []
    for sk, title in bib.rubric(cfg["rubric"]):
        if title.lower() not in headings.lower():
            gaps.append(f"section '{title}' absent")
    advisories = []
    # Ρ·emit·missing — a placement that DID NOT HAPPEN is a finding, not silence.  project.py renders
    # an absent emit: asset as `<!-- emit: missing … -->`, so the committed prose and its projection
    # agree ON THE COMMENT and the gate passed: green and visibly broken at once.  The asymmetry was
    # the tell — an UNCITED placement is already rejected under --safe as a postulate, so a placement
    # whose artifact is absent is at least as strong a signal.  Absence gets denoted, never defaulted.
    # (Reported by a downstream consumer whose `out` lived outside the project dir, so the generator
    # and the projector resolved the asset to two different paths.)
    for k, f in F.items():
        if f.get("emit") and not (cfg["out"].parent / f["emit"]).exists():
            gaps.append(f"placement [@{k}] emits {f['emit']} — the artifact is ABSENT, so the "
                        f"document renders a placeholder comment where the evidence should be")
    for k, f in F.items():
        if f.get("section") and k not in cited:
            if bib.is_placed(f):
                # An uncited placement is a POSTULATE: a block in the document with
                # no claim citing it — present and load-bearing, but outside the
                # checked claim-DAG.  Tolerated by default (advisory); under --safe
                # it fails, exactly as `agda --safe` rejects postulates.
                msg = (f"uncited placement [@{k}] (section={f['section']}) — a postulate: "
                       f"a block no claim cites; prefer an example the prose cites")
                (gaps if safe else advisories).append(msg)
            else:
                gaps.append(f"claim [@{k}] tagged section={f['section']} but not cited")
    secs = len(bib.rubric(cfg["rubric"]))
    if gaps:
        for g in gaps:
            print(f"paperkit-gate: coverage — {g}", file=sys.stderr)
        rc = 1
    else:
        info(f"paperkit-gate: coverage complete — {secs} sections, all tagged claims cited")
    for a in advisories:
        print(f"paperkit-gate: advisory — {a}", file=sys.stderr)

    if as_json:
        print(json.dumps({
            "document": out.name, "pass": rc == 0, "project_ok": proj_ok,
            "verified": len(to_verify), "undefined": undefined, "bad": bad,
            "dangling": sorted(list(e) for e in dangling),
            "sections": secs, "gaps": gaps,
            "postulates": sorted(k for k, f in F.items()
                                 if f.get("section") and k not in cited and bib.is_placed(f)),
            "collapses": collapses,
        }, indent=2))
    print("paperkit-gate: PASS" if rc == 0 else "paperkit-gate: FAIL", file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
