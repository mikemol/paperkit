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
| `from` | prose-order edge: topological ordering + glue adjacency (general→specific) | warrant |
| `rests-on` | grounding edge: effective-grade clamping + citation provenance (NOT prose order) | warrant |
| `reads` | the check's declared cross-package footprint — staging + audit tokens (Ζ·foot) | warrant |

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
