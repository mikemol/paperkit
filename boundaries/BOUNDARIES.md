# paperkit Tool Boundaries

*Each tool's ⟨P, F, δ⟩ lint suite, as a claim — this bib is a makefile, and the gate runs its checks in parallel.*

## The Δ Grader and --without-K

The Δ grader's boundary — it flags a check that provably cannot fail (vacuous) and passes one a mutation can break (behavioral) [@bnd-delta]. The --without-K boundary — it flags two cited claims that share a single witness and passes claims that carry distinct witnesses [@bnd-witness]. The ∂² coherence residual — it reports zero when a claim's from and rests-on edges agree and when witnesses carry distinct sensitivities, and surfaces the divergence and the collapse otherwise [@bnd-coherence].

## Projector and Gate

The projector's boundary — it emits a cited example verbatim, and --safe rejects an uncited placement (a postulate) [@bnd-emit]. The gate --json boundary — the structured fields track the gate's actual verdict, the pass flag and witness collapses included [@bnd-json]. The parallel gate's boundary — the verdict tracks the checks, never the worker count or a check's memory lease, so fanning out (and routing heavy checks through the membudget semaphore) equals running serially [@bnd-parallel]. The environment boundary — a check runs in a controlled, default-deny environment (sshd's defence against env injection), keeping PATH, locale, and paperkit's own knobs but dropping LD_PRELOAD, IFS, BASH_ENV, and the like, and dropping PATH's relative entries so a tool cannot resolve to the gated project dir [@bnd-env]. The reference projector's boundary — a non-adjacent grounding edge projects as a direction-aware cross-reference, an adjacent one is carried by the connective, and a target reachable by a longer grounding path is dropped as redundant [@bnd-references].

## Driver and Μ Cache

The driver's boundary — a witness pumps and serializes resumably, so a slow check is interruptible, not broken [@bnd-driver]. The memoization boundary — a grade is reused only when the content key matches, so a changed engine never serves a stale grade [@bnd-cache].

