#!/usr/bin/env python3
"""Η·hook·grid (H3) — the //:hook member list is HAND-TRANSCRIBED, and this makes its drift LOUD.

⚑ WHY THE LIST STAYS HAND-MAINTAINED.  `BUILD.bazel`'s own class note says the members are a
per-project x per-target-kind GRID that `tools/bibtex.bzl` already knows in full, transcribed by
hand into a file the generator cannot see — so "all 23 members can fall out this way, silently",
and three instances are recorded (Ζ·hook-rot for config, Ρ·talk·hook·wire for the talk, and
boundaries' adequacy, caught 2026-09-09).

The obvious repair — have the generator emit a per-project `test_suite(name = "all")` and reduce
//:hook to `@paperkit_*//:all` labels — CANNOT BE TAKEN, and the reason is structural rather than
incidental.  `paperkit/tests/boundaries_check.py` is what proves the hook COMPLETE, and it does so
by comparing two INDEPENDENT TEXTUAL SOURCES: the literal member list scraped out of BUILD.bazel,
against the `bib.project` tags scraped out of MODULE.bazel.  It then asserts by SET-EQUALITY
(boundaries_check.py:92-93) that every member matches
`@\\w+//:(gate|adequacy|cohere|decisions)$` plus exactly `//canary:canary` — an assertion a
`:all` label fails by construction.  That set-equality was chosen deliberately over a
project-shaped-or-not filter, because a filter "would silently admit any stray member".

So the completeness proof's soundness COMES FROM the list being explicit, enumerable, and written
somewhere the generator cannot reach.  Generating it would let the audited thing supply its own
audit — [[instrument-vs-gate]] — in a repo whose recurring defect is a green that measures the
census rather than the tree.

⚑ THEREFORE THIS GATE REMOVES THE **SILENTLY**, NOT THE HAND-MAINTENANCE.  The duplication is kept
ON PURPOSE (it is what makes bnd-check's two sources independent); what is added is a check that
the two copies AGREE.  Adding a per-project target kind still requires a human edit — it simply
can no longer be forgotten without a red.

WHAT IT COMPARES.  The emission rules, read from tools/bibtex.bzl and reproduced here as the
ONLY hand-copied thing (a rule set of four lines, versus a 24-line member list):

    gate       every wired project                      (bibtex.bzl:932, unconditional)
    adequacy   adequacy = True                           (bibtex.bzl:985)
    cohere     emerge = True                             (bibtex.bzl:892  `emerge and (calc_claims or imported_cert)`)
    decisions  emerge = True                             (bibtex.bzl:906  `emerge and dcns`)

`cohere`/`decisions` carry a second conjunct (non-empty calcs / decision records) that is true for
any project with claims; a project with none would have no gate either.  If that ever ceases to
hold, this gate reds and names the project — which is the correct failure direction.

    python3 tools/hook_grid.py          # exit 0 = the transcription matches the declarations
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Ζ·canary — the ONE non-project member (the harness positive control).  Named, not filtered, for
# the same reason bnd-check uses set-equality: an unnamed residual admits any stray member.
NON_PROJECT = {"//canary:canary"}

# ⚑ HOOK-MEMBERSHIP EXEMPTIONS — DECLARED HERE BECAUSE THEY ARE DECLARED NOWHERE ELSE.
#
# The generator emits `gate` for EVERY wired project, unconditionally and regardless of tier
# (bibtex.bzl:932) — there is no `local ⇒ omit from //:hook` rule anywhere in the build.  So the
# omission of these three is a HUMAN POLICY recorded only in prose, and reading it back off the
# `tier` attribute would be this gate INVENTING a rule the tree does not state.  Naming them here
# makes the policy attributable and reviewable: each exemption carries WHY, and an unlisted absence
# is a red.
#
# ⚑ These are audit finding 5, still open — not settled facts.  `prototypes/README.md:78` logs the
# setup/report pair as open operator decision G4, and Ω (tier-is-a-placement-not-a-constraint) is
# the live question of whether `local` names a constraint at all.  When Ω resolves, these entries
# are the first thing to revisit: two of the three were set to `local` by this session (Α), on an
# analogy rather than a measured dependency.
HOOK_EXEMPT = {
    # ⚑ CORRECTED 2026-09-09 (Ω-F7): this reason previously read "open operator decision G4" as
    # though G4 AUTHORISED the exemption.  It does not.  G4 (prototypes/README.md:78) reads: "setup
    # and report are outside //:hook.  BUILD.bazel:102-104 names this exact failure mode for the
    # talk and then wires it." — i.e. G4 FLAGS these two as the remaining UNFIXED instances of a
    # failure mode already fixed once.  "Operator decision" marks it as NEEDING a decision, not as
    # having received one.  G4 is also half stale: it names `report`, which Α has since wired.
    # So this exemption is UNJUSTIFIED-BUT-DECLARED: it records the status quo, not a warrant for it.
    "@paperkit_setup//:gate":  "tier=local (shells systemd-run, probes live /proc,/sys); ⚑ NOT "
                               "authorised — G4 flags this as an unfixed gap, see Ω-F7",
    # ⚑ UPDATED 2026-09-09 (Ω-F6): the reason is no longer an analogy — it is measured.  6 of 16
    # warrants were freed to sandbox tier and verified hermetic.  The 10 that remain all reach
    # SIBLING projects through gen.py (which subprocesses discriminate/gate), so they are Ω-F5-shaped:
    # the constraint is a source-tree path, not host access, and `local` does not supply it.
    "@paperkit_report//:gate": "tier=local for 10 of 16 warrants; they reach sibling projects via "
                               "gen.py, so Ω-F5 (execroot vs source tree) blocks them, not host need",
    # ⚑ Ω-F1 CORRECTED 2026-09-09: this reason previously said stable.sh fetches over the network.
    # It does not.  Containerfile.base is digest-pinned (python@sha256:…) and isolates the
    # non-deterministic apk layer; Containerfile is FROM localhost/… and COPY-only, so the proof
    # build touches no network.  The dependency is podman itself — NAMED, so toolchain-SHAPED — and
    # Ω-F2 is why it cannot be promoted yet: toolchain_status.sh emits no PODMAN key, so a
    # toolchain-tier image would cache against a fingerprint that does not track it.
    "@paperkit_image//:gate":  "tier=local; the 3 podman warrants need a PODMAN + base-digest stamp "
                               "key before toolchain tier is sound (Ω-F2)",
}


def declared(module: str) -> dict:
    """{repo: set(kinds)} the generator WOULD emit, from each bib.project tag's flags."""
    out = {}
    for line in module.splitlines():
        if "bib.project(" not in line:
            continue
        m = re.search(r'name\s*=\s*"([^"]+)"', line)
        if not m:
            continue
        kinds = {"gate"}                                    # unconditional
        if "adequacy = True" in line:
            kinds.add("adequacy")
        if "emerge = True" in line:
            kinds |= {"cohere", "decisions"}
        out[m.group(1)] = kinds
    return out


def transcribed(build: str) -> set:
    """The //:hook member list, verbatim.

    ⚑ DO NOT USE A NON-GREEDY `\\[(.*?)\\]` HERE.  bnd-check does (boundaries_check.py:34) and it is
    WRONG: the member list's own comments contain wiki-style refs like [[place-by-ownership-not-need]]
    (BUILD.bazel:191), so the first `]` the non-greedy match finds is INSIDE a comment, four lines
    above the real end of the list.  Measured 2026-09-09: that scrape captures 6,380 chars and 24
    members, while `bazel query tests(//:hook)` reports 25 — it silently drops
    `@paperkit_library//:decisions` (BUILD.bazel:194), the very member whose omission the surrounding
    comment was written to narrate.

    So the list is bracket-COUNTED from `tests = [` to its matching close, and only then scanned for
    quoted labels.  A label is `@repo//:target` or `//pkg:target`; a bracketed wiki-ref carries no
    quotes and cannot be mistaken for one, but the SLICE has to be right first.
    """
    i = build.find("tests = [", build.find('name = "hook"'))
    if i < 0:
        return set()
    i = build.index("[", i)
    depth, j = 0, i
    for j in range(i, len(build)):
        if build[j] == "[":
            depth += 1
        elif build[j] == "]":
            depth -= 1
            if depth == 0:
                break
    body = build[i + 1:j]
    return {t for t in re.findall(r'"([^"]+)"', body) if t.startswith("@") or t.startswith("//")}


def main() -> int:
    module = (ROOT / "MODULE.bazel").read_text()
    build = (ROOT / "BUILD.bazel").read_text()

    decl = declared(module)
    have = transcribed(build)
    if not have:
        print("hook-grid: could not find the //:hook test_suite member list in BUILD.bazel",
              file=sys.stderr)
        return 1

    emitted = {f"@{repo}//:{kind}" for repo, kinds in decl.items() for kind in kinds}
    want = (emitted - set(HOOK_EXEMPT)) | NON_PROJECT

    missing = sorted(want - have)   # the generator emits it; the hook does not run it
    extra = sorted(have - want)     # the hook names it; nothing emits it

    # An exemption that is no longer emitted is a STALE exemption — the policy outlived its subject,
    # which is the same silent-rot this gate exists to refuse, one level up.
    stale_exempt = sorted(set(HOOK_EXEMPT) - emitted)
    # An exemption whose target is ALSO in the hook is contradictory: it is both excused and run.
    contradicted = sorted(set(HOOK_EXEMPT) & have)

    if stale_exempt or contradicted:
        for t in stale_exempt:
            print(f"hook-grid: STALE EXEMPTION — {t}\n"
                  f"    HOOK_EXEMPT excuses it, but no bib.project tag emits it any more",
                  file=sys.stderr)
        for t in contradicted:
            print(f"hook-grid: CONTRADICTED EXEMPTION — {t}\n"
                  f"    HOOK_EXEMPT excuses it AND //:hook runs it; drop the exemption",
                  file=sys.stderr)
        return 1

    if missing or extra:
        for t in missing:
            print(f"hook-grid: MISSING from //:hook — {t}\n"
                  f"    the generator emits this target and local CI never runs it", file=sys.stderr)
        for t in extra:
            print(f"hook-grid: STALE in //:hook — {t}\n"
                  f"    no bib.project tag declares the flag that emits this", file=sys.stderr)
        print(f"\nhook-grid: the hand-transcribed //:hook grid has DRIFTED from MODULE.bazel's "
              f"declarations ({len(missing)} missing, {len(extra)} stale).  The list is "
              f"hand-maintained on purpose — it is one of bnd-check's two independent sources — so "
              f"the repair is to EDIT BUILD.bazel, never to relax this check.", file=sys.stderr)
        return 1

    print(f"hook-grid: //:hook matches MODULE.bazel — {len(decl)} project(s), {len(emitted)} "
          f"emitted target(s), {len(HOOK_EXEMPT)} declared exemption(s), "
          f"{len(NON_PROJECT)} harness member; {len(have)} transcribed")
    for t, why in sorted(HOOK_EXEMPT.items()):
        print(f"  exempt  {t}\n          {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
