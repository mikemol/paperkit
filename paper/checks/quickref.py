#!/usr/bin/env python3
"""Ν·genre·quickref — one unit per LENGTH BAND: the quick-reference cut.

A quick reference is read by someone scanning for an answer, not by someone reading forward.  So
the cut is by how much a claim COSTS to read: terse claims first, discursive ones last, regardless
of which section or file they came from.  A reader who wants the one-liner meets the one-liners.

⚑ THIS IS THE GENRE `PK-GENRE-BLIND` MADE IMPOSSIBLE.  Its objective is a function of CLAIM TEXT —
the exact thing `run_declared` withheld from a declared genre until Κ (tick 23) opened the records
channel.  It was recorded as BLOCKED-ON-`PK-GENRE-BLIND`, re-verdicted UNBLOCKED at tick 25 when
the field census showed `claim` present on all 114 records, and this file is that verdict cashed.

⚑ NOT A BUILT-IN IN DISGUISE (checked BEFORE writing — the Ν-F1 lesson): no built-in at any of
eight γ values produces the length-band partition.  It cannot be one: γ moves the BRACKETING of
the section grouping, while this objective cuts across every group by a property of the text.

THE BANDS ARE A MEASUREMENT, NOT A FEEL.  Over paper/ (114 claims, 4..142 words) the cut at 20 and
45 words gives 31 / 48 / 35 — three usable bands rather than one dominant one.  `_talk`'s own
budget constant is derived the same way (the corpus p75 × 2) and says so; a threshold picked for
feel would be the thing that comment exists to refuse.

TOTALITY.  Every key lands in exactly one band, and a key with no record lands in `full` — the
conservative choice: an unmeasured claim is not advertised as terse.
"""
import genrekit

TERSE, BRIEF = 20, 45
BANDS = ("terse", "brief", "full")


def band(words):
    return "terse" if words <= TERSE else "brief" if words <= BRIEF else "full"


def quickref(groups):
    """One unit per band, terse first.  A pure function of the grouping plus claim text."""
    claim = genrekit.field("claim", "")
    out = {b: [] for b in BANDS}
    for g in groups:
        for k in g:
            text = claim.get(k)
            # ⚑ no record ⇒ `full`, never `terse`: an unmeasured claim must not be advertised as
            # the cheap one to read.  `text is None` is the missing case; "" is a real empty claim.
            out[band(len(text.split())) if text is not None else "full"].append(k)
    return [out[b] for b in BANDS]


if __name__ == "__main__":
    raise SystemExit(genrekit.run(quickref))
