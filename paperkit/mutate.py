"""Ζ·mutant — the pure perturbation leaf now lives in mtools, as `mikemol.mutation.mutate`.

The 600-line AST surgery that used to be here was ported to mtools (mtools:W556) and is imported
from there; the two were compared over 137 tracked modules and 4277 site/spec comparisons with no
difference (only the arc symbol in the KeyError text was dropped by the port).

⚑ THIS FILE IS A TRANSITIONAL SHIM (paperkit:W343), declared and not hidden.  The old private
names below are what `grader.py` and two boundary suites still reach; those files carry lint
debt the per-file gate will not let a one-line repoint through, so they keep the old spelling
until each is cleaned and repointed onto `mikemol.mutation.mutate` directly.  The shim is
deleted with the last of them.  Nothing here may grow logic: it is names, not behaviour.
"""

from __future__ import annotations

import mikemol.mutation.mutate as _dist

emit_mutant = _dist.emit_mutant
main = _dist.main
_def_sites = _dist.def_sites
_branch_sites = _dist.branch_sites
_data_sites = _dist.data_sites
_flip_sites = _dist.flip_sites
_flip_condition = _dist.flip_condition
_mutate_lines = _dist.mutate_lines
_drop_data_multi = _dist.drop_data_multi

if __name__ == "__main__":
    raise SystemExit(main())
