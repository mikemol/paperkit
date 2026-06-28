#!/usr/bin/env python3
"""paperkit gate — verify the paper.

Three invariants, all from the warrant set:
  RESOLVE   every [@key] cited in the prose resolves — a claim whose `check`
            passes, or a reference (no `check`) that is at least defined.
  COVERAGE  every rubric section appears in the prose, and every claim tagged
            for a section is cited within it.  A PLACEMENT (emit:/figure) tagged
            to a section but cited by no prose is a postulate — advised against by
            default, and rejected under --safe (a zero-postulate document).
  --without-K  opt-in proof-relevance: every cited claim must carry a DISTINCT
            witness.  The gate's check→bool is proof-irrelevant (Axiom K / UIP), so
            it would otherwise identify distinct claims that share one check.
  PROJECT   the committed prose equals the projection (paperkit-project --check).

A claim's verifier is `<type>:<target>`.  Built-in types (no config needed):
  file:<path>   the artifact exists, relative to the project
  cmd:<script>  run `<target>` from the project dir; exit 0 = pass
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


def cited_keys(prose: str) -> set:
    # Citations live in prose, not in emitted code blocks — strip fenced blocks so
    # an example containing `@misc{…}` is not misread as a citation [@misc].
    prose = re.sub(r"```.*?```", "", prose, flags=re.S)
    return set(re.findall(r"@([A-Za-z0-9][\w.:-]*)", prose))


def main(argv: list) -> int:
    config.apply_args(argv)               # Ω·config: capture args (arg overrides env), process-local
    pos = config.positionals(argv)
    project_dir = Path(pos[0]).resolve() if pos else Path.cwd()
    raw = tomllib.loads((project_dir / "paper.toml").read_text())
    pol, custom = raw.get("paper", {}), raw.get("checks", {})   # project policy + custom check types
    safe = config.resolve(config.SAFE, pol)          # zero-postulate: uncited placements FAIL
    without_k = config.resolve(config.WITHOUT_K, pol)  # forbid two cited claims sharing a witness
    inv_only = config.resolve(config.INVARIANTS)     # Ζ·starlark: the invariants NODE (no per-check resolve)
    as_json = config.resolve(config.JSON)            # structured stdout (human lines suppressed)
    # The bib IS the makefile: a project's distinct checks are independent targets, so the gate
    # runs them concurrently (default = all cores; jobs=1 forces serial).
    jobs = int(config.resolve(config.JOBS) or (os.cpu_count() or 4))

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
    only = config.resolve(config.ONLY)
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
    cited = cited_keys(prose)
    rc = 0

    # PROJECT — committed prose is the projection (for the project's declared render target)
    proj_ok = prose == P.project(cfg, config.resolve(config.TARGET, pol))
    if not proj_ok:
        print(f"paperkit-gate: {out.name} ≠ projection — regenerate (paperkit-project)", file=sys.stderr)
        rc = 1
    else:
        info(f"paperkit-gate: {out.name} ≡ projection")

    # RESOLVE — every cited claim's check passes; references at least defined.
    # Placed warrants (emit:/figure) carry no citation but ARE in the document by
    # construction, so their checks must pass too.
    warrants = {k for k, f in F.items() if f.get("check")}
    placed = {k for k, f in F.items() if bib.is_placed(f)}
    to_verify = (cited | placed) & warrants
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
    if bad:
        for k in bad:
            print(f"paperkit-gate: check FAILED for [@{k}]: {F[k]['check']}", file=sys.stderr)
        rc = 1
    if inv_only:
        info(f"paperkit-gate: invariants node — {len(to_verify)} claim check(s) deferred to the leaf targets")
    elif not undefined and not bad:
        info(f"paperkit-gate: {len(to_verify)} cited/placed claim(s) all resolve to passing checks")

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
            "sections": secs, "gaps": gaps,
            "postulates": sorted(k for k, f in F.items()
                                 if f.get("section") and k not in cited and bib.is_placed(f)),
            "collapses": collapses,
        }, indent=2))
    print("paperkit-gate: PASS" if rc == 0 else "paperkit-gate: FAIL", file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
