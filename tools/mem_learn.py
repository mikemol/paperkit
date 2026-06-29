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
(observe ran without per-action cgroup isolation) is dropped — it carries no measurement."""
import json
import sys
from pathlib import Path

LO, HI = 128, 4096  # the pow2 reservation range (calc.bzl _RS)


def pow2(mb):
    b = LO
    while b < mb and b < HI:
        b *= 2
    return b


def resolution(stem):
    if stem.endswith("__dcalc"):
        return "def", stem[: -len("__dcalc")]
    if stem.endswith("__calc"):
        return "file", stem[: -len("__calc")]
    return None, stem


peaks = {}  # res -> {claim: mb}
for arg in sys.argv[1:]:
    p = Path(arg)
    res, claim = resolution(p.stem)
    if res is None:
        continue
    raw = p.read_text().strip()
    mb = (int(raw) if raw.isdigit() else 0) / (1024 * 1024)
    if mb <= 0:
        continue  # no isolated measurement; drop rather than learn a floor of 0
    peaks.setdefault(res, {})[claim] = mb

manifest = {"claims": {}}
for res, claims in sorted(peaks.items()):
    default = pow2(max(claims.values()))
    manifest[res] = default
    for claim, mb in sorted(claims.items()):
        b = pow2(mb)
        if b != default:
            manifest["claims"][claim] = b

print(json.dumps(manifest, indent=2, sort_keys=True))
