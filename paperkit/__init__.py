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

⚑ THE SIX SIBLING INSERTS (gate, project, rhetoric, discriminate, coherence, footdeps) DEFEND
ONE THING, NOT TWO — AND THIS DOCSTRING CLAIMED TWO UNTIL IT WAS MEASURED.

It said they also assert a PRIORITY: that `render/checks/bib.py` exists and would shadow the
engine's `bib` on a path resolving the other way, so the inserts "solve a case the package form
cannot reach".  ⚑ THAT HALF IS FALSE.  The shadowing is a property of the FLAT NAME.
`paperkit.bib` and `render.checks.bib` are different names, and a directory early on sys.path
cannot shadow a package attribute.  Measured directly — the hostile order the claim describes,
both spellings asked in ONE interpreter:

    sys.path[0] = render/checks
      flat  import bib                -> render/checks/bib.py     dep_order? False
      pkg   from paperkit import bib  -> paperkit/bib.py          dep_order? True

The flat name IS shadowed, reproducing the original failure exactly; the package name reaches the
engine regardless of what sits earlier.  So the insert defends a SPELLING, not a property, and
retires with the spelling.  (The probe that measured this, `tools/shadowprobe.py`, was a one-shot
instrument and is deleted with the finding recorded here — a tool whose method is constructing a
hostile sys.path has no place in the tree that is retiring sys.path mutation, and after the
conversion there is no flat `import bib` left for it to shadow.)

⚑⚑ WHAT REMAINS TRUE IS THE SCRIPT ROUTE, AND IT IS THE ARC'S ACTUAL BLOCKER.  A module run as
`python3 paperkit/gate.py` never imports this file — Python puts the SCRIPT's own directory on
sys.path instead — so the flat `import bib` inside it resolves by that rule alone.  Every Bazel
action and every bib `cmd:` spells exactly that invocation.  Removing the inserts without changing
how the engine is INVOKED regressed seven talk claims, which is what the earlier measurement
actually showed.

That makes Ζ·path·retire a change to the INVOCATION (the bib's `cmd:` and the sandbox's staging),
not a change to the imports alone — and the venv already answers it: `pyproject.toml` declares
`packages = ["paperkit", "tools"]`, and `tools/pathaudit.py --probe` measures both importable from
outside the repo with no mutation at all.
"""
import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
