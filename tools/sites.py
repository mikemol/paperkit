#!/usr/bin/env python3
"""Ζ·mutant·struct·surface — every PERTURBATION SITE of the engine as (module, SPEC), where SPEC is a
mutate.py mutation.  The def-sweep's original surface was def-sites only — a def's BEHAVIOUR, present
→ absent.  A perturbation TOGGLES an element's presence, so the surface generalizes to the import DAG,
enumerating present elements to DROP and absent ones to INJECT:

    <qualname>       DROP a def's behaviour (def_sites.py — the original surface; a bare qualname is a
                     def-drop to mutate.py, backward-compatible).
    branch:<qn>#<n>  DROP one BRANCH ARM's behaviour (Μ·sweep·atom — a finer, still-monotone reach probe
                     ADDITIVE to the def-drop; the same raise, the same grid path).
    flip:<qn>#<n>    INVERT one CONDITION (Μ·sweep·atom — NON-monotone; routed to the decision-coverage
                     grid, NOT the sensitivity sweep; the grid partition + sens.py's fail-loud assert are
                     the grid-level structural bar, mirroring the in-process FlipSite type).
    data-:<QN>#<n>   DROP one KEY/ELEMENT of a module-level dict/list/set/tuple literal (Μ·sweep·atom —
                     the DATA analog of branch:, still-MONOTONE: a witness flips iff it READS that entry;
                     a dict every read swallows a dropped key is REFUSED by _data_sites → the same sens
                     grid path as branch:).
    dflip:<QN>#<n>   PERTURB one dict-VALUE / non-set element to a valid same-position counterfactual
                     (Μ·sweep·atom — the DATA analog of flip:, NON-monotone: it flips only if the witness
                     ASSERTS the value → the SAME pk_decisions coverage grid + sens.py bar as flip:; a
                     set element has no perturbable value, so sets contribute NO dflip:).
    import+:<name>   INJECT an ABSENT engine import — the NEGATIVE polarity, over which a "module does
                     NOT import X" assertion (module-split) becomes falsifiable.  X ranges over the
                     engine modules the target does not already import (a bounded candidate set, not
                     all possible names — the injects that could matter are engine ones).

Emits `module<TAB>spec`; the grid runs `mutate.py <module> <spec>` per site.  import-DROP is OMITTED:
dropping an import breaks the module, which the def-drop of any function it uses already covers — a
redundant coarse cell.  (bib-edge / file nodes need eval.py to swap a non-.py artifact — a later rung;
this surface is the .py toggles mutate.py already emits.)  branch:/flip: come from mutate.py itself (the
ONE source the in-process sweep also imports — no separate twin to drift).  Usage: sites.py <module.py>…
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "paperkit"))

from def_sites import def_sites
from imports import imports

# Μ·sweep·atom — the ONE atom source (grader imports the same enumerators; no separate twin to drift).
from mutate import _branch_sites, _data_sites, _flip_sites


def sites(path, names):
    """The perturbation SPECS for one module: its def-drops (present behaviours), its branch-arm and
    condition sites, its DATA key-drops and value-perturbs (Μ·sweep·atom — all additive), and its
    import+ injects (absent engine imports).
    """
    text = Path(path).read_text()
    for qn in def_sites(text):
        yield qn                                        # def-drop — a bare qualname
    for qn, n, _arm in _branch_sites(text):
        yield "branch:%s#%d" % (qn, n)                  # Μ·sweep·atom — a branch-arm reach probe (raise-kind)
    for qn, n, _test in _flip_sites(text):
        yield "flip:%s#%d" % (qn, n)                    # Μ·sweep·atom — a condition inversion (non-monotone)
    for qn, n, kind, _k, _v in _data_sites(text):
        yield "data-:%s#%d" % (qn, n)                   # Μ·sweep·atom — a data key/elem DROP (raise-kind, like branch:)
        if kind != "Set":                               # a set element has no perturbable value (data-: covers presence)
            yield "dflip:%s#%d" % (qn, n)               # Μ·sweep·atom — a data value PERTURB (non-monotone, like flip:)
    absent = names - imports(text, names) - {Path(path).stem}
    for name in sorted(absent):
        yield "import+:" + name                         # inject an absent engine import (negative polarity)


if __name__ == "__main__":
    paths = sys.argv[1:]
    names = {Path(p).stem for p in paths}
    for p in paths:
        for spec in sites(p, names):
            print("%s\t%s" % (p, spec))
