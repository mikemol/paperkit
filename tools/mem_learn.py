#!/usr/bin/env python3
"""Τ·mem·learn — project a per-project memory manifest from observed cgroup peaks (the .peak output
groups of one project's pk_calc actions, measured under --config=memobserve).  This is the LEARN
step of the reservation ladder: a reservation is resolved (in the bib generator) down a
(project,resolution,claim) specificity ladder; this tool emits the per-project layer of that ladder.

Each arg is a `<claim>__{calc,dcalc}.peak` file holding one action's tree-peak RSS in bytes.
Output (stdout) is the project's manifest, DELTA-ENCODED against the next-coarser level:

    {"file": 256, "def": 1024, "claims": {"<claim>": <bucket>, ...}}

  - a resolution key (file/def) = pow2(max peak over that resolution's claims), the per-resolution
    default — recorded because it deviates from the cold-start floor;
  - "claims" holds an override ONLY for a claim whose own pow2 bucket differs from its resolution
    default (so ~0 intra-resolution variance ⇒ "claims" is empty, as the territory showed).

Buckets are clamped to the pow2 levels the resource_set map (calc.bzl _RS) provides.  A peak of 0
(observe ran without per-action cgroup isolation) is dropped — it carries no measurement.
"""
import json
import sys
from pathlib import Path

LO, HI = 4, 4096  # the pow2 reservation range (calc.bzl _RS) — starts TINY: an over-reservation
                  # is silent (idle cores), an under-reservation is LOUD (the cap kills, the
                  # failure names the cell, the next pass raises it).  Grow on evidence.


def pow2(mb):
    b = LO
    while b < mb and b < HI:
        b *= 2
    return b


def resolution(stem):
    """(resolution, claim) for a peak file's stem, or (None, stem) if it is not one of ours.

    Ζ·mem·def·blind — a DEF-sweep cell is a pk_eval named `<claim>__<site>`, not a pk_calc, so it
    matches neither suffix below and used to be skipped silently.  That left the EXPENSIVE
    resolution as the only unmeasured one: `def` could come from nothing but the cold-start floor
    (2048MB against a measured ~179MB file cell), and no amount of cold observing could correct it.

    A cell's peak is charged to the DEF resolution and to its claim, so the per-claim maximum over
    a claim's grid is that claim's def cost — which is the number a reservation needs, since the
    grid's cells run concurrently and each must fit.
    """
    if stem.endswith("__dcalc"):
        return "def", stem[: -len("__dcalc")]
    if stem.endswith("__calc"):
        return "file", stem[: -len("__calc")]
    if "__" in stem:                       # a pk_eval grid cell: <claim>__<site>
        return "def", stem.split("__", 1)[0]
    return None, stem


def main() -> int:
    """Ζ·mem·wire — the script body, guarded.  This module is imported for `pow2`/`resolution` by
    mem_db/mem_harvest/mem_project, and at module level it ran the whole aggregation and PRINTED a
    manifest — so importing a helper emitted JSON onto the importer's stdout.  A library and a
    script in one file need the guard; without it the library half is unusable.
    """
    peaks = {}


    unavailable = {}   # reason -> [claim]: named, never folded into 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        res, claim = resolution(p.stem)
        if res is None:
            continue
        raw = p.read_text().strip()
        # Τ·mem·observe·honest — a peak file may now say WHY it has no number ("unavailable:absent",
        # "unavailable:unreadable") instead of writing a 0 that reads as a measurement.  Count those
        # separately: dropping them is right, dropping them SILENTLY is what made 170 unmeasured cells
        # look like a measured corpus.  A cache hit and a clean result must not render identically.
        if raw.startswith("unavailable:"):
            unavailable.setdefault(raw.split(":", 1)[1], []).append(claim)
            continue
        mb = (int(raw) if raw.isdigit() else 0) / (1024 * 1024)
        # Drop un-isolated reads: 0 (cgroups absent / peak channel off) and anything above the largest
        # reservation bucket (a single sandboxed calc never needs >HI MB — a larger value is the SHARED
        # cgroup read of a non-`--config=memobserve` build, not this action's tree).  A dropped claim
        # falls through the ladder to its resolution default — never to a wrong learned floor.
        if mb <= 0 or mb > HI:
            continue
        peaks.setdefault(res, {})[claim] = mb

    if unavailable:
        for why, claims in sorted(unavailable.items()):
            print(f"mem_learn: {len(claims)} claim(s) UNAVAILABLE ({why}) — not measured this run, "
                  f"not a zero: {sorted(claims)[:4]}{'...' if len(claims) > 4 else ''}", file=sys.stderr)

    manifest = {"claims": {}}
    for res, claims in sorted(peaks.items()):
        default = pow2(max(claims.values()))
        manifest[res] = default
        for claim, mb in sorted(claims.items()):
            b = pow2(mb)
            if b != default:
                manifest["claims"][claim] = b

    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
