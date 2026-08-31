"""The adopted Claude hooks — a PACKAGE, because the hooks import each other by qualified name.

⚑ WITHOUT THIS FILE THE PYCHECK HOOK IS ARMED AND INERT, WHICH IS THE WORST STATE.
`hook_pycheck` was split into six modules upstream (substrate, 2026-08-30) and they import one
another as `from scripts.pycheck_analyze import …`.  In a repo whose `scripts/` is a bare
directory of symlinks that raises ModuleNotFoundError AT MODULE LOAD — and the harness reads a
hook's empty stdout as ALLOW, so the guard denies nothing while reading as armed in review.

⚑⚑ MEASURED HERE, NOT ASSUMED.  Invoked directly, the hook reported it:

    hook_pycheck: ARMED BUT INERT — cannot import a sibling
    (No module named 'scripts.pycheck_analyze').  This hook is checking NOTHING.

That fail-loud arm exists because this repo reported the ORIGINAL instance of the same defect to
substrate two days ago; upstream added the arm, and it is what turned a silent hole into a
sentence.  The adoption still has to supply what the arm names.

⚑ SAME LESSON AS `tools` ONE DIRECTORY OVER (Φ·fixture·path).  `pyproject.toml` claimed the
editable install already made `tools` importable and it did not — the package resolved by CWD and
nowhere else.  A directory is not a package because someone calls it one; the declaration is the
`__init__.py` and the entry in `[tool.setuptools] packages`.

Empty of code deliberately: the hooks are symlinks into substrate and ownership is not claimed.
This file declares the namespace they import through, and nothing else.
"""
