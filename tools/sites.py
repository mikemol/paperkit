"""Ζ·mutant·struct·surface — every PERTURBATION SITE of the engine as (module, SPEC).

SPEC is a mutate.py mutation.  The def-sweep's original surface was def-sites only — a def's
BEHAVIOUR, present → absent.  A perturbation TOGGLES an element's presence, so the surface
generalizes to the import DAG, enumerating present elements to DROP and absent ones to INJECT:

    <qualname>       DROP a def's behaviour (def_sites.py — the original surface; a bare
                     qualname is a def-drop to mutate, backward-compatible).
    branch:<qn>#<n>  DROP one BRANCH ARM's behaviour (Μ·sweep·atom — a finer, still-monotone
                     reach probe ADDITIVE to the def-drop; the same raise, the same grid path).
    flip:<qn>#<n>    INVERT one CONDITION (Μ·sweep·atom — NON-monotone; routed to the
                     decision-coverage grid, NOT the sensitivity sweep; the grid partition +
                     sens.py's fail-loud assert are the grid-level structural bar, mirroring
                     the in-process FlipSite type).
    data-:<QN>#<n>   DROP one KEY/ELEMENT of a module-level dict/list/set/tuple literal
                     (Μ·sweep·atom — the DATA analog of branch:, still-MONOTONE: a witness
                     flips iff it READS that entry; a dict every read swallows a dropped key is
                     REFUSED by data_sites → the same sens grid path as branch:).
    dflip:<QN>#<n>   PERTURB one dict-VALUE / non-set element to a valid same-position
                     counterfactual (Μ·sweep·atom — the DATA analog of flip:, NON-monotone: it
                     flips only if the witness ASSERTS the value → the SAME pk_decisions
                     coverage grid + sens.py bar as flip:; a set element has no perturbable
                     value, so sets contribute NO dflip:).
    import+:<name>   INJECT an ABSENT engine import — the NEGATIVE polarity, over which a
                     "module does NOT import X" assertion (module-split) becomes falsifiable.
                     X ranges over the engine modules the target does not already import (a
                     bounded candidate set, not all possible names — the injects that could
                     matter are engine ones).

Emits `module<TAB>spec`; the grid runs `mikemol-mutate <module> <spec>` per site.  import-DROP is
OMITTED: dropping an import breaks the module, which the def-drop of any function it uses already
covers — a redundant coarse cell.  (bib-edge / file nodes need eval.py to swap a non-.py
artifact — a later rung; this surface is the .py toggles mutate already emits.)  branch:/flip:
come from `mikemol.mutation.mutate` itself (the ONE source the in-process sweep also imports — no
separate twin to drift).  Usage: sites.py <module.py>…
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import mikemol.mutation.mutate

import tools.def_sites
import tools.imports

if TYPE_CHECKING:
    from collections.abc import Iterator


def sites(path: str, names: set[str]) -> Iterator[str]:
    """Yield the perturbation SPECS for one module.

    They are its def-drops (present behaviours), its branch-arm and condition sites, its DATA
    key-drops and value-perturbs (Μ·sweep·atom — all additive), and its import+ injects (absent
    engine imports).
    """
    text = Path(path).read_text()
    # def-drop — a bare qualname
    for qn in tools.def_sites.def_sites(text):
        yield qn
    # Μ·sweep·atom — a branch-arm reach probe (raise-kind)
    for qn, n, _arm in mikemol.mutation.mutate.branch_sites(text):
        yield f"branch:{qn}#{n}"
    # Μ·sweep·atom — a condition inversion (non-monotone)
    for qn, n, _test in mikemol.mutation.mutate.flip_sites(text):
        yield f"flip:{qn}#{n}"
    for qn, n, kind, _k, _v in mikemol.mutation.mutate.data_sites(text):
        # Μ·sweep·atom — a data key/elem DROP (raise-kind, like branch:)
        yield f"data-:{qn}#{n}"
        # a set element has no perturbable value (data-: covers presence)
        if kind != "Set":
            # Μ·sweep·atom — a data value PERTURB (non-monotone, like flip:)
            yield f"dflip:{qn}#{n}"
    absent = names - tools.imports.imports(text, names) - {Path(path).stem}
    for name in sorted(absent):
        # inject an absent engine import (negative polarity)
        yield f"import+:{name}"


def main(argv: list[str]) -> int:
    """Print `module<TAB>spec` for every perturbation site of the named modules."""
    names = {Path(p).stem for p in argv}
    for p in argv:
        for spec in sites(p, names):
            sys.stdout.write(f"{p}\t{spec}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
