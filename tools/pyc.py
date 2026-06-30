#!/usr/bin/env python3
"""Ζ·pyc — compile one .py to its .pyc BUILD ARTIFACT, the bytecode Python executes (like .cc→.o).

Compilation is a build step, not an import-time side effect.  The .pyc is written with PEP 552
UNCHECKED_HASH invalidation: it records a CONTENT hash of the source (not its mtime) and the runtime
NEVER rechecks the source — so the artifact is reproducible (no mtime ⇒ byte-deterministic, cacheable)
and authoritative (the build graph owns compilation; a mutated .pyc over an unchanged .py runs the
mutation).  Usage: pyc.py <src.py> <out.pyc>."""
import py_compile
import sys


def main(argv):
    src, out = argv
    py_compile.compile(src, cfile=out, doraise=True,
                       invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
