#!/usr/bin/env python3
"""Ζ·mutant·struct·surface — every PERTURBATION SITE of the engine as (module, SPEC), where SPEC is a
mutate.py mutation.  The def-sweep's original surface was def-sites only — a def's BEHAVIOUR, present
→ absent.  A perturbation TOGGLES an element's presence, so the surface generalizes to the import DAG,
enumerating present elements to DROP and absent ones to INJECT:

    <qualname>       DROP a def's behaviour (def_sites.py — the original surface; a bare qualname is a
                     def-drop to mutate.py, backward-compatible).
    import+:<name>   INJECT an ABSENT engine import — the NEGATIVE polarity, over which a "module does
                     NOT import X" assertion (module-split) becomes falsifiable.  X ranges over the
                     engine modules the target does not already import (a bounded candidate set, not
                     all possible names — the injects that could matter are engine ones).

Emits `module<TAB>spec`; the grid runs `mutate.py <module> <spec>` per site.  import-DROP is OMITTED:
dropping an import breaks the module, which the def-drop of any function it uses already covers — a
redundant coarse cell.  (bib-edge / file nodes need eval.py to swap a non-.py artifact — a later rung;
this surface is the .py toggles mutate.py already emits.)  Usage: sites.py <module.py>…"""
import sys
from pathlib import Path

from def_sites import def_sites
from imports import imports


def sites(path, names):
    """The perturbation SPECS for one module: its def-drops (present behaviours) and its import+
    injects (absent engine imports — every engine module it does not already import, itself aside)."""
    text = Path(path).read_text()
    for qn in def_sites(text):
        yield qn                                        # def-drop — a bare qualname
    absent = names - imports(text, names) - {Path(path).stem}
    for name in sorted(absent):
        yield "import+:" + name                         # inject an absent engine import (negative polarity)


if __name__ == "__main__":
    paths = sys.argv[1:]
    names = {Path(p).stem for p in paths}
    for p in paths:
        for spec in sites(p, names):
            print("%s\t%s" % (p, spec))
