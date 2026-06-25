#!/usr/bin/env python3
"""Behavioral-boundary examples for Ω·config — the ONE configurable-resolution pipeline
(config.resolve / apply_args / positionals).

⟨P, F, δ⟩.  Every knob resolves the same way: explicit ARG > ENV var > project CONFIG
(paper.toml [paper]) > default.  apply_args captures args PROCESS-LOCALLY (not os.environ), so
a check the grader spawns never inherits the grader's own flags and re-grades under them.

    python3 paperkit/tests/boundaries_config.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config as C  # noqa: E402


def reset(p):
    C._ARGS.clear()
    os.environ.pop(p.env, None)


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Ω·config — arg > env > config > default, one rule for every knob\n")
    p = C.RESOLUTION   # value: env PAPERKIT_RESOLUTION, config 'resolution', default 'file'
    reset(p)
    check("default when nothing is set", C.resolve(p) == "file")
    check("project config (paper.toml [paper]) overrides the default", C.resolve(p, {"resolution": "def"}) == "def")
    os.environ[p.env] = "file"
    check("env overrides project config", C.resolve(p, {"resolution": "def"}) == "file")
    C.apply_args(["--resolution", "def"])
    check("an explicit arg overrides the env", C.resolve(p, {"resolution": "def"}) == "def")
    check("apply_args is PROCESS-LOCAL — it does NOT mutate os.environ (a spawned check won't "
          "inherit the grader's flags)", os.environ.get(p.env) == "file")
    reset(p)

    check("a flag is False by default", C.resolve(C.SAFE) is False)
    C.apply_args(["--safe"]); check("a flag set by its arg is True", C.resolve(C.SAFE) is True)
    C._ARGS.clear()
    check("a flag set by [paper] config is True", C.resolve(C.SAFE, {"safe": True}) is True)
    C.apply_args(["--without-k"]); check("a flag honours its alias (--without-k)", C.resolve(C.WITHOUT_K) is True)
    C._ARGS.clear()

    os.environ[p.env] = "bogus"
    raised = False
    try:
        C.resolve(p)
    except SystemExit:
        raised = True
    os.environ.pop(p.env, None)
    check("a value outside the param's choices is REFUSED", raised)
    check("positionals strips flags + valued options, keeps the project dir",
          C.positionals(["--min-strength", "behavioral", "--safe", "myproj"]) == ["myproj"])

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    reset(p); os.environ[p.env] = "file"
    F = C.resolve(p)
    C.apply_args(["--resolution", "def"]); P_ = C.resolve(p)
    ok = F == "file" and P_ == "def"
    fails.append("arg-over-env") if not ok else None
    reset(p)
    print(f"  {'ok ' if ok else 'XX '}the same knob: an explicit arg flips the resolved value; the env alone does not")
    print("      P (arg given):  resolve == 'def'   (--resolution def)")
    print("      F (env only):   resolve == 'file'  (PAPERKIT_RESOLUTION=file)")
    print("      δ (min delta): the presence of the explicit arg, which overrides the env\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (11 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
