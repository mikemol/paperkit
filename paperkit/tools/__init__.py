"""Ζ·pyc·package — the package MARKER for paperkit's own tools subpackage.

⚑ A DIRECTORY OF MODULES IS NOT A PACKAGE, AND THIS REPO HAS PAID FOR THAT TWICE ALREADY.
`tools/BUILD.bazel` and the root `BUILD.bazel` both carry the lesson at length: a manifest that
listed individual `tools/*.py` and no `__init__.py` gave five boundary suites a
ModuleNotFoundError inside a sandbox cell while they passed on the host, where the editable
install supplies the package.

The bibstruct relocation created `paperkit/tools/` with three modules and no marker, and the
failure arrived by a third route — `boundaries_config` walks the component partition and imports
every engine module by name, so the whole bnd-config suite died at collection with the partition,
not the suite, at fault.

⚑⚑ AND THE NAME COLLIDES, WHICH THE MARKER ALONE DOES NOT SETTLE.  The repo root has its own
`tools/` package.  A consumer with `paperkit/` on sys.path (the flat spelling every engine module
still uses) resolves a bare `tools` to whichever directory comes first — so these modules are
reachable as `paperkit.tools.<m>` and NOT as `tools.<m>`.  That is the same ambiguity
`dagderive.stem_index` refuses one level down, and it is one more thing Ζ·engine·flat retires:
under the package spelling the two names are distinct and cannot shadow each other.

⚑ BUILT UNDER ANOTHER SUFFIX AND MOVED INTO PLACE, which is the route `hook_pycheck`'s own
docstring names for a bootstrap: ruff's INP001 fires on a package marker checked through
`--stdin-filename`, because the file that would satisfy the rule is the one being written and
does not exist on disk yet.  The gate keys on the `.py` suffix, so the honest move is to check it
at its real path once it is real — not to route around the gate, and not to suppress a rule whose
stated remedy is exactly this edit.
"""
