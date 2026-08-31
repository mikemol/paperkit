"""The render project — paperkit's rendering and accessibility-conformance witnesses.

⚑ Ζ·path·retire — THIS FILE EXISTS SO REACHABILITY IS A PACKAGING FACT, NOT A RUNTIME ONE.
Operator ruling 2026-08-30: *don't let the filesystem encode what packaging can.*  Measured
before starting: 113 `sys.path` mutations across 16 directories, of which exactly one was a
package.  Each injection answers "where do my siblings live?" by mutating global interpreter
state at import time — so a module resolves differently depending on how it was invoked, and the
import graph is EXECUTED rather than DECLARED.

A package answers the same question by declaration: `from . import lo` needs no path, no
ordering, and no guess about the caller's cwd.
"""
