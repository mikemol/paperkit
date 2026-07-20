#!/usr/bin/env python3
"""library/concepts.py — the concept-witness LIBRARY (the owner of each concept's proof).

A concept is authored ONCE — its record in the library's concepts.bib, its witness here — and the
library GRADES each witness once (a def-sweep, engine fingerprint) and exports that as a certificate.
Every VIEW that cites the concept (paper, deep; README, pitch; later a guide) resolves its
`concept:<key>` check by IMPORTING the certificate (verdict + fingerprint), instead of re-authoring a
parallel — and often weaker — witness.  (The README's old rm_delta GREPPED engine source; this witness
RUNS the real grader, so importing the concept also upgrades the pitch's proof.)

The library runs the witness as a plain `cmd:python3 concepts.py <key>` (cwd = library/).  Paths derive
from __file__: ROOT = the repo root (parents[1]), ENGINE = ROOT/paperkit.  PAPERKIT_ENGINE (a paperkit
knob, survives clean_env) points the engine at a mutated variant during Δ's def-sweep, so mutating an
engine def-site flips the witness → the certificate's sensitivity fingerprint IS the engine.
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
    # one witness, two keys: the README's pitch face and paper's deep grade-ladder face resolve to the
    # SAME grader run — the adequacy concept is authored once here, each view imports the certificate.
    "adequacy-pitch": adequacy_pitch,
    "grade-ladder": adequacy_pitch,
}


def main(argv) -> int:
    prove_mode = "--prove" in argv
    argv = [a for a in argv if a != "--prove"]
    if not argv or argv[0] not in CONCEPTS:
        print(f"usage: concepts.py <{'|'.join(CONCEPTS)}> [--prove]", file=sys.stderr)
        return 2
    if prove_mode:
        # Λ·witness — the SELF-PROVING face: emit this witness's own certificate ⟨verdict, sensitivity
        # fingerprint⟩ instead of a bare pass/fail, so the proof travels with the witness to every view
        # that imports it.  The same measurement the build caches as <key>__dcalc (see prove.py).
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import prove
        print(json.dumps(prove.certificate(argv[0]), indent=2))
        return 0
    try:
        CONCEPTS[argv[0]]()
    except AssertionError as e:
        print(f"concept {argv[0]}: FAIL — {e}", file=sys.stderr)
        return 1
    print(f"concept {argv[0]}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
