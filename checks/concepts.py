#!/usr/bin/env python3
"""checks/concepts.py — the SHARED concept-witness library.

A concept is authored ONCE — its records in the concept bibs, its witness here — and every VIEW that
imports it (paper, deep; README, pitch; later a guide/advocacy view) resolves its `concept:<key>`
check against this one module, instead of each view re-authoring a parallel — and often weaker —
witness.  (The README's old rm_delta GREPPED engine source; the shared witness below RUNS the real
grader, so importing the concept also upgrades the pitch's proof.)

Paths derive from __file__, so this runs from any project's cwd: README's `[checks.concept]` calls
`python3 checks/concepts.py <key>` (cwd = repo root); a paper-side importer calls
`python3 ../checks/concepts.py <key>` (cwd = paper/).  PAPERKIT_ENGINE (a paperkit knob, survives
clean_env) points the engine at a mutated variant during Δ's def-sweep, exactly as claims.py does.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = Path(os.environ.get("PAPERKIT_ENGINE") or ROOT / "paperkit")
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests"))
import _fixture as fx  # noqa: E402  (the validated fixture builder)


def adequacy_pitch():
    # the Δ grade ladder, the PITCH face — a passing check only proves a sentence named a verifier,
    # not that the verifier ENTAILS it, so Δ grades how much each check can actually fail.  Witnessed
    # the STRONG way (run the real grader over a fixture, not grep the engine source): a presupposed
    # file: grades vacuous, a content-sensitive cmd: grades behavioral.
    recs = json.loads(fx.discriminate(
        [fx.entry("vac", claim="v", check="file:w.bib"),
         fx.entry("beh", claim="b", check="cmd:grep -q TOKEN a.txt", frm="vac")],
        "--all", "--json", assets={"a.txt": "TOKEN\n"})[1])
    g = {r["key"]: r["grade"] for r in recs}
    assert g["vac"] == "vacuous" and g["beh"] == "behavioral", f"grade ladder wrong: {g}"


CONCEPTS = {
    "adequacy-pitch": adequacy_pitch,
}


def main(argv) -> int:
    if not argv or argv[0] not in CONCEPTS:
        print(f"usage: concepts.py <{'|'.join(CONCEPTS)}>", file=sys.stderr)
        return 2
    try:
        CONCEPTS[argv[0]]()
    except AssertionError as e:
        print(f"concept {argv[0]}: FAIL — {e}", file=sys.stderr)
        return 1
    print(f"concept {argv[0]}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
