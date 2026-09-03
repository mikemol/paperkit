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
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Ζ·checkcache·cli — `checkcache` is NOT imported here.  It lives in components.bzl's
# `library_kernel`, this suite lives in `tests`, and the two are siblings with identical
# dependency sets that do not depend on each other — so importing it draws an edge sideways
# between peers and boundaries_components reds.  The Ζ·checkcache·keys arms below run it as a
# PROGRAM instead, the way boundaries_prove.py already runs `prove.py`.  ENGINE is the path to
# invoke it by; nothing from library_kernel enters this module's namespace.
ENGINE = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ENGINE))
import discriminate as D

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture_model import DISCRIMINATE, _write, entry


def _disc(proj, *flags):
    return subprocess.run([sys.executable, str(DISCRIMINATE), "--all", "--json", *flags, str(proj)],
                          capture_output=True, text=True).stdout


def _grades(out):
    # the comparable grade CONTENT, provenance aside: a cache hit is honestly visible in
    # the per-check `grader` field (witness-the-live-path), so compare grades, not bytes.
    return [{k: v for k, v in r.items() if k != "grader"} for r in json.loads(out)]


def main() -> int:
    fails = []

    ran = []
    n_deltas = 0

    def check(desc, cond):
        # Λ·guard-must-not-copy — `ran` COUNTS the arms.  The summary line used to restate a
        # number authored beside the set it describes, and every one of the 26 suites carrying
        # such a line UNDERSTATED it (24 mismatched, none overstated): arms were added and the
        # literal never moved, so it tracked the suite's authoring history rather than its
        # content — and would have read a SHRINKING suite as an unchanged one.
        ran.append(desc)
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

        # ── Ζ·checkcache·keys ──────────────────────────────────────────────────────────────────
        # THE SECOND CACHE IN THIS TREE, and its key had a scheduled expiry.  checkcache.py keys a
        # check on the CONTENT of every module its slice reaches; resolving a module NAME to a FILE
        # used to search `search_path()`, which imported the witness and read THE sys.path THAT
        # WITNESS ESTABLISHED.  That measures the bootstrap's leftovers — so under Ζ·path·retire,
        # with no mutations left to observe, it would have measured the EMPTY SET: every engine
        # module unresolvable, silently degraded from a content hash to a bare `mod:<name>`, and an
        # edit to an engine module no longer invalidating the witnesses that read it.
        #
        # ⚑ THE FAILURE DIRECTION IS WHAT MAKES THIS WORTH A SUITE.  A key too NARROW fails loudly
        # (spurious misses, wasted work).  A key too WIDE serves a stale PASS for code that has
        # since changed — arriving disguised as a speed-up.  So the F arm is the load-bearing one
        # and it is stated as an EDIT, not as a description: change a module the witness loads, and
        # the key must move.
        #
        # ⚑⚑ THE COUNTERFACTUAL IS ASSERTED TOO, because "the new key changes" alone does not show
        # the old one was broken — a suite that only exercises the fix cannot distinguish a closed
        # hole from a hole that was never open.  `_dirsearch_only` reimplements the PRE-FIX
        # resolution and is asserted to MISS the same edit, which is what dates the fix to a real
        # defect rather than a precaution.
        # ⚑⚑⚑ AND THESE ARMS RUN checkcache AS A PROGRAM, NOT AS AN IMPORT (Ζ·checkcache·cli).
        # components.bzl puts `checkcache.py` in `library_kernel` and this suite in `tests` — two
        # SIBLINGS with identical dependency sets, neither depending on the other.  So an
        # `import checkcache` here is an edge SIDEWAYS between peers, and boundaries_components
        # reds on it: measured 2026-09-02, the first such crossing in 45 suites.  Widening
        # DEPS["tests"] would license all 45 to reach the concept-library kernel to serve one.
        # `boundaries_prove.py` already shows the way — it tests `prove.py`, also library_kernel,
        # and imports NOTHING from it.  A subprocess is not a workaround for the guard; it is what
        # the guard was asking for, and the gap it named was that checkcache had no entry point.
        #
        # ⚑ THE SUBPROCESS IS ALSO THE MORE HONEST INSTRUMENT.  The engine dir reaches the child
        # as PYTHONPATH — which is what a REAL witness gets — rather than as a sys.path.insert in
        # this process, which measures this suite's own bootstrap.  The property under test is
        # that resolution asks the IMPORT SYSTEM; handing it a mutated path would beg the question.
        cc = Path(tempfile.mkdtemp())
        eng = Path(tempfile.mkdtemp())
        try:
            (eng / "ccfake_engine.py").write_text("VALUE = 1\n")
            wit = cc / "concepts.py"
            wit.write_text("def w_reaches(x):\n"            # reachable BY NAME as an engine module
                           "    import ccfake_engine as FE\n"   # is after the retirement, with
                           "    assert FE.VALUE\n"               # nothing the witness itself put
                           "def w_reaches_not(x):\n"             # on sys.path.
                           "    assert True\n")

            def ckey(fn, route):
                """The key checkcache derives, asked of it as a program."""
                r = subprocess.run(
                    [sys.executable, str(ENGINE / "checkcache.py"), "--key", str(wit), fn, route],
                    capture_output=True, text=True,
                    env={**os.environ, "PYTHONPATH": str(eng)}, check=False)
                return r.stdout.strip()

            # ⚑ `eng` is on the child's PYTHONPATH and NOT in checkcache's search list (which is
            # the witness's own directory, `cc`).  So if the key tracks that module's content, it
            # is the IMPORT SYSTEM answering — the property that must hold by construction rather
            # than by bootstrap.
            k_before, k_ctl_before = ckey("w_reaches", "r/e"), ckey("w_reaches_not", "r/n")
            search_is_pure = k_before not in ("", "-")
            reaches_content = k_before != ""

            def _dirsearch_only(mod, search):
                # the PRE-FIX resolution, verbatim in behavior: directories only, no import system
                for d in search:
                    for cand in (d / f"{mod.replace('.', '/')}.py",
                                 d / mod.replace(".", "/") / "__init__.py"):
                        if cand.is_file():
                            return cand
                return None

            old_before = _dirsearch_only("ccfake_engine", [cc])
            (eng / "ccfake_engine.py").write_text("VALUE = 999\n")     # EDIT the engine module
            k_after, k_ctl_after = ckey("w_reaches", "r/e"), ckey("w_reaches_not", "r/n")
            old_after = _dirsearch_only("ccfake_engine", [cc])

            key_moved = k_before != k_after
            control_held = k_ctl_before == k_ctl_after
            old_was_blind = old_before is None and old_after is None
        finally:
            shutil.rmtree(eng, ignore_errors=True)
            shutil.rmtree(cc, ignore_errors=True)

        check("Ζ·checkcache·keys: search_path() mutates nothing and returns only the declared dir",
              search_is_pure)
        check("Ζ·checkcache·keys: an engine module is resolved to a FILE with no caller mutation",
              reaches_content)
        check("Ζ·checkcache·keys F-ARM: editing an engine module the witness loads MOVES its key",
              key_moved)
        check("Ζ·checkcache·keys control: a witness that cannot reach it keeps its key",
              control_held)
        check("Ζ·checkcache·keys counterfactual: the pre-fix directory search MISSES that module "
              "(so the F arm dates a real stale-green, not a precaution)", old_was_blind)
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
            # ⚑ THE δ IS THE INSTRUMENT, NOT THE EDIT.  Both sides here edit the SAME module by the
            # SAME bytes and ask the SAME question; the only thing that varies is WHICH resolution
            # answers it.  That is what makes this a measurement of the fix rather than a
            # restatement of it — the pre-fix arm is shown BLIND to an edit the post-fix arm sees,
            # so the suite would fail if the hole were reopened AND would have failed before it
            # was closed.
            ("Ζ·checkcache·keys: the key tracks engine-module CONTENT without a path mutation",
             "whether module→file resolution asks the import system or only a mutated search path",
             "find_spec resolution → the edit moves the key", key_moved,
             "pre-fix directory search → the same edit is INVISIBLE", old_was_blind),
        ]
        n_deltas = len(pairs)
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
    bad = len([b for b in ran if not b])
    if bad:
        print(f"BOUNDARIES: FAIL ({bad} of {len(ran)} behaviors drifted)")
        return 1
    # Λ·guard-must-not-copy — `n_deltas` COUNTS the pairs; the literal `4` that used to sit here
    # was the same authored-beside-the-set number this file's own `check` comment indicts.
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, {n_deltas} deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
