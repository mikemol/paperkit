#!/usr/bin/env python3
"""rhetoric.py — the rhetorical-scheme layer of projection.

Projection separates WHAT a paper says (the claim-DAG: `claim`, `from`) from HOW
its clauses attach (`join`/`glue`).  That attachment layer is not glue — it is
PROSODY: the rhetorical move binding one beat to the next.  This names those moves
as a typed vocabulary and gates each section against a declared SCHEME, so
"intentional use of language" stops being prose you write and becomes structure
you specify and check.  Form is made checkable the way the claim-DAG made content
checkable; the two registries below are the grammar.

Two layers, two scales — both data-driven (a new device is a new row):

MOVES — the inter-clause relation a claim's `move` field names.  Each carries a
`kind` (the abstract category a scheme constrains) and a default `connector` (the
realization project.py uses when a claim supplies no explicit `join`):

    move           kind      connector        gloss
    consequence    entail    "so "            B follows from A
    amplification  extend    "indeed, "       B widens / intensifies A
    scope-shift    extend    ". "             B applies A in a new domain
    concession     turn      "yet "           grant A, then qualify with B
    antithesis     turn      "but "           B opposes A in parallel form
    addition       parallel  "and "           B is a co-member (a tricolon / list beat)
    climax         parallel  ", above all, "  B is the ascending final member
    apposition     restate   " — that is, "   B restates A

SCHEMES — the shape a section's `scheme` (rubric.tsv 3rd column) declares, as a
constraint on its claim count and the KINDS of its non-first claims' moves:

    scheme       claims   non-first move kinds   gloss
    period       1        —                      a single balanced sentence
    distich      2        turn | extend | entail the two-beat: setup, then volta
    tricolon     3        parallel               the RULE OF THREE (asc = climax)
    enumeration  2+       parallel               a list
    ladder       2+       entail                 a chain of consequences

Only sections that DECLARE a scheme are checked (opt-in).  A declared section must
give every non-first claim a typed `move` whose kind the scheme admits.

    rhetoric.py [DIR]            # the rhythm map: each section's scheme + realized moves
    rhetoric.py --check [DIR]    # exit 1 if any section violates its declared scheme
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bib  # noqa: E402  (the parser/data-model leaf — NOT project, so rhetoric no longer closes the project↔rhetoric cycle)

# (kind, default connector).  kind is what SCHEMES constrain; connector is the
# realization project.py falls back to when a claim gives no explicit `join`.
MOVES = {
    "consequence":   ("entail",   "so "),
    "amplification": ("extend",   "indeed, "),
    "scope-shift":   ("extend",   ". "),
    "concession":    ("turn",     "yet "),
    "antithesis":    ("turn",     "but "),
    "addition":      ("parallel", "and "),
    "climax":        ("parallel", ", above all, "),
    "apposition":    ("restate",  " — that is, "),
}

# scheme -> (min_claims, max_claims | None, admissible kinds for non-first claims).
SCHEMES = {
    "period":      (1, 1, set()),
    "distich":     (2, 2, {"turn", "extend", "entail"}),
    "tricolon":    (3, 3, {"parallel"}),
    "enumeration": (2, None, {"parallel"}),
    "ladder":      (2, None, {"entail"}),
}


def kind_of(move: str):
    return MOVES[move][0] if move in MOVES else None


def schemes_from_rubric(path: Path) -> dict:
    """{section_key: scheme} from the optional 3rd tab-column of rubric.tsv."""
    out = {}
    for ln in path.read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "\t" in ln:
            parts = ln.split("\t")
            if len(parts) >= 3 and parts[2].strip():
                out[parts[0].strip()] = parts[2].strip()
    return out


def check_scheme(scheme: str, claims: list, moves: list) -> list:
    """Violations of `scheme` by a section with these claim keys and non-first moves."""
    if scheme not in SCHEMES:
        return [f"unknown scheme '{scheme}' (known: {', '.join(sorted(SCHEMES))})"]
    lo, hi, kinds = SCHEMES[scheme]
    v, n = [], len(claims)
    if n < lo or (hi is not None and n > hi):
        v.append(f"{scheme} wants {lo}–{hi if hi is not None else '∞'} claims, has {n}")
    for i, mv in enumerate(moves, start=2):
        if mv is None:
            v.append(f"claim #{i} has no `move` ({scheme} requires a typed move on each beat)")
        elif mv not in MOVES:
            v.append(f"claim #{i} move '{mv}' is not in the vocabulary")
        elif kinds and kind_of(mv) not in kinds:
            v.append(f"claim #{i} move '{mv}' is a {kind_of(mv)}, but {scheme} admits {sorted(kinds)}")
    return v


def analyze(project_dir: Path) -> list:
    """[(section, scheme, claim_keys, non_first_moves, violations)] for declared sections."""
    cfg = bib.load_config(project_dir)
    F = {}
    for b in cfg["bibs"]:
        F.update(bib.parse(b))
    by_sec = {}
    for k, f in F.items():
        if f.get("section"):
            by_sec.setdefault(f["section"], []).append(k)
    rows = []
    for sk, scheme in schemes_from_rubric(cfg["rubric"]).items():
        keys = bib.dep_order(by_sec.get(sk, []), F)
        claims = [k for k in keys if not bib.is_placed(F[k])]
        moves = [F[k].get("move") for k in claims[1:]]
        rows.append((sk, scheme, claims, moves, check_scheme(scheme, claims, moves)))
    return rows


def main(argv: list) -> int:
    args = [a for a in argv if not a.startswith("-")]
    project_dir = Path(args[0]).resolve() if args else Path.cwd()
    rows = analyze(project_dir)
    if not rows:
        print("rhetoric: no section declares a scheme (rubric.tsv 3rd column) — nothing to check")
        return 0
    rc = 0
    for sk, scheme, claims, moves, viol in rows:
        spectrum = ", ".join(m or "—" for m in moves) or "single beat"
        mark = "✓" if not viol else "✗"
        print(f"rhetoric: {mark} {sk}: {scheme} [{spectrum}]")
        for w in viol:
            print(f"rhetoric:     {w}", file=sys.stderr)
            rc = 1
    if "--check" in argv:
        print("rhetoric: PASS" if rc == 0 else "rhetoric: FAIL", file=sys.stderr)
        return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
