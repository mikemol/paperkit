#!/usr/bin/env python3
"""Behavioral-boundary examples for environment sanitization — gate.clean_env.

⟨P, F, δ⟩ per the boundary practice.  A check is arbitrary code (cmd: is the universal
escape hatch), so it must run in a CONTROLLED environment, not whatever the gate
inherited — sshd's lesson against env injection.  Bounds: the allow-list keeps what a
check legitimately needs (PATH, locale, the membudget/paperkit knobs) and DROPS the
injection vectors (LD_PRELOAD, IFS, BASH_ENV, PYTHONPATH) and any unknown var; and
within the kept PATH it drops the RELATIVE/empty entries (Τ·path) that would resolve a
tool to the cwd — the project dir being gated.

    python3 paperkit/tests/boundaries_env.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gate  # noqa: E402

DIRTY = {
    "PATH": "/usr/bin" + os.pathsep + "." + os.pathsep + os.pathsep + "rel/x",  # abs kept; .,"",rel dropped
    "HOME": "/h", "LC_ALL": "C",                                     # kept: needed
    "MEMBUDGET_PARENT": "abcd", "PAPERKIT_CHECK_MB": "256",          # kept: paperkit's own
    "LD_PRELOAD": "/evil.so", "IFS": " \t", "BASH_ENV": "/inj.sh",   # dropped: injection
    "PYTHONPATH": "/x", "FOO": "bar",                               # dropped: injection / unknown
}


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    e = gate.clean_env(DIRTY)

    print("env-sanitization behaviors\n")
    check("keeps PATH's absolute dirs so a check's tools still resolve", e.get("PATH") == "/usr/bin")
    check("DROPS PATH's relative/empty entries (Τ·path — they resolve to the gated cwd)",
          all(p and os.path.isabs(p) for p in e.get("PATH", "").split(os.pathsep)))
    check("keeps HOME and locale (LC_ALL)", e.get("HOME") == "/h" and e.get("LC_ALL") == "C")
    check("keeps the membudget / paperkit knobs (MEMBUDGET_*, PAPERKIT_*)",
          e.get("MEMBUDGET_PARENT") == "abcd" and e.get("PAPERKIT_CHECK_MB") == "256")
    check("DROPS injection vectors (LD_PRELOAD, IFS, BASH_ENV, PYTHONPATH)",
          not any(k in e for k in ("LD_PRELOAD", "IFS", "BASH_ENV", "PYTHONPATH")))
    check("DROPS unknown vars (FOO) — default-deny, not block-list", "FOO" not in e)
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("a var survives iff it is on the allow-list (default-deny)",
         "a variable's membership in the allow-list",
         "PATH (listed) → kept", "PATH" in e,
         "LD_PRELOAD (unlisted) → dropped", "LD_PRELOAD" not in e),
        ("paperkit's own knobs pass; the shell's injection vectors do not",
         "the variable's name (PAPERKIT_CHECK_MB vs BASH_ENV)",
         "PAPERKIT_CHECK_MB → kept", "PAPERKIT_CHECK_MB" in e,
         "BASH_ENV → dropped", "BASH_ENV" not in e),
        ("a PATH entry survives iff it is absolute (Τ·path)",
         "the entry's absoluteness (/usr/bin vs .)",
         "/usr/bin (absolute) → kept", "/usr/bin" in e["PATH"].split(os.pathsep),
         ". (relative, = the gated cwd) → dropped", "." not in e["PATH"].split(os.pathsep)),
    ]
    for name, axis, p_lbl, p_ok, f_lbl, f_ok in pairs:
        ok = p_ok and f_ok
        fails.append(name) if not ok else None
        print(f"  {'ok ' if ok else 'XX '}{name}")
        print(f"      P (pass side): {p_lbl}")
        print(f"      F (flag side): {f_lbl}")
        print(f"      δ (min delta): {axis}\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (6 behaviors, 3 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
