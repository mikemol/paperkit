# paperkit — architecture & per-file index

A maintainer's map of the repository: what every tracked file is for, what it consumes,
what consumes it, and how the whole thing fits together. Assembled from a full per-file
read (158 tracked files: 68 Python, 14 `.bazel`, 6 `.bzl`, 11 `.bib`, 10 `.toml`, 9 `.tsv`,
10 shell). This document is a plain reference — unlike `README.md` and `paper/paper.md`, it
is *not* a gated paperkit projection.

---

## Part 1 — The one idea (read this first)

**A paper is a projection of a verified claim-DAG.** Every distinction in the repo is a
consequence of taking that sentence literally and recursively:

- A **claim** is a `.bib` entry (`@misc{key, statement=…, from=…, check=…, rests-on=…}`).
  A project's `warrants.bib` is a DAG of claims.
- **project.py** *projects* the DAG into prose (README.md, paper.md, …). The prose passes
  the gate *by construction*.
- **gate.py** *verifies* the prose against four invariants (RESOLVE / COVERAGE /
  without-K / PROJECT). A claim's `check` is a verifier string (`file:` / `cmd:` /
  `result:` / `agree:` / custom).
- **discriminate.py** *grades* each check by **falsifiability**: can the check actually
  fail? (mutation testing over the engine). This is the Δ machinery.
- **coherence.py** reads the **boundary of the boundary** (∂²): does a project's declared
  structure match its measured sensitivity?

Everything else is either (a) the engine that does those four things, (b) the Bazel layer
that turns the bib into a build graph and runs it as local CI, or (c) one of eight
**projects** (any directory with a `paper.toml`) that instantiate the idea for a
different domain.

---

## Part 2 — Per-file index

### 2a. Engine core (`paperkit/`)

Modules form a strict import DAG (recorded as data in `dag.bzl`). Leaves are pure; CLIs
sit on top. Each module puts its own dir on `sys.path` and imports siblings by bare name,
so it runs both as a script and as a Bazel-staged `.pyc` closure.

| File | Purpose | Consumes | Consumed by |
|---|---|---|---|
| `bib.py` | Single source of truth for the `.bib` warrant grammar + data model (one entry = one claim). `parse()` returns full records; consumers project fields. | stdlib; reads `paper.toml`, rubric `.tsv`, `.bib` | coherence, discriminate, footdeps, gate, project, rhetoric; mirrored by `tools/bibtex.bzl` |
| `config.py` | Ω·config — the one resolution pipeline: arg > `PAPERKIT_*` env > `paper.toml` > default. Registry (`REGISTRY`) is data, so every knob is enumerable. | stdlib, `os.environ`, config dict | discriminate, gate, grader, layout, project, resolver; config-project checks; tests |
| `grade.py` | Μ·grade — pure grade LADDER + interpretation (rungs, clamp/strength/corroboration orders, flip-set→grade). No engine imports, so a grade can be *read* cheaply. | stdlib | discriminate, grader, `checks/readme.py`, `tools/read_grade.py`, paper checks |
| `mutate.py` | Ζ·mutant — pure AST perturbation leaf (drop def body→uncatchable raise, drop/inject import). Loud on a spec naming nothing. | stdlib (`ast`) | grader; `tools/calc.bzl` (`pk_mutate`), sites/sens/eval |
| `layout.py` | Project file TOPOLOGY — which files Δ may read/corrupt, where the sandbox roots (`$HOME`-or-above refusal), which nested dirs are OTHER projects. | stdlib, `config`, filesystem | cache, grader, `boundaries_sandbox`, paper checks |
| `resolver.py` | Check-RESOLUTION core: verb registry (`file:`/`cmd:`/`result:`/`agree:`/custom), env sanitization (`clean_env`, sshd-style default-deny + PATH pin), footprint tracing via strace. | stdlib, `config`; subprocess→`gate.py` (`result:`) | gate, grader, footdeps, many tests, paper checks |
| `rhetoric.py` | Rhetorical-scheme layer: names inter-clause MOVES + gates each section against a declared SCHEME (rubric col 3). Imports `bib` not `project` (breaks the old cycle). | stdlib, `bib` | project (`MOVES`), coherence test, paper checks |
| `cache.py` | Δ grade CACHE — content hashing + on-disk `.delta-cache.json`. A grade is a pure function of a check's read footprint over a global engine EPOCH. | stdlib, `layout` | discriminate, `boundaries_degrade` |
| `driver.py` | Domain-free liveness driver for pump()/parse() witnesses — advances a resumable witness in budgeted steps, persists a token. Slow-but-sound reads as "resume me." | stdlib, `--state` file | discriminate (`D.drive`), `boundaries_driver`, paper checks |
| `project.py` | The PROJECTOR — emits prose from the claim-DAG: orders by `from`, weaves glue/MOVES, renders non-adjacent `rests-on` as per-target cross-refs, places `emit:` assets + `depth` proof steps, LaTeX→Unicode. Output passes the gate by construction. | stdlib, `config`, `bib`, `rhetoric` | gate (`P.project`), readme/paper checks, render `plain.py`, report gen, several tests |
| `gate.py` | The VERIFIER — four invariants (RESOLVE closed transitively under `rests-on`, COVERAGE, `--without-K`, PROJECT). Also the Ζ·starlark leaf/node oracle for Bazel. | stdlib, `config`, `bib`, `project`, `resolver` | discriminate, resolver (`result:`), readme/paper checks, image entrypoint, report gen, Bazel `--only` |
| `grader.py` | The Δ GRADER — the mutation SWEEP: binary-split group-testing over mutation sites in a throwaway sandbox to find a check's sensitivity set. Holds resumable `GradeWitness`. | stdlib, `config`, `resolver`, `layout`, `mutate`, `grade` | discriminate, paper checks, `tools/calc.bzl` def-sweep |
| `discriminate.py` | Δ CLI + report — grades each check on the discrimination ladder (vacuous/existence/behavioral/indeterminate/imported); orchestrates footprint cache, mutation sweep, per-claim/per-mutant Bazel oracles, effective-grade clamp. A facade re-exporting from cache/grader/grade. | stdlib, `config`, `bib`, `gate`, `driver`, `cache`, `grader`, `grade` | coherence (subprocess), `tools/calc.bzl`+`grade.bzl` (`--only`/`--calc`), report gen, tests, paper checks |
| `coherence.py` | ∂² reading — declared-vs-measured residual across four faces (STRUCTURE/SENSITIVITY/GROUNDING/EMERGENCE). Advisory, not a hard gate. | stdlib, `bib`; subprocess→`discriminate.py` or cached calc `.json` | `boundaries_coherence`, paper checks, `tools/verdict.py cohere` |
| `footdeps.py` | Ζ·foot — projects the per-claim dep manifest (`footprints.json`) from live Φ footprints (strace→dep tokens), audits each claim's declared `reads`. Feeds Bazel `data` without stracing at fetch. | stdlib, `bib`, `resolver`; git, strace | `tools/grade.bzl` (`pk_footprint`/`pk_footaudit`), `tools/verdict.py`, `tools/calc.bzl` |
| `dag.bzl` | Ξ·dag — the engine import DAG as a Starlark dict (`IMPORTS`), AST-derived by `tools/imports.py`. Each `pk_pyc`'s deps = its imports. Never hand-edited. | nothing (static data) | `paperkit/BUILD.bazel`, `tools/calc.bzl` |
| `BUILD.bazel` | Declares engine as explicit `ENGINE_SRCS` (no globs), `:engine`/`:pyc` filegroups, `exports_files`, one `pk_pyc` per module mirroring the import DAG. | `tools/calc.bzl` (`pk_pyc`), `dag.bzl` (`IMPORTS`) | every project gate; downstream `pk_pyc` consumers; `bibtex.bzl` |

**CLI entry points** (`main`): coherence, discriminate, driver, footdeps, gate, project,
rhetoric, mutate. **Pure libraries** (no `main`): bib, cache, config, grade, grader,
layout, resolver.

**Import DAG** (authoritative, from `dag.bzl`): leaves `config`, `bib`, `mutate`, `grade`;
`layout→config`; `resolver→config`; `rhetoric→bib`; `cache→layout`;
`project→bib,config,rhetoric`; `grader→config,grade,layout,mutate,resolver`;
`gate→bib,config,project,resolver`; `footdeps→bib,resolver`; `coherence→bib`;
`discriminate→bib,cache,config,driver,gate,grade,grader`.

### 2b. Top-level build / config / front-door

| File | Purpose | Consumes | Consumed by |
|---|---|---|---|
| `README.md` | Front door AND a paperkit projection of the root `warrants.bib` (`out=README.md`). Each paragraph cites its warrant. | projected from root bib/rubric/toml + `assets/*` | `checks/readme.py rm-selfhost`, root `:gate` |
| `warrants.bib` | The root README project's claim-DAG (`rm-*` keys); every example is a cited claim that also emits its asset. | parsed by `bib` | project/gate/discriminate/coherence/rhetoric, `bibtex.bzl`→`@paperkit_root`, `checks/readme.py` |
| `rubric.tsv` | README section order/titles (COVERAGE gate; opt col-3 scheme). | TSV | project, gate, rhetoric, discriminate/coherence |
| `paper.toml` | Root project config; declares custom `[checks.claim]`=`python3 checks/readme.py {target}`. | TOML | every engine CLI on root; `bibtex.bzl`; project marker for `layout` |
| `mem.json` | Learned memory-bucket manifest (Τ·mem): per-claim/per-resolution RAM reservations → Bazel `resource_set`. | JSON | `tools/bibtex.bzl`, `tools/calc.bzl`; `boundaries_jobs` |
| `checks/readme.py` | Per-claim discriminating witnesses for README (`claim:` type); each asserts its claim against real engine behavior → Δ behavioral. | stdlib, engine `gate/project/grade`, `tests/_fixture`; reads engine source + assets | `paper.toml [checks.claim]` (via gate/discriminate) |
| `BUILD.bazel` (root) | Hand-kept root infra (Ζ·sunset): `:files` manifest + `//:hook` local-CI test_suite. Per-claim graph is GENERATED by `bibtex.bzl`. | root files, `//tools:*.bzl`; generated `@paperkit_{root,paper,boundaries}` | `.githooks/pre-commit`; `bnd-check` |
| `MODULE.bazel` | Bazel module root: hermetic Python toolchain + the `bib` module extension (`bibtex.bzl`) that projects each `warrants.bib` into a check repo. | `rules_python`; each project's bib | Bazel resolution; `//:hook` |
| `.bazelrc` | Invocation config + sandbox profiles: `memobserve` (cgroup peak learning), `mutant` (hermetic linux-sandbox), `mutant-oci` (container from proof image). | `//tools:observe`, proof image | `.githooks/pre-commit`, Containerfiles |
| `Containerfile.base` | Κ·image — pinned toolchain base (digest-pinned python-alpine + strace + bash), isolating the non-deterministic apk layer. | `python@sha256:…` | `Containerfile`, `.bazelrc mutant-oci` |
| `Containerfile` | The proof object as an immutable, byte-reproducible image (COPY-only atop base). `podman run` re-verifies the paper hermetically. | base image, `image/entrypoint.sh` | manual `podman build`; hermetic gate |
| `.githooks/pre-commit` | Local CI: `bazel test //:hook --config=mutant` via mise. Never lands the repo broken. | git, mise, `//:hook`, `mutant` profile | git (when `core.hooksPath` set); `rm-ci` witnesses it |

### 2c. Bazel tooling (`tools/`)

The Bazel-native reframing. `bibtex.bzl` (a module extension + repo rule) reads each
`warrants.bib` at *fetch* and generates a `BUILD.bazel` of typed check rules; those rules
live in the `.bzl` files below and all emit a JSON `{verb, verdict}` **record** via the one
authority `verdict.py`; `//:hook` runs each project's `gate`/`adequacy`/`cohere` as thin
`sh_test`s wrapping `assert_pass.sh`.

| File | Defines / Purpose | Consumed by |
|---|---|---|
| `bibtex.bzl` | The GENERATOR — `bib` module extension + `bib_repo` repo rule. Reads bib/toml/mem.json at fetch, writes a BUILD instantiating all pk_* rules (verbs, calc/verdict/grade, the emerge mutation grid, cohere, gate+adequacy+footaudit, proof/witness). | `MODULE.bazel` `bib.project(...)` for boundaries/config/paper/root/setup |
| `verb.bzl` | `pk_file` (EXISTS), `pk_cmd` (EXECS), `pk_result` (PARSES sibling verdict), `pk_agree` (CONCURS ≥2 producers), `pk_gate` (aggregate→verdict). | generated project BUILDs; `verb_demo` |
| `grade.bzl` | `pk_grade` (mutate-flavored), `pk_grade_claim` (one claim via `discriminate --only`), `pk_adequacy` (≥behavioral floor), `pk_footprint`/`pk_footaudit`. | generated adequacy/foot targets; `pi_demo` |
| `calc.bzl` | The calc/interp split + mutation grid: `pk_calc` (cached sweep→`{baseline,sens}` w/ `resource_set`), `pk_pyc`/`pk_mutate`/`pk_eval`/`pk_sens`, `pk_mem_learn`, `pk_cohere`, `pk_verdict`, `pk_grade`, `pk_mutant`; providers `PycInfo`/`ObserveInfo`; `observe_setting`. | generated calc/emerge targets; `calc_demo`; `paperkit/BUILD.bazel` (`pk_pyc`) |
| `witness.bzl` | `pk_witness` (claim as build artifact iff `holds` exits 0, consuming premise witnesses), `pk_proof` (building it proves the paper). | generated compose targets; `witness_demo` |
| `verdict.py` | The one `{verb,verdict}` record authority + every oracle (`emit`/`exists`/`agg`/`agree`/`calc`/`cohere`). Kills format drift. | default `_tool` for most pk_* rules |
| `assert_pass.sh` | `sh_test` reading a verdict record → exit 0 iff `"verdict":"pass"`. | the `gate`/`adequacy`/`cohere` members of `//:hook` |
| `eval.py` | Runs one check off the `.pyc` closure with exactly one module's bytecode swapped for its mutant → flip? | `pk_eval` |
| `sens.py` | Aggregate per-site eval flips → sensitivity set; loud if the ∅-baseline flipped. | `pk_sens` |
| `sites.py` | Every perturbation site of a module `(module, spec)` = def-drops + absent-import injects. | `bibtex.bzl` `_surface` |
| `def_sites.py` | Def/method def-sites of a `.py` (mirrors `grader._def_sites`). | `sites.py` |
| `imports.py` | Module's engine-internal import edges via AST — projection the build DAG is built from. | `sites.py`, `closure.py`; regenerates `dag.bzl` |
| `closure.py` | Per-claim engine-module closure roots + file/content toggle sites for the mutation grid. | `bibtex.bzl` `_closures` |
| `pyc.py` | Compile one `.py`→`.pyc` with PEP 552 `UNCHECKED_HASH` (content-addressed, reproducible). | `pk_pyc` |
| `read_grade.py` | Read a `pk_calc` record → grade via pure `grade._grade_from_sens` (grade as a reading, not a re-measure). | `pk_grade` |
| `mem_learn.py` | Project `mem.json` from observed cgroup peak-RSS files, delta-encoded, pow2-bucketed. | `pk_mem_learn` |
| `lint_bzl.py` | Ξ·lint — fail if any `.bzl` embeds bare `python3 script`, printf-JSON, or grep-parsed JSON (invoke-don't-embed). | root `:files`; `bnd-lint` |
| `pyinfo.py` | Prints `sys.executable` + version (which interpreter ran). | `tools:pyinfo` py_binary |
| `BUILD.bazel` | Exports tool scripts/`.bzl`; `//tools:observe` build-setting; `pyinfo`. | generated BUILDs; root `:files` |
| `{calc,pi,verb,witness}_demo/` | Removable, hand-written demos of each rule family (the only hand-written `.bzl` load-sites). Not in `//:hook`. | standalone `bazel build` |

### 2d. Engine test suite (`paperkit/tests/`)

Each `boundaries_*.py` is a self-contained `⟨P, F, δ⟩` script (minimal pass, minimal flag,
minimum delta) wired as a `cmd:` check in `boundaries/warrants.bib` and listed in
`ENGINE_SRCS`. Many share `_fixture.py`.

- `_fixture.py` — the one validated minimal-project builder; runs engine `main()`s
  in-process (`entry/project_text/gate/gate_json/discriminate`). Also read by
  `closure.py`/`bibtex.bzl` to map `fx.<helper>`→engine CLI.
- `boundaries_discriminate.py` — the largest: all Δ grade kinds, provenance, determinism,
  pulse, compose invariance, `_grade_parallel`≡`GradeWitness`, def-resolution loud guard.
- `boundaries_grounding.py` — gate resolves the transitive `rests-on` closure of the cited
  set (sectionless grounded nodes gated; cycles terminate; dangling fails; target-independent).
- `boundaries_footprint.py` — keystone: read footprint ⊋ Δ sensitivity, so reads are the
  sound cache key. `boundaries_memoize.py` — the footprint cache (the only test that spawns
  a real subprocess). `boundaries_degrade.py` — strace-absent → `None` sentinel not `[]`.
- `boundaries_{agree,config,corroboration,driver,emit,env,gate_json,jobs,path,references,sandbox,target,without_k,coherence,check}.py`
  — one engine behavior each (see the boundary each names: agree verb, config precedence,
  corroboration axis, driver liveness, emit placement + `--safe`, env allow-list, `--json`
  fields, `--jobs` inertness, PATH pin, cross-ref rendering, sandbox home-guard, per-target
  citation, without-K proof-relevance, ∂² residuals, `//:hook` completeness).

### 2e. The eight projects (any dir with `paper.toml`)

Uniform shape: `paper.toml` (config + custom check types) · `warrants.bib` (claim-DAG) ·
`rubric.tsv` (sections) · a projected `*.md` (the `out=`, a build artifact) · `BUILD.bazel`
(a `:files` manifest, data dep of the generated `@paperkit_<name>` repo) · optional `checks/`.

| Project | What it verifies | Checks are… | Bazel-wired? |
|---|---|---|---|
| **root (README)** | The engine's own pitch/model/commands/resolver/Δ/layout/CI, each a cited claim; examples emit their assets (`assets/*`). | `claim:` (`checks/readme.py`) + `cmd:grep/python3` + `result:boundaries`. | yes — `paperkit_root`, in `//:hook` (gate+adequacy+cohere) |
| **paper/** | The 74-claim flagship "a paper is a projection of a verified claim-DAG" — projection, gate invariants, resolver, self-hosting, Δ adequacy, liveness, rhetoric, honest limits. The one project with a real `rests-on` grounding DAG + a nested `checks/fixture/` counter-project. | `claim:` (`checks/claims.py`, 77 witnesses against the *real* engine modules). | yes — `paperkit_paper`, in `//:hook` |
| **boundaries/** | 18 tool ⟨P,F,δ⟩ boundaries, asserted by running the engine's own `paperkit/tests/boundaries_*.py` (+ `lint_bzl.py`). | engine reuse (`cmd:python3 ../paperkit/tests/…`). | yes — `paperkit_boundaries`, in `//:hook` |
| **config/** | 4 claims: knob precedence, registry well-formedness, total CLI+env coverage, generated (non-drifting) knobs table. Drives the engine's own `config.REGISTRY`. | own logic over engine `config.py` (`checks/registry.py`, `gen_knobs.py`). | yes — `paperkit_config`, not in `//:hook` |
| **setup/** | 27 host-coupled claims about this machine's swap/memory stack; evidence = shipped `reference.json` + a bounded cgroup oversubscription experiment (`loadtest.json`). Structurally mirrors pump/parse. | own logic (`probe.py` ref/fresh, `experiment.py` load) — custom `ref:`/`fresh:`/`load:` types. | yes — `paperkit_setup` (`local=True`, unsandboxed), not in `//:hook` |
| **report/** | 12 claims that every doc passes the gate zero-postulate, Δ grades each claim, without-K is clean, + an accurate/accessible grounding-DAG figure. Every figure is live pipeline output, fresh-by-construction. | own logic + engine subprocess (`gen.py` ingests `discriminate/gate --json`; `figure.py`, `figure_checks.py`; custom `fresh:`/`fig:`). | **no** — on-demand |
| **render/** | 10 claims that the rendered artifact faithfully *presents* the paper: docx emit, plain-text agreement, OOXML structure, PDF glyph/heading/OCR/font fidelity, citation resolution, vector/legible figures. | own domain (pandoc/libreoffice/pdftotext/tesseract) reading `../paper/paper.md` + `../report/assets/dag.svg`; only `plain.py` reuses the engine. | **no** — on-demand |
| **image/** | 5 claims that the proof reproduces as an immutable, network-isolated, digest-stable container image that can serve itself. | own domain (`podman build/run` scripts + grep). | **no** — on-demand |

**Assets** (`assets/*`, root project): eight `emit=` example blocks (claim.bib,
commands.sh, delta-cmds.sh, enable-hooks.sh, grades.md, layout.txt, resolver.md,
resolver.toml), each placed verbatim into README.md and gated by a `cmd:grep`.

**Inter-project dependency DAG:** engine ← everything. README →`result:boundaries` (+ runs
paper's gate); report → ingests paper/README/boundaries `--json`; render → reads
`paper/paper.md` + `report/assets/dag.svg`; image → serves/gates the paper. paper,
boundaries, config, setup rest on the engine alone.

---

## Part 3 — Architecture analysis

### 3.1 Shape: a kernel, a generator, and instances
The repo is three concentric rings:
1. **The engine kernel** (`paperkit/`, 17 modules): domain-free, a strict import DAG,
   pure leaves under CLI facades. It knows only claims, projection, verification, grading.
2. **The Bazel generator** (`tools/`, `MODULE.bazel`, `.bazelrc`): turns each
   `warrants.bib` into a per-claim check graph at fetch and runs it as local CI. The bib
   *is* the build graph; there is no hand-written check target in the live path — only the
   root `:files` manifest and `//:hook` are hand-kept (Ζ·sunset).
3. **Eight projects**: the same four verbs (project/gate/grade/cohere) instantiated for
   eight domains, each supplying only its *domain logic* through custom check types. The
   engine never grows a domain; the project brings it.

This is the extraction thesis realized: paperkit is mat260's engine with the crypto
domain removed, and the eight projects prove the removal is clean — a paper, a README, a
render pipeline, a container image, a config registry, a machine-setup note, a boundary
suite, and a report are *all* the same machine pointed at different bibs.

### 3.2 The recursive spine (verification of verification)
The system stacks meta-levels, each the "boundary of" the one below:
- **gate** asks *does the check pass?*
- **Δ / discriminate** asks *can the check fail?* — mutation-tests the engine so a
  tautological or content-blind check is graded `vacuous`/`existence` rather than trusted.
- **coherence ∂²** asks *does the declared structure match the measured sensitivity?* —
  the residual between what the bib says and what the sweep finds.
- **boundaries/** asks the same of the *engine's own tools* (⟨P,F,δ⟩), and **report/**
  renders the whole ladder as fresh-by-construction figures.
- **paper/** is the system describing itself, its checks running the real engine; **README**
  is literally its own projection (`rm-selfhost`). Self-hosting is load-bearing, not a stunt:
  it is how the engine's claims about itself become falsifiable.

### 3.3 Data-first: every structural fact is enumerable
The recurring move is *make the structure data so it becomes a checkable claim*:
- the import DAG is data (`dag.bzl`), regenerated from AST (`imports.py`), driving `.pyc`
  closures;
- the config registry is data (`config.REGISTRY`), so `config/` can claim total coverage
  and a non-drifting table;
- the memory ladder is data (`mem.json`), so Bazel can bound concurrent sweeps;
- the footprint manifest is data (`footprints.json`), so Bazel `data` deps need no strace.

Consequences (caching, scheduling, resource bounds) *emerge* from the data rather than
being hand-tuned.

### 3.4 The Δ falsifiability engine (the crown jewel)
The deepest machinery is the grade. A grade is defined as a **pure function of the bytes a
check reads** (its footprint Φ), so it caches per-check over a global engine epoch
(`cache.py`) and never re-measures what didn't change. The measurement is **mutation
testing turned on the warrants themselves**: `mutate.py` perturbs an engine module,
`grader.py` binary-splits over mutation sites in a throwaway sandbox to find the check's
sensitivity set, `grade.py` interprets flips into a rung. The whole sweep is then **lifted
into Bazel** as a `pk_mutate`/`pk_pyc`/`pk_eval`/`pk_sens` grid (`calc.bzl`) so each
(claim,site) cell is a parallel, cached action. The keystone invariant
(`boundaries_footprint`): read footprint ⊋ sensitivity, which is *why* reads are a sound
cache key.

### 3.5 Trust boundary and reproducibility
Because a `check` can be an arbitrary program (`cmd:`), the resolver is also a security
surface: `clean_env` is sshd-style default-deny, PATH is pinnable (`PAPERKIT_PATH`), the
sandbox refuses `$HOME`-or-above, and footprints are straced. The `lint_bzl.py` invariant
(no logic/JSON embedded in `.bzl` strings) keeps that surface auditable. The reproducibility
ladder tops it off: a digest-pinned toolchain base → a COPY-only, byte-reproducible proof
image → a hermetic gate you can `podman run` offline. Verification thus reproduces from
source to container.

### 3.6 Tensions and rough edges worth noting
- **`discriminate.py` is a facade god-CLI**: it re-exports ~15 names from cache/grader/grade
  for API compatibility. The engine is modular by import DAG, but its two top CLIs
  (`discriminate.py`, `project.py`) concentrate surface.
- **Two `pk_grade` rules** exist (`grade.bzl` vs `calc.bzl`), never loaded together — benign
  but a naming collision that can mislead.
- **Report staleness**: `report/gen.py` discovers *all* `paper.toml` dirs, but the committed
  `REPORT.md`/assets cover only paper/README/boundaries. render, image, config, setup are
  newer and unrepresented — the report's "every document" claim is scoped narrower than the
  repo now is.
- **Two verification tiers by cost**: boundaries/config/paper/root/setup are Bazel-wired
  (fast, in or near `//:hook`); render/image/report are on-demand (heavy pandoc/podman).
  The split is deliberate but means the hook does *not* exercise the render/image/report
  presentation and reproducibility claims.

### 3.7 One-line summary
paperkit is a **self-verifying document engine**: a domain-free kernel that projects prose
from a `.bib` claim-DAG, gates the prose against that DAG, and grades each gate-check by
whether it can actually fail — with Bazel turning the bib into the build graph, mutation
testing turning the warrants on the engine itself, and a reproducible container closing the
loop. Its eight projects, including its own README and paper, are the proof that the kernel
is genuinely domain-free.
