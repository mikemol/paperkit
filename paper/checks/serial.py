#!/usr/bin/env python3
"""Ν·genre·serial — one unit per SOURCE BIB: the serial / issue-based cut.

An issue of a serial is a bounded, dated, independently-citable batch of work.  In this corpus a
`.bib` file IS that batch — `implications.bib` is one issue's worth of thinking, `resolver.bib`
another — so issue identity is FILE identity, and this objective paginates on it.

⚑ THE FIRST GENRE TO READ THE RECORDS CHANNEL FOR STRUCTURE RATHER THAN TEXT.  Κ (tick 23) opened
`PAPERKIT_GENRE_RECORDS`; `brief` ignores it, and the built-in that most resembles this one
(`_collection`) reads `rests-on`.  This reads `_src`, a field set at parse time (`bib.py:217`:
`f = {"_src": path.name, "_type": e.typ}`) and carried on every record.

⚑ IT EXISTS BECAUSE `PK-BIB-PROVENANCE` TURNED OUT TO BE FALSE (Ξ-F1, 2026-09-10).  That obstacle
held that `observe`'s `F.update(entries(b))` over every bib erases file identity before a genre
runs, making this genre inexpressible.  It does not: the merge combines the DICTIONARIES, while
provenance rides on the DATA.  Measured over paper/: 12 declared warrant files, 12 distinct `_src`
values on the records, none absent, identical after the records channel.

⚑ WHY IT IS NOT A BUILT-IN IN DISGUISE, checked BEFORE this file was written (the Ν-F1 lesson —
`brief` was written and only later measured equal to `_staged`).  No built-in at any of eight γ
values produces the by-source partition, and the reason is structural: **2 of the 12 files span
more than one section**, so the file cut is not a bracketing of the section grouping at all.  A
built-in paginates the grouping it is given; this objective must cut ACROSS it.

MERGING, NOT SPLITTING.  Because a file may span sections, this is an UPWARD objective like
`_collection`: groups are merged when they share a source, never split.  A `_talk`-shaped
split-within-group would drop the totality invariant on exactly the two files that motivate the
genre.

TOTALITY.  Every key lands in exactly one unit: each key has exactly one `_src`, so grouping by it
is a partition by construction.  A key whose record is missing (or carries no `_src`) falls back to
its position in the incoming grouping rather than being dropped — a missing field is a reading
about the instrument, not licence to lose a claim.

ORDER.  Units come out in the order their first claim appears in the incoming grouping, and claims
keep the document order they arrived in — the serial reads forward, like every other cut.
"""
import genrekit


def serial(groups, src_of=None):
    """Merge the incoming grouping by source file.

    `src_of` maps key -> source name; omitted, it is read from Κ's channel.  A key with no entry
    gets a synthetic per-key source, which keeps it in a unit of its own rather than silently
    joining another file's issue.

    ⚑ THE EMPTY CASE DEGENERATES TO `atomic`, NOT TO THE IDENTITY — measured, and the prose here
    said "identity" until the test showed otherwise.  With no records every key gets a synthetic
    per-key source, so every key stands alone.  That is the honest reading: this genre's units ARE
    its provenance, so with no provenance there is no issue structure to assert, and inheriting the
    incoming bracketing would be claiming an issue boundary the data does not support.
    """
    if src_of is None:
        src_of = genrekit.field("_src")
    order, units = [], {}
    for g in groups:
        for k in g:
            s = src_of.get(k) or f"\0unsourced:{k}"
            if s not in units:
                units[s] = []
                order.append(s)
            units[s].append(k)
    return [units[s] for s in order]


if __name__ == "__main__":
    raise SystemExit(genrekit.run(serial))
