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

## Contents

- `slides.bib` — the claim-DAG for the slide-deck / document-collection projection design
  (2026-08-15): projection-as-coalgebra, the emergent `rests-on`-modularity cut, the
  compose⊣decompose adjunction, and genre-as-named-pagination-objective. A draft; reads as
  a DAG (follow `rests-on`, not file order). Parses clean, 0 dangling edges, no `check`s yet.

- `deck-observe.bib` — the SUCCESSOR record to `slides.bib` (2026-08-22), written after
  **Ρ·deck·node** landed: what the slide *format* delivered, what it deliberately did **not**
  (a deck is still a transform of finished prose, not an observation of the DAG), and what
  **Ρ·deck·observe** still needs. Records the five rungs that landed — **Ρ·deck·node** (the
  format), **Ρ·deck·residual** (`coherence.py`'s fifth face, calibrated against `slides.bib`'s
  independently-measured 57 edges / 61% within-section), **Ρ·deck·emit** (the route walked, and
  the four-slide cut collapse that exposed a too-weak gate) and **Ρ·deck·residual·gate**
  (`--max-residual`, which needed the `link` discharge first), and **Ρ·deck·genre·registry** (the
  pagination axis as an OPEN registry on the `resolver.VERBS` model, after the owner settled
  `open-gamma-set` as open). What remains is `open-objective-per-genre` — the objective functions
  themselves — inside a now-fixed shape. Parses clean, 0 dangling edges, no `check`s yet.

  Unlike the others, several of this file's claims are **gated elsewhere**: the deck bound is
  `@paperkit_render//:rnd-deck-bound`, the walked route `@paperkit_render//:rnd-slides`, and the
  residual + its gate `@paperkit_paper//:grouping-residual`, and the genre registry
  `@paperkit_paper//:genre-registry`. The design record stays un-enforced; the parts that landed
  are enforced where they live.
