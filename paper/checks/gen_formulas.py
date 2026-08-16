#!/usr/bin/env python3
"""Generate the paper's formula table from the claims that OWN the formulas.

The formula table (assets/formulas.md, placed by edge-formulas) is a second PROJECTION of the same
claim-DAG the paper projects — it gathers, as native math, the formulas already stated inside the
grounding-edge claims (edge-rests-grounds, grounding-reflected, emergence-collapse).  Authoring it by
hand would COPY the formulas the claims own, and a copy drifts.  So it is GENERATED here from the
claims' own inline math, and gated `fresh` (regenerate + byte-diff, exactly as config/ generates
knobs.md from the knob registry) — the table cannot drift from the claims because it IS a view of
them.  This is the paper's thesis applied to the paper's own table: a projection of the claim-DAG,
not authored prose.

    python3 checks/gen_formulas.py            # print the table to stdout (the fresh source)
    python3 checks/gen_formulas.py --check     # assert assets/formulas.md == the projection
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "paperkit"))
import bib  # noqa: E402

# Each row: the claim that owns the formula, a short relation label, and which of the claim's math
# spans is the row's formula (a claim may carry more than one — index into its spans).  This is the
# ONLY authored part: the label and the selection; the FORMULA itself is read from the claim.
ROWS = [
    ("edge-rests-grounds", "clamp", 0,
     "the effective grade is the weakest along `rests-on`"),
    ("grounding-reflected", "disjoint", 0,
     "a grounding edge the measurement cannot see"),
    ("emergence-collapse", "increment", 0,
     "the claim's irreducible sensitivity residual"),
    ("emergence-collapse", "collapse", 1,
     "the claim adds no sensitivity beyond its grounding"),
]

# an inline-math span in a claim value: $...$ with escaped-$ ignored (mirrors the projector's shield)
_MATH = re.compile(r"(?<!\\)\$(?!\$)(.+?)(?<!\\)\$", re.S)


def _claims() -> dict:
    recs = {}
    for f in sorted((Path(__file__).resolve().parents[1]).glob("*.bib")):
        recs.update(bib.parse(f))
    return recs


def table() -> str:
    recs = _claims()
    lines = ["| relation | claim | formula |", "|----------|-------|---------|"]
    for key, label, idx, gloss in ROWS:
        claim = recs.get(key, {}).get("claim", "")
        spans = _MATH.findall(claim)
        if idx >= len(spans):
            sys.exit(f"gen_formulas: claim {key} has no math span #{idx} — the table's owner changed")
        lines.append(f"| {label} | {gloss} | ${spans[idx].strip()}$ |")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    out = table()
    if "--check" in argv:
        asset = Path(__file__).resolve().parents[1] / "assets" / "formulas.md"
        if not asset.exists():
            print(f"gen_formulas --check: {asset} is absent — regenerate", file=sys.stderr)
            return 1
        if asset.read_text().strip() != out.strip():
            print("gen_formulas --check: assets/formulas.md drifted from the claims that own the "
                  "formulas — regenerate (checks/gen_formulas.py > assets/formulas.md)", file=sys.stderr)
            return 1
        print("gen_formulas --check: the formula table matches its owning claims")
        return 0
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
