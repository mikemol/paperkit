#!/usr/bin/env python3
"""Ζ·canary — the CHECK: discovers the probe exactly the way real witnesses discover the
engine — `Path(__file__).resolve()` — so it CO-DEGRADES with them by construction: under a
sandbox whose staged files are symlinks (processwrapper), resolve() escapes to the REAL tree
and imports the real, unmutated probe; under the hermetic linux-sandbox it stays inside and
imports the staged (possibly mutated) bytecode.  Exit 0 = truth() holds; the pos cell (truth's
body dropped) MUST flip this — if it doesn't, the harness is degraded and pk_canary fails LOUD."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canary_probe  # noqa: E402

assert canary_probe.truth() == 42, "the canary probe's truth() no longer holds"
