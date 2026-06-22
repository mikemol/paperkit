#!/usr/bin/env python3
"""Behavioral-boundary examples for Δ's content-addressed cache (Μ).

A Δ grade is a pure function of content_key(project) — the project's files plus the
engine.  So a cached grade is reused verbatim while that key holds, and recomputed
exactly when something a check could read changes.  Bounds: the key is deterministic,
tracks mutable inputs only, the cache reuses grades on an unchanged key, and --no-cache
recomputes the same answer.

    python3 paperkit/tests/boundaries_memoize.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import discriminate as D  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture import DISCRIMINATE, _write, entry  # noqa: E402


def _disc(proj, *flags):
    return subprocess.run([sys.executable, str(DISCRIMINATE), "--all", "--json", *flags, str(proj)],
                          capture_output=True, text=True).stdout


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    d = tempfile.mkdtemp()
    try:
        proj = _write(d, [entry("w", claim="alpha", check="cmd:true")], None,
                      (("s", "Sec"),), "t", False, False)

        print("Μ behaviors\n")
        k1, k2 = D.content_key(proj), D.content_key(proj)
        check("content_key is deterministic (same content → same key)", k1 == k2)

        (proj / "w.bib").write_text((proj / "w.bib").read_text() + "\n% edit\n")
        k3 = D.content_key(proj)
        check("a mutable input change → different key", k3 != k1)

        (proj / "note.log").write_text("ignored")
        k4 = D.content_key(proj)
        check("a non-input file (.log) → same key", k4 == k3)

        out1 = _disc(proj)
        check("first run writes the cache", (proj / ".delta-cache.json").exists())
        out2 = _disc(proj)
        check("second run (unchanged) returns identical grades",
              out1 == out2 and out1.strip().startswith("["))
        out3 = _disc(proj, "--no-cache")
        check("--no-cache recomputes the same grades", json.loads(out3) == json.loads(out1))
        print()

        print("⟨P, F, δ⟩ minimum-delta pairs\n")
        pairs = [
            ("the content key tracks mutable inputs only", "whether the changed file is an input",
             "edited .bib → key changes", k3 != k1,
             "added .log  → key holds", k4 == k3),
            ("a grade is reused iff the key holds", "the project content (via the cache)",
             "unchanged → cache hit, identical", out1 == out2,
             "--no-cache → recomputed, identical", json.loads(out3) == json.loads(out1)),
        ]
        for name, axis, p_lbl, p_ok, f_lbl, f_ok in pairs:
            ok = p_ok and f_ok
            fails.append(name) if not ok else None
            print(f"  {'ok ' if ok else 'XX '}{name}")
            print(f"      P (pass side): {p_lbl}")
            print(f"      F (flag side): {f_lbl}")
            print(f"      δ (min delta): {axis}\n")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (5 behaviors, 2 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
