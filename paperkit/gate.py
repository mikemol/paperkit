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

# Ζ·pkg·shape — the engine's own directory, FIRST on sys.path, and it must stay a per-module
# line rather than moving to paperkit/__init__.py: a package __init__ runs only when the
# package is IMPORTED, and these modules are also loaded as siblings by a caller that has
# already put its own directory ahead of ours.  render/checks/ ships its OWN bib.py, so a
# witness inserting that directory shadows the engine's parser and `from bib import
# dep_order` resolves to the wrong module.  MEASURED: removing these six lines reddened
# seven talk claims with "cannot import name 'dep_order' from bib (render/checks/bib.py)".
# The insert is a PRIORITY CLAIM, not a reachability fix — __init__.py handles reachability.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402  (Ω·config — the one configurable-resolution pipeline)
import bib  # noqa: E402  (the parser/data-model leaf)
import project as P  # noqa: E402  (the PROJECTOR — gate's only genuine need for project, the PROJECT invariant)


# Ζ·gate·exit (exit alphabet) — main()'s returns are TYPED, engine-aligned with discriminate/coherence
# (_REFUSE = 3), so a caller can tell "you asked wrong / I could not run" from "I ran and it failed":
#   0 pass · 1 RAN-AND-FAILED (an invariant did not hold) · _REFUSE CANNOT RUN — the gate could not
# even set up to evaluate this project (no/unloadable paper.toml, a bad --only key).  AVAILABILITY thus
# lives in the exit code (and in --json.available); WHICH invariant failed is NOT crammed into the code
# but read from --json, one field per invariant: RESOLVE → `bad` (the failing check keys), COVERAGE →
# `gaps` (a missing section, an uncited claim, a placement whose asset is missing or ambiguous), PROJECT → `project_ok`
# (prose ≡ projection).  The gate has NO resume, so there is no `2`.  A missing paper.toml used to
# crash with an unhandled traceback at exit 1 — indistinguishable from a real failure, so a consumer
# read "the tool is missing / this is not a project" as "the paper is broken" (summit ask-typed-gate-exit).
_REFUSE = 3


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
REGISTRY = [SAFE, WITHOUT_K, JOBS, JSON, ONLY, INVARIANTS, P.TARGET, P.GENRE, P.GAMMA, P.OBSERVE, P.CHECK, resolver.PATH]


def cited_keys(prose: str) -> set:
    # Citations live in prose, not in emitted code blocks — strip fenced blocks so
    # an example containing `@misc{…}` is not misread as a citation [@misc].
    prose = re.sub(r"```.*?```", "", prose, flags=re.S)
    # A `raw` placement is document syntax the engine did not construct, so it can
    # forge the same markers.  The projector brackets it (project.RAW_OPEN/CLOSE)
    # precisely so the shield fencing already gives code extends to it.
    prose = re.sub(r"<!-- paperkit:raw -->.*?<!-- /paperkit:raw -->", "",
                   prose, flags=re.S)
    # A citation materializes as a pandoc/web [@key] OR a footnote-target [^key] marker
    # (its document-end [^key]: definition names the same key) — count both as cited.
    #
    # Λ·key·graded — `/` is IN the charset, so a key may be PARAMETERISED as
    # `family[/subfamily]/argument`.  Without it a graded key cites as its own first segment:
    # `[@f/A]` scans as a citation to `f`, which is simultaneously an undefined citation AND a
    # "tagged section but not cited" coverage gap for `f/A` — two symptoms, one cause, and
    # neither of them names the charset.  Admitting `/` is what lets the claim-DAG SEE the
    # family axis (`rests-on` edges and coverage become family-aware) instead of the parameter
    # hiding inside the check string, where only the witness can read it.
    #
    # The two markers carry DIFFERENT termination risk, which is why only one is guarded:
    # `[^key]` is DELIMITED by its closing bracket, so widening the class cannot over-run.
    # `@key` is UNDELIMITED — it ends at the first character outside the class — so every
    # character added to the class extends how far it reaches.  A TRAILING `/` is therefore
    # stripped: a citation at a clause boundary ("[@f/A]/") must not bind the separator, and a
    # key with an empty last segment is not a key the walk can resolve anyway.  INTERIOR `/`
    # is kept — that is the parameter axis itself.
    return ({k.rstrip("/") for k in re.findall(r"@([A-Za-z0-9][\w.:/-]*)", prose)}
            | set(re.findall(r"\[\^([A-Za-z0-9][\w.:/-]*)\]", prose)))


def main(argv: list) -> int:
    config.apply_args(argv, REGISTRY)     # Ω·config: capture args (arg overrides env), process-local
    pos = config.positionals(argv, REGISTRY)
    project_dir = Path(pos[0]).resolve() if pos else Path.cwd()
    as_json = config.resolve(JSON)                   # structured stdout (human lines suppressed)

    # Ζ·gate·exit — CANNOT RUN is not RAN-AND-FAILED.  The boundary is not "did tomllib raise" but
    # "does the config ASSEMBLE INTO A GATEABLE PROJECT": no paper.toml, malformed TOML, no [paper]
    # table, or a declared INPUT (a warrant bib / the rubric) that does not exist.  Any of these →
    # REFUSE (_REFUSE), because the gate could not set up — and CRUCIALLY the verdict must NOT be the
    # downstream "not built — run paperkit-project" line: that predicate measures only a MISSING out
    # and would actively MISDIAGNOSE an unusable config as staleness, looping a consumer into a
    # projector that cannot help (A67 — a verdict may not assert more than it measured; summit
    # friction-cannot-gate-guard-misses-unloadable-config).  A stale-but-buildable doc is a genuine
    # ran-state (exit 1, below) reachable ONLY once the config's inputs exist.
    def cannot_run(reason):
        if as_json:
            print(json.dumps({"available": False, "reason": reason, "pass": False}, indent=2))
        print(f"paperkit-gate: CANNOT RUN — {reason}", file=sys.stderr)
        return _REFUSE
    ptoml = project_dir / "paper.toml"
    try:
        raw = tomllib.loads(ptoml.read_text())
    except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
        return cannot_run(f"no or unloadable paper.toml at {project_dir} ({e})")
    if "paper" not in raw:
        return cannot_run(f"paper.toml at {project_dir} has no [paper] table — not a gateable project")
    pol, custom = raw.get("paper", {}), raw.get("checks", {})   # project policy + custom check types
    safe = config.resolve(SAFE, pol)                 # zero-postulate: uncited placements FAIL
    without_k = config.resolve(WITHOUT_K, pol)       # forbid two cited claims sharing a witness
    inv_only = config.resolve(INVARIANTS)            # Ζ·starlark: the invariants NODE (no per-check resolve)
    # The bib IS the makefile: a project's distinct checks are independent targets, so the gate
    # runs them concurrently (default = all cores; jobs=1 forces serial).
    jobs = int(config.resolve(JOBS) or (os.cpu_count() or 4))

    def info(msg):              # human success lines — suppressed under --json
        if not as_json:
            print(msg)
    cfg = bib.load_config(project_dir)
    # A declared INPUT that does not exist means the config cannot assemble a gateable project — the
    # gate CANNOT RUN, not "ran and failed" (Ζ·gate·exit): warrants naming a missing .bib, or a
    # missing rubric.  This is measured BEFORE the built-artifact check so an unusable config never
    # reaches (and never gets misreported by) the "not built — run paperkit-project" line.
    missing = [str(b) for b in cfg["bibs"] if not b.exists()]
    if not cfg["rubric"].exists():
        missing.append(str(cfg["rubric"]))
    if missing:
        return cannot_run(f"declared input(s) do not exist: {', '.join(missing)}")

    F, primary = {}, cfg["bibs"][0].name
    for b in cfg["bibs"]:
        F.update(bib.parse(b, cfg["consumer_fields"]))

    # Ζ·starlark — the LEAF of the recursive check target: resolve ONE claim's check and exit.
    # A project's gate (the node) is this over every claim ∧ the project invariants; a Bazel
    # check target is exactly this leaf, so the bib's claim-DAG runs as the build graph.
    only = config.resolve(ONLY)
    if only:
        if only not in F or not F[only].get("check"):
            # A key naming no check is a caller BUG, not a ran-and-failed verdict.  Under --json it
            # must still SPEAK — the leaf was addressable but MUTE (info() is suppressed and the
            # --json block sits past the early return), so a machine consumer saw an exit code and
            # empty stdout and could not tell refuse from pass.  That silence is why result: could
            # not delegate per-warrant: the address existed, the ANSWER did not.
            if as_json:
                print(json.dumps({"available": False, "reason": f"no check for claim {only!r}",
                                  "pass": False, "only": only}, indent=2))
            print(f"paperkit-gate: no check for claim {only!r}", file=sys.stderr)
            return _REFUSE
        v = resolves(F[only]["check"], project_dir, custom)
        # Ω·verdict — the leaf answers the same TRISTATE the node does (ask-result-tristate): a
        # check that could not be EVALUATED is not a refutation of the claim.  Collapsing
        # unresolvable to FAIL here would make an unreachable sibling look like a failing one.
        if as_json:
            print(json.dumps({"available": not v.is_unavailable(), "pass": bool(v.passed),
                              "only": only, "check": F[only]["check"],
                              "reason": None if not v.is_unavailable() else (v.why or "check unresolvable")},
                             indent=2))
        info(f"paperkit-gate: {only} {'ok' if v.passed else 'FAIL'} — {F[only]['check']}")
        if v.is_unavailable():
            return _REFUSE
        return 0 if v.passed else 1

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

    # SAID-SOMETHING — a claim projected into PROSE must carry prose, never fall back to its bare
    # KEY.  bib.parse matches `claim` with a brace-balanced regex, so a claim whose closing brace
    # lands a field late (the value runs on and cannot close within the entry) simply does NOT
    # match: the field is ABSENT rather than malformed, and the projector (project.py:119-123)
    # falls back to `title`, then to the KEY.  PROJECT/RESOLVE/COVERAGE all still hold — the
    # committed prose IS that projection, `check` parsed, the claim is cited — so a placeholder
    # reading its own bibtex key (e.g. `Add-privacy.`) ships inside a gated document with nothing
    # asserting that a projected claim said anything.  A section-tagged prose claim with neither
    # `claim` nor `title` would render as its key; refuse it.  An emit PLACEMENT projects a BLOCK
    # (not a sentence) and a reference carries a title, so both are exempt by construction.
    mute = sorted(k for k, f in F.items()
                  if f.get("section") and not f.get("emit")
                  and not f.get("claim") and not f.get("title"))
    if mute:
        print(f"paperkit-gate: {len(mute)} claim(s) would project as their bare KEY, carrying no "
              f"prose — {mute} — a claim projected into prose must SAY something (a dropped `claim`, "
              f"likely a closing brace that lands a field late)", file=sys.stderr)
        rc = 1

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
        unresolvable: list = []
    else:
        distinct = sorted({F[k]["check"] for k in to_verify})

        def resolve1(c: str):
            return resolves(c, project_dir, custom)   # the Verdict — bad/unresolvable split below

        if len(distinct) > 1 and jobs > 1:
            with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
                cache = dict(zip(distinct, ex.map(resolve1, distinct)))
        else:
            cache = {c: resolve1(c) for c in distinct}

        # A non-passing check splits by KIND (ask-result-tristate): a check that RAN and did not hold
        # is `bad` (a real failure — the gate reds); one that could not be EVALUATED (an unreachable
        # sibling, a verb this engine lacks) is `unresolvable` — surfaced so a caller reads WHY, not
        # just not-pass, and does not read "I could not check it" as "the claim is false".  Both
        # keep the premise from certifying (fail-closed), but only across a repo boundary; in-repo
        # every sibling is present so `unresolvable` is empty.
        # Ζ·unavailable·why — test the STATE, not object identity: a cannot-run that carries the
        # delegate's reason is a distinct object, and `is UNAVAILABLE` would file it under `bad`,
        # turning "I could not check this" back into "the claim is false" — the exact conflation
        # the tristate exists to prevent.
        bad = sorted(k for k in to_verify if not cache[F[k]["check"]].passed
                     and not cache[F[k]["check"]].is_unavailable())
        unresolvable = sorted(k for k in to_verify if cache[F[k]["check"]].is_unavailable())
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
    if unresolvable:
        # ask-result-tristate — the check could NOT be evaluated (unreachable sibling, unknown verb),
        # not refuted.  Named distinctly from FAILED so a caller reads "I could not check this", not
        # "the claim is false" — and the gate still reds (fail-closed: an unverified claim cannot ship).
        for k in unresolvable:
            v = cache[F[k]["check"]]
            # Report the incomplete Π, not the sum: name WHO could not run and WHAT is missing,
            # so the reader is pointed at the fix.  The disjunction this replaced ("unreachable
            # delegate or unknown verb") named everything it might have been and nothing it was.
            why = (f"{v.owner}: {v.why}" if v.owner and v.why else
                   v.why or "unreachable delegate or unknown verb")
            print(f"paperkit-gate: check UNRESOLVABLE for [@{k}]: {F[k]['check']} — {why}; "
                  "NOT a refutation", file=sys.stderr)
        rc = 1
    if inv_only:
        info(f"paperkit-gate: invariants node — {len(to_verify)} claim check(s) deferred to the leaf targets")
    elif not undefined and not bad and not unresolvable and not dangling:
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
    # The asset resolves against BOTH legitimate anchors — project_dir (assets beside the warrants)
    # then out.parent (assets beside the output) — via bib.emit_anchors, the SAME resolver
    # project.py's emit_block reads, so the gate and the projector cannot diverge (that split WAS
    # the two-different-paths bug).  ABSENT when neither holds it; AMBIGUOUS, and NOISY, when both
    # distinct anchors do — the projector reads the first, so which content ships would otherwise
    # be a silent coin-flip.  (629af60 keyed on project_dir alone and broke the mirror layout.)
    for k, f in F.items():
        if not f.get("emit"):
            continue
        hits = bib.emit_anchors(cfg, f["emit"])
        if not hits:
            gaps.append(f"placement [@{k}] emits {f['emit']} — the artifact is ABSENT, so the "
                        f"document renders a placeholder comment where the evidence should be")
        elif len(hits) > 1:
            differ = len({p.read_bytes() for p in hits}) > 1
            detail = ("DIFFERENT content — the projector reads the first, the second is silently "
                      "ignored" if differ else "identical content, but the layout is ambiguous")
            gaps.append(f"placement [@{k}] emits {f['emit']} — AMBIGUOUS: it resolves at BOTH "
                        f"{' and '.join(str(p) for p in hits)} ({detail}); keep the asset at ONE "
                        f"anchor (beside the warrants OR beside the output, not both)")
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
            "available": True,
            "document": out.name, "pass": rc == 0, "project_ok": proj_ok,
            "verified": len(to_verify), "undefined": undefined, "bad": bad,
            "unresolvable": unresolvable,             # ask-result-tristate: could-not-evaluate ≠ failed
            "dangling": sorted(list(e) for e in dangling),
            "sections": secs, "gaps": gaps,
            "postulates": sorted(k for k, f in F.items()
                                 if f.get("section") and k not in cited and bib.is_placed(f)),
            "collapses": collapses,
        }, indent=2))
    print("paperkit-gate: PASS" if rc == 0 else "paperkit-gate: FAIL", file=sys.stderr)
    return rc


def _cli():
    """Console-script entry point (pyproject [project.scripts]).

    A wheel cannot point an entry point at `__main__`, so the same one-liner is named here
    and reused below — one call site, not two implementations that can drift.
    """
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    _cli()
