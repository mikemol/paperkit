#!/usr/bin/env python3
r"""Ρ·deck·genre — the pagination-objective REGISTRY: an OPEN set, on the check-verb model.

A GROUPING says what coheres (coherence.grouping_residual: the σ-regularized rests-on partition).
A GENRE says how that grouping PAGINATES — one dense staged slide, a slide per claim, a summary
line, a standalone document.  Two independent axes: the same cluster renders every one of those
ways, and which one is a rhetoric choice, not a structural fact.

    OPEN, not enumerated (the owner's decision, 2026-08-22).

`paragraph = woven|claim` is a CLOSED two-valued knob and was the tempting precedent.  The one this
follows instead is `resolver.VERBS`: a BUILT-IN set declared as data in one owner, plus a seam where
a project registers its OWN in paper.toml, and every consumer DERIVES from the registry rather than
hardcoding a list.  Decks have visibly more genres than prose has paragraph modes, and a genre is a
reusable named cost function — which is the shape of a registry, not an enumeration.

    WHAT A GENRE IS.

A genre NAMES an objective on pagination (slides.bib's genre-names-the-objective: the genre knob and
the "optimal cut" objective are the same choice viewed twice).  So a registry entry carries:

  objective  a callable (groups, records) -> list[list[key]] — the PAGINATION: it takes the
             grouping (a list of clusters, each a list of claim keys) and returns the UNITS, each
             a list of keys.  Pure, deterministic, total.
  gamma      the resolution this genre asks the grouping for — the γ in coherence's
             argmax[Q_E(P) − γ·d(P,σ)].  γ→∞ recovers pure section, γ→0 pure modularity.  A genre
             picks a point on that dial; it does not get its own clustering algorithm.
  what       one phrase, for the report.

    WHAT IS GATED, AND WHY IT IS THE SEAM AND NOT THE SET.

An open set cannot be gated by exhaustive case analysis — the same bind `cmd:` put on the resolver,
where the escape hatch is universal so the gate holds the SEAM.  Three registry invariants:

  RESOLVES     a named genre resolves to an entry (built-in or project-declared).
  TOTAL        an objective is a real function of the grouping: every input key appears in exactly
               one output unit.  A "pagination" that drops or duplicates claims is not one.
  LOUD         a project naming an UNREGISTERED genre is a refusal, never a silent fallback to a
               default — the failure mode an open registry makes possible and must foreclose.

    python3 genre.py            # print the registry
    python3 genre.py --check    # assert the three seam invariants over every registered genre
"""
from __future__ import annotations

import sys
from pathlib import Path

# NO engine imports: this module reads a project's paper.toml directly (tomllib, function-local)
# and is otherwise pure.  A module-level `import bib` here would make the parser a staged input of
# every grid cell that touches a genre — the dead-import trap Μ·kernel·fixture·reads closed.

# Ζ·ladder·sentinel — the same REFUSE rung the rest of the engine types for a caller bug.
_REFUSE = 3


# ── the built-in objectives ───────────────────────────────────────────────────────────────────
# Each is a pure function (groups, records) -> units.  They are DELIBERATELY few: the registry is
# open precisely so the interesting ones can be registered by the consumer that needs them, and
# a built-in that guessed wrong would be a closed set's mistake made slowly.

def _atomic(groups, records):
    """One unit per claim — the teaching cut (slides.bib: cluster → slide-per-claim).  The
    grouping's ORDER is preserved; only its bracketing is discarded.
    """
    return [[k] for g in groups for k in g]


def _staged(groups, records):
    """One unit per cluster — the talk cut: a cohering group stages onto one slide.  This is the
    identity on the grouping, which is the point: the grouping ALREADY is the talk's pagination,
    so `staged` is what makes "the cut is the grouping" a nameable choice rather than an
    unstated default.
    """
    return [list(g) for g in groups]


def _talk(groups, records):
    """One unit per cohering cluster, SPLIT to a load budget — the conference-talk cut.

    Neither built-in above is presentable on its own, and that is measured rather than asserted:
    over paper/, `staged` puts a whole section on one unit (34 to 850 words, median 146) while
    `atomic` gives a 4-word claim its own.  A talk wants the grouping's bracketing KEPT and only
    over-full clusters broken, so the objective is `staged` plus a budget.

    THE BUDGET IS A MEASUREMENT, NOT A THRESHOLD PICKED FOR FEEL.  _LOAD is the corpus's own p75
    claim length (paper/: 42 words) times two — i.e. a unit holds about two typical claims' worth
    of prose.  It is a module constant so it is visible and correctable, not buried in a branch.

    A cluster over budget splits at CLAIM boundaries, in the grouping's order, never mid-claim: a
    claim is the atom the whole engine is built on, so a pagination that broke one would be cutting
    below the unit its own document model defines.  A single claim that alone exceeds the budget
    gets its own unit and is NOT split — the honest outcome, since the alternative is inventing a
    sub-claim boundary the document does not have.
    """
    weight = {r["key"]: len((r.get("claim") or "").split()) for r in (records or ())}
    out = []
    for g in groups:
        unit, load = [], 0
        for k in g:
            w = weight.get(k, 0)
            if unit and load + w > _LOAD:        # over budget: break BEFORE this claim
                out.append(unit)
                unit, load = [], 0
            unit.append(k)
            load += w
        if unit:
            out.append(unit)
    return out


def _collection(groups, records):
    """One unit per SELF-CONTAINED subtree — the document-collection cut.

    The other objectives paginate for a reader's attention (a slide's load).  This one paginates
    for a document's INDEPENDENCE: each unit is meant to stand alone, so its cost is the
    cross-unit grounding edge — a unit that rests on a claim outside itself is not self-contained,
    and slides.bib's genre-names-the-objective named exactly this ("minimise cross-document
    rests-on edges, where the dangling-premise gate becomes the COST function").

    So it MERGES groups that ground into each other, rather than splitting like `talk` does — the
    first objective whose direction is upward, which is the point of registering it: a closed
    enumeration built around splitting would have had no room for it.

    Merging is by connected components over the cross-group grounding edges, which makes the
    result independent of group ORDER (a union-find closure, not a left-to-right sweep) — two
    groups joined by an edge in either direction land in one unit, and the grouping's own order is
    preserved inside each unit.  A group with no outward grounding stays its own unit, so a corpus
    with no rests-on (the degenerate case, measured as 7 of 11 projects) leaves this the identity.
    """
    rests = {r["key"]: [y for y in (r.get("rests-on") or [])] for r in (records or ())}
    owner = {}                                   # key -> index of the group holding it
    for i, g in enumerate(groups):
        for k in g:
            owner[k] = i
    parent = list(range(len(groups)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)    # lower index wins: deterministic

    for i, g in enumerate(groups):
        for k in g:
            for y in rests.get(k, ()):
                j = owner.get(y)
                if j is not None and j != i:
                    union(i, j)
    merged = {}
    for i, g in enumerate(groups):
        merged.setdefault(find(i), []).extend(g)
    return [merged[r] for r in sorted(merged)]


# The talk cut's load budget, in words per unit: paper/'s p75 claim length (42) x 2, so a unit
# carries roughly two typical claims.  Derived from the corpus rather than chosen — see _talk.
_LOAD = 84


BUILTIN = {
    "staged": {"objective": _staged, "gamma": 1.0,
               "what": "one unit per cohering cluster, unbudgeted — the grouping as-is"},
    "atomic": {"objective": _atomic, "gamma": 1.0,
               "what": "one unit per claim — the teaching cut"},
    "collection": {"objective": _collection, "gamma": 0.5,
                   "what": "one unit per self-contained subtree — minimise cross-unit grounding"},
    "talk":   {"objective": _talk, "gamma": 1.0,
               "what": f"clusters split to a {_LOAD}-word load budget — the conference-talk cut"},
}


def partition(records, gamma: float = 1.0) -> dict:
    """The σ-REGULARIZED GROUPING: P* = argmax_P [ Q_E(P) − γ·d(P, σ) ] over the rests-on graph.

    Lives HERE, not in coherence.py, by place-by-ownership (Ρ·deck·residual·wire).  Two consumers
    need this partition and they sit on opposite sides of the component lattice:

      the PROJECTOR (project component) cuts a deck on it — an observation's grouping;
      the ∂² GRADE (delta component) measures how far it sits from the authored σ.

    delta depends on project, never the reverse, so the shared computation has to live at or below
    the projector or the grade could not be reached without an upward edge.  It is pure — records
    in, {key: group} out — so it adds no dependency to either caller.

    σ is the authored `section` partition and doubles as BOTH the fallback where the grounding
    graph is too sparse to say anything (modularity's null term makes a lone edge contribute ≈0,
    so the −γ·d term dominates there) and the tie-break where the argmax is near-degenerate.  The
    greedy sweep is deterministic — keys in record order, candidate groups sorted — so the result
    is a function of the input, with no seed and no ambiguity.

    Returns {"part": {key: group}, "edges": n, "degenerate": bool, "within": n} — the partition
    plus the facts a caller needs to know whether it means anything.
    """
    keys = [r["key"] for r in records]
    idx = {k: i for i, k in enumerate(keys)}
    sec = {r["key"]: r.get("section") for r in records}
    adj = {k: set() for k in keys}
    for r in records:
        for y in r.get("rests-on", []):
            if y in idx and y != r["key"]:
                adj[r["key"]].add(y)
                adj[y].add(r["key"])
    edges = sum(len(v) for v in adj.values()) // 2
    if not edges:
        # Δ·degeneracy·kinds — a document with no grounding graph is degenerate for TWO different
        # reasons, and reporting one verdict for both hides the actionable case.  UNDECLARED: no
        # record carries a `rests-on` field at all — the document may well HAVE an argument and
        # simply has not declared it, which an author can fix.  UNGROUNDED: the field is declared
        # but names nothing reachable in this record set — there is no argument here to ground, so
        # the section cut is the honest answer and nothing is owed.  The bit stays `degenerate`
        # for every existing consumer; `kind` is the second field that tells them apart.
        kind = "undeclared" if not any("rests-on" in r for r in records) else "ungrounded"
        return {"part": dict(sec), "edges": 0, "degenerate": True, "within": 0, "kind": kind}

    within = sum(1 for r in records for y in r.get("rests-on", [])
                 if y in idx and sec.get(y) == r.get("section"))
    deg = {k: len(adj[k]) for k in keys}
    two_m = 2.0 * edges

    def modularity(part):
        q = 0.0
        for k in keys:
            for j in adj[k]:
                if part[k] == part[j]:
                    q += 1.0 - deg[k] * deg[j] / two_m
        return q / two_m

    def dist(part):
        best = {}
        for k in keys:
            best.setdefault(part[k], {}).setdefault(sec[k], 0)
            best[part[k]][sec[k]] += 1
        home = {g: max(c, key=c.get) for g, c in best.items()}
        return sum(1 for k in keys if home[part[k]] != sec[k])

    part = {k: sec[k] for k in keys}
    base = modularity(part) - gamma * (dist(part) / len(keys))
    improved = True
    while improved:
        improved = False
        # MOVE — relabel one claim into a neighbouring group.  Refines WITHIN the current
        # cardinality: it can empty a group (a split's inverse) but never creates one.
        for k in keys:
            cur = part[k]
            for g in sorted({part[j] for j in adj[k]} - {cur}):
                part[k] = g
                score = modularity(part) - gamma * (dist(part) / len(keys))
                if score > base + 1e-12:
                    base, improved = score, True
                    break
                part[k] = cur
        # MERGE — Ρ·deck·partition·merge.  The move step alone cannot change the group COUNT, so
        # the derived partition always carried σ's cardinality and γ moved only WHICH claims
        # grouped together, never HOW MANY groups there were.  A merge of two adjacent groups is
        # the operator that was missing: it is not a bigger move, it is a different one, and
        # modularity is exactly the quantity that says whether two connected groups belong
        # together.  Merges are tried in a deterministic order (sorted group pairs), and only an
        # adjacent pair (joined by a real rests-on edge) is a candidate — merging unconnected
        # groups would fuse a document on no evidence.
        pairs = sorted({tuple(sorted((part[k], part[j]))) for k in keys for j in adj[k]
                        if part[k] != part[j]})
        for a, b in pairs:
            trial = {k: (a if part[k] == b else part[k]) for k in keys}
            score = modularity(trial) - gamma * (dist(trial) / len(keys))
            if score > base + 1e-12:
                part, base, improved = trial, score, True
                break
    return {"part": part, "edges": edges, "degenerate": False, "within": within,
            "groups": len(set(part.values()))}


def run_declared(spec: dict, groups, records, cwd=None) -> list:
    """Ρ·deck·genre·cmd — invoke a PROJECT-DECLARED objective and validate what comes back.

    The open half of the registry was only half-open: a project could REGISTER an objective it
    could not USE, because nothing ran the `cmd`.  This closes it, on the `cmd:` model — the
    consumer's code, in the consumer's language, invoked by the engine.

    The protocol is the smallest thing that can carry a partition: the groups go in on stdin, one
    per line, keys tab-separated; the units come back on stdout in the same shape.  No JSON schema
    to version, and the format is the one the CLI already prints.

    WHAT IT DOES NOT RELAX.  The result is held to the SAME totality invariant a built-in is: every
    key in exactly one unit.  A declared objective that drops or duplicates a claim is refused with
    the same message, because the invariant is a property of what a pagination IS, not of who wrote
    it.  Running arbitrary code here is the same trust posture `cmd:` already establishes — a
    warrant set is trusted code — and it inherits the environment sanitization gating already does.
    """
    import subprocess
    cmd = spec.get("cmd")
    if not cmd:
        raise Unregistered("a declared genre with no `cmd` names no pagination at all")
    payload = "".join("\t".join(g) + "\n" for g in groups)
    r = subprocess.run(cmd, shell=True, cwd=cwd, input=payload,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"genre: declared objective exited {r.returncode} — {r.stderr.strip()[-300:]}")
    units = [ln.split("\t") for ln in r.stdout.splitlines() if ln.strip()]
    ok, why = is_total(lambda g, rec: units, groups, records)
    if not ok:
        raise SystemExit(f"genre: the declared objective's result is {why} — a declared objective "
                         f"is held to the same totality invariant as a built-in")
    return units


class Unregistered(Exception):
    """A project named a genre no registry entry provides (the LOUD invariant)."""


def registry(project_dir: Path | None = None) -> dict:
    """The genres available to a project: the built-ins, plus whatever it declares.

    A project registers its own in paper.toml, mirroring `[checks.<type>]`:

        [genres.brief]
        what  = "one line per cluster — the exec brief"
        cmd   = "python3 checks/brief.py"

    A project-declared genre names a COMMAND rather than a python callable, for the same reason a
    check type does: the engine stays domain-free, and the consumer's objective is its own code in
    its own language.  `run_declared` invokes it (Ρ·deck·genre·cmd) — the registry records that it
    exists and how, and the seam that runs it validates the result exactly as it validates a
    built-in, so a declared objective cannot buy laxity by living outside the engine.
    """
    reg = {k: dict(v) for k, v in BUILTIN.items()}
    if project_dir is None:
        return reg
    cfg_path = Path(project_dir) / "paper.toml"
    if not cfg_path.exists():
        return reg
    import tomllib
    with cfg_path.open("rb") as fh:
        raw = tomllib.load(fh)
    for name, spec in (raw.get("genres") or {}).items():
        reg[name] = {"objective": None,          # a declared genre's objective is its `cmd`
                     "cmd": spec.get("cmd"),
                     "gamma": float(spec.get("gamma", 1.0)),
                     "what": spec.get("what", ""),
                     "declared": True}
    return reg


def resolve(name: str, project_dir: Path | None = None) -> dict:
    """The RESOLVES + LOUD invariants at one seam: a registered genre returns its entry; an
    unregistered one RAISES rather than falling back to a default.  Silent fallback is the failure
    an open registry makes possible — a project would render under a genre it did not ask for and
    nothing would say so.
    """
    reg = registry(project_dir)
    if name not in reg:
        raise Unregistered(
            f"genre {name!r} is not registered — available: {sorted(reg)}.  A project registers "
            f"its own with a [genres.{name}] table in paper.toml (what/cmd/gamma).  Refusing "
            f"rather than falling back to a default: a silent fallback would paginate under a "
            f"genre nobody asked for.")
    return reg[name]


def is_total(objective, groups, records=()) -> tuple[bool, str]:
    """The TOTAL invariant: an objective must be a real FUNCTION of the grouping — every input key
    lands in exactly one output unit.  Returns (ok, why).  A pagination that drops a claim silently
    truncates the document; one that duplicates a claim double-counts it.  Neither is a cut.
    """
    src = [k for g in groups for k in g]
    try:
        units = objective(groups, records)
    except Exception as e:                       # an objective that raises is not total
        return False, f"objective raised {type(e).__name__}: {e}"
    out = [k for u in units for k in u]
    if sorted(out) != sorted(src):
        missing, extra = sorted(set(src) - set(out)), sorted(set(out) - set(src))
        dupes = sorted({k for k in out if out.count(k) > 1})
        return False, (f"not a function of the grouping — "
                       f"dropped {missing}, invented {extra}, duplicated {dupes}")
    return True, "every key lands in exactly one unit"


def main(argv: list) -> int:
    proj = Path([a for a in argv if not a.startswith("-")][0]) if [
        a for a in argv if not a.startswith("-")] else None
    reg = registry(proj)
    if "--check" in argv:
        # A fixture whose shape the invariant is stated over — two clusters, one singleton.
        groups = [["a", "b"], ["c"]]
        bad = 0
        for name, spec in sorted(reg.items()):
            obj = spec.get("objective")
            if obj is None:                      # a project-declared genre: its objective is a cmd
                if not spec.get("cmd"):
                    print(f"genre --check: {name!r} declares neither a built-in objective nor a "
                          f"`cmd` — the registry entry names no pagination at all", file=sys.stderr)
                    bad += 1
                continue
            ok, why = is_total(obj, groups)
            if not ok:
                print(f"genre --check: {name!r} objective is {why}", file=sys.stderr)
                bad += 1
        # LOUD: an unregistered name must RAISE, never resolve to a default.
        try:
            resolve("\0no-such-genre", proj)
            print("genre --check: an unregistered genre RESOLVED — the registry falls back "
                  "silently, so a project would paginate under a genre it did not ask for",
                  file=sys.stderr)
            bad += 1
        except Unregistered:
            pass
        if bad:
            return 1
        print(f"genre --check: {len(reg)} registered ({', '.join(sorted(reg))}) — every objective "
              f"is total over the grouping, and an unregistered name refuses loudly")
        return 0
    print("genre registry — pagination objectives over a grouping:\n")
    for name, spec in sorted(reg.items()):
        kind = "declared" if spec.get("declared") else "built-in"
        print(f"  {name:<10} γ={spec['gamma']:<4} [{kind}] {spec['what']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
