r"""Behavioral-boundary examples for Ζ·dag·regen — the generator that OWNS dag.bzl can write it.

paperkit/dag.bzl carries "REGENERATE (never hand-edit)" in its own header and bnd-components gates
it FRESH against its generator.  Both were true and the loop was still open: the generator emitted
edges to stdout and had no writer, so the only way past a stale-dag red was to hand-edit the file
whose header forbids hand-editing.  A generator built and left unwired.

What is pinned is the ROUND TRIP, not the flag's existence: add a real import edge and --check must
red naming its repair without mutating anything; --write must fix it; remove the edge, regenerate,
and dag.bzl must return BYTE-IDENTICAL.  That last arm is what makes --write a repair rather than a
rewriter — a regenerator that does not round-trip quietly rewrites history on every run.

HERMETIC BY CONSTRUCTION.  The probe mutates a COPY of the engine, never the live tree.  The first
draft mutated paperkit/genre.py in place and restored it in a finally; it passed alone and broke
boundaries_memoize when run concurrently, because that suite keys grades on an ENGINE EPOCH and a
sibling touching any engine file invalidates its fixture mid-run.  A restore-in-a-finally bounds
damage in TIME and does nothing for a concurrent reader — and the gate resolves checks in a thread
pool, so "restored afterwards" is not "never observed changed".

(Four probe defects in this session came from an edit that never landed, so the arms ASSERT the
mutation is present before drawing any conclusion from it.)

⚑ Ξ·dag·dotted — THE GENERATOR IS NOW `tools/dagbzl.py`, AND AN EDGE'S VALUE IS A MODULE PATH.
It was `tools/imports.py`, which recorded a path-shaped KEY against a bare-stem VALUE, so
paperkit/BUILD.bazel had to translate between the two namespaces via a `_STEM_TO_TARGET` dict
comprehension — silently last-wins over the three directories the engine spans.  The value is now
`durable.py`, not `durable`, which is what this suite's own edge-landed arm asserts: both sides of
an edge name the shape a Bazel target uses, and the translating map is deleted.

⟨P, F, δ⟩ per the boundary practice.

Run:  python3 paperkit/tests/boundaries_dag_regen.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ⚑ Ζ·engine·reach — the bib spells bare `python3`, which has no virtualenv and therefore no
# editable install.  Appending the repo root makes `paperkit` importable as a DIRECTORY.
# APPEND, not insert: it adds a namespace rather than shadowing one.
sys.path.append(str(Path(__file__).resolve().parents[2]))

from paperkit.tests._boundary import Suite

ENG = Path(__file__).resolve().parent.parent
ROOT = ENG.parent
ANCHOR = "import sys\n"
EDGE = "import sys\nimport durable  # boundaries_dag_regen probe\n"
# ⚑ Ζ·dagderive·pkg — THE SAME EDGE, WRITTEN THE OTHER WAY.  `import durable` and `from paperkit
# import durable` are one dependency in two spellings, and the derivation MUST record both
# identically or converting a file silently deletes its edges from dag.bzl — which is what Bazel
# stages each cell's .pyc closure from.
PKG_EDGE = "import sys\nfrom paperkit import durable  # boundaries_dag_regen probe\n"


def main() -> int:
    """Exercise the generator's --check/--write round trip against a copied engine tree."""
    # ⚑ Ζ·suite·count — THE SHARED RECORDER, not a per-file closure.  `_boundary.Suite` exists
    # because 45 suites each declared their own `check(desc, cond)` over their own `fails` list
    # and then printed a summary naming a count that had no owner: 24 of 26 such literals
    # UNDERSTATED, tracking authoring history rather than content.  Adopting it here means this
    # suite has no number to type — and it retires the FBT001 that a hand-rolled closure earns.
    s = Suite("dag-regen boundaries", "Ζ·dag·regen — the generator writes what it owns")

    live_before = (ENG / "genre.py").read_bytes()
    live_dag_before = (ENG / "dag.bzl").read_bytes()

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)

        # ⚑ `shutil.ignore_patterns` IS AN UNTYPED-CALLABLE BOUNDARY, narrowed here rather than
        # carried: typeshed gives it `Callable[[Any, list[str]], set[str]]`, so passing it around
        # poisons every expression it touches.  A local predicate says the same thing concretely.
        def ignore(_dir: str, names: list[str]) -> set[str]:
            """Skip compiled artifacts when copying the engine into the work tree."""
            return {n for n in names if n == "__pycache__" or n.endswith(".pyc")}

        shutil.copytree(ENG, work / "paperkit", ignore=ignore)
        shutil.copytree(ROOT / "tools", work / "tools", ignore=ignore)
        eng = work / "paperkit"
        dag, probe = eng / "dag.bzl", eng / "genre.py"

        def run(*args: str) -> tuple[int, str]:
            """Invoke the generator in the COPIED tree, as a module so its package edges resolve.

            ⚑ `-m tools.dagbzl` FROM THE WORK ROOT, not a path invocation.  `dagbzl` names its
            siblings in full (`from tools import dagderive`, `from paperkit import durable`), so
            it needs the work root as the import root — which is exactly what running it as a
            module with cwd=work provides, and what a bare path invocation would not.
            """
            r = subprocess.run([sys.executable, "-m", "tools.dagbzl", *args],  # noqa: S603
                               cwd=work, capture_output=True, text=True,
                               check=False)   # Λ·separate-filehandles
            return r.returncode, (r.stdout + r.stderr)

        pristine_dag = dag.read_text()
        pristine_probe = probe.read_text()
        if ANCHOR not in pristine_probe:
            sys.stdout.write(f"  XX fixture anchor {ANCHOR!r} absent from {probe.name}\n")
            return 1

        rc, _ = run("--check")
        s.check("P: --check is GREEN on a fresh tree", rc == 0)

        # δ — one real import edge, nothing else changed.
        probe.write_text(pristine_probe.replace(ANCHOR, EDGE, 1))
        s.check("the probe edit LANDED (assert the fixture, never assume it)",
                "boundaries_dag_regen probe" in probe.read_text())

        rc, out = run("--check")
        s.check("F: --check REDS on a stale dag.bzl", rc == 1)
        s.check("   ...and names the repair, not only the breach", "--write" in out)
        s.check("   ...without writing anything (a check must not mutate)",
                dag.read_text() == pristine_dag)

        rc, _ = run("--write")
        s.check("--write repairs it", rc == 0)
        # ⚑ THE VALUE IS A PATH (Ξ·dag·dotted): `durable.py`, not `durable`.  This arm is what
        # pins the rename — a regression to bare stems reds here rather than in a sweep.
        s.check("   ...and the new edge is actually IN the file, as a module PATH",
                '"genre.py": ["durable.py"]' in dag.read_text())
        rc, _ = run("--check")
        s.check("   ...so --check is green again", rc == 0)

        probe.write_text(pristine_probe)
        run("--write")
        s.check("ROUND TRIP: dag.bzl returns BYTE-IDENTICAL once the edge is removed",
                dag.read_text() == pristine_dag)

        # ── Ζ·dagderive·pkg — the SAME edge in the package spelling ────────────────────────
        #
        # ⚑ THE DEFECT THIS PINS DELETED A REAL EDGE AND REPORTED SUCCESS.  `dagderive.imports`
        # matched an `ImportFrom` only when `n.module` was itself an engine stem, so
        # `from paperkit import bibparse` — where `n.module` is `"paperkit"` and the module sits
        # in `n.names` — recorded NOTHING.  Measured 2026-08-31: converting paperkit/bib.py's one
        # import and regenerating dropped `"bib.py": ["bibparse.py"]` from dag.bzl entirely.  A
        # bulk conversion would have erased the engine's import DAG one file at a time, and the
        # consequence is under-staged sandbox cells — the ModuleNotFoundError class components.bzl
        # records costing four batch runs.
        #
        # ⚑⚑ AND IT WOULD HAVE PASSED EVERY ARM ABOVE, because they all write the FLAT spelling.
        # A round-trip that only ever exercises one form cannot see a derivation that understands
        # only that form.  This arm is the second form, asserting the identical output.
        probe.write_text(pristine_probe.replace(ANCHOR, PKG_EDGE, 1))
        s.check("the PACKAGE-spelling probe edit landed",
                "from paperkit import durable" in probe.read_text())
        rc, _ = run("--write")
        s.check("--write accepts the package spelling", rc == 0)
        s.check("   ...and records the SAME edge the flat form does",
                '"genre.py": ["durable.py"]' in dag.read_text())

        probe.write_text(pristine_probe)
        run("--write")
        s.check("   ...and it round-trips out byte-identically too",
                dag.read_text() == pristine_dag)

        rc, out = run("--write")
        s.check("--write is IDEMPOTENT (a no-op run says so and changes nothing)",
                rc == 0 and "already fresh" in out and dag.read_text() == pristine_dag)

    # No restore arm and no finally: the mutated tree was a temp copy, now discarded.
    s.check("the LIVE engine module was never modified",
            (ENG / "genre.py").read_bytes() == live_before)
    s.check("the LIVE dag.bzl was never modified",
            (ENG / "dag.bzl").read_bytes() == live_dag_before)

    return s.finish()


if __name__ == "__main__":
    raise SystemExit(main())
