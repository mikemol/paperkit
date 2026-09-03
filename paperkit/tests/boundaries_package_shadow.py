#!/usr/bin/env python3
"""Behavioral-boundary examples for Ζ·build·shadow — a competing DIRECTORY named `paperkit`.

⟨P, F, δ⟩.  The engine's modules import each other FLAT (`import bib`), and `paperkit/__init__.py`
inserts its own directory on sys.path so that spelling resolves however the package is reached.
A predecessor probe tested only the FLAT collision (`render/checks/bib.py` shadowing `bib`), which
fails LOUDLY — `ImportError: cannot import name 'dep_order'`.  This suite tests the case that
actually bit and that the flat probe could not see:

    a second DIRECTORY named `paperkit`, earlier on sys.path, serving a whole stale engine.

⚑ WHY THE ARMS ASSERT ON `__file__` AND NEVER ON `hasattr`.  Measured 2026-09-02 against the real
`build/lib/paperkit/` (23 stale setuptools-copied modules, every one differing from the live tree,
three live modules absent entirely): `hasattr(bib, "dep_order")` was **True in every path order**,
including the one serving five-day-old code.  The stale copy is a former self, so it has the same
attribute NAMES — an arm that probes the attribute passes in both arms and proves nothing.  That is
the false-green shape this engine exists to refuse, and it is why identity must be read off the
resolved FILE.

⚑ AND THE SHADOW ENTRENCHES ITSELF.  The stale copy carries its OWN `sys.path.insert(0, _HERE)` —
the same line that makes the live package work — so once it is reached first it pins its directory
ahead of the live one.  The mechanism that serves the package form is the mechanism that, duplicated,
locks in the duplicate.

`build/` is gitignored (`.gitignore:35`), so `git status` never showed it: the hazard is a directory
on sys.path, not a file in a diff, and an ignore rule is necessary but NOT sufficient.  This suite is
the sufficient half — it fails whenever a competing package directory can win.

    python3 paperkit/tests/boundaries_package_shadow.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent   # the repo root, which HOLDS `paperkit/`
LIVE = ROOT / "paperkit"

# Resolve `paperkit.bib` in a FRESH interpreter and report the file it actually came from.
# A subprocess, not an importlib.reload: this process already has the live package imported, and a
# reload would measure THIS process's state rather than what a consumer's interpreter would do.
_PROBE = (
    "import json\n"
    "from paperkit import bib\n"
    "print(json.dumps({'file': bib.__file__, 'hasattr': hasattr(bib, 'dep_order')}))\n"
)


def resolve(path_entries: list[str]) -> dict[str, object]:
    """Import `paperkit.bib` under an explicit sys.path prefix; return where it resolved."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(path_entries)
    env.pop("PYTHONHOME", None)
    r = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _PROBE],
        cwd=tempfile.gettempdir(),   # never the repo root — cwd must not smuggle a path entry in
        env=env, capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        return {"file": None, "hasattr": None, "err": r.stderr.strip().splitlines()[-1:]}
    out: dict[str, object] = json.loads(r.stdout)
    return out


def plant_competitor(d: Path) -> Path:
    """Build a decoy package DIRECTORY named `paperkit` — the shape `build/lib/` has.

    It reproduces the two properties that make the real one dangerous: it is spelled `paperkit`,
    and its `__init__` inserts its own directory on sys.path (the live package's own idiom).
    Never planted inside the repo — a test that leaves an importable `paperkit` behind IS the bug.
    """
    pkg = d / "paperkit"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        "import os, sys\n"
        "_HERE = os.path.dirname(os.path.abspath(__file__))\n"
        "if _HERE not in sys.path:\n"
        "    sys.path.insert(0, _HERE)\n",
        encoding="utf-8",
    )
    # ⚑ The decoy DEFINES dep_order.  The whole point: the F arm must not be distinguishable by
    # the attribute, only by the file.  A decoy missing it would make hasattr look sufficient.
    (pkg / "bib.py").write_text("def dep_order(*a, **k):\n    return []\n", encoding="utf-8")
    return d


def main() -> int:
    fails: list[str] = []
    ran: list[str] = []

    def check(desc: str, cond: bool) -> None:
        # Λ·guard-must-not-copy — `ran` COUNTS the arms; no authored literal to drift.
        ran.append(desc)
        if not cond:
            fails.append(desc)
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Ζ·build·shadow — a competing DIRECTORY named `paperkit`\n")

    live_first = resolve([str(ROOT)])
    lf = str(live_first.get("file") or "")
    check("the live tree resolves `paperkit.bib` to the live tree",
          lf.startswith(str(LIVE)))

    with tempfile.TemporaryDirectory() as td:
        decoy = plant_competitor(Path(td))
        shadowed = resolve([str(decoy), str(ROOT)])
        sf = str(shadowed.get("file") or "")

        # ⚑ THE ARM THAT MATTERS.  Resolution is read off __file__.  Stated as the FACT the suite
        # asserts about the mechanism: a directory named `paperkit` earlier on the path WINS.
        check("a competing `paperkit/` dir earlier on the path WINS (read off __file__)",
              sf.startswith(str(decoy)) and not sf.startswith(str(LIVE)))

        # ⚑ THE ARM THAT EXPLAINS WHY THE OLD PROBE WAS BLIND.  This does not test the engine; it
        # tests the INSTRUMENT — it asserts that hasattr CANNOT tell the arms apart, so that if a
        # future edit ever weakens the arm above into an attribute check, this line documents that
        # the weaker check is vacuous.  If this ever fails, the decoy stopped modelling the hazard.
        check("hasattr CANNOT distinguish the arms — it is True on BOTH (why __file__ is required)",
              live_first.get("hasattr") is True and shadowed.get("hasattr") is True)

        # The repo must not be CARRYING such a directory.  This is the standing guard: `.gitignore`
        # hides `build/` from a diff, so nothing else in the tree would report its return.
        strays = sorted(
            str(p.parent.relative_to(ROOT))
            for p in ROOT.glob("*/**/paperkit/__init__.py")
            if not p.is_relative_to(LIVE) and ".venv" not in p.parts and "bazel-" not in str(p)
        )
        check(f"no second importable `paperkit/` package exists in the tree (found: {strays or 'none'})",
              not strays)

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    with tempfile.TemporaryDirectory() as td:
        decoy = plant_competitor(Path(td))
        P = resolve([str(ROOT)])                      # only the live tree reachable
        F = resolve([str(decoy), str(ROOT)])          # ONE extra sys.path entry
        pf, ff = str(P.get("file") or ""), str(F.get("file") or "")
        ok = pf.startswith(str(LIVE)) and ff.startswith(str(decoy))
        if not ok:
            fails.append("shadow-delta")
        print(f"  {'ok ' if ok else 'XX '}one sys.path entry flips the ENGINE that `from paperkit import bib` serves")
        print(f"      P (live):   {pf}")
        print(f"      F (shadow): {ff}")
        print("      δ (min delta): one directory named `paperkit` earlier on sys.path")
        print(f"      ⚑ hasattr(bib,'dep_order') = {P.get('hasattr')} in P and {F.get('hasattr')} in F"
              " — identical, which is why the arms read __file__\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
