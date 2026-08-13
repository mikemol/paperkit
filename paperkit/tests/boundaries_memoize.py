#!/usr/bin/env python3
"""Behavioral-boundary examples for Δ's cache (Μ, Δ·footprint-cache).

A Δ grade is a pure function of the content a check reads — content_key(project) is the
coarse soundness basis (project + engine files).  The cache realizes it PER CHECK: each
grade is keyed on its read footprint (Φ) plus the engine epoch, so editing a file re-grades
only the checks that READ it, leaving the rest reused — and for a behavioral grade at DEFINITION
granularity (Δ·grain), so editing a def re-grades only the checks measured sensitive to that def,
while a file-granular grade keeps the whole-file key.  Bounds: content_key is deterministic
and tracks mutable inputs only; the cache reuses grades on unchanged inputs; an edit
invalidates exactly the checks whose footprint it touches; and --no-cache recomputes the same.

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
from _fixture_model import DISCRIMINATE, _write, entry  # noqa: E402


def _disc(proj, *flags):
    return subprocess.run([sys.executable, str(DISCRIMINATE), "--all", "--json", *flags, str(proj)],
                          capture_output=True, text=True).stdout


def _grades(out):
    # the comparable grade CONTENT, provenance aside: a cache hit is honestly visible in
    # the per-check `grader` field (witness-the-live-path), so compare grades, not bytes.
    return [{k: v for k, v in r.items() if k != "grader"} for r in json.loads(out)]


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
        check("second run (unchanged) returns the same grades",
              _grades(out2) == _grades(out1) and out1.strip().startswith("["))
        check("a cache hit is VISIBLE — the reused run reports grader 'cache'",
              all(r.get("grader") == "cache" for r in json.loads(out2)))
        out3 = _disc(proj, "--no-cache")
        check("--no-cache recomputes the same grades", _grades(out3) == _grades(out1))

        # Δ·footprint-cache: editing a file re-grades ONLY the checks that READ it.  The
        # per-check grader field shows it — the toucher is graded fresh, the rest "cache".
        fpp = _write(tempfile.mkdtemp(),
                     [entry("ca", claim="reads a", check="cmd:grep -q FOO fa.txt"),
                      entry("cb", claim="reads b", check="cmd:grep -q BAR fb.txt")],
                     {"fa.txt": "FOO\n", "fb.txt": "BAR\n"}, (("s", "Sec"),), "t", False, False)

        def graders(p):
            return {r["check"]: r.get("grader") for r in json.loads(_disc(p))}

        graders(fpp)                                   # cold run: populate the per-check cache
        (fpp / "fa.txt").write_text("FOO EDITED\n")    # touch only ca's footprint
        g = graders(fpp)
        ca_fresh = g.get("cmd:grep -q FOO fa.txt") != "cache"
        cb_reused = g.get("cmd:grep -q BAR fb.txt") == "cache"
        check("editing fa.txt re-grades the check that READS it (ca fresh)", ca_fresh)
        check("...and leaves the check that does not (cb) reused from cache", cb_reused)

        # Δ·grain — the per-check key is DEF-granular when the grade MEASURES def sensitivity
        # (behavioral, `tests` naming `file::qual`): a module edit then re-grades only the checks
        # sensitive to the DEFINITIONS it changed, not every check that reads the module.
        gd = Path(tempfile.mkdtemp())
        mod = gd / "mod.py"
        fh, fine = D._footprint_hash, D._fine
        DEF = fine({"grade": "behavioral", "tests": ["mod.py::foo"]})   # sensitive to foo, not bar
        FILE = fine({"grade": "behavioral", "tests": ["mod.py"]})       # whole-file sensitive
        mod.write_text("def foo():\n    return 1\n\ndef bar():\n    return 2\n")
        k_def0, k_file0 = fh(gd, ["mod.py"], DEF), fh(gd, ["mod.py"], FILE)
        mod.write_text("def foo():\n    return 1\n\ndef bar():\n    return 999\n")     # non-depended
        reuse_nondep = fh(gd, ["mod.py"], DEF) == k_def0
        mod.write_text("def foo():\n    return 42\n\ndef bar():\n    return 2\n")      # depended
        regrade_dep = fh(gd, ["mod.py"], DEF) != k_def0
        mod.write_text("def foo():\n    return 12345\n\ndef bar():\n    return 2\n")   # def-body edit
        sound_file = fh(gd, ["mod.py"], FILE) != k_file0
        shutil.rmtree(gd, ignore_errors=True)
        check("Δ·grain: a def the check does NOT depend on → grade reused (the def key holds)", reuse_nondep)
        check("Δ·grain: a def the check DEPENDS on → re-graded (the def key changes)", regrade_dep)
        check("Δ·grain SOUNDNESS: a FILE-granular grade keeps the WHOLE-file key — a def-body edit invalidates",
              sound_file)
        print()

        print("⟨P, F, δ⟩ minimum-delta pairs\n")
        pairs = [
            ("the content key tracks mutable inputs only", "whether the changed file is an input",
             "edited .bib → key changes", k3 != k1,
             "added .log  → key holds", k4 == k3),
            ("a grade is reused iff the inputs hold", "the project content (via the cache)",
             "unchanged → cache hit, same grades", _grades(out1) == _grades(out2),
             "--no-cache → recomputed, same grades", _grades(out3) == _grades(out1)),
            ("the cache invalidates PER CHECK, on its footprint", "which check's footprint the edited file is in",
             "ca reads fa.txt (edited) → re-graded", ca_fresh,
             "cb reads fb.txt (untouched) → reused", cb_reused),
            ("Δ·grain keys on the DEFINITIONS a check depends on, not the whole file",
             "whether the edited def is in the check's measured sensitivity set",
             "non-depended def edited → grade reused", reuse_nondep,
             "depended def edited → grade re-graded", regrade_dep),
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
    print("BOUNDARIES: PASS (12 behaviors, 4 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
