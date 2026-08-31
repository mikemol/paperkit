r"""Ζ·engine·flat — measure whether PACKAGING dissolves the shadowing the path inserts defend.

⚑ THE CLAIM IS RECORDED TWICE IN THE ENGINE, WITH A MEASUREMENT BEHIND IT.  From
`paperkit/footdeps.py` (and near-verbatim in `paperkit/__init__.py`):

    render/checks/ ships its OWN bib.py, so a witness inserting that directory shadows the
    engine's parser and `from bib import dep_order` resolves to the wrong module.  MEASURED:
    removing these six lines reddened seven talk claims with "cannot import name 'dep_order'
    from bib (render/checks/bib.py)".  The insert is a PRIORITY CLAIM, not a reachability fix.

If that holds under every spelling, the inserts must stay whatever else changes and Ζ·engine·flat
is dead on arrival.

⚑⚑ BUT THE ARGUMENT IS ABOUT A FLAT NAME.  `paperkit.bib` and `render.checks.bib` are DIFFERENT
NAMES, and a directory early on sys.path cannot shadow a package attribute.  If the package
spelling survives the hostile order, the priority claim DISSOLVES rather than needing to be
preserved — the insert defends a spelling, not a property.

This constructs exactly the hostile case the comment describes (render/checks FIRST on sys.path)
and asks both spellings in one process, so the comparison is against one interpreter state rather
than two runs.

    python3 tools/shadowprobe.py     # exit 0 = the priority claim dissolves under packaging
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
OUT = sys.stdout


def _file_of(mod: ModuleType) -> str:
    """Read a module's source path as a plain string (ModuleType declares no attributes)."""
    f: object = getattr(mod, "__file__", None)
    return str(f) if isinstance(f, str) else "<none>"


def _has(mod: ModuleType, name: str) -> bool:
    """Report whether a module exposes `name` — the engine parser's tell is `dep_order`."""
    got: object = getattr(mod, name, None)
    return got is not None


def main() -> int:
    """Resolve both spellings with render/checks ahead of the engine, and compare."""
    # the hostile order the engine's comment names: a witness's own directory first
    sys.path.insert(0, str(ROOT / "render" / "checks"))
    sys.path.append(str(ROOT))

    OUT.write("sys.path[0] = render/checks — the order the inserts defend against\n\n")

    flat = importlib.import_module("bib")
    pkg = importlib.import_module("paperkit.bib")

    OUT.write(f"  flat  import bib               -> {_file_of(flat)}\n")
    OUT.write(f"        exposes dep_order?       -> {_has(flat, 'dep_order')}\n")
    OUT.write(f"  pkg   from paperkit import bib -> {_file_of(pkg)}\n")
    OUT.write(f"        exposes dep_order?       -> {_has(pkg, 'dep_order')}\n")

    differ = _file_of(flat) != _file_of(pkg)
    OUT.write(f"\n  the two names resolve to DIFFERENT files: {differ}\n")

    if differ and _has(pkg, "dep_order") and not _has(flat, "dep_order"):
        OUT.write("\n  ⚑ THE PRIORITY CLAIM DISSOLVES UNDER PACKAGING.  The flat name is\n"
                  "    shadowed — reproducing the exact measured failure — while the package\n"
                  "    name reaches the engine regardless of what sits earlier on sys.path.\n"
                  "    The insert defends a SPELLING, not a property, and retires with it.\n")
        return 0
    OUT.write("\n  ⚑ the package spelling did NOT survive the hostile order.  The insert is\n"
              "    load-bearing beyond spelling and Ζ·engine·flat needs a different answer.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
