# paperkit

*A paper is a projection of a verified claim-DAG — write claims, not prose.*

## What paperkit is

Paperkit treats a document as the projection of a verified claim-DAG: you write claims, not prose [@rm-pitch], and each claim carries a machine-checkable verifier [@rm-verifier]; an unverified sentence does not project, so the document cannot overclaim [@rm-noship]. This README is itself such a projection — its claims are the root warrant set, and its examples are gated assets [@rm-selfhost].

## The model: a claim is a bibliography entry

A claim is one bibliography entry — a statement, the rubric section it belongs to, the claims it depends on (which set prose order and connective glue), and its check [@rm-model]. One entry reads like this [@rm-model-eg].

```bibtex
@misc{drift,
  section = {engine}, from = {projector},
  claim   = {the gate rejects any prose that has drifted from its projection},
  check   = {cmd:true}
}
```

And an entry may carry these fields, a project these paper keys — generated from the parser's own field set (bib._SCALAR, _LIST) and the keys load_config reads, so this table cannot drift from what the engine actually does [@rm-fields].

<!-- paperkit:raw -->
A bibliography entry (a warrant, or a `references.bib` citation) may carry these fields. Generated from the parser's own field set, so it cannot drift from the code.

| field | what the engine does with it | kind |
| --- | --- | --- |
| `title` | a reference's title, used as its citation text (or, on a warrant, its sentence) | reference |
| `author` | a reference's short author, in its citation parenthetical | reference |
| `year` | a reference's year, in its citation parenthetical | reference |
| `note` | parsed but consumed nowhere — reserved, engine-inert | inert |
| `section` | the rubric section this claim belongs to (grouping; a placed postulate marker) | warrant |
| `claim` | the assertion's prose — projected as the claim's sentence | warrant |
| `check` | the machine verifier (type:target) the gate resolves and Δ grades | warrant |
| `glue` | a connective added across a `from` prose edge (legacy weave override) | warrant |
| `join` | the full inter-clause connector to the previous claim (overrides glue/move) | warrant |
| `move` | a typed rhetorical move: its default connector, gated against the section scheme | warrant |
| `emit` | an on-disk asset placed as a block instead of a sentence | warrant |
| `as` | the renderer for `emit` — table, image, code, or raw (else inferred from the suffix) | warrant |
| `mem` | engine-inert; projected to a Bazel memory reservation for the check | warrant |
| `link` | an expound-rung footnote (a technical name, or a ∂² long-edge discharge) | warrant |
| `depth` | renders the claim as a nested (indented) proof-step list item | warrant |
| `tier` | the check's enforcement tier (Ζ·tier) — sandbox (hermetic, mutation-swept; default), local (host-coupled, uncached), or toolchain (host toolchain, cached + stamped with the toolchain fingerprint); a non-sandbox check is gated but not swept | warrant |
| `entails` | SCOPE (Ξ·entails) — how much of its claim this check reaches: `fragment` (the witness covers PART of what the sentence asserts) or `full` (default when absent). Never clamps the grade — an author's declaration that lowered its own number would be self-fulfilling — and coherence's scope face reds a `fragment` declared over a witness nothing flips | warrant |
| `from` | prose-order edge: topological ordering + glue adjacency (general→specific) | warrant |
| `rests-on` | grounding edge: effective-grade clamping + citation provenance (NOT prose order) | warrant |
| `reads` | the check's declared cross-package footprint — staging + audit tokens (Ζ·foot) | warrant |
| `consumes` | sibling warrant keys whose verdict RECORD this check reads (records-as-deps: the sibling runs once and is memoized; its verdict.json is a declared bazel input, exported in PAPERKIT_CONSUMED_RECORDS as key=path — Ρ·wcag·oracle-edge) | warrant |

A project's `paper.toml` `[paper]` table may set these keys. Generated from the keys `load_config` reads.

| key | what it controls |
| --- | --- |
| `title` | the document H1 heading |
| `subtitle` | an italic subtitle line under the title |
| `rubric` | path to rubric.tsv (section keys → titles → optional scheme) |
| `warrants` | the list of `.bib` claim-DAG files to parse |
| `out` | the output markdown path written |
| `numbered` | number the section headings (`## 1. …`) |
| `paragraph` | `claim` = one paragraph per claim; `woven` (default) = join a section into prose |
| `references` | emit the trailing References section |
| `adequacy` | engine-inert; emits a Bazel Δ-adequacy test for the project |
| `consumer_fields` | extra bib scalar fields this project's downstream consumer owns — carried verbatim, consumed by no engine invariant (a declared field is quiet in the unknown-field warning; an undeclared one is still named) |
<!-- /paperkit:raw -->

## The two commands

Two commands do the work — project turns the claims into the document, and gate verifies it [@rm-cmds]. You run them like this [@rm-cmds-eg].

```sh
python3 paperkit/project.py paper   # claims -> paper/paper.md (the projection)
python3 paperkit/gate.py    paper   # verify: projection-stable, checks pass, coverage
```

The gate enforces three invariants: the committed prose equals its projection, every cited claim's check passes, and every section is covered both ways [@rm-cmds-inv].

## The check-resolver

A verifier is named type:target, and one type ships built in per verb — exists, execs, parses, concurs, imports [@rm-resolver] --- the built-ins are [@rm-resolver-tbl].

<!-- paperkit:raw -->
| type | verb | passes when |
| --- | --- | --- |
| `file:<path>` | exists | the artifact exists |
| `cmd:<script>` | execs | the script exits `0` |
| `result:<project>[#<claim>]` | parses | the sibling project's gate verdict parses green --- for the whole project, or for the ONE named warrant |
| `agree:<p>\|\|\|<q>` | concurs | the independent producers all exit `0` and emit identical output |
| `concept:<key>` | imports | the project's concept library --- else the engine's --- certifies that key |

**When the mutation grade adds nothing.** If an `agree:` check's second producer is a *reference computation* --- a theorem or closed form the result must match --- rather than a *file read*, the agreement is already the whole falsification surface: a wrong result disagrees with the reference directly, so there is no separate "could this claim's data be corrupted" question for the mutation sweep to answer. paperkit's grade earns its keep when the oracle is a file whose *mutability* is the question, not when it is another computation.
<!-- /paperkit:raw -->

Cmd is the universal escape hatch every check reduces to, and a new domain adds named types in paper.toml without touching the engine [@rm-resolver-cmd]. A new domain declares them like this [@rm-resolver-eg].

```toml
[checks.agda]
cmd = "agda --safe {target}"

[checks.pytest]
cmd = "pytest -k {target}"
```

A check ALSO names how a claim is verified, which the footnote and plain render targets read as a provenance note — a cmd is machine-verified, an agda claim Agda-proved, and a premise a classical premise carried WITHOUT a machine check, surfaced honestly as not-machine-checked rather than dressed as a passing verb — so premise is a provenance KIND, not a resolving verb at all, and the built-in verb set stays closed against it [@rm-resolver-premise].

## Grading check adequacy (Δ)

A passing check only proves a sentence named a verifier, not that the verifier entails it — so discriminate.py grades how much each check can actually fail [@adequacy-pitch] --- the grades are [@rm-delta-tbl].

<!-- paperkit:raw -->
| grade | meaning |
| --- | --- |
| `imported` | delegated to a separately-gated owner — a sibling's verdict, or the library's certificate |
| `behavioral` | proven falsifiable — a single-file mutation flips it red |
| `existence` | `file:` of a contingent artifact — presence, not content |
| `indeterminate` | no generic mutation flips it — vacuous, or a negative-assertion check |
| `vacuous` | provably can't fail — `file:` of an input the build already requires |
| `broken` | does not pass in a pristine sandbox — the repo is not green |
<!-- /paperkit:raw -->

You run it as a report or as a gate, like this [@rm-delta-cmds].

```sh
python3 paperkit/discriminate.py paper                            # report grades
python3 paperkit/discriminate.py --min-strength behavioral paper  # gate on weak checks
```

Every tool ships its behavioral boundaries as the triple ⟨P, F, δ⟩ — a minimal pass, a minimal flag, and the minimum delta that flips the verdict [@rm-boundaries].

## Layout

The repository is the engine, the self-hosting paper, and this generated README [@rm-layout].

```text
paperkit/        the engine — project.py, gate.py, discriminate.py (domain-free)
  tests/         behavioral-boundary examples ⟨P, F, δ⟩ per tool
paper/           the self-hosting paper (warrants.bib, rubric.tsv, paper.toml, checks/)
assets/          README example assets — emitted verbatim and gated
README.md        this file — itself a paperkit projection of the root warrant set
```

## Local CI

Checks run locally as a pre-commit githook — every commit runs bazel test //:hook (gating both documents as per-claim check targets) and the Delta adequacy grade, keeping the tool boundaries intact [@rm-ci]. A fresh clone enables it once, since git cannot auto-enable a hook from a commit [@rm-ci-enable].

```sh
git config core.hooksPath .githooks   # enable the local-CI pre-commit hook (once per clone)
```

## Status

A working spike — the engine projects and gates, the self-hosting paper is green, discriminate.py grades check adequacy, and this README is itself a projection [@rm-status]. Next are render-to-PDF (pandoc/docx) and a packaged CLI (paperkit init/project/gate/build) [@rm-next].
