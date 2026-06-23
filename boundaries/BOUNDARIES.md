# paperkit Tool Boundaries

*Each tool's ⟨P, F, δ⟩ lint suite, as a claim — this bib is a makefile, and the gate runs its checks in parallel.*

## The Δ Grader and --without-K

The Δ grader's boundary — it flags a check that provably cannot fail (vacuous) and passes one a mutation can break (behavioral) [@bnd-delta]. The --without-K boundary — it flags two cited claims that share a single witness and passes claims that carry distinct witnesses [@bnd-witness].

## Projector and Gate

The projector's boundary — it emits a cited example verbatim, and --safe rejects an uncited placement (a postulate) [@bnd-emit]. The gate --json boundary — the structured fields track the gate's actual verdict, the pass flag and witness collapses included [@bnd-json]. The parallel gate's boundary — the verdict tracks the checks, never the worker count or a check's memory lease, so fanning out (and routing heavy checks through the membudget semaphore) equals running serially [@bnd-parallel].

## Driver and Μ Cache

The driver's boundary — a witness pumps and serializes resumably, so a slow check is interruptible, not broken [@bnd-driver]. The memoization boundary — a grade is reused only when the content key matches, so a changed engine never serves a stale grade [@bnd-cache].

