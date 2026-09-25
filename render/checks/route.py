#!/usr/bin/env python3
r"""Ρ·render·format — select the render ROUTE (Ω·config): a consumer builds the paper's PDF
deliverable via the intermediate format they want.  Every route terminates at the PDF node
(graph.py), reached through a chosen intermediate — so this is a thin selector over
`pdf.py --via <route>`, NOT a set of rival scripts.  Format is RENDER-LOCAL orchestration, not an
engine concern: the engine projects paper.md format-agnostically and the render coalgebra renders it
several ways, so a Param in the engine's registry would be a knob it does not own.

  PAPERKIT_FORMAT=docx (default) → pdf.py --via docx  (md→docx→pdf, office UA-1: link/math/widen)
  PAPERKIT_FORMAT=odf            → pdf.py --via odf   (md→odt→pdf,  office UA-1: link/math/widen)
  PAPERKIT_FORMAT=latex          → pdf.py --via latex (md→latex→pdf, native UA-2: \DocumentMetadata)

Each route is an independently gated warrant, so the paper is verified via every route regardless of
this selector — it just picks which deliverable to BUILD.  The route names are graph.ROUTES; adding
a node/edge (a beamer slide target) is a matrix entry, and this selector follows it.

⚑ WHY PYTHON, NOT THE sh IT WAS (2026-09-21).  As a shell script this claim carried
`tier = {local}`, which exempted it from the mutation sweep; moved to the sandbox tier (its selftest
touches no host), the sweep graded it INDETERMINATE — "no generic mutation flips it" — because a
shell script has no def-site surface for the engine to mutate.  A check the engine cannot falsify
is asserted, not verified.  In python, `route()` and `_ROUTES` ARE the surface: corrupt the map or
the refusal and the ⟨P,F,δ⟩ selftest reds.  `checks/render.sh` stays as a two-line shim so the
consumer invocation is unchanged.

⚑ NAMED `route.py`, NOT `render.py` — the first cut was `checks/render.py` and three sibling
claims (matrix, cube, wcag-entail-core) went red in the pool with `'render' is not a package`:
`python3 checks/matrix.py` puts checks/ first on sys.path, so `from render.checks import …` found
this FILE before the render/ PACKAGE.  bnd-package-shadow's failure class, one directory down.

    PAPERKIT_FORMAT=latex python3 checks/route.py   # build the paper's PDF via the chosen route
    python3 checks/route.py --which                 # print the selected route, run nothing
    python3 checks/route.py --selftest              # ⟨P,F,δ⟩: the selector dispatches on the format
"""
from __future__ import annotations

import os
import subprocess
import sys

# The format names ARE the graph's route keys (graph.ROUTES): docx|odf|latex.
_ROUTES = ("docx", "odf", "latex")
_DEFAULT = "docx"


def route(env: dict[str, str]) -> str | None:
    """The selected route, or None for an unknown PAPERKIT_FORMAT (refused, never defaulted)."""
    fmt = env.get("PAPERKIT_FORMAT", _DEFAULT)
    return fmt if fmt in _ROUTES else None


def _selftest() -> int:
    # ⟨P,F,δ⟩: the selector routes PAPERKIT_FORMAT onto a graph route.  P: docx/odf/latex map to the
    # matching --via, and no variable defaults to docx.  F: an unknown format is refused, not
    # silently defaulted.  δ: the one env var.
    ok = all(route({"PAPERKIT_FORMAT": r}) == r for r in _ROUTES)
    ok = ok and route({}) == "docx"
    ok = ok and route({"PAPERKIT_FORMAT": "bogus"}) is None
    if ok:
        print("  ok P: docx/odf/latex → pdf.py --via <route>, default docx")
        print("  ok F: an unknown format is refused, not silently defaulted")
        print("  ok δ: PAPERKIT_FORMAT is the one selector")
        print("RENDER SELFTEST: PASS")
        return 0
    print("RENDER SELFTEST: FAIL", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    r = route(dict(os.environ))
    if r is None:
        print(f"render: unknown PAPERKIT_FORMAT={os.environ.get('PAPERKIT_FORMAT')} "
              f"(expected {'|'.join(_ROUTES)})", file=sys.stderr)
        return 2
    if "--which" in argv:
        print(r)
        return 0
    return subprocess.run([sys.executable, "checks/pdf.py", "--via", r], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
