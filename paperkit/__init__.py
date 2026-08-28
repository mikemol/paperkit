"""paperkit — documents as projections of verified claim-DAGs.

⚑ WHY THIS FILE EXISTS, AND WHY IT MUTATES sys.path.

The engine's modules are invoked THREE ways and all three must keep working:

    python3 paperkit/gate.py <args>     a SCRIPT — every Bazel action runs the engine this way
    python3 -m paperkit.gate <args>     a MODULE — what an installed console-script resolves to
    import paperkit.bib                 a PACKAGE — how a downstream consumer reads the parser

Relative imports (`from . import bib`) satisfy the last two and BREAK the first: a module run as
__main__ has no parent package, so `from . import bib` raises ImportError.  Measured, not assumed.
Bazel invokes `python3 paperkit/<module>.py` in every pk_* action and stages a per-module .pyc
closure keyed by FLAT STEM (paperkit/BUILD.bazel's _STEM_TO_TARGET), so flat `import bib` is not a
legacy accident here — it is the form the build graph is a projection of.

So the modules keep `import bib`, and THIS file makes that resolvable however the package is
reached.  It is the one owner for the PACKAGE form, executed once at package import.

⚑ It does NOT replace the six `sys.path.insert(0, Path(__file__).parent)` lines in gate, project,
rhetoric, discriminate, coherence and footdeps — those are still there, deliberately, and this
docstring claimed otherwise until it was measured.  Removing them regressed seven talk claims:
each module may be run AS A SCRIPT (`python3 paperkit/gate.py`), where this file never executes,
and the insert also asserts a PRIORITY — `render/checks/bib.py` exists and would shadow the
engine's `bib` on a path that resolved the other way.  So the inserts are not six copies of one
fix; they solve a case the package form cannot reach (Λ·guard-must-not-copy — the seventh module to forget it would fail
only on the path nobody tested).

A module run directly as a script does not import this file at all — Python puts its own directory
on sys.path first, which is exactly what these lines reproduce for the other two entry paths.  That
is why the same flat import serves all three.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
