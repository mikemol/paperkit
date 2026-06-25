#!/usr/bin/env python3
"""Behavioral-boundary examples for Τ·path — pinning tool resolution (resolver.clean_env's PATH).

⟨P, F, δ⟩.  clean_env already drops RELATIVE PATH entries (bnd-env).  Τ·path closes the residual —
WHICH absolute dir resolves a tool: by DEFAULT the host's absolute entries (deduplicated, keep
first); when PAPERKIT_PATH is declared, resolution is PINNED to exactly those absolute existing
dirs and the ambient, user-writable host PATH is dropped entirely (reproducibility + defence).

    python3 paperkit/tests/boundaries_path.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import resolver  # noqa: E402
import config as C  # noqa: E402

SEP = os.pathsep


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Τ·path — pinning tool resolution\n")
    saved = os.environ.get("PAPERKIT_PATH")
    try:
        os.environ.pop("PAPERKIT_PATH", None); C._ARGS.clear()
        e = resolver.clean_env({"PATH": SEP.join(["/usr/bin", "/bin", "/usr/bin", "rel", "."])})
        check("default: keeps the host's ABSOLUTE entries", e["PATH"].split(SEP) == ["/usr/bin", "/bin"])
        check("default: DEDUPES the dup-laden host PATH (keep first)", e["PATH"].split(SEP).count("/usr/bin") == 1)

        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            os.environ["PAPERKIT_PATH"] = SEP.join([t1, t2, "/does-not-exist-xyz", "relative/d"])
            e = resolver.clean_env({"PATH": "/usr/bin"})
            check("a declared PATH pins resolution to exactly the declared dirs", e["PATH"].split(SEP) == [t1, t2])
            check("the host's ambient PATH is DROPPED when pinned", "/usr/bin" not in e["PATH"])
            check("a non-existent declared dir is dropped", "/does-not-exist-xyz" not in e["PATH"])
            check("a relative declared dir is dropped", "relative/d" not in e["PATH"])
    finally:
        os.environ.pop("PAPERKIT_PATH", None) if saved is None else os.environ.__setitem__("PAPERKIT_PATH", saved)

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    saved = os.environ.get("PAPERKIT_PATH")
    try:
        C._ARGS.clear()
        with tempfile.TemporaryDirectory() as t:
            host = SEP.join(["/usr/bin", "/bin"])
            os.environ.pop("PAPERKIT_PATH", None); F = resolver.clean_env({"PATH": host})["PATH"]
            os.environ["PAPERKIT_PATH"] = t; P = resolver.clean_env({"PATH": host})["PATH"]
            ok = F.split(SEP) == ["/usr/bin", "/bin"] and P == t
            fails.append("pin-delta") if not ok else None
            print(f"  {'ok ' if ok else 'XX '}declaring PAPERKIT_PATH flips resolution from the host PATH to the pinned set")
            print(f"      P (pinned):  {t}  — exactly the declared dir")
            print("      F (default): /usr/bin:/bin  — the host's absolute entries")
            print("      δ (min delta): PAPERKIT_PATH being declared\n")
    finally:
        os.environ.pop("PAPERKIT_PATH", None) if saved is None else os.environ.__setitem__("PAPERKIT_PATH", saved)

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (6 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
