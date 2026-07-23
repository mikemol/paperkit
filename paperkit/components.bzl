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
        "config.py",
    ],
    "model": [
        "bib.py",
        "rhetoric.py",
    ],
    "resolver": [
        "resolver.py",
    ],
    "project": [
        "project.py",
    ],
    "gate": [
        "gate.py",
    ],
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
    "tests": [
        "tests/_fixture_delta.py",
        "tests/_fixture_gate.py",
        "tests/_fixture_model.py",
        "tests/_fixture_project.py",
        "tests/boundaries_agree.py",
        "tests/boundaries_check.py",
        "tests/boundaries_coherence.py",
        "tests/boundaries_components.py",
        "tests/boundaries_config.py",
        "tests/boundaries_corroboration.py",
        "tests/boundaries_degrade.py",
        "tests/boundaries_discriminate.py",
        "tests/boundaries_dispatch.py",
        "tests/boundaries_driver.py",
        "tests/boundaries_emit.py",
        "tests/boundaries_env.py",
        "tests/boundaries_footprint.py",
        "tests/boundaries_gate_json.py",
        "tests/boundaries_grounding.py",
        "tests/boundaries_jobs.py",
        "tests/boundaries_ladder.py",
        "tests/boundaries_memoize.py",
        "tests/boundaries_path.py",
        "tests/boundaries_references.py",
        "tests/boundaries_sandbox.py",
        "tests/boundaries_surface.py",
        "tests/boundaries_target.py",
        "tests/boundaries_toplevel.py",
        "tests/boundaries_without_k.py",
    ],
}

DEPS = {
    "kernel": [],
    "model": ["kernel"],
    "resolver": ["kernel"],
    "project": ["model", "kernel"],
    "gate": ["project", "model", "resolver", "kernel"],
    "delta": ["gate", "project", "model", "resolver", "kernel"],
    "tests": ["delta", "gate", "project", "model", "resolver", "kernel"],
}
