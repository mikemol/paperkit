# Ledger

Seeded 2026-07-21 from the working plan's accumulated AI list (regroundings 20g–20m).
One line per item. Full detail and retrospectives live in the working plan; this is the
durable index. Append-only, retirement-logged (see README).

## The two live threads

1. **Container / sandbox** — the Ζ·idempotent arc's forward edge: `Κ·image·sandbox`
   (R3 DONE @ 2bae2aa, R4 dead, split attestation = terminus) + `Ζ·canary·v2`.
2. **Reconstitution → Μ·kernel** (the original goal, now moving) — concepts authored once
   and imported by every view: 7 witnesses / 17 keys lifted (26f96ec, c9daf03, 084cd4d,
   the resolver reconcile); `Σ·step5` guide view landed (c66334e, zero witness code).
   **Μ·kernel** [the owner's destination, 2026-07-22]: decompose the ENGINE into
   library-certified components around a microkernel, so mutate-verification becomes
   component-local instead of whole-repo-per-commit.
   - **Μ·kernel·bounds ✅** — components.bzl 7-way partition + derived ENGINE_SRCS +
     comp-* filegroups + bnd-components guard (first run caught dag.bzl stale by 10
     edges; bibtex.bzl extension re-pointed from BUILD-text-parsing to the owner).
   - **Μ·kernel·cells — MEASURED 2026-07-22, verdict reshapes the rung.** Probe: a
     docstring edit to coherence.py (ZERO in-engine dependents) re-ran 25,813/26,650
     actions (97%, 32 min). DIAGNOSIS CORRECTED (saturation agent, verified vs my aquery):
     the dominant mechanism was NOT closure width — every pk_eval cell ALSO staged the
     FLAT ENGINE via its `project` attr (bibtex.bzl _data "engine (always)" baked into the
     ev at :429), so the cone machinery bought zero locality; closures alone would explain
     ~900 coherence cells, not 25,813. FIXED by Μ·kernel·fixture·unstage (drop the flat
     engine from eval cells; the closure stages the engine modules). Closure width remains
     the SECOND-order limiter (witnesses → _fixture → discriminate/gate/project).
     Footprint-based staging is UNSOUND (under-approximates what a check could read);
     PAYOFF MEASURED (post-unstage, 5e7dacb): the same coherence probe re-ran 2,223
     cells in ~8 min (was 25,813 in ~32 min) — −91% invalidation, 4× cycle time.
     Remaining shrink: pk_grade's flat-engine data (small unstage), result: rows
     (legitimate), and the closure remainder via the split. The two follow-on levers:
     (1) **Μ·kernel·certs** — each concept: lift DELETES the claim's def-grid from its
     views (graded once at the library); the cell-count reduction IS Λ·full continuing.
     (2) **Μ·kernel·fixture** — split _fixture's hub imports into per-capability
     fixtures so remaining witnesses' closures collapse to their subsystem cones.
   - **Μ·kernel·certs** — resolver DONE (7 sites, 4 faces); parser/model, projector,
     gate, delta components next.

## Live

- **Κ·image·sandbox** `[owner: R3|R4|R5]` — resolve-escape-proof sandbox in a rootless
  `podman build`. R1 (eval.py fix) refuted. R3 gate-only image (sound, narrower); R4
  nested-userns for real linux-sandbox (host caps OK, needs the RUN-step probe); R5
  `--config=mutant-oci` (host test).
- **Ζ·canary·v2** `[ship regardless]` — sound `pk_eval` positive control that co-degrades
  by construction; `pk_canary` rule + `verdict.py canary` + `//canary:canary` hook member;
  same-commit generalization of the `boundaries_check.py` hook-completeness guard (highest
  blast radius). No longer coupled to any eval.py fix (none exists).
- **Λ·probe-isolation** `[G7]` — probe on an isolated copy; never mutate-and-restore a
  tracked file (an interruption leaves the tree dirty).
- **Λ·push** `[a48cfdc, OUTWARD, needs go]`.
- **Κ·inbox·vcs** `[in progress]` — inbox split into ephemeral drop-zone + tracked
  `inbox/archive/`; letters promoted. Push held pending cassian consent for the raw exchange.
- **Σ·cotype** `[in progress]` — this ledger. Step 2 = the `cotype-monotone` gate.
- **cotype-monotone** `[planned gate]` — enforce append-only+retirement-log on `ledger.md`;
  and (from cassian reply3) the over-decode predicate: a unifying entry is `entailed` (cite two
  points) or `asserted` (candidate, not closure). See README "over-decode guard".
- **Λ·cardinality** `[verified sound — cassian reply3]` — a derived completeness cross-check must
  assert cardinality against an OWNED count, not non-emptiness. Audited paperkit's guards: all sound
  (`for v in resolver.VERBS`, set-equality, `incomplete()` set-difference); the one floor
  (`skips >= 2`) is deliberate (no magic count) + backed by exact derivation. = design constraint on
  Ζ·canary·v2's new guard, not a fix.
- **Λ·doc·agree-boundary** `[done — assets/resolver.md]` — documented: if an `agree:` oracle is a
  reference COMPUTATION (a theorem) not a FILE read, the agreement is the whole falsification surface
  and the mutation grade adds nothing. Sharpens Ζ·surface's file-vs-computation falsifier axis.
- **Ζ·evidence·prune** `[near-moot]` — the ~1GB frozen layer is already gone; 250MB podman
  images remain, safely prunable (finding banked).
- **Ζ·bnd·gate** — `boundaries` is compose-only; no adequacy floor enforces its honest grades.
- **Ζ·measure·site** — re-site the gate-able practice memories from memory to a hook/gate.
- **Ζ·positive-control** `[class]` — every degradable mechanism (sandbox, strace, footprint)
  needs a control that fails loud on degradation. Generalizes Ζ·canary.
- **Ζ·degrade·roots** — the strace footprint measures imports, not dependencies.
- **Ζ·gen·coupling** — generator coupling flagged in the Ξ·compose investigation.
- **Λ·verbcount·chain** — the `concept-builtin` claim + witness in `paper/resolver.bib`.
- **Ζ·knobs → Ζ·hook-rot** — `gen_knobs.py` cwd-fragile (`parents[2]`); then add
  `@paperkit_config//:gate` to `//:hook` (config/setup rot silently).
- **Λ·resolver → Λ·full → Σ·step5** — the ~15–25 concept lift; library holds 2 today, so
  Λ·full is the constraint on Σ·step5.
- **Ζ·prove-gate** — gate the `--prove` envelope without re-running the sweep.
- **Θ·step3** — fold `boundaries` test-faces (20 suites ↔ 21 claims).
- **Λ·stash** — drop the obsolete `stash@{0}` (Λ·deep first-pass).
- **root paper.toml:5** — decide explicitly whether to repoint the pitch warrant to
  `//library:adequacy_pitch.bib` (arguably unnecessary; the pitch RECORD is view-side prose).
- **Λ·location** `[class]` — nothing gates the only out-of-repo consumer; the inbox is a
  human relay, not a gate.
- **Λ·commit·atomic** — small semantic commits, atomic not merely topical.
- **Λ·cite·unchecked** — `references.bib` entries carry no check; a cite asserting another
  project's behaviour is a stronger unchecked claim than citing Knuth.
- **Θ·charges** — carried from the downstream report (their A52).
- **Λ·enumerable** — choose the side you can enumerate (allowlist over blocklist).

## Closed

- **Λ·witness / Λ·library** `[1587578 2615582 0490c27]` — proof-carrying witness; concept
  authored + graded once at its owner, views import the certificate.
- **Λ·prove** `[ab386b4]` — the witness proves itself; `--prove` byte-equal to `__dcalc`.
- **Λ·verbcount** `[71315f0]` — de-counted the false "four builtins" prose.
- **Λ·registry·data** `[0627c56]` — `resolver.VERBS` owns the verb set; witness derives.
- **Λ·registry·gate** `[3e60cb1]` — `VERBS.crosses`; every dispatch site derives from VERBS.
- **Ζ·ladder** `[b2d313c]` — the grade ladder gets one owner; its floor fails CLOSED.
- **Ζ·surface·{land,iface,kind,suffix}** `[4e74917 8f823b8 fd402a8]` — a claim graded
  against its SUBJECT; a grade also says how much it looked at; `.json`/`.bzl` admitted.
- **Λ·library·seam / Ρ·emit·missing / Ζ·ladder·sentinel / Λ·prove·resolution** `[501c4cd
  38860c9 d1f9131]` — the seam owned by VERBS; a placement that did not happen is a finding;
  a resolution names its frame.
- **Λ·cite / Λ·doc·concept** `[444c031]` — cite the downstream field report with their
  attribution correction.
- **Κ·verify·commit** `[a48cfdc]` — `.base` committed sound; `.verify` committed with its
  KNOWN-LIMITATION caveat; neither wired into `//:hook`.
- **Ζ·idempotent** `[RESOLVED]` + **Ζ·idempotent·mechanism** `[experiment run]` — the Δ
  sweep needs a sandbox that blocks `resolve()` symlink-escape; processwrapper lets checks
  resolve out to the real unmutated tree. Mechanism CONFIRMED; agent's eval.py:90 fix REFUTED.

## Practice (banked as memory)

Λ·contact · Λ·outward · Λ·rationale · Λ·risk · Λ·act · Λ·iface · Λ·evidence · Ζ·pipestatus ·
Λ·instrument-vs-gate · Λ·standing-vs-construct · Λ·artifact-state.

## Retired

- **Ζ·image·hermetic** — RETIRED: subsumed by Κ·image·build (per-action toolchain declaration
  is the lower rung of pinning the ambient environment).
- **Λ·grid** — RETIRED: re-derives the proof per view — the anti-pattern `result:` refuses.
- **Λ·delegate (naive)** — RETIRED: a scalar `imported` stamp with `tests=[project]` breaks
  `:cohere`; the proof must travel with the witness (→ Λ·witness).
- **R1 (eval.py:90 unlink-then-write)** — RETIRED: refuted by the Ζ·idempotent·mechanism
  experiment; the mutant `.pyc` lands fine both ways, so it was never a delivery bug.
