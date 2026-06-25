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
  check   = {cmd:sh checks/drift-caught.sh}
}
```

## The two commands

Two commands do the work — project turns the claims into the document, and gate verifies it [@rm-cmds]. You run them like this [@rm-cmds-eg].

```sh
python3 paperkit/project.py paper   # claims -> paper/paper.md (the projection)
python3 paperkit/gate.py    paper   # verify: projection-stable, checks pass, coverage
```

The gate enforces three invariants: the committed prose equals its projection, every cited claim's check passes, and every section is covered both ways [@rm-cmds-inv].

## The check-resolver

A verifier is named type:target, and four types ship built in, one per verb — exists, execs, parses, concurs [@rm-resolver] --- the four built-ins are [@rm-resolver-tbl].

| type | verb | passes when |
| --- | --- | --- |
| `file:<path>` | exists | the artifact exists |
| `cmd:<script>` | execs | the script exits `0` |
| `result:<project>` | parses | the sibling project's gate verdict parses green |
| `agree:<p>\|\|\|<q>` | concurs | the independent producers all exit `0` and emit identical output |

Cmd is the universal escape hatch every check reduces to, and a new domain adds named types in paper.toml without touching the engine [@rm-resolver-cmd]. A new domain declares them like this [@rm-resolver-eg].

```toml
[checks.agda]
cmd = "agda --safe {target}"

[checks.pytest]
cmd = "pytest -k {target}"
```

## Grading check adequacy (Δ)

A passing check only proves a sentence named a verifier, not that the verifier entails it — so discriminate.py grades how much each check can actually fail [@rm-delta] --- the grades are [@rm-delta-tbl].

| grade | meaning |
| --- | --- |
| `vacuous` | provably can't fail — `file:` of an input the build already requires |
| `existence` | `file:` of a contingent artifact — presence, not content |
| `behavioral` | proven falsifiable — a single-file mutation flips it red |
| `indeterminate` | no generic mutation flips it — vacuous, or a negative-assertion check |

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

Checks run locally as a pre-commit githook — every commit must leave both documents green under --safe and the tool boundaries intact [@rm-ci]. A fresh clone enables it once, since git cannot auto-enable a hook from a commit [@rm-ci-enable].

```sh
git config core.hooksPath .githooks   # enable the local-CI pre-commit hook (once per clone)
```

## Status

A working spike — the engine projects and gates, the self-hosting paper is green, discriminate.py grades check adequacy, and this README is itself a projection [@rm-status]. Next are render-to-PDF (pandoc/docx) and a packaged CLI (paperkit init/project/gate/build) [@rm-next].

