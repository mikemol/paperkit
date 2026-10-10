"""paperkit — documents as projections of verified claim-DAGs.

⚑ THIS FILE DOES NOTHING, AND THAT IS THE POINT (Ζ·path·retire).

It used to put the engine's own directory on sys.path so the modules' flat `import bib` resolved
however the package was reached.  Two measurements retired it:

  * the shadow it was said to defend against is false: with a hostile directory first on sys.path
    a flat `import bib` IS shadowed, but `from paperkit import bib` reaches the engine's bib
    whatever sits earlier — the spelling was the defect, not the path;
  * the spelling is gone: the engine imports itself as `paperkit.<module>` everywhere
    (paperkit:W296), and a census over every tree on 2026-10-10 found 0 flat engine-sibling
    imports.

The engine is invoked three ways and all three work with no path mutation, because each module
names its dependencies as a package: as a MODULE (`python -m paperkit.gate`, what generated checks
run since paperkit:W299), as an installed console script, and as an imported PACKAGE
(`import paperkit.bib`).  Importing this package must not change the interpreter it runs in.
"""
