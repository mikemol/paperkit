r"""Ζ·bib·nest — the FILE-FIDELITY bib grammar: what the bytes say, including what the engine drops.

⚑ THIS IS THE SECOND GRAMMAR, AND THE SECOND IS NOT A DUPLICATE.  `bibparse` is the engine's
authority: it REFUSES malformed input with a positioned `BibSyntaxError`, because the projector
must never render a half-read record.  This module answers a different question — *what does the
FILE contain, including the parts the engine will not carry* — and to answer it at all it must
survive input `bibparse` correctly rejects.

    bibparse         strict.  A quoted value is a syntax error at line:col.
    bibfidelity      permissive.  A quoted value is a field this reader DROPS, and
                     `unaccounted()` reports the drop by name.

Both are needed and neither subsumes the other.  A tool that reports "the engine ignores your
`enables` field" cannot itself refuse the file, and a projector that silently under-read a claim
would publish a document missing a warrant.  ⚑ The DIVISION is the contract: strictness lives in
`bibparse`, and every consumer wanting file-fidelity comes HERE rather than writing a seventh
regex — which is what six render witnesses and `bibstruct` do today (Ζ·re·structural).

⚑⚑ THE PERMISSIVENESS IS CHARACTERISED, NOT ACCIDENTAL.  Five drops are pinned by
`bibstruct`'s selftest as EXPECTED behaviour, and this module reproduces them exactly:

    an INDENTED closing brace           the entry vanishes (`ENTRY` needs `\n}` at column 0)
    a ONE-LINE entry                    vanishes
    a QUOTED value      from = "B"      the field is absent, the entry survives with a hole
    a BARE value        year = 2026     the field is absent
    a DUPLICATE key                     the last declaration silently wins

A reader that "fixed" these would be a different tool with the same name.  What it drops it
DECLARES: `unaccounted()` is the totality probe, and a caller reporting `n of m` can distinguish
a clean read from one that examined nothing.
"""
from __future__ import annotations

import re

# ⚑ ONE ENTRY GRAMMAR, SPELLED ONCE.  The `(.*?)\n\}` terminator is why an indented closing brace
# makes an entry vanish — pinned above as characterised behaviour, not a defect to fix here.
ENTRY = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)\n\}", re.DOTALL)

# ⚑ THE FIELD *HEAD* ONLY — name, `=`, and the opening `{`.  The VALUE is scanned by `fields()`
# rather than matched, because a regex cannot count braces.  The optional quotes are load-bearing:
# a peer writes `'rests-on' = {…}`, and a `([\w-]+)` name class made five real edges VANISH.
_HEAD = re.compile(r"['\"]?([\w-]+)['\"]?\s*=\s*\{")

# ⚑ DELIBERATELY LOOSER, AND USED ONLY TO COUNT.  Any `<something> =` in the bytes is an
# assignment; if `fields()` yields fewer than this finds, the difference is a field the reader
# cannot see and the caller must be told.  It never produces a value, only a discrepancy — so it
# must NOT require a brace: `from = "quoted"` and `year = 2026` are exactly the assignments
# `fields()` also cannot read, and narrowing this to `= {` would blind the probe to both.
ASSIGN = re.compile(r"(?m)(?:^|,)\s*(\S+?)\s*=")


def strip_comments(text: str) -> str:
    r"""Blank every `%` comment line, PRESERVING length so byte offsets stay true.

    ⚑ BLANKED, NOT DELETED.  A caller reporting `line N` computes it from an offset into this
    text, and a span computed on masked text is applied to RAW text by any writer — so removing
    lines would corrupt every position.  Measured on the live bib as a diff that ERASED 533
    comment lines.

    ⚑⚑ AND OMITTING THIS PASS FABRICATES AN ENTRY, which is the worst failure this grammar has.
    The live bib is 66% comment lines, and a comment MENTIONING an entry shape —
    `% see @misc{GHOST, ...} for the shape` — is read as a real header, after which `.*?\n\}`
    runs forward from inside the comment and swallows the following entry whole.  A missing row
    can be noticed by a denominator; an invented row corroborates itself.

    ⚑ A `%` INSIDE A BRACED VALUE IS NOT A COMMENT in BibTeX, and this is a KNOWN NARROWING:
    values are read AFTER this pass, so a braced `%` would be blanked.  The live corpus has none,
    and `unaccounted()` would report the field if it did.
    """
    return "\n".join(" " * len(ln) if ln.lstrip().startswith("%") else ln
                     for ln in text.split("\n"))


def _value_end(body: str, start: int) -> int:
    r"""Find the index just past the `}` closing the value opened at `start`; -1 if unclosed.

    ⚑ ESCAPED BRACES ARE LITERALS, NOT NESTING LEVELS.  `\{` and `\}` are both live in this
    corpus (`\min\{\, \mathrm{grade}(c)\,\}`), and counting them unbalances every math value.
    An ODD run of preceding backslashes escapes; an even one does not.
    """
    i, depth = start, 1
    while i < len(body) and depth:
        if body[i] in "{}":
            run = len(body[:i]) - len(body[:i].rstrip("\\"))
            if run % 2 == 0:
                depth += 1 if body[i] == "{" else -1
        i += 1
    return -1 if depth else i


def fields(body: str) -> dict[str, str]:
    r"""Read one entry BODY into {name: value}, brace-counted to ARBITRARY depth.

    ⚑⚑⚑ Ζ·bib·nest — THE PATTERN THIS REPLACES COUNTED TO DEPTH ONE AND THE CORPUS GOES DEEPER.
    `bibstruct._FIELD` matched `\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}` — a body, then any number of
    SINGLY-nested groups.  Two levels is unmatchable, and `paper/model.bib:82` has two:

        claim = {... $\mathrm{eff}(c) = \min\{\, \mathrm{grade}(c)\,\} \cup \{…\}$ ...}

    Measured 2026-08-30: `--field claim` reported `14 of 15 entries` on that file, `--roundtrip`
    reported 4 unaccounted-for constructs over the composed corpus, and the value's own tail
    `$\mathrm{eff}(c) = {` was then read as a NEW FIELD NAME.  Proven over 38 bibs: gained 3
    fields, lost 0, changed 0.

    ⚑ AN UNCLOSED BRACE YIELDS NO FIELD, matching the old pattern (which simply failed to match)
    and leaving `unaccounted()` to report the name.  Returning a partial value that ran to
    end-of-entry would be the runaway-swallow class.
    """
    out: dict[str, str] = {}
    pos = 0
    while True:
        m = _HEAD.search(body, pos)
        if m is None:
            return out
        end = _value_end(body, m.end())
        if end < 0:
            return out
        out[str(m.group(1))] = " ".join(body[m.end():end - 1].split())
        pos = end


def mask_values(body: str) -> str:
    r"""Blank every value `fields()` parsed, length-preserving, for the totality probe.

    ⚑ WITHOUT THIS, PROSE READS AS AN ASSIGNMENT.  A claim discussing a Fano line says
    `p+q+r = 0 over F2`, and an unmasked scan reports `p+q+r` as an unparsed field — the
    use-versus-mention defect, committed by the instrument built to catch it.  What remains after
    masking is exactly the text the reader did not account for, which is the question being asked.

    ⚑⚑ AND THE MASK MUST COME FROM THE LIVE READER, WHICH IS WHY IT LIVES BESIDE IT.  Masking with
    the OLD depth-1 pattern while reading with the new scanner leaves the phantom
    `$\mathrm{eff}(c)` reported forever: the value parses, but the mask does not cover it.
    Measured — a one-site fix left the gate red with no visible cause.
    """
    out = body
    pos = 0
    while True:
        m = _HEAD.search(body, pos)
        if m is None:
            return out
        end = _value_end(body, m.end())
        if end < 0:
            return out
        out = out[:m.end()] + (" " * (end - 1 - m.end())) + out[end - 1:]
        pos = end


def unaccounted(body: str, parsed: dict[str, str]) -> list[str]:
    """List names present in the BYTES that `parsed` does not carry — the totality shortfall.

    ⚑ THE DENOMINATOR IS THE PRODUCT.  A bare "no losses" cannot distinguish a total read from a
    probe that examined nothing, which is why every consumer of this reports `n of m`.  An empty
    list means this read was TOTAL over this input — an algebra result about the INPUT, never a
    claim that the grammar's kernel is empty.
    """
    masked = mask_values(body)
    return [str(a.group(1)).strip("'\"") for a in ASSIGN.finditer(masked)
            if str(a.group(1)).strip("'\"") not in parsed]


def entries(text: str) -> dict[str, dict[str, str]]:
    """Read a whole bib into {key: {field: value}}, full-fidelity, comments stripped first.

    ⚑ `_type` CARRIES THE ENTRY TYPE as a field like any other (`@misc` -> `misc`).  It is not a
    separate mode and never was — but nothing SAID so, and two independent agents surveying the
    corpus both reported that the entry type was unavailable, read the ENGINE parser (which does
    discard it), and generalised.  A capability nobody can discover is functionally absent.

    ⚑ A DUPLICATE KEY SILENTLY KEEPS THE LAST — pinned behaviour, and a caller that needs to know
    tracks collisions itself while iterating `ENTRY`.
    """
    out: dict[str, dict[str, str]] = {}
    for m in ENTRY.finditer(strip_comments(text)):
        got = fields(str(m.group(3)))
        got["_type"] = str(m.group(1))
        out[str(m.group(2))] = got
    return out
