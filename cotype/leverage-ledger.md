# Leverage ledger — paperkit instrument repair → 21-genre projection

Externalized working state for the 15-minute tick loop. **The tick re-derives the ordering from
the tree each time; this file is the durable record of what landed and what it cost.** Prose here
is a hypothesis until a tick re-checks it (`fresh-comments-are-hypotheses-too`).

Plan: `~/.claude/plans/read-home-mikemol-downloads-paperkit-v4c-floofy-pike.md`
Survey: `~/Downloads/paperkit-v4cat-publication-format-survey-anchored.md`

## Standing rules for a tick

1. **Re-derive before working.** The ordering below is the *last* tick's reading, not an
   authority. Recompute leverage from the tree; if it changed, say so and why.
2. **Skip on overlap.** If a prior tick's work is in flight (uncommitted half-edit, background
   job running), record a no-op and exit. Do not start new work.
3. **Verify after every change**, with the tool that owns the artifact. A change that cannot be
   verified is reverted, not reported as done.
4. **A null is a reading about the instrument.** Empty grep, green gate, exit 0 — say what was
   measured, never "it's clean". `--roundtrip`, `--without-K`, and exit 3 are the honest forms.
5. **Never `--no-verify`.** Never `--force`. If a gate blocks, that is the finding.
6. **Findings are appended, not overwritten.** A wrong earlier reading stays, dated, with the
   correction beside it.
7. **Structural readers own their artifacts**: `.py` → `pycodemod.py`, `.bib` → `bibstruct.py`,
   `.json` → `jq`. No grep/sed on structured files.
8. ⚑ **AN EDIT TO A BIB IS AN EDIT TO THE PROJECTION.** `rests-on` feeds `transitive_reduction`
   and `references`, which render cross-references into the `out` document. After ANY bib edit:
   re-run the projector for that project, then re-grade. A2 changed one edge, did not regenerate,
   and left two claims `broken` — the repo red — while reporting the work complete (Γ-F4).
9. **A grade-ladder change is a first-class signal.** `grades.py` reporting a new rung (especially
   `broken`) means the repo's state moved. Attribute it by BISECTION (stash the suspect edit, re-run)
   before explaining it. Never narrate a cause you have not isolated.
11. ⚑⚑ **Π-TYPE A COMMENT BEFORE CITING IT. Existence is not inhabitation.** (operator, 2026-09-09:
    *"You have to treat comments like you would treat parameterized claims/witnesses; you have to
    not just assert existence, but pi-type it."*)

    A comment that reads `⚑ Operator decision` is **not** an existence claim ("a decision exists
    here"). It is a Π-type — `Π(d : Decision) → applies(d, <this site>)` — a FUNCTION AWAITING ITS
    ARGUMENT. G4 is the TYPE; nothing supplies the `d`. So the honest reading is *"this site requires
    a decision of this shape"*, and citing it as a warrant DISCHARGES AN OBLIGATION BY ASSERTING THE
    TYPE IS POPULATED.

    Both Ω failures were this, at different indices:
    - **Ω-F7:** read G4's `⚑ Operator decision` as an inhabitant. It is the type. Its own sentence
      even names the precedent that DISCHARGES it (the talk was wired), i.e. it exhibits what an
      inhabitant looks like and says this site lacks one.
    - **Ω-F1:** `Containerfile.base` mentions a network fetch — but that is `Π(layer)`, parameterized
      over WHICH layer, and the comment supplies the argument itself (the pinned, isolated apk
      layer). I took the existence of a network dependency and applied it at the wrong index.

    ⚑ **The engine already does this correctly, twice, and both are the model:**
    - `coherence.scope_residual` (`coherence.py:212`) refuses to let `entails = {fragment}` be
      self-fulfilling — *"on its own it is just a word"* — and checks the DECLARATION against
      MEASURED reach. A declaration that lowers its own obligation needs an independent witness.
    - `Ζ·pi·unresolved` (`grade.py:357`) makes an unresolvable edge a THIRD STATE, distinct from
      "resolved to no constraint", because *"no constraint recorded" and "constraint recorded as:
      none" render identically once collapsed*. Citing G4 collapsed exactly that: **"no decision
      recorded" vs "decision recorded as: exempt".**

    **Operationally:** when about to cite a comment as licence — NAME THE INHABITANT. Who decided,
    where is it recorded, what argument fills the parameter. If the answer is "the comment says
    there's a decision", the type is unpopulated and the correct state is UNRESOLVED, not exempt.
    ⚑ This matters most in a GATE: a wrong reason inside `hook_grid.py` launders the status quo into
    a decision, which is worse than an undocumented exemption because it reads as settled.

10. ⚑ **READ THE DENOMINATOR, NOT THE ROW COUNT.** `bibstruct --field X` prints `N of M entries`;
    when `N < M` the census is INCOMPLETE and the missing rows are invisible in the output. Ε found
    `bibstruct` silently dropping `claim` on 3 entries whose values contain LaTeX braces
    (`\{`, `\}`, `\bigcup_{…}`) — a tool bug, not a corpus bug (paperkit's own parser reads them).
    Run `--roundtrip` on any bib before trusting a field census over it, and never conclude a field
    is ABSENT from an `N of M` where `N < M`.

## Environment

> ⚑⚑ **RE-DERIVED AT TICK 40 (Ρ): 4 OF 5 CHECKABLE CLAIMS HERE WERE STALE.** This section is what
> a reader trusts BEFORE measuring anything, and every tick begins by reading it — so it is the
> worst place in the file for drift. Corrections are inline below, originals struck through per
> rule 6. Re-derive with `scratchpad/probe_ledger_env.py`.

- ~~`PAPERKIT_ROOT` is REQUIRED~~ — **superseded by Γ**: hook-set projects DECLARE `[paper] root`
  in their own `paper.toml` (root `"."`, the rest `".."`). No env var needed.
  `setup`/`report`/`image` deliberately still undeclared — `local` tier, never Δ-swept. ✅ still
  true (measured: those three plus two fixtures are the only undeclared `paper.toml`).
  - ⚑ ~~"all NINE hook-set projects"~~ → **TEN** declare a root, and **MODULE.bazel wires 13
    projects**. `arch` (tick 38) is adequacy-graded, so the hook-set grew. **Do not quote "nine".**
- ~~`discriminate --json paper` ≈ 61s, 110 claims~~ — ⚑ **both numbers are stale:**
  - **115 entries**, not 110 (tick 40) — `genre-declared-gated` and others landed since.
  - **~61s is a COLD sweep; a WARM one is ~0.1s** (Β-F3, measured over all nine graded projects).
    Quoting 61s for a warm run over-estimates by ~600×, and quoting 0.1s for a cold one
    under-estimates the same way. **Say which cache state you mean.**
- ⚑ **Γ MADE THE REPORT PIPELINE GENUINELY EXPENSIVE, AND THE OLD SPEED WAS THE REFUSAL.**
  Before Γ, `_delta` on the seven undeclared projects returned `[]` INSTANTLY because the grader
  refused and the exit code was swallowed. Those runs were fast because they measured nothing.
  ~~Now `gen.py --check delta.md` really grades nine projects and exceeds 600s~~ — ⚑ **corrected
  by Β-F3**: it exceeds **2700s** (exit 124 twice), and the cost is **NOT spread over nine
  projects**. Eight total ~18s; **`render` alone exceeds 240s, and within it `rnd-ocr` alone is
  ~98s of a 164s sweep.** The "600s over nine projects" reading both understates the figure and
  misattributes it. `coherence.py paper` spawns `discriminate --resolution def --json`, the
  def-resolution sweep. Budget accordingly, and do not read a long run as a hang.
- ⚑ **Do not run concurrent Δ sweeps.** Each copies a bounded sandbox PER MUTATION CELL. Three
  were once live at once here (two of them stale `gen.py --check` jobs launched pre-Γ, grading a
  tree that had since changed); killed. One sweep at a time, and re-launch after a corpus edit
  rather than letting a pre-edit run finish.

- ⚑⚑ **NEVER RUN THE IN-PROCESS SWEEP. USE THE BUILD GRAPH.** (operator, 2026-09-09; measured)
  `coherence.py paper --json` spawns `discriminate --resolution def --json`, the LEGACY on-demand
  loop. Measured over 1h53m: **10 threads at ~10.5% CPU each** (104% total — a ten-wide pool
  delivering ONE core), 9 of 11 threads parked on `futex_do_wait` (the GIL), and
  `/proc/<pid>/io` showing **59 GB rchar / 7.2M read syscalls with `read_bytes` FLAT at 32 MB** —
  i.e. ≈**3,000 sandbox copies**, all served from page cache. The sweep is **COPY-BOUND, not
  check-bound**: `_copy_sandbox`'s `shutil.copytree` of the ~20 MB repo per cell, in Python,
  under the GIL. It produced no output in two hours and was killed.

  `discriminate.main`'s OWN comment names the right path: *"Ζ·nest — grade ONE claim (the
  per-claim grade ORACLE)… **Bazel nests one of these per claim and aggregates them
  (pk_adequacy), so the whole-project SWEEP is the build graph — not the loop below**, which
  stays for direct/on-demand use."* `bibtex.bzl` already emits `pk_mutate` → `pk_pyc` → `pk_eval`
  per (claim, site) and `discriminate --mutant` is the single-site probe those actions call.
  Bazel then owns parallelism, action caching and per-cell sandboxing.

  **So: `bazel test @paperkit_<proj>//:adequacy`, never `coherence.py`/`discriminate` in-process
  for a def sweep.** Verified `@paperkit_paper//:adequacy` exists.

- ⚑ **NOTED, NOT FIXED (operator, 2026-09-09): THE GIL IS A STRUCTURAL BOTTLENECK.** *"In-python
  can work, but it requires a worker pool model where the pools are separate processes."*

  **The structure, which is what makes this actionable:**

      _grade_parallel  →  ThreadPoolExecutor(N)  →  N threads
                                                      ↓  all contend on
                                                    ONE mutex (the GIL)
                                                      ↓
                                                    1 interpreter

  A pool is a structure whose defining property is that its workers are INDEPENDENT. A thread
  pool in CPython is not one: every worker holds the same lock to execute bytecode, so the
  independence the pool asserts is contradicted by the carrier it runs on. The pool is
  nominally N-wide and structurally 1-wide — a *shape* mismatch, not a slow constant.

  **Why the work is bytecode-bound and therefore fully serialized.** `_grade_parallel`
  (`grader.py:942-979`) parallelises over distinct CHECKS, but each check's cost lives in
  in-interpreter work between subprocess calls: `shutil.copytree` per sandbox (`_copy_sandbox`,
  file-by-file in Python), the tri-modal AST pass in `_sites` (`_def_sites` + `_branch_sites` +
  `_data_sites` per `.py`), and the recursive bisection bookkeeping in `sensitivity.split`. None
  of it releases the lock for long, so the pool's width is decorative.

  **Why the repair is small: the dataflow is ALREADY process-shaped.** Each cell (a) owns a
  PRIVATE sandbox directory, (b) shares no mutable state with its siblings, (c) returns a small
  verdict record. That is precisely the shape `ProcessPoolExecutor` requires — nothing to
  marshal, no shared structure to split. **The GIL is the only thing making this serial**, so
  removing it is a swap of executor, not a redesign. (`fork` + a work queue is the same shape.)

  **Deliberately NOT done now:** the build graph (`bazel test @paperkit_<proj>//:adequacy`)
  already supplies independent workers — one `linux-sandbox` action per (claim, site), plus
  caching — so the legacy loop is off the critical path. Recorded so the structure is not
  re-derived: *the loop asserts independence its carrier denies.*

  ⚑⚑ **AND "USE PROCESSES" IS STILL ONE LEVEL TOO LOW (operator, 2026-09-09).** *"A work unit
  needs to be isolated. We need to not have to care if something is same-proc vs same machine vs
  same network UNLESS a constraint is structurally expressed to either force or reject such a
  relationship. That's v4cat-oss applied to scheduling constraints."*

  `ProcessPoolExecutor` is a PLACEMENT prescription, and placement is not the thing. The work
  unit asserts **CONSTRAINTS** — isolated mutable state, ordering, resource exclusivity,
  colocation-with-a-resource — and placement is whatever SATISFIES them. Same-proc / same-machine
  / same-network must be **derived**, never assumed, and only forced or rejected where a
  constraint expresses it.

  So "must be a separate process" is not a fact about the work unit at all — it is a fact about
  the GIL that leaked into the unit's definition. The honest statement is *"this unit requires
  isolated mutable state"*, and then: the GIL FAILS to witness that constraint, while
  `ProcessPoolExecutor`, `linux-sandbox`, and a remote executor each satisfy it. One constraint,
  several witnesses — the v4cat shape: a break is a named structural distinction, introduced only
  where something witnesses it, never read off an implementation's incidental location.

  ⚑ This is WHY the Bazel path works without rewriting a single check: an action DECLARES its
  inputs, outputs and sandbox requirement, and placement (local / sandboxed / `--config=remote`)
  FALLS OUT of the declaration. The action graph already IS the structural expression of
  scheduling constraints; the thread pool hard-codes a placement and asserts an independence
  nothing checks. Any future repair of the in-process loop should express the CONSTRAINT and let
  the executor be chosen — not swap one hard-coded placement for another.

### Ω — TICK 7 PROGRESS (2026-09-09): one warrant retiered, two corrections, one blocker

**⚑ Ω-F1 — CORRECTION: `img-stable` does NOT conceal an unstated network dependency. I was wrong.**
I recorded (above) that `podman build` over `Containerfile.base` *"fetches over the network — an
unstated NETWORK dependency, exactly the class `no-sandbox` conceals."* **Refuted by reading the
files.** `Containerfile.base` is **digest-pinned** —
`FROM docker.io/library/python@sha256:399babc8…` — and its own comment states the design: *"apk's
installed-db ordering is irreducibly non-deterministic, so the apk layer is ISOLATED here as a
pinned dependency."* `Containerfile` then reads `FROM localhost/paperkit-base:proof` and is
**COPY-only**, so the proof-image build touches no network at all. The network dependency is real,
**confined to the base, deliberate, and content-pinned** — stated, not concealed. Kept per rule 6:
I asserted a concealed dependency from the tier alone, which is the same infer-don't-measure error
the tier vocabulary itself invites.

**⚑ Ω-F2 — THE BLOCKER: promoting `image` to `toolchain` TODAY WOULD BE WORSE THAN `local`.**
`toolchain` tier caches an action against the stamp fingerprint. Read
`tools/toolchain_status.sh`: it emits exactly five keys — `PANDOC`, `VERAPDF`, `LUALATEX`,
`SOFFICE`, `VERAPDF_JAR` (sha256) — all render-toolchain. **It does not include `podman` or the base
image digest.** So a `toolchain`-tier `image` would be cached against a fingerprint that does not
track its actual dependency: a stale cache hit whenever podman or the base digest changes — a green
measuring the wrong fingerprint, precisely the defect Ω exists to remove.

⚑ The mechanism is already generic and correct: `emit()` takes any tool name plus a version
command, and the veraPDF JAR sha256 precedent argues for the finer key. So the shape is small —
`emit PODMAN podman --version` plus the pinned base digest — **but which keys belong in the
fingerprint is an owner decision, and Ω STOPS here for `image`'s three podman warrants.**
(`podman` IS present on this host, so the change is verifiable when authorised; the cost is that
`img-repro`/`img-stable` build container images per mutation cell.)

**⚑ Ω-F3 — LANDED: `img-hermetic` never needed the host, and passes hermetically.**
Its check is `cmd:grep -q -- "--network=none" checks/repro.sh` — a grep over a file INSIDE the
project. Added `tier = {sandbox}` per-warrant (the `render/warrants.bib` precedent: 29 per-warrant
tiers, no project default). Verified:
- the generator now emits `@paperkit_image//:img-hermetic__foot` and `:footaudit`, which appear ONLY
  for sandbox warrants (`bibtex.bzl:998` skips footprints for non-sandbox) — proof the tier took;
- `bazel build @paperkit_image//:img-hermetic` runs under `linux-sandbox` and the verdict record
  reads `{"verb":"cmd","verdict":"pass"}`.

**So one of image's five warrants was exempted from sandboxing, caching AND remote execution purely
by inheriting a project-level default, and needed none of it.** Ω's premise demonstrated on a real
warrant rather than argued.

**⚑ Ω-F4 — `img-pinned` is the same shape but NOT SAFE TO RETIER BLIND.** Its check greps
`../Containerfile.base` — **outside the project**. Whether the hermetic sandbox stages a parent-dir
file is unmeasured, and `--field reads` over render returns **0 of 34**, so `reads` is not the
in-tree mechanism for declaring an out-of-project input. Left `local`; retiering it needs the
staging question answered first (and would then be the second free win).

### Ψ.2 — GRANULARITY CENSUS (tick 11, 2026-09-09) — WITH A CORRECTION TO TICK 10

**⚑ CORRECTION TO MY OWN TICK-10 FINDING.** I wrote *"the coarse grade is NOT inert"* on the basis
that two faces read `grade`. **That was half wrong: THE GATE IS INERT, and I did not check the
exits.** `//:cohere`'s `--from-calcs` arm exits via `_grounding_exit` (`coherence.py:733→625`),
`_vacuous_exit` (`:731`, reading `rep["vacuous"]`, computed from `_engine_cap` over `tests`), and
the `Ν·partial` refusal (`:718`, edge counts). **No exit code on the gated path is a function of
`grade`** — so switching `_records_from_calcs` to `_grade_from_sens` cannot change the gate's
verdict. Refined further:
- `sensitivity_residual` — **does not move either**: under the coarse map `grade == "behavioral"`
  ⟺ `sens` non-empty, so the partition is the same, reached for a different reason.
- `scope_residual` — **the only real change**, and its residual would DROP, because a `broken`
  record would stop being misread as `vacuous` and leave the `("vacuous","indeterminate")` tuple.

I asserted a behaviour change without checking what the gate's exit actually reads. The honest
verdict is: **inert for the gate, one reported number moves, in the safe direction.**

**⚑⚑ Ψ.2-F2 — THE `UNREACHABLE` TRISTATE COLLAPSES AT THE CALC-RECORD BOUNDARY. Verified.**

`grade.py:86-98` records the defect this axis exists to fix, and its cost:
*"a check killed by its memory cap graded `broken` with 'repo is not green' — about a green repo.
**Measured: that exact false statement, twice, on 2026-08-26.**"* `BASELINE_C` is the repair.

The repair holds in-process and **dies at serialization**, at one hop:
1. `grader.py:499-500` — `rec = _grade_from_sens(baseline, sens, reachable=(baseline is not UNREACHABLE))`,
   then `rec["baseline"] = baseline` **overwrites the string with the RAW verdict** (a bool, or
   `UNREACHABLE` — an `int` subclass, falsy but not `False`).
2. `discriminate.py:252` — serializes that raw value. **`False → 0` and `UNREACHABLE → 0`:
   byte-identical.** Confirmed on a live record: `bnd-wheel__calc.calc.json` reads
   `{"claim":"bnd-wheel","baseline":0,"sens":[]}`.
3. `tools/read_grade.py` — calls `_grade_from_sens(c["baseline"], c["sens"])` with **no `reachable`
   argument**, so it defaults to `True`. The distinction is unrecoverable downstream.

**Measured** (`scratchpad/probe_baseline_tristate.py`):
- `refuted` and `unreachable` are indistinguishable once serialized — both `0`.
- The live path is nonetheless SOUND for `broken`: `0` is falsy, so a genuinely refuted check still
  reads `broken` with `baseline: "refuted"` (tick 9's `bnd-wheel` output confirms).
- ⚑ But had the STRING been written instead, every state would read truthy and a broken check would
  grade **`indeterminate`** — a rung UP, the unsafe direction. The current correctness depends on
  the raw value being serialized, not the string.

**Net:** the tristate is real, tested (`boundaries_clamp.py:225-238`), and reduced to a bistate at
the one boundary the Bazel pipeline runs through. An unreachable check in the build graph reports
*"repo is not green"* — the exact false statement `grade.py:91` was written to retire.
⚑ **My Ψ-F1 edit did not cause this; it MADE IT VISIBLE** by carrying `baseline` into the record.

**⚑ Ψ.2-F3 — `STRENGTH` IS AN UNGUARDED QUOTIENT, AND THE OWNER IS EXEMPT FROM ITS OWN CHECK.**
`grade.py:17-26` holds three maps, and they are not three orderings: `RANK_C` is the authority
(6 rungs, totally ordered, no ties); `ORDER` is a **domain** (the legal `--min-strength` values, its
own comment says so); `STRENGTH` is a genuine **coarsening** with no stated invariant — it TIES
`existence` and `indeterminate` at 1 (`RANK_C` separates them 2 and 1) and OMITS `broken` entirely,
which `discriminate.py:435` reads through `.get(…, 0)`, silently equating it with `vacuous`.
**Consequence: `--min-strength existence` PASSES an `indeterminate` claim, while
`grade.below("existence")` returns `['broken','vacuous','indeterminate']` and would FAIL it. Two
floors, disagreeing, one guarded.**

⚑ The contrast is in the same 10-line block: `rungs()`/`below()` (`grade.py:173-186`) are FUNCTIONS
of `RANK_C` with a universally-quantified test, a fail-closed injected-rung test, and a consumer
census (`boundaries_ladder.py:64-104`). `STRENGTH` has none. And `boundaries_ladder.py`'s regex
scans CONSUMERS for re-declared rung runs — `STRENGTH`'s literal IS such a run, but it lives in
`grade.py`, which is not in `CONSUMERS`. **The owner is exempt from the check it exports.**

**⚑ Ψ.2-F4 — `tier` IS THREE NAMES FOR FOUR INDEPENDENT BITS** (`verb.bzl:65-84`), confirming Ω
structurally: host-need, cacheability, python placement, and **sweptness** — the last decided
ELSEWHERE (`bibtex.bzl:738`, `:948`). So declaring a warrant `toolchain` because it needs pandoc
**silently also removes it from the falsifiability grade**. And `[checks.X] mechanical = false`
(`bibtex.bzl:943-951`) produces the identical disposition by a second, independent knob.

### Ψ.2 — GRANULARITY: MEASURED, NOT INERT (tick 10, 2026-09-09) — SUPERSEDED ABOVE, kept per rule 6

**The operator reframed the question** from *"is this behavior change acceptable"* to *"what
granularity axes exist, and which are conflated"* (the v4cat move). A research agent is studying the
full axis set; this is the decisive sub-question, measured directly.

**QUESTION:** does switching `_records_from_calcs`' coarse grade (`"behavioral" if sens else
"vacuous"`, `coherence.py:500`) to the full `_grade_from_sens` change what the GATED `pk_cohere`
reads — or is the coarse grade INERT for the ∂² faces?

**ANSWER: NOT INERT. Exactly two of six faces read `grade`, and both change.**

| face | reads | affected? |
|---|---|---|
| `structure_residual` (`:106`) | `rests-on` + prose position | no — never reads `grade` |
| `grounding_residual` (`:366`) | `tests` + `rests-on` | no |
| `emergence_residual` (`:405`) | `_engine_cap(tests)` + `rests-on` | no |
| `unmeasured_edges` (`:330`) | `rests-on` + key sets | no |
| **`sensitivity_residual` (`:197`)** | `if r["grade"] != "behavioral": continue` | ⚑ **YES** |
| **`scope_residual` (`:245,248`)** | `grade in ("vacuous","indeterminate")`; counts `== "behavioral"` | ⚑ **YES** |

- **`sensitivity_residual`** counts distinct sensitivity signatures among BEHAVIORAL witnesses.
  Under the coarse assembly every claim with non-empty `sens` is labelled `behavioral`, so the
  filter admits everything measured. Under `_grade_from_sens` a claim could grade `existence` or
  `imported` and be EXCLUDED — changing the face's population, hence its `collapse` count.
- **`scope_residual:245`** tests `grade in ("vacuous", "indeterminate")` — and ⚑ **the coarse
  assembly can never emit `indeterminate`**. That arm of the disjunction is DEAD under
  `--from-calcs` and reachable only via the other record source (`_records_from_cache`). So the
  same face measures different things depending on which assembler fed it.

### ⚑⚑ Χ · action-decomposition — THE ACTIONS THEMSELVES NEED DECOMPOSING (operator, 2026-09-09)

*"The actions themselves need to be decomposed."* — the specific defect behind the utilization
observation, not a general remark.

**Measured, on the tail of `@paperkit_boundaries//:adequacy`:** at 99/102 the pool has drained and
one action remains, `bnd-delta__calc`, reading **0.3% CPU / 0s of CPU across 3m21s**, parked in
`poll_schedule_timeout`. It is SUBPROCESS-bound, not CPU-bound: the work is in short-lived children
spawned ONE AT A TIME (sampled three distinct PIDs — 297619 → 298388 → 298629 — in three
consecutive calls), each a full run of `boundaries_discriminate.py`. That is `discriminate` grading
a check that itself runs `discriminate`'s boundary suite, which is why it is the long pole.
`sensitivity`'s bisection is serial by construction (`split(g[:m])` then `split(g[m:])`), so ONE
action cannot exceed ONE core no matter the `cgroup-scope 4` cap.

⚑ **Same structural fact as the GIL finding, one level out: parallelism is PER-ACTION, and a single
action's internal work is SERIAL.** 101 actions saturate ten cores; one action cannot.

**⚑ AND THE REPO ALREADY DOES IT RIGHT — the asymmetry is one gated branch.**
`bibtex.bzl:747`: `if emerge and (closures.get(k) or rroots.get(k)):` emits the CELL GRID — one
`pk_eval` per (claim, site), scoped to the claim's closure, plus the ∅-baseline cell, with `pk_sens`
reading them back into `{claim, baseline, sens}`. Its own comment states the thesis:
*"**The fanout IS the build graph — each cell a node** — lifted from `grader.sensitivity`'s
in-process group-testing."* Non-emerge projects fall to the monolithic `pk_calc`, which walks the
same sites SERIALLY inside one action.

⚑ **This finally explains tick 4's puzzle.** 102 actions for boundaries' 49 claims vs **94,796** for
paper's 110 is NOT a coverage gap (tick 4 confirmed 49/49 calc records) — it is a **DECOMPOSITION
gap**. The construction is already conceptually per-site in both; only `emerge` projects emit it as
a graph.

**⚑ THE BLOCKER: `emerge` IS Ψ.2-F4's CONFLATION AGAIN.** Only **3 of 12** projects set it
(`paper`, `root`, `library`), and it drives at least FOUR separate things:

| site | what `emerge` switches on |
|---|---|
| `bibtex.bzl:747` | the per-(claim,site) CELL GRID — the decomposition |
| `:892` | the ∂² coherence gate (`pk_cohere`, `//:cohere` in the hook) |
| `:912` | the decisions summary (`pk_decisions_summary`) |
| `:1091` | whether `sites`/`closures` are enumerated for the repo at all |

Its own attr doc (`:1042`) names two of them on one flag: *"a def-calc per claim + pk_cohere (∂²
faces in //:hook)"*. **So "decompose boundaries' actions" is not a flag flip** — setting
`emerge = True` on `boundaries` would also turn on a coherence GATE that has never run there, which
is a behaviour change to //:hook, not a scheduling change.

**⚑⚑ Χ-F2 — CORRECTION TO Χ-F1: I QUOTED A JUSTIFICATION FOR THE WRONG EMISSION.**
Operator pushed back — *"I don't know that it justifies ANYTHING sitting on it"* — and measurement
says the pushback is right about the lever that matters. **There are TWO `pk_calc` emissions and
Χ-F1 conflated them:**

| site | target | resolution | condition | who reads it |
|---|---|---|---|---|
| `bibtex.bzl:742` | `<k>__calc` | **file** | **UNCONDITIONAL** for every sandbox calc claim | `pk_verdict` — the claim's VERDICT |
| `bibtex.bzl:861` | `<k>__dcalc` | **def** | `elif emerge` — only witness-LESS claims | `pk_cohere` |

Χ-F1 quoted `:853-861`'s comment (*"the grid just optimizes the witness subset — a projection, not
a special case"*) as justifying the lever. **That comment governs `__dcalc`, the rare branch.**

**MEASURED on `paper` — the flagship emerge project with the 94,796-cell grid:**
- `kind("pk_calc", @paperkit_paper//:all)` → **81 targets**, and **0** of them are `__dcalc`. So the
  `elif emerge` branch — the one Χ-F1 justified — **NEVER FIRES in `paper`.**
- `kind("pk_sens", …)` → **81 targets**, named `<k>__dcalc`. So the grid's aggregate takes the name
  the fallback would have produced (as `:751` says: *"a drop-in for the old pk_calc `__dcalc`
  pk_cohere consumes"*).
- ⚑ **The same 81 claims carry BOTH**: a grid row (`pk_sens`, def-resolution, N cells) AND a
  monolithic `pk_calc` (file-resolution, one serial action). Verified on `prose-projected__calc`:
  `{baseline: true, sens_n: 9}` — a real 9-file file-resolution fingerprint.

**So the honest answer to "why do we even have that lever":** the `:742` `pk_calc` is not a fallback
for a subset at all — **it is the VERDICT path, and it runs for every sandbox calc claim, in
parallel with the grid.** `Ζ·calc·interp` (`:736-737`) says why it exists: *"ONE cached sweep
(pk_calc) feeds the verdict reading here (and the grade reading below); the redundant verdict run +
the adequacy re-sweep collapse into it"* — three runs collapsed into one, historically an
improvement.

⚑ **What that does NOT establish, and what the operator's question exposes:** why the verdict needs
a FILE-resolution sweep of its own once a DEF-resolution grid exists for the same claim. The grid
measures a strictly finer surface; `pk_verdict` needs only `baseline`, which the grid's ∅-cell
already computes. **Two sweeps per claim where the finer one subsumes the coarser is the shape of a
lever nothing should be sitting on** — but I have NOT verified that the grid's baseline is
substitutable for the file-calc's, and `sens` differs between them by construction (9 files vs N
def-sites), so the records are not interchangeable wholesale.

**⚑⚑ Χ-F3 — CHASED TO A VERDICT (operator: "chase it"). THE OPERATOR IS RIGHT: on an emerge
project, `pk_calc` is a WHOLE REDUNDANT SWEEP READ FOR ONE BOOLEAN.**

Four measurements, each independent:

**1. `pk_verdict` reads exactly one field.** `tools/verdict.py:194`:
`_write(a.out, a.verb, bool(json.loads(...).get("baseline")))`. The rule's own doc (`calc.bzl:672`):
*"A cheap READING of a calc record: **the verdict is the measured baseline**."* Nothing else.

**2. The grid ALREADY publishes that field, in the same shape, by design.** `tools/sens.py:46`
emits `{"claim": …, "baseline": baseline, "sens": sorted(sens)}` from the ∅-mutation cell
(`baseline = not base.get("flipped")`), and its comment states the substitutability outright:
*"This is the calc-record shape pk_cohere/read consume ({claim, baseline, sens}) — **a drop-in for
the old pk_calc `__dcalc`**. …baseline=false signals the sens is not to be trusted — the reading
layer grades it broken, **exactly as for a file-calc**."*

**3. The two baselines AGREE, measured.** Built `@paperkit_paper//:prose-projected__dcalc`
(**2,203 actions in 22s**, ten cores saturated — the decomposition working, for ONE claim):

| | `__calc` (file-res) | `__dcalc` (grid, def-res) |
|---|---|---|
| `baseline` | `true` | `true` |
| `sens` | **9** files | **111** def-sites |

**4. NOTHING reads the file-calc's `sens`.** `rdeps(@paperkit_paper//:all,
prose-projected__calc, 1)` → exactly two consumers: `prose-projected` (the `pk_verdict`, reads
`baseline` only, per 1) and `mem_learn` — which takes the **`peak` OUTPUT GROUP**
(`calc.bzl:209-210`, `t[OutputGroupInfo].peak`), not the JSON content at all.

⚑ **So on `paper`: 81 file-resolution sweeps run, each measuring a 9-file sensitivity set that NO
CONSUMER READS, to produce a boolean the grid's ∅-cell has already computed and published under the
same key.** The verdict target depends on `__calc` rather than `__dcalc` — confirmed at the graph
level by `deps(@paperkit_paper//:prose-projected, 1)`.

**The honest caveat, stated rather than glossed:** the two `sens` sets are NOT interchangeable
(9 file paths vs 111 def-sites, different granularities), and the file-calc is the ONLY
file-resolution measurement in the tree. Repointing `pk_verdict` at `__dcalc` would be sound for
the verdict (measurement 3) but would DELETE file-resolution sensitivity data — currently unread on
emerge projects, and the ONLY sensitivity data on non-emerge ones, where no grid exists.

**So the lever IS justified — but only for non-emerge projects, which is the opposite of where it
is doing the work.** On `boundaries` (no grid) `pk_calc` is the only measurement and must stay. On
`paper` (grid present) it is a redundant sweep. Χ-F1's justification was for the rare `__dcalc`
branch; the real justification is this one, and it covers exactly the projects the operator was NOT
asking about.

**The remaining decision, now precisely scoped:** repoint `pk_verdict` at `__dcalc` **when a grid
row exists for the claim**, keep `__calc` otherwise. That is a one-condition change at
`bibtex.bzl:745` mirroring the grid's own condition at `:747`, and it removes 81 sweeps from
`paper` alone. NOT DONE — it changes what the verdict is derived from on every emerge claim, and
the ∅-cell's `flipped=false` guard is the thing that would then carry the verdict.

**⚑⚑ Χ-F4 — TICK 13 ATTEMPTED THAT CHANGE AND REVERTED IT. THE CONCLUSION WAS WRONG; THE FINDING
STANDS.** (2026-09-09)

I wrote the change (hoist the grid predicate, emit `pk_calc` only when there is no grid row, point
`pk_verdict` at `__dcalc` otherwise), then found what it breaks BEFORE running it, and reverted.
`tools/bibtex.bzl` is byte-identical to committed (`git diff --stat` → empty).

**What breaks: `mem_learn`.** `bibtex.bzl:920` builds `ml = [":" + k + "__calc" for k in
calc_claims]` — so removing `__calc` for grid claims orphans every one of those labels. And
`:905-911` states the design this would destroy:

> *"Aggregates the **file-calcs' peaks**; the def-sweep is now a grid of pk_eval cells … not a
> pk_calc with a peak output group, so it is not here. **Ζ·mem·def·blind** — file-calcs only as
> DEPENDENCIES. The def-sweep's eval cells carry a peak too, but making mem_learn DEPEND on them
> inverts the economics: paper's grid is 52,584 cells, so the manifest that exists to make the
> sweep affordable would first require running the sweep unsized (measured: **41,468 deps on one
> action**). **The measurement must not cost what it is meant to save.**"*

⚑ **So Χ-F3's measurement was RIGHT and its conclusion was WRONG, in a specific way I should name:**
I established that nothing reads the file-calc's **JSON** (`sens`), and concluded the sweep was
redundant. But `mem_learn` consumes its **`peak` OUTPUT GROUP** — which I had *already measured* in
Χ-F3 and recorded as evidence of redundancy ("*not the JSON content at all*"). **I read "does not
read the JSON" as "does not need the target."** The peak is a real, load-bearing measurement: it is
the only affordable memory manifest, and the manifest is what SIZES the grid.

**Net:** the file-calc on an emerge claim computes a `sens` set nobody reads AND a `peak` the memory
ladder depends on. Those are two different outputs of one action, and the action cannot be deleted
for the first without losing the second.

**What would actually be needed** (NOT attempted): separate the peak measurement from the
sensitivity sweep, so a grid claim can publish a peak without a file-resolution sweep. That is a
new rule, not a condition — and `Ζ·mem·def·blind` already argues the obvious alternative (depend on
the cells) is economically inverted. ⚑ This is the same one-target-two-outputs conflation as `tier`
(Ψ.2-F4) and `emerge` (Χ): the file-calc is doing two jobs and only one is redundant.

**⚑⚑ Χ-F5 — `Ζ·mem·def·blind`'s ARGUMENT DOES NOT HOLD, AND THE REAL BLOCKER IS DIFFERENT.**
Operator: *"'The measurement must not cost what it is meant to save.' That's dumb. We have caching
for a reason."* ⚑ **I quoted that comment TWICE (Χ-F4, and again in the tick-13 report) without
testing it.** Measured, three ways:

**1. The cost argument is refuted by the cache.** Rebuilt `@paperkit_paper//:prose-projected__dcalc`
after its first build: **2,203 action cache hits, 1 process, 6.8s** — INCLUDING a cold Bazel server
start. First build: 22s, 729 sandboxed executions. So a dependency on already-built cells costs a
cache read, not a re-run. **41,468 deps is a DEPENDENCY COUNT, not a cost**, and the comment reads
it as one. The cells are built anyway — by the adequacy sweep the manifest exists to size.

**2. But the cells carry NO MEASUREMENT to depend on.** `prose-projected`'s grid peaks: **991 cells,
every one `0`**. `cellcgroup.write_peak` writes zero when no cgroup measurement is available, and
these cells run without a cgroup scope. **That is a real blocker — and it is NOT the one the comment
gives.** The comment argues COST; the actual obstacle is ABSENT DATA.

**3. ⚑ AND THE FILE-CALC'S PEAK IS ALSO `0`** (`prose-projected__calc.peak`). So on this machine
NEITHER source feeds the manifest. The committed `paper/mem.json` holds **3 per-claim entries** plus
two defaults (`def: 64`, `file: 256`) — for a project with **81 claims and ~52,000 cells**. The
manifest that *"exists to make the sweep affordable"* is ~96% default.

**Net, and it changes Χ's shape:** Χ-F4 concluded the file-calc must stay because `mem_learn` needs
its peak. **That is true as a dependency and nearly vacuous as a measurement** — the peak it
supplies is `0` here, and the manifest is mostly defaults regardless. The three obstacles are now
separable, and only one is real:
- *cost of depending on cells* — **refuted** (cache hits, measured)
- *cells carry no peak* — **REAL**, but a property of how cells are run (no cgroup scope), not of
  the design
- *file-calc peak is load-bearing* — **not on this machine**; it is `0` too

**4. ⚑⚑ THE MANIFEST BUILD, MEASURED END TO END: 84s, 82 SANDBOXED SWEEPS, AND THE OUTPUT IS
`{"claims": {}}`.** `bazel build @paperkit_paper//:mem_learn` → *"83 processes: 1 internal, 82
linux-sandbox… Elapsed 84.006s"*, and the generated `mem.json` is **empty of per-claim entries** —
FEWER than the 3 in the committed file, and without even the `def: 64` / `file: 256` defaults
(so those are AUTHORED, not derived).

`mem_learn` behaves exactly as documented — *"it skips what it cannot read and NAMES why, rather
than folding it to 0"* — and what it cannot read is everything, because every peak is `0`.

**So the full reading of `Ζ·mem·def·blind`:** the comment refuses to depend on grid cells to avoid
a cost that (1) the cache refutes, in order to protect a manifest that (2) currently derives
NOTHING, from a file-calc whose own peak is (3) also `0`. **81 file-resolution sweeps run per
manifest regeneration and produce an empty object.**

**⚑⚑ Χ-F7 — CORRECTION TO Χ-F6: THE `0` IS A DECLARED SENTINEL, NOT A DEGRADED MEASUREMENT. AND
THE REPO RECORDS MY EXACT MISDIAGNOSIS AS A PRIOR INCIDENT.** (tick 17, 2026-09-09)

Χ-F6 concluded the `0` peaks were a *silent degradation* — the sandbox hiding the cgroup parent, so
`PK_CAP` empties and the payload runs unmeasured. **The probe measurement was right; the conclusion
was wrong.** `tools/calc.bzl:129-148`, `_peak_snippet`:

    if observing:
        return " ; { P=$(cut -d: -f3 /proc/self/cgroup); F=/sys/fs/cgroup$P/memory.peak; … } > path"
    return " ; echo 0 > " + path

**When not observing, the peak is NEVER READ — `echo 0` unconditionally.** So the `0` is a
*declared* "not measured here", and `.bazelrc:130-132` states the intent: *"turn the peak read ON
only here; **default builds write a clean 0** (the read OFF would be the SHARED-cgroup garbage), and
the flag is part of the calc action key (observe-vs-default cache as **distinct actions**, so no
stale measured/0 peak crosses configs)."*

⚑⚑ **AND `Τ·mem·observe·honest` (`calc.bzl:132-138`) RECORDS THIS EXACT MISREADING AS A PRIOR
INCIDENT:** *"`2>/dev/null || echo 0` collapsed three distinct causes onto one value: observe-off (a
deliberate clean 0), a real cgroup that never charged a page, and a read that FAILED… (Cost,
measured: **170 cells read 0 and the diagnosis was a kernel capability gap; the real cause was a
cached non-observe write**.)"* **I reproduced that diagnosis, one incident later, from the same
`0`.** The repair — naming `unavailable:absent` / `unavailable:unreadable` — is exactly why I could
tell `0` from a failed read (Χ-F6.2) and still drew the wrong conclusion from it.

**MEASURED, and it settles Χ's gating question:**
`bazel build @paperkit_paper//:prose-projected__calc --config=memobserve` → the peak file now reads
**`5292032`** (5.3 MB), where the default build wrote `0`. So the file-calc DOES carry a real
measurement — under the config the manifest is designed to be regenerated in.

⚑ **Χ-F5.3 and Χ-F6's inversion are therefore BOTH WRONG.** I wrote *"the file-calc's peak is also
`0`, so neither source feeds the manifest"* and *"'the cells carry no peak' is not a difference —
neither carries one."* Under `--config=memobserve` the file-calc carries one.

**⚑⚑ Χ-F9 — THE CAPABILITY ALREADY EXISTS. `mem_learn.py` READS CELL PEAKS; `bibtex.bzl` NEVER
HANDS THEM TO IT.** (tick 19, 2026-09-09)

Χ-F8 scoped the work as *"teach `mem_learn` to read the cells' peaks"*. **It already does.**
`mem_learn.py:36-54` `resolution(stem)` classifies a grid cell — `if "__" in stem: return "def",
stem.split("__", 1)[0]` — and its docstring IS `Ζ·mem·def·blind`, recording the fix as already made:
*"a DEF-sweep cell is a pk_eval named `<claim>__<site>`… and **used to be skipped silently**."*
`main()` then drops zeros and names `unavailable:*` reasons separately, and emits per-resolution
defaults plus per-claim overrides. `mem_harvest.py:40-65` `peaks_for` goes further — it `rglob`s
**every** `.peak`, keys by `(resolution, claim, cell)`, and takes the MAX into `mem.sqlite`.

**The gap is one line of data flow:** `bibtex.bzl:920` builds
`ml = [":" + k + "__calc" for k in calc_claims]` — file-calcs ONLY. So the script never SEES a cell
peak, which is why the tick-15 run produced `{"claims": {}}`: every input was a file-calc holding a
clean `0`.

**⚑ Χ-F10 — OPERATOR'S QUESTION ANSWERED, AND MY "STRUCTURAL QUESTION" WAS WRONG.**
*"Does it need to make such a distinction? Aren't we talking about opaque identifiers here?"*

Measured, replaying `mem_learn`'s own `resolution`/`pow2` over all **62,579** peak files in the
paper repo:

    defaults : {'def': 64, 'file': 8}          ← the two resolutions DO separate, at top level
    claims   : 0 rows
    claims measured at BOTH resolutions : 1
    …of which the two buckets DIFFER    : 1
      prose-projected            file=8   def=64

**The identifiers are opaque and that is fine** — `_membucket` falls back to `mem[res]`, so the
per-resolution defaults work exactly as intended, and feeding cells alongside file-calcs produces
`{"def": 64, "file": 8}` with **no collision**.

⚑ The distinction the manifest cannot express is narrower than I claimed: not file-vs-def (top
level handles it) but **per-claim × per-resolution**. `manifest["claims"][claim]` is a single number
read with no resolution key, and `prose-projected` wants **8 at file and 64 at def** — an 8× spread.
Today `claims` is empty because each of those equals its own default, so **the collision is LATENT,
not active**. A third claim measured at both resolutions and differing from either default would
hit it.

⚑ **AND A SEPARATE, HARD CONSTRAINT SURFACED:** passing the cell peaks as action arguments is not
possible as-is — 62,579 paths exceeded `ARG_MAX` (`OSError errno 7`) when I tried to shell out.
`mem_learn` takes its inputs on `sys.argv`.

**⚑ Χ-F11 — THE ARG_MAX FIX IS A FILE, NOT A LONGER COMMAND LINE** (operator: *"you need to pass a
file, not a collection of arguments. Or use a file to hold argv one per line."*). Three options,
and the repo's current shape rules out the idiomatic one:

- **(A) Bazel's own param file** — `ctx.actions.args()` + `use_param_file("@%s")`, the mechanism
  built for exactly this. ⚑ **Not available as-is:** it is designed for `ctx.actions.run`, and
  `calc.bzl` uses **`run_shell` in all 14 actions** (`:167 … :713`), building command lines as
  shell strings. Measured: `grep params_file|param_file|ctx.actions.args` over `tools/` → **zero
  hits**. So this would be a NEW pattern for the repo, and would mean converting an action from
  `run_shell` to `run`.
- **(B) `mem_learn` reads a file of paths, one per line** — a `@file` / `--from` argument. Smallest
  change, no rule conversion, and it keeps `mem_learn`'s existing per-path classification untouched.
  Still needs a producer action to write the list.
- **(C) Directory walk** — the shape `mem_harvest.py:40-65` ALREADY uses: `tree.rglob("*.peak")`
  with a project filter, no path list at all. ⚑ This is why `mem_harvest` never hit ARG_MAX and
  `mem_learn` would: **one takes a tree, the other takes argv.** It is also why the on-demand
  harvest path is the one that already works end-to-end.

⚑ The ARG_MAX ceiling is therefore not an obstacle to the fix — it is **evidence about which of the
two existing tools the fix belongs in.** `mem_harvest` already solves it, already keys by
`(res, claim, cell)`, and already persists to sqlite; `mem_learn` is the one wired into the build
graph and the one that cannot scale to the cell corpus by argv.

**⚑⚑ Χ-F12 — OPTION (B) IS RULED OUT, AND THE FLATTENING IS ALREADY IN THE ARTIFACT** (operator:
*"we do not want anything flat. We want things structured, not flattened. We should not… have to
informally construct or intuit or guesstimate structure from flat data. Same as our policy around
logging — always structured, never flat."*).

A newline-delimited path list is flat, so **(B) is out as I framed it.** But the constraint bites
one level earlier than transport: **the peak ARTIFACT is already flat.**

`cellcgroup.write_peak` (`:58-63`) writes a **bare scalar** — `"37457920"`, or the string
`"unavailable:unreadable"`. No claim, no resolution, no site. Every one of those facts was KNOWN at
emission time and was **discarded into the filename**, then reconstructed downstream by
`mem_learn.resolution(stem)` doing `stem.split("__", 1)`. That is precisely *intuiting structure
from flat data*.

⚑ **The contrast is inside ONE cell, ONE action** — the same `pk_eval` writes both:

    prose-projected__bib__is_placed.eval.json
      {"claim":"prose-projected","site":"paperkit/bib.py::is_placed","flipped":false,"why":…}
    prose-projected__bib__is_placed.peak
      37457920

The eval record carries `claim` and `site` **as fields**; the peak carries the same facts **only in
its name**.

**And the reconstruction is convention, not construction.** `resolution()` takes `split("__", 1)`,
so a claim key containing `__` would be silently mis-attributed. Measured: `bibstruct --entries`
over `model/engine/projection.bib` → **28 keys, none containing `__`** (all single-hyphen). The
parse works because no author has yet written such a key — nothing enforces it. Meanwhile real cell
names carry TWO separators (`prose-projected__bib__branch_emit_anchors_arm_0`), so the delimiter is
already load-bearing and already ambiguous in principle.

**So the fix is not a transport change at all.** Make the peak a RECORD, the way its sibling
`.eval.json` already is:

    {"claim": "prose-projected", "resolution": "def",
     "site": "paperkit/bib.py::is_placed", "peak_bytes": 37457920}

— or `{"unavailable": "unreadable"}` for the honest-absence case `Τ·mem·observe·honest` already
distinguishes. Then `resolution(stem)` and its `split("__")` heuristic **disappear**, `mem_learn`
and `mem_harvest` stop deriving structure from names, and the ARG_MAX question is separable
(a directory walk over records, option (C), needs no path list at all).

⚑ This is the same defect class as `tier` (Ψ.2-F4), `emerge` (Χ), and the coarse grade (Ψ.2) —
**structure collapsed into a scalar, then re-derived by convention downstream.** Here it is a
filename doing the work of a schema.

**⚑ Χ-F13 — base64-encoded JSONL in the filename: a CORRECT solution to attribution, not the one
chosen** (operator asked *"why not base64-encode jsonl?"*).

⚑⚑ **CORRECTION TO MY FIRST ANSWER, which was wrong on the central point.** I called it *"still
intuiting structure from a flat string, just with a reversible codec instead of a fragile split"*.
Operator: *"it's not intuiting if it's bijective. It's encoding. And it's reversible."* **Correct,
and the distinction is exactly the one this ledger keeps insisting on elsewhere:**

- `split("__", 1)` is a **HEURISTIC** — lossy, convention-dependent, works only because no claim key
  contains `__` (measured: 28 keys, none do; nothing enforces it).
- base64(JSONL) is a **BIJECTION** — decode is total and exact, no convention, no ambiguity.

Collapsing both under "intuiting" was the same conflation-of-two-things-under-one-word this ledger
flags in `tier`, `emerge` and the coarse grade. **It let me dismiss the proposal with an argument
that does not apply to it.** The encoding genuinely solves the delimiter problem, and solves it
COMPLETELY rather than by luck.

**What survives as an objection is narrower, and it is about COST and CONTENT, not correctness:**

1. **⚑ THE DECIDING ONE — the RECORD stays flat either way.** Encoding the NAME fixes ATTRIBUTION;
   it does not make the ARTIFACT self-describing. `write_peak` still emits `37457920`. Putting the
   fields IN THE FILE fixes both, and costs less — **the reader already opens every peak to get the
   number**, so there is no extra I/O, and the result is `jq`-able and consistent with the
   `.eval.json` **its own cell already writes**.
2. ~~**`NAME_MAX` = 255 bytes, base64 inflates 4/3** → ~191 bytes of payload… tight, and the failure
   lands at EMISSION as a build error.~~ **⚑ WITHDRAWN — MEASURED, AND IT FITS WITH ROOM TO SPARE.**
   Operator: *"So base64 binproto if you have to."* Measured over **all 62,579 real peak identities**
   (`scratchpad/probe_name_encodings.py`), stem budget 250 bytes:

   | encoding | max | median | over budget |
   |---|---|---|---|
   | `json+b64` | 168 | 112 | **0 of 62,579** |
   | `proto+b64` | **124** | 72 | **0 of 62,579** |
   | `proto+b32` | 152 | 88 | 0 of 62,579 |
   | current (`__`-joined) | 86 | 45 | 0 of 62,579 |

   Longest identity: `depth-annotates-without-reordering__tests__fixture_model__data_drop___AUTHORED_arm_0`.
   ⚑ **My "~95 bytes, tight" was an ESTIMATE from one hand-picked example**, and the real
   distribution has ~2× headroom even for plain `json+b64`. Protobuf halves it again by dropping
   field names and punctuation. **The byte objection was wrong, and measuring it took one probe I
   should have run before asserting it.**
3. **Readability at scale.** `declare_file` requires a name regardless, and encoding identity into
   it makes every label in a **62,579-target** build opaque in progress output, error messages and
   `bazel query`. A real cost against a real benefit — not a knockdown.

⚑ **THE HONEST COMPARISON, after two of my three objections were withdrawn under measurement:**
base64-binproto in the name is a **correct, bijective, and comfortably-sized** solution to
attribution. It was never a heuristic (Χ-F13 correction) and it does not blow `NAME_MAX` (above).
**Exactly ONE argument separates the two options, and it is not about correctness:**

> Encoding the NAME fixes ATTRIBUTION. Putting the fields IN THE FILE fixes attribution **and** the
> flat CONTENT, for free — the reader already opens every peak to get the number, so it is the same
> I/O, and the artifact becomes `jq`-able and consistent with the `.eval.json` **its own cell
> already writes**.

The remaining cost of the name-encoding route is readability at 62,579 targets — real, but a
trade-off, not a knockdown. A codec in the name earns its keep when the filesystem is the sole index
and identity must be recovered WITHOUT opening files; that is not this case, because the number
itself is in the file.

**⚑ Χ-F14 — jsonl+compression+b64 (operator). MEASUREMENT DELEGATED; the REUSE MISS is recorded now.**
Operator: *"json+b64 is the best solution of the ones discussed so far; it fits, it's not
complicated. I'll go one step further and suggest jsonl+compression+b64. Though I don't know what
the right compression algorithm for something whose max compressed size is going to be 192 bytes.
Some kind of arithmetic coding?"*

⚑⚑ **I STARTED HAND-ROLLING A CODEC COMPARISON. The operator stopped me: "there are some stellar
compression experiments in the eliza code tree in substrate."** There are **~35 codec modules**
under `substrate/scratch/eliza/eliza/` — including `arith.py` (a 32-bit range coder, standalone,
round-trip verified) and `codec.py` (Markov-3 adaptive AC, `encode(data) -> bytes`) — plus
`CODEC.md` with benchmarks already run against gzip/bzip2/xz. **This is the second reuse miss
today**, after `mem_learn` already classifying cell peaks (Χ-F9); the `summit` skill exists for
exactly this pre-flight and I did not fire it either time.

⚑ **AND THE EXISTING BENCHMARKS DO NOT ANSWER THIS QUESTION — a real gap, not a lookup.**
`CODEC.md` measures **10KB and 100KB**, where LZ substring matching dominates and eliza's flat-I
*loses* to gzip by ~25% (its own "Honest findings" say so: *"Standard compressors beat it because
they exploit either long-range substring matches…"*). **Our payload is ~100 bytes**, where LZ has
nothing to match and header/framing cost dominates instead — so the ranking could plausibly invert,
and that regime is unmeasured in that tree.

⚑ Second operator correction, taken: *"if you're going to do comparison surveys, use all ten of my
cores"* — the probe now parallelises with `ProcessPoolExecutor` across `os.cpu_count()`.

Probe: `scratchpad/probe_compress_names.py`, run under `~/github/substrate/.venv/bin/python`
(eliza's package `__init__` imports numpy; the system python3 lacks it). Compares raw json, zlib -9,
zlib raw (no header), bz2, lzma raw, and eliza's Markov-3 AC — each + urlsafe base64 — over all
62,579 real identities. **Result pending.**

⚑ **PROCESS NOTE, and it is the tick's real lesson:** I raised three objections; **two were wrong**
(one a category error corrected by the operator, one an unmeasured byte estimate refuted by a
one-probe measurement). Both were assertions I could have checked before making. `absence-is-a-
reading-about-the-instrument` has a sibling this ledger keeps rediscovering: **a size estimate is a
reading about the estimator.**

Measured: `grep -rn 'b64|base64'` over `tools/` and `paperkit/` → **zero hits**. No precedent in the
tree either way, while the structured-sibling pattern is already present in the same action.

**⚑⚑ Χ-F8 — THE GRID CELLS CARRY REAL PEAKS TOO, AND THEY ARE 7× LARGER. Χ'S GATING QUESTION IS
ANSWERED.** (tick 18, 2026-09-09). Built `@paperkit_paper//:prose-projected__dcalc
--config=memobserve` — 2,203 cells — then censused every `.peak` file:

    files: 991     measured 730 · zero 261 · malformed 0
    min  =  5,292,032  (prose-projected__calc.peak — the FILE-CALC)
    max  = 39,190,528  (…__project__data_drop__REGISTRY_arm_0)
    mean = 37,301,896  over 730 cells

The 261 zeros are cells still cached from the pre-observe build (different action key, not rebuilt
by this target) — exactly the "no stale measured/0 peak crosses configs" property `.bazelrc:130-132`
describes, working.

**So both sources measure, and the grid measures MORE:** a def cell peaks at ~37 MB against the
file-calc's 5.3 MB, because it stages a mutated engine and runs the check against it. **The
file-calc is the MINIMUM of the population** — which makes `Ζ·mem·def·blind`'s stated worry
(*"the `def` bucket could only ever be a cold-start floor"*) the real one: sizing def cells from
file-calc peaks would under-reserve by ~7×.

⚑ And that is precisely what `calc.bzl:139-144` already says the grid's peak channel was ADDED to
fix: *"The def resolution is the EXPENSIVE one — 18-25 minute cells — and it was the one resolution
with **no measurement channel at all**: pk_eval returned DefaultInfo only, so `mem_learn` aggregated
file-calcs and the `def` bucket could only ever be a cold-start floor."* **The channel exists. What
does not exist is `mem_learn` reading it** — it still aggregates file-calcs only (`bibtex.bzl:920`).

**Χ's decision, now fully evidenced:** the file-calc cannot simply be dropped for grid claims,
because `mem_learn` depends on its peak — but the peak it supplies is the WRONG ONE for sizing the
def sweep, and the right one is already being written by the cells. The work is not "delete the
file-calc" (Χ-F4's framing) nor "prove the peak is worthless" (Χ-F5's) but **teach `mem_learn` to
read the cells' peaks** — which `Ζ·mem·def·blind` refused on cost grounds that Χ-F5.1 refuted by
measurement (2,203 cache hits, 6.8 s).

⚑ **MEASUREMENT ERROR, RECORDED:** my first census used `find … -exec cat {} +`, which CONCATENATED
peaks (the files carry no trailing newline) and produced values like `36098048373760000` — two peaks
glued into one. I nearly recorded that as corrupt data. The per-file reader
(`scratchpad/peak_census.py`) is the honest collection, and it also distinguishes the three states
`Τ·mem·observe·honest` exists to keep apart (integer / `unavailable:absent` / `unavailable:unreadable`).

⚑ **The general lesson, and it is this session's recurring one at a new address:** a `0` from an
instrument that is TURNED OFF is not a measurement of zero. `absence-is-a-reading-about-the-
instrument` — and I applied that skill's own vocabulary to Χ-F6 while getting the reading backwards,
because I never asked whether the instrument was ON.

**⚑⚑ Χ-F6 — THE `0` PEAKS ARE STRUCTURAL, NOT THIS MACHINE. MEASURED (tick 16, 2026-09-09).**
⚑ **SUPERSEDED BY Χ-F7 — the probe facts below are correct, the conclusion drawn from them is not.
Kept per rule 6.**
Χ-F5 ended on *"a peak of `0` may be this configuration rather than the tree's steady state"*. It
is not. The chain, each link measured:

1. **The host is fine.** `tools/cgroup-scope probe` from a normal shell → `subtree_control: cpu
   memory pids`, `writable: yes`, **`verdict: usable`**. And a live cgroup's `memory.peak` reads
   **6,822,768,640** — the interface works and does not naturally report `0`.
2. **`0` is a SUCCESSFUL read, not a failure.** `cellcgroup.write_peak` (`:58-63`) writes
   `"unavailable:unreadable"` when `peak_bytes()` returns `None`; `peak_bytes` (`:37-55`) returns
   `None` on any `OSError`/`ValueError`. So a file containing `0` means `memory.peak` was READ and
   CONTAINED ZERO — a cgroup that was never charged.
3. **⚑ THE PROBE FAILS INSIDE THE SANDBOX.** Run under `linux-sandbox` with the same mount set the
   cells use (`-M /bin -M /etc -M /lib -M /lib64 -M /usr` — note **no `/sys`**):

       verdict : UNUSABLE (exit 3) — caller must degrade
       delegating parent : <none>  (no v2 ancestor whose cgroup.subtree_control lists memory)

   The same probe that says `usable` from a shell says `UNUSABLE` from a cell, because the sandbox's
   mount namespace hides the delegating parent.
4. **So `PK_CAP` is EMPTY in every sandboxed cell.** `calc.bzl:124-125` sets it only if the probe
   succeeds; `:121-123` documents the intended degradation — *"where it is not, PK_CAP is empty and
   the command runs bare — the same command either way, so the action key does not change with the
   box."* The payload then runs OUTSIDE the scope `write_peak` measures, and reads `0`.

**Net: every peak in the tree is structurally zero under `linux-sandbox`, and the degradation is
SILENT.** The graceful-degradation design is doing exactly what it says — and the cost is that the
memory manifest is fed zeros by construction, which is why `mem_learn` produced `{"claims": {}}`
from 82 sweeps (Χ-F5.4). The 3 entries in the committed `paper/mem.json` were measured under some
other execution strategy (`--config=memobserve`, per `bibtex.bzl:902-904`, which the comment says
must run *"in a clean output base"* — plausibly non-sandboxed).

⚑ **This RESOLVES Χ's gating question and INVERTS one of its premises.** Χ-F4 kept the file-calc
because `mem_learn` depends on its peak. That dependency is real in the graph and **empty in
measurement under the default strategy** — the file-calc supplies `0`, exactly as the grid cells
would. So *"the cells carry no peak"* (Χ-F5.2) is not a difference between the two sources: **NEITHER
carries one here.** The remaining honest difference between them is the dependency-count economics,
which Χ-F5.1 already refuted with cache hits.

**Still not acting**, and now for a precise reason rather than a hedge: the decision needs one run
under `--config=memobserve` to see which sources carry real peaks when the capper IS usable. That is
the configuration the manifest is designed to be regenerated under, and it is the only one where
"which source feeds the manifest" is a live question. ⚑ Everything measured so far was under the
DEFAULT strategy, where the answer is "neither".

⚑ **SUPERSEDED HEDGE (kept per rule 6):** every peak reading here is `0`, which is exactly the shape
`absence-is-a-reading-about-the-instrument` warns about —
applied to MY OWN measurement. A `0` peak may be this configuration (no active `cgroup-scope`
probe) rather than the tree's steady state, and `mem.json`'s 3 committed entries prove SOME machine
once measured real values. **What is settled: the quoted justification is not the reason, the cost
argument is refuted, and Χ-F4 should not have rested on either.** What is needed before removing
anything: one run on a machine where the cgroup probe is live, to see whether the file-calc's peak
is genuinely load-bearing or whether the grid's cells could carry it.

**⚑ Χ-F1 — "WHY DO WE EVEN HAVE THAT LEVER?" (operator). ⚑ SUPERSEDED BY Χ-F2 ABOVE — this answer
quotes a comment governing `__dcalc`, not the unconditional `__calc` that boundaries sits on. Kept
per rule 6.**

`bibtex.bzl:853-861`, the `elif emerge` branch: a calc claim with **no engine witness** (a
`cmd:`/`result:` check — the comment's example is a grep over a static asset) has no closure, so
`closure.py` enumerates nothing and the grid condition at `:747` is FALSE **even inside an emerge
project**. Its engine sensitivity is empty by construction, and `pk_calc` computes exactly
`{claim, baseline, sens:∅}`. The load-bearing sentence:

> *"pk_cohere consumes a `__dcalc` for EVERY emerge calc claim uniformly (**the grid just optimizes
> the witness subset — a projection, not a special case**)."*

So the answer to *why have the lever* is: **`pk_calc` is TOTAL over calc claims; the cell grid is
defined only where a closure exists.** Removing it would leave witness-less claims with no calc at
all. That is a genuine reason, and it is NOT the vestigial-fallback story I half-expected.

⚑ **But it does not cover `boundaries`.** Its 49 checks are `cmd:python3 ../paperkit/tests/
boundaries_*.py` — every one runs an engine witness with a real closure (tick 4 measured
`bnd-clamp`'s fingerprint at **7 files**). So boundaries is not the case `pk_calc` exists to serve;
it falls to `pk_calc` only because `emerge` is unset, and `emerge` is unset because it is welded to
the ∂² gate. **The lever is justified; boundaries' position on it is not.**

⚑ **AND THERE IS A SECOND WELD, which is the real obstacle.** `_closures` (`bibtex.bzl:442-450`)
computes a witness's closure *"per emerge project"*, from the project's `[checks.claim]` witness
module — and returns `[]` when *"the project declares no claim: type"*. **`boundaries/paper.toml`
declares no `[checks.claim]` custom type at all** (tick 4: its checks are bare `cmd:`). So even
setting `emerge = True` would yield empty closures and NO grid — the flag alone cannot decompose
boundaries' actions.

**Revised options, and X1 is now clearly right:**
- **(X1)** separate the axes — but the work is larger than an attr: the grid needs a closure, and
  `_closures` derives one only from a declared claim-witness module. Boundaries would need either a
  `[checks.claim]` type or a closure derived from the `cmd:` target directly.
- **(X2)** `emerge = True` on boundaries — ⚑ **now known to be INSUFFICIENT**, not merely risky. It
  would turn on `pk_cohere` and still emit no cells.
- **(X3)** leave it — weaker than it looks (the same shape cost `rpt-delta-out` 33 minutes), but
  now also the only option that does not require new closure machinery.

**STOPPED — this needs an owner decision**, and it is the same shape as Ω (tier) and Ψ.2-F4: one
knob doing several jobs. The options, unpriced because pricing them means measuring the coherence
gate on boundaries first:
- **(X1)** separate the axes — a distinct attr for the cell grid, leaving `emerge` to mean the ∂²
  gate. Correct, and touches the generator.
- **(X2)** set `emerge = True` on `boundaries` and accept whatever `//:cohere` reports there — the
  red, if any, is the measurement.
- **(X3)** leave it: boundaries' 102 actions finish in ~4 minutes, so the decomposition buys wall
  clock on ONE project's tail, not correctness.

⚑ Worth noting X3 is weaker than it looks: the SAME serial-inside-one-action shape is what made
`rpt-delta-out` take 33 minutes (Ψ-F2), and that one is not a tail.

**✅ Ψ.2-F2 — FIXED (tick 12, 2026-09-09): the tristate now survives serialization.**

`grader._Unreachable` is an `int` subclass returning `0` — falsy so `if not baseline` holds,
distinguishable IN PROCESS, and byte-identical to `False` once JSON'd. Its own docstring says *"the
ONE caller that builds a grade record"*; there are now TWO, and the Bazel one is where it was lost.

**The sentinel cannot survive JSON, so the AXIS is carried beside the value** — on the
`decisions_unasserted` model directly below it in the same function: an orthogonal key, present only
when it applies, that names the gap and never moves the rung.

- `discriminate.py` — `if rec.get("baseline") is UNREACHABLE: calc["reachable"] = False`, plus the
  import (`UNREACHABLE` was not bound in that module — my first edit would have `NameError`'d;
  caught by `pycodemod --binding` before running anything).
- `tools/read_grade.py` — `reachable=c.get("reachable", True)`. **Absent ⇒ reachable**, the honest
  default for every record written before the axis existed.

**Verified end-to-end** (`scratchpad/probe_reachable_roundtrip.py`, simulating
grader → discriminate → read_grade through the REAL script), 5/5 properties:

| property | result |
|---|---|
| grades AGREE (`broken` both ways) — the axis names the gap, never moves the rung | ✅ |
| baselines DIFFER (`refuted` vs `unreachable`) — the tristate survived | ✅ |
| unreachable does NOT claim *"repo is not green"* | ✅ |
| refuted DOES claim it (unchanged) | ✅ |
| legacy record with no `reachable` key still reads `refuted` | ✅ |

⚑ The false statement `grade.py:86-92` records as **measured twice on 2026-08-26** is now closed at
the one boundary the Bazel pipeline runs through. Ψ-F1 (carrying the full reading) is what made it
visible; this closes it.

**⚑⚑ CONFIRMED ON THE REAL GATE, and it corrected a live misdiagnosis on first run.**
`@paperkit_boundaries//:adequacy` — same three reds, but `bnd-wheel` now reads:

    "baseline": "unreachable",
    "why": "check could not be REACHED in a pristine sandbox — its toolchain or a resource it
            needs was unavailable, so nothing was established about the claim
            (THIS IS NOT A STATEMENT THAT THE REPO IS RED)"

Previously `"refuted"` / *"repo is not green"*. ⚑ **This independently confirms tick 4's
hand-diagnosis** — I recorded `bnd-wheel` as needing the BUILT WHEEL, which the pristine sandbox
does not stage; the engine now states that itself, in the record, without a human reading the
suite. And `bnd-closure-script` / `bnd-dispatch` correctly stay `refuted`: those are genuine
failures. **The tristate distinguishes them where one string used to cover all three.**

**✅ Ψ.2-F8 — RESOLVED (tick 14): it is KRON (Kron/Schur node elimination), and it is THE SAME
OPERATION as gcalculus's star-mesh — implemented three times in the jea Python.**

Not Krohn-Rhodes, not Kronecker product. **Kron reduction** = eliminating a node from a conductance
network by Schur complement. `jea_onegraph.py:59-64`:

    def series_schur(a, b):
        """SCHUR-eliminate the shared middle node of a 2-edge series path -> equivalent conductance
        a·b/(a+b).  THE Kron reduction step, as a graded-ℚ WEDGE on the carrier: mul (a·b),
        add (a+b), recip (swap), mul.  Commutative + associative -> FOLD a series path…"""

⚑ **That is `GValueAsQ`'s `gand` (`a*ℚb *ℚ recip(a+ℚb)`, Ψ.2-F6) and gcalculus's degree-2
`eliminate` (Ψ.2-F5), on the graded-ℚ carrier — three repos, one operation.** The unification
ledger states the identity: *"`series_schur(a,b) = a·b/(a+b)` = the SCHUR/Kron reduction as a
graded-ℚ WEDGE on the carrier … **W4 `series_schur == el-atlas g_eff`**"*
(`jea_unification_ledger.md:206-207`), and names the direction: *"branchless lets the hardware-model
**KRON REDUCTION** be the …"* (`:190`), *"retiring the el-atlas Python Kron silo"* (`:197`).

**Census:** `--binding series_schur` → **4 sites** — `jea_circuit.py:66`, `jea_onegraph.py:59`,
`metalanguage/jea_picircuit.py:46`, plus an import in `metalanguage/sql_lift.py:367` (**it is
lifted into SQL**). The tree already flags the duplication: `metalanguage/README.md:55` —
*"`jea_picircuit` **reimplements** the onegraph Kron/Schur"*.

**⚑ INSTRUMENT FINDING, and it cost four probes.** My original `grep -rln 'kron'` over `jea/`
returned **11 files** and I read that as code. Three structural readers disagreed:
`--binding kron` → 0, `attr_reads.py kron` → **0 in 1587 files**, `--literal kron` → 0 in 140.
**The readers were right.** Every hit is in **markdown** (`jea_unification_ledger.md`,
`metalanguage/README.md`, `CONSOLIDATION_MAP.md`, `evolution/00_SYLLABUS.md`) — the concept is
DOCUMENTED under `kron` and IMPLEMENTED under `series_schur`. A name search for the concept's name
finds only its prose; the code is reachable only by the operation's name.
⚑ Also: `pycodemod --attr` is RETIRED and **refuses rather than answering** — *"a superseded reader
that still RESPONDS is worse than a deleted one: it answers whoever reaches the old spelling first,
wrongly"* — naming `substrate/attr_reads.py` as successor. That is
`absence-is-a-reading-about-the-instrument` enforced by the tool itself.

**⚑ Ψ.2-F7 — CORRECTION TO F6(2): the name is likely KRONECKER, not Krohn, and it is in the JEA
PYTHON, not the Agda** (operator, 2026-09-09). ⚑ **Half right — see F8: the tree, yes; the name is
KRON, not Kronecker.** Kept per rule 6. My agent searched `krohn|Rhodes|cascade|flip-flop|
aperiodic|wreath` across 3598 Agda modules — **wrong name AND wrong tree**. `grep -rln 'kron|Kron'`
over `jea/` returns **11 files**, including `jea_circuit.py` (conductance networks),
`metalanguage/numpy_law_bridge.py`, `metalanguage/sql_lift.py`, `jea_onegraph.py`,
`jea_navigator.py`, `metalanguage/jea_picircuit.py`, `evolution/05_control/jea_live_cost.py`, and
three docs (`jea_unification_ledger.md`, `CONSOLIDATION_MAP.md`, `evolution/00_SYLLABUS.md`).

⚑ **The F6(2) negative stands only as written** — "Krohn-Rhodes is absent from the Agda names and
comments" — and is USELESS for the question actually asked. A negative is a reading about the
instrument's REACH, and this instrument was pointed at the wrong corpus under the wrong spelling.
NOT YET INVESTIGATED; `jea_circuit.py` + `numpy_law_bridge.py` are the two to open first, given
`numpy_builders.py`'s four-gauges-through-one-contraction is already the established coarse-view
mechanism in that tree.

**✅ Ψ.2-F6 — LANDED. And it REFUTES my premise; F5's comparison INVERTS.**

**(1) The resource-counting half is NOT sympy-only. It is derived and machine-checked**, in the same
`--safe --without-K`, zero-postulate module as the antipode law:

    gor a b = a +ℚ b                                      GValueAsQ.agda:83-84   (parallel = ℚ addition)
    gor-comm / gor-assoc                                  :88-92
    gor-non-idempotent : (gor 1ℚ 1ℚ ≈ℚ 1ℚ) → ⊥            :96-97   proof: `()`
    gand a b = (a *ℚ b) *ℚ recip (a +ℚ b)                 :115-116 (series)
    demorgan : recip (gor a b) ≈ℚ gand (recip a) (recip b) :124-139

⚑ Non-idempotence is proved by **ABSURD PATTERN** — refuted by unification, not by computing a
number. `:94-95` names it *"the calculus's signature (contraction halves / Landauer ±ln2)"*. The
module's scope block: *"The whole rational G-space conductance algebra is machine-checked."*
I told the agent the resource half was probably sympy-only. **Wrong.**

⚑⚑ **THE F5 COMPARISON INVERTS:** substrate has **the algebra with its laws proved** (comm, assoc,
non-idempotence, De Morgan, antipode) **and no network reduction**; gcalculus has **the network
reduction with its invariant tested** (`r_eff` under star-mesh) **and proves no algebraic law** — the
agent found no De Morgan theorem in `solver.py`. **Neither is the other's superset.** Do not cite F5
as "gcalculus has the machinery"; it has half of it.

**(2) Krohn reduction — ABSENT**, under every spelling, control passing, **3598 modules scanned**:
`krohn` (0 names), `[Kk]rohn|KROHN|[Rr]hodes` (0 comment lines), `cascade decomposition|flip-flop|
aperiodic` (11 lines, all `aperiodic` in the COINDUCTIVE sense — a grading axis on
`ExtrudeCoEmitGraded`, no semigroup use), `[Ww]reath` (9 hits, all `⟡rig-UP-wreath` — a wreath
ACTION of a symmetric-rig tensor on Lehmer codes, **not** a wreath-product decomposition theorem).
⚑ This is a negative over NAMES AND COMMENTS, the widest route the tool offers — not over concepts.
A Krohn-Rhodes-shaped construction under other vocabulary would not appear.

**(3) ⚑ CANONICAL FORM AS COARSE VIEW — PRESENT, and STRONGER than gcalculus's.**
`ℚ-Canonical-bezout : Canonical ℚ-Quotient` (`CanonicalBezout/RatCanonicalBezout.agda:30-36`). The
invariant is a **RECORD FIELD**, not an assertion in a test (`Algebra/Quotient/Canonical.agda:34-40`):

    ≈-canonical          : (a : A) → a ≈ canonical a          the VALUE is preserved, ∀ over ℚ
    canonical-idempotent : canonical (canonical a) ≡ canonical a   a RETRACTION
    canonical-respects-≈ : a ≈ b → canonical a ≡ canonical b   ⚑ the coarse-view property proper:
                                                                two representations of one value map
                                                                to the SAME form under propositional ≡

Certificate: `reduced-≈⇒≡-bezout` (`ReducedApproxEqBezout.agda:38-56`) — two reduced rationals that
are `≈ℚ`-equal are propositionally equal, via Euclid both ways + `∣-antisym`. And
`EEAReduce.agda:13-18`: *"the EEA fold-table's gcd (and the Bézout cofactors it carries) are the
PRECISE tools that reduce a rational to lowest terms with **NO new division**"* — the cofactors are
*"projections of the SAME trace the gcd-fold collapses"* (`:69-74`).
⚑ **TWO independent uniqueness routes over ONE trace** (Bézout, and CF-shape injectivity
`:98-108`), with `routes-agree` (`RouteAgreement.agda:10`) equating them as a TERM.

**⚑⚑ THE DISTINCTION TO CARRY FORWARD — two different answers to "coarse view over fine data":**

| | gcalculus | substrate |
|---|---|---|
| coarsening | `eliminate` (star-mesh) | `reduce` (canonical field) |
| invariant | `r_eff`, asserted on fixtures | `≈-canonical`, a FIELD, ∀ over ℚ |
| certificate | gauge word | Bézout cofactors / EEA trace |
| **recoverable?** | **YES — a RETRACT with a stored inverse** (`unwind` replays) | **NO — a QUOTIENT with a stored certificate**; the representation IS lost, and Bézout certifies the loss was exactly the gcd |

⚑ And `ResidueIsBezoutGCD` says WHICH REGIME YOU ARE IN: `gcd ≡ 1` is the case where the fibre is
already a point.

**(4) YES — the residue couples to grading, on two separate channels.**
- **Bézout is a DISCHARGE OBLIGATION in the evidence lattice.** `ElAtlas.agda:102`:
  `Statement NOE = {a b g : ℕ} → EEATrace a b g → BezoutℤWitness a b g`, discharged at
  `Proofs.agda:63` by `proof-tier NOE = bezout-ℤ`. `proof-tier` is TOTAL, so *"the totality of
  proof-tier then FORCES a witness or the build breaks"* — `bezout-ℤ` keeps the evidence module
  compiling. ⚑ *"the gcd g is the conserved charge, and the Bézout coefficients are the conserved
  momenta"* (`:98-101`).
- **DEGREE IS THE COST.** `CenterIsStarGraded.agda:6-10`: *"the degree IS the cost of the
  obstruction (the off-balance Wheatstone coupling), **not a binary wall**."* The `Coherent`
  witnesses carry the degree as their first component (`1` and `0`, `:52-60`) — **cost as data in
  the proof term.** ★ = G_NOT = the conductance↔resistance swap (`StarIsGNot.agda:9,20,44`).
- ⚑ **STATED HOLE, do not borrow as proved** (`CenterIsStarGraded.agda:21-24`): a NUMERAL carrier
  where *"the degree varies with actual conductance imbalance"* is residual. Degree-as-cost is built
  abstractly; conductance-indexed degree is not.
- **COUNTERWEIGHT — the scalar cannot carry the verdict.** `NedgeShadow.agda:74-89`:
  `bias-conflates-U-V` (conflict and ignorance both give G = 1) and
  `bias-cannot-carry-verdict : (d : Bias → Verdict) → (∀ e → d (bias e) ≡ verdict e) → ⊥`.
  But `:92-131` qualifies: the scalar is *"a TRUNCATED LOOK at a non-lossy WEDGE"*, with
  `recode`/`unrecode` round-tripping and `verdict-survives-recode` proved. **The residue is rotated
  into a hidden channel, never destroyed — only the LOOK truncates.** Same shape as (3)'s two
  regimes, one tier up.

**PROVENANCE: a proof, not a sketch.** `Substrate.Logic.Evidence` — 54 modules scanned, **0
postulates, 0 holes, 0 non-`--safe`**. `Substrate.Algebra.Q` — 96 scanned, 1 finding
(`QToRCrossMix` widens with `--guardedness`; not on any path cited). Two self-declared holes:
L-space (`GValueAsQ.agda:146-155`, buildable, prior "out-of-scope" reading explicitly RETRACTED) and
the numeral graded carrier above. ⚑ Three files in scope were NOT opened
(`GValueLSpace/Properties`, `WitnessTower/EEAUnitBezout`, `EEAFoldTable`, `Q/HetReduceBezout`) —
treat as unread, not as confirmations.

⚑ **INSTRUMENT NOTE, worth keeping:** the agent's first two `--prose` calls returned *"0 modules
scanned"* because `-i` was consumed as a subtree prefix — a blind scan reading as a NEGATIVE. It
caught this only because the count was 0 rather than 3598. **Every negative above is from a re-run
that scanned 3598 modules.** Read the denominator (standing rule 10), now at the tool-invocation
level.

### ⏳ Ψ.2-F6 — the ORIGINAL open note (superseded above, kept per rule 6)
⚑ Ψ.2-F5 below answers from `~/github/gcalculus` ONLY. The substrate half — which the operator
pointed at twice — **never came back**, and I recorded F5 without noticing (the agent's own footnote
said a background search was still running). Re-dispatched, scoped to substrate.

**Operator's pointer, recorded verbatim so it is not lost again:** *"`Substrate/Logic/Evidence/` —
an evidence tree, which is the right neighbourhood for grading. `GValueAsQ` is the
conductance-values-as-rationals carrier. That's also going to be critical as it relates **krohn
reduction, bezout and EEA**."*

**What I read first-hand before handing it back** (so a later reader need not re-open these):
- `Logic/Evidence/ElAtlas/ResidueIsBezoutGCD.agda` — COMPLETE, zero postulates, `--safe
  --without-K`. The dichotomy: `gcd ≡ 1` ⟹ **ORTHOGONAL**, cross-term vanishes
  (`orthogonal-no-residue : cross crt-mix e₁ e₂ ≡ 0`), and the EEA trace bottoming at 1 IS the
  Bézout certificate of the clean split; `gcd > 1` ⟹ **GRADED RESIDUE**
  (`residue-from-shared : cross numeral-mix 2 2 ≡ 4`), *"the obstruction's cost"*.
  ⚑ **THE RESIDUE IS THE GCD'S DEVIATION FROM 1, AND EEA COMPUTES IT.**
- `Logic/Evidence/GValueAsQ.agda` — a G-value is a POSITIVE ℚ `(suc na')/(suc db)`; balance is
  `1ℚ`; the antipode is the reciprocal; and the antipode constraint `G·G(¬P) ≈ 1` is ℚ's
  multiplicative-inverse law, machine-checked over the ℚ-setoid `≈ℚ`. ⚑ **DERIVED, not postulated** —
  explicitly contrasted in its own header with the Drive spec `NedgeGCalculus`, which POSTULATES the
  scalar and proves no law (OB-6; see `Verdict/NedgeShadow.agda`).

**The four questions still open** (asked of the agent): (1) is the NON-IDEMPOTENT `OR(a,a)=2a`
formalised in the Agda at all, or only the multiplicative/antipode half — i.e. is the
resource-counting half sympy-only? (2) is **Krohn reduction** present under any spelling, and what
invariant does it preserve? (3) ⚑ the load-bearing one — is EEA-reduction-to-lowest-terms stated and
PROVED as a canonical form with a preserved invariant plus a Bézout certificate
(`Algebra/Q/Properties/CanonicalBezout/`, `EEAReduce.agda`)? That would be the Agda counterpart to
gcalculus's star-mesh `r_eff` preservation — **coarse view over fine data with a stated invariant**.
(4) is the graded residue ever read as EVIDENTIAL STRENGTH, or is it purely algebraic?

⚑ Do not treat F5 as the whole answer to the operator's question until F6 lands.

**⚑⚑ Ψ.2-F5 — GCALCULUS HAS THE COARSE-VIEW MACHINERY, FULLY, AND IT IS THE MODEL.**
⚑ **HEADING OVERSTATED — SEE F6.** "Fully" is wrong: gcalculus has the network REDUCTION with its
invariant tested and proves **no algebraic law**; substrate has the ALGEBRA with its laws proved
(non-idempotence by absurd pattern, De Morgan exact) and **no network reduction**. Neither is the
other's superset. The retract-vs-quotient table in F6 is the corrected reading. Kept per rule 6.
The operator's question — *"can gcalculus's resource-aware logic and nodal reductions construct
coarse views over fine data?"* — answers YES, with three separated records where paperkit has one
scalar.

**Star–mesh node elimination** (`gcalc/solver.py:99-122`), `y_ij = y_i·y_j / Σ_k y_k`: removes a
node, replaces its star with a mesh over its neighbours — a strictly coarser network. Series and
parallel are not separate reductions; parallel is `G.add` (`solver.py:42`) and degree-2 elimination
IS the series rule, both subsumed by `eliminate`.

**The invariant is STATED AND TESTED**, not asserted: two-terminal effective resistance `r_eff`
(`solver.py:404-410`), preserved EXACTLY over `Fraction`, checked by
`eliminating_a_node_preserves_the_answer` (`upstream/acceptance.py:528-534`) and registered in
`claims.md:57`.

⚑ **THE STRUCTURE PAPERKIT NEEDS — three records, never one scalar** (`solver.py:62-79`):

    as_gauge() → ("eliminate", witness)      INVERTIBLE — a word in a group
    as_cost()  → ("eliminate", q_emitted)    a MEASUREMENT — a value in a monoid

*"`q_emitted` is a statistic and belongs in the cost ledger — it can undo nothing, so it is not a
witness."* The reduction is a **RETRACT, not a discard**: `_undo_eliminate` (`solver.py:82-96`) and
`unwind` (`:377`) replay the gauge word in reverse to recover the fine data. And the split is
measured both ways — `elimination_order_changes_the_cost_not_the_answer` (`acceptance.py:580-596`)
asserts two orders agree on `r_eff` AND that the costs differ.

**So the discipline is: ANSWER, COST, and ROUTE are three records.** That is exactly what
`paperkit.grade` states four times in prose — `CORRO_C`, `DECISIONS_C`, `RESOLUTION_C`, `BASELINE_C`
each "names the gap, never lowers the rung" — and exactly what `coherence.py:500` breaks by folding
a measurement into a rung, and what Ψ.2-F2 breaks by serializing a tristate as a bit.

⚑ Also relevant to Δ: `Obstruction` (`solver.py:426-484`) is a **refusal to collapse** — when local
patches fail to glue it returns an H¹ class with a `kind` and a `rank`, not a boolean, and its
docstring records that the previous single-`rank` reading CONFLATED two failures and that the
obvious repair would have shipped `0` — the glue value — for patches that do not glue. `__bool__`
returns `False` so it is falsy without being a bool: the same shape as `UNREACHABLE`, done right.

**⚑⚑ Ψ.2-F1 — NON-IDEMPOTENCE *IS* THE RESOURCE SEMANTICS (operator, 2026-09-09).**
*"'resource-aware' as a named concept is absent from gcalculus — correct. However, it's manifest
from the fact that gcalculus is not idempotent."*

`OR(a,a) = 2a` means the algebra **COUNTS USES**: two parallel copies of a thing are not one thing.
That is a resource semantics falling out of the ALGEBRA rather than annotated on top — so searching
for the phrase finds nothing while the property is everywhere. ⚑ I had already recorded this exact
fact (Δ-F6, the *"mass shadow"*, `jea_strictify_gcalc.py:38-41`) as a CYCLE-fixpoint property and
did not see it was the resource reading.

**And it bears directly on Ψ.2.** `sensitivity_residual` reports
`collapse = behavioral − signatures` — a **MULTIPLICITY** measurement: how many witnesses share a
fingerprint. But its grade carrier is `RANK_C` folded with `min`, which is **IDEMPOTENT**
(`min(x,x) = x`), so multiplicity is invisible to the carrier while being exactly what the face
counts. The face is measuring something its own grade algebra cannot represent — the Δ-F5/F7 defect
(total order vs poset, tropical collapse) appearing a third time, now on the multiplicity axis
rather than the incomparability axis.

⚑ **SCOPE CORRECTION (operator):** gcalc/gcalculus code also lives in the SUBSTRATE repo — 
`agda/Substrate/Logic/Evidence/{GValueAsQ,ElAtlas/CenterWitness,Verdict/NedgeShadow}.agda`,
`agda/Substrate/Foundation/Hedberg/DecidableUIP.agda`, and `jea/{jea_strictify_gcalc,jea_check,
jea_regression_gate}.py`. Note **`Logic/EVIDENCE/`** — the relevant neighbourhood for grading. Any
"absent from gcalculus" verdict scoped to `~/github/gcalculus` alone is a fact about that directory,
not the ecosystem. The research agent has been redirected.

⚑ **THE REPO HAS ALREADY FOUND THIS CLASS AND NAMED IT.** `unmeasured_edges`' docstring
(`coherence.py:331-357`) is a conflation finding written about itself: *"`if not sy` CONFLATES two
states that mean opposite things"* — measured-empty (a real verdict: Y tests no capability) vs
never-graded (not a verdict: the measurement has not looked) — *"the sentinel error one level down:
**not measurable from here is not nothing to measure**."* The repair was a NEW FACE separating them,
not a changed threshold. **That is the precedent for the axis-separation move, in this exact file.**

**So the honest statement of the choice:** this is not a refactor and not a no-op. It is a decision
about whether `sensitivity_residual`'s "behavioral witnesses" means *"everything the sweep could
measure"* (coarse, today) or *"the `behavioral` RUNG specifically"* (fine) — two different questions
wearing one word. **STOPPED here per the standing rule**; the research agent's axis census is the
input that decides it.

### Ψ · sweep-in-action — CONSTRUCT ONCE, READ MANY (tick 9, 2026-09-09)

**The framing is the operator's** (*"we want to run the construction once, and then process the
resulting artifact two different ways"*) and it dissolves the design question I was about to price.
I was asking *"should `delta_md` be re-founded on calcs?"* — a choice BETWEEN two constructions.
There is no choice: there is ONE construction and several readings, and one reading had been
re-running the construction.

    CONSTRUCTION   pk_calc → {claim, baseline, sens}      (the expensive measurement, once per claim)
       READING 1   tools/read_grade.py  → _grade_from_sens, pure, per-claim
       READING 2   coherence._records_from_calcs + ∂² faces, per-project
       READING 3   the CLAMP — a pure fold over the same assembled records (what _delta_section needs)

⚑ **The tree already holds this position.** `Ζ·calc·interp` (`bibtex.bzl:736`): *"ONE cached sweep
(pk_calc) feeds the verdict reading here (and the grade reading below); the redundant verdict run +
the adequacy re-sweep collapse into it."* Two readings deliberately collapsed onto one
construction. `delta_md` is a THIRD reading that was never connected, so it re-ran the construction
instead.

**⚑ Ψ-F1 — LANDED: `read_grade.py` was discarding five of six fields.**
`_grade_from_sens` returns `{grade, tests, baseline, why, not_higher, not_lower}`. Line 16 read
`["grade"]` and dropped the rest, so every `<claim>__grade.grade.json` in the build graph was a bare
`{claim, grade}`. **A reading throwing away what the construction produced.** Load-bearing twice:
- `report/gen.py`'s `_delta_section` renders exactly those justification columns (`why`,
  `not_higher`, `not_lower`) plus the clamp — so it could not read the build graph and re-ran the
  whole def-resolution sweep in-process, per project, per asset.
- **Δ-F9 recorded these records as carrying "no fingerprint". `tests` IS the fingerprint** —
  computed here and discarded. That correction matters for the `−` census's data source.

Verified on a real calc record: `bnd-clamp` now emits `grade: behavioral` **plus a 7-file
fingerprint** (`config.py`, `grade.py`, `grader.py`, `layout.py`, `mutate.py`, `resolver.py`,
`boundaries_clamp.py`), `baseline: established`, and all three justification strings.
⚑ `grade` stays FIRST and unchanged, so `pk_adequacy`'s `--field grade` aggregation and the
adequacy assert read exactly what they read before — additive, not a shape change.

**⚑ Ψ-F1 VERIFIED END-TO-END** (`bazel test @paperkit_boundaries//:adequacy`, re-run after the
change): **3 reds, not 4** — `bnd-check` is gone, confirming tick 6's hook wiring held. The three
remaining are exactly tick 4's diagnosed set (`bnd-closure-script`, `bnd-dispatch`, `bnd-wheel`),
two of them the staged changeset's. **No regression from Ψ-F1.**

⚑ **And the gate's own output went from a rung to a DIAGNOSIS.** Before, a red line read
`{"claim": "bnd-wheel", "grade": "broken"}`. Now:

    {"claim": "bnd-wheel", "grade": "broken", "tests": [], "baseline": "refuted",
     "why": "check does not pass in a pristine sandbox — repo is not green", …}

`tests: []` is correct and informative on a `broken` claim: nothing was measured, because the check
never passed to be mutated from. A passing record (`bnd-clamp__grade.grade.json`) reads
`{claim, grade: behavioral, baseline: established, …}` — `grade` first and unchanged, so
`verdict.py agg --field grade` keys on exactly what it did before. Additive, confirmed by the gate
reporting the known reds rather than erroring on the record shape.

**⚑ Ψ-F2 — THE MEASURED COST OF THE UNCONNECTED READING.** `@paperkit_report//:gate` sat on
`rpt-delta-out` for **33 minutes** running `gen.py --check delta.md`, which spawns
`discriminate.py --json render` IN-PROCESS — the legacy serial path. Measured at the time:
**4.5% CPU, 11 threads, 8s of CPU across 3 minutes** (not even GIL-saturated — mostly waiting on
sandbox copies: 1.8 GB read / 721 MB written in that window). `delta_md` calls `_delta(proj)` for
every project in `_graded()`, i.e. **nine full sweeps per asset**, and `_delta`'s cache is
per-PROCESS, so each of the four `fresh:*` warrants pays it again. Killed.

⚑ And `grep -c 'paperkit-discriminate: graded'` on the build log returns **0** — `gen.py` pipes the
child's stderr, so the Δ·pulse heartbeat never surfaced. **33 minutes with no progress output**:
the "a pipe hides the liveness signal" finding, biting in production.

**NOT DONE (the remaining two-thirds of Ψ), and deliberately:** re-founding `_delta_section` on the
calc records needs READING 3 — the clamp — which `_records_from_calcs` does not compute (it also
uses a coarse `behavioral if sens else vacuous` rather than `_grade_from_sens`, now unnecessary
since Ψ-F1 carries the full reading). That is a real change to what the report MEASURES and wants
its own tick. Ψ-F1 is the enabling half: the data now exists in the graph.

**⚑ Ω-F7 — I MISREAD G4. IT FLAGS THE GAP; IT DOES NOT AUTHORISE IT.** (operator challenge, tick 8)

I had been describing `setup`'s exemption as *"an explicit operator decision (G4)"* — carried from
the audit and repeated into `hook_grid.py`'s exemption reason. **Read as written**
(`prototypes/README.md:78`):

> **G4** — `setup` and `report` are outside `//:hook`. `BUILD.bazel:102-104` names this exact
> failure mode for the talk and then wires it. ⚑ **Operator decision**

Three errors in what I had been saying:

1. **G4 is about HOOK MEMBERSHIP, not tier.** It says nothing about `tier = "local"`. I had
   conflated "setup is `local`" with "setup is outside `//:hook`" — two separate facts.
2. **It is a flagged PROBLEM, not an authorisation.** Its own sentence says the identical failure
   mode was diagnosed for the talk *and then fixed by wiring it* — so G4's content is that setup and
   report are the remaining UNFIXED instances. ⚑ **"Operator decision" marks something as NEEDING a
   decision, not as having received one.** I read a work-item as a warrant.
3. **It names `report`, not `image`** — and `report` has since been wired (Α), so G4 is half stale.

**This is Ω-F1's error a second time:** citing a source as licensing something it actually flags.
Both instances were reasons I wrote into `hook_grid.py`, which makes them worse than a note — a
wrong reason inside a gate launders the status quo as a decision.

**Corrected all three exemption reasons** to state measured facts:
- `image` — needs a PODMAN + base-digest stamp key before `toolchain` is sound (Ω-F2)
- `report` — 10 of 16 remain, blocked by Ω-F5 (execroot vs source tree), NOT by host need (Ω-F6)
- `setup` — ⚑ **NOT authorised**; G4 flags it as an unfixed gap

⚑ **Consequence for the next tick:** `setup` is not exempt-by-decision, it is exempt-by-default with
a flag against it. So the question is not "may we retier it" but "why is it still outside the hook" —
G4's own answer being that the talk's precedent says *wire it*.

**⚑ Ω-F6 — LANDED (tick 8): SIX of `report/`'s SIXTEEN warrants never needed the host.**

`report/`'s exemption reason said *"the justification is an analogy"* — and Ω-F5 had just proved
that analogy wrong for its sibling `image`. Tested rather than reasoned:

- **Probe first.** `rpt-fig-svg` under the inherited `local` tier built with `1 local`. Added
  `tier = {sandbox}` per-warrant → rebuilt with **`1 linux-sandbox`**, verdict `fig well-formed: OK`.
  So the exemption was doing nothing but removing hermeticity, caching and remote eligibility.
- **Then the rest of the shape.** All six `fig:` warrants — `rpt-fig-svg`, `rpt-fig-palette`,
  `rpt-fig-contrast`, `rpt-clamp`, `rpt-terminal`, `rpt-dag-fig` — read `assets/dag.svg` INSIDE the
  project (`figure_checks.py`'s `SVG` constant), the same shape as Ω-F3's `img-hermetic`.
- **Verified together:** one build of all six → **`6 linux-sandbox`**, every verdict OK.

**Running total for Ω: 7 warrants retiered `local` → `sandbox` across two projects (1 image, 6
report), every one of them exempt from sandboxing + caching + remote execution purely by inheriting
a PROJECT-LEVEL default, and none of them needing any of it.** That is the granularity defect from
the defaults note, measured: the exemption was declared at the coarsest available scope and
over-applied to warrants with no host dependency at all.

Still `local` in `report/` (10 warrants, NOT retiered — each needs its own evidence):
`cmd:python3 {grounding,grades,distinct,mitigation,determinism}.py` (5) — these import `gen.py`,
which subprocesses `discriminate`/`gate` over SIBLING projects, so they are Ω-F5-shaped
(execroot-relative paths) and need the staging question answered; `fresh:{delta.md,without-k.md,
gate.md,dag.svg}` (4) — same, via `gen.py`; and `rpt-status` (1), which shells
`../paper .. ../boundaries` explicitly.

**⚑⚑ Ω-F5 — THE SHARPEST INSTANCE YET: THREE SOUND CHECKS THAT BAZEL CANNOT RUN, AND `local`
CANNOT FIX IT.** (measured, tick 7)

`@paperkit_image//:gate` is **RED** — and NOT from the Ω-F3 retier (`img-hermetic` and `img-pinned`
both PASS). The three podman warrants fail:

    img-repro   "sh: can't open '/work/image/entrypoint.sh': No such file or directory"
    img-serve   'building at STEP "COPY . /work" … copier: get: "/"("/"):
                 lstat //local-spawn-runner.18346359105032470267: no such file or directory'
    img-stable  fail

**Diagnosed:** `pk_cmd` runs `cd <project> && sh -c <cmd>` (`verb.bzl:101`) relative to the ACTION's
cwd, which is Bazel's **execroot**. So `repro.sh`'s `cd ..` lands in the execroot, and
`podman build … .` uses the EXECROOT as its build context — `COPY . /work` then tries to copy
Bazel's own transient `local-spawn-runner.*` files, which vanish mid-copy. `img-repro` fails
downstream because `/work/image/entrypoint.sh` was never copied.

**Verified the checks are SOUND:** `env -C image sh checks/repro.sh` from the source tree →
**`paperkit-gate: PASS`, exit 0.** It builds the image, runs the gate inside it network-isolated,
and the paper verifies hermetically. So these are correct witnesses that the build system cannot
currently invoke.

⚑ **AND THIS IS Ω'S THESIS IN ITS SHARPEST FORM.** `local` was chosen (by me, in Α) to mean *"this
needs the host."* What these checks actually need is **the SOURCE TREE as the podman build
context** — a completely different constraint. `local` supplies `no-sandbox` (real files rather than
symlinked inputs) but says nothing about WHERE the action runs, so it does not and cannot satisfy
the requirement. A placement was chosen for a constraint it does not express, and the check has been
red ever since — invisibly, because `@paperkit_image//:gate` is HOOK-EXEMPT (Η-F1), so nothing ran
it.

**Three exemptions compounding:** `tier=local` → outside `//:hook` → never run → the breakage is
undetectable. Α wired the project (so the target exists), Η-F1 named the exemption (so the gap is
declared), and Ω-F5 is the first time anything actually RAN it. **Each layer of exemption hid the
next.**

**⚑ CORRECTION TO Α:** I recorded `report` and `image` as `tier = "local"` with the justification
*"host-coupled."* For `image` that reason is now measurably the WRONG one — the requirement is a
build-context path, not host access — and `local` does not deliver it. The retier decision in Α was
made on an analogy (matching `setup`) and this is what the analogy cost.

**What it needs (NOT done — an owner decision, and larger than a tier flag):** the podman warrants
need their build context declared, e.g. an absolute-path anchor captured before the `cd` (the
`pk_agree`/`PAPERKIT_CONSUMED_RECORDS` idiom at `verb.bzl:95-99` already does exactly this for
sibling records), or the scripts taught to build from a declared root rather than `.`. Combined
with Ω-F2's missing `PODMAN` stamp key, `image` needs BOTH before it can be sound under Bazel at
any tier.

### ⚑ NEW — Ω · tier-is-a-placement-not-a-constraint (2026-09-09, operator challenge)

*"I don't know that I trust anything that asserts it needs to be `local`, since `local` is a
relative coordinate."* — Correct, and the tree confirms it. **I asserted `local` three times in Α
without checking what it means.**

**What the two host tiers actually are** (`tools/verb.bzl:77-83`), differing by ONE requirement:

    local:     {local, no-sandbox, no-cache, no-remote}
    toolchain: {local, no-sandbox,           no-remote}  + stamp_inputs = [ctx.info_file]

So `local` **IS** `toolchain` **PLUS `no-cache`**. And `verb.bzl:180` names them:
*"sandbox (hermetic, swept) | local (host-coupled, **uncached** — Ζ·resist) | toolchain (host
toolchain, **cached + stamped with the toolchain fingerprint**)"*.

**The asymmetry is the finding.** `toolchain` is a STRUCTURALLY EXPRESSED constraint: *"I depend
on the host toolchain, here is its fingerprint (`STABLE_TOOLCHAIN_*`), invalidate me precisely
against it"* — a named dependency with a witness, so a toolchain change invalidates and an
unchanged one is a cache hit. **`local` expresses NO constraint**: it says *"I depend on something
I will not name, so never cache me."* That is a declared INABILITY to state a dependency, not a
colocation requirement — and `Ζ·resist` names it as resistance rather than a property.

Both carry `no-remote`, i.e. both encode a **PLACEMENT** (this machine, no sandbox, no remote
executor) rather than a constraint placement could be DERIVED from. That is exactly the
v4cat-applied-to-scheduling error one layer down from `_grade_parallel`.

**Three `local` assertions need re-examining, and I wrote them:**
- **`image`** shells podman — a NAMED dependency. That is `toolchain`-SHAPED (it wants a
  fingerprint of the container runtime), not `local`-shaped. I chose `local` by analogy with
  `setup`, not by reading the tiers.
- **`report`** is worse: I justified it as host-coupled *transitively* because `rpt-status` shells
  sibling gates. That is not a host dependency AT ALL — it is a dependency on other ACTIONS,
  which is precisely what a build graph expresses natively (`consumes` / records-as-deps already
  exists, `verb.bzl:90`). Wrong axis entirely.
- **`rnd-format`** (`render/warrants.bib:168`) — the ONE pre-existing `local` I did not write, and
  the only `local` among render's 29 tier declarations (the other 28 are `toolchain`). Its check
  is `sh checks/render.sh --selftest` and its claim is about a CONFIG SELECTOR (an env knob
  choosing docx/odf/latex, refusing unknowns). No evident host coupling — arguably LESS than its
  `toolchain` neighbours, since it invokes neither pandoc nor LaTeX. Reads as an unclassified
  residual, not a constraint.

**NOT ACTED ON.** Retiering changes what is cached and what is swept; doing it mid-sweep, on a
reading of two `.bzl` lines, is the guess this ledger's rules forbid. What it needs: for each
`local` warrant, NAME the dependency (a binary? a fingerprint? another action's output?) and
either promote it to `toolchain` with a stamp, express it as `consumes`, or keep `local` WITH the
reason recorded. Filed as a new symbol so it is invocable.

#### ⚑⚑ THE OPERATOR'S POSITION IS STRONGER, AND IT IS THE RIGHT ONE (2026-09-09)

*"I don't want ANY no-remote, PERIOD. Nor any no-cache, nor any no-sandbox. I want to see the
things that break when they can't have those things, since those things are crutches for
unsoundness."*

**Each flag is an EXEMPTION FROM A SOUNDNESS PROPERTY, not a requirement:**

| flag | exempts the action from |
|---|---|
| `no-sandbox` | declaring its inputs |
| `no-cache` | being a FUNCTION of its inputs |
| `no-remote` | being location-independent |
| `local` | having its placement DERIVED |

A check that needs an exemption is not a check with a special requirement — it is a check whose
dependencies are UNSTATED. Removing the exemption does not break the check; it **reveals that the
check was already unsound and the flag was hiding it.** Same move as `--without-K`,
`Ζ·rests·unresolved` and the zero-postulate gate: refuse to let an unstated thing read as fine.
This also makes `toolchain` legible as a PARTIAL repair — it named ONE dependency (the fingerprint)
and bought back caching, then stopped, keeping `no-sandbox` and `no-remote`.

**The surface is TWO LINES** — `verb.bzl:78` and `:80`. Every exemption in the repo flows through
them.

**⚑ THE TREE ALREADY DID THIS ONCE, DELIBERATELY, AND IT WORKED.** `tools/wheel.py:62` +
`MODULE.bazel` (Ζ·wheel·backend): `//paperkit:wheel` shelled HOST `uv`, so it ran `no-sandbox` —
and even staged it would not have been hermetic, since uv materialised `setuptools>=68` from its
own cache, an undeclared input. DECLARING the build backend removed the tool, the host cache and
the exemption together: *"the wheel becomes an ordinary action the remote executor can run"*
(Ζ·rbe measured `uv` MISSING from the executor image — the gap this closes by not needing it).
**The exemption was the symptom; the undeclared input was the disease.** Precedent, in-tree, with
its own narration.

**What a no-exemptions pass would expose, sampled:**
- `img-hermetic` (`cmd:grep -q -- "--network=none" checks/repro.sh`) and `img-pinned`
  (`cmd:grep -q "python@sha256:" ../Containerfile.base`) are **greps over repo files** — ZERO host
  coupling. They inherit `local` only from the project default I set in Α. Two of image's five
  warrants are exempted from soundness for no reason whatsoever. ⚑ `tier` being a PROJECT-level
  default systematically over-applies the exemption.
- ⚑ **`img-stable` is the sharpest case in the repo.** `image/checks/stable.sh` asserts BUILD
  REPRODUCIBILITY — two `--no-cache --timestamp 0` builds yield the same digest — and it is the
  one check exempted from every mechanism that would VERIFY determinism (`no-sandbox`: undeclared
  inputs; `no-cache`: not a function of its inputs; `no-remote`: cannot run elsewhere). **A check
  asserting reproducibility, exempted from reproducibility enforcement.** If it could run remote
  and cached, the EXECUTOR would be testing the property the check merely asserts — a strictly
  stronger witness than its own internal double-build.
- And it names a real undeclared input: `podman build` over `Containerfile.base` pinning
  `python@sha256:…` **fetches over the network**. Not host coupling — an unstated NETWORK
  dependency, exactly the class `no-sandbox` conceals. (`img-hermetic` greps for `--network=none`
  in a SIBLING script, which is a grep for a string, not a network constraint on this action.)

#### ⚑ DEFAULTS MUST BE MOST-RESTRICTIVE, NOT MOST-PERMISSIVE (operator, 2026-09-09)

The ENGINE already gets this right: `bibtex.bzl:1039` declares `tier` with
`default = "sandbox"` — the most restrictive. **The permissiveness enters at the PROJECT seam.**

Resolution is `wt = tier if tier else proj_tier` (`bibtex.bzl:666`), so a project-level
`tier = "local"` is a **FLOOR**: it silently grants the maximal exemption to every warrant that
stays quiet. Exemption at the coarsest granularity available, with no reason attached to any
individual warrant.

**The correct shape inverts it:** project default stays `sandbox`; any warrant needing an
exemption declares it INDIVIDUALLY, beside the claim, with the reason. Restriction is inherited;
exemption is stated.

**⚑ `render` IS ALREADY THE MODEL, in-tree:**

| project | project tier | per-warrant tiers | exemptions granted |
|---|---|---|---|
| `render` | **none** (inherits `sandbox`) | **29 explicit** (28 `toolchain`, 1 `local`) | attributable, per claim |
| `setup` | `local` | **0** | 29 warrants, blanket |
| `report` | `local` (mine, Α) | **0** | 16 warrants, blanket |
| `image` | `local` (mine, Α) | **0** | 5 warrants, blanket |

One word exempts **50 warrants** across those three, and nothing records why any single one needed
it. Two of the three are mine.

⚑ **And a project default cannot express render's actual shape at all.** 28 `toolchain` + 1 `local`
in one project is a distinction a blanket default DESTROYS: it does not merely over-permit, it
erases the difference between warrants with genuinely different dependencies — which is exactly
how `img-hermetic` (a grep over a repo file) ended up exempted from sandboxing, caching and remote
execution alongside `img-stable` (three podman builds and a network fetch).

**Direction for Ω, superseding "name the dependency and retier":** delete the exemptions and let
the reds be the census. Each failure names an undeclared input; declaring it is the repair, on the
Ζ·wheel·backend model. Expect: container-runtime and network deps surfacing on image, pandoc /
LaTeX / veraPDF toolchain deps on render, and — the interesting ones — checks like `img-hermetic`
and `rnd-format` that turn out to need nothing at all and were only ever riding a project default.

  ⚑ The evidence was a reading, not the finding — `ps -T` showing every worker at 1/N of a core
  and 9 of 11 threads on `futex_do_wait`, `/proc/<pid>/io` showing rchar climbing with
  `read_bytes` flat (page-cached copies). Those readings LOCATED the bottleneck; the bottleneck
  is the lock. [[dont-collapse-to-smallest-representable]] — a scalar is where a diagnosis goes
  to die, and this ledger has spent the whole Δ thread on exactly that error one level up
  (tropical `min` collapsing a derivation to a rung, `interval_width: 0` collapsing an interval
  to a point).

- ⚑ **THE ADEQUACY DENOMINATOR IS DYNAMIC, NOT A PRECOMPUTED PRODUCT** (operator, 2026-09-09).
  Observed on `bazel test @paperkit_paper//:adequacy`: the total moved
  **81,429 → 84,699 → 94,532 → 94,796** while running, then plateaued — and a plateau is NOT a
  ceiling. Thousands of actions are **SYNTHESIZED LATER**: the mutation grid cannot be known until
  sites are enumerated, and enumeration is itself work IN the graph, so each `Ζ·eval` leaf belongs
  to a subgraph a prior action produced.

  ⚑ Correcting my own earlier note in this file: I wrote that Bazel gives *"progress as a property
  of a graph with a known extent."* **False.** The extent is not known in advance. What it
  actually provides is a **MONOTONE denominator** — it only grows, and only for a stated reason (a
  synthesized subgraph) — which is weaker and more honest than "known extent". Do not read a
  stable total as completion, and do not compute an ETA from a ratio whose denominator is still
  being discovered.

  The size has three independent causes, none of them a runaway: (1) **Γ** made seven previously
  ungradeable projects enumerable, so cells that were structurally unreachable now exist;
  (2) **`Μ·sweep·atom`** adds branch-arm sites ADDITIVELY beside def-sites rather than replacing
  them (`_sites`: `_def_sites` + `_branch_sites` + `_data_sites`), visible in the action names —
  `__qualname`, `branch__…_arm_N`, `data_drop__…_arm_N`, `import_add__…`; (3) dynamic synthesis
  above.

- ⚑ **A pipe hides the liveness signal.** `_grade_parallel` emits a Δ·pulse heartbeat *"so a slow
  grade reads as LIVE, never stalled"* — but `coherence.py` captures the child's stdout AND
  stderr (`/proc/<pid>/fd/{1,2}` → pipes), so the heartbeat is buffered and invisible. Progress
  was indistinguishable from a hang for two hours. Diagnose a quiet sweep with `/proc/<pid>/io`
  (rchar climbing = alive) and `.../task/*/wchan` (`futex_do_wait` = GIL, not I/O).
- Repo has a large PRE-EXISTING staged changeset (`library/` → `paperkit/library/`, wheel work).
  **Not ours. Do not commit it, do not revert it.**

---

## Ordering (last re-derived: 2026-09-09, tick 0)

### Α · wired-scope — ✅ LANDED (see Landed section)

### Β · doc-identity — ✅ LANDED (tick 35, 2026-09-10). See Landed and Β-F1.

### Β — original READY note (kept per rule 6, superseded by the above)
`_all_docs()` (`report/gen.py:80`) keys by `d.name`; key by repo-relative path and exclude
gitignored trees.
**Leverage:** fixes duplicate `library` BEFORE Α bakes bare-name matching into `_hook_names()`,
and before Phase D adds `arch/`+`graph/` (two more collision candidates). Cheap now, structural
later. See A2-F2.
**Verify:** `distinct.py` reports 9 distinct documents, no duplicate.

### Γ · tristate-delta — ✅ LANDED (see Landed section)

### Δ · cycle-axis — ⚑ RESCOPED (operator correction, 2026-09-09). A CYCLE IS A POSTULATE.

**The correction:** I called a `rests-on` cycle "an authoring error with no fixpoint that makes it
true." Wrong — that collapses two states this repo exists to separate. A cycle is not FALSE; it is
**VACUOUS / unfalsifiable in the grounding dimension** — a cluster of claims each supported only
by the others, never bottoming out in anything external. That is exactly a **postulate**, and the
repo already owns that word.

**Three facts that make this the right frame, all verified:**
1. `gate.py:84` — `--safe` is the **zero-postulate** invariant. A postulate is ADMISSIBLE by
   default and fatal only under `--safe`. So the engine's stance on unsupported admission is
   already "name it, let policy decide" — never "repair it."
2. `gate.py:418` — `postulates` is computed as `section ∧ ¬cited ∧ is_placed`: a purely
   **prose-side** notion (an uncited placement). A grounding-side postulate — a claim whose
   `rests-on` cone reaches no externally-grounded claim — is **structurally analogous and
   currently invisible**.
3. `grade.py:_grade_from_sens` — `behavioral`'s own `not_higher` reads: *"a proof-grade (total,
   **postulate-free** witness) tier is not yet defined."* The ladder NAMES this missing rung. And
   the two axes are independent: Δ measures FALSIFIABILITY over the witness (does a mutation flip
   it), grounding measures whether the premise cone terminates. A postulate cluster grades
   `behavioral` — top tier — because both witnesses flip. The witness is falsifiable; the
   grounding is circular; nothing tells them apart.

**Why cycle-TERMINATION is already solved and is not the work** (three deliberate sites):
`rests_closure` (`bib.py:614`, docstring: *"Cycles are handled (each key is visited once)"*),
`clamp()`'s `eff()` `stack` guard, and — decisive — `boundaries_grounding.py:82-86`, a **PASSING**
test asserting a cycle terminates and gates its checks (`rc_c == 0`), sitting beside `:88-90`
where a DANGLING edge is asserted to FAIL. The repo has drawn the line: dangling = error,
cycle = terminate-and-gate. Any Δ that reds a cycle must argue against that stated position.

**⚑ SPPF internment — SURVEYED 2026-09-09, then CORRECTED BY THE OPERATOR. Read the correction.**

~~An SPPF cannot hold a cycle at all. `Intern.intern` requires child ids to EXIST before the parent
is interned, so the table is *structurally incapable* of representing one — stronger than a
guard.~~ **WRONG, and wrong in an instructive way: I generalised a SEQUENTIAL-CONSTRUCTION property
into a CARRIER property.**

Operator: *"true iff the edge level is the coarsest granularity afforded. If, in a single
transaction, a batch of IDs is precisely allocated and exhausted to hold the cycle, integrity is
maintained. (And one edge of the cycle is the SPPF reentrancy.)"*

Verified against `jea_pyalg.py:67-78`: the ONLY hard constraint is `self.fanin[c] += 1`, which
requires `c` to index an already-appended slot — a **list-bounds** constraint, not an acyclicity
one. Nothing checks `c < i`. Allocate `n` placeholder slots for the SCC (ids `i..i+n-1`), fill
them with children drawn from that range, and every `fanin` index is in bounds. **Integrity holds;
the cycle is representable.** One-node-at-a-time is the coarsest granularity the current API
affords, not a property of the store.

⚑ And the substrate's `max_parents = 1 / post_order = total` measurement is **producer-side, not
carrier-side**: `local_id` is `agdai_shim.hs`'s monotonic post-order print counter, so a forest is
what THAT producer emits. It is not evidence about what the table can hold.

**⚑ THE REENTRANCY EDGE IS THE POSTULATE MARKER, AND HASH-CONSING FORCES IT.** `IR.key()` is
`(kind, role, op, lit, children)` with children as ids, so identity is structural all the way down.
In a cycle a node's key depends on an id whose key depends back on it — **the key is not
well-founded**, so you cannot hash-cons to the fixpoint. Representing the cycle REQUIRES declaring
one edge the reentrancy, and that declaration is exactly the postulate marker. The construction
does not merely permit the honesty; it compels it.

This converges with the whole thread: tropical `min` CANNOT see the cycle (idempotent fixpoint),
bare reachability SEES it and draws the wrong conclusion (licenses a false "redundant"), and an
SPPF MUST NAME it to represent it at all. Three carriers, and only the third is forced to be
honest. Acyclicity is producer-side and measured: `scripts/sppf_db.py:978-982`
reports `total = 130,915,197 · post_order = 130,915,197 · max_parents = 1` — a FOREST at that
tier — and `:984-989` gives the cause (`local_id` is the shim's monotonic post-order print
counter), *"not an empirical regularity the fold is lucky to find — it is the walk order, by
construction."*

So interning would REFUSE a cyclic corpus, not absorb it. Arguably a good property (the postulate
becomes unrepresentable rather than invisible) but **not available**: every intern entry point is
source-derived (`lower_source`, `lower_source_cst`, `intern_signature`); there is no CLI or API
that interns a caller-supplied node/edge relation. `Intern.intern` is generic but undriven.

**⚑ THE TROPICAL DIAGNOSIS IS CONFIRMED AT THE SUBSTRATE (operator, 2026-09-09).**
`clamp()` is min-over-a-total-order — `grade.py:20` says it literally: *"effective grade = min over
self + premises"*. It is a **bottleneck** semiring (min/min), not even min/plus: path LENGTH is
invisible, only the weakest link survives, so the derivation structure is discarded by
construction. `min` over a cycle is a fixpoint — `min(x,x) = x` contributes nothing — which is why
the cycle guard is not papering over a defect: **the semiring genuinely cannot see a cycle.**
Δ-F1's `interval_width: 0` on a postulate cluster is exact semiring behaviour, not a bug in `lo()`.

The substrate makes the choice explicit and shows what it costs: `numpy_builders.py:52`
`SR_TROP = Semiring("tropical", np.add, _trop_reduce, _INF, 0, np.minimum)`, one of FOUR gauges
(`nat`, `bool`, `tropical`, `f2`) running through ONE contraction that *"PLACES ITSELF via the
gauge: Bool = reachability, ℕ = path-count, tropical = cost"* (`:6-9`), byte-exact-checked at
`:498,513`. Tropical is one gauge among several; picking it discards what path-count sees — and a
cycle lives exactly in multiplicity. **g-calculus's strength is being more precise than the
tropical** (operator). So Δ is not "add cycle detection to clamp" — it is that clamp collapses a
DERIVATION to a scalar RUNG, and the collapse is where the information goes.

**⚑ `scratch/dagcone.py` ALREADY NAMES PAPERKIT AS A CALLER.** Docstring `:43-46`: *"THE GRAPH IS
SUPPLIED, NEVER DISCOVERED HERE. Callers own their edges — the import DAG comes from
`parse_tree()`, **the warrant graph from the bib** — and this module owns only the walk."* Entry
points take `successors(node) -> iterable` over arbitrary hashable nodes: `reach` `:70`
(cycle-safe), `weigh` `:315`, `cone` `:389`, and — the one Δ wants — `layers` `:363`, whose
`:379-385` reads **"A CYCLE IS A FINDING, NOT A CRASH"** and raises
`ValueError("not a DAG; cycle: ...")` via `nx.find_cycle`. Caveat: `module_importers dagcone`
reports the name is AMBIGUOUS (`scratch.dagcone` and `substrate.dagcone`) — the same two-bodies-
one-name defect its own docstring was written to retire.

**Transitive reduction is ABSENT from the substrate** (searched every `.py` outside
`.git/build/__pycache__/.mypy_cache/.venv/.edit-snapshots` for
`transitive.?(reduction|closure)|WITH RECURSIVE|premise.?cone|toposort|topological|cycle` and for
`tropical|min-plus|clamp|min_over|fold_min`; zero hits for reduction). Closure exists in three
cross-checked forms (`q_reach` SQL `WITH RECURSIVE`, `dagcone.reach`, `np_closure`, with
`np_sql_coherent` asserting the identity at `numpy_builders.py:383`). So `transitive_reduction` is
genuinely paperkit's own operation and its cycle-correctness is paperkit's to fix.

⚑ Two premise corrections from the survey, worth keeping because both would produce a false
"not found": the file is `scripts/sppf_db.py` (NOT `scratch/`), and `decode_core` is not in it at
all — it lives at `jea/metalanguage/jea_agdai.py:419`.

**Δ.1 — report a grounding-side postulate.** A `rests-on` cycle (more generally: a cone that
reaches no externally-grounded claim) is named on the record and in `gate --json`'s `postulates`,
in the vocabulary already there. Admissible by default; `--safe` decides. This is the honest
denotation of what `clamp()` currently reports as `clamp: 0, clamped_by: null` — which reads
"nothing constrains this claim" when the truth is "nothing GROUNDS it."

**Δ.2 — `transitive_reduction` is wrong independently, and stays wrong under the postulate
reading.** `project.py:245` `reaches(a,b)` drops X→Y when Y is reachable the long way. On the
A2-F7 cycle it dropped the REAL edge `observe-second-shape → genre-registry`, because the walk
escaped through `grouping-not-pagination` and back. Post-fix it is kept — that is exactly the
annotation the regeneration diff added. Cycle-TERMINATING but not cycle-CORRECT: it silently
deleted a true grounding edge from rendered prose. Vacuity is admissible; a cross-reference
asserting derivation THROUGH a postulate cluster is a different error and must not be rendered as
ordinary grounding.

**⚑ Retro-doubt on A2-F7:** I broke the cycle by re-pointing an edge on prose evidence. If a cycle
DENOTES a postulate cluster, the honest move may have been to NAME it before removing it — I
removed the structure before the engine could see what it was. The prose evidence for the
direction was strong (three agreeing lines) so I do not think the edge was wrong, but the ORDER
was: name, then decide. Applies to every corpus edit in Phase D/E.

**⚑ Δ-F1 — `_bracket`'s admissible interval reports CERTAINTY on a postulate cluster.**
`grade.py:435` computes `effective_min`/`effective_max` because an unresolved unfold leaves the
true grade underdetermined; `interval_width` is *"the cost of not having unfolded"*. But `lo()`
carries the same `y not in stack and y != k` cycle guard, so a cycle contributes nothing to the
pessimistic bound either. A postulate cluster therefore gets `effective_min == effective_max`,
**`interval_width: 0`** — maximum confidence — on claims grounded in nothing. The instrument built
to expose underdetermination reports certainty exactly where the grounding is circular.

**⚑ Δ-F2 — my proposed fix is a method this ecosystem has already RETRACTED BY NAME.**
`_bracket`'s docstring: *"The fix is not a bound on the EDGE (an error bound on a step you should
not take licenses taking it — linux-sources retracted exactly that as a method: 'an error bound on
an unreachable state is not a bound, it is an invitation')."* My revision — "refuse to drop an edge
whose redundancy is witnessed only through a cycle" — IS a bound on the edge. Do not do it. The
shape the repo uses instead is a **pair of bounds on the RESULT**, computed by the same operator
over the same ladder.

**⚑ Δ-F7 — LAWVERE × TARSKI: THE ORGANIZING CLAIM (operator, 2026-09-09).**
*"lawvere and tarski work together to form a maelstrom that lands at a fixed point."*

This names the shape the whole Δ thread was circling, and it is literal, not analogy:

**LAWVERE — self-reference FORCES a fixed point.** A point-surjective `A → B^A` makes every endo
on `B` have one. `IR.key()` states the equation as code: the key is
`(kind, role, op, lit, children)` with children as **ids**, so a cyclic node's key satisfies
`k = f(k)` — an endo on the key space. Hash-consing cannot REACH that fixpoint by descent (the key
is not well-founded, Δ-F4), so the reentrancy edge is where you are **compelled to CHOOSE the
fixed point rather than compute it**. The choice is forced; only its location is free.

**TARSKI — a monotone endo on a complete lattice has a LATTICE of fixed points, lfp ≤ … ≤ gfp.**
`clamp`'s `eff(k) = min(grade(k), min over premises)` is exactly a monotone endo on `RANK_C`. On an
SCC it HAS fixed points — an INTERVAL of them. But `RANK_C` is a **total order** (Δ-F5), so lfp and
gfp collapse to one value. **That is `interval_width: 0`**: a bracket that should have been
`[lfp, gfp]` reporting a point, because the carrier cannot hold two.

**The maelstrom:** Lawvere says the self-reference MUST produce a fixed point; Tarski says on a
lattice you get an INTERVAL of them. Take the tropical quotient and the interval degenerates to a
point — the structure Lawvere guaranteed is still there, but the carrier has nowhere to put it.
⚑ `_bracket` (`grade.py:435`) is ALREADY REACHING FOR THIS and cannot grasp it: it computes
`effective_min`/`effective_max` precisely because an unresolved unfold leaves the grade
underdetermined — but `lo()` carries the SAME cycle guard as `eff()`, so both endpoints come from
the same collapsing fold. The instrument built to hold an interval reports a point exactly where
the interval is real.

**The non-degenerate version is Δ-F6's split.** `witness = ker(B)` is the fixed-point residue given
a **basis** instead of a scalar — the directions in which the self-reference is irreducible.
Lawvere's forcing appears as the parity result (`jea_strictify_gcalc.py:71-72`: odd cycle-dimension
⇒ `ker ≥ 1`, a witness is COMPELLED); Tarski's interval appears as `representable ⊕ witness`, where
representable is what lfp and gfp AGREE on and the kernel is where they do not.

⚑ So Δ is not "detect cycles". It is: **the carrier cannot represent what the structure forces.**
Every symptom on this thread is that one fact — `interval_width: 0` (Δ-F1), the silent `stack`
guards (A2-F5), the false redundancy license (Δ.2), EMERGENCE never reaching `leaf` (Δ-F3).

**⚑ Δ-F8 — SURVEYED (witness-tower, 2026-09-09): LAWVERE IS PROVED; TARSKI AND THE POSET ARE
ABSENT FROM THE WHOLE SUBSTRATE. Correct the framing above accordingly.**

**Lawvere — EXISTS, general, machine-checked, and UNWIRED.**
`agda/Substrate/Category/Lawvere.agda:126-134`, zero postulates, `--safe --without-K`, verified
compiling:
`lawvere-fixed-point : (φ : A → A → V) → PointSurjective φ → (f : V → V) → Σ V (λ v → f v ≡ v)`
— the exact form invoked in Δ-F7, at **Set** (A, V bare `Set`s; `B^A` spelled `A → V`), not the
general CCC statement. Contrapositive `diag-not-in-family` at `:94-95` over
`record FixedPointFree` (`:72-75`). The tower's specialisation is `WitnessTower/Diagonal.agda`
(`cantor-diagonal :89-95`, `F₂-fpf :119-120`, `cantor-lawvere :124-125`), populated BY `Algebra.F2`.
⚑ **`Diagonal.agda` has 0 importers** — nothing consumes it. Built and unwired.

**Tarski — ABSENT.** No lfp/gfp, no least/greatest fixed point, no monotone endo on a poset or
lattice anywhere in `agda/Substrate`. Searched `arski|lfp|gfp|east-fix|reatest-fix|ixpoint|
ixed-point|ixedPoint|onotone` → 35 names, none Tarski-shaped. The near-misses are **coalgebraic**
(`Coalgebra.FixedPoint`, `DiagonalEscapeCoalg.prediction-is-nu-fixed-point-fwd/bwd`,
`ExtrudeMinimalCoalgebra.μ-iterate-fixpoint`) — initial-algebra/final-coalgebra on FUNCTORS, not
Tarski on an ordered carrier, and no theorem relates the μ and ν names.

**⚑ NO POSET CARRIER EXISTS EITHER — the substrate has paperkit's own limitation.** The only `≤` in
the tree is `Foundation/Nat/Le.agda`, a **TOTAL** order on ℕ. No `Poset`, `PartialOrder`,
`Preorder`, `antichain`, or incomparability predicate; `InclusionLattice`
(`Category.ReedMullerHierarchy`) is a lattice by name with no incomparability. And
`--prose 'incomparab|partial order|poset|antichain|total order'` over `Substrate.WitnessTower`
returns **0 comment lines in 349 modules**.

⚑ **So Δ-F7's "Tarski's interval degenerates because the carrier is total" HAS NO SUBSTRATE
COUNTERPART TO CITE.** I was implicitly treating the ecosystem as holding machinery it does not
hold. The substrate cannot be cited for lfp≠gfp-on-a-non-total-carrier because it has no carrier
where the two could differ. The Lawvere half stands, machine-checked; the Tarski half is a claim
about paperkit's `RANK_C` with no in-tree formalisation behind it. **Do not present it as
grounded in the substrate.**

**The nearest parity-forcing result is CLOSE AND NOT IT.**
`WitnessTower/Hodge.agda:120-124`:
`witness-distinct : (i : Fin 4) → (dual-grade₃ i ≡ i) → Fin 0`
— *"n=3 odd ⇒ ★ has no fixed point"* (`:117`), genuine odd-parity forcing, but the carrier is
`Fin 4` **grade labels**, the proof is case exhaustion, and there is no rank argument and no cycle
space. Contrasted in-file with n=4 where grade 2 IS self-dual, so parity does real work — on
labels. ⚑ `Hodge` and `Diagonal` **do not import each other**; the link is asserted in a COMMENT
(`Diagonal.agda:21`) and proved nowhere. Nothing connects either to the orientation rig.

**Residue-as-kernel — NO.** `FixedPointFree.δ-free : (v : V) → δ v ≡ v → ⊥` is `⊥`-valued: a
refutation FLAG with no linear structure. `translate-fpf` (`:254-257`) hypothesises CANCELLATION
(`fix→unit`), a group condition, not a form; `prove-or-correct` (`:265-270`) returns a sum type — a
two-valued flag with a witness, never a dimension. Real kernel machinery (`KernelDim`, `inKer`,
`ker-quotient`, `dim-ker-Φσ`) lives entirely in `Algebra.F2.Linear.*`; the tower's
`apex-kernel` is a DETECTOR kernel (diagonal-of-a-relation, decidable equality), not a subspace.
The one kernel-dimension statement (`HodgeGradeInvolution.nullity-factored :72-73`) has no parity
hypothesis and is F₂'s theorem re-exported verbatim.

**⚑ NET: Δ-F6's `representable ⊕ witness` with odd-dim ⇒ `ker ≥ 1` has NO COUNTERPART in the Agda
tree.** It exists only in `jea/jea_strictify_gcalc.py` — exact sympy, `check(...)`-asserted, and
explicitly self-described as *"the intermediate rung between 'proved on the g-calculus/graph side'
and '--safe Agda witness'"*. So it is strictified, not mechanized. Treat it as the strongest
available statement of the shape and NOT as a proved theorem of this ecosystem.

**⚑ Δ-F5 — POSET, NOT TOTAL ORDER. This is the defect at every level (operator, 2026-09-09).**
On `Intern.intern` needing only that `c` be already-allocated, never `c < i`: *"right, because we
deal in posets and partial order, not total order."*

`c < i` would be a TOTAL order on ids — every node comparable, position on a line. The table
requires only ALLOCATION order: a **partial** order, in which **incomparability is a first-class
state**. Two nodes in an SCC are mutually reachable and therefore **INCOMPARABLE — not tied.**

That is the same defect one level up, and it is DECLARED: `grade.py:20` reads *"**Total order** for
clamping"*, `RANK_C` maps rungs to ℤ, and `clamp` folds `min` over it. When two claims ground each
other the poset answer is *"incomparable — neither is below the other"*; the tropical answer is
`behavioral`, because `min(3,3)=3`. **The fixpoint is not the semiring being lossy by accident —
it is a total order being asked a question only a poset can answer, and answering anyway.** A
total order has no representation for incomparability, so it must return a value, and `min`
obligingly returns one.

The three carriers, correctly placed:
- **total order + min** — forces comparability; the SCC collapses to a tie and vanishes
- **reachability** — IS the poset's ≤, but its transitive closure without an antisymmetry check
  conflates "X below Y" with "X and Y mutually reachable". That is exactly what licenses the false
  redundancy: `reaches(a,b)` through an SCC is true but is not a STRICT ≤, so it cannot license a
  drop. `transitive_reduction` is only well-defined on a POSET.
- **SPPF + reentrancy** — the Hasse structure plus an explicit marker where antisymmetry fails

A poset order is a DAG up to reachability; an SCC is precisely where the relation stops being
antisymmetric and becomes a PREORDER. The reentrancy edge is the record of that failure.

⚑ `poset` appears **0 times in paperkit** (`pycodemod --literal poset`, 0 of 81 files). The
vocabulary is absent, and the ladder's own comment says which order it chose.

**⚑ Δ-F6 — THE G-CALCULUS ALREADY DECOMPOSES CYCLE SPACE, AND THE WITNESS IS THE KERNEL.**
`~/github/substrate/jea/jea_strictify_gcalc.py` — exact sympy strictification, header `:11-13`:
*"(2) the **cycle-space antisymmetric (exterior-algebra) form B** per rung; its rank/kernel EXACT.
(3) the **witness = kernel(B)**, exactly; representable = row space; orthogonality witness ↔ rep."*

So a cycle is **not an error condition** — it is a linear-algebraic object with a basis, and what
certifies it is the kernel. The split (`:74-86`, verified exactly):

    cycle space  =  representable (= image B)  ⊕  witness (= ker B)          B·w = 0

Part of a cycle is REPRESENTABLE — derivable within the structure. The rest is KERNEL — the residue
nothing in the structure derives. **That kernel IS the postulate**: not a marker bolted on, but the
exact residue of the cycle space, with nameable basis directions.

⚑ And the PARITY result (`:71-72`): **odd cycle-dimension FORCES a witness** (`ker >= 1`). Some
cycle spaces cannot be fully representable — a postulate is COMPELLED, not merely permitted.

This is what "more precise than the tropical" buys. Tropical returns ONE SCALAR for the SCC;
this returns a **decomposition** — how much is derived, how much is irreducibly assumed, and in
which directions. Also `:38-41`: non-idempotence `(n,d)+(n,d) = (2nd,d²)`, class `2n/d`, named the
**mass shadow** — the exact fact that makes a cycle unable to vanish into a `min` fixpoint.

**⚑ Δ-F3 — THE DISCRIMINATOR ALREADY EXISTS IN PAPERKIT: the EMERGENCE face.**
`coherence.py:405` `emergence_residual` tests `fp(X) ⊆ ∪fp(rests-on)` over **measured sensitivity
fingerprints**, classifying each claim `collapse` / `increment` / `leaf`. `leaf` (no `rests-on`)
is stated in its own docstring as **"an axiom"** — the postulate notion, already named, already
computed.

**Why fingerprints are the right carrier and reachability is not:** a cycle can make `reaches()`
true vacuously; **a cycle cannot manufacture a fingerprint.** `fp` is what a mutation sweep
measured the check to be sensitive to — an external fact about the witness, not a property of the
declared edge set. That is the precision the tropical collapse discards.

**But EMERGENCE as written does NOT catch the postulate cluster**, and the gap is one line:
`prem = [y for y in r.get("rests-on", []) if y in S]` — a cycle member HAS premises, so it is
never `leaf`. It is scored `collapse` or `increment` against its own cycle partner. The face has
the right carrier and the wrong terminating condition, exactly like `clamp` and `lo`.

⚑ Read the docstring precisely, NOT a summary of it: an `increment` is explicitly **NOT** by itself
under-grounding — a fingerprint includes the check's MECHANISM and the claim's own
origin-capability, not just the thesis's grounding. *"The sound under-grounding signal is the
GROUNDING face (overlap), not this one."* Do not build Δ on a misreading of increment.

⚑ **gcalculus records that this face has NEVER RUN there** — blocked because `coherence.py`
consumes `discriminate --resolution def --json`, which failed in its bounded sandbox
(`NOTES-COHERENCE.md:33-43`). **That is the same Δ-sandbox-root refusal Γ just fixed here.** Γ may
have unblocked the one face that answers this question. A run was in flight when this was written.

**The construction to copy: `resolution`.** `grade.py:357-363` surfaces truncation as a VALUE
(`truncated|resolved`), derived transitively by `_reaches_truncation` so a claim resting on a
truncated premise is itself truncated. A grounding-side postulate is the SAME construction with a
different terminating condition — not "an edge we could not resolve" but "a cone that closes on
itself." Machinery, transitivity and vocabulary all already exist.

**Not `entails`.** `Ξ·entails` / `scope_residual` (`coherence.py:212`) is an adjacent but distinct
axis: declared witness-to-SENTENCE coverage vs measured reach, and `measured: false` on every
project here. It does not speak to whether a grounding path discharges its obligations.

**Operator pointer: g-calculus.** ⚑ I first glossed it as a "logical framework" and reasoned about
cut-admissibility. **Wrong — inferred from the name.** SURVEYED: it is an **algebra on the positive
rationals**, carrier = electrical conductance, two primitives (`gcalc/kernel.py:27-33`):
`NOT(x)=1/x`, `OR(a,b)=a+b` (PARALLEL), `AND(a,b)=ab/(a+b)` (SERIES). `kernel.py:20`: *"Nothing
here asserts anything."* No judgements, no inference rules; "calculus" as in calculus-of-
resistances. Interface is a route dispatcher returning **an exit code only** (0 certified / 1
failed / 2 not-mine, `gcalc/__init__.py:70`) — no judgement object, no derivation.

**But the pointer was right, one level down: series/parallel IS the non-tropical refinement.**
- tropical `clamp`: `min(a,b)` — weakest link, everything else discarded
- **series** `ab/(a+b)`: resistances ADD — path LENGTH is visible, every premise contributes
- **parallel** `a+b`: independent grounding paths STRENGTHEN the conclusion

Two independent `behavioral` premises give `min = behavioral` under clamp but strictly more under
parallel; a long chain of strong premises degrades under series where `min` reports the endpoint
unchanged. And `OR(a,a)=2a` — **non-idempotent**, which is exactly why a cycle cannot vanish into a
fixpoint the way it does under `min`.

**What gcalculus DOES contribute, gated:** `fano.py:244-259` states our exact distinction —
*"asking whether a composite is grounded in the goal axis is a REACHABILITY question, not a parity
question, **and the two answers differ**"* — gated as
`probe/a-syndrome-reads-directness-not-grounding`. Plus the **over-decode guard**
(`unified = entailed` vs `asserted`, gated) and the **standing-line rule**: one populated point is
correct and stable; forcing the second is a fake tidy *"a later pass discovers and consumes as
real."* That is structurally our bug one level up.

⚑ **gcalculus has a LIVE 2-cycle in its own corpus** — `wcr-is-refuted-not-open ⇄
newman-bounds-the-residue` — and `NOTES-COHERENCE.md:82-84` already records that entry as
inconsistent (`points` has 2, `rests-on` has 3, from a merge). Nothing gates it. Its cycle handling
is the OPPOSITE of what we need: `fano.py:227` (*"a cycle contributes no depth"*) and `:255-256`
(*"a cycle contributes no new ground"*) both silently absorb.

⚑ **WARNING AGAINST REPEATING A2-F7.** `NOTES-COHERENCE.md:77-81`: a Fano line is three points
with `p+q+r=0` over 𝔽₂ — **symmetric**; *"Any two force the third; which is 'the conclusion' is a
choice of vantage."* `points` records the two populated members (already a projection) and
`rests-on` projects further to an unordered bag. **So a grounding edge's DIRECTION may be an
artefact of the projection** — which is precisely what I picked from prose in A2-F7.

**Verify:** a fixture cycle is reported as a postulate, not an error; `--safe` reds it; a
non-cycle corpus reports none; `interval_width` is non-zero (or the postulate axis is set) on a
cluster with no external ground. `transitive_reduction` does not license a drop whose only
redundancy witness runs through an undischarged cone.

### Ε — ⛔ BLOCKED ON OWNERSHIP, SCOPE NOW MEASURED EXACTLY (tick 15, 2026-09-09)

**Blocked, and not by difficulty.** `git -C ~/github/substrate status --short scratch/bibstruct.py`
→ **`A `** — the tool is **staged-added**, part of a very large uncommitted changeset in substrate
(the same class as paperkit's `library/` → `paperkit/library/` work). Standing rule: *do not touch
the pre-existing staged changeset.* Editing another repo's staged file would entangle with someone
else's in-flight work.

**⚑ Ε-F1 — THE TRUE SCOPE, MEASURED CORPUS-WIDE FOR THE FIRST TIME: 3 of 455 entries, all in
`paper/`.** Every prior measurement was `implications.bib` alone.

| corpus | roundtrip |
|---|---|
| `paper/` (12 bibs, the flagship) | **3 of 114** — `edge-rests-grounds` (`model.bib:82`), `grounding-reflected` (`implications.bib:44`), `emergence-collapse` (`implications.bib:50`) |
| every other bib (16 files: root, boundaries, render, talk, config, demo, guide, image, report, setup, library, prototypes×3, assets, adequacy_pitch) | **0 of 341** |

⚑ The defect is **confined to the one project that carries LaTeX math** — consistent with the
trigger pinned in tick 5 (`\{`/`\}` and `{}` nested inside `\mathrm{…}`/`\bigcup_{…}`). And
`bibstruct` states its own limit on the clean read, which is the honest form:
*"this read is TOTAL over this input — an ALGEBRA result. It does NOT say the parser's kernel is
empty; it says nothing in THIS file fell into it."*

**Considered and NOT built: a paperkit-side roundtrip gate.** The contract is usable (exit 1 on
drift, exit 0 clean, and no such gate exists — `.githooks/pre-commit` has no `roundtrip`/`bibstruct`
invocation). Two objections stopped it, and both are this session's own recurring defect classes:

1. ⚑ **It would introduce an undeclared cross-repo dependency.** A paperkit hook calling
   `~/github/substrate/.venv/bin/python ~/github/substrate/scratch/bibstruct.py` makes paperkit's
   pre-commit depend on a sibling repo's **uncommitted, staged-only** file — the Ω class exactly
   (a real dependency that nothing declares), and worse than the `uv` case `Ζ·wheel·backend`
   retired, because the dependency is not even committed.
2. **The gate would be RED TODAY** on 3 entries I cannot fix here (the fix is in substrate). So it
   would either block every commit or need a **baseline** — and a baseline grandfathering exactly
   these 3 is a RATCHET, with the absent-vs-empty semantics that `precommit-gates` records as
   having inverted five gates elsewhere. That is a design, not a guard.

**What is actually actionable, in order:** (a) file the `bibstruct` bug to substrate's owner via
`summit` rather than patching a staged file — the LaTeX-brace trigger is pinned and reproducible,
so the report is complete; (b) revisit the gate only once `bibstruct` is committed AND the 3
entries parse, at which point it guards a clean baseline and needs no ratchet.

⚑ **Standing rule 10 already covers the day-to-day risk** (*read the denominator, not the row
count*), so the unguarded window is not silent — it is documented and the tool self-reports.

### Ε · roundtrip-repair — ✅ DIAGNOSED, AND THE TARGET WAS WRONG (tick 5, 2026-09-09)

**⚑ NOT A PAPERKIT DEFECT. The bug is in `bibstruct.py` — the substrate tool I have used all
session to make claims about `.bib` files.**

My plan entry said *"a field the parse drops is a field no invariant can read"*, implying a paperkit
parser bug. **Refuted:** `paperkit/bib.py` parses these claims correctly — verified by finding
`emergence-collapse`'s claim text rendered in `paper/paper.md`. The engine reads them; `bibstruct`
does not.

**Three instances found, and the trigger is pinned: LaTeX brace constructs inside a BibTeX
brace-delimited value.**

| entry | file:line | the construct |
|---|---|---|
| `grounding-reflected` | `implications.bib:44` | `\cap \mathrm{fp}(d) = \emptyset` |
| `emergence-collapse` | `implications.bib:50` | `\setminus \bigcup_{d \in \mathrm{rests\text{-}on}(c)} \mathrm{fp}(d)` |
| `edge-rests-grounds` | `model.bib:82` | `$\mathrm{eff}(c) = \min\{\, … \,\}$` — **escaped braces `\{` `\}`** |

`bibstruct` is brace-counting to find a value's end and mis-handles `\{`/`\}` and/or `{}` nested
inside `\mathrm{…}` / `\bigcup_{…}`. ⚑ Ruled out: `link` is NOT the cause — `grouping-residual` and
`observe-second-shape` both carry `link` AND parse fine.

**⚑ THE COST TO THIS SESSION, STATED PLAINLY:** every `bibstruct --field claim` census I ran
under-reported by exactly these entries. `--field claim` on `implications.bib` returns **24 of 26**.

**⚑ AND THE TOOL BEHAVED CORRECTLY, WHICH IS THE POINT.** It prints `24 of 26` — the denominator
DECLARES the shortfall — and `--roundtrip` exists precisely to name unparsed bytes. This is
`struct-tools`' own argument working as designed: *"a parser that knows the shape can say UNREADABLE
where a grep can only say nothing."* A grep would have returned 24 lines and no denominator.
**Read the denominator, not the row count.**

**Scope: cross-repo, not paperkit's to fix.** The repair belongs in
`~/github/substrate/scratch/bibstruct.py`'s value scanner. Per `summit`/`census-kit`, this is a
shared-tool defect other repos depend on (gcalculus's `concepts.bib` also carries LaTeX claims —
its 175 entries should be re-checked with `--roundtrip`). **NOT FIXED HERE:** editing a substrate
tool mid-paperkit-tick is out of scope, and the finding is more valuable filed than silently
patched.

**Standing rule added (rule 10, below).**
`paper/implications.bib` lines 44, 50: `claim` in bytes, absent from parse (A2-F8, pre-existing).
**Leverage:** a field the parse drops is a field no invariant reads. Must precede Phase D or new
corpora are authored against unmapped parser blind spots.
**Verify:** `bibstruct --roundtrip` → 0 findings.

### Ζ · boundaries-adequacy — ✅ LANDED, RED BY DESIGN (tick 4, 2026-09-09)

**The red IS the deliverable.** 49 witnesses gating the engine's own tools were swept for the first
time: **45 pass, 4 `broken`.** `broken` = does not pass in a pristine sandbox, i.e. these fail
BEFORE any mutation — not weak witnesses, unrunnable ones. 103 actions, 374s.

    GATE RED: {"verb":"adequacy","verdict":"fail"}
      RED  bnd-check__grade            {"grade": "broken"}
      RED  bnd-closure-script__grade   {"grade": "broken"}
      RED  bnd-dispatch__grade         {"grade": "broken"}
      RED  bnd-wheel__grade            {"grade": "broken"}

**Four DIFFERENT causes. Do not treat `broken` as one bucket.**

**1. `bnd-check` — CAUSED BY MY OWN EDIT, AND CORRECTLY CAUGHT. ✅ FIXED.**
It is the hook-completeness witness. Setting `adequacy = True` created a graded project whose
`:adequacy` was not a `//:hook` member, and it went red on exactly that — its own ⟨P,F,δ⟩ pair
names the case: *dropping the boundaries adequacy target from the hook is CAUGHT as an incomplete
local CI*. **This is audit finding 6 firing as designed**: the hand-transcribed grid rots the
instant a project gains a kind — detected this time rather than silently. Added
`"@paperkit_boundaries//:adequacy"` to `BUILD.bazel`; re-ran: **PASS (7 behaviors, 1 delta)**, and
the witness now uses my target as its own minimum-delta example.
⚑ Comment written quote-free on purpose: `bnd-check` reads quoted tokens out of the member list, so
scare-quotes in a comment parse as a bogus hook member (`BUILD.bazel:121-122` records it catching
exactly that).

**2. `bnd-closure-script` — a LOAD failure, not a check failure. ⚑ STOPPED: needs a judgement.**
`ModuleNotFoundError: No module named 'paperkit'`. Its check is `cmd:python3
../paperkit/tests/boundaries_closure_census.py` — **bare `python3`** — but the file is
self-documented (`:32-42`) as **the FIRST file converted** to package-relative imports
(`from paperkit.tests._boundary import Suite`) under the `Ζ·flat` arc retiring `sys.path` mutation,
and states the property holds *under the project venv*. The conversion is right; the INVOCATION was
never updated. Verified: with `PYTHONPATH` set it **PASSES (8 behaviors, 2 deltas)**.
Two fixes, different costs — NOT chosen:
  (a) give boundaries a `[checks.*]` custom type supplying the path (the `Ζ·entry·point` pattern
      `paperkit/library` already uses via `run-witness`) — localised, but boundaries has no custom
      type today and adding one touches all 49 warrants;
  (b) install the package so `paperkit.tests` imports anywhere — matches the file's own stated
      intent and the arc's direction (`pathaudit` enumerates **95** remaining files), but is
      entangled with the wheel/venv work in the PRE-EXISTING STAGED CHANGESET.
(b) is almost certainly intended and is not mine to land.

**3. `bnd-wheel` — an UNDECLARED INPUT. Ω class. Not mine (staged changeset).**
Run directly it **PASSES (6 behaviors, 1 delta)**. It needs the BUILT WHEEL, which the pristine
sandbox does not stage — so `broken` is a fact about undeclared inputs, not about the witness. This
is exactly Ω: the dependency is real and unnamed. `A paperkit/tests/boundaries_wheel.py` is newly
added in the staged changeset.

**4. `bnd-dispatch` — a REAL bug on a seam already flagged. Not mine (staged changeset).**
Fails one delta pair: *an UNREACHABLE crossing check is UNAVAILABLE, not FAIL*, whose parenthetical
reads *"no `__bool__` so no consumer folds silently; **identity-hashable** so the determinism set
works."* ⚑ That is the `UNAVAILABLE`-singleton finding from the anchor survey:
`unavailable(why, owner)` (`resolver.py:130`) returns a DISTINCT object, so identity comparison is
unreliable while this witness asserts identity-hashability. `M paperkit/tests/boundaries_dispatch.py`
is in the staged changeset — in-flight work on precisely this seam.

**Net:** 45 of 49 engine-tool witnesses are now mutation-swept and sound. Of the 4 reds, 1 was mine
and is fixed, 1 needs an owner decision (2, above), and 2 belong to the staged changeset. **Audit
finding 4 is closed**: the boundary suite is no longer gated-but-never-graded.

**⚑ THE 102-ACTION QUESTION — MEASURED, AND MY WORRY WAS UNFOUNDED.** Last tick I flagged 102
actions (vs `paper/`'s 94,797) as possibly meaning the sweep was not reaching the witnesses.
Measured: **49 `.calc.json` records, one per warrant, all 49 present.** Every boundaries witness WAS
swept. 102 = 49 calcs + 49 grades + aggregation.

The contrast is a DECOMPOSITION difference, not a coverage gap: `pk_calc` emits ONE action per claim
that does its binary-split bisection internally, while `paper/` (via the `Μ·sweep·atom` cell grid)
emits a separate `pk_eval` action PER MUTATION CELL. Same work, two granularities — and the
per-claim form is why boundaries took 374s while paper took 2h08m for far more actions.

⚑ **Consequence for the `−` census (revises Δ-F9):** the per-cell `.eval.json` ledger exists ONLY
for cell-grid projects. `boundaries/` yields a `sens` LIST inside one calc record instead —
e.g. `bnd-clamp` has `baseline: true, sens_count: 7`, a real 7-site fingerprint, the first ever
measured for a boundaries witness. So a coverage/differentiation census must read BOTH shapes: the
per-cell records where they exist, and `calc.sens` where they do not. Reading only `.eval.json`
would report boundaries as having zero coverage.

### Ζ — superseded IN-FLIGHT note (kept per rule 6)
`MODULE.bazel:47` now carries `adequacy = True, calc = True` for `paperkit_boundaries`.

⚑ **`calc = True` is REQUIRED alongside `adequacy`, not optional.** `bibtex.bzl:735` gates
`pk_calc` emission on `calc and wt == "sandbox" and _body(...) != None`, and adequacy's `pk_grade`
READS those calc records — so `adequacy` without `calc` emits grade rules with nothing to read.
Verified unanimous: all 8 pre-existing adequacy projects set both.

`@paperkit_boundaries//:adequacy` materialised and is running. **102 actions** — against `paper/`'s
94,797, from 49 warrants.

⚑ **My first explanation of the small count was WRONG and is recorded so it is not repeated.** I
inferred that `_body(check, custom)` would reject the `cmd:python3 ../paperkit/tests/…` checks
because `..` escapes the project. **False** — `_body` (`bibtex.bzl:169-179`) returns the command
string for ANY `cmd:` check; all 49 pass that conjunct. The real cause is almost certainly
`Δ·scope` footprint scoping (the sweep mutates only sites in files the check READS, and each
boundaries witness reads one test module plus the engine modules it imports), but that is
UNCONFIRMED — do not write it down as fact until measured.

Observed while running, both benign: the `membudget` semaphore doing adaptive OOM-and-retry
escalation (4→8→16→32→64MB) — that is the RAM lease working, not a failure; and Γ-F3's `bnd-wheel`
`builds` field being loud-dropped on every parse.

**Verify:** every `vacuous`/`indeterminate` recorded per claim with its reason, never waived.

### Η · hook-grid — ✅ LANDED as H3 (operator chose H3, tick 6, 2026-09-09)

**H3: keep the explicit list; gate the drift.** The duplication is kept ON PURPOSE — it is what
makes `bnd-check`'s completeness proof sound (two independent textual sources), and generating the
list would let the audited graph supply its own audit. **What was removed is the *silently*, not the
hand-maintenance.**

**Landed:**
- `tools/hook_grid.py` — compares `BUILD.bazel`'s transcribed `//:hook` list against the targets
  `MODULE.bazel`'s `bib.project` flags would emit. Reds on either direction (a target emitted but
  never run; a member nothing emits), plus two exemption-integrity checks.
- Wired in `.githooks/pre-commit` beside `hook-index` — text-only, so it fails before any build cost.
- Current: **12 projects, 27 emitted, 3 declared exemptions, 1 harness member = 25 transcribed**,
  reconciling exactly with `bazel query tests(//:hook)`.

**Emission rules, read from the generator** (the only hand-copied thing — 4 rules vs a 24-line list):
`gate` unconditional (`bibtex.bzl:932`) · `adequacy` iff `adequacy=True` (`:985`) · `cohere` iff
`emerge` (`:892`) · `decisions` iff `emerge` (`:906`).

**⚑ Η-F1 — THE THREE `local` PROJECTS ARE EXEMPT BY A POLICY THAT EXISTS NOWHERE IN CODE.**
The gate first red-flagged `@paperkit_{image,report,setup}//:gate` as drift. Investigated: the
generator emits `gate` for every project **regardless of tier** — there is no `local ⇒ omit from
//:hook` rule anywhere in the build. So the omission is a HUMAN policy recorded only in prose, and
inferring it from the `tier` attribute would be this gate INVENTING a rule the tree does not state.
Declared them in `HOOK_EXEMPT` with a per-entry reason instead, each pointing at Ω and at open
operator decision G4. Two of the three were set to `local` by this session (Α) on an ANALOGY rather
than a measured dependency — so these are the first entries to revisit when Ω resolves. Added
stale-exemption and contradicted-exemption checks so the exemption list cannot rot the way the
member list did.

**⚑⚑ Η-F2 — `bnd-check` WAS SCRAPING 24 OF 25 MEMBERS AND REPORTING PASS. FIXED.**
`boundaries_check.py:34` used `re.search(r'…tests\s*=\s*\[(.*?)\]', …)` — **non-greedy**. The member
list's own comments contain `[[place-by-ownership-not-need]]` (`BUILD.bazel:191`), so the first `]`
the match finds is INSIDE a comment, four lines above the real close. **Measured: 24 scraped vs 25
from `bazel query`** — it silently dropped `@paperkit_library//:decisions` (`BUILD.bazel:194`), *the
very member whose earlier omission the surrounding comment was written to narrate.*

So the completeness proof ran over 24 of 25 members and reported PASS: **a green that measured the
scrape, not the tree** — the exact defect class this repo keeps rediscovering. Replaced with
bracket-counting in BOTH `hook_grid.py` and `boundaries_check.py`; `bnd-check` re-run: **PASS
(7 behaviors, 1 delta)** over the full list.

⚑ Found only because `hook_grid.py` COPIED the regex and inherited the bug — the copy is what made
it visible. Reuse surfaced a latent defect in the original.

**Discrimination verified** (`scratchpad/test_hook_grid.py`, 7 cases, all correct): clean tree passes;
a project gaining `emerge=True` with nothing wired reds (**reproducing the Ζ incident exactly**); a
deleted member reds; a member nothing emits reds; a stale exemption reds; a contradicted exemption
reds; and the non-greedy scrape is *proven* to lose `@paperkit_library//:decisions`.

### Η — the DECISION RECORD (kept per rule 6; H1/H2 not taken)

**The plan's design for Η conflicts with `bnd-check` by construction, not by omission.** The plan
called the `bnd-check` edit a "required companion edit". It is more than that: `bnd-check`'s whole
METHOD is textual over the literal member list, so generating the suite does not need `bnd-check`
adjusted — it needs `bnd-check` **RE-FOUNDED on a different source of truth**.

**Measured** (`paperkit/tests/boundaries_check.py`):
- `:29-30` reads `BUILD.bazel` and `MODULE.bazel` as TEXT.
- `:33-35` `hook_tests()` regex-extracts the `test_suite(name="hook")` member list.
- `:38-48` `projects()` parses `bib.project(` lines for `adequacy = True` / `emerge = True`.
- `:51-62` `incomplete()` compares the two: a graded project owes `gate`+`adequacy`, an emerge
  project owes `cohere`.
- ⚑ `:92-93` asserts by **SET-EQUALITY** that every member matches
  `@\w+//:(gate|adequacy|cohere|decisions)$` plus exactly `//canary:canary`. Its own comment
  (`:88-89`) says set-equality was chosen deliberately because *a bare project-shaped-or-not filter
  would silently admit any stray member*.

So reducing `//:hook` to `@paperkit_*//:all` labels **fails that assertion by construction** —
`:all` does not match the regex. And the soundness of `bnd-check`'s completeness argument COMES FROM
the list being explicit and enumerable in text.

**Both positions are correct and cannot both hold as written:** the grid should not be
hand-maintained (`bibtex.bzl` already knows it — verified: it emits all four kinds at `:902`,
`:915`, `:932`, `:985`, guarded by `emerge`/`adequacy`), AND `bnd-check` derives completeness by
comparing two independent textual sources.

**Current state, measured:** 24 hand-transcribed `@paperkit_*` members + canary = **25 targets**,
and `bazel query tests(//:hook)` enumerates all 25 authoritatively.

**⚑ THREE OPTIONS, PRICED. This is an owner decision about where the authority for "local CI is
complete" lives.**

**(H1) Generate the suite; re-found `bnd-check` on `bazel query`.** Replace text-scraping with
`bazel query tests(//:hook)` as the member source, keep the `MODULE.bazel` side as-is.
- *Buys:* the grid stops being hand-typed; adding a project costs one line, adding a KIND costs zero.
- *Costs:* `bnd-check` gains a dependency on running Bazel from inside a Bazel-run test (nesting —
  the repo already treats this warily, cf. `_grade_parallel`'s "a heavy check may itself fan out a
  nested gate"). Set-equality over member SHAPE is lost, or must be re-expressed over the query
  output.
- *Risk:* the witness would then read the same graph it is meant to audit — losing the independence
  that makes it a check rather than a tautology. ⚑ [[instrument-vs-gate]].

**(H2) Generate the suite; re-found `bnd-check` on the GENERATOR.** Have `bnd-check` compare
`bibtex.bzl`'s emission rules against `MODULE.bazel`'s tags — i.e. audit the generator's grid
directly, and drop the hook-list comparison entirely.
- *Buys:* independence preserved (two sources: the generator's logic and the project declarations),
  and it audits the thing that actually decides membership.
- *Costs:* `bnd-check` must parse `.bzl` control flow, which is strictly harder than a member list —
  and audit finding 1 already says the generator itself is gated only by `bnd-lint`'s three regexes.
  This would deepen reliance on reading 80KB of Starlark textually.

**(H3) KEEP the hand list; make its completeness GENERATED-CHECKED.** Leave `//:hook` explicit
(so `bnd-check` keeps its method and its set-equality), and add a gate that fails when
`bibtex.bzl`'s emitted kinds ≠ the transcribed list — i.e. keep the redundancy and make the drift
loud instead of removing the redundancy.
- *Buys:* nothing existing is re-founded; `bnd-check` is untouched; the rot becomes a red rather
  than a silence. Smallest blast radius.
- *Costs:* the list is still hand-maintained — this fixes the DETECTION, not the duplication.
  Adding a kind still needs a human edit, but now it cannot be forgotten silently.

⚑ **My reading, offered as a recommendation and not acted on:** H3 preserves the property that
matters (two independent sources, so a green is not a tautology) and directly answers the class note
at `BUILD.bazel:176-182` — *all 23 members can fall out this way, silently* — by removing the
SILENTLY rather than the hand-maintenance. H1 is the plan's original intent but trades independence
for convenience, which is the wrong direction for an instrument in a repo whose recurring defect is
green-that-measures-the-census. **Ζ is live evidence for H3:** the rot was caught the moment it
happened, by the existing witness, with no generation at all.

### Η — ORIGINAL PLAN NOTE (kept per rule 6, superseded by the above)
`tools/bibtex.bzl` emits per-project `test_suite(name="all")`; `//:hook` reduces to labels +
`//canary:canary`. ⚑ **`bnd-check` companion edit is REQUIRED** (`BUILD.bazel:121-122` reads
quoted tokens from the member list) — skipping it converts a completeness check into a check of a
stale list.
**Leverage:** highest instrument leverage. New genre project → one line; new target kind → zero.
Retroactively fixes the report's scope (A2-F3). Do BEFORE Phase D adds projects.
**Verify:** `bazel test //:hook` green; membership matches the generator's own grid.

### Θ · genre-docstring — ✅ LANDED (tick 20, 2026-09-10)
See Landed. D1 verified at BOTH ends before editing; docstring corrected, wire format untouched.

### Ι · brief — ✅ LANDED (tick 21, 2026-09-10). See Landed, and Ι-F1.

### Ι — original READY note (kept per rule 6, superseded by the above)
⚑ **Θ's verification sharpened Ι's premise.** `claims.py:884` `genre_registry()` tests
REGISTRATION ONLY, never invocation: it writes `[genres.brief]` into a **tempdir** fixture
(`:890-892`), then compares `reg["brief"]["cmd"] == "python3 checks/brief.py"` as a STRING
(`:894`). **`brief.py` is never executed, so the fixture passes today with the file absent** —
it is not a gate fixturing a missing file, it is a gate that cannot tell whether the file exists.
That is a WEAKER starting position than the plan assumed and makes Ι more valuable, not less:
nothing in the tree currently executes a declared genre against a real project.
Confirmed absent: `paper/checks/` holds `claims.py`, `gen_formulas.py`, `fixture` — no `brief.py`.
Confirmed unregistered: `genre.py --check paper` → `4 registered (atomic, collection, staged, talk)`.
`paper/checks/brief.py` + `[genres.brief]` in `paper/paper.toml`.
**Leverage:** proves `run_declared` on a real project (today: only a temp-dir fixture at
`claims.py:1020`); closes a gate fixturing a file that does not exist (`claims.py:884-901`); hits
D1 cheaply. The end-to-end proof Phase E repeats 21 times.

### Κ · records-channel — ✅ LANDED (tick 23, 2026-09-10). `PK-GENRE-BLIND` IS CLOSED. See Landed.

### Λ · arch — READY (tick 36 re-derivation: **Ε does NOT gate it**; Β and Η landed)
New `arch/` project; `ARCHITECTURE.md` becomes a projection. Three false assertions become
counting witnesses. §3.6 preserved as declared-nonmechanical prose.

**⚑ Blocker list was STALE. Re-derived, with the measurement (tick 36):**
- **Β** — landed (tick 35). The `d.name` collision class is closed, so `arch/` cannot collide.
- **Η** — landed (tick 6).
- **Ε** — ⚑ **does not gate Λ.** Ε is `bibstruct` dropping `claim` on entries carrying LaTeX braces
  (confirmed still live: `--roundtrip paper/implications.bib` → 2 of 27 unparsed). But
  `ARCHITECTURE.md` carries **no LaTeX**: a grep for `bigcup|\{|\}|$` finds **2 lines, both `$HOME`
  in prose** (`:50`, `:234`) — shell syntax, not math. Ε bites `paper/` only, and inheriting it as
  a blocker was an assumption nobody had checked.

**The counts, measured from their OWNERS (audit finding 2, now exact):**

| assertion | site(s) | measured | owner |
|---|---|---|---|
| "17 modules" | `:179` | **26** non-test files (83 total, 57 tests) | `components.bzl` COMPONENTS |
| "eight projects" | `:147`, `:190`, `:260` | **12** wired | `MODULE.bazel` bib.project tags |
| — | — | 14 `paper.toml` on disk | the filesystem |

⚑ **"eight" IS the component count** (`delta, gate, kernel, library_kernel, model, project,
resolver, tests`) — so the prose likely conflated COMPONENTS with PROJECTS. A counting witness must
therefore name WHICH count it asserts; "eight projects" is not merely stale, it is a category error
that a bare number-refresh would preserve.

### Μ · graph — ⚑ SUPERSEDED (tick 39). The PROJECT is not needed; the CLAIMS are, and they landed.

The plan's sole stated reason for a separate `graph/` project was that `boundaries/` inherited
`adequacy=false`. **Ζ set `adequacy = True` at tick 4** (`MODULE.bazel:57`), so the reason is gone,
and `boundaries/` already carries all three generator claims (`bnd-genre-emit`, `bnd-generator`,
plus `bnd-lint`) across its `engine` section. A new project would add a `paper.toml`, a rubric, a
BUILD file and a hook member to host claims that already have a home — cost with no argument.
⚑ Λ-F1's lesson applied one tick later: **measure whether a plan step is still right before
executing it.**

### Μ — original BLOCKED note (kept per rule 6, superseded by the above)
New `graph/` project (NOT `build/` — collides with the real dir). Generator semantics for
`bibtex.bzl` + `calc.bzl`, currently gated only by `bnd-lint`'s three regexes.

### Ν · genres — READY (Ι, Κ landed). Ν.0 done; see Ν-F1/F2/F3.
The 21, split by axis: 7 exist and need naming, 9 need a `[genres.*]` script, 5 need a corpus.

**Corrected by tick 24's sweep — do not re-derive these:**
- ⚑ **Check a proposed objective against the four BUILT-INS before writing it.** `brief` turned out
  to be `staged` (Ν-F1). The reuse question is over the OBJECTIVE population, not the file
  population; `find checks/genre_*.py` answers the wrong one.
- **loose-leaf is a REAL RESIDUE** (Ν-F2) — `collection` at low γ is not it, measured. Stays in
  the "needs a script" column.
- **The discriminating axis is WHAT THE OBJECTIVE READS, not γ** (Ν-F3): bracketing
  (`staged`/`collection`, γ-sensitive) vs claim text (`talk`) vs neither (`atomic`, γ-invariant by
  construction). Ν's 9 scripts should be sorted on that axis, since Κ now makes claim-text
  genres expressible for the first time.
- ⚑ **`PK-GENRE-BLIND` IS RETIRED** (Κ, tick 23). Do not cite it as an obstacle for new genres; the
  four residuals that collapsed onto it need re-verdicting against the records channel.

### Ξ · residuals — RE-VERDICTED (tick 25, 2026-09-10). **3 of 4 are UNBLOCKED; 2 of 3 obstacle
### keys are RETIRED.** See Ξ-F1/F2.

| residual | old verdict | **new verdict** |
|---|---|---|
| quick-reference | BLOCKED-ON-`PK-GENRE-BLIND` | **UNBLOCKED** — claim text reaches the genre (Κ) |
| index/catalog | BLOCKED-ON-`PK-GENRE-BLIND` | **UNBLOCKED** — the term is in the claim text |
| serial/issue-based | BLOCKED-ON-`PK-BIB-PROVENANCE` | **UNBLOCKED** — `_src` was there all along (Ξ-F1) |
| troubleshooting | BLOCKED-ON-`PK-GENRE-PURE` | **STILL BLOCKED** — verified, Ξ-F2 |

Obstacle keys: `PK-GENRE-BLIND` **RETIRED** (Κ) · `PK-BIB-PROVENANCE` **FALSE, retired** (Ξ-F1) ·
`PK-GENRE-PURE` **STANDS** (Ξ-F2). Do not cite the retired two.

---

## Landed

### Σ — `bazel test //:hook`: THE FULL GRAPH, AND A MEASURED WASTE (2026-09-10, tick 41)

**First full-graph run since `arch` joined at tick 38.** Nothing had exercised the 13-project graph
end to end; every tick since verified claims in isolation, which cannot catch an integration
failure.

**Integration confirmed at the phase that would have failed**: `Loading` completed with no Starlark
error, `Analyzing: 27 targets` — **exactly the count `hook_grid` derives** — then 645 actions over
**104 packages / 75,797+ targets configured**. So `arch/`'s repo generates, its `:gate` and
`:adequacy` resolve, and Μ.1's conditional `:genres` emission survives contact with the real graph.

Per-project `:invariants` verdicts came back green as they landed — `demo` (1 claim), `config` (4),
`guide` (9) — each reporting *"`--without-K` — N cited claim(s) each carry a distinct witness"*.

#### ⚑⚑ Σ-F1 — ELEVEN OF THIRTEEN PROJECTS HAVE NO MEMORY MANIFEST, AND EVERY CELL PAYS FOR IT

The run's own output shows every `config/` and `boundaries/` cell climbing the OOM ladder:

    OOM at 4MB — retrying at 8MB · at 8MB → 16MB · at 16MB → 32MB · at 32MB → 64MB

**Four killed processes per cell before one survives.** Measured 19 OOM retries in the first ~70
actions alone.

**Cause, measured not inferred**: only **2 of 13** projects carry a `mem.json` — `paper/` and
`paperkit/library/`. The library's declares `{"file": 256, "def": 64, "claims": {…}}`, so its cells
start at a real reservation. The other **eleven have no manifest at all**, so every cell starts at
the 4 MB floor and ladders up.

⚑ **The discriminating evidence is in the same run**: once execution reached `paper/` and root
claims — the projects that DO have a manifest — **the ladder stopped**. Same machine, same build,
same action kind; the only difference is the manifest.

⚑ **This is the Χ thread's subject, now visible in a LIVE RUN rather than inferred.** Χ established
that `mem_learn` already classifies grid cells (`mem_learn.py:36-54`) and that `bibtex.bzl:920`
feeds it file-calcs only. Σ-F1 is what that costs: **four wasted process spawns per cell across
eleven projects**, every build, silently — the retry ladder makes it correct-but-expensive rather
than broken, which is exactly why nobody noticed.

**Not fixed here.** Generating a `mem.json` per project needs a `--config=memobserve` run to
populate peaks (Χ-F7/F8), and that is a sweep-scale job that must not race this one (standing rule:
one sweep at a time). ⚑ And Χ's open question still gates the shape: the manifest wants a per-claim
× per-resolution key, and `claims[]` holds ONE number per claim with no resolution key
(`prose-projected` wants `file=8, def=64`, an 8× spread) — **latent today because both equal their
defaults**, but a manifest generated for eleven more projects is exactly what would make it active.

### ⚑⚑ Σ-F7 — Χ's COLLISION DOES NOT GATE TEN OF THE ELEVEN, AND A MANIFEST ALONE DOES NOT TAKE (tick 45)

**The gating premise, re-derived and NARROWED.** I had recorded Χ's per-claim × per-resolution
collision as blocking Σ-F1. Measured from the generator:

- `bibtex.bzl:786` — the **def-resolution grid (`pk_eval` cells) is emitted ONLY under `emerge`**.
- `MODULE.bazel` — **only 3 projects declare `emerge = True`**: `paper`, `.` (root),
  `paperkit/library`. Two of the three ALREADY have a manifest.

⚑ So **ten of the eleven manifest-less projects are single-resolution (`file` only)** and the
collision cannot arise there. It gates `root` alone. My "Χ's key-shape question gates the manifest's
shape" was true of one project, stated of eleven.

⚑ And the shape is smaller than assumed: `paperkit/library/mem.json` is
`{"claims": {"gate-dispatches": 128}, "def": 64, "file": 256}` — **one override row out of 43
claims**; everything else rides the resolution default. ⚑ Note `file` (256) needs **MORE** than
`def` (64), inverting the direction Χ's note assumed.

**Generated one for real.** `bazel build --config=memobserve @paperkit_arch//:mem_learn` →

    {"claims": {"arch-projects": 4, "arch-two-pk-grade": 4}, "file": 8}

Single resolution, exactly as predicted. ⚑ Confirms Χ-F7 as well: a DEFAULT build writes the
sentinel `0` (verified by reading `arch-components__calc.peak` → `0`), and `mem_learn` correctly
returns `{"claims": {}}` rather than learning a false floor.

#### ⛔ Σ-F7b — THE MANIFEST DID NOT TAKE, AND MY PREDICTION WAS WRONG

I installed `arch/mem.json`, added it to the filegroup, rebuilt — and **the OOM ladder still starts
at 4MB**. The generated `BUILD.bazel` still carries `mem = 0` on all six cells.

**Cause, read from source** (`bibtex.bzl:617-620`):

    memp = …dirname.get_child("mem.json")
    if memp.exists:
        repository_ctx.watch(memp)      # ← only watched IF IT ALREADY EXISTS
        mem = json.decode(…)

⚑ **A repo rule cannot be invalidated by the CREATION of a file it did not previously watch.** The
prior evaluation found no `mem.json`, so it registered no watch on that path, so writing one is
invisible to Bazel's dependency tracking. The generator is correct for a manifest that CHANGES and
blind to one that APPEARS — and every one of the eleven projects is exactly the appearing case.

**Not forced.** Making it take needs a repo re-fetch (`--repo_contents_cache=` did not do it; the
targets were fully action-cached), and clearing repo caches has a blast radius across all 13
projects — wider than this tick should take unilaterally, and it would race nothing but cost a full
regeneration of `paper`'s 52,584 `pk_eval` targets.

**Owner's call, and it is a one-line generator question**: whether `bibtex.bzl` should
`repository_ctx.watch(memp)` **unconditionally** (watching a non-existent path so its creation
invalidates), which is the standard Bazel idiom for exactly this, or whether manifests are expected
to be generated once at project creation and this is working as intended.

#### ⚑⚑ Σ-F8 — THE DIAGNOSIS IS NOW **PROVEN**, AND I HAD IT HALF-WRONG (tick 46)

Tick 45 asserted *"a repo rule cannot be invalidated by the CREATION of a file it never watched"*.
⚑ **That is wrong as a statement about Bazel** — `repository_ctx.watch()` (8.7.0 here) explicitly
supports NON-EXISTENT paths, and watching one means its later creation DOES invalidate. A finding
that names the wrong law is worth less than no finding, so it was tested.

**THE MARKER FILE IS THE AUTHORITY, and it settles it.** Bazel records exactly what each repo rule
watched:

    @+bib+paperkit_arch.marker      FILE:@@//arch/paper.toml   …
                                    FILE:@@//arch/warrants.bib …
                                    ⚑ NO mem.json line

    @+bib+paperkit_library.marker   FILE:@@//paperkit/library/concepts.bib …
                                    FILE:@@//paperkit/library/mem.json      …   ⚑ WATCHED
                                    FILE:@@//paperkit/library/paper.toml    …

**Same generator, same code path, opposite outcome — decided solely by whether `mem.json` existed
when the rule last ran.** `bibtex.bzl:618` guards the call: `if memp.exists: repository_ctx.watch(memp)`.
So the mechanism I named was right; the claim about Bazel's capability was wrong. **The guard is
the defect, not the platform.**

**And it explains a result my tick-45 reading could not.** A probe modifying an EXISTING
`arch/mem.json` — content change, not `touch`, since Bazel digests rather than stats — ALSO failed
to re-run the rule (`mem` stayed `[0]`). Under "creation isn't watched" that is unexplained; under
"the path is not in the marker at all" it is expected: no watch, no invalidation, in either
direction.

⚑ **A second, smaller defect, and it was MINE**: `arch/mem.json` arrived `-r-xr-xr-x` because I
`cp`'d it out of `bazel-bin`, where outputs are read-only. `paperkit/library/mem.json` is
`-rw-rw-r--`. The probe hit `PermissionError` before it could test anything — **an installation
step that copies a build output must restore a writable mode**, or the manifest is un-editable by
the next reader. Fixed with `chmod 644`.

~~**The owner's call is unchanged but now precisely priced**: one line, `watch(memp)` before the
`.exists` test rather than inside it.~~

### ⚑ Σ-F8 — FIXED (tick 47). ANOTHER OVER-CAUTIOUS DEFERRAL; THE TREE SETTLED IT.

**Third time this pattern has appeared** (Ι-F1 tick 22, Σ-F3 tick 42, now this): I deferred a
one-line change as an owner call, then found the tree already establishes the intended behaviour.

**Two independent lines of evidence, both in the file itself:**
1. ⚑ **The block's OWN comment promises it**: *"Watching the projection invalidates exactly when a
   RESERVATION changes"*. A manifest APPEARING is a reservation changing — from the cold-start
   floor to a learned value. The code did not do what its comment said.
2. ⚑ **The unguarded form is already the idiom in this same file** — the warrant read at `:590`
   calls `repository_ctx.watch(wp)` with no `.exists` test, because it is a must-read input.
   `paper.toml` at `:564` is guarded because it is genuinely optional; `mem.json` was guarded like
   an optional input while behaving like a must-watch one.

**The change**: `watch(memp)` moved OUTSIDE the `.exists` test (the read stays inside).

**Measured — the manifest takes, and the ladder shortened:**

    before:  mem = 0 ×6      every cell climbs 4→8→16→32MB
    after:   mem = 8 ×4, mem = 4 ×2      ⚑ ZERO cells start at the 4MB rung

The per-claim overrides resolved correctly through `_membucket`'s ladder: `arch-projects` and
`arch-two-pk-grade` at 4, the rest at the `file: 8` default.

**Verified by discrimination, 5/5** (`scratchpad/test_mem_watch_fix.py`) — all THREE directions,
because a fix that always-invalidates is as wrong as one that never does:
1. the manifest TAKES (generated `[4, 8]`, not `[0]`) · 2. **the 4MB rung is GONE** (0 cells at the
floor, was every cell) · 3. a manifest CHANGE takes (`[77]` after an edit — the behaviour the
comment promises) · 4. **REMOVING it falls back to the floor** (`[0]`, no stale value) · 5. restored.

⚑ **`lint_bzl` clean** on all four `.bzl` files (`bnd-lint` is the gate that owns them).

⚑ **Scope confirmed by counter-example**: `@paperkit_boundaries//:gate` STILL ladders from 4MB —
it has no `mem.json`. The fix makes a manifest effective; it does not create one. **Σ-F1's ten
remaining projects are now unblocked follow-on work** rather than blocked on a generator defect.

### ⚑⚑ Σ-F9 — "ELEVEN MISSING" WAS WRONG, AND `cp` IS THE WRONG PROCEDURE (tick 48)

**The population, re-derived from MODULE.bazel rather than from four `ls` calls:**

| | count | projects |
|---|---|---|
| HAVE a manifest | **7** | paper, root, paperkit/library, guide, talk, render, arch |
| CAN gain one (`calc = True`) | **3** | boundaries, config, demo |
| ⚑ CANNOT — no `calc` | **3** | setup, report, image |

⚑ **Σ-F1's "eleven of thirteen" was measured by listing four directories.** Seven already had
one — including `guide`, `talk`, `render`, and root, which I counted as missing. And three
**cannot** have one: no `calc` ⇒ no `pk_calc` ⇒ no peaks ⇒ **no `:mem_learn` target at all**. A
manifest there is not missing; it is not a thing that exists. Counting it is the
census-over-the-wrong-population error `mem_converge.py`'s own docstring names.

#### ⚑⚑ THE PIPELINE ALREADY EXISTS AND I WAS ABOUT TO BYPASS IT

`git log guide/mem.json` → one commit, `Τ·mem·learn — the reservation loop, closed and
self-checking`, which states the intended procedure:

    observe   a cell reads its own cgroup memory.peak (--config=memobserve)
    harvest   mem_harvest.py folds peaks into mem.sqlite, MERGE never replace — "a warm build
              re-executes few cells, so overwriting a manifest with a partial harvest DELETES
              measurements an earlier pass established"
    project   mem_project.py derives mem.json FROM THE STORE
    size      the grid reads the manifest down the (project, resolution, claim) ladder

**I installed `arch/mem.json` by `cp` from `bazel-bin`, skipping harvest and project entirely** —
exactly the "overwriting with a partial harvest" the commit warns against. It happened to be
harmless for `arch` (a cold project, one observe pass, nothing prior to delete) and would NOT be
for a project with existing measurements.

~~⚑ **The 8-vs-256 gap is the tell I nearly ignored.** `config`/`demo`/`arch` measure `file = 8`;
every pre-existing manifest says `file = 256` and root says `def = 1024`. Those are real measured
values from a full pass, not placeholders. **A warm partial build under-reads, which is precisely
why the store merges.** Installing `file: 8` over a project that had measured 256 would cap cells
at 1/32 of their true peak.~~

### ⚑⚑ Σ-F10 — THAT WARNING WAS BACKWARDS: `256` IS THE SEED, `8` IS THE MEASUREMENT (tick 48)

**I asserted the committed 256s were "real measured values from a full pass". They are not, and
three independent lines say so:**

1. ⚑ **Six of seven manifests say `file = 256` EXACTLY**, across projects that differ
   structurally — `guide`/`talk`/`render` have no grid and no `def`; `paper`/root/`library` do.
   **A measurement does not land on the same number for six unlike projects.** The uniformity is
   itself the evidence.
2. ⚑ **`git show 8dc9868` — identical blob hash `e1b0174`** for `guide`, `talk` and `render`.
   Byte-identical files created in one commit: a TEMPLATE, not three observations.
3. ⚑⚑ **THE STORE SETTLES IT.** `mem.sqlite` holds **125 observations for exactly TWO projects**:

       paper     81 rows   max 226,521,088 B  (~216 MB → 256 is the next power of two)
       library   44 rows   max 205,271,040 B  (~196 MB → likewise)

   **`guide`, `talk`, `render` and root have ZERO rows.** Nothing backs their `256`; it was copied
   from paper's real figure.

**So the direction is inverted from what I recorded.** `file = 8` (measured for `arch`, `config`,
`demo`, and now `boundaries`) is a **32× improvement** over a seeded 256 — not a regression that
would cap cells at 1/32 of their peak. `boundaries` confirms the shape is systematic rather than an
`arch` artifact:

    boundaries: {"file": 8, "claims": {23 claims at 4}}   (52 claims, no grid)

⚑ **The merge warning still stands where it applies** — `paper` and `library` have 125 real
observations and a partial harvest there WOULD delete them. It does not apply to the four projects
with no rows at all, which is what I conflated.

⚑ **And `mem_converge.py` is scoped to GRID projects only** (the 3 with `emerge`), so it never had
an opinion about `guide`/`talk`/`render`/`boundaries`/`config`/`demo` — their seeds were outside
every check.

#### ⚑ Σ-F9b — `mem_converge.py` REPORTS A FALSE "NOT CONVERGED", AND IT IS Β-F1's SHAPE AGAIN

    library     cells=67514   at-floor=0   def=MISSING   NOT CONVERGED
    paper       cells=79228   at-floor=0   def=64        converged
    root        cells=16376   at-floor=0   def=1024      converged

`paperkit/library/mem.json` **contains `"def": 64`.** The checker looks for it at
`library/mem.json` — `mem_converge.py:68` builds the path as `"%s/mem.json" % proj` from the REPO
SUFFIX. That directory no longer exists (the staged rename `library/` → `paperkit/library/`).

⚑ **Third occurrence of `@paperkit_X` ⇒ path `X`** — Β-F1 (`report/gen.py`'s `_hook_names`),
Μ-F3 (my `bnd-generator` scanner), now this. It holds for twelve of thirteen projects and fails on
the one whose path differs. ⚑ Its own output contradicts it: `at-floor=0` means every cell IS
sized.

⚑ The file's header already warns why this survived: **`Ζ·mem·unwired` — "referenced by no
BUILD.bazel, no .bzl, no hook and no warrant — nothing runs it, so nothing would notice it
breaking. An instrument earns trust per-use."** It broke, and nothing noticed.

**NOTHING INSTALLED THIS TICK.** The generated manifests sit in `bazel-bin`. Installing them
correctly means `mem_harvest.py` → `mem_project.py` (which merges), not `cp` — and that is a
different, larger job than this tick's remit. ⚑ The `arch/mem.json` installed at tick 45 should be
re-derived through the store before it is trusted as anything but a cold-start improvement.

### ⚑ Σ-F11 — THE PIPELINE RUN PROPERLY: 4 MANIFESTS FROM THE STORE (2026-09-10, tick 49)

**Ran the real loop** — `--config=memobserve` → `mem_harvest.py` → `mem_project.py` — after
verifying its safety property at source rather than from prose (twice burned on this subsystem):

⚑ **`deposit` is MONOTONE AND THE DATABASE ENFORCES IT**: `ON CONFLICT … SET bytes =
max(bytes, excluded.bytes)` (`mem_harvest.py:68-81`). A partial harvest can only RAISE a value.
Its docstring names the bug this replaced — *"a hand-written merge over mem.json … taking max over
THAT harvest lowered library's manifest from 512/41-overrides to 256/2 on a narrow pass."*

**The store went 125 → 189 observations, 2 → 6 projects:**

    paper       81 rows   226,521,088 B      library     44 rows   205,271,040 B
    boundaries  53 rows     5,070,848 B      arch         6 rows     4,947,968 B
    config       4 rows     5,115,904 B      demo         1 row      4,485,120 B

⚑ **Σ-F10 CONFIRMED BY MEASUREMENT, not just by blob hashes**: the four new projects peak at
**~5 MB**; `paper`/`library` at **~215 MB**. A genuine ~40× difference, so `file = 8` is a real
reading and the seeded `256` was ~50× over-provisioned on projects that never measured anything.

**Four manifests projected FROM THE STORE** (`boundaries`, `config`, `demo`, and `arch`
re-derived), each `{"claims": {}, "file": 8}`.

⚑ **`mem_project --check` CAUGHT MY tick-45 `cp` AS STALE** — the pipeline's own freshness gate
refused the hand-installed file. Its header says why: *"GENERATED, never authored
(project-dont-author)"*. The difference was real: `cp` carried two per-claim overrides at 4 from a
warm partial run; the store's monotone max resolved all six `arch` claims to 8. **The merge did
exactly what it exists for.**

#### ⚑ Σ-F11b — `mem.json` IS NOT DELIVERED BY THE FILEGROUP, AND I ADDED IT TO ONE

`guide/BUILD.bazel` does **not** list `mem.json`, and its manifest has worked since August.
Neither does `boundaries/BUILD.bazel` — yet its 53 cells now generate at `mem = 4|8`, **zero at the
floor**, with no filegroup entry at all.

The repo rule reads it at **FETCH time** (`repository_ctx.read`), not from the sandbox. So the
`"mem.json"` line I added to `arch/BUILD.bazel` at tick 47 is harmless but wrong-headed — I
generalised Σ-F5's `ARCH.md` staging lesson to a file that reaches the generator by a different
route entirely.

#### ⚑ Σ-F11c — `file = 8` IS TOO LOW FOR SOME CLAIMS, AND THE LADDER IS DOING ITS JOB

`bazel build @paperkit_boundaries//:gate_rec` after installing: **173 OOM retries**, and
`bnd-delta` climbed **8 → 16 → 32 → 64 → 128 MB**, taking 75s.

**This is the loop mid-convergence, not a defect.** The observe pass measures what the cells
actually touched on THAT run; a claim whose heaviest path did not execute reports a low peak. The
retry ladder rescues it, the next harvest records the higher figure, and the monotone max keeps it.
⚑ That is precisely why `deposit` maxes rather than replaces — and why one observe pass is a
starting point rather than an answer.

**Convergence needs a second iteration**: observe → harvest → project again, until
`mem_project --check` is clean and the climb count stops falling.

### ⚑⚑ Σ-F13 — Σ-F12's "OWNER CALL" WAS THREE OPTIONS WHERE THE TREE OFFERS ONE, AND THAT ONE IS BLOCKED ON A VENDORING RULE (2026-09-10, tick 51)

**Σ-F12 priced three options. Two are refuted by the tree; the survivor is blocked by an explicit
ownership banner, not by a design question.**

#### The repair ALREADY EXISTS, is TESTED, and has ONE of its TWO callers wired

`pk_eval` (`calc.bzl:446-455`) carries the `Τ·mem·observe·inside` comment recording **this exact
defect and its fix**:

> *"the peak is read BY eval.py, from inside the cgroup-scope cell, not by a trailing shell
> statement outside it. The `; read-the-peak` form ran AFTER the scope exited and sampled bazel's
> sandbox cgroup instead: 4.7MB reported for a cell whose in-scope peak is 35MB and which OOMs
> under a 32MB cap."*

⚑ **So Σ-F12 was not a discovery — it was a re-discovery of a defect this repo already diagnosed,
fixed, and documented for the OTHER caller.** `tools/cellcgroup.py`'s module docstring is Σ-F12,
written before I wrote it, with the same measurement.

**The structural gap, measured with the owning tools (rule 7):**

| | `pk_eval` (fixed) | `pk_calc` (defective) |
|---|---|---|
| payload | `tools/eval.py` (a py_binary, `tools = [...]`) | `paperkit/discriminate.py` (engine, `inputs =` only) |
| peak read by | `cellcgroup.write_peak()`, **inside** the scope | a trailing `; { … }` shell stmt, **outside** it |
| verified | `--calls write_peak` → 1 def, **2 calls, both `eval.py`** | `--calls write_peak` → **0 calls** |

`--literal '--peak'` over `tools/ paperkit/` → **1 site**, `cellargs.py:64`, declared
*"write this cell's in-scope memory.peak here"*. The seam is real and has exactly one consumer.

#### ⚑ WHY OPTION 1 CANNOT BE APPLIED AS WRITTEN: `discriminate.py` CANNOT REACH `cellcgroup`

`--imports paperkit/discriminate.py` → 10 sibling imports, all engine-internal (`bib`, `grader`,
`layout`, …), 5 stdlib. **The engine package does not import from `tools/`**, and `pk_calc` stages
no Python tool (only `_cap`, the cgroup-scope binary) — where `pk_eval` declares
`tools = [ctx.attr._tool[DefaultInfo].files_to_run]`. So "call `write_peak` from the calc payload"
requires either staging a tool into `pk_calc` or putting cgroup vocabulary in the engine kernel.

#### ⚑⚑ THE CHEAPEST FIX IS IN `cgroup-scope` — AND ITS OWN BANNER FORBIDS IT

`cgroup-scope` **creates** the scope, holds its path in `$CG`, already reads `$CG/memory.events`
once per climb attempt (`_oom_count`), and `rmdir`s `$CG` in an EXIT trap. Reading
`$CG/memory.peak` before that trap is the *same file, same scope, same lifetime* as a read it
already performs. Σ-F12's option 1 ("cgroup-scope knows the scope path it created") is therefore
~3 lines at a site whose vocabulary already exists.

⚑ **And the climb makes it MORE correct, not less**: the retry loop re-runs the payload in the
SAME `$CG`, so `memory.peak` after a climb is the watermark across every attempt — exactly the
number a reservation wants. (Confirmed against the kernel: `memory.peak` is a lifetime watermark
unless explicitly reset via a write, which nothing here does.)

**THE BLOCKER, quoted from the file's own header:**

> *"Upstream fixes flow substrate → here by re-copying; **this file is not edited in place.**"*

`diff substrate/scripts/cgroup-scope paperkit/tools/cgroup-scope` — **251 → 367 lines, FOUR
paperkit-authored additions already present**: the UUID naming (a measured collision in 24,376
actions), the `pids.max` backstop, the OOM climb, and the vendoring banner itself.

⚑⚑ **THE RULE HAS ALREADY BEEN BROKEN FOUR TIMES, AND NOTHING RECORDS THAT.** The banner states a
one-way flow that the file's own contents refute. So the honest reading is not "I may not edit
this" but **"the stated vendoring discipline is not the one in force, and no one has said what
replaced it."** That is a Π-type with no inhabitant (rule 11): the banner is the TYPE
*"upstream owns this file"*; the four additions are evidence the argument was never supplied.

**Options, priced:**

1. **Add the peak write to `tools/cgroup-scope`** (~3 lines) and *also* correct the banner to
   state the real discipline (paperkit extends; substrate's 251-line core is re-copied under it).
   Cheapest code, but it edits a file whose header forbids editing — and the honest version of
   this option is a banner change, which is an ownership statement I cannot make.
2. **Push the fix UPSTREAM to substrate**, re-copy, re-apply the four paperkit additions. Honours
   the stated flow. But substrate's copy has no climb and no `$CG` reuse across attempts, so the
   peak semantics differ there — and the census found substrate's own `membudget` measures via
   `/usr/bin/time` maxRSS, not cgroup peak, so this fix has no upstream consumer.
3. **Stage a tool into `pk_calc`** as `pk_eval` does, and read the peak from inside the payload.
   No vendored file touched; costs a `tools =` dependency on every calc action (41,468 of them per
   the `Ζ·mem·def·blind` note) and puts a second peak-read path beside `cellcgroup`.

**Recommendation: (1), contingent on the operator settling the vendoring question.** It is three
lines at a site that already reads a sibling file in the same directory, and the banner it
contradicts is *already* contradicted four times over.

#### ⚑ Σ-F13b — A SECOND, INDEPENDENT DEFECT: THE LADDER CANNOT EXPRESS WHAT THE CLIMB CAN REACH

Measured, not inferred:

    mem_learn.py:24    LO, HI = 4, 4096      # and `if mb <= 0 or mb > HI: continue`
    calc.bzl:83        _RS = {4 … 4096}      # 12 buckets, top 4096
    cgroup-scope:360   CLIMB_MAX_MB:-8192    # the climb's ceiling

`HI` is **correct** relative to `_RS` — its comment says so, and it is not a stray error threshold.
The inconsistency is between **`_RS`'s ceiling (4096) and the climb's (8192)**: a cell that
legitimately needs 8192 MB has no expressible reservation, so its observation is discarded by
`mb > HI` as an un-isolated read, it falls back to the resolution default, and it OOM-climbs again
every run. **Non-convergence at the top bucket, structurally.**

⚑ This is live, not hypothetical: `Ζ·mem·ceiling` (`cgroup-scope:337-347`) records
`concept-views__config__flip_positionals_arm_2` climbing 4→4096 and being refused **twice**,
killing a full `//:hook` run each time — which is why the ceiling was raised to 8192. **The raise
fixed the climb and left the ladder behind.**

⚑ **CORRECTION TO MY OWN CENSUS READING (same tick).** A cross-repo census I ran this session
reported this as *"`mem_learn.py:85` discards observations > HI as instrument error"* — framing
`HI` as the bug. Reading the owning files says otherwise: `HI` tracks `_RS` faithfully; the gap is
`_RS` vs the climb. **The census's summary was directionally right and causally wrong**, and acting
on it would have raised `HI` while leaving `_RS` unable to schedule the bucket.

#### ⚑ Σ-F13c — `own_cgroup` HAS THREE INDEPENDENT IMPLEMENTATIONS IN THIS REPO

`reuse_check.py --propose tools/cellcgroup.py --against 'tools/*.py' 'paperkit/*.py'` (the wedge,
read as ∩+residues rather than a percentage — every row is OVERLAP with ∩ 8–14 against large
residues, i.e. the shared support is the `pathlib`+`try/except OSError`+`int()` file-read idiom,
NOT cgroup semantics). Reading the named neighbours directly:

- `tools/cellcgroup.py:29` `own_cgroup` — the authority, with the Σ-F12 docstring
- `tools/coord_sample.py:43` `_cgroup_current`
- `tools/cpuweight.py:64` `_cgroup_of`

Three readers of `/proc/self/cgroup`, one vocabulary. **Not this tick's work** — recorded so it is
not re-derived. The wedge verdict for the peak fix itself is *reuse the existing `write_peak`*, not
a new module: no new def is warranted anywhere in Σ-F13's option space.

#### What did NOT change

Nothing. This tick edited no file. The measurement stands: `bnd-delta`'s store row is 4.6 MB
against a demonstrated 128 MB need, and the OOM ladder remains load-bearing.

### ⚑⚑ Σ-F12 — THE OBSERVE CHANNEL MEASURES THE WRONG CGROUP (2026-09-10, tick 50)

**Σ-F11c said "the observe pass did not exercise the heavy path". That was too generous. The
channel is measuring the wrong thing entirely.**

**The discriminating measurement** — `bnd-delta`, the claim that climbed 8→16→32→64→**128 MB** in a
real build:

    store says          4.6 MB   (1 row, res=file, cell=bnd-delta__calc)
    the build needed  128 MB     — a 28× gap
    highest peak recorded across ALL 53 boundaries claims: 4.8 MB

⚑ **A systematic ceiling, not one missed path.** Fifty-three claims all reporting ≤4.8 MB while the
build demonstrably needs 128 MB for one of them is not sampling error.

**The cause, read from the two owners:**

- `calc.bzl:_peak_snippet` appends `P=$(cut -d: -f3 /proc/self/cgroup); cat /sys/fs/cgroup$P/memory.peak`
  — the cgroup of **the action's own shell**.
- `calc.bzl:_cap_prefix` runs the payload as `$PK_CAP <cmd>` where `PK_CAP` is
  `cgroup-scope <bucket> --`, which executes the work in a **CHILD scope** it creates per rung
  (`mb-14-…-<uuid>.scope`, visible in every OOM line).
- `cellcgroup.peak_bytes()` likewise reads `own_cgroup()`.

**So the reservation is learned from the SHELL's cgroup while the work runs in a CHILD's.** The
number is real — it is just a measurement of the wrong scope, and it cannot rise with the payload
because the payload was never charged to it.

⚑ **This subsumes Σ-F11c**: no number of observe→harvest→project iterations converges, because
every iteration re-measures the same wrong cgroup. The loop is not slow to converge; it is
converging on a different quantity.

⚑ **And it explains the seeded 256 being left in place.** `paper`/`library` have real ~215 MB
observations from the def grid (`pk_eval` cells, a different action shape); the file-resolution
channel has apparently never produced a large number for anyone. The four manifests I derived
(`file: 8`) are internally consistent and externally too low — which is why the OOM ladder is
load-bearing rather than vestigial.

**NOT FIXED — this is an owner call and a real design question.** Options, priced:
1. **Read the child scope's peak** — `cgroup-scope` knows the scope path it created; it could write
   the peak itself rather than leaving the shell to read its own. Correct, and localised to the two
   files that already own this vocabulary.
2. **Charge the payload to the action's own cgroup** (no child scope) — but the child scope is what
   makes `memory.max` a kill boundary rather than a reclaim threshold (the commit's own measured
   note about zram), so this trades the cap's soundness for the measurement's.
3. **Leave it and treat the ladder as the mechanism** — honest, but then `mem.json` is a
   cold-start hint, not a reservation, and `mem_converge.py`'s "converged" means less than it says.

⚑ **What is NOT in doubt**: the ladder rescues every under-reservation, so nothing is broken — this
is a measurement-fidelity finding, and the cost is the retries (173 in one `boundaries` build).

#### THE VERDICT: 26 of 27 GREEN, one FAILED — `@paperkit_render//:gate`

    Executed 4 of 27 tests: 3 pass, 1 fails locally, 23 skipped (cached)
    8,248 processes: 5,481 action-cache hits, 8,004 linux-sandbox
    13,722 / 152,899 actions

Nine reds inside that one gate, and they are **not one cause** — they separate cleanly:

#### ⚑⚑ Σ-F2 — `rnd-units` WAS MINE: RULE 8's REACH IS WIDER THAN I APPLIED IT (FIXED)

    paper-units.tsv ≠ segmentation — 65 committed units vs 66 projected;
    first divergence at unit 59: committed `gamma-is-reachable` / projected `genre-declared-runs`

The `genre-declared-gated` claim I added at tick 29. **Rule 8 says a bib edit is a PROJECTION
edit — and `paper.md` is not the only projection of that corpus.** `render/assets/paper-units.tsv`
is a SECOND one (the `talk`-genre segmentation), and I regenerated the first and not the second.
The other three units files were clean, which is the discriminating evidence that only `paper/`
drifted.

**Fixed**: regenerated, `65 → 66` units, and all four now read `≡ segmentation`. ⚑ Written by a
SCRIPT rather than the shell redirect `units.py --check` suggests — a redirect is composition the
toolchain refuses, and a program can refuse to truncate the asset when the projector emits nothing.

**⚑ Rule 8 amended in practice: after a bib edit, regenerate EVERY projection of that corpus, not
just `out`.** `units.py --check` is what makes the second one findable.

#### ⚑ Σ-F3 — `pikepdf` ABSENT IS REPORTED AS *fail* BY TWO CALLERS AND *cannot-run* BY TWO OTHERS

Same missing dependency, four claims, two different verdicts:

| claim | verdict | why |
|---|---|---|
| `rnd-link-alt`, `rnd-math-alt` | **cannot-run** ✅ | routed through `linkalt.main`'s guard |
| `rnd-a11y`, `rnd-pdf` | **fail** ⚑ | `AttributeError: 'NoneType' object has no attribute 'open'` |

`linkalt.py:34-37` sets `pikepdf = None` on ImportError with the comment *"pikepdf absent is
CANNOT-RUN (exit 3, **guarded in main**), not an uncaught ImportError read as a failure"* — the
intent is explicit and correct. But `describe_links` is called from **`a11y_own.py:73` and
`pdf.py:63`**, which never pass through `main`. Measured: **2 of 8 call sites are cross-module and
bypass the guard**; the other 4 are in-module and downstream of it.

⚑ **This is the tristate collapse the repo refuses everywhere else** (`Ζ·rests·unresolved`,
Α-F3's `cannot-run` verdict plumbing, Γ.2's `CannotGrade`): *"a missing toolchain"* and *"the claim
is false"* rendered identically. And Β-F4 graded `rnd-pdf` **broken** partly on this.

⚑ **CORRECTION to my own Β-F3 reading**: I attributed `render`'s reds to "document-conversion
toolchains". `rnd-widen` reported *"Pillow absent"* — but **`pillow 12.1.1` IS installed and
`widen_tables.py --selftest` PASSES on the host**. It fails only inside the sandbox, which stages
the engine and not the host site-packages. So "the environment lacks the library" was wrong for
Pillow; the sandbox boundary is the cause there, and genuine absence is the cause for pikepdf.
**Two different failures I had merged into one.**

~~**Owner's call, not a tick's**: guarding the two cross-module call sites changes what `render`'s
claims REPORT (fail → cannot-run), which is a change to what the gate guarantees.~~

### ⚑⚑ Σ-F3 — FIXED (tick 42). MY "OWNER'S CALL" WAS OVER-CAUTIOUS; THE TREE SETTLES IT.

**Re-examined and the deferral was wrong** — the same error as Ι-F1 (tick 22), where I priced three
options for a question the tree already answered. `Ζ·tier·exit` is not a preference, it is a
**named contract implemented across `render/`**:

- `linkalt.py:310` and `mathalt.py` both guard `pikepdf is None` in their own `main` → `return 3`.
- `pdf.py:main` **already had two `return 3` cannot-run exits**, one of them literally *"the
  route's toolchain is unavailable"*.
- `verb.bzl:160` implements the mapping: `if [ "$rc" = 3 ]; then V=cannot-run` — its comment names
  this exact case, *"the render checks return 3"*.

So this was an **omission in 2 of 4 consumers**, not a policy question. `a11y_own.main` had NO
toolchain guard at all; `pdf.main` had two for other tools and none for pikepdf.

**Fixed at the ENTRY POINTS, not in `describe_links`** — deliberately: guarding the callee would
make it return a sentinel its four in-module callers must each re-interpret, while guarding `main`
keeps ONE owner for the verdict, which is why `linkalt`/`mathalt` do it there.

**Measured — the gate's own words changed:**

    before:  RED  rnd-a11y: {"verdict":"fail", … AttributeError: 'NoneType' has no attribute 'open'}
             RED  rnd-pdf:  {"verdict":"fail", … AttributeError …}
    after:   check UNRESOLVABLE for [@rnd-a11y] … NOT a refutation
             check UNRESOLVABLE for [@rnd-pdf]  … NOT a refutation

**8/8 discrimination** (`scratchpad/test_tier_exit.py`): all four pikepdf consumers now exit **3**
and AGREE (`{linkalt: 3, mathalt: 3, pdf: 3, a11y_own: 3}`); both guards test the real import
rather than a flag; `verb.bzl`'s rc-3 mapping verified rather than asserted.

⚑ **AND IT CASCADED INTO THE CONFORMANCE DISCLOSURE.** `rnd-wcag`/`rnd-wcag-entail` previously
read *"rnd-a11y: its veraPDF validator (consumed record) FAILS — cannot back a Supports"*. They now
read *"some SCs disclose **Not Evaluated**, not Supports (conservative)"*. **A false `fail` was
propagating into what the VPAT claims about accessibility** — the collapse was not cosmetic.

~~**Remaining `render` reds are environmental, all pre-existing**: `rnd-latex` (pikepdf, via a direct
`import` rather than the guarded path)~~ — ⚑ **`rnd-latex` was NOT merely environmental; it was the
SAME omission one file further. Fixed at tick 43, see Σ-F4.**

### ⚑ Σ-F4 — THE GUARD EXISTED AND A BRANCH JUMPED OVER IT (2026-09-10, tick 43)

**Σ-F3's census was incomplete, and the reason is instructive**: I enumerated callers of
`describe_links` and found four. The real population is **pikepdf IMPORTERS** — and
`--binding pikepdf` finds three more, all **function-local** imports invisible to a caller search:
`latex._selftest:170`, `pdf._formula_alts:89`, `pdf._link_count:115`.

`pdf.py`'s two were already covered (tick 42's entry guard returns 3 before reaching them).
`latex.py` was not — and its shape is sharper than Σ-F3's:

    def main(argv):
        if argv and argv[0] == "--selftest":
            return _selftest()          # ← the ONLY path that imports pikepdf directly
        absent = _deps_absent()         # ← the Ζ·tier·exit guard, ALREADY HERE
        if absent: return 3

**The guard already existed. `--selftest` branched above it.** So the one path needing the roster
was the one path that never consulted it, and `ModuleNotFoundError` propagated as a FAIL.

**Two gaps, both fixed:**
1. **The roster did not know the dependency.** `_deps_absent` checked lualatex, pandoc, two `.sty`
   files and veraPDF — not pikepdf. ⚑ *A dependency missing from the roster is a dependency whose
   absence lies*, because the roster is precisely what separates "the toolchain is not here" from
   "the claim is false".
2. **The branch order.** The guard now runs first, for both paths. ⚑ And the selftest is exactly
   the thing that must not "pass" without its tools: it is a ⟨P,F,δ⟩ proof of the METHOD, so a
   selftest green without the method's tools is the `vacuous` grade this repo refuses.

**Measured — `render`'s gate, before → after:**

| claim | tick 41 | tick 42 | tick 43 |
|---|---|---|---|
| `rnd-a11y`, `rnd-pdf` | fail | **cannot-run** | cannot-run |
| `rnd-latex` | fail | fail | **cannot-run** |
| `rnd-a11y-latex` | *masked* | *masked* | **cannot-run** (surfaced) |
| `rnd-wcag`, `rnd-wcag-entail` | fail | Not Evaluated | Not Evaluated |

⚑ **`rnd-a11y-latex` was hidden behind `rnd-latex`'s crash** — a sixth consumer that only became
visible once the fifth stopped throwing.

**`rnd-bib` is NOT a defect, verified**: `PYTHONPATH=<repo> python3 checks/bib.py` →
*"bib ok: warrants inline (machine-checked)…"*. My standalone invocation lacked it; Bazel supplies
it. ⚑ Note `PAPERKIT_PYTHONPATH` alone does NOT work — the engine's runner reads it and sets
`sys.path`; the bare script does not.

~~**One genuine red remains in `render`**: `rnd-widen`, the sandbox-vs-host site-packages case
(Pillow IS installed and `widen_tables.py --selftest` PASSES on the host).~~ — ⚑ **WRONG on the
cause. `rnd-widen` is the SAME omission at a fourth site; fixed at tick 44, see Σ-F5.**

### ⚑⚑ Σ-F5 — TWO MORE SITES, AND ONE IS THE WORST SHAPE YET (2026-09-10, tick 44)

#### (a) `arch/` — my own project's `out` was never staged

`bazel test //:hook` → **`@paperkit_arch//:gate` FAILED**, all six claims RED with ONE root cause:

    RED  invariants: "paperkit-gate: ARCH.md not built — run paperkit-project"

`ARCH.md` exists on disk and the gate passes on the HOST; it is simply absent from
`//arch:files`, so the sandbox never sees it. **Μ-F1's lesson, recorded at tick 30 and repeated by
me at tick 38.** Fixed by listing it.

⚑ `talk/BUILD.bazel` draws the distinction I needed and its comment states it: the `out` document
**is** listed (it is what `≡ projection` compares against), while FURTHER-derived artifacts
(`talk.odp`, `talk.pptx`) are not — *"listing a deliverable as a source input would make the
artifact an input to its own gate."*

⚑ **`Executed 3 of 16 tests` was NOT a shrunken graph** — the log also says `Analyzing: 27
targets`. Bazel **aborted at the first failure**; 16 is how far it got. Re-run with `--keep_going`
to get the full verdict, which is why the two numbers disagreed.

#### (b) `rnd-widen` — the guard existed, the claim's paths jumped over it, ⚑ AND IT LIED

`_deps_absent()` exists at `widen_tables.py:265` and knows about Pillow. But `main` branches on
`--selftest` and `--deliverable` **before** calling it — the identical structure Σ-F4 found in
`latex.py`, now at a fourth site.

⚑⚑ **AND THIS SHAPE IS WORSE THAN AN UNGUARDED IMPORT.** Read the tick-41 account:

    "-- Pillow absent; the measurement cannot run here."
    "WIDEN SELFTEST: SKIP (loud) — the method is present but unrunnable on this box"
    "widen_tables: DELIVERABLE unmeasurable — render deps absent — nothing to grade"
    …  {"verdict":"fail"}

**Both halves DETECTED the absence, announced it correctly, and then returned a failing exit code
anyway.** `latex.py` at least crashed visibly. Here the honest account and the dishonest verdict
shipped in the same record — the evidence for the right reading was already printed beside the
wrong one. That is `Ζ·rests·unresolved`'s collapse with the correction sitting in the same JSON.

**Fixed**: the guard now runs first for both claim-invoked flags (the copy-through path keeps its
own, which correctly returns 0). Verified the guard does NOT fire where the deps exist —
`--selftest` still **PASSES** on the host with real measurements.

⚑ **CORRECTION to Σ-F3's note**: I recorded `rnd-widen` as "sandbox stages the engine, not host
site-packages". Measured: `--deliverable` on the host reports real numbers (5956 twips, 3 columns),
so the host has the toolchain — but the failure was never about *where* the deps are. It was the
verdict, and I had quoted the selftest's message while reasoning about a different one.

### ⚑⚑ Σ-F6 — ⛔ `arch/` IS BLOCKED ON A DESIGN QUESTION I CANNOT SETTLE (2026-09-10, tick 44)

**Progress**: staging `ARCH.md` fixed `invariants` (**PASS — `ARCH.md ≡ projection`, `--without-K`
6 distinct**), and declaring `reads` took **4 of 6 claims GREEN**. `reads = {.}` is the mechanism —
`boundaries/` uses it on 26 of 54 entries for exactly this (its witnesses read engine sources).

**Two claims remain RED, both `baseline: false, sens: []`** — they fail in the sandbox even
UNMUTATED, which is the `broken`/`vacuous` shape, not a mutation result.

⚑ **THE CAUSE IS THE CLAIMS, NOT THE STAGING.** Both assert facts about **the whole repository**
from inside a sandbox that stages a subset:

| claim | asserts | why no `reads` fixes it |
|---|---|---|
| `arch-projects` | every wired project's dir carries a `paper.toml` | the sandbox stages `arch`+root+`report`; the other ten dirs are absent BY DESIGN |
| `arch-report-scope` | `report/gen.py`'s census covers ≥11 documents | `_all_docs()` walks the real tree; in the sandbox it finds what is staged |

⚑ **My first repair of `arch-projects` was itself unverifiable and I replaced it**: it `rglob`ed
for every `paper.toml` and asserted `on_disk > wired` (fixtures/starters are unwired projects).
True on the host; in the sandbox `on_disk` can never exceed `wired`, so **the check could not pass
where it runs** — no `reads` declaration helps, because the missing files are precisely the ones
deliberately not staged. Rewritten to assert the DECLARATIONS, and the claim's prose corrected to
match (`bibstruct --set`, 6 entries round-trip). It still reds, for the narrower reason above.

**Three options, priced, for the owner:**
1. **`reads` every wired project** (`. , boundaries, config, demo, guide, image, paper, …`) —
   makes both verifiable, but stages ~the whole repo per cell and inflates every `arch` Δ mutation
   sweep. It also makes `arch`'s footprint the union of all projects, which defeats the footprint
   audit's purpose.
2. **Declare the two `mechanical = false`** — `bib.py:460`'s honest use, *gated but not graded*.
   They become prose-with-a-gate rather than mutation-graded claims. ⚑ Cheapest and arguably
   correct: *"the repository has N projects"* is a fact about the CHECKOUT, and a hermetic sandbox
   is by construction not the checkout.
3. **Retier `arch` to `local`** — the whole project gated-but-not-graded, like `report`/`image`.
   Heaviest; loses Δ on the four claims that DO work hermetically.

⚑ **I lean (2), but it changes what the gate guarantees for two claims, so it is an owner call.**
The four hermetic claims (`arch-components`, `arch-modules`, `arch-two-pk-grade`, `arch-two-tiers`)
are unaffected under every option.

### ⚑⚑ Ρ — bnd-env-facts: THE LEDGER'S OWN ENVIRONMENT BLOCK WAS 4/5 STALE (2026-09-10, tick 40)

**This file — the one every tick reads FIRST, before measuring anything — carried four stale facts
out of five checkable ones.** Measured with `scratchpad/probe_ledger_env.py`:

| the prose said | the tree says |
|---|---|
| "all **NINE** hook-set projects declare a root" | **TEN** declare one; MODULE.bazel wires **13** |
| "`discriminate --json paper` … **110 claims**" | **115** entries across 12 bibs |
| "`gen.py --check delta.md` … **exceeds 600s**" | exceeds **2700s**, and NOT over nine projects — `render` alone (Β-F3) |
| "**~61s**" as the sweep cost | that is a **COLD** sweep; a warm one is **~0.1s** — a ~600× gap |
| "setup/report/image deliberately undeclared" | ✅ still true |

⚑ **The third entry was stale in TWO ways at once** — wrong magnitude AND wrong attribution. I had
already corrected the magnitude in Β-F3 and left the environment block quoting the old figure, so
the ledger contradicted its own findings section.

**Corrected inline, originals struck through per rule 6.** But prose corrected by hand goes stale
again — so the three figures with a single owner are now **GATED**.

#### `bnd-env-facts` — the figures, not the sentences

`paperkit/tests/boundaries_env_facts.py` + `bnd-env-facts` (**54 entries, round-trips**). It
re-derives wired projects (MODULE.bazel), root-declaring projects (each `paper.toml`), and bib
entries (the warrants list), and asserts the Environment block quotes them correctly.

⚑ **It does NOT pin the numbers.** A count that must never change is a different and usually wrong
claim. When a project is added the gate reds, the prose is corrected, and it goes green — **the red
is the notification, not the verdict.**

⚑ **It gates the FIGURES, not the PROSE.** The ledger is a working log, not a projection;
claim-ifying 3,659 lines of narrative would repeat Λ-F1's error (316 words measured against 27 KB).
⚑ And it scans **only the Environment block** — the tick log is append-only history whose old rows
are SUPPOSED to record what was true then (rule 6). **A stale FACT and a dated RECORD are different
things**, and a witness that confused them would red on correct history.

**Verified by discrimination, 6/6**: each of the three figures drifting REDS with the true cause
named, and ⚑ **deleting the sentence rather than correcting it also REDS** — so a figure cannot be
silently un-gated.

⚑ **My own instrument failed once first**: the wired-project pattern required `wires 13 projects`
adjacent, but markdown **wraps**, so it reported the statement MISSING — accusing the prose of a
defect that was the pattern's blind spot. Μ-F3's shape, third occurrence. Fixed with `\s+`.

**Regression**: `BOUNDARIES.md` **4560 words ≡ projection** (rule 8) · suite PASS (3 figures,
1 delta) · new suite placed in `components.bzl`.

### Μ — bnd-generator: AUDIT FINDING 1 CLOSED, WITHOUT THE PROJECT (2026-09-10, tick 39)

**`paperkit/tests/boundaries_generator.py` + `bnd-generator`** (`bibstruct --add --apply`;
**53 entries, round-trips**). Audit finding 1's substance: `bibtex.bzl` (1,109 lines) + `calc.bzl`
(730) ARE the build graph, and `bnd-lint` — their only prior claim — is **three regexes, all shell
hygiene** (`bare-python3`, `printf-json`, `grep-json`), read from source. None asserts what the
generator EMITS.

**Three declaration→target rules now gated, over 13 projects:**

| rule | measured |
|---|---|
| `adequacy = True` ⇒ `:adequacy` record | guarded by `adequacy`; **10 of 13** declare it |
| `emerge = True` ⇒ `:cohere` record | guarded by `emerge`; **3 of 13** declare it |
| every project ⇒ `:invariants`, `--without-K`, ANY tier | unguarded, command carries the flag |

⚑ **The third is the one that needed gating.** Α wired `report`/`image` on exactly this argument —
*"`:invariants` is emitted for EVERY project regardless of tier, so wiring buys `--without-K` even
at `local`"* — and nothing checked it. A tier guard would silently strip the only cross-claim
invariant from both.

#### ⚑⚑ Μ-F3 — THE WITNESS ACCUSED THE GENERATOR **TWICE** AND WAS WRONG BOTH TIMES

**Neither was a defect in `bibtex.bzl`. Both were my instrument, and both are recorded because a
false accusation from a boundary suite is worse than no suite.**

1. **A 14-line scan window.** Reported `adequacy_rec` UNGUARDED — its guard sits **47 lines** above
   (`:992` guarding `:1039`). A window is a guess about DISTANCE; enclosure is a fact about
   INDENT. Rewritten to walk outward by indentation.
2. **One spelling taken for the concept.** Reported `cohere_rec` UNGUARDED because its guard reads
   `if emerge and (…)` — a LOCAL bound from the attribute, not `repository_ctx.attr.emerge`.
   ⚑ **Β-F1's shape exactly**, one file over: `@paperkit_X` ⇒ project `X` held for 11 of 12
   projects and silently failed for the twelfth.

#### ⚑ Μ-F4 — AND THE DISCRIMINATION PROBE CAUGHT TWO MORE, AT 5/6

Passing after two false alarms is not evidence — it may just have stopped complaining. Mutating
`bibtex.bzl` found:

- **`"--without-K" in bzl` was too weak**: the string occurs **twice**, so removing it from the
  invariants command left the check green. Now reads the `inv = ` assignment that BUILDS the
  command — the file is not the command.
- **A right verdict with the wrong cause**: injecting `if proj_tier == "sandbox":` around
  `:invariants` was CAUGHT, but reported the guard as **`emerge`** — the scanner walked past an
  unrecognised guard into an outer block. Now the nearest enclosing `if` is the answer whatever it
  tests, so the diagnostic names `proj_tier`.

**After: 6/6** — tier-guarding `:invariants`, dropping `--without-K`, and unguarding either record
each RED with a diagnostic naming the true cause; restored cleanly each time.

**Verified**: suite PASS (3 rules, 13 projects, 1 delta) · discrimination **6/6** ·
`bibstruct --add` 53 entries round-trip · `BOUNDARIES.md` **4453 words ≡ projection** (rule 8) ·
`bnd-components` **85 files, no new drift** (new suite placed in `components.bzl`).

⚑ **Μ-F2 unchanged** — `dag.bzl` still the owner's one command.

### Λ — arch: THE COUNTS ARE WITNESSES NOW (2026-09-10, tick 38)

**New project `arch/`, wired, gated, in `//:hook`.** `paperkit-gate arch` → **PASS, 6 claims**;
`hook_grid` → **13 projects, 29 targets, grid matches**; `bnd-check` PASS with `paperkit_arch` in
the graded set.

Audit finding 2's three false assertions are now claims that **count from the manifest that owns
the count**: components ← `components.bzl`, modules ← the same partition's non-test files,
projects ← `MODULE.bazel`'s `bib.project` tags.

⚑ **`arch-components` and `arch-modules` are SEPARATE claims on purpose.** "Eight" was the
COMPONENT count and the prose said "eight projects" — so a bare refresh from 8 to 12 would have
preserved the category error while looking correct. Each claim names which count it asserts.

#### ⚑⚑ Λ-F1 — THE PLAN SAID "CONVERT ARCHITECTURE.md TO A PROJECTION". MEASURED, THAT DELETES IT.

Projecting these six claims yields **316 words**. The authored document is **27 KB**. A projector
emits exactly what its claims say, so pointing `out` at `../ARCHITECTURE.md` destroys ~98% of it —
narrative, module tables, rationale, none of it claim-shaped.

⚑ **AND I LEARNED THIS BY DOING IT.** `--check` had already reported the difference; I ran the
WRITER "to measure" and it overwrote the document. Restored with `git checkout` (27 KB intact,
`git status` clean). **The writer is destructive by design and `--check` answers the same question
without the damage.** My own error, recorded rather than smoothed over.

**Resolution**: `out = "ARCH.md"` — the project gets its own document. ARCHITECTURE.md keeps its
prose and **gains gated counts beside it**. Whether the narrative should ever be claim-ified is an
owner's call.

#### ⚑ Λ-F2 — §3.6's TENSIONS: 2 of 4 ARE ALREADY FALSE, AND NOTHING SAID SO

The plan called §3.6 "not claim-shaped, preserve as authored prose". Read and checked, it is
**mixed**:

| bullet | status |
|---|---|
| `discriminate.py` is a facade god-CLI | a JUDGEMENT — genuinely not claim-shaped |
| two `pk_grade` rules | ⚑ **still TRUE** — `grade.bzl:61`, `calc.bzl:722` |
| report covers only paper/README/boundaries | ⚑ **FALSE** — Β made the census 11 documents |
| render/image/report are on-demand | ⚑ **FALSE** — `_ondemand_names()` is **EMPTY** |

**Two entries went stale silently, which is precisely what claims exist to prevent.** So the
retirements are GATED, not narrated: `arch-report-scope` and `arch-two-tiers` assert the CORRECTED
state and go red if either tension returns. A tensions ledger nothing re-derives is
`fresh-comments-are-hypotheses-too` at document scale.

#### ⚑ Λ-F3 — THE COUNTING WITNESS EARNED ITS PLACE INSIDE ITS OWN TICK

`arch-projects` was authored asserting **12** wired projects. Wiring `arch/` itself made it **13**,
and the witness **caught it before the gate did**. A prose count would have shipped stale on the
day it was written. The claim now records that.

⚑ Two other gates fired the same way and both are the machinery working: `arch-two-tiers` failed
first because `arch/` existed on disk unwired (so `_ondemand_names()` reported it), and
`hook_grid` caught **both** `@paperkit_arch` members missing from `//:hook` — the **third recorded
instance** of the class `BUILD.bazel:114-119` already documents for `boundaries`.

**Verified**: `bibstruct --roundtrip arch/warrants.bib` → **0 of 6 unparsed** · all 6 witnesses
pass standalone · `gate arch` PASS · `hook_grid` 13/29 · `bnd-check` PASS (7 behaviors, 1 delta) ·
`ARCHITECTURE.md` **unmodified** (`git status` clean).

### Β — doc-identity: A2-F2 CLOSED, AND IT WAS WORSE THAN RECORDED (2026-09-10, tick 35)

**A2-F2 reproduced exactly** before any edit: `_all_docs()` reported **12 documents, two named
`library`** — `paperkit/library` (live) and `build/lib/paperkit/library` (a gitignored stale wheel
copy).

#### ⚑⚑ Β-F1 — THE COLLISION WAS THE VISIBLE HALF. THE REPORT'S TABLES DISAGREED ABOUT ONE DOCUMENT.

A2-F2 recorded a duplicate row. Measuring the consumers found a **three-way inconsistency**, each
component naming the same document differently:

| function | source | yields |
|---|---|---|
| `_all_docs()` | `d.name` (last path segment) | `library` ×2 |
| `_wired_names()` | MODULE.bazel `project=` | **`paperkit/library`** |
| `_hook_names()` | BUILD.bazel `@paperkit_(\w+)` | `library` |

So `_wired_names()` produced a name `_all_docs()` could **never** match, and the consequences were
both real and opposite:
- **`_ondemand_names()` = `{library}`** — the concept library was reported as an unwired,
  non-reproducible document. It is `emerge = True`, adequacy-graded, and in `//:hook`.
- **`_graded()` listed `library` TWICE** — the live project and the wheel artifact, both matching
  the hook name.

⚑ **One document simultaneously "not gated by CI" and "graded twice".** The name truncation did
not merely duplicate a row; it made the report's own tables contradict each other, and nothing
could say so because every table read the same broken key.

**The fix keys on the REPO-RELATIVE PATH — the identity MODULE.bazel already uses.**
- `_all_docs()` returns `rel` instead of `d.name`.
- `_hook_names()` reads the **repo→project map out of MODULE.bazel** rather than assuming
  `@paperkit_X` ⇒ project `X`. That identity held for 11 of 12 projects and diverged silently for
  the twelfth — the shape `Ζ·hook-rot` keeps producing.
- `_ignored()` consults **`git check-ignore`**, the authority that reads every `.gitignore`,
  global excludes and negations. A hand-rolled matcher would be a second, drifting reading of the
  same rules. ⚑ If git is unavailable it **falls back to walking everything and SAYS SO** — an
  unverifiable exclusion is not applied silently.

**Measured after**: 11 documents, no duplicate, `build/` excluded, `paperkit/library` matching the
hook, **`_ondemand_names()` now EMPTY** (was `{library}`), `_graded()` 9 rows each once.
`distinct.py` → *"--without-K clean across 9 document(s): … paperkit/library …"* where A2-F2
reported ten with two named `library`.

**Verified by discrimination, 7/7** (`scratchpad/test_doc_identity.py`), including the COLLISION
CLASS rather than today's instance: a fresh top-level `graph/render` beside `render` yields
`['graph/render', 'render']` — the exact shape Phase D's `arch/`/`graph/` will create, so Λ and Μ
are unblocked from this hazard rather than merely patched around it.

⚑ **Case 6 first FAILED and my TEST was wrong, not the fix.** The probe placed the colliding
project at `demo/render`, nested inside an existing project — where the nested-fixture filter
correctly excludes it, proving nothing. Moved to a top-level tree.

**Regression**: `hook_grid.py` green (12 projects, 27 targets) · `grounding.py` 111 claims,
acyclic · `gen.py --check gate.md` **RED, as designed** — the committed asset says `library` where
the census now says `paperkit/library`.

#### ⚑ Β-F2 — REGENERATING `gate.md` EXCEEDS 900s. ⚑⚑ AND MY FIRST EXPLANATION WAS WRONG.

`gen.py gate.md` hit `timeout 900` with **no output** (exit 124).

**I attributed it to Β and to the gates, and MEASURED OTHERWISE.** The reasoning was: Β emptied
`_ondemand_names()`, so a previously-skipped document is now gated; `_gate_once` allows 300s per
project × 11 documents. Plausible, and false.

**Measured** (`scratchpad/probe_gate_cost.py`, every document timed separately):

    paper 3.2s · README 3.5s · boundaries 6.4s · config 0.2s · demo 0.2s · guide 0.6s
    image 15.3s · paperkit/library 1.2s · render 43.2s · setup 0.3s · talk 5.4s
    total 80s sequential; documents over 120s: NONE

**80 seconds for every gate.** No document is slow, so the gates are not the cost and Β's change to
`_ondemand_names()` is not the cause.

**The real cause, read from `main()`**: the write path **ignores the asset name**.
`produced = {name: g() for name, g in GENERATORS.items()}` — Γ.2's generate-all-then-write means
`gen.py gate.md` generates **all four assets**, including the two that call `_delta`, which runs a
mutation sweep per project (~61s each, warm, per the environment note). The 900s belongs to Δ, not
to the gates.

⚑ **Fourth wrong performance diagnosis on this thread, and the same shape each time**: reasoning
from what the code *should* cost instead of timing it. The probe cost 80 seconds and refuted a
paragraph of arithmetic.

⚑ **Γ.2's generate-all-then-write HELD, verified**: `git status report/assets/` is **clean** after
the timeout — no asset overwritten with a partial rendering. First real exercise of the guard, and
it is also *why* the run is expensive: the same design that protects the assets forbids generating
one cheaply. That trade is deliberate and worth stating, not a defect.

**Still open**: the ledger's *">600s"* note is stale — the true figure is >900s, and a single-asset
regeneration is not available by design.

#### ⚑⚑ Β-F3 — >2700s, AND MY SECOND ESTIMATE WAS WRONG TOO (2026-09-10, tick 37)

`report/gen.py` under a **2700s** budget with `-u`: **exit 124, zero bytes**.

**Both of my cost models are now refuted by measurement:**

| tick | estimate | refuted by |
|---|---|---|
| 35 | "300s × 11 gates" | every gate timed: **80s total**, none over 120s |
| 36 | "~61s × 9 projects ⇒ ≥10 min" | 9 × 61 = 549s, which **fits inside 2700s** — it did not finish |

⚑ **`-u` also refuted my BUFFERING explanation.** Zero bytes unbuffered means `gen.py` genuinely
emits nothing until it finishes: every generator runs before any write or `print`, so silence is
the design, not a stdio artifact. The diagnostic loss I blamed on buffering was structural.

⚑ The environment note's *"~61s"* is `discriminate --json paper` **with a warm footprint cache**.
`_delta` runs per graded project and **nothing has ever measured the other eight**. Assuming
`paper`'s figure generalised is the same error as assuming `@paperkit_X` ⇒ project `X` (Β-F1):
a value true for one member of a set, taken for the set.

**Fourth performance question on this thread; the first three were answered by guessing and all
three were wrong.**

**MEASURED — `_delta` is ~0.1s per project, and Δ IS NOT THE COST AT ALL:**

    paper 0.1s (111 claims) · README 0.1s (24) · boundaries 0.1s (52) · config 0.1s (4)
    demo 0.1s (1) · guide 0.1s (9) · paperkit/library 0.1s (43)   [render, talk pending]

Seven of nine graded projects return in a tenth of a second with the footprint cache warm. So the
tick-36 model — *"Δ sweeps are the ≥10 minutes"* — is wrong in the OPPOSITE direction from
tick 35's: I over-estimated Δ as badly as I had over-estimated the gates.

**COMPLETED — `render` IS THE ENTIRE COST, and it is ONE project, not a slow pipeline:**

    paper 0.1 · README 0.1 · boundaries 0.1 · config 0.1 · demo 0.1 · guide 0.1
    paperkit/library 0.1 · talk 17.7   →  eight projects total ~18s
    render 240.1  ⚑ EXCEEDS THE CAP — did not finish

⚑ **AND THE 0.1s FIGURES ARE CACHE HITS, NOT SPEED.** Running `discriminate.py` on the root prints
*"all 24 grade(s) reused from footprint cache"* — so the eight fast projects are REUSING grades,
and `render`'s 240s+ means its footprint cache is **cold or invalid**. The environment note's
"~61s" is what a COLD sweep of `paper` costs; the 0.1s is what a warm one costs. Two different
measurements of two different things, and I had been quoting one for the other.

⚑ **Why `render` is the expensive one is structural, and visible in its own bib**: 34 checks
(`--field check` → 34 of 34), of which `docx.py`, `pdf.py`, `ocr.py`, `odf.py`, `latex.py`,
`omml.py` shell **document-conversion toolchains** (pandoc / LibreOffice / OCR). Δ re-runs each
check per mutation site, so `render`'s sweep is 34 toolchain-invoking checks × sites — a different
order of magnitude from a project whose checks are pure Python.

**⚑⚑ AND IT IS NOT EVEN `render` — IT IS ONE CLAIM.** The full progress trace:

    7/34 @ 3s · 10 @ 8s · 16 @ 12s · 20 @ 18s · 29 @ 21s · 30 @ 35s
    31 @ 136s · 32 @ 150s · 33 @ 164s · then >116s on the LAST claim, unfinished

⚑ **My "~3 claims" reading was ALSO wrong, and the completed trace refuted it**: 31→32 and 32→33
each took **14s**, not 100s. The true shape is 30 claims in 35s, three more in ~130s, and **one
claim that alone exceeds 116s**.

**Named by measurement, not inferred** (`discriminate.py --json --only <claim> render`):

| claim | seconds | grade |
|---|---|---|
| **`rnd-ocr`** | **98** | behavioral |
| `rnd-pdf` | 5 | ⚑ **broken** |
| `rnd-docx` | 5 | behavioral |

⚑ **The TOOLCHAIN hypothesis is refuted.** I predicted `docx`/`pdf`/`ocr`/`odf`/`latex`/`omml`
would all be expensive because they shell document converters. `pdf` and `docx` are **5s each**.
The cost is not the class — it is **OCR specifically**, one claim, ~98s.

#### ⚑ Β-F4 — `rnd-pdf` GRADES `broken`, AND Γ IS WHAT MADE IT VISIBLE

`rnd-pdf` → **`broken`**: it does not pass in a pristine sandbox. Attributed rather than assumed
(rule 9): the only uncommitted change under `render/` is **Γ.1's `root = ".."` declaration**
(tick 2), which is what made `render` Δ-gradable *at all*. Before it, `layout._sandbox_root`
refused and the project could not be swept.

**So the grade is not newly broken — it was previously UNMEASURABLE.** Γ.1 did not break
`rnd-pdf`; it revealed a claim that had never been graded. That is Γ's purpose working as designed,
and it is a real finding needing an owner: a `broken` claim in a project inside `//:hook`.

**So the report cannot regenerate here without a warm `render` cache, and that is a fact about the
INSTRUMENT, not about drift in the assets.** `rpt-reproducible` is the claim that would own it.

⚑ **The actionable shape is now ONE claim, not a class**: `rnd-ocr` costs ~98s of the sweep. The
question is whether its Δ grade is worth that, or whether it belongs at a non-sandbox `tier`
(**gated but not graded** — the `Ζ·tier` mechanism `image`/`report`/`setup` already use for
exactly this reason). ⚑ Note `render/paper.toml` ALREADY carries a `Ζ·tier` comment for its
"PURE compliance warrants", so the mechanism is in use in this very project — `rnd-ocr` simply is
not among them. **Owner's decision, not a tick's call**; retiering someone's claim changes what the
gate guarantees.

⚑ **And `rnd-pdf`'s `broken` grade (Β-F4) is the more urgent of the two** — a cost is an
inconvenience, an unpassing claim inside `//:hook` is a correctness gap.

⚑ **Γ.2 held a SECOND time** — `report/assets/` clean after a 45-minute kill.

### Ξ.2 — `bnd-genre-census`: THE APPARATUS'S THESIS, MADE CHECKABLE (2026-09-10, tick 34)

**`boundaries_genre_census.py` + `bnd-genre-census`** (`bibstruct --add --apply`; **52 entries,
round-trips**). The design says *"each publication genre is its own vantage"* and *"disagreement
between vantages is DATA"* — **empty if two genres produce the same partition.** That is not
hypothetical: it is what `brief` was for one tick (Ν-F1).

**Measured — every genre is a distinct vantage, 36 of 36 pairs:**

| | staged | atomic | collection | talk | brief | serial | quickref | catalog | tutorial |
|---|---|---|---|---|---|---|---|---|---|
| units | 11 | 115 | 11 | 66 | 15 | 12 | 3 | 23 | 13 |

Pairwise disagreement (fraction of claim-PAIRS read differently) ranges **0.019 – 0.394**.
`tutorial` and `quickref` are the most independent readings (0.25–0.39 from everything) — they cut
on grounding depth and text length, axes nothing else uses. `atomic`/`talk` are near-twins (0.019).

⚑ **The measure is over PAIRS, not unit counts** — `staged` and `collection` both give 11 units and
disagree on 8.8% of pairs. A count would have called them identical.

⚑ **No claim is foregrounded by every vantage.** 8 of 9 open with `paper-is-projection`; `catalog`
opens with `min-strength`, purely because "M" sorts where it does. The absence of a fixed point is
the honest result — the vantages do not agree on where the corpus starts.

#### ⚑⚑ Ξ-F4 — THE CENSUS CAUGHT THE LEDGER CARRYING A FACT ITS OWN REPAIR HAD INVALIDATED

Ν-F1 recorded `brief ≡ staged` **"at every γ"**. The census's stale-exemption check RED-ed
immediately: they now differ by **0.051**.

**Both readings were true when made.** Ν-F1 measured them at a time when γ was UNREACHABLE — 
`bib._misplaced_paper_key` refused `gamma` under `[genres.*]`, so every genre ran at the project
default (Ι-F1). **Ι-F1 fixed that**, `brief` declares `gamma = 4.0`, and the two now differ at
their own resolutions while remaining identical at the same one. Verified directly:
`--observe --genre staged --gamma 4.0 paper` → **15 units, identical to `brief`**.

So the equivalence is `brief ≡ staged@γ=4.0`, **not** `staged` simpliciter. A repair three ticks
back silently invalidated a recorded finding, and only a machine re-derivation noticed.

#### ⚑⚑ Ξ-F5 — I WROTE AN UNFALSIFIABLE CHECK IN THE FIX FOR AN UNFALSIFIABLE CHECK

Having γ-qualified the exemption, I added a "stale exemption" guard comparing `brief` and `staged`
at the declared γ. The discrimination probe scored **4/5**: that case could not fail.

An explicit γ **overrides both genres' declarations**, so the two are compared on the same grouping
— and both are the identity on it. The equivalence is **ANALYTIC**: it cannot break. One tick after
Ξ-F3 caught exactly this shape, I reproduced it inside the repair.

**Fixed by stating what it is** rather than testing a tautology: the suite now reports the
equivalence as analytic and points at the pairwise scan, where `brief` vs `staged` IS a live
comparison at their own γ. After: **5/5**, and case 3 asserts the true fact (changing brief's γ
keeps the census green *because* the equivalence is analytic).

**Verified**: `bnd-genre-census` PASS (9 genres, all distinct, 1 declared coincidence) ·
discrimination **5/5** — a new genre duplicating `brief` REDS, a genuinely distinct one passes ·
`BOUNDARIES.md` **4374 words ≡ projection** (rule 8) · `bnd-components` **84 files, no new drift** ·
`grades.py` 111 claims, behavioral=82, unchanged (rule 9).

⚑ **Μ-F2 unchanged** — `dag.bzl` still needs the owner's one command.

### Ξ.1 — `bnd-genre-pure`: A BLOCKED VERDICT MADE FALSIFIABLE (2026-09-10, tick 33)

**Phase F's actual deliverable, for the one surviving obstacle.** `boundaries_genre_pure.py` +
`bnd-genre-pure` (via `bibstruct --add --apply`; **51 entries, round-trips**).

**Why a BLOCKED verdict needs a witness**: of the three obstacle keys, **two were false** —
`PK-GENRE-BLIND` retired by Κ, `PK-BIB-PROVENANCE` never true at all (Ξ-F1). Both survived because
a verdict living in prose is re-read, never re-derived. `PK-GENRE-PURE` now **goes RED the day the
obstacle is removed**, and its own diagnostic says to DELETE it and build troubleshooting rather
than relax it.

**Two independent halves**, because either alone is weak:
1. **no verdict is EXPRESSIBLE on a record** — no verdict-shaped name in the engine's 21-field
   vocabulary nor in any project's 7 declared `consumer_fields`; `check` is present and is the
   DECLARED VERIFIER, never its result.
2. **the projector cannot compute one** — `components.bzl` declares `"delta": ["gate", "project", …]`,
   so a `project → delta` import is an UPWARD edge `bnd-components` refuses. Structural, not an
   oversight.

#### ⚑⚑ Ξ-F3 — MY FIRST WITNESS WAS UNFALSIFIABLE, AND THE PROBE CAUGHT IT: **2/4**

The suite passed. The falsifiability probe then lifted both obstacles and **the suite stayed
green** — the exact defect it exists to prevent, in the check written to prevent it.

**Half 1 read the wrong LAYER.** It censused fields on parsed records, but `bib.parse` PROJECTS
each entry onto `_SCALAR + consumer_fields` and loud-drops the rest — so `verdict = {pass}` written
into a `.bib` can never reach a record. The check asserted something the parser makes structurally
impossible: **vacuous, not false**. Fixed to read the engine's VOCABULARY (`bib._SCALAR | _LIST`)
plus every project's `consumer_fields` — the layers that would actually have to change.

**Half 2's logic was sound; my TEST was wrong.** The probe patched `"project": [` and hit its FIRST
occurrence — the `COMPONENTS` file list at line 65 — not the `DEPS` edge at line 210. **Two tables,
one key spelling**; the mutation landed where nothing reads it. Same shape as `_claim_script`'s
recorded trap (a bare `find` matching the word inside a `cmd` string), one file over.

⚑ Both errors were mine and both were caught by *measuring the measurement*. Neither would have
been visible from a green suite — which is the whole argument for the probe.

**After the fix: 4/4** — the engine vocabulary gaining `verdict` reds, and `DEPS` gaining
`project → delta` reds, each naming the refuted half; restored cleanly both times.

**Regression**: `BOUNDARIES.md` regenerated (**4279 words**, `≡ projection`, rule 8) ·
`bnd-components` shows **83 files, only `library/concepts.py` missing** — my new suite correctly
placed in `components.bzl`, **no new drift added** · `gate boundaries` still the SAME 5 failures as
tick 31.

⚑ **Μ-F2 REMAINS THE BLOCK, unchanged and still not mine**: `dag.bzl` needs `dagbzl.py --write`,
which would fold the staged rename's 5 edges in beside my 1 (`genre.py → resolver.py`, from Κ).
Owner's call, one command.

### Ν.3 — `tutorial`, AND FIVE GENRES REFUTED BEFORE A LINE WAS WRITTEN (2026-09-10, tick 32)

**`genre.py --check paper` → 9 registered, 4 built-in + 5 declared each INVOKED.**
`--observe --genre tutorial paper` → **13 units, depths 0..12**, atoms first and theses last.

#### ⚑⚑ Ν-F9 — THE PRE-WRITE NOVELTY CHECK REFUTED **FIVE OF SIX** PROPOSALS

The survey's "needs a `[genres.*]` script" column listed six. Measured against the OBJECTIVE
population first (`scratchpad/probe_remaining_novelty.py`), scoring three axes — duplicate,
collapse, degenerate — because Ν-F5 showed "novel" alone is not enough:

| proposal | units | max | verdict |
|---|---|---|---|
| tutorial (grounding depth) | 13 | 54 | **NOVEL and usable** |
| cookbook (problem-cone) | 115 | 1 | ⚑ **DUPLICATE of `atomic`** — every claim's cone is distinct |
| procedure (absorb forward) | 11 | 28 | ⚑ **DUPLICATE of `staged@γ=1.0`** |
| example-collection (has emit) | 2 | 114 | ⚑ DEGENERATE — one unit holds **99%** |
| effective/style (check kind) | 3 | 82 | ⚑ DEGENERATE — **71%** |
| service-manual (tier) | 1 | 115 | ⚑ COLLAPSES to one unit — **every claim is `sandbox`** |

⚑ **`procedure` IS THE PLAN'S OWN WORKED EXAMPLE** — written out in full, with a script and a
`[genres.procedure]` table, in the approved plan. It is `staged` at the default γ. Had it been
written from the plan rather than measured, it would have been a second `brief` (Ν-F1).

⚑ **The check cost one probe and refuted five files.** This is the Ν-F1 discipline paying compound
interest: the first application caught a duplicate after the fact, the fourth prevents five.

#### Ν.3 — what `tutorial` asserts, and the property that makes it one

Reads `rests-on` through Κ's channel (STRUCTURE, the path `serial` uses for `_src`) and groups by
grounding depth, so **nothing appears before what it rests on**. Depth 0 is the foundational atoms
— where a tutorial starts by definition, not by choice.

**Verified by discrimination, 7/7** (`scratchpad/test_tutorial.py`), the first being the one that
matters:

1. ⚑ **NO claim precedes its premise, across all 88 rests-on edges** — the tutorial property, not
   merely a partition · 2. the live cut IS the depth partition · 3. differs from every built-in at
   every γ · 4. unit 0 is exactly the **54** foundational atoms · 5. a 2-CYCLE terminates with
   integer depths (a cycle is a POSTULATE, not a crash — the `clamp()` guard shape) · 6. an edge to
   a key OUTSIDE the grouping is ignored, not depth-0 padding · 7. no records ⇒ every claim an atom
   ⇒ ONE unit.

⚑ **Caught before running**: `depths(rests)` was called INSIDE the per-key loop, recomputing the
whole map 115 times. Hoisted — it is a property of the graph, not of a key.

⚑ **Μ-F1's lesson applied without being re-learned**: `checks/tutorial.py` added to `//paper:files`
in the same edit as the declaration, because Μ.1's generator now stages declared genre scripts and
a missing manifest entry reds the sandbox.

**Regression**: `paperkit-gate paper` PASS (111 claims) · `test_text_genres.py` **11/11**
(quickref/catalog/serial/brief all unmoved) · `genre.py --check` 9 registered, 5 declared invoked.

⚑ **Μ.2 remains BLOCKED** (Μ-F2, `dag.bzl` / staged changeset) — untouched by this tick, which
edits no build-graph state.

### Μ.2 — `bnd-genre-emit`: THE FIRST CLAIM ABOUT THE GENERATOR'S **OUTPUT** — ⛔ BLOCKED ON OWNERSHIP (2026-09-10, tick 31)

**The witness is written, verified and wired; the gate is RED on a repair that is not mine to make.**
That red is the deliverable (rule 5), and the block is recorded rather than routed around.

**What landed.** `paperkit/tests/boundaries_genre_emit.py` + `bnd-genre-emit` in
`boundaries/warrants.bib` (via `bibstruct --add --apply`; **50 entries, round-trips**). Audit
finding 1's first repair: `bibtex.bzl` is 1,109 lines of build graph whose only prior claim was
`bnd-lint`'s three regexes over its TEXT. This asserts its **OUTPUT**.

**⚑ THE ASSERTION IS A BICONDITIONAL, deliberately.** A project declaring `[genres.X]` gets a
`:genres` target; a project declaring none gets no target. **Either half alone is satisfiable by a
constant** — "always emit" passes the first, "never emit" passes the second — so only the iff pins
the generator's actual rule. Measured: **1 declaring (paperkit_paper), 11 silent**, all 12
partitioned.

**⚑ It reads the SOURCES, never the Bazel cache.** `hook_grid.py` is the precedent: derive what the
generator WOULD emit from `MODULE.bazel`, compare against the tree, invoke no `bazel`. A witness
keyed on an output-base hash reports a fact about one laptop's cache layout as a fact about the
generator.

**Verified by discrimination, 5/5** (`scratchpad/test_genre_emit_discriminates.py`), mutating
`bibtex.bzl` and restoring in a `finally`: guard removed → RED · attribute never filled → RED ·
emission deleted → RED · unmodified passes before and after.

⚑ **The first run was 5/5 with a WRONG DIAGNOSTIC, and that was fixed rather than accepted.**
Deleting the emission reported *"the emission is UNCONDITIONAL"* — red for the right reason, naming
the wrong cause. `emission_state()` now returns **three** states (`guarded`/`unconditional`/
`absent`), because *"no record" and "no constraint" render identically once collapsed*
(`Ζ·rests·unresolved`, quoted in the source).

#### ⛔ Μ-F2 — THE BLOCK: `dag.bzl` IS STALE, AND THE REPAIR WOULD COMPLETE SOMEONE ELSE'S CHANGESET

`bazel test`-equivalent `gate boundaries` → **5 FAILED checks**. Bisected rather than guessed
(rule 9); `bnd-components` names the cause:

    XX the partition is TOTAL over the real tree (82 files)
        missing=['library/concepts.py', 'tests/boundaries_genre_emit.py']
    XX dag.bzl IMPORTS is FRESH (130 edges)
        live-only=[('genre.py','resolver.py'), ('library/concepts.py', ×5)]

**Two owners, cleanly separable:**

| drift | owner | status |
|---|---|---|
| `tests/boundaries_genre_emit.py` unplaced | **mine** (this tick) | ✅ FIXED — added to `components.bzl` |
| `genre.py → resolver.py` edge | **mine** (Κ, tick 23 — `import resolver as _resolver` for `clean_env`) | ⛔ needs `dag.bzl` |
| `library/concepts.py` unplaced + its 5 edges | **the staged changeset** (`R library/concepts.py → paperkit/library/concepts.py`) | not mine |

⚑ **`python3 tools/dagbzl.py --write` is the tool's own named repair and I did NOT run it.** It
regenerates the whole file, so it would fold the staged rename's five edges in beside my one —
**completing a changeset whose author has not recorded those consequences yet**. `dag.bzl` is
currently untouched by the staged set (`git status` clean on it), so writing it would silently make
my tick the author of someone else's build-graph edit. Standing rule: *do not touch the
pre-existing staged changeset*.

**Cost of each option, for the owner's call:**
1. **Run `--write` now** — one command, gate green, but `dag.bzl` then carries 6 edges attributed to
   this tick, 5 of them the wheel work's. Cheapest and least honest.
2. **Land the staged changeset first, then `--write`** — correct attribution, blocked on work that
   is not ours to land.
3. **Hand-edit `dag.bzl` for the single `genre.py → resolver.py` edge** — attribution correct, but
   `dagbzl.py --check` compares against a full regeneration, so a partial hand-edit stays STALE and
   the gate stays red. **Does not work**; recorded so it is not retried.

⚑ Note the pre-existing reds are independent: `bnd-wheel`'s `builds` field still loud-drops
(Γ-F3), and `BOUNDARIES.md` regenerated cleanly (**4185 words**, `≡ projection`) after the bib
edit — rule 8 honoured.

**Verified in isolation**: `boundaries_genre_emit.py` **PASSES** standalone (2 structural
behaviors, 12 projects, 1 delta) · `hook_grid.py` green (`:genres` correctly needs no hook entry —
it is a *gate* member like `:invariants`, not a hook member) · `bibstruct --field section` **50 of
50**.

### Μ.1 — THE GENERATOR NOW EMITS A GENRE CHECK (2026-09-10, tick 30)

**Ν-F7's named gap closed at the level it belonged.** Tick 29 gated `paper/`'s declarations with a
claim in `paper/`'s own witness — correct, but a fact about the corpus (no other project declares
genres *today*), not a property of the build. Now **`bibtex.bzl` emits `:genres` for any project
that declares one**, and `@paperkit_paper//:genres` is in `//:hook`'s gate.

**Audit finding 1 re-verified before building on it**: `bibstruct --field check` over
`boundaries/warrants.bib` → **49 of 49** (full census, rule 10 satisfied), and `bnd-lint` is the
**only** claim naming a `.bzl`. `lint_bzl.main` is a line-by-line regex — it asserts nothing about
what the generator EMITS. 2,194 lines of `.bzl` gated by three patterns, as recorded.

**Three edits, each following an established precedent rather than inventing one:**

| edit | precedent |
|---|---|
| `_declared_genres(module_ctx, project)` parses `[genres.<name>]` headers | `_claim_script` — same file, same two documented traps (match at LINE START; a foreign `[` ENDS the scan) |
| `genres` repo-rule attribute | `witness`/`sites`/`closures`/`exports` — resolved in the extension, passed in, because **a `repository_ctx` cannot read `paper.toml`** (`bibtex.bzl:1046`) |
| `pk_cmd(name="genres")` appended to `recs` | `:invariants` — a whole-project meta-check at project tier, joining the gate |

⚑ **Emitted ONLY when the project declares a genre.** Verified by query: `attr(name, "genres", …)`
over boundaries/render/talk/config → **Empty results**. An unconditional target would add eleven
green-by-vacuity rows and one that matters — the `--without-K` collapse in target form.

⚑ **It runs `genre.py --check`, which already invokes each declared `cmd` through `run_declared`.**
Re-implementing the protocol in Starlark would give the build a second reading of what a pagination
is, free to drift from the engine's. **The generator's job is to WIRE the oracle, not to be one.**

#### ⚑ Μ-F1 — THE FIRST BUILD WENT RED, AND THE RED WAS THE MEASUREMENT

`bazel build @paperkit_paper//:genres` → **four `[Errno 2] No such file or directory`**, one per
genre. The check ran correctly under `linux-sandbox` and the sandbox was RIGHT: `//paper:files`
is a hand-maintained manifest listing `checks/claims.py` and `checks/gen_formulas.py` and **not the
five genre scripts**. A `[genres.X] cmd` names a file the build graph had no way to know was an
input.

⚑ **The tempting fix is the one `Ζ·entry·point` retired**: scan the `cmd` string for a `.py` token.
That reads a filename out of a string whose only contract is to be RUNNABLE — it returned `""` for
`cmd = "./run-witness {target}"` and emitted three cells with an empty `--check`. So the inputs are
**DECLARED** in `paper/BUILD.bazel`, where a manifest already lists them. Α-F2's shape, one project
over: a manifest that stages nothing cannot be wrong.

**Measured after**: `genre --check: 8 registered — 4 built-in objective(s) and 4 declared `cmd`(s)
each INVOKED and total over the grouping`, produced **inside the sandbox**. First time the genre
seam has been gated by the build graph.

**Regression**: `bazel test @paperkit_paper//:gate` → **1 test passes**, 111 claims, `--without-K`
distinct, 120 actions · `lint_bzl` clean on all three `.bzl` files · `bazel query
@paperkit_paper//:genres` resolves · `labels(data, :gate)` contains `:genres` beside `:invariants`.

⚑ **Still open (Μ proper, not done here)**: the generator remains gated by `bnd-lint`'s three
regexes. This tick added a target the generator EMITS and verified it end-to-end, but no claim yet
asserts that `bibtex.bzl` emits `:genres` **iff** a project declares a genre — the `graph/` project
of the plan's D2. The conditional emission is verified by QUERY here, not by a gate.

### ⚑⚑ Ν-F7 — THE FIX FROM TICK 28 WAS WIRED TO NOTHING; NOW IT IS A CLAIM (2026-09-10, tick 29)

**`genre.py --check` runs when a human types it.** Two independent searches — over `BUILD.bazel`,
`tools/bibtex.bzl`, and `.githooks/pre-commit` — find **zero** references. So tick 28 fixed a
gate that nothing invokes, and I reported it as closing a false green.

⚑ **That is the same shape as the defect it fixed, one level up.** Tick 28: a message asserting
more than the check performed. Tick 29: a check asserting more than the build runs. Audit finding
6 and Η-F2 both record this class (`Ζ·hook-rot`, `Ρ·talk·hook·wire`) — a capability that exists,
is correct, and is reachable by nobody.

**What was and was not gated, measured rather than assumed:**

| | reaches |
|---|---|
| `//:hook` (12 projects, 27 targets, `hook_grid.py` green) | `gate`/`adequacy`/`cohere`/`decisions` — **not the genre seam** |
| `claims.py:genre_declared_runs` | `run_declared` on **tempdir fixtures** (`ok.py`/`bad.py`/`fail.py`), never the project's own declarations |
| `genre.py --check` (tick 28, invokes the real `cmd`s) | **nothing — unwired** |

**The wire is a claim**, since that is how this repo gates things: `genre-declared-gated` in
`paper/implications.bib` + `genre_declared_gated()` in `claims.py`, resting on
`genre-declared-runs`. It walks `registry(proj)`, takes the entries with `declared=True`, and runs
each through `run_declared` — the same seam `--observe` uses, not a copy, so the check and the live
path cannot diverge.

**Verified by discrimination, 6/6** (`scratchpad/test_declared_gated.py`), which MUTATES the real
`paper.toml` four ways and restores it in a `finally`:

| broken declaration | caught? |
|---|---|
| the real tick-27 `-Ichecks` bug | RED — `NameError: name 'hecks' is not defined` |
| `cmd` naming a file that does not exist | RED — `exited 2 — can't open file …` |
| `cmd` that exits non-zero | RED — `exited 3` |
| `cmd` that DROPS a claim | RED — `not a function of the grouping — dropped ['b']` |

plus the unmodified project passing before, and passing again after restore.

**Rule 8 fired as designed** — a bib edit is a projection edit. `--check paper` went RED
(`paper.md ≠ projection`), regenerated to **5035 words**, diff +2/−2: the claim landed where
declared, and `transitive_reduction` moved three cross-reference annotations (the Γ-F4 behaviour,
now expected rather than surprising).

**Rule 9 checked, not assumed**: `grades.py` → **111 claims, behavioral=82 (was 81), imported=29,
no `broken`**. Δ's mutation sweep independently confirms the new witness flips — a second opinion
on the 6/6 harness, from the instrument rather than from me.

**Regression**: `paperkit-gate paper` PASS, **111 claims** (was 110) · `bibstruct --roundtrip` 2 of
27 unparsed, both pre-existing (A2-F8/Ε-F1 LaTeX braces at lines 44/50, upstream of the edit).

⚑ **STILL OPEN, and named rather than quietly left**: the claim gates `paper/`'s declarations
because `claims.py` is `paper/`'s witness. **No other project declares a `[genres.*]` table today**
(grep over all 14 `paper.toml` files), so the population is covered — but that is a fact about the
corpus, not a property of the gate. A second project declaring a genre would be ungated again.
The general fix belongs in `bibtex.bzl` (emit a genre check per project that declares one), which
is Μ's territory.

### Ν-F6 — FIXED: `--check` NOW INVOKES EVERY DECLARED `cmd` (2026-09-10, tick 28)

**The defect was a MESSAGE ASSERTING MORE THAN THE CHECK PERFORMED**, not a missing feature.
`main`'s loop read `if obj is None: … continue` — a declared genre was tested only for HAVING a
`cmd` string — and the success line then said *"every objective is total over the grouping"*, a
universal quantifier over a set it had half examined. Measured cost, one tick earlier: two genres
declared `python3 -Ichecks checks/…` (`-I` is ISOLATED MODE, so it parsed as `-c hecks` →
`NameError`) and `--check` reported **all 8 registered and total while neither could execute**.

**The fix runs them**, reusing `run_declared` rather than re-implementing the protocol, so the
check and the live path cannot diverge. A declared objective's totality is not a property of its
declaration; it is a property of what the command DOES.

**And the message now names what was actually run:**

    genre --check: 8 registered (…) — 4 built-in objective(s) and 4 declared `cmd`(s) each
    INVOKED and total over the grouping, and an unregistered name refuses loudly

⚑ A reader could not previously distinguish a universal that was VERIFIED from one that was
ASSUMED. The counts make the claim proportional to the work — the same discipline as
`bnd-check`'s member count (Η-F2) and `--without-K`'s "16 cited claims each carry a distinct
witness".

**Verified by discrimination, 6/6** (`scratchpad/test_check_invokes.py`) — a fix that only keeps
the green case green is not verified, so each case reconstructs a failure `--check` used to
CERTIFY:

| case | before | now |
|---|---|---|
| the real `-Ichecks` bug | **passed** | RED — *"declared objective exited 1 — Traceback…"* |
| a declared cmd that DROPS a claim | **passed** | RED — *"not a function of the grouping"* |
| a declared cmd that EXITS non-zero | **passed** | RED — *"exited 3"* |
| a declared cmd that INVENTS a key | **passed** | RED — *"not a function of the grouping"* |
| a correct declared cmd | passed | green |
| neither objective nor cmd | RED | RED (unchanged) |

⚑ `claims.py:genre_gates_the_seam` was inspected and NOT edited: it exercises `is_total` and the
built-ins directly and never calls `--check`, so this change neither weakens nor strengthens it.
Checked rather than assumed, because a claim about the seam is exactly what a seam change could
silently hollow out.

**Regression**: `paperkit-gate paper` PASS (110 claims) · `claims.py genre-gates-the-seam` OK ·
`--check paper` green with 4+4 invoked.

### Ν.2 — `quickref` + `catalog`: THE CLAIM-TEXT PAIR, AND A FACTORED CORE (2026-09-10, tick 27)

**Both genres `PK-GENRE-BLIND` made impossible are now built.** `genre.py --check paper` → **8
registered** (was 6), every objective total. These read CLAIM TEXT where `serial` read structure,
so between them Ν.1 and Ν.2 exercise both halves of what Κ opened.

| genre | cut | units over paper/ |
|---|---|---|
| `quickref` | one unit per LENGTH BAND, terse first | 3 — **31 / 48 / 35** |
| `catalog` | one unit per initial letter of the SIGNIFICANT term | 23 |

**Ν-F1 check ran first on both: neither is a built-in at any γ.** They cannot be — γ moves the
bracketing of the section grouping, while both cut ACROSS every group on a property of the text.

#### ⚑ Ν-F4 — THE WEDGE SAID FACTOR, AND FOUR COPIES WERE ABOUT TO EXIST

`reuse_check.py --propose serial.py --against brief.py` reported **`main ∩ main = 23`**, verdict
**OVERLAP — factor the shared core**. Two genres existed and two more were being written: four
copies of one stdin-parse/print loop. OVERLAP is not "no action" — it is the wedge skill's first
named anti-pattern to read it that way.

**Lifted `paper/checks/genrekit.py`**: `groups()` / `records()` / `field()` / `emit()` / `run()`,
plus the protocol and the D1 column-offset warning stated ONCE instead of in every genre. Each
genre keeps only its residue — the objective, the one thing a genre actually IS. `brief` and
`serial` were refactored onto it, and **11/11 discrimination cases** confirm neither moved
(`serial` still 12 units / the 2 spanning files merged; `brief` still the identity; tick 26's own
5/5 suite re-run and still 5/5).

⚑ `records()` deliberately does NOT supply a default for the empty case: what "no records" MEANS
is the genre's business — `serial` degenerates to `atomic` (no provenance ⇒ no issue structure),
`quickref` to the identity. A default here would impose one genre's reading on every other.

#### ⚑ Ν-F5 — THE STOP-LIST IS THE GENRE, NOT POLISH (measured before writing)

Keying `catalog` on the first character of the claim indexes ENGLISH GRAMMAR, not terms:
**A = 32, T = 32 of 114**, because claims open "A …" and "The …". Skipping leading function words:
**largest unit 15**, top letters C/P/S/G — real subject terms. One rule, 32 → 15 on the largest
unit. Measured in the novelty probe BEFORE the file existed, so the genre was never written wrong.

⚑ **The `atomic` collapse was a real risk and was tested, not assumed** — "one unit per letter"
degenerates to one unit per claim if every claim starts with a distinct term. Measured: 3 singleton
units of 23. On a corpus where it did collapse, that would be a true reading about the corpus.

#### ⚑ Ν-F6 — `--check` PASSES A GENRE WHOSE `cmd` CANNOT RUN

I declared `cmd = "python3 -Ichecks checks/quickref.py"` believing `-I` adds an include path. It is
**ISOLATED MODE**, so it parsed as `-I` plus `-c hecks` → `NameError: name 'hecks' is not defined`.

⚑ **`genre.py --check paper` reported all 8 registered and TOTAL while two of them were broken.**
The `--check` path validates the registry and the objectives it can call in-process; it does not
execute a declared `cmd`. Only `--observe` did, and it failed immediately. **A green `--check` is
not evidence a declared genre runs** — worth knowing before the census treats it as one.

The fix needed no flag at all: python puts the SCRIPT'S OWN DIRECTORY on `sys.path`, so
`python3 checks/quickref.py` finds `checks/genrekit.py` unaided — and `PYTHONPATH` would have been
dropped by `clean_env` anyway (Κ-F1's sanitization, now load-bearing for a case it was not written
for).

**Regression**: `paperkit-gate paper` PASS (110 claims) · `genre.py --check paper` 8 registered ·
`test_text_genres.py` 11/11 · `test_serial.py` 5/5 (unchanged after refactor).

### Ν.1 — `serial`: THE FIRST GENUINELY NEW GENRE (2026-09-10, tick 26)

**Two files, no engine change**: `paper/checks/serial.py` + `[genres.serial]`. One unit per source
bib — the issue cut. `genre.py --check paper` → **6 registered**; `--observe --genre serial paper`
→ **12 units for 12 warrant files**.

**⚑ THE Ν-F1 CHECK RAN FIRST, AND THIS TIME IT PASSED.** `brief` was written and only afterwards
measured equal to `_staged`. So before this file existed, the PROPOSED partition was compared
against all four built-ins at eight γ values (`scratchpad/probe_serial_novelty.py`): **no built-in
produces the by-source partition at any γ.**

The reason is structural, not incidental: **2 of the 12 files span more than one section**
(`model.bib`, `composition.bib`). A built-in paginates the SECTION grouping it is handed, so where
a file crosses sections, no bracketing of that grouping can recover the file cut. `serial` must cut
ACROSS the grouping — an UPWARD/merging objective like `_collection`, never a `_talk`-shaped split
(which would drop totality on exactly the two files that motivate the genre).

**It is the first genre to read Κ's records channel for STRUCTURE rather than text**, and the first
consumer of `_src` anywhere in the tree — the field Ξ-F1 found had been carried on every record
since parse time (`bib.py:217`) while an obstacle key asserted it was erased.

**Verified by discrimination, 5/5** (`scratchpad/test_serial.py`), since `--check` asserts only
totality (which the identity also satisfies):
1. the live cut IS the by-`_src` partition (12 units / 12 bibs) · 2. differs from every built-in at
every γ · 3. ⚑ the 2 section-spanning files each land in ONE unit (`model.bib`,
`composition.bib`) · 4. an unsourced key gets its own unit — a missing field never loses a claim ·
5. with no records every key stands alone.

⚑ **Case 5 corrected the docstring, not the code.** I wrote *"the empty case degenerates to the
identity on the grouping"*; the test showed it degenerates to `atomic` — every key gets a synthetic
per-key source. The behaviour is right (this genre's units ARE its provenance, so with none there
is no issue structure to assert, and inheriting the incoming bracketing would claim an issue
boundary the data does not support). The prose was wrong and now says so.

**γ deliberately NOT declared**: the units are determined by `_src`, and γ only moves the
bracketing this objective merges across — a declared γ would imply a dial that does nothing
(the `_atomic` γ-invariance of Ν-F3), stated rather than left to be discovered.

**Regression**: `paperkit-gate paper` PASS (110 claims, 15 sections) · `claims.py genre-registry`
OK · `genre.py --check paper` 6 registered, all total.

### Ξ — RESIDUALS RE-VERDICTED: two obstacle keys retired (2026-09-10, tick 25)

Κ retired `PK-GENRE-BLIND`, leaving four residuals carrying a verdict that cited it. **A stale
BLOCKED is worse than no verdict — it reads as settled.** So the residuals were re-verdicted
against what a genre can ACTUALLY see, measured through the real seam rather than re-read from the
plan's prose (`scratchpad/probe_residual_reach.py`, `probe_src_provenance.py`).

**The field census — what 114 records actually carry to a declared genre:**

    key 114 · _src 114 · _type 114 · section 114 · claim 114 · from 114 · rests-on 114
    reads 114 · consumes 114 · check 110 · join 96 · link 13 · title/author/year 4
    depth/move/glue 3 · journal/volume/pages 2 · emit/as/number/booktitle/doi 1

#### ⚑⚑ Ξ-F1 — `PK-BIB-PROVENANCE` IS FALSE. `_src` WAS THERE THE WHOLE TIME.

The obstacle claimed: *"`observe` composes all bibs into one `F` (`project.py:499-500`), so issue
identity — which IS file identity — is erased before the grouping runs."*

**Measured:** every record carries `_src`, set to `path.name` at parse time (`bib.py:217`:
`f = {"_src": path.name, "_type": e.typ}`). Over `paper/`:

    12 declared warrant files · 12 distinct _src values on the records · 0 declared-but-absent
    through Κ's channel to the genre: 12 distinct, IDENTICAL to pre-seam

    implications.bib 26 · resolver.bib 20 · model.bib 15 · composition.bib 15 · engine.bib 8
    adequacy.bib 7 · projection.bib 5 · gate.bib 4 · rhetoric.bib 4 · references.bib 4
    liveness.bib 3 · conclusion.bib 3

**The reasoning error, worth keeping:** `F.update()` merges the DICTIONARIES, and the loop variable
`b` does go out of scope — so "the composition erases the source" looks right if you read the
control flow. But provenance was never in the loop; it is a FIELD ON THE DATA, written before the
merge. I reasoned about the code path and never looked at a record.

⚑ Same shape as Ν-F1 one tick earlier (searched the file population, not the objective population)
and as the `mem_learn` miss at tick 19 (the capability existed; one line of data flow didn't).
**Three consecutive findings where the thing was already built and I inferred its absence from
structure instead of measuring.** Standing rule 4 exists for the null case; this is its dual — a
PRESENT thing invisible to a reading that never queried it.

**serial/issue-based is UNBLOCKED**: issue identity = `_src`, no engine change needed.

#### Ξ-F2 — `PK-GENRE-PURE` STANDS, and the census says exactly why

`check` is present on 110 of 114 records — but it is the **DECLARED VERIFIER STRING**
(`cmd:python3 …`, `claim:key`), not its current result. A genre can see *what would verify this
claim*; it cannot ask *what is failing NOW*.

Troubleshooting's ordering ("which observation next") is a function of the CURRENT failure state,
which no field carries and which `observe` never computes — the gate does, downstream, and
`project.py` must not import the grader (the component lattice forbids the upward edge). So the
obstacle is REAL and structural, not an oversight. **Troubleshooting stays BLOCKED-ON-`PK-GENRE-PURE`.**

⚑ The 4 records with no `check` are a separate reading, not chased here: `--without-K` and the
gate both key off `check`, so a claim without one is uncited or non-mechanical by construction.

### Ν.0 / Ξ-Q — THE γ SWEEP: three findings, one of them about MY OWN GENRE (2026-09-10, tick 24)

Read-only sweep of 5 genres × 8 γ values over `paper/` (114 claims, the one dense-`rests-on`
corpus). `scratchpad/probe_gamma_sweep.py`. Every cell paginates the same 114 claims — totality
holds throughout, which is the invariant the sweep is measuring against.

| γ | staged | atomic | collection | talk | brief |
|---|---|---|---|---|---|
| 0.0 | 10u max48 | 114u max1 | 10u max48 | 65u max9 | 10u max48 |
| 0.2 | 11u max44 | 114u max1 | 11u max44 | 65u max9 | 11u max44 |
| 0.5 | 12u max25 | 114u max1 | 11u max44 | 65u max9 | 12u max25 |
| 1.0 | 11u max28 | 114u max1 | 10u max48 | 65u max9 | 11u max28 |
| 2.0–100.0 | 15u max26 | 114u max1 | 9u max73 | 66u max7 | 15u max26 |

#### ⚑⚑ Ν-F1 — `brief` ≡ `staged` AT EVERY γ. I BUILT A DUPLICATE OF A BUILT-IN.

Ι shipped `brief` as *"the identity on the grouping"*. `_staged` **is** the identity on the
grouping. Verified beyond the probe's key-tuple equality: `--observe --genre staged --gamma 4.0
paper` is **byte-identical** to `--genre brief --gamma 4.0 paper`.

`reuse-sppf-wedge` fired at tick 21 and I recorded *"no sibling to factor against — NOVEL by
absence of corpus"*. That was **the wrong corpus**: I searched `checks/genre_*.py` for a sibling
SCRIPT and never compared the OBJECTIVE against the four built-ins the registry already carries.
The wedge's own anti-pattern list names this — *assume-floor*, deciding a thing is novel without
running the enumeration over the right population.

⚑ **It does not invalidate Ι, and this is the distinction worth keeping.** Ι's deliverable was
never the brief cut; it was *"the first declared genre EVER EXECUTED"* — proving `run_declared`
end-to-end on a real project. A duplicate objective is the IDEAL pilot for that: the seam is under
test, and the objective is a known-good control whose expected output is independently derivable
from a built-in. Ι is a valid instrument test and an invalid new capability, simultaneously.

**Not deleted** — `brief` stays as the declared-seam regression fixture, now with its equivalence
DECLARED rather than accidental. A genre whose output is byte-comparable to a built-in's is a
better test than one whose correctness only its own author can judge.

#### Ν-F2 — THE LOOSE-LEAF CONTROL IS A MISS (the plan's cheap positive control, refuted)

Plan: *"try `collection` at γ≈0.2 for loose-leaf BEFORE writing anything. A hit is a codomain win;
a miss is a real residue."* **Miss.**

    γ=0.0   10 units, largest holds 48 of 114 (42%)  sizes=[48, 25, 9, 7, 5, 5]…
    γ=0.2   11 units, largest holds 44 of 114 (38%)  sizes=[44, 25, 9, 7, 5, 5]…
    γ=1.0   10 units, largest holds 48 of 114 (42%)  sizes=[48, 25, 9, 7, 5, 5]…

Loose-leaf wants MANY SMALL independently-replaceable units. `collection` merges by connected
components of `rests-on`, and on a corpus where most claims ground into one cone that produces
**one giant unit plus a tail** — the opposite of loose-leaf, at every γ probed. Lowering γ does not
help because γ moves the *modularity* partition and `collection` then merges across it anyway.

**Loose-leaf is a REAL RESIDUE**, not an existing form under another name. It stays in Ν's
"needs a script" column.

#### Ν-F3 — Ξ-Q PARTIAL: `atomic` and `talk` are γ-INVARIANT BY CONSTRUCTION

`staged ≡ collection` only at **γ ≤ 0.2**; they diverge from γ=0.5 upward. `atomic` and `talk` are
**never** equal to anything, and are FLAT across all eight γ values.

The cause is structural, read from source rather than inferred: `_atomic` is
`[[k] for g in groups for k in g]` (`genre.py:62-66`) — it **discards the bracketing entirely**,
and γ only changes the bracketing, so γ cannot reach it. `_talk` splits on a WORD BUDGET, also
independent of how the groups were bracketed.

**So the hypothesis is half right, and the half that fails is the informative one.** The registry
is NOT one continuum: `staged`/`collection` are γ-parameterised quotients of the grouping, while
`atomic` and `talk` are objectives whose output is *invariant* under the grouping's bracketing.
Two kinds, not four points on a line — and `_talk`'s invariance is exactly the CONTENT-dependence
that made it the `PK-GENRE-BLIND` outlier. The axis that separates the built-ins is **what the
objective reads** (bracketing vs claim text), not γ.

### Κ — records-channel: `PK-GENRE-BLIND` CLOSED (2026-09-10, tick 23)

**The obstacle four residual genres collapsed onto is gone.** `records` reached `is_total` and
nothing else; the subprocess got keys and no way to ask what a claim SAYS, while built-in `_talk`
reads `r["claim"]` for its 84-word budget and `_collection` reads `rests-on`.

**The channel**: records written as **JSONL to a temp file**, path exported as
`PAPERKIT_GENRE_RECORDS`. Each property chosen against a measured alternative:

| choice | against | why |
|---|---|---|
| a FILE, not argv | argv | 62,579 paths hit **ARG_MAX (`errno 7`)** in this repo's own tooling (tick 19); a corpus is exactly what grows |
| JSONL, not a flat table | TSV | `structured-not-flat` — a claim carries nested `emit`/`items`; a flat projection forces every consumer to re-invent escaping |
| env var under `PAPERKIT_` | a new positional arg | `resolver._ENV_KEEP_PREFIX` already allow-lists it; same "set by the ENGINE rather than inherited" pattern as `PAPERKIT_PYTHONPATH`; a new arg would break `cmd` templates in the wild |

**Optional by construction** — stdin is byte-identical, so a genre that ignores the variable is
unaffected and the three shipped fixtures (`claims.py:1031-1046`, all passing `records=[]`
positionally) are untouched.

**Verified by discrimination, 6/6** (`scratchpad/test_records_channel.py`):
1. a declared genre READS claim text · 2. ⚑ **a DECLARED genre reproduces `_talk`'s cut exactly —
`[['a'], ['b','c']]` both ways** · 3. a genre ignoring records is unaffected · 4. stdin
BYTE-IDENTICAL to the pre-Κ protocol · 5. the temp file is cleaned up · 6. the child's env is
sanitized (`LD_PRELOAD`/unlisted → `None`).

⚑ **Case 2's first run was WEAK EVIDENCE and was fixed rather than reported.** The fixture's
claims summed to 52 words, under the 84-word budget, so `declared == builtin == [['a','b','c']]`
proved only that two objectives agreed on a cut NEITHER made. Re-fixtured to 50+50 words so the
budget actually bites; the pass now shows the split.

**Regression**: `paperkit-gate paper` PASS (110 claims, 15 sections) · `claims.py
genre-declared-runs` OK · `boundaries_env` PASS (6 behaviors, 3 deltas) · `genre.py --check paper`
5 registered · `--observe --genre brief paper` 16 units, unchanged.

### ⚑ Κ-F1 — `run_declared` CLAIMED ENVIRONMENT SANITIZATION IT DID NOT PERFORM (2026-09-10)

The docstring read: *"it inherits the environment sanitization gating already does."* It did not.
`subprocess.run` passed **no `env=`**, so a project-declared genre ran with the **full ambient
environment** — `LD_PRELOAD`, `PYTHONPATH`, and a `PATH` whose relative entries resolve to the
project being gated (the exact `Τ·path` attack `clean_env`'s comment describes: *"a document could
shadow a tool by planting it beside itself"*).

**Measured**: `pycodemod --calls clean_env` → **11 calls, all in `resolver.py` or its boundary
tests, ZERO from `genre.py`.**

Same class as D1 — a docstring asserting a property of code that does not hold — but with teeth:
D1 cost a confusing error message, this one was a real hole in the trust posture the same
paragraph invokes. **Fixed by making the claim TRUE** (`env=_resolver.clean_env()`), not by
deleting the sentence. Case 6 of the harness is its witness.

⚑ Caught by reading `clean_env` to design Κ's channel, not by looking for it — the same accident
that produced Γ-F4. Worth noting as a pattern: the defects on this thread are found while
verifying a PREMISE, not while auditing.

### Ι — brief: THE FIRST DECLARED GENRE EVER EXECUTED (2026-09-10, tick 21)

**Two files, no engine change** — which is the property being demonstrated, not an economy:
`paper/checks/brief.py` (new, 57 lines incl. docstring) and a `[genres.brief]` table in
`paper/paper.toml`.

**Measured result** — `paperkit-project --observe --genre brief paper` returns **14 units, one per
section**, `brief.py` invoked as a subprocess through `run_declared`, `is_total` satisfied. Before
this the open half of the registry had NEVER run against a real project: `claims.py:894` compares
`cmd` as a STRING against a tempdir fixture and never executes it.

**The objective is the IDENTITY on the grouping** — one unit per cluster. Deliberately the
smallest non-built-in objective: the point of the file is to prove the SEAM, so the risk must not
live in the objective. `reuse-sppf-wedge` fired first and found **no sibling to factor against** —
`find` for `genre_*.py`/`brief*.py` returns empty, so this is the tree's first declared-genre
script. NOVEL by absence of corpus, not by measured wedge; the next such script is where the
factoring question actually arises.

**⚑ It cannot consult claim text, and that is `PK-GENRE-BLIND` demonstrated rather than asserted.**
`run_declared` sends `"\t".join(g)` — keys only — while the built-in `_talk` reads `r["claim"]`
for its 84-word budget. A brief is expressible BECAUSE it is a pure function of the grouping. The
file's docstring records this as the ceiling of the declared seam.

**Verified**: `pycodemod --source brief` (1 def, resolves) · `genre.py --check paper` → **5
registered (atomic, brief, collection, staged, talk)**, up from 4 · `--observe --genre brief` →
14 units · `claims.py genre-registry` OK · `claims.py genre-gates-the-seam` OK ·
`project --check paper` → `paper.md ≡ projection (4978 words)` (no bib edited, so rule 8 does not
fire — confirmed rather than assumed).

**D1 visible in the output**: the unit lines print `intro`, `edges`, `resolver` … in column 0 —
the section column stdin does NOT accept. Θ's correction, observable one tick later.

### Ι-F1 — ✅ FIXED (tick 22, 2026-09-10). THE TREE SETTLED IT; MY THREE "OPTIONS" WERE TWO TOO MANY.

**Tick 21 priced three options and called it an owner decision. That was over-cautious: the tree
already answers it, and I had read one artifact short.**

`GAMMA = Param("gamma", "PAPERKIT_GAMMA", config="gamma", default=None)` (`project.py:603`) with
its own comment: *"the RESOLUTION dial… Each genre carries a default γ… Default None = whatever
the genre asks for, which keeps a genre's declared γ meaningful instead of overriding it with an
engine-wide constant."* And `claims.py:gamma_is_reachable` is a **PASSING gate** asserting
*"γ … must be REACHABLE, not frozen into each genre"* plus `GAMMA.default is None`.

**So there are TWO γ parameters that share a spelling:**

| declaration | meaning | owner |
|---|---|---|
| `[paper] gamma` | the PROJECT-WIDE OVERRIDE | `GAMMA` Param |
| `[genres.X] gamma` | THAT GENRE'S DECLARED DEFAULT — the value the override overrides | `genre.registry` |

Refusing the second made the first's documented behaviour **unreachable**: nothing left to
override. Option 3 (γ becomes `[paper]`-only) would have contradicted a passing gate — I priced it
without checking, which is the error worth recording.

**The fix — exemption BY OWNERSHIP, not by key.** `bib._SCHEMA_TABLES = frozenset({"genres"})`,
skipped in the sibling-table loop. The guard tests key NAMES against the `[paper]` set, which is
right for a table with no schema of its own and wrong for one whose keys are a declared vocabulary
another module owns. `genre.registry` (`genre.py:326`) owns `[genres.*]`, schema `{what, cmd,
gamma}` — documented in its docstring and named in `resolve`'s refusal message.

⚑ **`[checks.*]` is deliberately NOT exempt** — its `cmd` shadowing trap is one of the three faces
this guard exists for, and its keys are not a closed schema owned elsewhere.

**Verified by DISCRIMINATION, not by the happy path** (`scratchpad/test_schema_tables.py`,
**7/7**): `[genres.*]` with `gamma` loads; all three recorded faces still refuse (`root` under
`[checks.X]`, `consumer_fields` under `[checks.X]`, `root` above `[paper]`); `adequacy` under an
arbitrary table still refuses; and ⚑ **`gamma` under `[checks.X]` still refuses** — proving the
exemption keys on the TABLE's ownership, not on the key name.

**γ measurably works now**: `--observe --genre brief paper` gives **16 units at γ=4.0** vs **14 at
the default 1.0** — `intro`/`model`/`selfhost` split, `engine` separated. The dial was inert for
this project one command earlier.

**Full gate green**: `paperkit-gate paper` → PASS, 110 claims, 15 sections · `boundaries_check`
PASS (7 behaviors, 1 delta) · `boundaries_toplevel` PASS · `genre.py --check paper` → 5 registered
· `project --check paper` → `paper.md ≡ projection (4978 words)` · `claims.py gamma-is-reachable`
OK.

### ⚑ Ι-F1 — ORIGINAL FINDING (2026-09-10, tick 21; kept per rule 6, superseded by the fix above)

`gamma = 4.0` under `[genres.brief]` **exits the build**:

    paperkit: `gamma` is declared under [genres.brief], but it belongs under [paper].  TOML
    scoped it out of the [paper] table, so the engine reads NONE of it …

Two components disagree, both deliberately written:

| component | site | says |
|---|---|---|
| `bib._misplaced_paper_key` | `bib.py:335-382` | **REFUSE** — `gamma` ∈ `paper_keys() \| _param_config_keys()`, so outside `[paper]` it is a misplacement |
| `genre.registry` / `observe` | `project.py` `spec.get("gamma", 1.0)` | **REQUIRED THERE** — a genre carries its own γ |
| `claims.py:896` | fixture | **ASSERTS IT IS CARRIED** — `reg["brief"]["gamma"] == 4.0` |

`gamma` lands in the forbidden set BY CONSTRUCTION: `_param_config_keys` AST-walks every engine
`Param(..., config="…")` and `GAMMA = Param("gamma", …, config="gamma")`.

**⚑ Why nothing caught it: the fixture is not on the guard's path.** `genre_registry()` writes a
tempdir `paper.toml` and calls `genre.registry(d)` **directly**, never `load_config` — so the tree
contains a green fixture asserting a declaration the engine refuses on every real project. Same
shape as A2-F1 (a check verifying a PICTURE of its proposition) and as `Ζ·toml·scope`'s own
docstring: *"a trap that catches CONSUMERS and never us"* — here it catches a consumer who follows
the registry's own documented schema (`resolve`'s refusal message names **what/cmd/gamma**).

**Not fixed — needs an owner decision, and the tree does not settle it** (standing rule: gather,
price, stop). Three options:
1. **Exempt `[genres.*]` from the guard** — cheapest, but the guard is deliberately TOTAL over the
   key set ("per-key would have missed the instance that prompted it"); an exemption re-opens the
   class it closed.
2. **Rename the registry key** (`resolution`? `sigma`?) — no collision, but breaks the documented
   schema in `resolve`'s error message, `claims.py:896`, and `_collection`'s own γ prose.
3. **Make γ genuinely `[paper]`-only** — one γ per project, not per genre; contradicts
   `spec.get("gamma", 1.0)` and the loose-leaf plan note (*"try `collection` at γ≈0.2"*), which
   needs γ to vary BY GENRE.

Ι shipped **without** `gamma`, taking the genre default (1.0), and `paper/paper.toml` carries the
contradiction as a comment beside the omission rather than a silent workaround.

### Θ — genre-docstring / D1 (2026-09-10, tick 20)

**One docstring, +11/−1, no behaviour change.** `genre.py`'s `run_declared` claimed *"the format
is the one the CLI already prints."* It is not, and both ends were verified from source before the
edit rather than carried from the plan:

| end | site | shape |
|---|---|---|
| IN | `genre.py:298` | `payload = "".join("\t".join(g) + "\n" for g in groups)` — **keys only** |
| OUT | `project.py:639` | `print(f"{u['section']}\t" + "\t".join(u["keys"]))` — **section in column 0** |

**The trap, stated in the docstring now:** an author developing a declared objective by
round-tripping `--observe` output feeds section LABELS back as claim keys, and `is_total` refuses
them as *invented keys* — an error naming TOTALITY when the fault is a COLUMN OFFSET. The wrong
error is the cost; the seam all 21 genres cross is where it sits.

**Fixed the prose, not the protocol** — deliberately, and the docstring now says why: a section
label is not a claim key, and a pagination is a partition OF KEYS. The wire format is the correct
half.

**Verified** (`.py` → `pycodemod.py`, standing rule 7): `--source run_declared` re-resolves,
1 definition, body byte-identical (278-309 → 278-319, docstring-only). `boundaries_check.py`
**PASS (7 behaviors, 1 delta)**. `genre.py --check paper` → *"4 registered (atomic, collection,
staged, talk) — every objective is total over the grouping"*.

⚑ **Ran the boundary suite specifically because Η-F2 was this exact shape** — a regex scraping a
comment and reporting PASS on 24 of 25 members. A docstring edit to an engine file is a plausible
input to a scraper, so the suite was evidence, not ceremony. It did not move.

### A2 — report witness split (2026-09-09, pre-loop)
All 16 `report/warrants.bib` checks distinct; was 7 claims on `fresh:all`. New witnesses
`distinct.py`, `grades.py`, `grounding.py` (all exit 3 on cannot-run) + `fig:shows-layout` mode.
`gen.py` unknown-asset fallthrough → refusal. Fixed a **2-cycle** in `paper/implications.bib`
(`grouping-not-pagination` ⇄ `genre-registry`) decided from three agreeing lines of evidence;
graph now 110 claims / 87 edges / depth 0..12 / acyclic.
Findings A2-F1..F8 in the plan file.

### Α — wired-scope (2026-09-09)
`report/` + `image/` wired into `MODULE.bazel`, both `tier = "local"` (host-coupled: image shells
podman; report shells sibling gates transitively). Created `image/BUILD.bazel` (Α-F1: the dir was
not a Bazel package at all — the extension failed to LOAD, a second reason under the missing
`bib.project`). Completed `report/BUILD.bazel`'s manifest (Α-F2: `determinism.py` and
`mitigation.py` were absent while two claims invoked them; a manifest feeding no target cannot be
wrong).

**Measured** — `@paperkit_report//:invariants`, first run ever:
`--without-K — 16 cited claim(s) each carry a distinct witness`. A2's split is machine-confirmed.

`@paperkit_report//:gate` = 9 pass / 2 cannot-run / 5 fail. The 5: four stale assets (pre-existing
drift, now attributable per-asset instead of one indistinguishable red) + `rpt-status`.

**Α-F3 CORRECTION:** I first read the red gate as "the gate cannot express cannot-run." Wrong.
`pk_gate` aggregates with `bad = "fail"` (`verb.bzl:302`), `verdict.py:223` maps rc 2 →
`cannot-run`, and `rpt-dag.verdict.json` reads `"verdict": "cannot-run"`. The tristate is honored
end to end; the red was five genuine fails. Recorded because the wrong reading is instructive: I
inferred the aggregator's policy from a red instead of reading the rule.

### Γ — tristate-delta (2026-09-09)
**Declared, did not route around.** `layout._sandbox_root` refuses when the engine is a sibling
and no root is declared — a hard-won guard (the old inference copied ~/github ten times, 95.8 GB,
all green; and let Δ mutate 52 unrelated repos and call it this project's sensitivity). The
boundary suite makes the δ *the declaration itself*, over a size threshold, because ownership is
what only the owner can state. So Γ declares.

⚑ **Only 2 of 9 hook-set projects had a root** (`paper/` added here, `paperkit/library/`). Seven
could not be Δ-graded at all. All nine now declare: root `"."`, the rest `".."` (the repo).

`_delta()` now raises `CannotGrade` instead of `json.loads(r.stdout or "[]")`. Three call sites
updated; the regeneration path changed to **generate-all-then-write**, because the old
write-as-produced loop silently overwrote four committed assets with the degenerate rendering of
an empty list whenever the grader could not run — the write path was strictly worse than the
check path.

**Gain:** both witnesses' empty branch can now mean what it says. They previously had to hedge
("could not run OR graded nothing"); an empty corpus is now a real refutation.

⚑ **Γ-F4 — Γ CAUGHT A REGRESSION A2 LEFT BEHIND, AND I HAD REPORTED A2 DONE.** `grades.py` read
`broken=2` (was `behavioral=81, imported=29`): the repo was RED. Bisected — pristine files OK, root
declared + cycle fix reverted OK, cycle fix present FAIL. The A2-F7 edge fix changed `rests-on`,
which feeds `transitive_reduction`/`references` and therefore renders INTO `paper.md`; the
committed document went stale against its own corpus. Re-ran the projector: 2 lines, both claims
OK, ladder clean. The diff is independent evidence the cycle was real — with the cycle,
`transitive_reduction` could not decide which of `observe-second-shape`'s two edges was redundant
and emitted NO annotation; with a DAG it resolves. **New standing rules 8 and 9 exist because of
this.**

**Γ-F1:** `delta.md` was rendering from `[]` for SEVEN of nine projects, and the freshness check
was green-or-stale over a structurally incomplete table with nothing able to say so.
**Γ-F2 (unfixed):** `library/paper.toml`'s comment says "two up — the repo" but `root = ".."`
resolves to `paperkit/`, one up. Prose or value is wrong.
**Γ-F3 (unfixed, pre-existing):** `bnd-wheel` declares `builds`, dropped loudly by the parser.

### ADEQUACY SWEEP — RESULT (2026-09-09, `bazel test @paperkit_paper//:adequacy`)

**PASSES.** 94,797 actions, 72,347 executed (22,451 action-cache hits), **2h08m** wall, ten
`linux-sandbox` actions throughout. Denominator settled at 94,796 — this time the plateau WAS the
ceiling (the monotone-denominator caution still stands; it just happened to have converged).

**All 110 graded claims in `paper/` read `behavioral`.** Zero `broken`, zero `vacuous`, zero
`indeterminate` — every claim is falsifiable by mutation.
- ⚑ Confirms **Γ-F4 fully repaired**: the `broken=2` from the unregenerated projection is gone.
- ⚑ And the earlier in-process reading of `imported=29` becomes `behavioral` here, because the
  Bazel path reads the library certificate WITH the owner's engine fingerprint
  (`bibtex.bzl:956-960`, Λ·witness) instead of flattening to the `imported` tag. **The two paths
  give different grades for the same claims** — worth its own investigation; the Bazel reading is
  the more informative one.

**⚑ Δ-F9 — THE `−` CENSUS NEEDS NO NEW INSTRUMENTATION; THE SWEEP IS ALREADY THE COVERAGE LEDGER.**
Every mutation cell emits its own record: `<claim>__<module>__<sitekind>__<site>_arm_<n>.eval.json`
(e.g. `prose-projected__genre__flip__talk_arm_0`, `prose-projected__bib__branch__scalar_value_arm_2`,
`prose-projected__project__dflip_GLUE_arm_0`). ~72k of them for one project.

That is EXACTLY the granularity the `−` census termination condition requires — one record per
(claim × module × site × arm). Read as a relation *"which (site, arm) is flipped by which claim"*:
- a site **no** claim flips → **UNCOVERED**
- a site whose arms are all flipped by the **same** claim set → **UNDIFFERENTIATED** (covered, but
  no claim tells the arms apart — the ambiguity case in the chart reading)

⚑ **But the aggregate records are NOT sufficient.** `adequacy_rec.verdict.json` is bare
`{"verb":"adequacy","verdict":"pass"}`, and each `<claim>__grade.grade.json` is bare
`{"claim","grade"}` — the `read_grade.py` reading is deliberately cheap and carries NO `tests`
fingerprint, no `why`/`not_higher`/`not_lower`, no clamp. **The `−` census must read the per-cell
`.eval.json` files, not the grade records.** A census built on the grades would see 110×
`behavioral` and conclude coverage was complete.

⚑ **Three exclusions from grading, from the generator itself** — the `−` census must enumerate
these as gaps, not inherit them as fine: non-sandbox `tier` (`bibtex.bzl:948`), non-mechanical
check type (`:954`), imported certificate (`:958`). The 50 blanket-exempted warrants (Ω) are
therefore ABSENT from this ledger entirely — they were never graded, so no `.eval.json` exists for
them, and their absence is invisible from inside the sweep.

⚑ Also observed: **two `pk_grade` rules exist** — `calc.bzl:722` and `grade.bzl:61`. This is the
naming collision `ARCHITECTURE.md` §3.6 already flags as a real defect (see Λ · arch). The
adequacy path uses `calc.bzl`'s, which emits `<name>.grade.json`.

## Tick log

| tick | date | item | outcome |
|---|---|---|---|
| 51 | 2026-09-10 | Σ-F13 · the fix already exists | ⛔ **STOPPED ON A VENDORING RULE — and Σ-F12's "three options" were two too many.** ⚑⚑ **The repair is already written, tested, and wired to ONE of its TWO callers.** `calc.bzl:446-455` carries `Τ·mem·observe·inside` recording *this exact defect and its fix* for `pk_eval` — *"4.7MB reported for a cell whose in-scope peak is 35MB"* — and `tools/cellcgroup.py`'s docstring **is** Σ-F12, written before I wrote it. So t50 was a RE-discovery. Measured with the owning tools (rule 7): `--calls write_peak` → 1 def, **2 calls, both `eval.py`**; `pk_calc`'s payload `discriminate.py` makes **0**. `--literal '--peak'` → 1 site, `cellargs.py:64`, *"in-scope memory.peak"*. **Option 1 cannot be applied as written**: `--imports discriminate.py` → 10 engine-internal siblings, so the engine cannot reach `tools/cellcgroup`, and `pk_calc` stages no Python tool (only `_cap`) where `pk_eval` declares `tools = [...]`. **The cheapest fix is ~3 lines in `cgroup-scope`** — it owns `$CG`, already reads `$CG/memory.events` per climb attempt, and `rmdir`s in an EXIT trap; and the climb REUSES `$CG`, so the post-climb `memory.peak` is the cross-attempt watermark, exactly what a reservation wants. ⛔ **Blocked by that file's own banner: *"this file is not edited in place."*** ⚑⚑ **But `diff` says the rule is already broken FOUR times** — 251→367 lines, paperkit-authored UUID naming, `pids.max` backstop, OOM climb, and the banner itself. **A Π-type with no inhabitant (rule 11): the banner is the TYPE "upstream owns this file"; the four additions are evidence the argument was never supplied.** 3 options priced; recommend (1) *plus* a banner correction, which is an ownership statement a tick may not make. ⚑ **Σ-F13b, independent**: `_RS` tops at **4096** while `cgroup-scope` climbs to **8192**, so a cell legitimately needing 8192 has no expressible reservation — `mem_learn`'s `mb > HI` discards it as un-isolated, it falls to the default, and it re-climbs every run. **Non-convergence at the top bucket, structurally**; live in `Ζ·mem·ceiling` (one cell killed two `//:hook` runs, which is why the ceiling was raised — **the raise fixed the climb and left the ladder behind**). ⚑ **CORRECTION to my own cross-repo census this session**: it framed `HI` as the bug; the owning files say `HI` faithfully tracks `_RS` and the gap is `_RS` vs the climb — **directionally right, causally wrong**, and acting on it would have raised `HI` while leaving `_RS` unable to schedule the bucket. ⚑ **Σ-F13c**: the wedge (∩ 8–14 vs large residues = the `pathlib`/`OSError`/`int` idiom, NOT cgroup semantics) names **three** independent `/proc/self/cgroup` readers — `cellcgroup:29`, `coord_sample:43`, `cpuweight:64`. Verdict for the peak fix itself: **reuse `write_peak`, author nothing**. **No file edited this tick.** |

| 50 | 2026-09-10 | Σ-F12 · wrong cgroup | ⚑⚑ **THE OBSERVE CHANNEL MEASURES THE WRONG CGROUP — and my t49 reading was too generous.** I said the observe pass "did not exercise the heavy path"; measured, it is systematic. **`bnd-delta`: store says 4.6 MB, the build needed 128 MB — 28×**, and the **highest peak across ALL 53 boundaries claims is 4.8 MB**. Fifty-three claims capped at ≤4.8 MB while one demonstrably needs 128 MB is not sampling error. **Cause, from the two owners**: `calc.bzl:_peak_snippet` reads `/proc/self/cgroup` — **the action SHELL's** cgroup — while `_cap_prefix` runs the payload via `cgroup-scope … --` in a **CHILD scope created per rung** (the `mb-14-…-<uuid>.scope` in every OOM line); `cellcgroup.peak_bytes()` likewise reads `own_cgroup()`. **The reservation is learned from the shell while the work runs in a child.** ⚑ **This SUBSUMES Σ-F11c**: no number of observe→harvest→project iterations converges, because each re-measures the same wrong scope — the loop is not slow, it is converging on a different quantity. ⚑ Explains the seeded 256 surviving: paper/library's ~215 MB rows come from the def grid (`pk_eval`, a different action shape); the file channel has never produced a large number for anyone. **NOT FIXED — owner call**, 3 options priced (have `cgroup-scope` write the peak it owns / drop the child scope and lose the kill boundary / accept the ladder as the mechanism and stop calling `mem.json` a reservation). ⚑ Nothing is broken — the ladder rescues every under-reservation; the cost is 173 retries in one `boundaries` build. |
| 49 | 2026-09-10 | Σ-F11 · the pipeline, run properly | **4 MANIFESTS DERIVED FROM THE STORE** — `--config=memobserve` → `mem_harvest.py` → `mem_project.py`, after verifying the safety property AT SOURCE rather than from prose (twice burned here): ⚑ `deposit` is **monotone and the DATABASE enforces it** — `ON CONFLICT … SET bytes = max(bytes, excluded.bytes)`; a partial harvest can only RAISE. Store **125 → 189 observations, 2 → 6 projects**. ⚑ **Σ-F10 confirmed by measurement**: the four new projects peak at **~5 MB** vs paper/library at **~215 MB** — a real ~40× gap, so `file = 8` is a reading and the seeded `256` was ~50× over-provisioned. ⚑ **`mem_project --check` CAUGHT MY tick-45 `cp` AS STALE** ("GENERATED, never authored") — and the difference was real: `cp` carried two overrides at 4 from a warm partial run, the store's monotone max resolved all six `arch` claims to 8. **The merge did what it exists for.** ⚑ **Σ-F11b: `mem.json` is NOT delivered by the filegroup** — `guide`/`boundaries` never list it, yet boundaries' 53 cells now generate at `mem = 4|8`, **zero at the floor**; the repo rule reads it at FETCH time. So the `"mem.json"` line I added to `arch/BUILD.bazel` at t47 is harmless but wrong-headed — I generalised Σ-F5's staging lesson to a file that arrives by another route. ⚑ **Σ-F11c: `file = 8` is TOO LOW for some claims** — `bnd-delta` climbed 8→16→32→64→**128 MB** (75s), 173 retries total. **Loop mid-convergence, not a defect**: an observe pass measures what THAT run touched, the ladder rescues the rest, the next harvest records it and the max keeps it. Needs a second iteration until `--check` is clean and the climb count stops falling. |
| 48 | 2026-09-10 | Σ-F9 · mem population | **"ELEVEN MISSING" WAS WRONG, AND `cp` IS THE WRONG PROCEDURE — nothing installed.** Re-derived from MODULE.bazel: **7 projects HAVE a manifest** (paper, root, library, guide, talk, render, arch — I had counted guide/talk/render/root as missing), **3 CAN gain one** (boundaries, config, demo), **3 CANNOT** — no `calc` ⇒ no `pk_calc` ⇒ no peaks ⇒ **no `:mem_learn` target exists** (setup, report, image). Σ-F1's count came from listing four directories, which is the census-over-the-wrong-population error `mem_converge.py`'s own docstring names. ⚑⚑ **The pipeline already exists and I was bypassing it**: `git log guide/mem.json` → the `Τ·mem·learn` commit states **observe → harvest → project**, where `mem_harvest.py` **MERGES never replaces** because *"a warm build re-executes few cells, so overwriting a manifest with a partial harvest DELETES measurements an earlier pass established"*. **My tick-45 `cp` from `bazel-bin` skipped harvest and project entirely** — harmless for cold `arch`, destructive for a project with prior measurements. ⚑⚑ **Σ-F10 — AND THAT WARNING WAS BACKWARDS, corrected within the tick.** I said the committed 256s were "real measured values". Three lines refute it: **six of seven say `file = 256` EXACTLY** across structurally unlike projects (a measurement does not do that); **`git show 8dc9868` gives guide/talk/render the IDENTICAL blob `e1b0174`** — a template, not three observations; and ⚑ **the STORE settles it — `mem.sqlite` holds 125 observations for exactly TWO projects** (paper 81 rows / max 226 MB, library 44 / 205 MB → 256 is their next power of two), with **guide, talk, render and root at ZERO rows**. So `file = 8` is a **32× improvement over a seed**, not a regression. `boundaries` confirms it is systematic: `{"file": 8, 23 claims at 4}` over 52 claims. The merge warning stands only for paper/library (125 real rows); it never applied to the four with none — which is what I conflated. ⚑ `mem_converge.py` surveys GRID projects only, so those seeds were outside every check. ⚑ **Σ-F9b: `mem_converge.py` reports a FALSE "library NOT CONVERGED / def=MISSING"** — the manifest HAS `def: 64`; the checker builds the path from the repo suffix (`:68`, `"%s/mem.json" % proj`) and `library/` no longer exists after the staged rename. **Third occurrence of `@paperkit_X` ⇒ path `X`** (Β-F1, Μ-F3, this), and its own `at-floor=0` contradicts it. Its header already says why it survived: **`Ζ·mem·unwired` — nothing runs it, so nothing would notice it breaking.** |
| 47 | 2026-09-10 | Σ-F8 · watch fix | **FIXED — and it was ANOTHER over-cautious deferral, the THIRD** (Ι-F1 t22, Σ-F3 t42, this). Two independent lines of evidence, both in the file: ⚑ **the block's OWN comment promises it** (*"watching the projection invalidates exactly when a RESERVATION changes"* — a manifest APPEARING is a reservation changing), and ⚑ **the unguarded form is already the idiom in the same file** (`:590` watches the warrant with no `.exists` test; `paper.toml` at `:564` is guarded because it is genuinely optional — `mem.json` was guarded like an optional input while behaving like a must-watch one). **Change**: `watch(memp)` moved OUTSIDE the `.exists` test. **Measured**: `mem = 0 ×6` → **`mem = 8 ×4, mem = 4 ×2`**, and ⚑ **ZERO cells start at the 4MB rung** (was every cell); per-claim overrides resolved correctly through `_membucket`'s ladder. **5/5 discrimination**, all three directions since a fix that always-invalidates is as wrong as one that never does: creation takes · the 4MB rung gone · a CHANGE takes (`[77]`) · **REMOVAL falls back to the floor** (`[0]`, no stale value) · restored. `lint_bzl` clean. ⚑ **Scope confirmed by counter-example**: `@paperkit_boundaries//:gate` still ladders from 4MB — no `mem.json`. The fix makes a manifest EFFECTIVE, it does not create one, so **Σ-F1's ten remaining projects are now unblocked follow-on** rather than blocked on a generator defect. |
| 46 | 2026-09-10 | Σ-F8 · marker proof | **THE DIAGNOSIS IS NOW PROVEN, AND I HAD IT HALF-WRONG.** t45 asserted *"a repo rule cannot be invalidated by the CREATION of a file it never watched"* — ⚑ **wrong as a statement about Bazel**: `repository_ctx.watch()` (8.7.0) explicitly supports non-existent paths, so watching one DOES catch its creation. A finding naming the wrong law is worth less than none, so I tested it. ⚑⚑ **The MARKER FILE settles it**: `@+bib+paperkit_arch.marker` lists `paper.toml` and `warrants.bib` and **NO `mem.json` line**, while `@+bib+paperkit_library.marker` **DOES list it** — same generator, same code path, opposite outcome, decided solely by whether the file existed when the rule last ran. `bibtex.bzl:618` guards the call (`if memp.exists: watch(memp)`), so **the guard is the defect, not the platform**. ⚑ It also explains what t45's reading could not: a probe modifying an EXISTING `mem.json` (content change — Bazel digests, so `touch` proves nothing) ALSO failed to re-run the rule; under "creation isn't watched" that is unexplained, under "the path is absent from the marker" it is expected. ⚑ **A second defect, MINE**: `arch/mem.json` arrived `-r-xr-xr-x` because I `cp`'d it from `bazel-bin` where outputs are read-only (the library's is `-rw-rw-r--`) — the probe hit `PermissionError` before testing anything. **An install step that copies a build output must restore a writable mode.** Fixed. Owner's call unchanged but now exactly priced: one line, `watch(memp)` OUTSIDE the `.exists` test. |
| 45 | 2026-09-10 | Σ-F7 · mem manifest | **THE GATING PREMISE WAS TRUE OF ONE PROJECT AND I STATED IT OF ELEVEN.** Re-derived: `bibtex.bzl:786` emits the def-resolution grid **only under `emerge`**, and **only 3 projects declare it** (`paper`, root, `paperkit/library`) — two already have a manifest. ⚑ So **ten of eleven are single-resolution and Χ's collision cannot arise there**; it gates `root` alone. ⚑ The shape is also smaller than assumed — the library's manifest is **one override row out of 43 claims**, and `file` (256) needs **MORE** than `def` (64), inverting Χ's assumed direction. **Generated a real one**: `--config=memobserve @paperkit_arch//:mem_learn` → `{"claims": {arch-projects: 4, arch-two-pk-grade: 4}, "file": 8}`, single resolution as predicted; and confirmed Χ-F7 (a default build writes the sentinel `0` — verified by reading the peak — and `mem_learn` returns `{}` rather than a false floor). ⛔ **Σ-F7b: THE MANIFEST DID NOT TAKE, refuting my prediction.** Installed, staged, rebuilt — the ladder still starts at 4MB and the generated BUILD still says `mem = 0`. **Cause read from source**: `if memp.exists: repository_ctx.watch(memp)` — ⚑ **a repo rule cannot be invalidated by the CREATION of a file it never watched.** The generator handles a manifest that CHANGES and is blind to one that APPEARS, which is every one of the eleven. **Not forced** — a repo re-fetch spans all 13 projects and would regenerate `paper`'s 52,584 targets. **Owner's call, one line**: `watch(memp)` unconditionally (the standard idiom) vs manifests being a create-once step. |
| 44 | 2026-09-10 | Σ-F5 · arch stage + widen | **TWO MORE SITES; the graph run named a failure I did NOT predict.** ⚑ **(a) `@paperkit_arch//:gate` FAILED — my own project from t38.** Six claims RED, ONE root cause: `"ARCH.md not built — run paperkit-project"`. The `out` document exists on disk and the gate passes on the HOST, but it was never listed in `//arch:files`, so the sandbox never saw it — **Μ-F1's lesson, recorded at t30 and repeated by me at t38.** `talk/BUILD.bazel` states the rule I needed: the `out` IS listed (it is what `≡ projection` compares), further-derived artifacts are not. ⚑ `Executed 3 of 16 tests` was **not a shrunken graph** — the same log says `Analyzing: 27 targets`; Bazel **aborted at the first failure**. Re-running with `--keep_going`. ⚑⚑ **(b) `rnd-widen` — I had it WRONG as "sandbox vs host site-packages".** `_deps_absent()` exists and knows Pillow, but `main` branches on `--selftest`/`--deliverable` **before** calling it — Σ-F4's exact structure, fourth site. **And this shape is WORSE than an unguarded import**: both halves DETECTED the absence and said so loudly (*"SKIP (loud)"*, *"DELIVERABLE unmeasurable"*) **and returned a failing exit anyway** — the honest account and the dishonest verdict in the same record, the correction printed beside the error. `latex.py` at least crashed visibly. Fixed; verified the guard does NOT fire on the host, where `--selftest` still PASSES with real measurements (5956 twips). ⚑⚑ **Σ-F6: `arch/` PARTIALLY FIXED, then ⛔ BLOCKED on a design question.** Staging `ARCH.md` made `invariants` PASS (`≡ projection`, `--without-K` 6 distinct); declaring **`reads = {.}`** (the mechanism `boundaries/` uses on 26 of 54 entries) took **4 of 6 claims GREEN**. Two remain `baseline: false, sens: []` — failing UNMUTATED, the `vacuous` shape. **The cause is the CLAIMS, not the staging**: both assert facts about the WHOLE REPOSITORY from inside a sandbox that stages a subset, so no `reads` fixes them. ⚑ My first repair of `arch-projects` was ITSELF unverifiable (`rglob` for every `paper.toml`, asserting `on_disk > wired` — impossible where the files are deliberately unstaged); rewritten to assert the DECLARATIONS and the prose corrected to match. **3 options priced** (reads-everything / `mechanical = false` / retier to `local`); I lean `mechanical = false` — *"the repository has N projects"* is a fact about the CHECKOUT and a hermetic sandbox is not the checkout — but it changes what the gate guarantees, so it is an **owner call**. |
| 43 | 2026-09-10 | Σ-F4 · latex tier-exit | **FIXED — and Σ-F3's CENSUS WAS INCOMPLETE.** I had enumerated callers of `describe_links` (four); the real population is pikepdf **IMPORTERS**, and `--binding pikepdf` finds three more — all **function-local** imports a caller search cannot see (`latex._selftest:170`, `pdf._formula_alts:89`, `pdf._link_count:115`). `pdf.py`'s two were already covered by t42's entry guard; `latex.py` was not. ⚑ **Its shape is sharper: the `Ζ·tier·exit` guard ALREADY EXISTED in `main`, and `--selftest` branched ABOVE it** — so the one path importing pikepdf directly was the one path that never consulted the roster. **Two gaps fixed**: (1) `_deps_absent` checked lualatex/pandoc/2 `.sty`/veraPDF but **not pikepdf** — ⚑ *a dependency missing from the roster is a dependency whose absence lies*; (2) the guard now runs first for both paths — ⚑ a selftest is a ⟨P,F,δ⟩ proof of the METHOD, so one that "passes" without the method's tools is the `vacuous` grade this repo refuses. **Measured**: `rnd-latex` fail → **cannot-run**, and ⚑ **`rnd-a11y-latex` SURFACED as cannot-run — a sixth consumer masked behind `rnd-latex`'s crash**. ⚑ **`rnd-bib` verified NOT a defect**: `PYTHONPATH=<repo> checks/bib.py` → "bib ok"; `PAPERKIT_PYTHONPATH` alone does not work (the engine's runner reads it, the bare script does not). **One genuine red left in render**: `rnd-widen` (sandbox ≠ host site-packages; Pillow IS installed, selftest PASSES on host). |
| 42 | 2026-09-10 | Σ-F3 · tier-exit | **FIXED — and my tick-41 "owner's call" was OVER-CAUTIOUS.** Re-examined: `Ζ·tier·exit` is a **named contract already implemented across `render/`** — `linkalt`/`mathalt` guard `pikepdf is None` in their own `main` → rc 3, `pdf.main` **already had two `return 3` cannot-run exits** (one literally "the route's toolchain is unavailable"), and `verb.bzl:160` maps `rc 3 → cannot-run` with a comment naming *"the render checks return 3"*. So this was an **omission in 2 of 4 consumers**, not a policy question — the same error as Ι-F1, pricing options for what the tree settles. Guarded at the **ENTRY POINTS** (not in `describe_links`: a callee sentinel would need re-interpreting by 4 in-module callers; `main` keeps ONE verdict owner). **Measured, the gate's own words**: `rnd-a11y`/`rnd-pdf` went from `{"verdict":"fail", … AttributeError}` to **"UNRESOLVABLE … NOT a refutation"**. **8/8 discrimination** — all four consumers exit 3 and AGREE, both guards test the real import, `verb.bzl` mapping verified not asserted. ⚑⚑ **AND IT CASCADED INTO THE VPAT**: `rnd-wcag`/`rnd-wcag-entail` previously read *"its veraPDF validator FAILS — cannot back a Supports"*, now *"disclose **Not Evaluated**, not Supports (conservative)"* — **a false `fail` was propagating into the accessibility disclosure.** Remaining render reds all environmental/pre-existing (latex: pikepdf; widen: sandbox ≠ host site-packages, Pillow IS installed; bib: standalone PYTHONPATH, green under Bazel). |
| 41 | 2026-09-10 | Σ · hook (full graph) | **FIRST FULL-GRAPH RUN SINCE `arch` JOINED (t38)** — every tick since verified claims in isolation, which cannot catch an integration failure. **Integration confirmed at the phase that would have failed**: Loading clean (no Starlark error), **`Analyzing: 27 targets` — exactly `hook_grid`'s derived count** — then 645 actions over 104 packages / 75,797+ targets. `arch/`'s repo generates, its gate+adequacy resolve, Μ.1's conditional `:genres` survives the real graph. Per-project `:invariants` green as they landed (demo 1, config 4, guide 9 claims, each "--without-K … distinct"). ⚑⚑ **Σ-F1: ELEVEN OF THIRTEEN PROJECTS HAVE NO `mem.json`**, so every cell climbs **4→8→16→32→64MB — four killed processes before one survives** (19 OOM retries in the first ~70 actions). Only `paper/` and `paperkit/library/` carry a manifest. ⚑ **The discriminating evidence is in the SAME run**: when execution reached `paper/` and root, **the ladder stopped** — same machine, same action kind, only the manifest differs. This is the **Χ thread's subject seen LIVE rather than inferred**: `mem_learn` already classifies cells, `bibtex.bzl:920` feeds it file-calcs only, and the retry ladder makes it correct-but-expensive, which is why nobody noticed. **Not fixed** — needs a `--config=memobserve` sweep (must not race this run), and Χ's per-claim × per-resolution key question still gates the manifest's shape. **VERDICT: 26 of 27 green, `@paperkit_render//:gate` FAILED** (8,248 processes, 5,481 cache hits). Nine reds inside it, **not one cause**. ⚑⚑ **Σ-F2 (FIXED, MINE): `rnd-units` — 65 committed vs 66 projected.** The `genre-declared-gated` claim from t29: **rule 8's reach is wider than I applied it** — `paper.md` is not the corpus's only projection; `render/assets/paper-units.tsv` is a SECOND one and I regenerated only the first. The other three units files were clean, which is the discriminating evidence. Regenerated 65→66, all four now `≡ segmentation`; written by a SCRIPT, since the redirect `units.py` suggests is composition the toolchain refuses. **Rule 8 amended in practice: regenerate EVERY projection of a corpus, not just `out`.** ⚑ **Σ-F3: the same missing `pikepdf` is `cannot-run` for 2 claims and `fail` for 2 others** — `linkalt.py:34-37` guards it "in main", but `describe_links` is called from `a11y_own.py:73` and `pdf.py:63`, which bypass main (**2 of 8 call sites cross-module**). The tristate collapse the repo refuses everywhere else. ⚑ **CORRECTS my Β-F3 reading**: `rnd-widen` says "Pillow absent" but **pillow 12.1.1 IS installed and the selftest PASSES on the host** — it fails only in the sandbox, which stages the engine not site-packages. Two different failures I had merged into "toolchain". Owner's call: guarding changes what render's claims REPORT. |
| 40 | 2026-09-10 | Ρ · bnd-env-facts | ⚑⚑ **THE LEDGER'S OWN ENVIRONMENT BLOCK WAS 4/5 STALE** — the block every tick reads FIRST. "NINE hook-set projects" → **TEN** rooted / **13** wired; "110 claims" → **115**; "exceeds 600s" → **2700s** AND misattributed to nine projects when `render` alone is the cost (Β-F3 — so the ledger contradicted its own findings section); "~61s" → that is a **COLD** sweep, warm is **~0.1s**, a ~600× gap. Only "setup/report/image undeclared" survived. **Corrected inline, originals struck through (rule 6)** — then GATED, because prose corrected by hand goes stale again. `bnd-env-facts` re-derives the three figures with a single owner (MODULE.bazel, each `paper.toml`, the warrants list) and checks the prose matches. ⚑ **It does NOT pin the numbers** — a project added reds the gate, the prose is corrected, green returns: **the red is the notification**. ⚑ **Figures, not prose** — claim-ifying 3,659 lines of log would repeat Λ-F1 (316 words vs 27 KB); and it scans **only** the Environment block, because the tick log is append-only history where a **dated RECORD is not a stale FACT**. **6/6 discrimination**, incl. ⚑ deleting the sentence rather than correcting it also REDS, so a figure cannot be silently un-gated. ⚑ My pattern failed once first — required `wires 13 projects` adjacent, but markdown **wraps**, so it accused the prose of a defect that was its own blind spot (Μ-F3's shape, third occurrence). `BOUNDARIES.md` 4560 words ≡ projection. |
| 39 | 2026-09-10 | Μ · bnd-generator | **LANDED — audit finding 1 closed, and the PROJECT was refuted before building it.** ⚑ The plan's only stated reason for a separate `graph/` was `boundaries/` inheriting `adequacy=false`; **Ζ set `adequacy = True` at tick 4**, so the reason is gone and `boundaries/` already hosts all three generator claims. Λ-F1's lesson applied one tick later: measure whether a plan step is still right before executing it. **`bnd-generator` gates three declaration→target rules** over 13 projects: `adequacy=True` guards the adequacy record (10 of 13), `emerge=True` guards cohere (3 of 13), and **`:invariants` is unguarded and carries `--without-K` at any tier** — the argument Α wired report/image on, which nothing checked. ⚑⚑ **Μ-F3: the witness ACCUSED THE GENERATOR TWICE AND WAS WRONG BOTH TIMES** — a 14-line scan window (the real guard sits **47 lines** up) and one spelling taken for the concept (`if emerge and …` reads a LOCAL, not `repository_ctx.attr.emerge` — **Β-F1's shape exactly**). Both were my instrument, not `bibtex.bzl`. ⚑ **Μ-F4: the probe then caught two MORE at 5/6** — `"--without-K" in bzl` was too weak (the string occurs **twice**, so removing it from the command left it green; now reads the `inv = ` assignment) and a right-verdict-wrong-cause (tier guard CAUGHT but reported as `emerge`; now names `proj_tier`). After: **6/6**. `BOUNDARIES.md` 4453 words ≡ projection; `bnd-components` 85 files, no new drift. |
| 38 | 2026-09-10 | Λ · arch | **LANDED — new project wired, gated, in `//:hook`.** `gate arch` **PASS, 6 claims**; `hook_grid` **13 projects / 29 targets**; `bnd-check` PASS with `paperkit_arch` graded. Audit finding 2's three false assertions are now claims that COUNT from the owning manifest. ⚑ `arch-components` and `arch-modules` are separate claims because **"eight" was the COMPONENT count** — a bare 8→12 refresh would have preserved the category error. ⚑⚑ **Λ-F1: the plan's "convert ARCHITECTURE.md to a projection" DELETES IT** — six claims project to **316 words** against a **27 KB** document. **And I learned this by DOING it**: `--check` had already reported the difference, I ran the WRITER "to measure", it overwrote the file; restored via `git checkout`, verified clean. The writer is destructive by design. Resolved with `out = "ARCH.md"` — prose keeps its narrative and GAINS gated counts beside it. ⚑ **Λ-F2: §3.6 is MIXED, not un-claim-shaped** — 1 judgement, 1 still-true (two `pk_grade` rules), and **2 already FALSE** (report scope, on-demand tiers) that went stale silently. Their retirements are now GATED, so they red if either tension returns. ⚑ **Λ-F3: the counting witness earned its place INSIDE its own tick** — `arch-projects` was authored at 12, wiring `arch/` made it 13, and the witness caught it before the gate. Two more gates fired correctly: `arch-two-tiers` (arch on disk but unwired) and `hook_grid` (both members missing — **third recorded instance** of the class `BUILD.bazel:114-119` documents). `bibstruct --roundtrip` 0 of 6 unparsed; ARCHITECTURE.md unmodified. |
| 37 | 2026-09-10 | Β-F3 · cost, measured | **THE REGENERATION FAILED AGAIN (2700s, exit 124, ZERO bytes) AND BOTH MY COST MODELS WERE WRONG.** t35 said "300s × 11 gates" — refuted, all gates total **80s**. t36 said "~61s × 9 Δ sweeps ⇒ ≥10 min" — refuted twice over: 9×61=549s **fits** in 2700s, and measurement now shows `_delta` is **~0.1s per project** (7 of 9 timed: paper 111 claims, boundaries 52, library 43 — each a tenth of a second, cache warm). **Δ is not the cost at all**; I over-estimated it as badly as I had over-estimated the gates, in the opposite direction. ⚑ `-u` also refuted my BUFFERING story: zero bytes unbuffered means `gen.py` emits nothing until it finishes **by design** — every generator runs before any write or print. ⚑ The "~61s" environment note is `paper` **with a warm cache**; assuming it generalised to all nine is Β-F1's shape again (a value true for one member taken for the set). **ATTRIBUTED**: `render` is the ENTIRE cost — eight projects total ~18s (`talk` 17.7s, the rest 0.1s each), `render` **exceeds 240s and does not finish**. ⚑ **And the 0.1s figures are CACHE HITS, not speed** — `discriminate.py` prints *"all 24 grade(s) reused from footprint cache"*; `render`'s cache is cold. The note's "~61s" is a COLD sweep of `paper`, the 0.1s is a WARM one, and I had been quoting one for the other. ⚑⚑ **AND IT IS NOT EVEN `render` — IT IS ONE CLAIM.** Completed trace: 30/34 @ 35s, then 31 @ 136s, 32 @ 150s, 33 @ 164s, then **>116s on the LAST claim alone**. ⚑ My "~3 claims" reading was ALSO wrong (31→32 and 32→33 were **14s each**, not 100s) — the finer measurement refuted the finer guess. **Named by `--only`**: **`rnd-ocr` 98s**, `rnd-pdf` **5s**, `rnd-docx` **5s**. ⚑ **The TOOLCHAIN hypothesis is REFUTED** — I predicted all six converter-shelling claims would be slow; `pdf` and `docx` are 5s. It is **OCR specifically**, one claim. ⚑ **Β-F4: `rnd-pdf` grades `broken`** — attributed per rule 9, the only uncommitted change under `render/` is **Γ.1's `root = ".."`**, which is what made `render` gradable AT ALL. So it is not newly broken, it was **previously UNMEASURABLE** — Γ working as designed, and a real finding: a `broken` claim inside `//:hook`, more urgent than the cost. **The report cannot regenerate here without a warm `render` cache — INSTRUMENT, not asset drift**; `rpt-reproducible` owns it. ⚑ **Γ.2 held a SECOND time** — assets clean after a 45-minute kill. |
| 36 | 2026-09-10 | Λ · re-derive + asset regen | **RE-DERIVATION IS THE DELIVERABLE; regeneration in flight.** Launched `report/gen.py` under a 2700s budget (`-u`, so the next timeout is diagnosable — tick 35's 900s run produced *zero* bytes). Cost now exact rather than guessed: `delta_md` calls `_delta` for **all 9 graded projects** (~61s each) and `dag_svg` once more, so ≥10 min is structural, and Γ.2's generate-all-then-write means the asset NAME cannot narrow it. ⚑ **Λ's blocker list was STALE and I checked instead of inheriting it**: Β (t35) and Η (t6) are landed, and **Ε does NOT gate Λ** — Ε is `bibstruct` dropping `claim` on LaTeX-brace entries (still live: 2 of 27), but `ARCHITECTURE.md` has **no LaTeX**, only 2 lines containing `$HOME` in prose. Λ is **READY**. ⚑ **Audit finding 2 measured from its owners**: "17 modules" → **26** non-test files (83 total, 57 tests); "eight projects" (stated **3×**) → **12** wired, 14 `paper.toml` on disk. ⚑ **"eight" IS the COMPONENT count** — the prose conflated components with projects, so a counting witness must name WHICH count it asserts; a bare number-refresh would preserve the category error. Λ not started: it is a new project, and starting one while a Δ-sweep run holds the machine violates the no-concurrent-sweeps rule. |
| 35 | 2026-09-10 | Β · doc-identity | **LANDED — A2-F2 closed, and it was WORSE than recorded.** Reproduced first: 12 documents, **two named `library`** (live + a gitignored stale wheel copy). ⚑⚑ **Β-F1: the duplicate was the visible half — the report's TABLES DISAGREED ABOUT ONE DOCUMENT.** Three components, three names for it: `_all_docs` → `library`×2 (`d.name`), `_wired_names` → **`paperkit/library`** (MODULE.bazel `project=`), `_hook_names` → `library` (BUILD.bazel regex). So `_wired_names` produced a name `_all_docs` could never match, and the concept library was **simultaneously reported ON-DEMAND** (`_ondemand_names = {library}` — it is `emerge=True`, adequacy-graded, in `//:hook`) **and GRADED TWICE**. Fixed by keying on the **repo-relative path** — the identity MODULE.bazel already uses: `_all_docs` returns `rel`; `_hook_names` reads the **repo→project map from MODULE.bazel** instead of assuming `@paperkit_X` ⇒ `X` (true for 11 of 12, silently false for the twelfth — `Ζ·hook-rot`'s shape); `_ignored` consults **`git check-ignore`**, the authority, and ⚑ falls back to walking everything **and says so** rather than applying an unverifiable exclusion. After: 11 docs, no duplicate, `_ondemand_names` **EMPTY**, `_graded` 9 rows each once; `distinct.py` → "9 document(s) … paperkit/library". **7/7 discrimination** incl. the collision CLASS — a fresh `graph/render` beside `render` coexists, the exact shape Phase D creates, so Λ/Μ are unblocked from the hazard rather than patched around it. ⚑ Case 6 first FAILED and **my TEST was wrong** (probe nested under `demo`, correctly excluded by the fixture filter). `hook_grid` green; `gen.py --check gate.md` **RED by design** (asset says `library`). ⚑⚑ **Β-F2, and my first explanation of it was WRONG**: regeneration hit `timeout 900`; I blamed Β emptying `_ondemand_names()` and 300s×11 gates, then **timed every gate — 80s total, none over 120s** (slowest `render` 43s). The real cause, read from `main()`: the write path **ignores the asset name** — Γ.2's generate-all-then-write produces ALL four assets, two of which call `_delta` (a mutation sweep per project). The cost is Δ, not the gates. **Fourth wrong performance diagnosis on this thread, same shape: reasoning about what code should cost instead of timing it.** ⚑ Γ.2 HELD — `report/assets/` clean after the timeout, no partial write; the guard that protects the assets is also why a single-asset regeneration is unavailable, a deliberate trade. |
| 34 | 2026-09-10 | Ξ.2 · genre-census | **LANDED — the apparatus's thesis is now checkable** (52 entries, round-trips). *"Each genre is its own vantage"* is EMPTY if two produce the same partition — which is what `brief` was for a tick. **Measured: 36 of 36 pairs distinct**, disagreement **0.019–0.394**; `tutorial`/`quickref` most independent (they cut on grounding depth and text length, axes nothing else uses). ⚑ Over **PAIRS, not unit counts** — `staged` and `collection` both give 11 units and differ on 8.8% of pairs. ⚑ **No claim is foregrounded by every vantage** (8 of 9 open with `paper-is-projection`; `catalog` with `min-strength`, because "M" sorts there) — the absence of a fixed point is the honest result. ⚑⚑ **Ξ-F4: the census caught the LEDGER carrying a fact its own repair invalidated.** Ν-F1 recorded `brief ≡ staged` "at every γ" — true when measured, because γ was UNREACHABLE then; **Ι-F1 fixed that**, and they now differ by **0.051** at their own γ while identical at the same one (verified: `staged --gamma 4.0` → 15 units, = `brief`). A three-tick-old repair silently invalidated a recorded finding; only machine re-derivation noticed. ⚑⚑ **Ξ-F5: I wrote an UNFALSIFIABLE check inside the fix for one.** The γ-qualified "stale exemption" guard scored **4/5** — it could not fail, because an explicit γ overrides both declarations and both genres are the identity on the grouping: the equivalence is **ANALYTIC**. One tick after Ξ-F3 caught this shape, I reproduced it. Fixed by STATING it rather than testing a tautology; after: **5/5**. `BOUNDARIES.md` 4374 words ≡ projection, `bnd-components` 84 files no new drift, `grades.py` unchanged. Μ-F2 still the owner's one command. |
| 33 | 2026-09-10 | Ξ.1 · genre-pure | **LANDED — the surviving obstacle is now a FALSIFIABLE gated claim** (Phase F's deliverable). `boundaries_genre_pure.py` + `bnd-genre-pure` (**51 entries, round-trips**). Of 3 obstacle keys **2 were false** (`PK-GENRE-BLIND` retired by Κ; `PK-BIB-PROVENANCE` never true, Ξ-F1) — both survived because a verdict in prose is re-read, never re-derived. Two independent halves: no verdict-shaped name in the engine's **21-field vocabulary** nor any project's **7 consumer_fields** (`check` = DECLARED verifier, never its result), and `"delta": [… "project" …]` makes a project→delta import an **upward edge** `bnd-components` refuses. ⚑⚑ **Ξ-F3: MY FIRST WITNESS WAS UNFALSIFIABLE — 2/4.** It passed, then the probe lifted both obstacles and it **stayed green**: the exact defect it exists to prevent. **Half 1 read the wrong LAYER** — it censused PARSED records, but `bib.parse` projects onto `_SCALAR` and loud-drops the rest, so a `verdict` field can never reach one: **vacuous, not false**. Fixed to read the engine VOCABULARY + `consumer_fields`. **Half 2's logic was sound, my TEST was wrong** — the probe patched `"project": [` and hit the `COMPONENTS` file list (line 65), not the `DEPS` edge (line 210): **two tables, one key spelling**, the same trap `_claim_script` records one file over. After: **4/4**, each half reddening on its own lift. `BOUNDARIES.md` 4279 words ≡ projection; `bnd-components` 83 files, **no new drift** (new suite placed). Μ-F2 unchanged — still the owner's one command. |
| 32 | 2026-09-10 | Ν.3 · tutorial | **LANDED — and the pre-write check REFUTED FIVE OF SIX proposals.** `--check paper` → **9 registered, 4 built-in + 5 declared each INVOKED**; `--observe --genre tutorial` → **13 units, depths 0..12**. ⚑⚑ **Ν-F9**: scoring the survey's six remaining scripts on three axes (duplicate/collapse/degenerate) before writing — **cookbook ≡ `atomic`** (every cone distinct), **procedure ≡ `staged@γ=1.0`** — ⚑ **the PLAN'S OWN WORKED EXAMPLE**, which would have been a second `brief` had it been written from the plan instead of measured — and example-collection/effective/service-manual DEGENERATE at 99%/71%/100% (every claim is `sandbox`). **One probe refuted five files**; the Ν-F1 discipline compounding. `tutorial` reads `rests-on` through Κ's channel and groups by grounding depth. **7/7 discrimination**, the first load-bearing: ⚑ **no claim precedes its premise across all 88 edges** — the tutorial property, not merely a partition; unit 0 is exactly the **54** atoms; a 2-cycle terminates (a cycle is a POSTULATE); an out-of-corpus edge is ignored, not depth-0 padding. ⚑ Caught before running: `depths()` was called inside the per-key loop, recomputing 115×. ⚑ Μ-F1's lesson applied unprompted — script added to `//paper:files` in the same edit, since Μ.1 stages declared genre scripts. `paperkit-gate paper` PASS (111), `test_text_genres` 11/11. Μ.2 still BLOCKED (untouched — this tick edits no build-graph state). |
| 31 | 2026-09-10 | Μ.2 · bnd-genre-emit | **WITNESS LANDED, GATE RED, BLOCKED ON OWNERSHIP — the red IS the deliverable (rule 5).** `boundaries_genre_emit.py` + `bnd-genre-emit` (via `bibstruct --add --apply`, **50 entries, round-trips**) — audit finding 1's first repair: the generator's only prior claim was 3 regexes over its TEXT; this asserts its **OUTPUT**. ⚑ **A BICONDITIONAL, deliberately**: either half alone is satisfiable by a constant ("always emit" / "never emit"), so only the iff pins the rule. **1 declaring, 11 silent, 12 partitioned.** Reads the SOURCES not the Bazel cache (`hook_grid.py`'s precedent — a witness keyed on an output-base hash reports one laptop's cache as a fact about the generator). **5/5 discrimination** mutating `bibtex.bzl` and restoring. ⚑ First run was 5/5 with a **WRONG DIAGNOSTIC** — deletion reported as "UNCONDITIONAL"; `emission_state()` now returns **3** states, since *"no record" and "no constraint" render identically once collapsed* (`Ζ·rests·unresolved`). ⛔ **Μ-F2: `gate boundaries` → 5 FAILED.** Bisected: `bnd-components` finds my new test unplaced (**FIXED** in `components.bzl`) and **`genre.py → resolver.py`** live-only — mine, from Κ's `clean_env` import — plus `library/concepts.py` + 5 edges belonging to the **staged rename**. ⚑ **Did NOT run `dagbzl.py --write`**: it regenerates wholesale, folding the staged changeset's 5 edges in beside my 1 and making this tick the author of someone else's build-graph edit. 3 options priced; ⚑ option 3 (hand-edit one edge) **does not work** — `--check` compares against a full regeneration, so a partial edit stays stale. Owner's call. `BOUNDARIES.md` regenerated (4185 words, ≡ projection, rule 8), suite PASSES standalone, `hook_grid` green. |
| 30 | 2026-09-10 | Μ.1 · generator-emits-genres | **LANDED — Ν-F7's gap closed at the BUILD level.** t29 gated `paper/`'s genres with a claim (a fact about the corpus); now **`bibtex.bzl` emits `:genres` for any project declaring one**, and it is in `//:hook`'s gate. Audit finding 1 re-verified first: `bibstruct --field check` → **49 of 49**, `bnd-lint` the only claim naming a `.bzl`, and `lint_bzl.main` is a line-by-line regex asserting nothing about what the generator emits. Three edits, each on an existing precedent: `_declared_genres` parses `[genres.*]` (following `_claim_script`'s two documented traps), a `genres` attribute (following `witness` — **a repository_ctx cannot read paper.toml**), and a `pk_cmd` joining `recs` (following `:invariants`). ⚑ **Conditional**: `attr(name,"genres", boundaries+render+talk+config)` → **Empty** — an unconditional target would be 11 green-by-vacuity rows. ⚑ It runs `genre.py --check` rather than re-implementing totality in Starlark: **the generator's job is to WIRE the oracle, not be one.** ⚑ **Μ-F1: the first build went RED and the red was the measurement** — 4× `[Errno 2]`, because `//paper:files` is a hand manifest that never listed the genre scripts. The tempting fix (scan `cmd` for a `.py`) is exactly what `Ζ·entry·point` retired; inputs DECLARED in `paper/BUILD.bazel` instead (Α-F2's shape, one project over). After: `4 built-in + 4 declared cmd(s) each INVOKED`, **inside the sandbox** — first time the genre seam is gated by the build graph. `bazel test @paperkit_paper//:gate` **1 test passes**, 111 claims. ⚑ Open: no claim yet asserts the generator emits `:genres` **iff** a project declares one — verified by QUERY, not by a gate (the `graph/` project, plan D2). |
| 29 | 2026-09-10 | Ν-F7 · wire-the-check | ⚑⚑ **TICK 28's FIX WAS WIRED TO NOTHING, AND I REPORTED IT AS CLOSING A FALSE GREEN.** Two independent searches (BUILD.bazel, tools/bibtex.bzl, .githooks/pre-commit) find **zero** references to `genre.py --check` — it runs when a human types it. **Same shape as the defect it fixed, one level up**: t28 was a message asserting more than the check did; t29 is a check asserting more than the build runs (the `Ζ·hook-rot` class, audit finding 6 / Η-F2). Measured what actually gated the seam: `//:hook` reaches gate/adequacy/cohere/decisions, **not genres**; `claims.py:genre_declared_runs` exercises `run_declared` on **tempdir fixtures**, never the project's own declarations. **The wire is a claim** — `genre-declared-gated` (bib + witness), walking `registry(proj)` for `declared=True` entries and running each through `run_declared`, the same seam `--observe` uses. **6/6 discrimination** by MUTATING the real `paper.toml` and restoring in a `finally`: the `-Ichecks` bug, a missing file, exit 3, and a DROP all RED with naming diagnostics; unmodified passes before and after. **Rule 8 fired**: `--check` went red, regenerated to 5035 words (+2/−2), `transitive_reduction` moved 3 cross-refs (Γ-F4 behaviour). **Rule 9 checked**: `grades.py` → **111 claims, behavioral 81→82, imported 29, no broken** — Δ's sweep independently confirms the witness flips. ⚑ Open, named: no other project declares `[genres.*]` today, so the population is covered — a fact about the corpus, not the gate. General fix (emit a genre check per declaring project) is **Μ**'s territory. |
| 28 | 2026-09-10 | Ν-F6 · check-invokes | **FIXED — the false green is closed.** The defect was a MESSAGE ASSERTING MORE THAN THE CHECK DID: `if obj is None: … continue` tested a declared genre only for HAVING a `cmd` string, while the success line claimed *"every objective is total over the grouping"*. `--check` now INVOKES each declared `cmd` via `run_declared` (reused, so check and live path cannot diverge), and the message states the counts — **"4 built-in objective(s) and 4 declared `cmd`(s) each INVOKED"** — so a verified universal is distinguishable from an assumed one. **6/6 discrimination**, each case reconstructing a failure `--check` used to CERTIFY: the real `-Ichecks` bug, a cmd that DROPS, one that EXITS 3, one that INVENTS a key (all four previously **passed**, now RED with naming diagnostics); correct cmd still green; no-objective-no-cmd unchanged. ⚑ `claims.py:genre_gates_the_seam` inspected and deliberately NOT edited — it exercises `is_total` and the built-ins directly, never `--check`, so the change neither weakens nor strengthens it. `paperkit-gate paper` PASS (110). |
| 27 | 2026-09-10 | Ν.2 · quickref + catalog | **LANDED — both genres `PK-GENRE-BLIND` made impossible.** **8 registered** (was 6): `quickref` 3 units (31/48/35 length bands, terse first), `catalog` 23 units (alphabetical by significant term). Both read CLAIM TEXT where `serial` read structure, so Ν.1+Ν.2 cover both halves of Κ's channel. Ν-F1 novelty check ran first on both — neither is a built-in at any γ, and cannot be (γ moves bracketing; these cut across it on text). ⚑ **Ν-F4: the wedge said FACTOR** — `reuse_check --propose serial --against brief` gave **`main ∩ main = 23`, OVERLAP**, with 4 copies of one stdin loop about to exist. Lifted `checks/genrekit.py` (groups/records/field/emit/run + the protocol and D1 warning stated once); `brief` and `serial` refactored onto it, **11/11** confirming neither moved, tick 26's 5/5 re-run unchanged. ⚑ **Ν-F5: the stop-list IS the genre** — first-character keying indexes English grammar (**A=32, T=32 of 114**); skipping function words gives **largest unit 15**, top letters C/P/S/G. Measured BEFORE writing, so it was never written wrong. The `atomic`-collapse risk was tested, not assumed (3 singletons of 23). ⚑⚑ **Ν-F6: `--check` PASSES A GENRE WHOSE `cmd` CANNOT RUN.** I wrote `-Ichecks` thinking it adds an include path; `-I` is ISOLATED MODE → parsed as `-c hecks` → `NameError`. **`--check` reported all 8 total while two were broken** — it validates the registry, never executing a declared `cmd`; only `--observe` does. A green `--check` is NOT evidence a declared genre runs. Fix needed no flag: python puts the script's own dir on `sys.path`. `paperkit-gate paper` PASS (110). |
| 26 | 2026-09-10 | Ν.1 · serial | **LANDED — the first genuinely NEW genre.** Two files, no engine change: `paper/checks/serial.py` + `[genres.serial]`. **6 registered**; `--observe --genre serial paper` → **12 units for 12 warrant files**. ⚑ **The Ν-F1 check ran BEFORE writing this time and passed**: no built-in produces the by-source partition at any of 8 γ values, and the reason is structural — **2 of 12 files span multiple sections** (`model.bib`, `composition.bib`), so the file cut is not a bracketing of the section grouping and must MERGE across it (upward, like `_collection`, never a `_talk`-shaped split). First genre to read Κ's channel for STRUCTURE not text, and the tree's first consumer of `_src` — the field Ξ-F1 found had been on every record since parse time while an obstacle key claimed it was erased. **5/5 discrimination** (`--check` asserts only totality, which the identity also satisfies): live cut = by-`_src` partition · differs from every built-in at every γ · the 2 spanning files each land in ONE unit · an unsourced key keeps its own unit · no-records case honest. ⚑ **Case 5 corrected my DOCSTRING, not the code** — I wrote "degenerates to the identity", it degenerates to `atomic`; behaviour right, prose wrong, now fixed. γ deliberately not declared (it would be an inert dial — Ν-F3). `paperkit-gate paper` PASS (110). |
| 25 | 2026-09-10 | Ξ · re-verdict | **READ-ONLY; 3 of 4 residuals UNBLOCKED, 2 of 3 obstacle keys RETIRED.** Κ retired `PK-GENRE-BLIND` and left 4 residuals citing it — a stale BLOCKED reads as settled, so all four were re-verdicted against a measured field census (114 records through the real seam), not the plan's prose. ⚑⚑ **Ξ-F1: `PK-BIB-PROVENANCE` IS FALSE.** Every record carries **`_src = path.name`** (`bib.py:217`), and over `paper/` it gives **12 distinct sources for 12 declared bibs, 0 absent, identical after Κ's channel**. `F.update()` merges the DICTS and the loop var goes out of scope — so the control flow reads as erasure — but provenance is a FIELD ON THE DATA, written before the merge. **I reasoned about the code path and never looked at a record.** ⚑ Third consecutive finding of this shape (Ν-F1 wrong population, tick 19 `mem_learn` capability-exists): a PRESENT thing inferred absent from structure — the dual of standing rule 4. serial/issue-based UNBLOCKED, issue identity = `_src`, no engine change. **Ξ-F2: `PK-GENRE-PURE` STANDS** — `check` is on 110/114 but is the DECLARED verifier STRING, not its current result; troubleshooting needs current failure state, which `observe` cannot compute (the component lattice forbids importing the grader). Real and structural. `paperkit-gate paper` PASS (110). |
| 24 | 2026-09-10 | Ν.0 / Ξ-Q · γ sweep | **READ-ONLY MEASUREMENT, 3 findings, no tree edit but a docstring.** 5 genres × 8 γ over paper/ (114 claims); totality holds in every cell. ⚑⚑ **Ν-F1: `brief` ≡ `staged` at EVERY γ — I built a duplicate of a built-in.** Verified byte-identical CLI output, not just key-tuple equality. Tick 21's reuse check searched the wrong population (sibling SCRIPTS, none existed) and never compared the OBJECTIVE against the 4 built-ins — *assume-floor*, the wedge's own named anti-pattern. **Ι is still valid**: its deliverable was the first declared genre ever EXECUTED, and a duplicate objective is the IDEAL pilot (known-good oracle). Kept as the declared-seam regression fixture with the equivalence now DECLARED in its docstring. **Ν-F2: the loose-leaf control is a MISS** — `collection` at γ=0.0–1.0 gives 10–11 units whose largest holds **42% of the corpus**; loose-leaf wants many small units, so it is a REAL RESIDUE, not an existing form. **Ν-F3: Ξ-Q partial** — `staged ≡ collection` only at γ≤0.2; `atomic`/`talk` are γ-invariant BY CONSTRUCTION (`_atomic` discards bracketing, γ only moves bracketing). Not one continuum: the discriminating axis is **what the objective READS** (bracketing vs claim text), not γ. `paperkit-gate paper` PASS (110). |
| 23 | 2026-09-10 | Κ · records-channel | **LANDED — `PK-GENRE-BLIND` CLOSED**, the obstacle 4 residual genres collapsed onto. Records go to the subprocess as **JSONL in a temp file**, path in `PAPERKIT_GENRE_RECORDS`; each choice made against a measured alternative (a FILE because 62,579 paths hit ARG_MAX in tick 19; JSONL because `structured-not-flat`; an env var because `_ENV_KEEP_PREFIX` already allow-lists `PAPERKIT_` and a new positional arg would break `cmd` templates). **Optional by construction** — stdin byte-identical, the 3 shipped fixtures untouched. **6/6 discrimination**, the decisive one: ⚑ **a DECLARED genre reproduces `_talk`'s budget cut exactly, `[['a'],['b','c']]` both ways** — parity on the objective that DEFINED the obstacle. ⚑ That case first passed on WEAK evidence (52 words, under the 84-word budget → both sides made no cut); re-fixtured to 50+50 so the budget bites, rather than reporting the trivial agreement. ⚑ **Κ-F1: the docstring claimed env sanitization it never performed** — `subprocess.run` passed no `env=`, so a declared genre ran with full ambient env (`LD_PRELOAD`, `PYTHONPATH`, relative `PATH` resolving to the gated project). `--calls clean_env` → 11 calls, **0 from genre.py**. Fixed by making the claim TRUE, not by deleting it. `paperkit-gate paper` PASS (110), `boundaries_env` PASS (6/3). |
| 22 | 2026-09-10 | Ι-F1 · toml-scope | **FIXED, and my tick-21 framing was wrong.** I priced 3 options and called it an owner decision; the tree settles it — I had not read `GAMMA`'s declaration or `claims.py:gamma_is_reachable`. `GAMMA = Param(…, config="gamma", default=None)` means *"whatever the genre asks for"*, and a **PASSING gate** asserts γ *"must be REACHABLE, not frozen into each genre"*. **Two γ parameters share one spelling**: `[paper] gamma` = project-wide OVERRIDE, `[genres.X] gamma` = the genre's DECLARED DEFAULT that it overrides — so refusing the latter made the former's documented behaviour unreachable. Option 3 would have contradicted a passing gate; pricing it unchecked is the error worth keeping. **Fix: `bib._SCHEMA_TABLES = frozenset({"genres"})`** — exemption by TABLE OWNERSHIP (`genre.registry` owns `[genres.*]`, schema `{what,cmd,gamma}`), never by key name. `[checks.*]` deliberately NOT exempt. **Verified by discrimination 7/7**: all 3 recorded faces still refuse, and ⚑ `gamma` under `[checks.X]` still refuses — the exemption keys on the table, not the name. γ now measurably live: **16 units at γ=4.0 vs 14 at 1.0**. `paperkit-gate paper` PASS (110 claims), `boundaries_check` PASS, `boundaries_toplevel` PASS. |
| 21 | 2026-09-10 | Ι · brief | **LANDED — the first declared genre ever EXECUTED.** Two files, no engine change: `paper/checks/brief.py` + `[genres.brief]`. `--observe --genre brief paper` → **14 units**, `brief.py` run as a subprocess through `run_declared`, `is_total` satisfied; `genre.py --check paper` → **5 registered** (was 4). Objective is the IDENTITY on the grouping — smallest non-built-in, so the risk isn't in the objective. `reuse-sppf-wedge` ran first: **no sibling exists**, so NOVEL by absence of corpus. `PK-GENRE-BLIND` demonstrated rather than asserted (keys-only stdin vs `_talk` reading `r["claim"]`). D1 visible in the output's leading section column. ⚑ **Ι-F1: the engine contradicts itself about `gamma`** — `bib._misplaced_paper_key` REFUSES it under `[genres.*]` (it is a `Param(config=…)` key) while `observe` reads `spec.get("gamma")` and `claims.py:896` ASSERTS it is carried. The fixture is green only because it calls `genre.registry(d)` on a tempdir, never `load_config` — so a green fixture asserts a declaration the engine refuses on every real project. 3 options priced, **not fixed**: needs an owner call. Shipped without `gamma` (default 1.0), contradiction recorded beside the omission. |
| 20 | 2026-09-10 | Θ · genre-docstring | **LANDED** (docstring only, +11/−1, no behaviour change). D1 verified at BOTH ends from source before editing — `genre.py:298` sends keys only, `project.py:639` prints a leading `section` column — so the docstring's *"the format is the one the CLI already prints"* was false and the round-trip trap is real: section labels arrive as keys and `is_total` calls them INVENTED KEYS, naming totality when the fault is a column offset. Fixed the PROSE, not the protocol (a section label is not a claim key). Verified `--source run_declared` (body byte-identical), `boundaries_check.py` **PASS 7/1**, `genre.py --check paper` → 4 registered. ⚑ **Ι's premise SHARPENED, and it is weaker than the plan assumed**: `claims.py:884` tests REGISTRATION only — `cmd` is compared as a STRING against a tempdir fixture and `brief.py` is never executed, so **the gate passes today with the file absent**. Nothing in the tree executes a declared genre against a real project. |
| 0 | 2026-09-09 | ledger created | ordering derived, loop armed |
| 1 | 2026-09-09 | Α · wired-scope | LANDED; 3 findings; promoted Γ to blocking |
| 2 | 2026-09-09 | Γ · tristate-delta | LANDED; 3 findings; 7 projects gained a Δ root |
| 3 | 2026-09-09 | — (overlap) | NO-OP. `coherence.py paper --json` (pid 909361) + its `discriminate --resolution def` sweep (909393) in flight. Standing rule 2. This is the EMERGENCE run Γ unblocked — the answer to Δ-F3 — so waiting IS the work. |
| 19 | 2026-09-09 | Χ-F9/F10 · already built | **THE CAPABILITY EXISTS; ONE LINE OF DATA FLOW DOESN'T.** `mem_learn.py:36-54` already classifies grid cells (`if "__" in stem → def`), and its docstring IS `Ζ·mem·def·blind` recording that fix as made; `mem_harvest.py:40-65` rglobs every `.peak` into sqlite keyed by `(res, claim, cell)`. **`bibtex.bzl:920` passes file-calcs only** — which is why tick 15's run emitted `{"claims": {}}`. ⚑ **Operator's question answered, my framing corrected**: the identifiers ARE opaque and the manifest DOES separate resolutions at top level (`{'def': 64, 'file': 8}`, no collision). The gap is narrower — **per-claim × per-resolution**: `prose-projected` wants `file=8, def=64`, an 8× spread, in one unkeyed `claims[]` slot. **Latent, not active** (0 rows today; both equal their defaults). ⚑ Hard constraint found: 62,579 peak paths exceed **ARG_MAX** (`errno 7`), and `mem_learn` reads `sys.argv` — so the fix needs a param-file or the directory-walk shape `mem_harvest` already uses. |
| 18 | 2026-09-09 | Χ-F8 · grid peaks | **Χ'S GATING QUESTION ANSWERED.** Built the 2,203-cell grid under `--config=memobserve` and censused 991 `.peak` files: **730 measured, 261 zero (stale pre-observe action key), 0 malformed**. **Grid cells peak at mean 37.3 MB / max 39.2 MB; the file-calc is the MINIMUM at 5.3 MB.** So both sources measure and the grid measures ~7× more — sizing def cells from file-calc peaks under-reserves, which is the exact failure `calc.bzl:139-144` says the cell peak channel was added to fix. **The channel exists; `mem_learn` just doesn't read it** (`bibtex.bzl:920` aggregates file-calcs only). ⚑ Reframes Χ: not "delete the file-calc", but "teach `mem_learn` to read the cells" — refused by `Ζ·mem·def·blind` on cost grounds Χ-F5.1 already refuted (2,203 cache hits, 6.8 s). ⚑ Own measurement error recorded: `-exec cat {} +` CONCATENATED peaks (no trailing newlines), producing `36098048373760000`; nearly filed as corrupt data. |
| 17 | 2026-09-09 | Χ-F7 · observe | **CORRECTED TICK 16.** The `0` peak is a **declared sentinel, not a degraded measurement**: `calc.bzl:148` writes `echo 0` unconditionally when not observing — the peak is never READ. `.bazelrc:130-132` states the intent and makes the flag part of the action key. **Measured under `--config=memobserve`: the file-calc peak reads `5292032` (5.3 MB)** where the default wrote `0` — so Χ-F5.3 ("the file-calc's peak is also 0, neither source feeds the manifest") and Χ-F6's inversion are BOTH WRONG. ⚑⚑ `Τ·mem·observe·honest` records my exact misdiagnosis as a prior incident: *"170 cells read 0 and the diagnosis was a kernel capability gap; the real cause was a cached non-observe write."* **A `0` from an instrument that is TURNED OFF is not a measurement of zero** — I applied `absence-is-a-reading-about-the-instrument`'s vocabulary while never asking whether the instrument was on. Grid-cell peaks under observe: measuring (2,203-cell rebuild in flight). |
| 16 | 2026-09-09 | Χ-F6 · peak diagnosis | **RESOLVED the gating question.** The `0` peaks are **structural, not this machine**: the host probe says `usable` and a live cgroup reads 6.8 GB, but the SAME probe under `linux-sandbox`'s mount set (**no `/sys`**) returns **exit 3, UNUSABLE — "no v2 ancestor whose cgroup.subtree_control lists memory"**. So `PK_CAP` is empty in every sandboxed cell (`calc.bzl:124`), the payload runs outside the measured scope, and `write_peak` reads `0` — a SUCCESSFUL read of an uncharged cgroup, distinguishable from its `"unavailable:unreadable"` failure string. ⚑ **Inverts a Χ-F5 premise**: "the cells carry no peak" is not a difference between grid and file-calc — **neither carries one** under the default strategy. Needs one `--config=memobserve` run (the config the manifest is designed for) before any removal. |
| 15 | 2026-09-09 | Ε · roundtrip | **BLOCKED ON OWNERSHIP — measurement is the deliverable.** `bibstruct.py` is **staged-added** in substrate (`A `), inside a very large uncommitted changeset; standing rule forbids touching it. ⚑ **Ε-F1: true scope measured corpus-wide for the first time — 3 of 455 entries, ALL in `paper/`** (3 of 114 there; **0 of 341** across the other 16 bibs), confined to the one project carrying LaTeX math. Considered and did NOT build a paperkit-side roundtrip gate: it would (1) introduce an **undeclared cross-repo dependency on an uncommitted file** — the Ω class, worse than the `uv` case `Ζ·wheel·backend` retired — and (2) be RED TODAY on 3 unfixable-here entries, so it would need a **ratchet baseline**, which is a design with absent-vs-empty semantics, not a guard. Actionable instead: file to substrate via `summit`; build the gate once `bibstruct` is committed and clean. |
| 14 | 2026-09-09 | Ψ.2-F8 · Kron | **RESOLVED.** Not Krohn-Rhodes, not Kronecker — **Kron/Schur node elimination**, `series_schur(a,b) = a·b/(a+b)`, implemented 4× in the jea Python (`jea_onegraph.py:59`, `jea_circuit.py:66`, `jea_picircuit.py:46`, + `sql_lift.py:367` — lifted into SQL). ⚑ **Same operation as `GValueAsQ.gand` (F6) and gcalculus's degree-2 `eliminate` (F5): three repos, one operation**, with the ledger asserting `series_schur == el-atlas g_eff`. Instrument finding: my `grep` found 11 files and I read it as code; three structural readers said 0 and were RIGHT — every hit is markdown. The concept is documented under `kron`, implemented under `series_schur`. `pycodemod --attr` is retired and REFUSES rather than answering falsely. |
| 13 | 2026-09-09 | Χ · action-decomposition | **ATTEMPTED AND REVERTED — the revert IS the deliverable.** Wrote Χ-F3's scoped change (verdict from `__dcalc` where a grid row exists), then found it orphans `mem_learn`: `bibtex.bzl:920` depends on every `__calc` for its **`peak` output group**, and `Ζ·mem·def·blind` (`:905-911`) records why depending on grid cells instead is economically inverted (**41,468 deps on one action**; *"the measurement must not cost what it is meant to save"*). ⚑ **Χ-F4: my Χ-F3 measurement was right and my conclusion was wrong** — I had already measured that `mem_learn` reads the peak output group, recorded it as *evidence of redundancy*, and read "does not read the JSON" as "does not need the target". `git diff --stat tools/bibtex.bzl` → empty. Verified BEFORE running anything. |
| 12 | 2026-09-09 | Ψ.2-F2 · tristate | **FIXED.** `discriminate.py` carries `reachable: false` beside `baseline` (the `decisions_unasserted` model — orthogonal key, present only when it applies); `read_grade.py` reads it with `absent ⇒ reachable`. 5/5 properties verified end-to-end through the real script: grades AGREE (`broken` both ways — names the gap, never moves the rung), baselines DIFFER, unreachable no longer claims "repo is not green", refuted unchanged, legacy records unaffected. ⚑ `pycodemod --binding` caught a missing import before anything ran. Closes the false statement `grade.py:86-92` records as measured twice. **Ψ.2-F7**: operator corrected F6(2) — the name is likely **Kronecker**, and it is in the **jea PYTHON** (11 files, incl. `jea_circuit.py`, `numpy_law_bridge.py`), not the Agda. My agent searched the wrong name in the wrong tree; that negative is a fact about its reach, not the ecosystem. |
| 11 | 2026-09-09 | Ψ.2 · granularity census | **CORRECTED TICK 10**: the gate IS inert (I never checked what `//:cohere`'s exits read — none is a function of `grade`); only `scope_residual`'s reported number moves, downward, safely. **Ψ.2-F2**: the `UNREACHABLE` tristate collapses at the calc boundary — `grader.py:500` overwrites the string with the raw verdict, `discriminate.py:252` serializes `False` and `UNREACHABLE` both to `0`, `read_grade.py` cannot pass `reachable=`. Live path sound for `broken` by luck of falsiness; verified on `bnd-wheel__calc.calc.json`. My Ψ-F1 edit made it VISIBLE, did not cause it. **Ψ.2-F3**: `STRENGTH` is an unguarded quotient (ties `existence`/`indeterminate`, omits `broken`) — `--min-strength existence` and `grade.below("existence")` DISAGREE; the owner is exempt from the ladder check it exports. **Ψ.2-F4**: `tier` = 3 names for 4 bits, sweptness decided elsewhere. **Ψ.2-F5**: gcalculus's star-mesh elimination is the model — answer/cost/route as three records, invariant stated and tested, reduction a RETRACT not a discard. |
| 10 | 2026-09-09 | Ψ.2 · granularity | **MEASURED, STOPPED at the judgement.** Operator reframed to the v4cat question (what axes exist / which are conflated); research agent dispatched on the full census. Settled the decisive sub-question directly: the coarse grade is **NOT inert** — 4 of 6 ∂² faces never read `grade`, but `sensitivity_residual` filters on `== "behavioral"` (coarse admits everything measured; fine would exclude `existence`/`imported`) and `scope_residual` tests `in ("vacuous","indeterminate")` where ⚑ **the coarse path can never emit `indeterminate`** — a dead arm, so one face measures different things per assembler. Precedent found in-file: `unmeasured_edges` is a conflation finding about itself, repaired by a NEW FACE, not a changed threshold. |
| 9 | 2026-09-09 | Ψ · sweep-in-action | **Ψ-F1 LANDED** (one line + its argument): `tools/read_grade.py` read `_grade_from_sens(...)["grade"]` and discarded **five of six fields**, so every build-graph grade record was a bare `{claim, grade}`. Now carries `tests`/`baseline`/`why`/`not_higher`/`not_lower`; verified on `bnd-clamp` (7-file fingerprint + all three justifications). ⚑ **Corrects Δ-F9**: `tests` IS the fingerprint, computed and dropped. Ψ-F2: measured the cost of the unconnected reading — 33 min on ONE asset, 4.5% CPU, 9 sweeps per asset, heartbeat swallowed by a pipe. Framing is the operator's: **construct once, read many** — `Ζ·calc·interp` already says so; `delta_md` was a third reading that re-ran the construction. Remaining two-thirds (the clamp reading) deferred: it changes what the report measures. |
| 8 | 2026-09-09 | Ω · report retiers | **Ω-F6 LANDED.** Probed one `fig:` warrant (`local`→`sandbox`: `1 local` → `1 linux-sandbox`, verdict OK), then retiered all six `fig:` warrants; verified together as **`6 linux-sandbox`**, all OK. **Ω running total: 7 warrants freed across 2 projects**, every one exempt from sandbox+cache+remote purely by inheriting a project default and needing none of it. The other 10 report warrants stay `local` — all Ω-F5-shaped (they reach sibling projects through `gen.py`, so execroot-relative), each needing its own evidence. |
| 7b | 2026-09-09 | Ω (cont.) | ⚑ **Ω-F5:** `@paperkit_image//:gate` is RED, and NOT from my retier — the 3 podman warrants fail because `pk_cmd` runs with cwd=**execroot**, so `podman build … .` copies Bazel's transient spawn-runner files instead of the repo. Verified SOUND from the source tree (`paperkit-gate: PASS`, exit 0). **`local` names a placement; the constraint is a build-context path, which `local` cannot express** — Ω's thesis, measured. Three exemptions compounded to hide it: `tier=local` → hook-exempt → never run → breakage invisible. Corrects Α's "host-coupled" justification for `image`. |
| 7 | 2026-09-09 | Ω · tier-is-a-placement | **PARTIAL, by design.** Ω-F3 LANDED: `img-hermetic` retiered `local`→`sandbox` per-warrant; verified hermetic (footprint target now emitted, verdict `pass` under `linux-sandbox`) — one warrant was exempt from sandboxing+caching+remote purely by inheriting a project default and needed none of it. Ω-F1: **I retracted my own claim** that `stable.sh` conceals a network dep (base is digest-pinned, proof image COPY-only) and corrected the reason string in `hook_grid.py`. Ω-F2 BLOCKER: `toolchain` tier for the 3 podman warrants would cache against a fingerprint with no PODMAN key — worse than `local`; needs an owner call on stamp scope. Ω-F4: `img-pinned` reads `../Containerfile.base`, so retiering it needs the sandbox-staging question measured first. |
| 6 | 2026-09-09 | Η · hook-grid (H3) | **LANDED.** `tools/hook_grid.py` + pre-commit wiring; 25 members reconcile with `bazel query`. Η-F1: the 3 `local` exemptions exist in NO code — declared explicitly with reasons rather than inferred from `tier`. ⚑ Η-F2: `bnd-check` was scraping **24 of 25** members (non-greedy regex stopping at `[[wiki-ref]]` in a comment) and reporting PASS — a green measuring the scrape; fixed in both files. 7/7 discrimination cases correct. |
| 5 | 2026-09-09 | Η (STOPPED) + Ε (diagnosed) | **Η blocked on an OWNER DECISION**: the plan's design conflicts with `bnd-check` BY CONSTRUCTION (it set-equality-asserts member shape `@w//:(gate\|adequacy\|cohere\|decisions)$`, which `:all` cannot satisfy) — three options priced (H1/H2/H3), recommendation H3, not acted on. Then **Ε diagnosed and re-targeted**: NOT a paperkit bug — `bibstruct.py` drops `claim` on 3 entries carrying LaTeX braces, while paperkit's own parser reads them fine. Cross-repo tool defect, filed not patched. Standing rule 10 added. |
| 4 | 2026-09-09 | Ζ · boundaries-adequacy | **LANDED, RED BY DESIGN.** 45/49 swept sound, 4 `broken` with 4 DIFFERENT causes. 1 was my own incomplete edit (caught by `bnd-check`, fixed by wiring the hook member); 1 needs an owner decision; 2 are the staged changeset's. Audit finding 4 CLOSED. Two wrong inferences retracted (`_body` and the 102-action worry). Δ-F9 revised: two ledger shapes, not one. |
