#!/usr/bin/env python3
"""Ι·genre·brief — one line per cohering cluster: the BRIEF cut.

THE FIRST PROJECT-DECLARED GENRE IN THE TREE.  Until this file existed, `run_declared`
(`genre.py:278`) was exercised only by a tempdir fixture that compares `cmd` as a STRING
(`paper/checks/claims.py:894`) and never runs it — so the engine's open registry had a half
nothing had ever executed against a real project.

WHAT A BRIEF IS.  One unit per cluster, whatever the cluster's size: a brief says one thing about
each thing that coheres, and says it once.  Where `talk` KEEPS the grouping's bracketing and
splits over-full clusters to a load budget, and `atomic` gives every claim its own unit, `brief`
does neither — it is the IDENTITY on the grouping.

⚑⚑ AND THAT MAKES IT EQUAL TO THE BUILT-IN `staged` AT EVERY γ (Ν-F1, measured 2026-09-10).
`_staged` IS the identity on the grouping.  A 5-genre × 8-γ sweep over paper/ found
`brief ≡ staged` in all eight cells, and `--observe --genre staged --gamma 4.0 paper` is
BYTE-IDENTICAL to the same command with `--genre brief`.  This file adds no objective the registry
did not already have.

It is kept, deliberately, and the equivalence is DECLARED here rather than left to be
rediscovered:

  · Its purpose was never the brief cut.  It is the first project-declared genre ever EXECUTED —
    before it, `run_declared` ran only against a tempdir fixture that compares `cmd` as a string
    (`paper/checks/claims.py:894`).  Proving the seam is the deliverable.
  · A duplicate objective is the IDEAL pilot for that: the seam is under test while the objective
    is a known-good control whose expected output is independently derivable from a built-in.  A
    genre whose correctness only its own author can judge would test the seam far less.
  · So this is a REGRESSION FIXTURE for the declared seam, and `staged` is its oracle.  If a
    change to `run_declared` ever makes these two diverge, the seam moved.

⚑ The reuse check at tick 21 missed this by searching the wrong population — it looked for a
sibling SCRIPT (`checks/genre_*.py`, none existed) and never compared the OBJECTIVE against the
four built-ins the registry already carries.  Novelty of the FILE is not novelty of the FUNCTION.

⚑ WHY IT CANNOT CONSULT CLAIM TEXT, AND WHY THAT IS THE FINDING, NOT A LIMITATION OF THE BRIEF.
`run_declared` passes `records` to `is_total` and NOT to the subprocess (`genre.py:298`: the
payload is `"\t".join(g)` — keys only).  The built-in `_talk` reads `r["claim"]` for its 84-word
budget; a declared genre cannot.  That asymmetry is the named obstacle `PK-GENRE-BLIND`, and every
length-, term- or difficulty-dependent genre collapses onto it.  A brief is expressible here
BECAUSE it is a pure function of the grouping — so this file is also the demonstration of exactly
where the declared seam's ceiling is.

⚑ THE COLUMN OFFSET (D1).  stdin here is KEYS ONLY, one group per line, tab-separated.  The CLI's
`--observe` prints a LEADING SECTION COLUMN (`project.py:639`), so output from the CLI is NOT
valid input here — feed it back and `is_total` refuses the section labels as INVENTED KEYS, an
error naming totality when the fault is a column offset.  `genre.py`'s own docstring claimed the
two formats matched until Θ corrected it (2026-09-10).

TOTALITY.  Every input key lands in exactly one output unit — here by construction, since the
objective is the identity: each line in becomes one line out, with its keys unchanged and in
order.  Empty lines are skipped rather than emitted as empty units, because a unit with no claims
is not a page of a brief; `is_total` compares multisets of KEYS, so skipping them is invisible to
the invariant and honest about what a unit is.  No key is created, dropped, reordered or split.
"""
import genrekit


def brief(groups):
    """The identity on the grouping: one unit per cluster.

    Kept as a function of one argument rather than inlined so the totality property is testable
    without a subprocess — `sorted(k for u in brief(g) for k in u) == sorted(k for u in g ...)`
    is checkable directly, which is what `paper/checks/claims.py` needs to assert about it.
    """
    return [list(g) for g in groups if g]


if __name__ == "__main__":
    raise SystemExit(genrekit.run(brief))
