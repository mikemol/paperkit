# prototypes/

Version control for design state that is **not yet gated** — drafts, proposals, and
in-progress claim-DAGs that aren't clean enough (or don't yet have `check` witnesses)
to be a real project, but are load-bearing enough that losing them would hurt.

**Versioned and gated are different axes.** A thing can be worth preserving in history
long before it is worth enforcing in `//:hook`. The scratchpad and a session's plan file
are durable-for-a-session but *unversioned* — a prototype that matters belongs here, in
the tree, where git preserves it and a diff shows how the thinking moved.

## The contract

- **Versioned, not gated.** Nothing here is in `//:hook`, any project's `warrants`, or
  `footdeps.WIRED`. A prototype `.bib` has no `check` fields (design claims, not warrants),
  so it is a well-formed claim-DAG paperkit's parser reads but no gate enforces. Confirmed
  safe by construction: `//:hook` and every `warrants` list are explicit (never globbed), so
  a file here is picked up by nothing until a project's config names it.
- **May be unclean.** A prototype does not have to be finished, consistent, or correct. It
  has to be *saved*. Half-formed is fine; lost is not.
- **Self-describing where natural.** A proposal *about* paperkit's own format is best kept
  *as* a paperkit bib — the reasoning stored in the format it reasons about, `rests-on`
  edges carrying the argument's real dependencies. Such a file is its own worked example.

## Graduation

A prototype graduates by growing what a gate needs, not by moving: add `check` fields to
the claims, a `paper.toml` + `rubric.tsv`, wire it as a `@paperkit_*` project, and it
becomes a gated warrants.bib like any other. Until then it lives here, tracked, un-enforced.

## Status: DRAINING (2026-08-27)

⚑ **This folder is being emptied, not maintained.** Every one of its 217 entries (101 remaining after the mem-climb purge) was given a
per-entry verdict by an exhaustive two-pass reconciliation — pass 1 (six agents, one per file
or chunk) and an adversarial pass 2. No sampling, no arc-level inheritance.

The disposition rule, and it has three arms:

- **OBSOLETE / SUPERSEDED → delete outright.** Nothing is archived. Where a successor landed,
  the successor IS the record; keeping the superseded entry stores a wrong thing next to a
  right one and invites a reader to trust the wrong one.
- **IMPLEMENTED → the REASONING moves into the tree**, as claims with `rests-on` edges. ⚑ A
  verdict of IN-CORE is *not* the same as drained: `never-writing-is-the-immune-pattern` is
  in-core (`tools/calc.bzl` reads `memory.peak` with a bare `cat` and never writes it) while
  the *reasoning* — why writing registers you into a shared floor, why since-creation is the
  action's own window — lives only here. Delete that today and the code keeps working while
  its justification vanishes.
- **NOT YET IMPLEMENTED → build it.** Not recorded elsewhere; built. Then it is arm two.

**Measured drain state at the start:** only **4 of 217** entry keys were named anywhere outside
this folder (`docx-pdf-are-transforms-not-observations`, `grouping-is-not-pagination`,
`genre-names-the-objective`, `measured-grounding-is-sparse-and-section-aligned`). That number is
the honest measure of how much has actually moved, and it is what the drain has to raise.

**Shape of the remaining work.** 186 of the 217 entries are load-bearing — something else in the
DAG rests on them — and only 31 are terminal. 15 are hubs, depended on three or more times. So
relocation is not 217 decisions; it is chains, and a chain usually collapses to one claim plus
`rests-on` edges. Work the hubs first.

## What remains to build

Thirteen items, cross-checked across all eight agent reports — every DROPPED entry lands in one
of them, so this list is the whole of the not-yet-implemented arm:

| item | what it is |
|---|---|
| `Ζ·concept·manifest` | `bibtex.bzl` hardcodes `@paperkit_library//:` while `result:` computes `@paperkit_<proj>//:`; `concept:` carries no owner. `MODULE.bazel` is already the manifest; the CLI walks the filesystem instead. Also blocks the wheel (`pyproject.toml:11`). ⚑ **Operator decision** |
| `Ζ·mem·unwired` | `tools/zswap_probe.py` and `tools/mem_converge.py` are source-complete, correct, and wired to nothing. 8+ IN-CORE verdicts rest on them; under *reflected AND enforced* they are instruments |
| `Ζ·observe·rosetree` | `S → RoseTree(S)` is asserted in four files; `observe()` returns a flat list. The language was copied into three check docstrings without revisiting it |
| `Ζ·suite·count` | 21 of 45 boundary suites hardcode their behavior count; ~22 more hardcode the delta count. Two fixed |
| `Ζ·render·tier` | the deck apparatus (`rnd-graph`/`deck-bound`/`slides`/`units`) is `tier={toolchain}` — gate-wired every commit, never adequacy-swept. ⚑ **Operator decision** |
| three-state manifest | per-bucket provenance (unmeasured / converged / climbing). Its absence cost 55,447 cells at the 4MB floor |
| quote-laundering | a conclusion adjacent to a verbatim quote must be backed by something other than the quote. `conclusiongate.py` is the home and is blind to it |
| `brief` genre | ⚑ already load-bearing in a gate *without existing* — `claims.py genre_registry` uses `[genres.brief]` as its fixture while `paper/implications.bib:110` promises it as a rendering |
| G1 | `rnd-units` prose says "THREE projects commit one"; `OBSERVED` holds four |
| G2 | `collection`'s objective IS gated (`claim:genre-collection`); only a committed manifest is absent |
| G3 | `--max-residual` parses but is never invoked with a value — a CONTROL only ever tested as an INSTRUMENT |
| G4 | `setup` and `report` are outside `//:hook`. `BUILD.bazel:102-104` names this exact failure mode for the talk and then wires it. ⚑ **Operator decision** |

## The files

- `slides.bib` (32) — the deck/collection design. Its successor `deck-observe.bib` built almost
  all of it. Several entries are **self-retracted in-file**: `rubric-becomes-the-override` is
  overturned by `two-instances-failed-and-that-is-the-finding` ("rubric was in the wrong family"),
  and the mechanism it reached for landed as `coherence.grouping_residual`.
- `deck-observe.bib` (50) — roughly four hours of implementation immediately before the talk this
  arc produced the deck for. 40 IN-CORE, 9 obsolete, 1 in-core-but-ungated, 0 undetermined. The
  only genuinely dropped thing is the `brief` genre.
- `mem-climb.bib` — **PURGED 2026-08-28.** The memory-measurement material is engine-EXTERNAL:
  the reservation belongs to the encapsulating environmental context (Bazel's execution layer, the
  cgroup, `--local_resources`), not to paperkit's semantics. `bnd-parallel` is not a coverage gap
  over it but the correct and complete statement of the relationship — the engine is inert to the
  reservation BY DESIGN, so no claim asserting the instrumentation's correctness belongs in
  `boundaries/` or root. The file's 116 entries hung off six roots, five of them memory roots, so
  it was a tree with an engine-external trunk rather than a removable prefix. Its one surviving
  engine-semantic finding (`result:` is an ADDRESS, not a Π-typed vector) was applied to
  `memory/pi-typed-boundary-delegation.md` before deletion; the floor/derived-domain cluster had
  already landed as `units.py`'s `_OBSERVED_FLOOR` with its rationale intact.
- `result-tristate.bib` (19) — the `result:` tristate. The ARM shipped (`resolver.py:37`,
  `:114-122`); the Π INDEX is deliberately deferred with the reason recorded at `resolver.py:59-62`.

⚑ **A caution for whoever drains these.** These bibs are DAGs with chronology: a later session
frequently retracts an earlier claim in the same file, and the retraction is sometimes *not*
cabled by a `from`/`rests-on` edge. Read later entries before concluding anything about an
earlier one. Six of the first seven items investigated turned out to have been refuted by a
later rung in their own file.
