"""render's witnesses, as a package of COMPONENTS rather than a directory of scripts.

⚑ A WITNESS IS A COMPONENT IN A FRAMEWORK, NOT AN INDIVIDUAL IMPERATIVE (operator, 2026-08-30).
Every module here used to run its whole check AT IMPORT: the pandoc call, the conversion, the
asserts and the print were all module-level statements, so importing the module WAS running it.
That shape has three costs, and the third is the one that matters:

  1. the module cannot be imported to be inspected, listed, or tested;
  2. an import cycle or a stray import runs a document conversion as a side effect;
  3. ⚑ THE FRAMEWORK CANNOT HOLD A REFERENCE TO THE CHECK — it can only spawn a process and read
     an exit code, which is why `resolver.run_ok` reconstructs a tristate from a NUMBER plus a
     scraped stderr line (rc 3 = cannot-run BY CONVENTION).  A typed verdict is destroyed at that
     boundary and rebuilt downstream, which is the `Ε·fold` shape this engine names elsewhere.

So each witness now exposes `check() -> int` and keeps a THIN `__main__` adapter over it.  The
bib's spelling is unchanged — `cmd:python3 checks/foo.py` still works, and three downstream
consumers author bibs against exactly that — but the framework now has something to CALL.
"""
