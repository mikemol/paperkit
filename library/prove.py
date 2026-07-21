#!/usr/bin/env python3
"""library/prove.py — Λ·witness: a witness PROVES ITSELF.

A concept witness is not merely an executable that passes or fails; it is a PROOF-CARRYING object.
Run in prove mode it emits its own CERTIFICATE — ⟨verdict, sensitivity fingerprint⟩ — so the proof can
travel WITH the witness wherever it is imported, instead of each importing view re-deriving it (which
duplicates the sweep) or delegating without it (which drops the fingerprint and blinds the view's ∂²).

ONE calculation, two faces.  This is the EXECUTABLE's self-proving face; the build caches the identical
measurement as `<key>__dcalc` and views import that.  They stay byte-equivalent because this runs the
SAME oracle the build runs — `discriminate.py --only <key> --calc --resolution def` over the owner —
rather than re-implementing the sweep.  A second implementation would be a second thing to drift.

    python3 concepts.py <key> --prove      # the certificate, as JSON
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

OWNER = Path(__file__).resolve().parent                 # the library: the concept's owner
ROOT = OWNER.parent
ENGINE = Path(os.environ.get("PAPERKIT_ENGINE") or ROOT / "paperkit")


def certificate(key: str) -> dict:
    """This witness's ADEQUACY CERTIFICATE.  The def-resolution sweep mutates ENGINE def-sites and
    re-runs the witness; the sites whose mutation flips it are its sensitivity fingerprint — which, for
    a witness that exercises the grader, IS the engine.  That is what makes the certificate worth
    importing: it carries the measured ground of the claim, not a bare verdict."""
    # Λ·prove·resolution — the fingerprint's GROUND is the resolution that measured it, so the
    # certificate must carry it.  Def-resolution is structurally unavailable to a downstream consumer
    # (the engine is a compiler on the box, not a directory in their repo, so _sandbox_setup's Ν·loud
    # refusal fires — correctly), which means downstream certificates are FILE-resolution.  An
    # unlabelled fingerprint read as a def fingerprint OVERSTATES the ground it carries; a labelled
    # one is honestly weaker.  Reported by a downstream consumer who now records it explicitly.
    resolution = "def"
    argv = [sys.executable, str(ENGINE / "discriminate.py"), "--only", key,
            "--calc", "--resolution", resolution, str(OWNER)]
    r = subprocess.run(argv, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"prove {key}: the def-sweep failed — {r.stderr.strip()[-400:]}")
    calc = json.loads(r.stdout)
    baseline, sens = bool(calc.get("baseline")), calc.get("sens", [])
    sys.path.insert(0, str(ENGINE))
    from grade import _grade_from_sens      # the ONE ladder — derived, never re-declared here
    return {
        "concept": key,
        "owner": OWNER.name,
        "resolution": resolution,     # the frame the fingerprint was measured in — never implicit
        "claim": calc.get("claim", key),
        "verdict": "pass" if baseline else "fail",
        "baseline": baseline,
        "grade": _grade_from_sens(baseline, sens)["grade"],
        "sens": sens,
        "fingerprint": sens,                # alias: the ⟨verdict, fingerprint⟩ vocabulary
    }
