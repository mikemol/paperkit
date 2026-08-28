#!/usr/bin/env python3
r"""Ρ·deck·observe·gate — the OBSERVED analogue of the gate's PROJECT invariant.

project()'s output is held byte-identical against a committed file: prose ≡ projection, so the
prose cannot drift from the claims.  observe()'s units had no such hold.  `rnd-slides` checks that
the observed deck CORRESPONDS to whatever units observe() returns at that moment, which is a
consistency check between two things computed in the same breath — it cannot catch the units
themselves drifting from the claim-DAG, because both sides move together.

So the segmentation gets a committed artifact of its own: `assets/<project>-units.tsv`, one unit per
line (section, then its claim keys, tab-separated).  This check regenerates it and compares.  A
claim added, removed, re-sectioned, or re-grounded moves the partition, which moves the manifest,
which fails here — the same "the artifact is a build output, not a source" discipline the prose
already lives under.

WHY A MANIFEST AND NOT THE .ODP.  The deck is a binary produced by pandoc and LibreOffice; two runs
need not be byte-identical, and gating on that would be gating the toolchain rather than the
projection (which is why the render project's own deck warrants are tier=toolchain).  The MANIFEST
is the projection's own output — pure, deterministic, diffable in review — and it is where drift
between the claims and the cut actually shows.  The deck is then gated to correspond to the
manifest by rnd-slides, so the chain closes: claims → units (here) → slides (there).

    python3 checks/units.py            # print the current segmentation
    python3 checks/units.py --check    # assert the committed manifest IS the segmentation
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "paperkit"))

# The observed projects and the genre each is cut under.  A project appears here once it commits a
# manifest; the genre is part of the declaration because a different genre is a different cut, and
# a manifest that did not say which would be ungateable.
OBSERVED = {
    "paper": "talk",       # the densest cut available.  (A count once sat here — "87 claims,
                           #   68 grounding edges" — against slides.bib's 84/57 for the same
                           #   project: two uncoordinated snapshots, neither marked stale.
                           #   Dropped rather than re-measured; the manifest itself carries
                           #   the live numbers and cannot drift from them.)
    "setup": "talk",       # 26 edges: a SECOND grounded project, so the gate is not one instance
    "talk": "talk",        # the delivered talk: a FOURTH project, and the only one whose claims
                           #   are a mix of imported certificates, own witnesses and honest
                           #   premises — so its manifest is the one that would move if a
                           #   post-talk edit quietly re-sectioned or re-grounded a claim.
    "root": "talk",        # 9 units, 9 placed assets — the asset-heaviest, and DEGENERATE
                           #   (no rests-on), so it exercises the σ-fallback path the dense
                           #   projects never reach.  One observed project could not tell whether
                           #   the manifest held for a document the partition falls back on.
}


# Ρ·witness·family·floor — OBSERVED is a DELIBERATE subset (not every project needs a manifest),
# so its domain cannot be derived.  But a deliberate subset and a silently-shrunk one render
# identically: removing an entry is indistinguishable from never having added it.  The floor is a
# declared literal a human must EDIT DOWN, owned by this comment rather than by the dict it guards
# — the weak-but-real form of independence, since a constant computed from OBSERVED would move
# with it.  (Measured elsewhere tonight: deriving a domain without a floor let it shrink 4->3 and
# still pass.)  Raise it when a project joins; lowering it is the edit that must be argued for.
_OBSERVED_FLOOR = 4


def manifest(project_dir: Path, genre_name: str) -> str:
    """The segmentation as text: one unit per line, section then keys, tab-separated."""
    import project as P
    cfg = P.load_config(project_dir)
    units = P.observe(cfg, genre_name, project_dir)
    return "".join(f"{u['section']}\t" + "\t".join(u["keys"]) + "\n" for u in units)


def main(argv: list) -> int:
    check = "--check" in argv
    rc = 0
    if len(OBSERVED) < _OBSERVED_FLOOR:
        print(f"units --check: OBSERVED holds {len(OBSERVED)} project(s), below the declared "
              f"floor of {_OBSERVED_FLOOR} — a manifest was dropped, which reads identically to "
              f"never having been added.  Lower the floor deliberately or restore the entry.",
              file=sys.stderr)
        return 1
    for name, genre_name in sorted(OBSERVED.items()):
        want = manifest(_ROOT if name == "root" else _ROOT / name, genre_name)
        path = Path(__file__).resolve().parent.parent / "assets" / f"{name}-units.tsv"
        if not check:
            print(want, end="")
            continue
        if not path.exists():
            print(f"units --check: {path.name} is MISSING — the segmentation has no committed "
                  f"artifact, so nothing holds it to the claim-DAG", file=sys.stderr)
            rc = 1
            continue
        got = path.read_text()
        if got != want:
            gl, wl = got.splitlines(), want.splitlines()
            drift = next((i for i, (a, b) in enumerate(zip(gl, wl)) if a != b), min(len(gl), len(wl)))
            print(f"units --check: {path.name} ≠ segmentation — {len(gl)} committed units vs "
                  f"{len(wl)} projected; first divergence at unit {drift + 1}:\n"
                  f"  committed: {gl[drift] if drift < len(gl) else '(past end)'}\n"
                  f"  projected: {wl[drift] if drift < len(wl) else '(past end)'}\n"
                  f"Regenerate: python3 paperkit/project.py --observe --genre {genre_name} "
                  f"{'.' if name == 'root' else name} > render/assets/{name}-units.tsv",
                  file=sys.stderr)
            rc = 1
        else:
            print(f"units --check: {path.name} ≡ segmentation ({len(want.splitlines())} units, "
                  f"genre {genre_name})")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
