"""Ζ·suite·count — the boundary suites' SHARED RECORDER, and the owner of their summary line.

⚑ THE DEFECT THIS EXISTS FOR IS `guard-must-not-copy`, COMMITTED 45 TIMES.  Every boundary suite
declares its own `check(desc, cond)` closure over its own `fails` list, and then prints a summary
naming how many behaviors it ran.  The recorder and the summary are copy-pasted per file, so the
COUNT has no owner: it is a literal beside the set it describes.  Measured across the suites, 24
of 26 such literals UNDERSTATED — arms were added and the number never moved, so it tracked the
suite's authoring history rather than its content, and would have read a SHRINKING suite as an
unchanged one.

⚑ AND THE PER-FILE REMEDIATION IS WHY THIS MODULE EXISTS RATHER THAN A 46TH FIX.  Two rounds of
"fix all N files" have run (commit 8fe18b8 converted two); four remain — `boundaries_otlp`
("13 behaviors, 1 delta"), `boundaries_surface` ("7 behaviors, 1 delta"), `boundaries_prove`,
`boundaries_prove_envelope` ("6 structural, 1 delta").  They survived both passes for a reason
visible only once you open them: their `check()` appends to `fails` ALONE.  It records what
BROKE, never what RAN — so there is no accumulator a summary could derive from, and a literal is
the only thing left to print.  Fixing the four files does not stop the 46th suite from doing the
same, because nothing owns the shape.

So the recorder is lifted here, and the count is DERIVED from the arms it has seen.  A suite that
adopts `Suite` cannot hardcode its summary: there is no number to type.

Prior art in this package: `_fixture_project.py`, `_fixture_gate.py`, `_fixture_model.py`,
`_fixture_delta.py` — the same lift, for construction rather than recording.

Usage:

    from _boundary import Suite

    def main() -> int:
        s = Suite("DISPATCH", "the verb set's dispatch boundary")
        s.check("a declared verb dispatches", cond)
        s.delta("one token flips the skip-set", p_ok, f_ok,
                p="CROSSING is asked", f="the literal returns", d="one token")
        return s.finish()
"""
from __future__ import annotations

import sys

# ⚑ THE ⟨P, F, δ⟩ PROSE IS ONE RECORD, NOT THREE OPTIONS.  Three separate `p=`/`f=`/`d=`
# parameters put `delta()` at six arguments (PLR0913/PLR0917), and the rule turned out to be
# right about the MODELLING rather than merely about the count: nothing sensibly passes two of
# the three, because they are the pass side, the flag side, and the difference BETWEEN them —
# one description of one pair.  Naming the triple says that; three defaulted strings said the
# opposite.  ⚑ Found only once the hook came back from being inert.
Says = tuple[str, str, str]
_LABELS = ("P (pass side)", "F (flag side)", "δ (min delta)")


class Suite:
    """A boundary suite's arms, and the ONE place its summary is computed.

    ⚑ `ran` and `deltas` are the accumulators the per-file closures lacked.  `failed` is derived
    from them rather than tracked separately: a second list is a second roster, and two rosters
    over one set is the shape this module exists to retire.
    """

    def __init__(self, name: str, subtitle: str = "") -> None:
        self.name = name
        self.ran: list[tuple[str, bool]] = []       # every behavior arm
        self.deltas: list[tuple[str, bool]] = []    # every ⟨P, F, δ⟩ pair
        if subtitle:
            sys.stdout.write(f"{subtitle}\n\n")

    def check(self, desc: str, cond: object) -> bool:
        """Record one behavior arm.  Returns the condition so a caller may branch on it.

        ⚑ `cond` IS `object`, NOT `bool`, AND THAT IS DELIBERATE.  Arms pass whatever their
        predicate yields — a list that must be empty, a dict, a comparison — and coercing at the
        boundary is the honest seam.  Typing it `bool` would push `bool(...)` onto ~45 call sites
        and earn an FBT001 at every one.
        """
        ok = bool(cond)
        self.ran.append((desc, ok))
        sys.stdout.write(f"  {'ok ' if ok else 'XX '}{desc}\n")
        return ok

    def section(self, title: str) -> None:
        """Print a section heading between groups of arms."""
        sys.stdout.write(f"\n⟨{title}⟩\n\n")

    def delta(self, desc: str, p_ok: object, f_ok: object, says: Says = ("", "", ""),
              **prose: str) -> bool:
        """Record a ⟨P, F, δ⟩ pair: BOTH arms must hold, or the pair proves nothing.

        ⚑ A pair whose P passes and whose F also passes is a witness that cannot fail — the
        vacuity the Δ grader reserves its lowest rung for.  Requiring both is what makes the
        minimum-delta claim falsifiable rather than decorative.

        `says` is the (P, F, δ) prose in that order; `p=`/`f=`/`d=` spells the same thing as
        keywords.  An empty element prints nothing.

        ⚑⚑ IT TAKES BOTH SPELLINGS BECAUSE CHANGING IT TO ONE STRANDED FOUR SUITES MID-FLIGHT.
        Three defaulted strings put this at six arguments (PLR0913), and collapsing them to one
        record IS the better model — nothing sensibly passes two of the three.  But it is a
        breaking change to every caller, and four (`boundaries_prove`, `_prove_envelope`,
        `_otlp`, `_surface`) could not be migrated in the same pass: each DECLARES a dependency
        whose own findings block any edit to it.  They ran with a TypeError until a 61,000-action
        sweep reported ELEVEN red boundary suites.

        ⚑ THE RULE THIS COST, WRITTEN DOWN: a shared signature cannot be migrated ahead of the
        callers that are themselves gate-blocked.  Accepting both spellings lets the model
        improve WITHOUT stranding anyone — the keyword form retires per caller as each becomes
        editable, and nothing breaks in between.
        """
        ok = bool(p_ok) and bool(f_ok)
        self.deltas.append((desc, ok))
        sys.stdout.write(f"\n  {'ok ' if ok else 'XX '}{desc}\n")
        parts = (prose.get("p", ""), prose.get("f", ""), prose.get("d", "")) if prose else says
        for label, text in zip(_LABELS, parts, strict=True):
            if text:
                sys.stdout.write(f"      {label}: {text}\n")
        return ok

    def finish(self) -> int:
        """Print the summary and return the process exit code.

        ⚑ THE COUNTS ARE COMPUTED HERE AND NOWHERE ELSE.  A suite has no number to hardcode
        because it never sees one — which is the whole point of the lift.
        """
        bad = [d for d, ok in self.ran + self.deltas if not ok]
        if bad:
            sys.stdout.write(f"\n{self.name}: FAIL ({len(bad)} drifted)\n")
            for d in bad:
                sys.stdout.write(f"  - {d}\n")
            return 1
        n, m = len(self.ran), len(self.deltas)
        sys.stdout.write(f"\n{self.name}: PASS ({n} behavior{'' if n == 1 else 's'}, "
                         f"{m} delta{'' if m == 1 else 's'})\n")
        return 0
