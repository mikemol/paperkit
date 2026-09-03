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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

# Ζ·anno·rhetoric — the shapes bib.py's readers actually return, named HERE because the engine's
# flat sibling import (below) is invisible to the type checker: `import bib` behind a sys.path
# insert resolves at runtime and not at analysis time, so every value crossing that edge arrives
# untyped.  MEASURED, because the opposite was claimed: making the import resolve
# (--ignore-missing-imports) takes this file from 65 mypy errors to 64 — it deletes the
# import-not-found line and NOTHING else.  The Any-cascade was never the import's doing; it was
# unannotated defs and bare generics inside this file.  So these aliases are not a workaround for
# the import spelling, and fixing that spelling would not retire them: they are this module's
# statement of what it requires of its dependency, which is a thing worth writing down either way.
#
# ⚑ READ OFF bib.py, NOT GUESSED.  A precise-looking annotation over a genuinely loose structure
# buys a green by telling the checker something false, so each of these traces to a line:
#   Fields  — bib.parse builds `f = {"_src": ..., "_type": ...}` (str), adds _SCALAR fields verbatim
#             (str), and sets every _LIST field to `[a for a in re.split(...)]` (list[str]).  The
#             union is REAL: `f.get("from", [])` is a list where `f.get("move")` is a str, and
#             flattening it to dict[str, str] would be the false claim.
#   Row     — bib.rubric_rows returns `[c.strip() for c in row]` over csv.reader → list[str].
#   Config  — bib.load_config returns a HETEROGENEOUS dict (str, Path, list[Path], bool, tuple),
#             so it is dict[str, object] and each read below narrows at its own use site.
Fields = dict[str, "str | list[str]"]
FieldMap = dict[str, Fields]
Row = list[str]
Config = dict[str, object]

# One analyzed section: (key, declared scheme, claim keys in dep order, the non-first claims'
# moves, the violations).  Named because it is analyze's return element AND main's loop variable,
# and the two were free to drift while it was spelled `list` at both ends.
Section = tuple[str, str, list[str], list[str | None], list[str]]

# Ζ·pkg·shape — the engine's own directory, FIRST on sys.path, and it must stay a per-module
# line rather than moving to paperkit/__init__.py: a package __init__ runs only when the
# package is IMPORTED, and these modules are also loaded as siblings by a caller that has
# already put its own directory ahead of ours.  render/checks/ ships its OWN bib.py, so a
# witness inserting that directory shadows the engine's parser and `from bib import
# dep_order` resolves to the wrong module.  MEASURED: removing these six lines reddened
# seven talk claims with "cannot import name 'dep_order' from bib (render/checks/bib.py)".
# The insert is a PRIORITY CLAIM, not a reachability fix — __init__.py handles reachability.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bib

# ⚑ Ζ·anno·rhetoric — THE UNTYPED EDGE IS DECLARED ONCE, HERE, and this is the placement decision
# in this file.  The import above is unfollowable to mypy (a runtime sys.path insert is not an
# analysis-time fact), so every `bib.foo(...)` is a call on an Any and each such CALL EXPRESSION is
# itself Any — casting the result narrows the value but not the call, which is why a per-call cast
# left five errors standing and this binding leaves none.
#
# Naming the five functions this module uses, with the signatures bib.py actually defines, does
# three things a scattered cast does not: it states this module's REQUIREMENT of its dependency in
# one readable block, it confines the untyped surface to five lines instead of a dozen call sites,
# and it puts the drift in ONE place if bib.py's signatures change.  These are not stubs for bib —
# bib.py owns its own annotations — they are the contract rhetoric.py depends on.
_rubric_rows: Callable[[Path], list[Row]] = bib.rubric_rows
_load_config: Callable[[Path], Config] = bib.load_config
_parse: Callable[[Path, tuple[str, ...]], FieldMap] = bib.parse
_dep_order: Callable[[list[str], FieldMap], list[str]] = bib.dep_order
_is_placed: Callable[[Fields], bool] = bib.is_placed

# (kind, default connector).  kind is what SCHEMES constrain; connector is the
# realization project.py falls back to when a claim gives no explicit `join`.
MOVES: dict[str, tuple[str, str]] = {
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
SCHEMES: dict[str, tuple[int, int | None, set[str]]] = {
    "period":      (1, 1, set()),
    "distich":     (2, 2, {"turn", "extend", "entail"}),
    "tricolon":    (3, 3, {"parallel"}),
    "enumeration": (2, None, {"parallel"}),
    "ladder":      (2, None, {"entail"}),
}


def kind_of(move: str) -> str | None:
    """Return the category a scheme constrains, or None if `move` is outside the vocabulary."""
    return MOVES[move][0] if move in MOVES else None


def schemes_from_rubric(path: Path) -> dict[str, str]:
    """{section_key: scheme} from the optional 3rd tab-column of rubric.tsv."""
    # Ζ·rubric·csv — the ROWS come from bib.rubric_rows (the csv-backed single owner of the .tsv
    # format); this function owns only the MEANING of column 3.  It used to re-implement the
    # strip/comment/tab skip beside bib.rubric's copy, so the two could drift on which lines are
    # data — and they had already drifted on robustness.
    # A row is `key<TAB>title[<TAB>scheme]`; column 3 is this function's, and an absent or empty
    # one means the section declares no scheme (the check is opt-in).
    scheme_column = 3
    return {r[0]: r[2] for r in _rubric_rows(path) if len(r) >= scheme_column and r[2]}


def check_scheme(scheme: str, claims: list[str], moves: list[str | None]) -> list[str]:
    """Violations of `scheme` by a section with these claim keys and non-first moves."""
    if scheme not in SCHEMES:
        return [f"unknown scheme '{scheme}' (known: {', '.join(sorted(SCHEMES))})"]
    lo, hi, kinds = SCHEMES[scheme]
    v: list[str] = []
    n = len(claims)
    if n < lo or (hi is not None and n > hi):
        v.append(f"{scheme} wants {lo}–{hi if hi is not None else '∞'} claims, has {n}")
    for i, mv in enumerate(moves, start=2):
        if mv is None:
            v.append(f"claim #{i} has no `move` ({scheme} requires a typed move on each beat)")
        elif mv not in MOVES:
            v.append(f"claim #{i} move '{mv}' is not in the vocabulary")
        elif kinds and kind_of(mv) not in kinds:
            v.append(f"claim #{i} move '{mv}' is a {kind_of(mv)}, "
                     f"but {scheme} admits {sorted(kinds)}")
    return v


def analyze(project_dir: Path) -> list[Section]:
    """[(section, scheme, claim_keys, non_first_moves, violations)] for declared sections."""
    # Ζ·anno·rhetoric — load_config returns a heterogeneous dict (str, Path, list[Path], bool,
    # tuple), so it is narrowed PER KEY at the point of use rather than once at the top: there is
    # no single element type to give it, and inventing one would be a false claim about a mapping
    # whose whole job is to carry different kinds of thing under different names.
    cfg = _load_config(project_dir)
    bibs = cfg["bibs"]
    consumer_fields = cfg["consumer_fields"]
    if not isinstance(bibs, list) or not isinstance(consumer_fields, tuple):
        msg = f"paperkit-rhetoric: {project_dir}/paper.toml gave a malformed bibs/consumer_fields"
        raise TypeError(msg)
    fields: FieldMap = {}
    for b in bibs:
        fields.update(_parse(b, consumer_fields))

    # `section` is a _SCALAR field, so it is a str where present; the `.get` guard is what makes
    # an unsectioned warrant simply not participate rather than key the map under a falsy value.
    by_sec: dict[str, list[str]] = {}
    for k, f in fields.items():
        sec = f.get("section")
        if sec and isinstance(sec, str):
            by_sec.setdefault(sec, []).append(k)

    rubric = cfg["rubric"]
    if not isinstance(rubric, Path):
        msg = f"paperkit-rhetoric: {project_dir}/paper.toml gave a non-path rubric"
        raise TypeError(msg)
    rows: list[Section] = []
    for sk, scheme in schemes_from_rubric(rubric).items():
        keys = _dep_order(by_sec.get(sk, []), fields)
        claims = [k for k in keys if not _is_placed(fields[k])]
        # `move` is a _SCALAR field: a str when the claim declares one, None when it does not —
        # and the None is MEANINGFUL here, since a declared scheme requires a typed move on every
        # non-first beat and check_scheme reports its absence by name.
        moves = [m if isinstance(m, str) else None
                 for m in (fields[k].get("move") for k in claims[1:])]
        rows.append((sk, scheme, claims, moves, check_scheme(scheme, claims, moves)))
    return rows


def main(argv: list[str]) -> int:
    """Print the rhythm map, or under --check the scheme verdict (exit 1 on any violation)."""
    # Ζ·anno·rhetoric — sys.stdout.write, not print.  This module's stdout IS its protocol (the
    # rhythm map is the output), which is the reason pyproject's per-file T201 list exempts the
    # other entrypoints — gate, project, discriminate, coherence.  rhetoric.py is the same species
    # and is NOT on that list, so rather than reach for a waiver in a file this arc does not own,
    # it takes the conversion linux-sources paid tree-wide for the same rule.  The trailing \n is
    # now explicit: write does not add one, and that is the whole behavioural risk in this change.
    args = [a for a in argv if not a.startswith("-")]
    project_dir = Path(args[0]).resolve() if args else Path.cwd()
    rows = analyze(project_dir)
    if not rows:
        sys.stdout.write(
            "rhetoric: no section declares a scheme (rubric.tsv 3rd column) — nothing to check\n")
        return 0
    rc = 0
    for sk, scheme, _claims, moves, viol in rows:
        spectrum = ", ".join(m or "—" for m in moves) or "single beat"
        mark = "✓" if not viol else "✗"
        sys.stdout.write(f"rhetoric: {mark} {sk}: {scheme} [{spectrum}]\n")
        for w in viol:
            sys.stderr.write(f"rhetoric:     {w}\n")
            rc = 1
    if "--check" in argv:
        sys.stderr.write("rhetoric: PASS\n" if rc == 0 else "rhetoric: FAIL\n")
        return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
