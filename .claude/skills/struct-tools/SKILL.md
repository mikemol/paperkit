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
| Bazel targets and deps | `bazel query` | `bazel query --help` | `.bzl` `.bazel` |
| decision coverage | `tools/decisions.py` | `python3 tools/decisions.py` | — |
| effective grades (clamped) | `tools/effective.py` | `python3 tools/effective.py` | — |

## The rule

If you have a question the tooling does not answer directly, **fix the tooling** — do not
reach for `grep`. There is no exception list, and its absence is the design: a gap in the
toolkit is not a category of question that is inherently textual.

⚑ **And a paperkit absence claim is cleared by a MUTATION, not a search.** The question is
almost always *"can this check fail?"*, which no reader can answer. See `tools/absence_audit.py`
and `Λ·audit·provenance`: mutate the mechanism out, don't source-scan.
