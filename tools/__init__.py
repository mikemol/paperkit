"""paperkit's build and measurement tools, as a package.

⚑ Ζ·tools·package — WHY THIS FILE EXISTS, AND WHAT IT DOES NOT CHANGE.

`Ζ·eval·split` cut `tools/eval.py` (238 lines, a 127-line `main()` doing five jobs) into three
modules, and the split immediately failed its own gate:

    error: Cannot find implementation or library stub for module named "cellcgroup"
    error: Cannot find implementation or library stub for module named "cellstage"

A bare `import cellcgroup` beside `eval.py` works at RUNTIME — the interpreter puts a script's own
directory on `sys.path` — and is invisible to a CHECKER, which has no such rule.  So the debt was
hidden until a file was decomposed: **you cannot split a module into siblings without a package to
put them in.**  `Ζ·eval·split` and `Ζ·path·retire` are one arc from two ends.

⚑ MEASURED BEFORE WRITING THIS, because the population decides the shape:

    30 .py modules · 26 RUNNABLE AS SCRIPTS · 5 with sibling imports · 8 with a sys.path injection

**26 of 30 are ENTRY POINTS.**  Bazel invokes them by absolute path (`eval.py`, `sens.py`,
`pyc.py` per grid cell), `.githooks/pre-commit` invokes six more, and `paper.toml` templates name
others.  So this directory is a set of PROGRAMS that happen to share code — not a library — and
`__init__.py` must leave `python3 tools/foo.py` working exactly as before.

WHAT IT CHANGES: `tools` becomes an importable name, so a sibling edge can be DECLARED
(`from tools import cellcgroup`) instead of relying on the script-directory rule that only the
interpreter knows.  A checker can then follow the edge, which is the whole point — the injection
was never causing the debt, it was hiding it.

WHAT IT DOES NOT CHANGE: nothing here runs at import.  A package `__init__` executes when the
package is imported, and these tools are `import`ed by exactly the five modules with sibling
edges; making it do work would put that work in the path of every one of 137,553 grid cells.

⚑ AND IT IS NOT IN THE WHEEL.  `pyproject.toml` already records that shipping the wrong thing to
a consumer is a live problem (Ζ·wheel·library — the concept library walks UP out of the package,
so an installed paperkit resolves no `concept:` at all).  A consumer installing paperkit has no
use for the sweep's cell runner or the memory-manifest harvester; `[tool.setuptools] packages`
stays deliberate rather than becoming a glob.
"""
