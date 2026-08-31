"""Μ·kernel — the engine's boundary suites, as a PACKAGE rather than a directory of scripts.

⚑ Φ·fixture·path — THE FILESYSTEM WAS ENCODING WHAT PACKAGING OWNS.  Every suite opened with
`sys.path.insert(0, <own dir>)` before `from _fixture_gate import gate`, ~46 copies of one
reachability claim, each slipping a detail (some inserted `parent`, some `parent.parent`, some
`parents[2] / "tools"`).  That is [[test-fixture-duplication]] one level down from the fixtures
themselves, and `_boundary.py` — the module that exists to END copy-paste — was itself reached by
the flat import being retired.

⚑⚑ AND IT COST THE BUILD A TRANSLATION MAP.  Flat imports meant `dag.bzl` recorded a path-shaped
KEY against a bare-stem VALUE, so `paperkit/BUILD.bazel` carried
`_STEM_TO_TARGET = {stem: path for …}` — a dict comprehension, hence silently LAST-WINS over the
three directories the engine spans.  Measured: 79 sources, 79 distinct stems, no collision TODAY
and nothing that would refuse one; a second `bib.py` here would collapse onto `paperkit/bib.py`'s
key and the loser's .pyc would never be staged.  A naming convention with no owner is
guard-must-not-copy at the build layer.

⚑ WHAT THIS FILE DOES NOT DO.  It does not make a relative import work on the route the bib
spells.  All 42 suites are invoked as `cmd:python3 ../paperkit/tests/boundaries_X.py` from
`boundaries/` — the SCRIPT route, where there is no parent package, so `from . import x` raises at
module level before any `__main__` shim can help (measured on render/checks/matrix.py this
session).  Suites therefore name their siblings ABSOLUTELY (`from paperkit.tests._fixture_gate
import gate`), which works on every route because `paperkit` is a declared package.

Empty of code deliberately: `paperkit/__init__.py` owns the engine's own path claim, and a second
one here would be a second roster over one fact.
"""
