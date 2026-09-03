---
name: struct-tools
description: The structural readers for paperkit's artifacts — ask the tool that owns the artifact, never grep its bytes.
---

# struct-tools — ask the owner, don't read the bytes

⚑ **ADOPTED, NOT INVENTED.** The routing-table shape and the two PreToolUse hooks that
read it are substrate's (`scripts/hook_structural_query.py`, `scripts/hook_no_chaining.py`,
symlinked from `scripts/`). Only this table is paperkit's, because only the artifacts differ.
**Ownership is not claimed.**

## Why this repo needs it particularly

paperkit's whole thesis is that a document is a **projection of a verified claim-DAG** — so
every artifact here has a structural owner *by construction*, and a textual query about one is
asking the wrong layer on purpose. The engine refuses an unwitnessed sentence; the agent
working on it should not answer a structured question with `grep`.

Measured, 2026-08-28: a hand-rolled regex census over 45 boundary suites reported **2** suites
hardcoding a behavior count. The true answer is **4** — the pattern required the literal to be
followed by `behavio|arm|check`, so it missed `PASS (6 structural, 1 delta)`. The error was the
*method*, not the pattern: a question about which suites hardcode a summary count is a question
about their structure, and it was answered by reading their bytes.

## The table

| artifact | tool | run bare to list its modes | claims |
|---|---|---|---|
| the claim-DAG (warrants, checks, `rests-on`, `from`) | `paperkit/bib.py` | `python3 paperkit/bib.py` | `.bib` |
| a project's config + declared knobs | `paperkit/config.py` | `python3 paperkit/config.py` | `.toml` |
| Python def-sites (the mutation surface) | `tools/def_sites.py` | `python3 tools/def_sites.py` | `.py` |
| a witness's engine-module closure | `tools/closure.py` | `python3 tools/closure.py --help` | — |
| the engine's import DAG | `tools/imports.py` | `python3 tools/imports.py --check` | `dag.bzl` |
| a check's verdict + grade | `tools/read_grade.py` | `python3 paperkit/gate.py --help` | `.json` |
| adequacy grades / sensitivity | `paperkit/discriminate.py` | `python3 paperkit/discriminate.py --help` | `__dcalc` |
| the document projection | `paperkit/project.py` | `python3 paperkit/project.py --help` | `.md` |
| the deck segmentation | `paperkit/project.py` | `python3 paperkit/project.py --observe --help` | `.tsv` |
| Bazel targets and deps | `bazel query` | `bazel query --help` | `.bazel` |
| decision coverage | `tools/decisions.py` | `python3 tools/decisions.py` | — |
| effective grades (clamped) | `tools/effective.py` | `python3 tools/effective.py` | — |

## The rule

If you have a question the tooling does not answer directly, **fix the tooling** — do not
reach for `grep`. There is no exception list, and its absence is the design: a gap in the
toolkit is not a category of question that is inherently textual.

⚑ **And a paperkit absence claim is cleared by a MUTATION, not a search.** The question is
almost always *"can this check fail?"*, which no reader can answer. See `tools/absence_audit.py`
and `Λ·audit·provenance`: mutate the mechanism out, don't source-scan.


⚑ **A CLAIM MUST BE NO WIDER THAN ITS TOOL'S GLOSS.** `.bzl` was claimed by `bazel query`,
whose own gloss reads *"Bazel targets and deps"* — the BUILD GRAPH. A `.bzl` file is Starlark
SOURCE, and no query mode reads it, so *"where is this rule implemented?"* was refused with
nowhere to go: `--output=build` returns instantiations (measured: 4.9 MB for one paper query),
never the `rule()` call. Dropped 2026-09-01; an unclaimed suffix falls through to `Read`, which
is what this document already prescribes. `.bazel` stays — a `BUILD.bazel` IS target
declarations, so there the claim and the gloss agree.

A gate that blocks without routing is half a gate (substrate's `cat >> doc.md`, which is why
`mdstruct` grew `--append-section`). The tell is a row whose gloss already states the limit its
`claims` cell contradicts — so read the gloss as the claim's BOUND, and widen the tool before
widening the row. The tool that would earn `.bzl` back is a Starlark source reader; `pycodemod
--source` is the same capability one language over.

A comment is prose the engine does not gate. Nothing in `//:hook` reads one, so a comment is the
one artifact in this repo that can assert a falsehood indefinitely. Two rules, one shape:
**a comment's TENSE declares whether it is still under check.**

⚑ **`Λ·comment·tense` — A PRESENT-TENSE COMMENT IS A LIVE CLAIM.** Measured 2026-09-02 in
`tools/*.bzl`: of the comment sites carrying a number, the ones that had rotted were present-tense
(*"paper's grid **is** 52,584 cells"* — live value 71,154, 26% low), and the ones that had not
were past-tense or explicitly marked superseded (`calc.bzl` *"used to bottom at 2,981,888 bytes"*,
*"the **old** 2048 floor"*). This is structural, not luck: **a past-tense claim about a superseded
state cannot go stale** — it is a historical record, correctly typed, and a later change does not
touch it. A present-tense claim is an assertion about the tree as it now stands, and every commit
is a chance to falsify it. So write a fact about the current tree in the present tense **and date
it**; write a fact about why something changed in the past tense. The failure mode is a historical
record written in the present tense — it reads as a live assertion, invites no check because
nothing depends on it, and misleads precisely the careful reader who trusts it.
`paperkit/grader.py`'s `unmeasured_reads` docstring is the non-numeric instance: it says `.json`
and `.bzl` are not `MUTABLE_SUFFIXES`, true when the defect was found and false since
`paperkit/layout.py` admitted both. The prose is a correct account of *why the axis exists*; only
its tense is wrong.

⚑ **AND A NUMBER NO ARGUMENT DEPENDS ON IS A NUMBER NOTHING WILL CHECK.** Both `52,584` sites
survive the correction — one argument turns on a ratio, the other on an inversion, and neither
needs the magnitude. That is exactly why it rotted unnoticed. An illustrative magnitude is
decoration on a correct predicate ([[verified-claim-unverified-furniture]]): date it, or drop it.

⚑ **`Λ·cite·remeasure` — A CITED COMMENT IS A LIVE PREMISE.** The dual, and the worse half:
**a stale number invites checking; a stale conclusion invites deference.** `.bazelrc`'s
*"Containerising the ACTION was never the same as containerising the PATH"* was cited in this repo
as authority for a design direction (remote execution, a worker image, a cross-repo conversation).
One command refuted the scope it was read with. It carried no number, so nothing looked checkable,
and it read as settled — the discipline therefore runs **opposite to confidence**: the more a
comment reads as authority, the more it needs a date and a scope.

⚑ **AND THE CHECK BELONGS AT CITATION, NOT AUTHORSHIP.** That was not a writing failure — the line
was true of what it described. It was a citation failure, and citation is where the check is cheap:
one reader, one claim, one command. This repo already requires re-verifying a claim before it
LEAVES the repo ([[verify-outward-artifacts]]); a comment cited as a premise is also leaving —
**it is leaving the past and entering a live decision.** Re-measure it in the turn that cites it,
or attribute it (*"the comment says…"*) rather than asserting it in your own voice.

⚑ **SHOULD A CONCLUSION NAME ITS REFUTATION CONDITION? YES — one clause, and only on conclusions.**
Had the `.bazelrc` line read *"(checked under the default strategy; `--config=mutant` not tried)"*,
the next reader inherits an open question instead of a closed door. That is [[declared-partial]] at
comment scale: the defect is never partialness but UNDECLARED partialness, and a conclusion whose
scope is unstated is unfalsifiable as written — it cannot be refuted, only outgrown, silently. The
bound that keeps it light is that it applies to a comment which CLOSES AN OPTION (*"X was never
Y"*, *"this cannot work"*, *"the fix is Z and not W"*), never to one describing mechanism.
Descriptions are checkable against the code by anyone reading it; conclusions are not — they name a
road not taken, and the evidence for them lives only in the session that took the other one. Naming
what was and was not tried costs a parenthesis, and is the whole difference between a record and a
wall.
