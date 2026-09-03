# Μ·kernel·bounds — the engine's COMPONENT partition, the layer ABOVE Ξ·dag's module DAG.
# Declared ONCE here (pure literals — BUILD.bazel derives ENGINE_SRCS and the per-component
# filegroups from COMPONENTS; tests/boundaries_components.py guards it).  A component is the
# unit of OWNERSHIP for Μ·kernel: its behavior is certified by library concepts, and Δ cells
# scope their inputs to component cones (Μ·kernel·cells) so invalidation is component-local.
#
# DEPS is the ALLOWED import DAG between components (a component may also import within
# itself).  The guard asserts, against tools/imports.py's freshly derived edges: the
# partition is TOTAL and DISJOINT over paperkit's .py files, DEPS is acyclic, and every
# real import edge respects DEPS — so an import that crosses the architecture cannot land
# silently.

COMPONENTS = {
    "kernel": [
        "__init__.py",
        "config.py",
    ],
    # ⚑ Ζ·bib·parser — `bibparse.py` is `bib.py`'s GRAMMAR LEAF and belongs to the same component.
    # It is the recursive-descent parser `bib.parse` projects its records from; the edge is
    # bib → bibparse and it is INTRA-component, so it adds no DEPS entry.  The parser imports
    # nothing engine-internal (stdlib only), which is what keeps `model`'s existing
    # `["kernel"]` honest.
    #
    # ⚑ ITS ABSENCE HERE COST FOUR BATCH RUNS, and the failure was silent in exactly the way this
    # partition exists to prevent.  A new module on disk that nobody DECLARES is invisible all the
    # way down: `engine_srcs()` reads COMPONENTS, `imports.py` derives edges over that set, dag.bzl
    # projects those edges, and Bazel stages from dag.bzl.  So `imports.py --check` reported
    # "dag.bzl is fresh" -- truthfully, since it was consistent with a partition that never
    # mentioned the file -- while every sandboxed cell died on `ModuleNotFoundError: No module
    # named 'bibparse'`.  The generator was correct and its INPUT was incomplete.
    #
    # place-by-ownership-not-need: writing the file where it was needed (paperkit/) is not the
    # same act as registering it with the layer that owns WHICH MODULES EXIST.  This is that layer.
    # ⚑ Ζ·re·any — `rematch.py` is the TYPED SEAM over stdlib `re`, and it is in `model` because
    # it is a data-reading leaf like `bibparse`: it imports nothing engine-internal (its only
    # import is `re`, and that for typing alone), so it adds no DEPS edge.  Registered HERE at
    # the moment it was created rather than after a build failed — the bibparse lesson, which
    # cost four batch runs because a module on disk that this partition does not name is
    # invisible to imports.py, to dag.bzl, and therefore to every sandboxed cell.
    # ⚑ Ζ·bib·nest — `bibfidelity.py` is the SECOND bib grammar and belongs beside the first.
    # `bibparse` is STRICT (refuses malformed input at a position, so the projector never renders
    # a half-read record); `bibfidelity` is PERMISSIVE (drops what it cannot read and DECLARES the
    # drop), which is what a tool answering "what does the FILE say, including what the engine
    # ignores" requires — it must survive input `bibparse` correctly rejects.  Two grammars, two
    # jobs, one component: both are data-reading leaves whose only import is `re`, so neither
    # adds a DEPS edge and `model`'s `["kernel"]` stays honest.
    #
    # ⚑⚑ IT EXISTS BECAUSE SEVEN MODULES RE-DERIVED THE FORMAT.  Six render witnesses plus
    # `paperkit/tools/bibstruct.py` each carry an inline bib regex, four byte-identical, all
    # counting braces to depth ONE against a corpus that goes to two — measured, that lost three
    # `claim` fields and invented a phantom field name from the leftover tail.  This is the ONE
    # place a file-fidelity read is spelled, which is the same consolidation `bib.py`'s own
    # docstring records having already done once for the engine side (Ζ·re·structural).
    "model": [
        "bib.py",
        "bibfidelity.py",
        "bibparse.py",
        "durable.py",
        "rematch.py",
        "rhetoric.py",
    ],
    "resolver": [
        "resolver.py",
    ],
    "project": [
        "genre.py",
        "project.py",
    ],
    "gate": [
        "gate.py",
    ],
    # Ζ·library·kernel — the CONCEPT-LIBRARY machinery, lifted out of library/ where it was private
    # to paperkit's own concepts.  Mechanism, not content: the graded route walk and its exit-code
    # protocol, a witness that proves itself, the concept/label index, a check cache keyed on what
    # each check reaches, the printed-conclusion gate.  Zero domain coupling.
    #
    # Two things forced the lift.  Inside library/ they were invisible to closure.py (which
    # enumerates ENGINE modules), so the per-claim grid staged a closure without them and
    # concept-views' ∅-baseline flipped — the harness refusing to trust a measurement whose
    # witness could not run.  And a downstream consumer building four concept libraries wrote
    # their own harness for this protocol, because paperkit shipped `concept:` as a verb while
    # keeping the library-side machinery private to one project.
    "library_kernel": [
        "checkcache.py",
        "conclusiongate.py",
        "labelmap.py",
        "prove.py",
        "routes.py",
    ],
    # Ζ·tools·merge — THE `vendored` COMPONENT IS GONE, AND ITS ABSENCE IS THE FIX.
    #
    # It held `bibstruct.py` + the two modules it composes (`vfs`, `edit_snapshot`), adopted from
    # substrate 2026-08-28, at `paperkit/tools/`.  With an `__init__.py` that made them a PACKAGE
    # named `tools` — colliding with the repo-root `tools/` that pyproject.toml also declares.
    # MEASURED 2026-09-02: a boundary suite run as a script puts `paperkit/` on sys.path[0], so
    # `from tools import dagderive` bound to the THREE-module package and raised.  Four checks
    # red on it (bnd-components, bnd-toplevel, bnd-closure-script, bnd-hook-index), identically
    # on the host and in the cell — never a sandbox artifact.
    #
    # ⚑ THE TWO SETS WERE DISJOINT, WHICH IS WHAT MADE THE COLLISION ACCIDENTAL RATHER THAN A
    # DESIGN.  Three modules against ~55, zero overlap, no shared history — they landed inside
    # `paperkit/` because they are engine-adjacent, and nobody chose to shadow anything.
    #
    # ⚑⚑ AND `vendored` NAMED A TRANSITIONAL STATE, NOT A PROPERTY.  The comment this replaces
    # said "transfer accepted by summit; ownership not yet flipped" — so the word described a
    # handover in progress.  paperkit owns them now.  A directory named for an expiring state
    # tells the next reader a lie about who owns the code, which is why the repair is not a
    # RENAME (paperkit/vendored/, paperkit/struct/ — the latter would shadow the stdlib, the same
    # class one door over) but a MERGE: one `tools` package instead of two.  The collision cannot
    # recur because the second package no longer exists.
    #
    # The old comment argued that "placing them anywhere else would have quietly licensed an edge
    # nobody wants".  That reasoning was about the ENGINE, and repo-root `tools/` is not the
    # engine — nothing here may import it either.  The property survives the move: these files
    # are gone from this partition because they are gone from `paperkit/`, and a partition that
    # walks the engine tree cannot place a file outside it.
    #
    # ⚑⚑⚑ Census before the move: 7 in-repo references to `paperkit/tools/`, ZERO external.
    # summit names it `bibstruct` as a COMMAND, never a path — so no consumer breaks.
    "delta": [
        "cache.py",
        "coherence.py",
        "discriminate.py",
        "driver.py",
        "footdeps.py",
        "grade.py",
        "grader.py",
        "layout.py",
        "mutate.py",
    ],
    # ⚑ Φ·fixture·path — `tests/__init__.py` MAKES THIS A PACKAGE, and it is placed HERE at the
    # moment it was created rather than after a build failed.  A module on disk that this
    # partition does not name is invisible all the way down: engine_srcs() reads COMPONENTS,
    # dagderive derives over that set, dagbzl projects it, and Bazel stages from dag.bzl — so a
    # freshness check can truthfully report "fresh" while every sandboxed cell dies on
    # ModuleNotFoundError.  That cost four batch runs when `bibparse.py` went unplaced.
    "tests": [
        "tests/__init__.py",
        "tests/_boundary.py",
        "tests/_fixture_delta.py",
        "tests/_fixture_gate.py",
        "tests/_fixture_model.py",
        "tests/_fixture_project.py",
        "tests/boundaries_agree.py",
        "tests/boundaries_bib.py",
        "tests/boundaries_check.py",
        "tests/boundaries_clamp.py",
        # Ξ·dag·script — the closure derivation's subprocess boundary.  Registered HERE at the
        # moment the file was created, which is the lesson the bibparse comment above records
        # costing four batch runs: I wrote the suite, wired its bib claim, declared its `reads`,
        # regenerated the projection — and it still reddened the gate, because a module this
        # partition does not name is staged by nothing and the cell ran against a file that was
        # not there.  Three rounds of diagnosis-by-hypothesis before checking the partition.
        "tests/boundaries_closure_census.py",
        "tests/boundaries_coherence.py",
        "tests/boundaries_components.py",
        "tests/boundaries_concept_route.py",
        "tests/boundaries_config.py",
        "tests/boundaries_cpuweight.py",
        "tests/boundaries_corroboration.py",
        "tests/boundaries_dag_regen.py",
        "tests/boundaries_data_atom.py",
        "tests/boundaries_data_grade.py",
        "tests/boundaries_decisions.py",
        "tests/boundaries_degrade.py",
        "tests/boundaries_discriminate.py",
        "tests/boundaries_dispatch.py",
        "tests/boundaries_driver.py",
        "tests/boundaries_emit.py",
        "tests/boundaries_env.py",
        "tests/boundaries_footprint.py",
        "tests/boundaries_gate_json.py",
        "tests/boundaries_grounding.py",
        "tests/boundaries_hook_index.py",
        "tests/boundaries_jobs.py",
        "tests/boundaries_ladder.py",
        "tests/boundaries_logs_push.py",
        "tests/boundaries_mem_db.py",
        "tests/boundaries_memoize.py",
        "tests/boundaries_mutate_atom.py",
        "tests/boundaries_mutable.py",
        "tests/boundaries_otlp.py",
        "tests/boundaries_package_shadow.py",
        "tests/boundaries_path.py",
        "tests/boundaries_prove.py",
        "tests/boundaries_prove_envelope.py",
        "tests/boundaries_references.py",
        "tests/boundaries_result_addr.py",
        "tests/boundaries_sandbox.py",
        "tests/boundaries_scope.py",
        "tests/boundaries_surface.py",
        "tests/boundaries_target.py",
        "tests/boundaries_toplevel.py",
        "tests/boundaries_verdict.py",
        "tests/boundaries_write_atomic.py",
        "tests/boundaries_without_k.py",
    ],
}

DEPS = {
    "kernel": [],
    "model": ["kernel"],
    "resolver": ["kernel"],
    "project": ["model", "kernel"],
    "gate": ["project", "model", "resolver", "kernel"],
    "library_kernel": ["delta", "gate", "project", "model", "resolver", "kernel"],
    "delta": ["gate", "project", "model", "resolver", "kernel"],
    # Ζ·tools·merge — `vendored` is gone from DEPS because it is gone from the partition; see the
    # block above.  The property it enforced (nothing in the engine imports bibstruct/vfs/
    # edit_snapshot) now holds for a stronger reason than a DAG rule: those files are no longer
    # under `paperkit/`, so the partition cannot name them and an engine import of one would be
    # an edge to a module this file does not know about.
    "tests": ["delta", "gate", "project", "model", "resolver", "kernel"],
}
