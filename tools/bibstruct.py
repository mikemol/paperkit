#!/usr/bin/env python3
r"""Structural questions about a warrants `.bib` — the claim-DAG, not its text.

⚑ BUILT BECAUSE I KEPT GREPPING IT (user, three times: *"Bibtex? Use our tool
that does structural queries against bibtex."*).  There was no such tool, so the
instruction was to build one — the same way `mdstruct` and `pycodemod` were built
after I kept reaching for `grep` at markdown and Python.  What I actually did in
the meantime:

  * `grep -n -A6 "^@misc{B3"` to read two tied claims before adjudicating them;
  * `_re.finditer(r"@\\w+\\{...")` INSIDE `worklist_gate.order()`, to read the
    `enables` field — because `paperkit.bib.parse` drops unknown fields.

That second one is the sharper miss.  `paperkit/bib.py` opens by recording that
it IS a consolidation of THREE parsers that had "each re-derived the format and
disagreed on which fields survive"; my regex made a FOURTH, in the tool whose job
is to reason about the DAG.

⚑ THE DIVISION OF LABOUR, AND WHY IT IS NOT A FOURTH PARSER.  The engine's
`bib.parse` is the authority for what the ENGINE sees — a whitelist, deliberately,
because the projector must not render fields it does not understand.  This module
asks a different question: what does the FILE say?  It reads both and reports the
DIFFERENCE, which is exactly the class of fact the whitelist hides:

    bibstruct.py --entries [bib]        every key, with the fields it carries
    bibstruct.py --field <name> [bib]   which entries set <name>, and to what
    bibstruct.py --field _type [bib]    the BibTeX ENTRY TYPE (@article/@book/@misc/…).
                                        # ⚑ NOT A SEPARATE MODE, AND THE BANNER'S SILENCE COST
                                        # TWO SURVEYS.  `entries` has always captured it
                                        # (`fields["_type"] = m.group(1)`), because the type is
                                        # a field of the entry like any other — but nothing said
                                        # so here, so two independent agents surveying the corpus
                                        # BOTH reported "bibstruct cannot answer what entry types
                                        # a file uses", read the ENGINE parser's entry regex
                                        # (which genuinely discards it) and generalised to here.
                                        # One of them read files by hand instead and said so.
                                        # A capability nobody can discover is functionally absent
                                        # — the same finding summit exists for, landing on this
                                        # tool's own docstring.
    bibstruct.py --dropped [bib]        fields the FILE sets and the ENGINE drops
    bibstruct.py --edges [bib]          from / rests-on / enables, as a graph
    bibstruct.py --orphans [bib]        keys named by an edge that do not exist
    bibstruct.py --mentions <key> [bib] whose PROSE names <key> — edge evidence

⚑⚑ AND THERE IS A WRITE HALF, WHICH THIS BANNER OMITTED AND THAT OMISSION COST A
PEER REAL WORK.  Summit's floor carries it as `friction-capability-summary-drifts`:
the ecosystem registry calls this tool a "STRUCTURAL bib READER" and lists exactly
the six modes above, and *this docstring agreed with it*, so a delegate concluded no
write mode existed and appended four reports with `cat >>` — bypassing `--add`'s
refusals of duplicate keys, unresolvable witnesses and dangling edges.  Both surfaces
described the tool by the half they kept, and the `cmd:test -f` check passes on a
present file and by construction cannot notice.

    bibstruct.py --add <key> <field>=<value> ... [--bib <path>] --apply
                                        # create a NEW entry.  `claim` and `check`
                                        # are required; every edge target and the
                                        # `item:` witness must ALREADY exist or it
                                        # refuses.  Without --apply: the diff only.
    bibstruct.py --set <key> <field> <value...> [--bib <path>] --apply
                                        # edit ONE field of ONE existing entry.
                                        # Adding an entry or a field is refused.
    bibstruct.py --addfield <key> <field> <value...> [--bib <path>] --apply
                                        # add a field an EXISTING entry does not carry.
                                        # ⚑ THE THIRD VERB, AND ITS ABSENCE LEFT AN ENTRY
                                        # UNREPAIRABLE BY EITHER OTHER ONE.  `--set` refuses
                                        # a missing field ("adding a field is a different
                                        # operation") and `--add` refuses an existing key
                                        # ("this only creates") — both right, and together
                                        # they stranded a report filed without `note`, which
                                        # summit needs because it parses kind/by/of OUT of
                                        # that one field.  Measured on the live floor: the
                                        # entry read back `kind ?  by ?` and the only routes
                                        # left were a hand edit of a peer's file or a
                                        # delete-and-re-add that loses it if the re-add
                                        # refuses.  The verbs now partition by refusal:
                                        # MINT / WIDEN / EDIT.
    bibstruct.py --add ... --corpus <bib> [<bib> …]
                                        # sibling bibs an EDGE may resolve into.  TAKES
                                        # OPERANDS UP TO THE NEXT FLAG — order-independent,
                                        # and it was not: the first cut scanned to the end
                                        # of argv filtering flags out, so `--corpus a.bib
                                        # --bib target.bib` ATE `target.bib` and left the
                                        # write falling through to DEFAULT.  A write aimed
                                        # at a peer's floor then diffs cleanly against THIS
                                        # repo's warrants.bib.  Measured by summit: two
                                        # failed invocations, `--corpus` LAST the only
                                        # working order, nothing saying so.  ⚑ THE
                                        # WRITE VALIDATED EDGES AGAINST THE TARGET FILE
                                        # ALONE, which was right while a floor was one bib
                                        # and became a FALSE REFUSAL the moment summit split
                                        # 242 entries into five per-genre files: a
                                        # corroboration resting on a use-case in a sibling
                                        # refused as dangling WHEN IT IS NOT, and the entry
                                        # shipped with its edge demoted to prose.  The
                                        # refusal's own text named the bug — it protects
                                        # `--orphans`, which reads MANY bibs.  A FLAG and
                                        # not a glob: which files are the corpus is the
                                        # writer's claim, and widening it silently on a tree
                                        # this tool does not own would pass an edge for the
                                        # wrong reason.
    bibstruct.py ... --bib <path>       # the TARGET bib for a write.  A FLAG and not
                                        # a trailing positional, because a positional
                                        # path is indistinguishable from a value word
                                        # — measured: it was appended to the PREVIOUS
                                        # field's value while the write went to the
                                        # DEFAULT bib.  This is what makes filing into
                                        # a PEER repo's floor possible at all.

Every mode reports `n of m`: "there are no sweeps, only censuses" — a bare list
cannot distinguish "no matches" from "no file read".
"""
import os
import re
import sys

# ⚑ ⟡vfs-chokepoints — the ONE read/write seam over the working tree and git history.
# See `_read_bib` for what the three-valued `Presence` buys this parser over the `except OSError`
# it replaced.
#
# ⚑⚑ REACHED BY PACKAGE, NOT BY SCRIPT DIR.  This read `import vfs` on the stated reasoning that
# "a sibling in this package dir, so a plain import resolves" — which is true for `python3
# paperkit/tools/bibstruct.py` (python puts the SCRIPT's directory on sys.path) and false for
# every other route.  `boundaries_config` imports each engine module by name, so as
# `paperkit.tools.bibstruct` the flat spelling raised `ModuleNotFoundError: No module named
# 'vfs'` and reddened bnd-config.  A relative import is correct on BOTH routes and says which
# `vfs` is meant — the repo root has its own `tools/` package, so a bare name here is ambiguous
# as well as unreachable.
try:
    from paperkit.tools import vfs
except ImportError:               # run as a script: no parent package, sibling on sys.path
    import vfs

# Ζ·bibstruct·root — RELOCATED FROM substrate/scratch/ TO paperkit/tools/ (2026-08-28), and BOTH
# anchors needed re-pointing.  In the old home the file sat at `<repo>/scratch/bibstruct.py`, so
# up-TWO was the repo; here it sits one level deeper, at `<repo>/paperkit/tools/bibstruct.py`, so
# up-two lands inside the PACKAGE and up-THREE is the repo.  Measured rather than reasoned: the
# first cut of this edit kept up-two and resolved to `paperkit/paperkit/warrants.bib`, which vfs
# correctly reported ABSENT rather than empty.
#
# `DEFAULT` did not survive the move at all — it named `catalog/worklist/warrants.bib`, a path
# that exists in the OWNER'S tree and nowhere here, so an invocation omitting `--bib` read a file
# that is simply not there.  It is now this repo's ROOT PROJECT bib, the analogue of what it named
# before: the bib of the project the tool ships inside.  A write still REQUIRES `--bib` for any
# other target (that is what makes filing into a peer's floor possible), so this is a read-side
# convenience and never a write-side assumption.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT = os.path.join(ROOT, "warrants.bib")

# ⚑ THE VERBS THAT WRITE, and therefore the only ones for which `--bib` names a TARGET
# rather than a member of the read set. Three, partitioned by what they REFUSE: `--add`
# mints an entry (refuses an existing key), `--addfield` widens one (refuses an existing
# field), `--set` edits a value (refuses a missing field). Kept here because the `--bib`
# guard and its own error message both need it, and an inline pair left the third verb
# rejected by a message that named only the other two.
WRITE_MODES = ("--add", "--addfield", "--set")


def _mutation_contract_error():
    """The exception `edit_snapshot.guard()` raises when mutation intent is unstated.

    ⚑ RESOLVED LAZILY, and that is the point: the READ modes must keep working where
    `edit_snapshot` is not importable at all.  Returning a never-raised private type on
    ImportError makes the `except` clause inert rather than making the import mandatory —
    a read-only consumer of this tool pays nothing for the write half's contract.
    """
    try:
        import edit_snapshot as _es
        return _es.MutationContractError
    except Exception:                       # not importable here — the clause becomes inert
        class _Never(Exception):
            pass
        return _Never


def operands_after(flag, argv):
    """Operands following `flag` UP TO the next `-`-prefixed token — never past it.

    ⚑ A MULTI-OPERAND FLAG NEEDS A BOUNDARY, and filtering flags out while scanning to
    the end of argv is not one. `--corpus a.bib --bib target.bib` consumed `target.bib`
    as a corpus member, leaving `--bib` operandless and the write falling through to
    DEFAULT — so a write aimed at a peer's tree diffs cleanly against this repo's own
    bib. Extracted so the gate tests THIS function rather than a copy of its loop.
    """
    if flag not in argv:
        return []
    out = []
    for a in argv[argv.index(flag) + 1:]:
        if a.startswith("-"):
            break
        out.append(a)
    return out

# ⚑ ONE ENTRY GRAMMAR, SPELLED ONCE.  This is the file-level read the engine's
# whitelist cannot give; it is not a competing parser of the same question.
_ENTRY = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)\n\}", re.DOTALL)
# ⚑ NOT LINE-ANCHORED, AND THE SELFTEST CAUGHT WHY.  My first cut used
# `(?m)^\s*(name) = {...}$`, which reads only fields that OWN their line — but
# the real bib writes `section = {s}, from = {A}, rests-on = {A},` on ONE line,
# so `from` and `rests-on` were invisible and `--edges` reported `enables` only.
# That is the statement-span class this repo has retired in fifteen tools
# (§"drop_dead_renames"), reproduced in a parser written to END hand-parsing.
# A field is `name = {...}` wherever it sits; braces nest one level for LaTeX.
_FIELD = re.compile(r"['\"]?([\w-]+)['\"]?\s*=\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")
# ⚑⚑⚑ THE OPTIONAL QUOTES COST FIVE REAL EDGES OVER THREE DAYS. `([\w-]+)` excluded
# them, so gabion's `'rests-on' = {…}` — written quoted in five placed entries — did not
# match and the field VANISHED: `--entries` listed four fields where the bytes held five,
# `--orphans` could not see the edges, and every surface read green because summit's own
# reader parses the `of=` note tail independently and printed each entry perfectly.
#
# ⚑⚑ AND THE COMMENT DIRECTLY ABOVE RECORDS THE PREVIOUS TIME THIS GRAMMAR SILENTLY
# DROPPED FIELDS (line-anchoring hid `from`/`rests-on` on a shared line). Same lexer,
# same failure mode, same silence — a grammar that does not match simply produces fewer
# fields, and "fewer fields" is indistinguishable from "the entry has fewer fields".
#
# ⚑ WHICH IS WHY THE REAL FIX IS `_ASSIGN` BELOW, NOT THIS CHARACTER CLASS. Widening the
# pattern handles the spelling gabion used; the NEXT unanticipated spelling is silent
# again. `--dropped` answers for the engine's whitelist and nothing answered for the
# LEXER, which is gabion's framing and the gap this closes.
#
# ⚑⚑ A DELIBERATELY LOOSER PATTERN, USED ONLY TO COUNT. Any `<something> = {` at all is
# an assignment in the bytes; if `_FIELD` yields fewer of them than `_ASSIGN` finds, the
# difference is a field the parser cannot see and the reader must be told. It is not a
# second parser — it never produces a value, only a discrepancy.
#
# ⚑⚑ AND IT MUST NOT REQUIRE A BRACE, WHICH MY FIRST CUT DID (`(\S+)\s*=\s*\{`). Two
# EXISTING cases broke immediately: `from = "quoted"` and `year = 2026` are assignments
# with non-brace values that `_FIELD` also cannot read, and the OLD probe caught both.
# Widening the NAME while narrowing the VALUE traded one blind spot for two — a fix that
# regresses the coverage it was extending is worse than the gap.
_ASSIGN = re.compile(r"(?m)(?:^|,)\s*(\S+?)\s*=")
# the fields the engine's parser carries; anything else is DROPPED by it
_ENGINE_LIST = ("from", "rests-on", "reads")
EDGE_FIELDS = ("from", "rests-on", "enables")

# ⚑ [(key, first_bib, later_bib)] from the most recent COMPOSED `entries()` read — a key two
# bibs both declare.  Module-level and not a return value because `entries()` returns a map that
# MANY call sites iterate, and widening that signature to a tuple would touch every one of them
# to report a condition almost none of them can act on.  Read it directly after a composed call;
# it is cleared at the start of each.  A single-bib read cannot collide and leaves it empty.
#
# ⚑⚑ THE CALL-SITE COUNT USED TO BE SPELLED HERE AS A BARE NUMBER, AND IT ROTTED TWICE.
# ⟡bibstruct-prose-28-vs-39: this comment said `28`, two comments in `_read_bib`/`entries` said
# `39`, and the live census said something else again.  ALL OF THEM WERE COUNTING THE SAME
# POPULATION — call sites of `entries()` — read at three different times, so the "28 vs 39"
# discrepancy was never two scopes disagreeing; it was one growing number frozen at two moments.
# ⚑ SCOPE STATED 2026-08-25, AND THE NUMBERS REMOVED RATHER THAN REFRESHED.  A bare count with
# no stated population is the defect; replacing it with a fresher bare count reproduces it.  The
# population that matters to the argument above is *every site that iterates the returned map*,
# which spans this module AND its external readers (`catalog/library/items.py`,
# `scripts/wg_order.py`, `scripts/worklist_gate.py`).  Re-derive it, never quote it:
#     pycodemod.py --calls entries scratch scripts catalog     # tree-wide: def + calls + refs
#     pycodemod.py --calls entries --root scratch/bibstruct.py # this module alone
# The `--calls`/`--root` split IS the two populations, and naming which one you mean is the
# whole repair.  Measured at the time of writing: the in-module reading and the tree-wide
# reading differ by the four external call sites above — which is why an unscoped number could
# be honestly derived twice and disagree with itself.
collisions = []


import difflib


def _strip_comments(text):
    """Blank every `%` comment line, PRESERVING line count and offsets.

    ⚑ BLANKED, NOT DELETED — every caller reports `line %d` from an offset into
    this text, so removing lines would shift every reported position. Same rule
    `agda_lex.mask_comments` follows for the Agda corpus: mask, do not excise.

    ⚑ A `%` INSIDE A BRACED VALUE IS NOT A COMMENT in BibTeX, but this module's
    grammar never sees one -- `_FIELD` reads `{...}` bodies AFTER this pass, so a
    braced `%` would be blanked. Recorded as a KNOWN NARROWING rather than
    silently assumed away: the live bib has none (the probe would report the
    field dropped if it did), and widening this to a brace-aware scan is the
    fifth-parser risk the module docstring forbids.
    """
    # ⚑ SAME LENGTH, NOT JUST SAME LINE COUNT.  My first cut emitted "" for a
    # comment line, which preserves the LINE count but shrinks the file, so every
    # character offset after the first comment shifts.  `entries` only ever reads
    # from the masked text so it never noticed; `set_field` computes a span
    # against masked text and applies it to RAW text, and there the shift is a
    # corrupting write -- measured on the live bib as a diff that ERASED all 533
    # comment lines, i.e. the whole adjudication record.  Replacing each comment
    # with spaces keeps every subsequent offset identical, so a span computed on
    # one text is valid on the other.
    out = []
    for line in text.split("\n"):
        out.append(" " * len(line) if line.lstrip().startswith("%") else line)
    return "\n".join(out)


def _report_collisions(n_distinct):
    """Print the duplicate-key report, if a composed read found any.

    ⚑ THE DENOMINATOR IS THE POINT.  A composed read reports DISTINCT KEYS, which is smaller
    than RECORDS DECLARED whenever two bibs name the same key — so a caller comparing this
    tool's count against a record-counting parser sees a disagreement with no stated cause and
    reasonably suspects the parser.  paperkit hit exactly that (77 here vs 84 there) and had to
    rule out a parse defect by hand.  Naming the gap costs one line and retires that whole class
    of investigation.
    """
    if not collisions:
        return
    # ⚑⚑ GROUPED BY FILE PAIR, BECAUSE THE PER-KEY LIST BURIED ITS OWN FINDING.  First cut
    # printed one line per collision: on substrate's corpus that is 157 near-identical lines
    # saying, in aggregate, the ONE thing that matters — `warrants_sigma.bib` is WHOLLY
    # CONTAINED in `warrants.bib`.  A report whose reader must aggregate it by eye is the
    # judgement-in-the-turn shape; the containment is the fact, so the tool computes it.
    pairs = {}
    for key, first, later in collisions:
        pairs.setdefault((os.path.basename(first), os.path.basename(later)), []).append(key)
    for (first, later), keys in sorted(pairs.items()):
        shown = ", ".join(sorted(keys)[:4])
        more = "" if len(keys) <= 4 else ", … (%d more)" % (len(keys) - 4)
        print("  ⚑ %d key(s) declared in BOTH %s and %s (later wins): %s%s"
              % (len(keys), first, later, shown, more))
    print("  ⚑ %d distinct key(s) over %d declaration(s): %d key(s) declared in more than one "
          "bib.\n     A record-counting parser will report the LARGER number; neither is wrong."
          % (n_distinct, n_distinct + len(collisions), len(collisions)))


def _read_bib(path):
    """UTF-8 text of a bib, or a `SystemExit` that NAMES WHICH ARM FAILED.

    ⚑⚑ ⟡vfs-chokepoints — THE ONE `.bib` READ.  `entries` (many call sites — see the
    ⚑⚑ at `collisions` for why the number is not spelled here, and for the two
    `pycodemod --calls entries` invocations that re-derive it under a STATED scope) and
    `roundtrip` each carried a byte-identical private copy of this reader; the
    duplication was invisible because both copies were CORRECT about the happy path
    and identically wrong about everything else.

    ⚑ THE THREE-VALUED SPLIT IS THE PRODUCT, and collapsing it is the measured bug.
    `except OSError` reported "cannot read <path>" for a bib that does not exist, a
    bib that is a directory, and a bib the process cannot open — one line for three
    facts, of which exactly ONE (absence) is a legitimate answer a caller might act
    on.  `vfs.Presence` keeps them apart at the seam and this function keeps them
    apart in the message.

    ⚑ AND A NON-UTF-8 BIB IS *BROKEN*, NOT EMPTY AND NOT PARTIAL.  `vfs.read` hands
    back RAW BYTES precisely so the codec is a decision made here rather than by the
    environment; `.text()` defaults to `errors="strict"`, so a mangled byte RAISES
    instead of yielding a replacement-char corpus that parses into plausible-but-
    fictional entries.  That fabrication direction is the worst of this parser's
    seven classes — its own `_strip_comments` note records why: "a missing row can be
    noticed by a denominator, an invented row corroborates itself."
    """
    r = vfs.read(path)
    if r.presence is vfs.Presence.ABSENT:
        raise SystemExit(
            f"bibstruct: no such bib {path} — ABSENT.  The file is not there; this is NOT "
            "the same as an empty bib, and not the same as a read that failed.")
    if r.presence is vfs.Presence.BROKEN:
        raise SystemExit(
            f"bibstruct: cannot read {path} — BROKEN, the read did NOT happen ({r.error}).  This "
            "is not an absence: do not read it as 'the bib has no entries'.")
    try:
        return r.text()
    except UnicodeDecodeError as e:
        raise SystemExit(
            f"bibstruct: {path} is not valid UTF-8 ({e}).  A bib that cannot be decoded is "
            "BROKEN, not empty — refusing to parse a mangled corpus into entries that "
            "would look plausible and corroborate themselves.")


def entries(path=None):
    """{key: {field: raw}} — a FULL-FIDELITY read of the file.

    ⚑ Deliberately NOT filtered to the engine's whitelist: the whole point is to
    see what the file says, including what the engine will silently ignore.

    ⚑⚑ `path` MAY BE A LIST, AND THE COMPOSED SET IS THE UNIT. A paperkit document
    projects from SEVERAL bibs (substrate's own cotype corpus has five), so
    `rests-on` closure is a property of the SET, never of one member. Fixing it here
    rather than per-mode is the point: this is the one parser EVERY call site routes
    through, so no two modes can disagree about what the corpus IS. Fixing it only in
    `main` was the first attempt and it was WORSE — the entry map merged while
    `orphans(path)` re-read a single file, reporting 154 edges against 971 entries.

    ⚑ Measured 2026-08-14 (paperkit found the shape first, in its own corpora): the
    CLI collected every positional and parsed `paths[0]`. Substrate re-ran with all
    five bibs, got a BYTE-IDENTICAL count, and read that as the finding surviving
    composition. It was the same single file twice. A verification that cannot fail
    reads exactly like one that passed.
    """
    if isinstance(path, (list, tuple)):
        # ⚑⚑⚑ A KEY DECLARED IN TWO BIBS IS A COLLISION, AND MERGING IT SILENTLY IS THE SAME
        # DEFECT AS THE SILENT DROP THIS FUNCTION WAS JUST FIXED FOR — one level in.  A plain
        # `out.update(entries(one))` keeps the LAST definition and loses the earlier one with no
        # signal, so N files declaring 84 records report as 77 distinct keys and the difference
        # reads as a parse disagreement rather than as duplicate declarations.
        #
        # ⚑⚑ FOUND BY paperkit 2026-08-14, FROM THE OUTSIDE, ON ITS OWN CORPUS: `--orphans`
        # printed "over 77 entries" while paperkit's parser and substrate's own `_ENTRY` regex
        # both counted 84 over the same 12 files.  They flagged it as signature-shaped without
        # chasing it — correctly, since a verdict can be sound while its denominator is not.
        # The orphan verdict WAS sound; the entry count was not, and only the count was wrong.
        #
        # ⚑ WHICH ONE WINS IS NOT DECIDED HERE.  Last-write-wins is kept (a later bib overriding
        # an earlier one is how a composed projection layers), but the collision is REPORTED, so
        # "77 of 84" is a fact the caller can see rather than a silence they must reconstruct.
        # ⚑ THE COLLISION LIST LIVES BESIDE THE MAP, NEVER INSIDE IT.  A first cut stored it as
        # an `out["_collisions"]` key — which would have injected a PHANTOM ENTRY into the map
        # every call site iterates, inflating the very count being corrected.  Fixing a
        # miscount by adding a fake member is the cleaver, not the differential.
        out, seen = {}, {}
        collisions.clear()
        for one in (path or [DEFAULT]):
            for key, fields in entries(one).items():
                if key in seen and seen[key] != one:
                    collisions.append((key, seen[key], one))
                seen[key] = one
                out[key] = fields
        return out
    path = path or DEFAULT
    # ⚑⚑ ⟡vfs-chokepoints: THE ONE READ FOR ALL `.bib` PARSING.  EVERY call site
    # routes through this function, so this single `read` IS the `.bib` surface —
    # which is why it is the chokepoint rather than any per-mode `open()`.
    #
    # ⚑ WHAT THE LIFT BUYS, AND IT IS NOT COSMETIC.  The bare `open(encoding="utf-8")`
    # collapsed THREE distinct facts into one `SystemExit`: the bib is not there, the
    # path is a directory, the read failed.  Only the FIRST is a legitimate answer.
    # The messages below say WHICH, so a caller pointed at a typo'd path no longer
    # reads the same line as one whose bib was deleted.
    #
    # ⚑ THE `SystemExit` CONTRACT IS PRESERVED DELIBERATELY.  Every call site and
    # the `entries(one)` composition loop above expect a raise, not a three-valued
    # branch; converting them is a different edit with a different blast radius.  What
    # changes is that the raise NAMES its arm instead of laundering every failure
    # through one `OSError` message.
    text = _read_bib(path)
    # ⚑ A `%` COMMENT IS NOT INPUT TO THE ENTRY GRAMMAR, AND OMITTING THIS
    # FABRICATED A KEY.  Found by `--roundtrip` on its first run (2026-08-02).
    # The live bib is 66% comment lines, and a comment that MENTIONS an entry
    # shape -- `% see @misc{GHOST, ...} for the shape` -- was read as a real
    # header: `_ENTRY`'s `.*?\n\}` then ran forward from inside the comment and
    # swallowed the following entry whole.  Measured on that two-entry fixture:
    # `--entries` reported `GHOST  claim / entries: 1 of 1 entry` -- the REAL
    # entry `A` absent, a FICTIONAL one in its place, and a clean `n of m`.
    #
    # ⚑ THIS IS THE ONLY ONE OF THE SEVEN CLASSES THAT FABRICATES RATHER THAN
    # OMITS, which makes it the worst: a missing row can be noticed by a
    # denominator, an invented row corroborates itself.  And it is exactly the
    # failure this module exists to expose (`--dropped` reports what the ENGINE
    # silently ignores) reproduced in the module's own reader.
    text = _strip_comments(text)
    out = {}
    for m in _ENTRY.finditer(text):
        body = m.group(3)
        fields = {f.group(1): " ".join(f.group(2).split())
                  for f in _FIELD.finditer(body)}
        fields["_type"] = m.group(1)
        out[m.group(2)] = fields
    return out


def engine_view(path=None):
    """{key: record} as the ENGINE sees it — via `paperkit.bib.parse`, never a copy.

    ⚑ ROUTED THROUGH THE AUTHORITY.  Re-implementing the whitelist here would
    recreate the disagreement `bib.py` exists to have ended.
    """
    for root in (os.environ.get("PAPERKIT"),
                 os.path.expanduser("~/github/paperkit")):
        if root and os.path.isfile(os.path.join(root, "paperkit", "bib.py")):
            if root not in sys.path:
                sys.path.insert(0, root)
            import paperkit.bib as B
            # ⚑⚑⚑ MANY PATHS OR ONE, BECAUSE EVERY READ MODE TAKES THE LIST. `main` hands
            # `path` in as a LIST and `B.parse` wants a single path, so `--dropped`
            # crashed with `not 'list'` on EVERY input — a floor bib, a peer ledger, and
            # no file at all, identically. The engine merges naturally: one parse per
            # file, keys unioned, which is what `entries()` already does on this side.
            #
            # ⚑⚑ SECOND INSTANCE OF ONE DEFECT, IN A SIBLING FUNCTION. `--roundtrip` had
            # exactly this shape and I fixed it hours ago while testing something else,
            # without asking which OTHER single-path helper the list reaches. A fix
            # applied where it was noticed rather than where the class lives.
            #
            # ⚑ AND THE INTERVAL IS UNKNOWN. summit hit this crash this morning, wrote a
            # private census instead, and told nobody; gcalculus found it independently
            # during an adoption test. Nothing in my suite invoked `--dropped` on a real
            # corpus, so the mode could not report its own breakage — a tool nobody runs
            # is a tool whose failure is undetectable, which is the `--roundtrip`
            # circularity one level out.
            # ⚑⚑⚑ `parse_project`, NOT `parse` — THE CONFIG IS HALF THE AUTHORITY AND THIS
            # FUNCTION WAS PASSING ONLY THE OTHER HALF.  `B.parse(path)` applies paperkit's
            # DEFAULT whitelist; a project widens it with `consumer_fields = [...]` in its
            # own `paper.toml`, and `parse_project` is (its docstring) *"the ONE place that
            # binds which extra fields this project tolerates"*.  Calling `parse` meant the
            # "engine view" was the engine's DEFAULTS, so `--dropped` reported every
            # declared consumer field as dropped forever, whatever the project said.
            #
            # ⚑ MEASURED 2026-08-23, and the diagnosis was paperkit's owner running my
            # exact config: declared -> carried (`'A, B'`), zero engine warnings;
            # undeclared -> dropped, one warning.  My tool emitted 14 warnings against a
            # correctly-declared field and I read them as the engine's.
            #
            # ⚑⚑ AND THE DOCSTRING ABOVE MADE IT WORSE BY BEING HALF TRUE.  *"ROUTED
            # THROUGH THE AUTHORITY … re-implementing the whitelist here would recreate the
            # disagreement"* — it routes the PARSER through the authority and then supplies
            # the WRONG CONFIG.  A partial routing that reads as a complete one is harder
            # to catch than no routing at all, because the comment answers the question a
            # reader would have asked.  Same law as the finding gcalculus sent paperkit
            # from the other direction (*"a ledger field that hand-declares something the
            # engine can measure is a bug waiting for the measurement to arrive"*): ONE
            # AUTHORITY, CONSULTED, NEVER COPIED — and config is part of the authority.
            #
            # ⚑⚑ `load_bib(bib, project_dir)` IS THE FUNCTION FOR THIS CALL SHAPE, and my
            # first fix reached for `parse_project` instead — which parses ALL of a
            # project's bibs and so answers a WIDER question than "what does THIS file
            # look like to the engine". Named by paperkit's owner; its docstring is this
            # situation verbatim: *"for a caller that reads a LONE bib by a narrower
            # projection … It still binds the project's DECLARED consumer fields, so such
            # a caller cannot loud-drop a field the project carries."*
            #
            # ⚑ THE DEFAULT IS WHAT MADE THIS SILENT, and the owner calls it their trap
            # rather than my mistake: `parse(path, consumer_fields=())` makes the
            # bare-whitelist call the SHORT one and the correct call the one you must know
            # to write. I am the second consumer to write `parse(path)` and get silently
            # degraded behaviour. Recorded because the shape generalises: A DEFAULT THAT
            # SILENTLY NARROWS AN AUTHORITY IS A TRAP FOR EVERY CALLER THAT DOES NOT KNOW
            # THE PARAMETER EXISTS.
            #
            # ⚑ FALLS BACK to `parse` for a bib with no project dir (a peer's floor, a bare
            # `.bib` on argv). That case has no `paper.toml` to widen anything, so the
            # defaults ARE the right whitelist — and a drop reported there is honest.
            _ps = [path] if isinstance(path, (str, bytes, os.PathLike)) else list(
                path or [DEFAULT])
            merged = {}
            for _p in _ps:
                _dir = os.path.dirname(os.path.abspath(_p))
                _cfg = os.path.join(_dir, "paper.toml")
                if hasattr(B, "load_bib") and os.path.isfile(_cfg):
                    import pathlib as _pl
                    merged.update(B.load_bib(_pl.Path(_p), _pl.Path(_dir)))
                else:
                    merged.update(B.parse(_p))
            return merged
    raise SystemExit(
        "bibstruct: no paperkit engine found (set PAPERKIT=<checkout>); "
        "refusing rather than re-deriving the warrant grammar locally")


def dropped(path=None):
    """[(key, field, value)] the FILE sets and the ENGINE silently discards.

    ⚑ THIS IS THE CLASS THAT BIT.  `enables` is not in the engine's `_LIST`, so
    `rec.get("enables", [])` returns `[]` FOREVER while looking correct — the
    inert-guard shape.  A field the file sets and the engine drops is either a
    consumer's own concern (fine, but it must read the file) or a typo that will
    never be reported.
    """
    have = entries(path)
    try:
        seen = engine_view(path)
    except SystemExit:
        seen = {}
    out = []
    for key, fields in sorted(have.items()):
        rec = seen.get(key, {})
        for name, raw in sorted(fields.items()):
            if name.startswith("_"):
                continue
            if name not in rec and name not in _ENGINE_LIST:
                out.append((key, name, raw))
    return out


def edges(path=None):
    """[(kind, src, dst)] over from / rests-on / enables."""
    out = []
    for key, fields in sorted(entries(path).items()):
        for kind in EDGE_FIELDS:
            for dst in [d for d in re.split(r"[,\s]+", fields.get(kind, "")) if d]:
                out.append((kind, key, dst))
    return out


def orphans(path=None):
    """[(kind, src, dst)] whose target is not an entry — a dangling edge.

    ⚑ The engine FILTERS these silently (`if d in bib`), so a mistyped
    dependency reads as no dependency: the item sorts as if unblocked.
    """
    keys = set(entries(path))
    return [(k, s, d) for k, s, d in edges(path) if d not in keys]


def mentions(key, path=None):
    r"""[(other, field, context)] where another entry's PROSE names `key`.

    ⚑ THIS IS THE EDGE-WARRANT QUESTION, AND IT WAS A JUDGEMENT I KEPT MAKING
    (user: *"don't attack the adjudication as a judgement"*).  When `--order`
    emits a tie, the fix is to declare an edge — but WHICH edge was me reading
    two claims side by side and deciding they were related.  That is exactly
    the reasoning-not-codified shape, one level up from the tie itself.

    An edge is WARRANTED, not chosen, when one entry's prose already names the
    other's subject: the relation is asserted in the document and merely not
    yet declared as a field.  This finds those.  It reports EVIDENCE, never a
    verdict — naming which direction the edge runs is a separate act, and one
    the prose usually settles ("re-emitted against THAT current census" names
    its premise by position).

    ⚑ SUBSTRING, NOT WORD-BOUNDARY: warrant keys carry `-` and digits (`R14-v2`,
    `T12-rederive`, `R2-SWEEP`), and `\\b` is a `\\w` transition — the same
    boundary defect `agda_lex.word` exists to fix, where 1269 of 10831 names
    were invisible to `\\b`.  Longest-first so `R14-v2` is not reported as a
    mention of `R14-v1`'s prefix.
    """
    have = entries(path)
    if key not in have:
        raise SystemExit("bibstruct: no entry %r (have %d)" % (key, len(have)))
    out = []
    for other, fields in sorted(have.items()):
        if other == key:
            continue
        for name, raw in sorted(fields.items()):
            if name.startswith("_") or name in EDGE_FIELDS:
                continue          # a declared edge is not a MENTION
            i = raw.find(key)
            if i < 0:
                continue
            # ⚑ a longer key that CONTAINS this one is a different subject
            if any(k != key and key in k and k in raw for k in have):
                continue
            lo, hi = max(0, i - 40), min(len(raw), i + len(key) + 40)
            out.append((other, name, ("…" if lo else "") + raw[lo:hi] +
                        ("…" if hi < len(raw) else "")))
    return out


def _n_of_m(label, rows, total):
    print("%s: %d of %d entr%s" % (label, len(rows), total,
                                   "y" if total == 1 else "ies"))


def main(argv, intent=None):
    # ⚑⚑ `intent` IS `edit_snapshot.guard`'s FIXTURE ESCAPE, THREADED — NOT A NEW CONTRACT.
    # ⟡bibstruct-selftest-swallowed: `guard` checks the explicit-mutation contract against
    # the PROCESS argv, and a `_selftest` driving a write against a temp bib legitimately
    # carries `--selftest` there and neither mutation flag. `guard`'s own docstring names
    # exactly this case and provides `intent="apply"` for it; this parameter is how a
    # caller that reaches `guard` THROUGH `main` can state it. It is None for every CLI
    # invocation, so the command line keeps answering for itself.
    #
    # ⚑ IT IS A STATEMENT, NOT A BYPASS. `require_explicit_mutation` validates the value
    # ('apply' or 'dry-run', anything else refused), so a fixture that writes still has to
    # SAY it writes — one level in, the same contract. Routing around the guard to make a
    # case pass would be the false-green this whole repair exists to remove.
    if intent is not None:
        # ⚑ THERE IS NO `--dry-run` FLAG ON THIS TOOL; the preview is the ABSENCE of
        # `--apply`, so a stated `dry-run` intent never reaches `guard` anyway. Refusing an
        # unknown value HERE rather than letting it ride to the write means a typo cannot
        # look like a preview.
        if intent not in ("apply", "dry-run"):
            print(f"bibstruct: intent={intent!r} is not 'apply' or 'dry-run'.",
                  file=sys.stderr)
            return 2
    # ⚑ THERE IS NO `--entry <key>` HERE, AND ITS ABSENCE IS THE FINDING.  I
    # built one (hunting G1's fields had taken five reads) and was asked *"isn't
    # that just --items <key>?"*  It is: `worklist_gate --items <key>` already
    # takes a key, and the declaration is that question's LOWER GRADE, not a
    # second question.  Two key-taking commands with nothing saying which
    # answers what is the `leverage`-defined-twice shape (T23) at the CLI.
    # `--items` now prints DECLARED + the verdict, delegating here for the read
    # so there is still ONE bib parser.  Do not re-add this as a convenience.
    # ⚑ THE WRITE VERBS COME FROM `WRITE_MODES`, not a second spelling of them. This set
    # and the `--bib` guard listed the same verbs independently, so `--addfield` reached
    # the guard and never the recogniser: `mode` stayed None and the refusal printed
    # "None reads every bib positionally" — a message about a mode that does not exist,
    # for a mode that does. Two rosters of one fact, disagreeing, exactly as this file's
    # banner records for the tool's own documented-vs-dispatched modes.
    known = {"--entries", "--dropped", "--edges", "--orphans", "--field",
             "--mentions", "--roundtrip", "--selftest"} | set(WRITE_MODES)
    if "--selftest" in argv:
        return _selftest()
    mode = next((a for a in argv if a in known), None)
    paths = [a for a in argv if not a.startswith("-")]
    # ⚑⚑ `--bib <path>` — THE FLAG `--set`'s OWN COMMENT ALREADY CLAIMED EXISTED.  It said
    # *"The bib path is a FLAG here rather than a trailing positional, because a positional
    # path is indistinguishable from a value word"* — correct reasoning for a flag that was
    # never implemented, so both write modes were hardwired to DEFAULT.  Prose forging a
    # structural fact, in the justification for the very design it describes.
    #
    # ⚑⚑ AND THE ABSENCE WAS NOT INERT, IT CORRUPTED SILENTLY.  `--add` takes its key as the
    # first `=`-free token and CONTINUES the previous value on any later one, so a trailing
    # `path/to/other.bib` was appended to whichever field came last — measured: a `check`
    # field silently grew a filesystem path.  That is the operand-ownership class this
    # function's own comments record twice (`--key --archive f.py`; `claim={the}`),
    # reproduced a third time by the code written to avoid it.  A write mode that cannot
    # name its target and mangles the attempt is why cross-repo filing was done by hand.
    write_bib = None
    target = DEFAULT
    if "--bib" in argv:
        _i = argv.index("--bib")
        if _i + 1 >= len(argv) or argv[_i + 1].startswith("-"):
            print("bibstruct.py --bib needs a path", file=sys.stderr)
            return 2
        write_bib = argv[_i + 1]
        # ⚑⚑⚑ `--bib` IS THE WRITE TARGET, AND A READ MODE ACCEPTING IT SILENTLY MISREAD THE
        # CORPUS.  It takes exactly ONE path and is REMOVED from `paths` below — so
        # `--orphans --bib a.bib b.bib … l.bib` read ELEVEN of twelve files and dropped the
        # named one, producing an unstable entry count and FALSE DANGLING EDGES for every
        # premise that lived in the dropped file.
        #
        # ⚑⚑ Measured 2026-08-14: paperkit ran exactly that against its own 12-bib corpus, got
        # 77 then 70 entries and 18 "no such entry" reports on premises its own parser resolves,
        # and reasonably read it as a merge defect still live in substrate's fix.  It was not —
        # the same 12 files passed POSITIONALLY give `0 dangling of 144 over 84 entries`, exact
        # agreement with paperkit's parser.  The tool was right and the INVOCATION was wrong,
        # which is the worst combination: a flag that means something else in this mode, accepted
        # in silence, reporting a peer's clean corpus as broken.
        #
        # ⚑ FALSE DANGLING IS THE DANGEROUS DIRECTION — it tells an author a resolved premise is
        # broken.  Every other defect in this file this week under-reported; this one over-reports,
        # and a silent flag mismatch is not a user error when the tool could refuse.
        # ⚑⚑ THE ROSTER IS A CONSTANT AT MODULE SCOPE, NOT A LITERAL HERE. It was the pair
        # `("--add", "--set")` inline, and adding a third write verb left `--addfield`
        # rejected by its own tool with a message naming only the other two — the
        # frozen-roster shape this module's own banner records (a mode shipped without
        # reaching the dispatch). One list, read by the guard and named in the message.
        if mode not in WRITE_MODES:
            print("bibstruct.py: --bib is the WRITE target ({}) and takes ONE path;\n"
                  "  {} reads every bib given POSITIONALLY. Passing --bib to a read mode would\n"
                  "  DROP {} from the read set and report false dangling edges for anything it\n"
                  "  defines. Re-run without --bib:\n"
                  "    bibstruct.py {} <bib> [<bib> …]".format("/".join(WRITE_MODES), mode, os.path.basename(write_bib), mode),
                  file=sys.stderr)
            return 2
        paths = [a for a in paths if a != write_bib]
        target = write_bib
    # ⚑⚑⚑ `--corpus` NAMES THE SIBLINGS AN EDGE MAY RESOLVE INTO. `--add` validated every
    # edge target against the WRITE FILE alone, which was correct while a floor was one
    # bib and became a FALSE REFUSAL the moment summit split 242 entries into five: a
    # corroboration resting on a use-case in a sibling file read as dangling when it is
    # not, and the entry had to be placed with its edge demoted to prose.
    #
    # ⚑⚑ A FLAG AND NOT A GLOB, because "which files count as the corpus" is the writer's
    # claim to make and not mine to infer. Globbing `<dir>/*.bib` would silently widen the
    # validation set on a tree I do not own, and a target that resolves only because an
    # unrelated file happened to sit beside it is a pass for the wrong reason.
    #
    # ⚑ AND IT IS REFUSED ON A READ MODE for the same reason `--bib` is: a read takes its
    # corpus POSITIONALLY, so accepting `--corpus` there would create a second spelling of
    # one thing — the two-rosters shape this file has already paid for twice.
    corpus = []
    if "--corpus" in argv:
        if mode not in WRITE_MODES:
            print("bibstruct.py: --corpus names sibling bibs for a WRITE's edge check "
                  "({});\n  {} reads its corpus POSITIONALLY — pass the bibs directly:\n"
                  "    bibstruct.py {} <bib> [<bib> …]".format("/".join(WRITE_MODES), mode, mode), file=sys.stderr)
            return 2
        # ⚑⚑⚑ IT STOPS AT THE NEXT FLAG, AND GREEDY CONSUMPTION MADE IT ORDER-DEPENDENT.
        # `[a for a in argv[i+1:] if not a.startswith("-")]` filtered flags out but kept
        # scanning PAST them, so `--corpus a.bib --bib target.bib` swallowed
        # `target.bib` as a corpus member and left `--bib` with nothing — summit measured
        # two failed invocations and found that putting `--corpus` LAST was the only
        # working order, with the usage text saying nothing about it.
        #
        # ⚑⚑ AND THE SILENT HALF IS WORSE THAN THE ERROR. With `--bib`'s operand eaten,
        # the write falls through to DEFAULT — this repo's own warrants.bib — so an `--add`
        # aimed at a peer's floor can report a clean diff against a file the author never
        # named. A flag that changes the TARGET by being ordered differently is the
        # operand-ownership class this file already records twice (`--key --archive f.py`;
        # a trailing path appended to the previous field's VALUE), arriving a third time
        # in the code written to fix the second.
        #
        # ⚑ SO THE BOUNDARY IS THE NEXT `-`-PREFIXED TOKEN, which is what a `nargs="+"`
        # would give and what every other multi-operand flag here already assumes.
        corpus = operands_after("--corpus", argv)
        if not corpus:
            print(f"usage: bibstruct.py {mode} … --corpus <bib> [<bib> …]",
                  file=sys.stderr)
            return 2
        paths = [a for a in paths if a not in corpus]
    # ⚑ AND A STRAY POSITIONAL IS NOW A REFUSAL, NOT A SILENT SUFFIX.  Without this the
    # pair-loop below appends any extra `=`-free token to the PREVIOUS field's value, so
    # the natural `--add <key> f=v … other.bib` (every read mode takes a trailing bib)
    # wrote the path INTO the entry.  Refusing names the operand instead of eating it.
    if mode in ("--add", "--set") and write_bib is None:
        _stray = [a for a in paths if a.endswith(".bib")]
        if _stray:
            print(f"bibstruct.py {mode}: {_stray[0]!r} looks like a target bib, but {mode} takes it as "
                  "`--bib <path>` — a trailing positional here would be swallowed into "
                  "the preceding field's VALUE.", file=sys.stderr)
            return 2
    # `--field <name>` consumes the next positional as its argument
    fname = None
    if mode == "--add":
        # ⚑ `name=value` PAIRS, NOT POSITIONALS.  An entry has 5-7 fields and a
        # positional order would be a roster nobody can read at the call site --
        # and `--set`'s own operand handling is already the cautionary case
        # (three positionals, value joined, path forced to a flag).
        # ⚑ A VALUE CONTAINS SPACES, SO A PAIR IS NOT ONE ARGV WORD.  My first cut
        # took every `x=y` token independently: `claim=the bib reader has...`
        # became `claim={the}` and the trailing `[tag=0]` was parsed as a FIELD
        # NAMED `[bib-kernel-unwitnessed`.  That is the operand-ownership class
        # measured in `pycodemod` today (`--key --archive f.py`), reproduced in
        # code written to avoid it -- and `--set` already had the fix (it joins
        # its trailing words).  A new pair STARTS at a token whose `=` is
        # preceded by a bare field name; everything else continues the value.
        akey = next((a for a in paths if "=" not in a), None)
        pairs, cur = [], None
        for a in paths:
            if a == akey and cur is None:
                continue
            if re.match(r"^[\w-]+=", a):
                if cur is not None:
                    pairs.append(cur)
                cur = a
            elif cur is not None:
                cur += " " + a
        if cur is not None:
            pairs.append(cur)
        if not akey or not pairs:
            print("usage: bibstruct.py --add <key> <field>=<value> ... --apply\n"
                  "  creates a NEW entry. Editing an existing field is --set.\n"
                  "  `claim` and `check` are required; every edge target and the\n"
                  "  item: witness must already exist, or this refuses.",
                  file=sys.stderr)
            return 2
        newfields = {}
        for p in pairs:
            n, _s, v = p.partition("=")
            newfields[n.strip()] = v.strip()
        new = add_entry(akey, newfields, target, corpus)
        old = open(target, encoding="utf-8").read()
        for line in difflib.unified_diff(old.split("\n"), new.split("\n"),
                                         "before", "after", lineterm="", n=1):
            print("  " + line)
        if "--apply" not in argv:
            print("--add: DRY RUN — pass --apply to write.")
            return 0
        import edit_snapshot as _es
        _es.guard(f"bibstruct --add {akey}", [target], intent=intent)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(new)
        bad = roundtrip(target)
        if bad:
            for kind, what, detail in bad:
                print("  ⚠ %-16s %-24s %s" % (kind, what, detail))
            print("--add: WROTE, but the result does NOT round-trip. Recover with "
                  "edit_snapshot --from-snapshot.")
            return 1
        # ⚑ AND THE ENTRY MUST READ BACK.  Writing text that round-trips is not
        # the same as writing the entry asked for -- the mis-sliced `--set`
        # produced a file that parsed fine and had the wrong content.
        back = entries(target)
        if akey not in back:
            print(f"--add: WROTE, but {akey!r} does not read back. Recover with "
                  "edit_snapshot --from-snapshot.")
            return 1
        print("--add: ✓ wrote %s; the file round-trips (%d entries, was %d)."
              % (akey, len(back), len(back) - 1))
        return 0
    if mode == "--addfield":
        # ⚑⚑ SAME OPERAND SHAPE AS `--set`, DELIBERATELY — three positionals with a
        # space-bearing value and the bib as a FLAG. A third verb with a fourth calling
        # convention is how a toolkit becomes unlearnable; the difference between the
        # verbs is what they REFUSE, not how they are typed.
        if len(paths) < 3:
            print("usage: bibstruct.py --addfield <key> <field> <value...> --apply\n"
                  "  adds a field an EXISTING entry does not carry. Creating an entry\n"
                  "  is `--add`; editing an existing value is `--set`; both are refused\n"
                  "  here. Without --apply this prints the diff and writes nothing.",
                  file=sys.stderr)
            return 2
        akey2, afield, avalue = paths[0], paths[1], " ".join(paths[2:])
        new = add_field(akey2, afield, avalue, target)
        old = open(target, encoding="utf-8").read()
        for line in difflib.unified_diff(old.split("\n"), new.split("\n"),
                                         "before", "after", lineterm="", n=1):
            print("  " + line)
        if "--apply" not in argv:
            print("--addfield: DRY RUN — pass --apply to write.")
            return 0
        import edit_snapshot as _es
        _es.guard(f"bibstruct --addfield {akey2}.{afield}", [target], intent=intent)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(new)
        bad = roundtrip(target)
        if bad:
            for kind, what, detail in bad:
                print("  ⚠ %-16s %s %s" % (kind, what, detail))
            print("--addfield: WROTE, but the result does NOT round-trip. Recover with "
                  "edit_snapshot --from-snapshot.")
            return 1
        back = entries(target)
        print("--addfield: ✓ wrote %s.%s; the file still round-trips (%d entries)."
              % (akey2, afield, len(back)))
        return 0
    if mode == "--set":
        # ⚑ THREE OPERANDS, AND THE VALUE MAY CONTAIN SPACES.  Taking only the
        # first positional would silently truncate `enables = {A, B}` to `{A,`,
        # which is the operand-ownership class measured in `pycodemod` today
        # (`--key --archive f.py` bound another mode's operand).  The bib path is
        # a FLAG here rather than a trailing positional, because a positional
        # path is indistinguishable from a value word.
        if len(paths) < 3:
            print("usage: bibstruct.py --set <key> <field> <value...> --apply\n"
                  "  edits ONE field of ONE existing entry. Adding an entry or a\n"
                  "  field is a different operation and is refused.\n"
                  "  without --apply this prints the diff and writes nothing.",
                  file=sys.stderr)
            return 2
        skey, sfield, svalue = paths[0], paths[1], " ".join(paths[2:])
        new = set_field(skey, sfield, svalue, target)
        old = open(target, encoding="utf-8").read()
        if new == old:
            print(f"  {skey}.{sfield} is already {svalue!r} — nothing to write.")
            return 0
        for line in difflib.unified_diff(old.split("\n"), new.split("\n"),
                                         "before", "after", lineterm="", n=1):
            print("  " + line)
        if "--apply" not in argv:
            print("--set: DRY RUN — pass --apply to write.")
            return 0
        import edit_snapshot as _es
        _es.guard(f"bibstruct --set {skey}.{sfield}", [target], intent=intent)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(new)
        # ⚑ THE POST-CONDITION IS THE TOTALITY PROBE, RE-RUN ON WHAT WE WROTE.
        # A write that makes the file unreadable to its own parser is the
        # fabrication class arriving through the write path; `--roundtrip` is the
        # only check that can see it, and a diff cannot.
        bad = roundtrip(target)
        if bad:
            for kind, what, detail in bad:
                print("  ⚠ %-16s %-24s %s" % (kind, what, detail))
            print("--set: WROTE, but the result does NOT round-trip. Recover with "
                  "edit_snapshot --from-snapshot.")
            return 1
        print("--set: ✓ wrote %s.%s; the file still round-trips (%d entries)."
              % (skey, sfield, len(entries(target))))
        return 0
    if mode in ("--field", "--mentions"):
        if not paths:
            print(f"usage: bibstruct.py {mode} <name> [bib]", file=sys.stderr)
            return 2
        fname, paths = paths[0], paths[1:]
    if mode is None:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    # ⚑ EVERY BIB GIVEN IS READ. `path` is the composed LIST (see `entries`), not `paths[0]` —
    # so `--orphans a.bib b.bib` resolves a premise living in the other file, and every mode
    # below inherits it because they all route through the one parser.
    path = paths or [DEFAULT]
    have = entries(path)
    if mode == "--entries":
        for key, f in sorted(have.items()):
            names = ", ".join(sorted(n for n in f if not n.startswith("_")))
            print("  %-16s %s" % (key, names))
        _n_of_m("entries", have, len(have))
    elif mode == "--field":
        rows = [(k, f[fname]) for k, f in sorted(have.items()) if fname in f]
        for k, v in rows:
            print("  %-16s %s" % (k, v[:110] + ("…" if len(v) > 110 else "")))
        _n_of_m(f"{fname}", rows, len(have))
    elif mode == "--mentions":
        rows = mentions(fname, path)
        for other, field, ctx in rows:
            print("  %-16s %-8s %s" % (other, field, ctx))
        # ⚑ EVIDENCE, NOT A VERDICT.  An edge is warranted when the prose
        # already asserts the relation; which DIRECTION it runs is read from
        # that prose, not chosen here.
        print("%s: named by %d of %d other entr%s (prose only; declared edges "
              "excluded)"
              % (fname, len(rows), len(have) - 1,
                 "y" if len(have) == 2 else "ies"))
    elif mode == "--dropped":
        rows = dropped(path)
        for k, n, v in rows:
            print("  %-16s %-12s %s" % (k, n, v[:80]))
        print("dropped: %d field(s) the engine ignores, across %d entr%s"
              % (len(rows), len(have), "y" if len(have) == 1 else "ies"))
    elif mode == "--edges":
        rows = edges(path)
        for kind, s, d in rows:
            print("  %-9s %-16s -> %s" % (kind, s, d))
        print("edges: %d over %d entr%s" % (len(rows), len(have),
                                            "y" if len(have) == 1 else "ies"))
    elif mode == "--roundtrip":
        # ⚑ ONE PATH OR MANY. `roundtrip()` takes a single path while every other read
        # mode takes the list, so `--roundtrip a.bib` crashed with `expected str, bytes
        # or os.PathLike object, not list` — a totality probe that could not be pointed at
        # the corpus it exists to check. Found while testing the quoted-field defect,
        # which is exactly what it should have caught.
        rows = [r for p in path for r in roundtrip(p)]
        for kind, what, detail in rows:
            print("  %-16s %-24s %s" % (kind, what, detail))
        # ⚑ REPORT THE DENOMINATOR THE PROBE COVERED, NOT JUST THE FAILURES.  A
        # bare "0 losses" cannot distinguish a total read from a probe that
        # examined nothing — the same reason every other mode prints `n of m`.
        print("roundtrip: %d unaccounted-for construct(s) over %d parsed entr%s"
              % (len(rows), len(have), "y" if len(have) == 1 else "ies"))
        if not rows:
            print("   this read is TOTAL over this input — an ALGEBRA result. It "
                  "does NOT say the\n   parser's kernel is empty; it says nothing "
                  "in THIS file fell into it.")
        return 1 if rows else 0
    elif mode == "--orphans":
        rows = orphans(path)
        for kind, s, d in rows:
            print("  ⚠ %-9s %-16s -> %s   (no such entry)" % (kind, s, d))
        print("orphans: %d dangling edge(s) of %d over %d entr%s"
              % (len(rows), len(edges(path)), len(have),
                 "y" if len(have) == 1 else "ies"))
        _report_collisions(len(have))
    return 0


def roundtrip(path=None):
    r"""[(kind, key_or_line, detail)] — every place the PARSE fails to ACCOUNT for
    the file. Empty list = this read is TOTAL over this input.

    ⚑ THE ALGEBRA / COALGEBRA DISTINCTION, AND IT IS WHY A CENSUS CANNOT STAND IN
    FOR THIS (user, 2026-08-02: *"That's assuming the data is never corrupted.
    There's a difference between the homology and the cohomology, the algebra and
    the coalgebra."*).

    `--entries` reporting `42 of 42` is an ALGEBRA statement: at THIS input, the
    parser agrees with a second reading of the same bytes.  The hazard the external
    review named is a COALGEBRA one — what the map DOES TO inputs it has not seen.
    Measured on the live bib: 0 quoted fields, 0 bare-integer fields, 42 raw headers
    = 42 parsed.  **That says the kernel is UNWITNESSED, not empty** — and an
    unwitnessed kernel is the dangerous case, because nothing exercises it and its
    first firing is invisible.  Six classes, each returning SUCCESS with data gone:

      * `_ENTRY`'s `\\n\\}` requires the closing brace at column 0 on its own line,
        so an INDENTED `  }` or a ONE-LINE entry makes the WHOLE ENTRY vanish;
      * `_FIELD` matches only `= {...}`, so `= "quoted"` and `= 2026` vanish, and
        the entry is present WITH A HOLE — worse, because a partial answer reads
        as a complete one;
      * `_FIELD`'s brace nesting is ONE level, so `{x {y {z}} w}` truncates;
      * a duplicate `@misc{K,` silently keeps the LAST, so a key can be lost.

    ⚑ AND THE TOOL'S OWN THESIS IS WHAT MAKES THIS LOAD-BEARING.  `--dropped`
    exists to report what the ENGINE'S whitelist silently ignores.  A silent-drop
    parser inside THAT tool reports a clean bill of health for the population it
    cannot see — the failure it was built to expose, one level up.

    ⚑ WHY THIS IS NOT A RE-EMITTER DIFF.  `pycodemod --roundtrip` compares bytes
    because libcst is a lossless CST and any diff is a bug.  There is no lossless
    BibTeX emitter here, and WRITING one would be a second grammar — a fifth
    parser, in the module whose docstring records that it exists to stop being a
    fourth.  So totality is checked the other way: every `@`-header in the file
    must appear as a parsed key, and every `name =` in an entry's body must appear
    as a parsed field.  The file is the oracle; the parse is what must account for
    it.

    `keys-unique` is NOT this check: it compares `@` counts to parsed counts, so
    it sees the duplicate-key row and is blind to all five FIELD-level classes.
    """
    path = path or DEFAULT
    # ⚑⚑ AND THIS WAS A *SECOND*, BYTE-IDENTICAL SPELLING OF `entries`' READER —
    # found by the ⟡vfs-chokepoints migration, not by anything that was looking for
    # it.  `roundtrip` is the mode whose entire job is "the file is the oracle; the
    # parse is what must account for it", and it reached the oracle by a private copy
    # of the read it audits.  Two readers of one artifact can disagree about what
    # ABSENT means, which is precisely the defect class this module's own banner
    # records ("a FOURTH parser, in the tool whose job is to reason about the DAG").
    # Both now route through `_read_bib`, so `--entries` and `--roundtrip` cannot
    # disagree about whether the file is there.
    text = _read_bib(path)

    # ⚑ THE PROBE MUST MASK COMMENTS THE SAME WAY THE PARSE DOES, or it measures
    # a different file and reports the difference as a defect. Routed through the
    # SAME `_strip_comments` rather than re-testing `startswith("%")` here: my
    # first cut did the latter and, because the masking was missing from `entries`
    # itself, correctly reported a vanished entry for the RIGHT reason -- which is
    # how the fabrication bug was found. Two comment rules would have hidden it.
    text = _strip_comments(text)
    out = []
    parsed = entries(path)

    # (1) ENTRY-LEVEL: every @-header must have become a key.
    seen_hdr = []
    for m in re.finditer(r"(?m)^\s*@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        seen_hdr.append((m.group(2), text[:m.start()].count("\n") + 1))
    for key, line in seen_hdr:
        if key not in parsed:
            out.append(("entry-vanished", key, "line %d: header present, not parsed"
                        % line))
    # duplicates: the parse keeps the last, so a repeated key is a silent loss
    counts = {}
    for key, _l in seen_hdr:
        counts[key] = counts.get(key, 0) + 1
    for key, n in sorted(counts.items()):
        if n > 1:
            out.append(("duplicate-key", key, "%d headers, parse keeps 1" % n))

    # (2) FIELD-LEVEL: every `name =` inside a parsed entry's span must be a field.
    # ⚑ The span is re-derived from _ENTRY so this asks about the SAME region the
    # parse read — asking over the whole file would flag prose in comments.
    # ⚑⚑⚑ THE PROBE USED `([\w-]+)` — THE PARSER'S OWN CHARACTER CLASS — SO IT COULD ONLY
    # SEE WHAT THE PARSER SEES. A totality check that re-derives the grammar it is checking
    # measures its own reimplementation and reports TOTAL on a file with invisible fields.
    # Demonstrated: a two-entry fixture with `'rests-on' = {A}` (quoted, well-formed
    # BibTeX) read back as `0 unaccounted-for construct(s) … this read is TOTAL`, while
    # `--entries` listed three fields where the bytes hold four.
    #
    # ⚑⚑ AND THE LIVE COST WAS 60% OF A GRAPH. summit found 56 quoted `rests-on` across
    # its placed floor — 19 of 20 workarounds had their grounding edge invisible — and
    # unquoting moved the edge count from 39 to 98. Every surface was green throughout,
    # including this one. gabion's framing is exact: **`--dropped` answers for the
    # whitelist; nothing answered for the LEXER.**
    #
    # ⚑ SO IT SCANS WITH `_ASSIGN` (`(\S+)\s*=\s*\{`), which is deliberately looser than
    # `_FIELD` and never produces a value — only a discrepancy. Any `<something> = {` the
    # parse did not turn into a field is reported with the raw spelling, so a name form
    # nobody anticipated is LOUD rather than silent. A widened character class handles the
    # spelling seen today; this handles the next one.
    for m in _ENTRY.finditer(text):
        key, body = m.group(2), m.group(3)
        got = set(parsed.get(key, {}))
        # ⚑⚑⚑ MASK THE PARSED VALUES FIRST, OR PROSE READS AS AN ASSIGNMENT. Live false
        # positive on the first run against summit's floor: an entry whose claim discusses
        # a Fano line says `p+q+r = 0 over F2`, and the scan reported `p+q+r` as an
        # unparsed field. That is the USE-VERSUS-MENTION defect for the THIRD time today —
        # after summit's note tail read a narrated attribution as its datum, and after my
        # `_FIELD` grammar read an `=` inside a value as a field boundary — now committed
        # by the instrument built to catch the other two.
        #
        # ⚑⚑ SO THE SCAN RUNS OVER THE BODY WITH EVERY PARSED VALUE BLANKED. What remains
        # is exactly the text the parser did not account for, which is the question being
        # asked; anything inside a value it DID read is by definition accounted for. The
        # masking is length-preserving so the reported line number stays true.
        _masked = body
        for _fm in _FIELD.finditer(body):
            _lo, _hi = _fm.span(2)
            _masked = _masked[:_lo] + (" " * (_hi - _lo)) + _masked[_hi:]
        for f in _ASSIGN.finditer(_masked):
            raw = f.group(1)
            name = raw.strip("'\"")
            if name not in got:
                line = text[:m.start(3) + f.start()].count("\n") + 1
                out.append(("field-unparsed", f"{key}.{raw}",
                            "line %d: `%s = {` in the bytes, no field in the parse"
                            % (line, raw)))
    return out


def set_field(key, field, value, path=None):
    """Return the file text with `key`'s `field` set to `value`. PURE — no write.

    ⚑ DECIDE, THEN APPLY -- the shape `prune_imports` learned after writing
    unconditionally and `conduit_resolve.plan` was built with.  The caller writes;
    this only computes, so a dry run and a real run share one code path and cannot
    disagree.

    ⚑ AND IT REFUSES RATHER THAN GUESSING.  Three refusals, each a measured class:
      * an unknown key -- appending an entry is a DIFFERENT operation from editing
        one, and silently creating it is how a typo becomes a phantom item;
      * a field the entry does not carry -- adding a field is also different, and
        `--dropped` exists precisely because a field the engine ignores is not the
        same as one that is absent;
      * a value containing an unbalanced brace -- `_FIELD` nests ONE level, so a
        deeper value would be truncated at read-back and the write would silently
        lose data.  Refusing is the only honest answer while that is the grammar.

    ⚑ THE POST-CONDITION IS A ROUND-TRIP, NOT A DIFF.  `roundtrip()` over the NEW
    text must be empty: a write that makes the file unparseable to its own reader
    is the fabrication class (a `%` comment swallowing an entry) arriving through
    the write path instead of the read path.
    """
    path = path or DEFAULT
    have = entries(path)
    if key not in have:
        raise SystemExit("bibstruct --set: no entry %r (have %d). Adding an entry "
                         "is a different operation." % (key, len(have)))
    if field not in have[key]:
        raise SystemExit("bibstruct --set: {} carries no {!r} (has: {}). Adding a "
                         "field is a different operation.".format(key, field, ", ".join(sorted(
                             n for n in have[key] if not n.startswith("_")))))
    if value.count("{") != value.count("}"):
        raise SystemExit("bibstruct --set: unbalanced braces in the value; "
                         "`_FIELD` nests one level and would truncate it.")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    # ⚑ MATCH ON MASKED, SLICE THE RAW — and this is only sound because
    # `_strip_comments` is LENGTH-PRESERVING (see its own ⚑).  Returning masked
    # text here instead would write a bib with every comment erased; the dry run
    # measured exactly that against the live file, 533 lines gone.
    masked = _strip_comments(text)

    # ⚑ THE SPAN COMES FROM THE SAME GRAMMAR THE READ USES.  Locating the field by
    # a fresh regex here would be a second parser of the same question -- the
    # fourth-parser hazard this module's docstring exists to name.
    for m in _ENTRY.finditer(masked):
        if m.group(2) != key:
            continue
        body_start = m.start(3)
        for f in _FIELD.finditer(masked[body_start:m.end(3)]):
            if f.group(1) != field:
                continue
            lo = body_start + f.start(2)
            hi = body_start + f.end(2)
            return text[:lo] + value + text[hi:]
    raise SystemExit(f"bibstruct --set: {key}.{field} parsed but its span was not "
                     "located -- the read and the locate disagree, which is a "
                     "defect, not a missing field.")


def add_field(key, field, value, path=None):
    """Return the file text with a NEW `field` on an EXISTING `key`. PURE — no write.

    ⚑⚑⚑ THE THIRD WRITE OPERATION, AND ITS ABSENCE LEFT A REPORT UNREPAIRABLE.  `--set`
    refuses a field the entry does not carry ("adding a field is a different operation")
    and `--add` refuses a key that exists ("this only creates") — both correct, and
    together they mean an entry filed with a MISSING field can be fixed by neither.
    Measured on the live floor: a corroboration written without `note` reads back as
    `kind ?  by ?` and cannot say what it corroborates, because summit parses all three
    of kind/by/of OUT of `note`.  The only routes left were a hand edit of a peer's file
    or deleting and re-adding — the first is the thing this tool exists to prevent, the
    second loses the entry if the re-add refuses.

    ⚑⚑ IT REFUSES A FIELD THAT ALREADY EXISTS, which is `--set`'s job.  The three verbs
    partition cleanly: `--add` mints an entry, `--addfield` widens one, `--set` edits a
    value.  An upsert would make "did I mean to create this?" unanswerable at the call
    site, which is the reason `add_entry` and `set_field` were split in the first place.

    ⚑ THE FIELD LANDS BEFORE THE CLOSING BRACE, matching the existing indentation, and
    the post-condition is the same round-trip `set_field` holds: a write that makes the
    file unparseable to its own reader is the fabrication class arriving through the
    write path.
    """
    path = path or DEFAULT
    have = entries(path)
    if key not in have:
        raise SystemExit("bibstruct --addfield: no entry %r (have %d). Creating an "
                         "entry is `--add`." % (key, len(have)))
    if field in have[key]:
        raise SystemExit(f"bibstruct --addfield: {key} already carries {field!r} (= {have[key][field]!r}). Editing "
                         "a value is `--set`.")
    if value.count("{") != value.count("}"):
        raise SystemExit("bibstruct --addfield: unbalanced braces in the value; "
                         "`_FIELD` nests one level and would truncate it.")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    masked = _strip_comments(text)
    for m in _ENTRY.finditer(masked):
        if m.group(2) != key:
            continue
        # ⚑ INSERT AFTER THE LAST FIELD, not before the first: an entry's first field
        # is conventionally `section` here, and prepending would put a new `note` above
        # it — a diff that touches the entry's shape rather than extending it.
        last = None
        for f in _FIELD.finditer(masked[m.start(3):m.end(3)]):
            last = f
        if last is None:
            raise SystemExit(f"bibstruct --addfield: {key} parsed with no fields to "
                             "follow — the read and the locate disagree.")
        at = m.start(3) + last.end(2)
        # the closing brace of the value, then the comma-and-newline this file uses
        while at < len(text) and text[at] in "}":
            at += 1
        return text[:at] + ",\n  %-8s = {%s}" % (field, value) + text[at:]
    raise SystemExit(f"bibstruct --addfield: {key} parsed but its span was not located — "
                     "the read and the locate disagree, which is a defect.")


def add_entry(key, fields, path=None, corpus=()):
    """Return the file text with a NEW entry appended. PURE — no write.

    `corpus` names SIBLING bibs an edge may legitimately resolve into — see the ⚑ at the
    edge check for why validating against `path` alone was a false refusal.

    ⚑ `--set` REFUSES TO CREATE AND THIS REFUSES TO EDIT, DELIBERATELY.  Editing
    a field and minting a claim are different acts with different blast radii: a
    wrong `--set` changes one value, a wrong `--add` puts a claim into the DAG
    that the ordering will surface as work.  Collapsing them into one
    upsert would make "did I mean to create this?" unanswerable at the call site.

    ⚑ THE WITNESS MUST EXIST BEFORE THE ENTRY, AND THAT IS ENFORCED HERE.
    Measured: `worklist_gate --items D0-kernel` returns `unknown item key(s)`,
    because `check = {item:K}` resolves to a FUNCTION in catalog/library/items.py.
    An entry whose witness is absent files as ORDERED BUT NEVER CLOSABLE --
    permanently open, permanently counted, and indistinguishable from real work.
    That is the `--banner` mistake in its worst form: a census entry nothing can
    ever discharge.  So a `check = {item:K}` naming an unresolvable witness is
    REFUSED rather than written.

    ⚑ AND AN EDGE INTO A NON-EXISTENT KEY IS REFUSED.  `--orphans` reports 0
    dangling edges over 105 today; appending an entry that cites a key which does
    not exist would break an invariant the file currently holds, and it is
    cheaper to refuse than to detect later.
    """
    path = path or DEFAULT
    have = entries(path)
    # ⚑ THE DUPLICATE CHECK STAYS TARGET-LOCAL, DELIBERATELY, and the asymmetry with the
    # edge check below is the point: "does this key already exist HERE" is a question
    # about the file being written, while "does this edge resolve" is a question about
    # the corpus. Widening both would refuse a key that legitimately appears in another
    # genre's bib; widening neither is the bug summit measured.
    if key in have:
        raise SystemExit(f"bibstruct --add: {key!r} already exists. Editing a field is "
                         "`--set`; this only creates.")
    if "claim" not in fields or "check" not in fields:
        raise SystemExit("bibstruct --add: an entry needs at least `claim` and "
                         "`check` (got: {})".format(", ".join(sorted(fields))) or "none")
    for name, value in sorted(fields.items()):
        if value.count("{") != value.count("}"):
            raise SystemExit(f"bibstruct --add: unbalanced braces in {name!r}")
    # ⚑⚑⚑ THE EDGE IS VALIDATED AGAINST THE CORPUS, NOT THE WRITE TARGET, and validating
    # against the target was a FALSE REFUSAL — the dangerous direction. Measured by summit
    # on the first two writes after it split a 242-entry monolith into five per-genre
    # bibs: a corroboration in `reports-corroboration.bib` resting on a use-case in
    # `reports-usecase.bib` was refused as dangling WHEN IT IS NOT, and the entry had to
    # be placed with its edge demoted to prose.
    #
    # ⚑⚑ THE REFUSAL'S OWN JUSTIFICATION NAMED THE BUG. It says an edge into a
    # non-existent key "would make `--orphans` non-empty" — and `--orphans` reads MANY
    # bibs, positionally, by design. So the writer was enforcing a corpus-wide invariant
    # against a single-file population: a narrower set than the property it protects,
    # which is exactly how a valid edge reads as dangling.
    #
    # ⚑ AND IT IS THE SAME SHAPE AS THE `--bib`-ON-A-READ-MODE REFUSAL THIS FILE ALREADY
    # CARRIES, inverted. That one exists because passing `--bib` to a read DROPPED a file
    # from the read set and reported a peer's clean corpus as broken — over-reporting from
    # a too-narrow population. This is the write-side instance of one defect: whenever the
    # population and the invariant disagree about scope, the answer is wrong in whichever
    # direction the gap points. `--corpus` states the scope rather than inferring it.
    known = dict(have)
    for other in corpus or ():
        if os.path.abspath(other) != os.path.abspath(path):
            known.update(entries(other))
    for efield in EDGE_FIELDS:
        for dest in re.split(r"[,\s]+", fields.get(efield, "").strip()):
            if dest and dest not in known and dest != key:
                raise SystemExit(
                    "bibstruct --add: %s names %r, which is not an entry in the %d "
                    "file(s) read. An edge into a non-existent key would make "
                    "--orphans non-empty.\n"
                    "  ⚑ IF THE TARGET LIVES IN A SIBLING BIB, name it: "
                    "`--corpus <bib> [<bib> …]`. A split corpus makes an edge "
                    "cross files, and this check reads only what it is given — "
                    "'not in the population' is NOT 'does not exist'."
                    % (efield, dest, 1 + len(corpus or ())))
    # the witness must resolve, or the item can never be closed
    m = re.match(r"item:(\S+)", fields["check"].strip())
    if m:
        wkey = m.group(1)
        # ⚑⚑ THE WITNESS FILE IS THE TARGET PROJECT'S, NOT A HARDCODED PATH — and it WAS
        # hardcoded to `catalog/library/items.py` until 2026-08-23, which made this guard
        # refuse every `item:` check filed into any OTHER paperkit project in the tree. The
        # first such project (`.claude/agents/`, the oracle findings ledger) could not file a
        # single entry: a correct refusal, aimed at the wrong file, with an error message
        # naming a project the filer was not using.
        # ⚑ THE PROJECT OWNS THE VERB. `paper.toml`'s `[checks.item] cmd` is what actually
        # resolves a witness at gate time, so the resolver here must read the SAME project the
        # bib belongs to — the bib's own directory. Falling back to `catalog/library/items.py`
        # keeps every existing caller working, since that is where the original project's
        # witnesses live.
        _bibdir = os.path.dirname(os.path.abspath(path or DEFAULT))
        ipath = next((p for p in (os.path.join(_bibdir, "findings.py"),
                                  os.path.join(_bibdir, "items.py"),
                                  os.path.join(ROOT, "catalog", "library", "items.py"))
                      if os.path.exists(p)), None)
        if ipath is None:
            raise SystemExit(
                f"bibstruct --add: no witness module to resolve check=item:{wkey} against — "
                f"looked for findings.py or items.py beside {_bibdir}, then "
                "catalog/library/items.py")
        # ⚑ THE DEFINITION, NOT A MENTION.  A key named in a docstring or a
        # comment is not a witness; this is the `--calls` lesson (a name in prose
        # is not a call) applied to the witness roster.
        isrc = open(ipath, encoding="utf-8").read()
        # ⚑ THE KEY IS NOT THE FUNCTION NAME, AND MY FIRST CUT ASSUMED IT WAS.
        # `T28-edges` resolves to `def T28_EDGES(`; the mapping is hyphen->
        # underscore, and the tail is UPPERCASED.  Checking the literal key
        # rejected `D0-kernel` on its own correct witness -- and would have
        # rejected every hyphenated key, which is most of them.  A guard that
        # refuses the whole population it governs is worse than none, because it
        # reads as strictness.  ⚑ AND THE REGISTRATION IS THE REAL PREDICATE:
        # `--items` resolves through the ITEMS dict, so a defined-but-
        # unregistered function is still unreachable (measured: `def D0_KERNEL(`
        # existed and `--items D0-kernel` said `unknown item key(s)`).
        cands = {wkey, wkey.replace("-", "_"),
                 wkey.replace("-", "_").upper()}
        # ⚑⚑ TWO WITNESS SHAPES, AND REQUIRING ONE WOULD BE A ROSTER REFUSING ITS OWN
        # POPULATION. `catalog/library/items.py` registers `def KEY(...)` and maps the name in
        # `ITEMS`; `.claude/agents/findings.py` registers a lambda directly in `WITNESSES`, one
        # entry per finding, because a finding's witness is usually two lines and a named def
        # per line is ceremony. Both are REGISTRATIONS — the predicate that matters is *can
        # `--items <key>` resolve it*, which is the dict membership tested below, and the
        # definition check is the weaker one. A key registered as a dict value satisfies the
        # real requirement without a matching `def`.
        _defined = any(re.search(rf"(?m)^def\s+{re.escape(c)}\s*\(", isrc)
                       for c in cands)
        _lambda = re.search(rf'(?m)^\s*"{re.escape(wkey)}"\s*:\s*(lambda|_)', isrc)
        if not (_defined or _lambda):
            raise SystemExit(
                "bibstruct --add: check=item:{} but {} defines none of {}. The witness must "
                "exist FIRST, or the item files as ordered-but-never-closable.".format(wkey, os.path.relpath(ipath, ROOT),
                   ", ".join(f"`def {c}(`" for c in sorted(cands))))
        if not re.search(rf'(?m)^\s*"{re.escape(wkey)}"\s*:', isrc):
            raise SystemExit(
                f"bibstruct --add: check=item:{wkey} has a witness function but is "
                f"NOT REGISTERED in the ITEMS dict, so `--items {wkey}` cannot "
                "resolve it. Defining the function is not registering the item.")

    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    # ⚑ FIELD ORDER IS THE FILE'S, NOT A DICT'S.  The bib writes section/from/
    # join before claim/check; matching it keeps the projection's render order
    # stable and the diff readable.
    order = ["section", "from", "rests-on", "enables", "join", "claim", "check"]
    keys = [k for k in order if k in fields] + \
           [k for k in sorted(fields) if k not in order]
    body = "".join("  %-8s = {%s},\n" % (k, fields[k]) for k in keys)
    body = body.rstrip(",\n") + "\n"
    entry = f"\n@misc{{{key},\n{body}}}\n"
    return text.rstrip("\n") + "\n" + entry


def _refuses(fn):
    """True if `fn` REFUSES (SystemExit) rather than returning a value.

    ⚑ A refusal is a VERDICT and must be asserted as one: a predicate that
    returns empty where it should refuse is the inert-guard shape.
    """
    try:
        fn()
        return False
    except SystemExit:
        return True


def _selftest():
    import tempfile
    cases = []

    def check(label, got, want):
        cases.append((label, got == want, got, want))

    with tempfile.TemporaryDirectory() as d:
        # ⚑⚑ THE WITNESS MODULE IS WRITTEN BY THE FIXTURE, not borrowed from the OWNING
        # REPO'S `catalog/library/items.py`.  Found by the paperkit relocation (2026-08-28):
        # `T27` was a live witness in ONE tree, so every `item:` case silently depended on
        # this suite running inside that checkout, and it died anywhere else with `no witness
        # module to resolve check=item:T27 against`.  A selftest that reads a roster it does
        # not create is measuring the CHECKOUT, not the tool.  `add_entry`'s resolver already
        # looks BESIDE THE BIB first (generalised 2026-08-23), so writing the module into the
        # fixture's own tmpdir needs no resolver change and makes the suite self-contained.
        # It is written HERE, at the top, because `item:` entries appear in the very first
        # fixture bib below — placing it beside the `--add` cases was too late by ~500 lines.
        # `T27`/`T28-edges` are REGISTERED, `_open` is defined-but-UNREGISTERED (the
        # roster-vs-definition case), and `NoSuchWitness` is absent from both.
        with open(os.path.join(d, "items.py"), "w", encoding="utf-8") as fh:
            fh.write("def T27():\n    pass\n\n\n"
                     "def T28_EDGES():\n    pass\n\n\n"
                     "def A():\n    pass\n\n\n"
                     "def B():\n    pass\n\n\n"
                     "def C():\n    pass\n\n\n"
                     "def _open():\n    pass\n\n\n"
                     # ⚑ DOUBLE-QUOTED, ONE PER LINE: the registration probe is
                     # `^\\s*"<key>"\\s*:` (line-anchored), so a single-quoted key or two
                     # on one line reads as UNREGISTERED and the refusal names the
                     # roster rather than the spelling.
                     "ITEMS = {\n"
                     '    "T27": T27,\n'
                     '    "T28-edges": T28_EDGES,\n'
                     '    "A": A,\n'
                     '    "B": B,\n'
                     '    "C": C,\n'
                     "}\n")
        p = os.path.join(d, "w.bib")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("% a comment line\n"
                     "@misc{A,\n"
                     "  section = {s},\n"
                     "  claim   = {alpha},\n"
                     "  check   = {item:A}\n"
                     "}\n\n"
                     "@misc{B,\n"
                     "  section = {s}, from = {A}, rests-on = {A},\n"
                     "  enables = {A, NOSUCH},\n"
                     "  claim   = {beta},\n"
                     "  check   = {item:B}\n"
                     "}\n")
        e = entries(p)
        check("both entries parse", sorted(e), ["A", "B"])
        check("fields are read verbatim", e["A"]["claim"], "alpha")

        # ⚑⚑ THE COMPOSED-CORPUS CASES, AND THEY MUST DRIVE `main()` RATHER THAN `entries()`.
        # The defect lived entirely in the CLI: `entries()` was always correct, and `main` read
        # `paths[0]` while collecting every positional.  A case calling `entries()` twice by hand
        # would pass against the broken code — it never touches the layer that dropped the files.
        p2 = os.path.join(d, "w2.bib")
        with open(p2, "w", encoding="utf-8") as fh:
            fh.write("@misc{C,\n"
                     "  section = {s}, rests-on = {A},\n"
                     "  claim   = {gamma},\n"
                     "  check   = {item:C}\n"
                     "}\n")
        import contextlib
        import io

        # ⚑⚑⚑ A `SystemExit` FROM `main` IS A CASE OUTCOME, NOT THE END OF THE SUITE.
        # ⟡bibstruct-selftest-swallowed, repaired 2026-08-25.  This helper used to let a
        # `SystemExit` propagate out of `_selftest`, so ANY refusal reached through the CLI
        # terminated the run at that line — and every case after it never executed while the
        # suite still printed an `N/N` that read as full coverage.  Measured: the abort was
        # at the `--add F` case (line ~1925), which drives a real write and therefore hits
        # `edit_snapshot.guard`; `guard` reads the PROCESS argv (`--selftest`), never the
        # synthetic list handed to `main`, so the explicit-mutation contract refused with
        # exit 2 and 24 cases below it were dead text.  A prior agent MEASURED this, filed
        # it in-line, and refused to report those cases green — which is why it is fixed
        # here rather than discovered later.
        #
        # ⚑⚑ THE COUNT WAS THE ARTIFACT THAT LIED.  `census-green-is-a-fact-about-the-census`
        # in its strongest form: a suite's own N/N is what every other reading trusts, and
        # this one was reporting a population it had stopped iterating.  Cases that cannot
        # run are not coverage, and a suite that cannot survive a refusal cannot ASSERT on
        # one — which matters here because refusing is most of what this tool does.
        #
        # ⚑ CAPTURED AS TEXT, NOT SWALLOWED.  The exit's message is appended to the
        # captured stdout so a case can assert on the refusal's WORDING, and `_rc` below
        # remains the mode for asserting on the return CODE.  Nothing is hidden: a case
        # that did not expect a refusal now goes RED with the refusal text in `got`.
        def _run(*argv):
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    main(list(argv))
            except SystemExit as _exc:
                return buf.getvalue() + f"\nSystemExit: {_exc}"
            return buf.getvalue()

        # C rests-on A, which lives in the OTHER bib. Read alone, that premise is unresolvable
        # and C reports as dangling; read TOGETHER, it resolves. Same edge, opposite verdict —
        # which is the whole reason a composed corpus is the unit.
        check("a premise in another bib is DANGLING when that bib is not passed",
              "no such entry" in _run("--orphans", p2), True)
        # ⚑ NAMED, not just "no such entry": `w.bib` carries a DELIBERATE dangling
        # `enables = {A, NOSUCH}`, so the file is never orphan-free and a bare
        # "no orphans" assertion would fail for a reason that has nothing to do with
        # composition. The claim is about C's premise specifically.
        check("...and C's premise RESOLVES when both bibs are passed",
              "C -> A" in _run("--orphans", p2, p), False)
        check("...while the fixture's OWN deliberate dangler is still reported",
              "NOSUCH" in _run("--orphans", p2, p), True)
        # ⚑ THE COUNT CASE — the one that catches the exact silent-drop signature. Reading both
        # must report 3 entries; the broken code reported the first file's 2 and ignored the rest,
        # so a byte-identical count across a widened input read as "the finding survives."
        check("every bib passed is counted", "over 3 entries" in _run("--orphans", p, p2), True)

        # ⚑⚑ THE DUPLICATE-KEY CASES — paperkit's 77-vs-84, reduced.  A composed read reports
        # DISTINCT KEYS; a record-counting parser reports DECLARATIONS.  Both are right, and an
        # unexplained gap between them reads as a parse defect (paperkit had to rule one out by
        # hand).  `p3` re-declares A, which `p` already has.
        p3 = os.path.join(d, "w3.bib")
        with open(p3, "w", encoding="utf-8") as fh:
            fh.write("@misc{A,\n"
                     "  section = {s},\n"
                     "  claim   = {alpha-redeclared},\n"
                     "  check   = {item:A}\n"
                     "}\n")
        out = _run("--orphans", p, p3)
        check("a key declared in two bibs is REPORTED, not merged silently",
              "1 key(s) declared in BOTH" in out and "(later wins): A" in out, True)
        check("...and the distinct-vs-declared gap is named",
              "1 key(s) declared in more than one bib" in out, True)
        # ⚑ THE CONTROL: without it, a mode that warned unconditionally would pass both cases
        # above while being useless. Two bibs with disjoint keys must report NO collision.
        check("...while disjoint bibs report no collision",
              "declared in BOTH" in _run("--orphans", p, p2), False)
        # ⚑⚑ AND THE STATE CASE, WHICH ONLY WORKS IN THIS ORDER.  `collisions` is module-level,
        # so a stale list from the COLLIDING read above must not leak into a clean one after it.
        # Running the clean read first would pass against a version that never clears — the
        # assertion has to follow the dirty read to mean anything, which is why the two
        # identical-looking `_run(p, p2)` calls are not redundant: one is a control, this is a
        # sequence.
        _run("--orphans", p, p3)
        check("a stale collision does NOT leak into the next clean read",
              "declared in BOTH" in _run("--orphans", p, p2), False)

        # ⚑⚑ `--bib` ON A READ MODE IS A REFUSAL, NOT A SILENT DROP.  It is the WRITE target and
        # is removed from the read set, so `--orphans --bib a b` read only `b` — which on a
        # peer's 12-bib corpus produced an unstable entry count and 18 FALSE dangling edges,
        # reporting a clean corpus as broken.  Over-reporting is the dangerous direction, and a
        # flag that means something else in this mode must not be accepted in silence.
        # ⚑ SAME TRAP AS `_run`, FOR THE SAME REASON (⟡bibstruct-selftest-swallowed).  A
        # `SystemExit` here is REPORTED AS THE RETURN CODE, which is the honest mapping:
        # `sys.exit(2)` and `return 2` are the same verdict to an operator, and a case
        # asserting `rc == 2` must not care which spelling produced it.  The refusal's text
        # still reaches the caller through the captured stderr.
        # ⚑ AND A THIRD SPELLING OF THE SAME VERDICT, FOUND BY THE PAPERKIT RELOCATION.
        # `guard()` enforces the --apply XOR --dry-run contract by RAISING
        # `edit_snapshot.MutationContractError`, not by exiting — so the armed arm below,
        # which asserts `rc == 2`, never saw a return value at all: the exception escaped
        # `_rc`, unwound the whole selftest, and the run died at case ~90 with a traceback
        # instead of a verdict.  Measured in BOTH trees (substrate's copy fails identically),
        # so this is a live defect the move surfaced rather than one it caused.  A refusal is
        # rc 2 whether it was spelled `return 2`, `sys.exit(2)`, or a contract exception; the
        # trap must cover every spelling or the case asserts nothing about the armed world.
        def _rc(*argv):
            buf, err = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
                    rc = main(list(argv))
            except SystemExit as _exc:
                _code = _exc.code
                return (_code if isinstance(_code, int) else 2), err.getvalue() + str(_exc)
            except _mutation_contract_error() as _exc:
                return 2, err.getvalue() + str(_exc)
            return rc, err.getvalue()

        # ⚑⚑⚑ THE DENOMINATOR INVARIANT — one case that would have caught ALL THREE of this
        # tool's silent defects, where the three case-families above each catch one.  paperkit
        # proposed it after the second: *"a reported entry-count that disagrees with the parse
        # by 7 is the signature-shaped thing worth a selftest case: `over N entries` must equal
        # the parsed key count."*
        #
        # ⚑⚑ WHY IT IS THE GENERAL FORM.  Every defect this tool shipped today was a DENOMINATOR
        # that stopped describing the input, in a different direction each time — silent DROP
        # (read one file, reported it as all: N too small); silent MERGE (read all files,
        # reported distinct keys as declarations: N too small in a second way); silent FLAG
        # (dropped a file from the read set and over-reported dangling: N too small, verdict too
        # big).  Each individual VERDICT looked like a result.  Asserting the printed N against
        # an independently-computed N catches the class rather than the instance.
        #
        # ⚑ AND IT IS STILL NOT THE FULL GATE, WHICH IS THE HONEST LIMIT.  This runs on a
        # FIXTURE with argv this function wrote — and the third defect only manifested on a
        # peer's corpus with a peer's invocation, which no fixture reaches.  The general
        # statement (paperkit's, and it belongs in their RFC not in this comment) is that an
        # instrument measuring composition must be gated against the CONSUMED input, invocation
        # included.  This case is the reachable half of that; the unreachable half is why the
        # exchange that produced it was worth more than the case.
        _n_expected = len(set(entries(p)) | set(entries(p2)) | set(entries(p3)))
        _out = _run("--orphans", p, p2, p3)
        check("the REPORTED denominator equals the independently-parsed key count",
              "over %d entries" % _n_expected in _out, True)
        # ⚑ THE CONTROL: the invariant must be able to FAIL. A wrong expectation must not pass,
        # or the case is asserting the tool's output against itself.
        check("...and a wrong denominator would NOT match",
              "over %d entries" % (_n_expected + 1) in _out, False)

        rc, err = _rc("--orphans", "--bib", p, p2)
        check("a read mode REFUSES --bib", rc, 2)
        check("...and the refusal names the read form", "POSITIONALLY" in err, True)
        # ⚑ THE CONTROL: --bib must still WORK on the write modes it belongs to, or the refusal
        # has broken the flag's actual purpose — cross-repo filing, which is why it exists.
        check("...while a write mode still accepts it",
              _rc("--set", "A", "claim", "x", "--bib", p)[0] != 2, True)

        # ⚑ THE CASE THAT PINS THE DEFECT.  `enables` is NOT in the engine's
        # whitelist, so a consumer using `bib.parse` reads it as absent — which
        # is how `worklist_gate.order()` came to hand-roll a regex for it.
        drops = {(k, n) for k, n, _v in dropped(p)}
        check("`enables` is reported as ENGINE-DROPPED", ("B", "enables") in drops,
              True)
        check("a whitelisted field is NOT reported dropped",
              ("B", "rests-on") in drops, False)

        # ⚑⚑⚑ THE COMPLEMENT, AND ITS ABSENCE IS WHY THE DEFECT SHIPPED.  The case above
        # pins the UNDECLARED half and passed throughout; nothing pinned the DECLARED half,
        # so `engine_view` calling `B.parse(path)` — which applies paperkit's DEFAULT
        # whitelist and ignores a project's `consumer_fields` — reported every declared
        # field as dropped forever and no case could tell.  MEASURED 2026-08-23 on the live
        # worklist: 14 warnings against a field the project had correctly declared, which I
        # read as the ENGINE's verdict and spent a cross-session thread chasing.
        #
        # ⚑ A CENSUS OF WHAT AN AUTHORITY DROPS MUST ASK THE AUTHORITY AS THIS PROJECT
        # CONFIGURED IT.  `parse(path, consumer_fields=())` is correctly configured for a
        # project that declares nothing, so the wrong call is the SHORT one and silent —
        # paperkit's owner names that default as their trap, and I am its second victim.
        # The fix routes through `load_bib(bib, project_dir)`, which binds the project's
        # declared fields; this case is what would have caught it.
        _proj = os.path.join(d, "declared")
        os.makedirs(_proj, exist_ok=True)
        open(os.path.join(_proj, "paper.toml"), "w").write(
            '[paper]\ntitle = "t"\nwarrants = ["w.bib"]\nout = "O.md"\n'
            'consumer_fields = ["enables"]\n')
        _dp = os.path.join(_proj, "w.bib")
        open(_dp, "w").write(
            "@misc{B,\n  section = {s},\n  claim = {c},\n  check = {item:T27},\n"
            "  enables = {A},\n}\n")
        check("⚑ a DECLARED consumer field is NOT reported dropped",
              ("B", "enables") in {(k, n) for k, n, _v in dropped(_dp)}, False)

        # ⚑ THE TOTALITY PROBE — and every case below drives a REAL DROP rather
        # than asserting the probe's own arithmetic.  A case that only checks
        # `roundtrip([]) == []` on a clean file would pass against a probe that
        # examines nothing, which is the inert-guard shape this repo has now
        # caught five times.
        check("a well-formed bib round-trips with no loss", roundtrip(p), [])

        # ⚑⚑⚑ `_read_bib`'s THREE ARMS, STARVED AGAINST EACH OTHER (⟡vfs-chokepoints).
        # Before the `vfs` lift, `entries` and `roundtrip` EACH carried a private,
        # byte-identical `except OSError -> SystemExit("cannot read %s")`, so a bib
        # that was absent, a bib that was a directory, and a bib that could not be
        # opened produced ONE message.  Exactly one of those three is a legitimate
        # answer.  Both readers now route here, so the two modes cannot disagree about
        # whether the corpus is there.
        #
        # ⚑ THE ARMS ARE ASSERTED TO DIFFER, not merely to each fire.  A check whose
        # all-clear has never been shown to differ from its found-something is not a
        # measurement — and the mdstruct half of this same migration was measured to
        # have exactly that gap, which is why these are here rather than assumed.
        #
        # ⚑⚑⚑ AND THESE CASES DID NOT RUN — MEASURED, AND SAID OUT LOUD RATHER THAN LEFT
        # FOR A LATER READER TO DISCOVER.  Claim as filed (2026-08-25, kept verbatim):
        # *"This suite ABORTS earlier (exit 2) because `_run` invokes `main`, and `main`'s
        # `--add` explicit-mutation refusal raises `SystemExit`, which `_run` does not trap.
        # So execution never reaches this point, and adding cases here moved the suite's
        # output by ZERO bytes against its own baseline.  A case that cannot run is not
        # coverage, and reporting these as green would be exactly the false-green this file
        # censuses elsewhere.  They were verified through the CLI instead
        # (`--entries`/`--roundtrip` against a missing path and against a directory), and
        # the abort is a PRE-EXISTING suite defect — filed here, not fixed here, because
        # repairing `_run`'s `SystemExit` handling would change what the whole suite
        # asserts and belongs in its own edit."*
        #
        # ⚑ STATUS 2026-08-25 (⟡bibstruct-selftest-swallowed): REPAIRED, in that separate
        # edit.  `_run` and `_rc` now trap `SystemExit` and report it as a case outcome,
        # and the write-driving cases state `intent="apply"` at the call site rather than
        # relying on a process argv that says `--selftest`.  The diagnosis above was exactly
        # right; re-derive the reach with `bibstruct.py --selftest` and compare the printed
        # denominator, which is the number that was lying.  The filing is kept rather than
        # deleted — a repair is residue, not an erasure, and the defect is the argument for
        # the trap.
        _absent_msg = _broken_msg = None
        try:
            entries(os.path.join(d, "nosuch.bib"))
        except SystemExit as _e:
            _absent_msg = str(_e)
        try:
            entries(d)                             # a DIRECTORY, not a bib
        except SystemExit as _e:
            _broken_msg = str(_e)
        check("⚑ an ABSENT bib names itself ABSENT",
              bool(_absent_msg) and "ABSENT" in _absent_msg, True)
        check("⚑ a BROKEN read names itself BROKEN, and says the read did not happen",
              bool(_broken_msg) and "BROKEN" in _broken_msg, True)
        check("⚑⚑ ABSENT and BROKEN are DIFFERENT messages, not one 'cannot read'",
              _absent_msg == _broken_msg, False)
        # ⚑ AND `roundtrip` — the SECOND former reader — must agree with `entries`
        # about absence.  Two readers of one artifact disagreeing about what ABSENT
        # means is precisely the defect this module's banner records against itself.
        _rt_msg = None
        try:
            roundtrip(os.path.join(d, "nosuch.bib"))
        except SystemExit as _e:
            _rt_msg = str(_e)
        check("⚑⚑ roundtrip and entries give the SAME verdict on an absent bib",
              _rt_msg, _absent_msg)
        # ⚑ A NON-UTF-8 BIB IS BROKEN, NOT EMPTY AND NOT PARTIAL.  The strict decode
        # refuses rather than handing the grammar a replacement-char corpus that would
        # parse into plausible entries — the one failure class here that FABRICATES.
        _mangled = os.path.join(d, "mangled.bib")
        open(_mangled, "wb").write(b"@misc{A,\n  claim = {\xff\xfe},\n}\n")
        _utf8_msg = None
        try:
            entries(_mangled)
        except SystemExit as _e:
            _utf8_msg = str(_e)
        check("⚑ a non-UTF-8 bib is refused, not parsed into plausible entries",
              bool(_utf8_msg) and "not valid UTF-8" in _utf8_msg, True)

        # (1) ENTRY-VANISHED: the closing brace INDENTED.  `_ENTRY` requires
        # `\n}` at column 0, so the whole entry disappears and `--entries`
        # reports success over a file it did not fully read.
        q = os.path.join(d, "indent.bib")
        with open(q, "w", encoding="utf-8") as fh:
            fh.write("@misc{A,\n  claim = {a}\n}\n\n"
                     "@misc{B,\n  claim = {b}\n  }\n")
        check("an INDENTED closing brace makes the entry vanish from the parse",
              "B" in entries(q), False)
        check("and roundtrip REPORTS that vanished entry",
              [k for k, w, _d in roundtrip(q) if w == "B"], ["entry-vanished"])

        # (2) ENTRY-VANISHED: the whole entry on ONE line.
        r = os.path.join(d, "oneline.bib")
        with open(r, "w", encoding="utf-8") as fh:
            fh.write("@misc{A,\n  claim = {a}\n}\n\n@misc{B, claim = {b}}\n")
        check("a ONE-LINE entry vanishes from the parse", "B" in entries(r), False)
        check("and roundtrip reports it",
              any(w == "B" for _k, w, _d in roundtrip(r)), True)

        # (3) FIELD-DROPPED: a QUOTED value.  The entry survives WITH A HOLE,
        # which is the worse case — a partial answer reads as a complete one.
        s = os.path.join(d, "quoted.bib")
        with open(s, "w", encoding="utf-8") as fh:
            fh.write('@misc{A,\n  claim = {a},\n  from = "B"\n}\n')
        check("a QUOTED field is silently absent from the parse",
              "from" in entries(s).get("A", {}), False)
        check("and roundtrip reports the hole, naming entry.field",
              [w for _k, w, _d in roundtrip(s)], ["A.from"])

        # (4) FIELD-DROPPED: a BARE INTEGER value.
        t = os.path.join(d, "bare.bib")
        with open(t, "w", encoding="utf-8") as fh:
            fh.write("@misc{A,\n  claim = {a},\n  year = 2026\n}\n")
        check("a BARE-INTEGER field is silently absent",
              "year" in entries(t).get("A", {}), False)
        check("and roundtrip reports it",
              [w for _k, w, _d in roundtrip(t)], ["A.year"])

        # (5) DUPLICATE KEY: the parse keeps the LAST silently, so an entry is
        # lost with no count change that `--entries` could show.
        u = os.path.join(d, "dup.bib")
        with open(u, "w", encoding="utf-8") as fh:
            fh.write("@misc{A,\n  claim = {first}\n}\n\n"
                     "@misc{A,\n  claim = {second}\n}\n")
        check("a DUPLICATE key silently keeps the last", entries(u)["A"]["claim"],
              "second")
        check("and roundtrip reports the duplicate",
              [k for k, _w, _d in roundtrip(u)], ["duplicate-key"])

        # ⚑ A `%` COMMENT MENTIONING AN @-KEY IS NOT AN ENTRY.  The live bib is
        # 66% comment lines; counting prose as a header would make the probe
        # refuse a clean file — a false positive in a totality check is worse
        # than none, because it trains the reader to ignore it.
        v = os.path.join(d, "cmt.bib")
        with open(v, "w", encoding="utf-8") as fh:
            fh.write("% see @misc{GHOST, ...} for the shape\n"
                     "@misc{A,\n  claim = {a}\n}\n")
        check("an @-key inside a % comment is not read as an entry",
              roundtrip(v), [])

        # ⚑ `--set` IS PURE AND REFUSES THREE CLASSES.  Each refusal is asserted
        # as a VERDICT (`_refuses`), not as an empty return -- a predicate that
        # returns nothing where it should refuse is the inert-guard shape.
        check("--set edits the named field in place",
              "beta2" in set_field("B", "claim", "beta2", p), True)
        check("--set leaves the OTHER entry untouched",
              "alpha" in set_field("B", "claim", "beta2", p), True)
        check("--set REFUSES an unknown key",
              _refuses(lambda: set_field("NOPE", "claim", "x", p)), True)
        check("--set REFUSES a field the entry does not carry",
              _refuses(lambda: set_field("A", "enables", "x", p)), True)
        check("--set REFUSES an unbalanced value",
              _refuses(lambda: set_field("B", "claim", "a {b", p)), True)
        # ⚑ THE PURITY CASE.  `set_field` returning text is what lets the dry run
        # and the real run share one path; if it ever wrote, this would fail.
        _before = open(p, encoding="utf-8").read()
        set_field("B", "claim", "beta3", p)
        check("--set is PURE — computing a change writes nothing",
              open(p, encoding="utf-8").read(), _before)
        # ⚑ AND THE RESULT MUST STILL ROUND-TRIP.  A write is only correct if the
        # file remains readable to the parser that produced it.
        w = os.path.join(d, "written.bib")
        with open(w, "w", encoding="utf-8") as fh:
            fh.write(set_field("B", "enables", "A, C", p))
        check("a --set result still round-trips", roundtrip(w), [])
        check("and the new value reads back", entries(w)["B"]["enables"], "A, C")

        # ⚑⚑⚑ `--addfield` — THE OPERATION WHOSE ABSENCE LEFT AN ENTRY UNREPAIRABLE.
        # Measured on summit's live floor: a corroboration filed WITHOUT `note` reads
        # back as `kind ?  by ?` and cannot say what it corroborates, because summit
        # parses kind/by/of out of that one field. `--set` refused (no such field),
        # `--add` refused (key exists), and the two refusals are individually right —
        # so the entry could be fixed by neither, and the only routes left were a hand
        # edit of a peer's file or a delete-and-re-add that loses it if the re-add
        # refuses. The verbs now partition: mint / widen / edit.
        # ⚑⚑⚑ A CROSS-FILE EDGE IS NOT A DANGLING EDGE, and validating against the write
        # target alone was a FALSE REFUSAL — the dangerous direction. Measured by summit
        # on the first two writes after splitting a 242-entry floor into five per-genre
        # bibs: a corroboration resting on a use-case in a sibling file refused, and the
        # entry was placed with its edge demoted to prose. The refusal's own text named
        # the bug (it protects `--orphans`, which reads MANY bibs) and nothing here
        # caught it, because every case fed one file.
        _sib = os.path.join(d, "sib.bib")
        with open(_sib, "w", encoding="utf-8") as fh:
            fh.write("@misc{FAR,\n  section = {s},\n  claim = {far},\n"
                     "  check = {item:T27}\n}\n")
        _here = os.path.join(d, "here.bib")
        with open(_here, "w", encoding="utf-8") as fh:
            fh.write("@misc{NEAR,\n  section = {s},\n  claim = {near},\n"
                     "  check = {item:T27}\n}\n")
        check("--add REFUSES an edge into a key it cannot see",
              _refuses(lambda: add_entry(
                  "X", {"claim": "c", "check": "item:T27", "rests-on": "FAR"}, _here)),
              True)
        check("...and ACCEPTS it once --corpus names the sibling that defines it",
              "FAR" in add_entry(
                  "X", {"claim": "c", "check": "item:T27", "rests-on": "FAR"},
                  _here, [_sib]), True)
        # ⚑⚑ AND A KEY IN NO FILE IS STILL REFUSED WITH THE CORPUS WIDE OPEN. Widening
        # the population must not weaken the invariant — otherwise `--corpus` becomes a
        # way to silence the check rather than to state its scope.
        check("...while a key in NEITHER file is still refused",
              _refuses(lambda: add_entry(
                  "X", {"claim": "c", "check": "item:T27", "rests-on": "NOWHERE"},
                  _here, [_sib])), True)
        # ⚑ THE DUPLICATE CHECK STAYS TARGET-LOCAL. A key existing in a SIBLING is not a
        # duplicate here — genres are separate files and `--add` must still create.
        check("...and a key defined only in the sibling is NOT a duplicate here",
              "FAR" in add_entry("FAR", {"claim": "c", "check": "item:T27"},
                                 _here, [_sib]), True)
        # ⚑⚑⚑ `--corpus` STOPS AT THE NEXT FLAG. It scanned to the END of argv filtering
        # out `-`-prefixed tokens, so `--corpus a.bib --bib target.bib` ate `target.bib`
        # as a corpus member — summit measured two failed invocations and found only
        # `--corpus` LAST worked, with nothing saying so. The silent half is worse: with
        # `--bib`'s operand consumed, the write falls through to DEFAULT, so an `--add`
        # aimed at a peer's floor can diff cleanly against THIS repo's warrants.bib.
        # Asserted on the PARSE, since the failure is an operand crossing a flag boundary.
        _argv_probe = ["--add", "K", "claim=c", "check=true",
                       "--corpus", _sib, "--bib", _here]
        # ⚑⚑⚑ THE LEXER CENSUS — fields present in the BYTES and absent from the PARSE.
        # The field-level probe used `([\w-]+)`, the parser's OWN character class, so it
        # measured its own reimplementation and reported TOTAL on a file whose fields it
        # could not see. Live cost, measured by summit: 56 quoted `'rests-on'` across the
        # placed floor, 19 of 20 workarounds with their grounding edge invisible, and the
        # edge count moving 39 → 98 on repair. Every surface green throughout, including
        # this probe. gabion's framing: `--dropped` answers for the WHITELIST; nothing
        # answered for the LEXER.
        _unp = os.path.join(d, "unparsed.bib")
        with open(_unp, "w", encoding="utf-8") as fh:
            fh.write("@misc{U,\n  section = {s},\n  claim = {c},\n"
                     "  check = {item:T27},\n  meta:origin = {A}\n}\n")
        _rows = roundtrip(_unp)
        check("roundtrip reports a field the LEXER cannot see",
              [k for k, _w, _d in _rows], ["field-unparsed"])
        # ⚑⚑ IT NAMES THE RAW SPELLING, not a normalised guess. A name form nobody
        # anticipated is exactly the case here, so echoing what is in the bytes is the
        # only honest report — `meta:origin`, not `origin` or a shrug.
        check("...naming the raw spelling from the bytes",
              [w for _k, w, _d in _rows], ["U.meta:origin"])
        # ⚑ AND A FILE WHOSE FIELDS ALL PARSE STILL READS CLEAN. A probe that fires on
        # everything is as useless as one that fires on nothing; both halves are asserted
        # because only the pair distinguishes a detector from a constant.
        _ok2 = os.path.join(d, "allparsed.bib")
        with open(_ok2, "w", encoding="utf-8") as fh:
            fh.write("@misc{V,\n  section = {s},\n  claim = {c},\n"
                     "  check = {item:T27},\n  'rests-on' = {U}\n}\n")
        check("...while a quoted-but-parseable field is NOT reported", roundtrip(_ok2), [])
        # ⚑⚑ AND PROSE INSIDE A VALUE IS NOT AN ASSIGNMENT. Live false positive on the
        # first run against summit's floor: a claim discussing a Fano line says
        # `p+q+r = 0 over F2`, and the scan reported `p+q+r` as an unparsed field. That is
        # USE-VERSUS-MENTION for the third time in one day — summit's note tail read a
        # narrated attribution as its datum, my `_FIELD` read an `=` inside a value as a
        # field boundary, and then the instrument built to catch both did it too.
        _prose = os.path.join(d, "prose.bib")
        with open(_prose, "w", encoding="utf-8") as fh:
            fh.write("@misc{W,\n  section = {s},\n"
                     "  claim = {three points, p+q+r = 0 over F2, symmetric},\n"
                     "  check = {item:T27}\n}\n")
        check("...and an `=` inside a VALUE is prose, not an unparsed field",
              roundtrip(_prose), [])

        # ⚑⚑⚑ EVERY READ MODE MUST SURVIVE THE PATH LIST, and two did not. `main` hands
        # `path` in as a LIST; `roundtrip()` and `engine_view()` each took a single path,
        # so `--roundtrip <bib>` and `--dropped <bib>` crashed with `not 'list'` on EVERY
        # input. I fixed `--roundtrip` hours ago while testing something else and never
        # asked which OTHER single-path helper the list reaches — a fix applied where it
        # was NOTICED rather than where the class LIVES, which is why `--dropped` was
        # still broken when two delegates found it independently.
        #
        # ⚑⚑ AND THE INTERVAL WAS UNKNOWN because nothing in this suite ran these modes
        # over a real corpus. summit hit the crash, wrote a private census, and told
        # nobody; the workaround that answers the question is exactly what removes the
        # pressure to report it. **A tool nobody runs is a tool whose breakage is
        # undetectable** — the `--roundtrip` circularity finding one level out.
        #
        # ⚑ SO THE CASE IS OVER THE MODE SET, not over two names. A read mode added
        # tomorrow that forgets the list is caught by this arm without an edit.
        _twofile = [_here, _sib]
        for _mode, _fn in (("entries", lambda p: entries(p)),
                           ("dropped", lambda p: dropped(p)),
                           ("edges", lambda p: edges(p)),
                           ("roundtrip", lambda p: [r for q in p for r in roundtrip(q)])):
            check(f"--{_mode} accepts the path LIST every read mode is handed",
                  _refuses(lambda: _fn(_twofile)), False)

        check("--corpus takes only operands BEFORE the next flag",
              operands_after("--corpus", _argv_probe), [_sib])
        check("...so --bib's own operand survives the scan",
              _argv_probe[_argv_probe.index("--bib") + 1], _here)
        check("...and a flag given LAST still takes its operands",
              operands_after("--corpus", ["--add", "K", "--bib", _here,
                                          "--corpus", _sib, _here]), [_sib, _here])
        check("...while an absent flag takes nothing (not everything)",
              operands_after("--corpus", ["--add", "K", _sib]), [])
        check("--addfield adds a field the entry lacks",
              "kind=x" in add_field("B", "note", "kind=x", p), True)
        check("--addfield REFUSES a field the entry already carries (that is --set)",
              _refuses(lambda: add_field("B", "claim", "x", p)), True)
        check("--addfield REFUSES an unknown key (that is --add)",
              _refuses(lambda: add_field("NOPE", "note", "x", p)), True)
        check("--addfield REFUSES an unbalanced value",
              _refuses(lambda: add_field("B", "note", "a {b", p)), True)
        # ⚑ PURE, like its two siblings — the dry run and the real run share one path.
        _b2 = open(p, encoding="utf-8").read()
        add_field("B", "note", "kind=x", p)
        check("--addfield is PURE — computing a change writes nothing",
              open(p, encoding="utf-8").read(), _b2)
        # ⚑ AND THE RESULT MUST ROUND-TRIP AND READ BACK. A widened entry that the
        # parser can no longer read is the fabrication class through the write path.
        w2 = os.path.join(d, "widened.bib")
        with open(w2, "w", encoding="utf-8") as fh:
            fh.write(add_field("B", "note", "kind=corroboration by=substrate", p))
        check("an --addfield result still round-trips", roundtrip(w2), [])
        check("and the added field reads back",
              entries(w2)["B"]["note"], "kind=corroboration by=substrate")
        check("...while the entry's existing fields survive",
              entries(w2)["B"]["claim"], entries(p)["B"]["claim"])

        # ⚑ THE CASE THE ORIGINAL FIXTURE COULD NOT EXPRESS, AND IT IS THE ONE
        # THAT MATTERS.  The suite read 30/30 with a single comment line while
        # `--set` would have ERASED ALL 533 COMMENTS of the live bib -- the whole
        # adjudication record -- because the masking shrank the text and every
        # later offset shifted.  A fixture whose comment volume does not resemble
        # the real input tests nothing about comment handling.
        c = os.path.join(d, "commented.bib")
        with open(c, "w", encoding="utf-8") as fh:
            fh.write("% a long banner line that is much wider than the entry\n"
                     "% ⚑ a second comment, also long, carrying an adjudication\n"
                     "%\n"
                     "@misc{A,\n  claim = {alpha},\n  section = {s}\n}\n")
        _new = set_field("A", "claim", "rewritten", c)
        check("--set PRESERVES comment lines verbatim",
              _new.count("% a long banner line that is much wider than the entry"),
              1)
        check("--set preserves EVERY comment, not just the first",
              _new.count("%"), 3)
        check("--set writes the value at the right offset past comments",
              "claim = {rewritten}" in _new, True)

        # ⚑ `--add` IS THE SIBLING THAT CREATES, AND ITS REFUSALS ARE THE POINT.
        # Every case below drives a real refusal or a real read-back; a case
        # asserting only "the text grew" would pass against a writer that
        # appended garbage.
        # ⚑ WRITTEN AND READ BACK, NOT INSPECTED AS A STRING.  My first cut of
        # these cases called `_parse_text`/`_roundtrip_text` -- two helpers I
        # INVENTED so the assertions could avoid touching disk.  Neither exists;
        # writing the computed text and re-reading it is both honest and a test
        # of the path `--apply` actually takes.
        def _via_disk(text, name):
            q = os.path.join(d, name)
            with open(q, "w", encoding="utf-8") as fh:
                fh.write(text)
            return q

        # ⚑ THE FIXTURE USES A WITNESS THAT REALLY EXISTS.  My first cut wrote
        # `check = {item:C}` and the gate refused it -- correctly, and the
        # refusal (a SystemExit) aborted the whole suite.  A fixture that cannot
        # satisfy a guard the tool enforces is not testing the guard, it is
        # tripping over it; the positive cases must exercise the ACCEPTING branch
        # and the negative case below still names a genuinely absent one.
        # (the witness module for these cases is written at the top of the fixture)
        _ok = {"claim": "gamma", "check": "item:T27", "section": "s"}
        _addp = _via_disk(add_entry("C", _ok, p), "added.bib")
        check("--add appends a NEW entry that reads back",
              "C" in entries(_addp), True)
        check("--add preserves the entries already there",
              sorted(entries(_addp)), ["A", "B", "C"])
        check("--add result round-trips", roundtrip(_addp), [])
        check("--add REFUSES a key that already exists",
              _refuses(lambda: add_entry("A", _ok, p)), True)
        check("--add REFUSES an entry with no claim",
              _refuses(lambda: add_entry("D", {"check": "item:D"}, p)), True)
        check("--add REFUSES an edge into a non-existent key",
              _refuses(lambda: add_entry(
                  "D", dict(_ok, **{"rests-on": "NOSUCH"}), p)), True)
        check("--add ACCEPTS an edge into an existing key",
              "rests-on" in entries(_via_disk(
                  add_entry("D", dict(_ok, **{"rests-on": "A"}), p),
                  "edged.bib"))["D"], True)
        # ⚑ THE WITNESS GATE.  `item:` naming no `def` in items.py must refuse:
        # such an entry is ordered-but-never-closable, which is worse than absent
        # because the ordering will surface it as work forever.
        check("--add REFUSES an item: witness with no def in items.py",
              _refuses(lambda: add_entry(
                  "D", {"claim": "d", "check": "item:NoSuchWitness"}, p)), True)
        # ⚑ THE KEY IS NOT THE FUNCTION NAME.  `T28-edges` resolves to
        # `def T28_EDGES(`, so checking the LITERAL key rejects every hyphenated
        # key -- most of them.  Measured: this refused `D0-kernel` on its own
        # correct, registered, mutation-tested witness.  A guard that refuses the
        # population it governs reads as strictness and is a defect.
        check("--add ACCEPTS a hyphenated key whose witness is UPPER_SNAKE",
              "T28-edges" in entries(_via_disk(
                  add_entry("T28-edges",
                            {"claim": "x", "check": "item:T28-edges"}, p),
                  "hyphen.bib")), True)
        # ⚑ AND DEFINING IS NOT REGISTERING.  `def D0_KERNEL(` existed while
        # `--items D0-kernel` still said `unknown item key(s)`, because the
        # roster is the ITEMS dict.  An entry whose witness is defined but
        # unregistered is exactly as unclosable as one with no witness at all.
        check("--add REFUSES a witness that is defined but NOT in ITEMS",
              _refuses(lambda: add_entry(
                  "E", {"claim": "e", "check": "item:_open"}, p)), True)
        check("--add is PURE — computing an entry writes nothing",
              open(p, encoding="utf-8").read(), _before)
        # ⚑ THE PAIR-SPLITTER, DRIVEN THROUGH THE CLI'S OWN PARSE.  The unit
        # under test is `main`'s argv handling, not `add_entry` -- the defect was
        # entirely in the splitter, and a case calling `add_entry` with a ready
        # dict cannot see it.  A claim carries spaces AND a trailing `[tag=N]`,
        # which is the live shape; the bracketed token must CONTINUE the claim,
        # never start a field.
        # ⚑ `--apply` IS REQUIRED, AND OMITTING IT MADE THIS CASE ASSERT THE
        # OUTCOME OF A WRITE IT NEVER REQUESTED.  The first cut ran the dry run
        # and then read the file back: `entries` correctly found nothing, and the
        # case failed while the parse it tests was provably right (the printed
        # diff showed the claim whole).  A case must request the effect it
        # asserts.
        _argv = ["--add", "F", "section=s",
                 "claim=a claim with spaces [some-tag=0]", "check=item:T27",
                 "--apply"]
        _ap = os.path.join(d, "pairs.bib")
        with open(_ap, "w", encoding="utf-8") as fh:
            fh.write(open(p, encoding="utf-8").read())
        # ⚑⚑⚑ THIS IS THE CASE THE SUITE USED TO DIE ON (⟡bibstruct-selftest-swallowed).
        # It drives a REAL write, so it reaches `edit_snapshot.guard`, which checks the
        # explicit-mutation contract against the PROCESS argv — `--selftest`, carrying
        # neither `--apply` nor `--dry-run`. The refusal is `sys.exit(2)`, and with nothing
        # trapping it the suite ended HERE while still printing an N/N. Everything below
        # this point was dead text.
        #
        # ⚑ THE FIX IS TO STATE THE INTENT, NOT TO DISARM THE GUARD. `intent="apply"` is
        # `guard`'s own documented fixture escape and it is validated, not merely truthy.
        # Unsetting `SUBSTRATE_EXPLICIT_MUTATION` for the duration would have made the case
        # pass by removing the check — the route-around this file censuses elsewhere.
        _saved, DEFAULT_ = DEFAULT, None
        try:
            globals()["DEFAULT"] = _ap
            main(_argv, intent="apply")
            _got = entries(_ap).get("F", {})
        finally:
            globals()["DEFAULT"] = _saved
        # ⚑⚑ AND THE REFUSAL ITSELF IS NOW ASSERTED, WHICH IS THE OTHER HALF. The contract
        # firing is `SUBSTRATE_EXPLICIT_MUTATION` WORKING; a suite that can only be killed
        # by it can never state that it works. Same argv, intent UNSTATED: exit 2.
        # ⚑⚑⚑ Ⓥ20 ⟡armed-conditional-measures-nothing — BOTH WORLDS NOW ASSERT SOMETHING.
        # The previous cut wrote `_rc_unstated if _armed else 2` against an expected `2`, so
        # under `SUBSTRATE_EXPLICIT_MUTATION=0` the assertion degenerated to `2 == 2` and
        # measured NOTHING while still reporting a pass. Its author flagged that honestly and
        # chose it over asserting the hatch is broken — which was the right call between those
        # two options, and both were worse than the third.
        #
        # ⚑⚑ THE THIRD OPTION IS TO ASSERT THE OTHER WORLD'S ACTUAL CONTRACT, WHICH IS NOT
        # "nothing happens". `require_explicit_mutation` under `=0` does something specific and
        # documented: it prints `RUNNING UNARMED: SUBSTRATE_EXPLICIT_MUTATION=0 downgraded this
        # REFUSAL to a warning`, returns `"advisory"`, and lets the write proceed. That is a
        # BEHAVIOUR, and its own comment says why it exists — *"an unarmed run must never be
        # mistakable for a compliant one in a log read later"*. A case can hold it to that.
        #
        # ⚑ SO EACH WORLD ASSERTS ITS OWN CONTRACT AND NEITHER BRANCH IS A TAUTOLOGY: armed,
        # the invocation is REFUSED with exit 2; unarmed, it is ANNOUNCED as unarmed. What is
        # NOT measured either way is the OTHER world — one run cannot observe both, and the
        # case says which one it was in rather than implying it covered both.
        _ap2 = os.path.join(d, "pairs2.bib")
        with open(_ap2, "w", encoding="utf-8") as fh:
            fh.write(open(p, encoding="utf-8").read())
        _armed = os.environ.get("SUBSTRATE_EXPLICIT_MUTATION") != "0"
        try:
            globals()["DEFAULT"] = _ap2
            _rc_unstated, _err_unstated = _rc(*_argv)
        finally:
            globals()["DEFAULT"] = _saved
        if _armed:
            check("⚑ ARMED: an UNSTATED mutation intent is REFUSED, not guessed "
                  "(this run did NOT measure the =0 advisory path)",
                  _rc_unstated, 2)
        else:
            # ⚑ NOT A SKIP AND NOT A TAUTOLOGY. The hatch's documented job is to be LOUD;
            # a silent downgrade is the failure mode its own author named. Asserting the
            # announcement is a real assertion about the unarmed world.
            check("⚑ UNARMED (=0): the downgrade ANNOUNCES itself — a silent bypass is the "
                  "defect (this run did NOT measure the armed refusal)",
                  "RUNNING UNARMED" in _err_unstated, True)
        # ⚑ AND THE WRITE-SIDE CONSEQUENCE, WHICH ALREADY MEASURED SOMETHING IN BOTH WORLDS
        # and still does: armed, nothing lands; unarmed, the advisory lets the write through.
        # The expectation FLIPS with the world, so neither branch is satisfied by the other's
        # answer — which is what makes this one a genuine two-world assertion rather than a
        # constant wearing a condition.
        check("...and the write follows the world: armed writes NOTHING, unarmed proceeds",
              "F" in entries(_ap2), not _armed)
        check("--add keeps a multi-word claim whole",
              _got.get("claim"), "a claim with spaces [some-tag=0]")
        check("--add does not read `[tag=N]` as a field name",
              sorted(n for n in _got if not n.startswith("_")),
              ["check", "claim", "section"])

        kinds = sorted({k for k, _s, _d in edges(p)})
        check("all three edge kinds are read", kinds,
              ["enables", "from", "rests-on"])

        # ⚑ A DANGLING EDGE IS A FINDING, and the engine hides it: its `if d in
        # bib` filter makes a mistyped dependency read as NO dependency, so the
        # item sorts as if unblocked.
        check("a dangling edge target is reported",
              orphans(p), [("enables", "B", "NOSUCH")])

        # ⚑ MENTIONS IS EVIDENCE FOR AN EDGE, and a DECLARED edge is excluded:
        # `B` already declares `from = {A}`, so reporting that as a "mention"
        # would recommend an edge that exists.
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("\n@misc{C,\n"
                     "  section = {s},\n"
                     "  claim   = {gamma, which rests on B's result},\n"
                     "  check   = {item:C}\n"
                     "}\n")
        m = mentions("B", p)
        check("a prose mention is reported", [(o, f) for o, f, _c in m],
              [("C", "claim")])
        check("a DECLARED edge is not reported as a mention",
              [o for o, _f, _c in mentions("A", p)], [])
        check("an unknown key refuses, never returns empty",
              _refuses(lambda: mentions("NOPE", p)), True)

        # a missing file REFUSES rather than reporting an empty bib as clean
        try:
            entries(os.path.join(d, "nope.bib"))
            check("a missing bib refuses", "returned", "SystemExit")
        except SystemExit:
            check("a missing bib refuses", "SystemExit", "SystemExit")

        # ⚑⚑ A TRAILING BIB PATH ON A WRITE MODE IS REFUSED, NOT SWALLOWED.  Every READ
        # mode takes `[bib]` as a trailing positional, so reaching for the same shape on
        # `--add` is the natural move — and it used to append the path to the PREVIOUS
        # field's VALUE, because the pair-loop continues a value on any `=`-free token.
        # MEASURED on a real filing: a `check` field that silently grew a filesystem
        # path, while the write itself landed in the DEFAULT bib rather than the named
        # one — a corrupted entry in the wrong file, reported as success.
        # ⚑ RENAMED FROM `_rc`, WHICH SHADOWED THE `_rc` HELPER DEFINED ABOVE. It worked
        # only because nothing called the helper after this line — a latent trip-wire that
        # ⟡bibstruct-selftest-swallowed's new refusal case (which DOES call `_rc`) would
        # have walked into had it been placed below rather than above. A name reused for a
        # different kind in one scope is the same one-spelling-two-populations shape this
        # file censuses elsewhere; spelled apart rather than left to call ordering.
        _rc_trailing = main(["--add", "K", "claim=c", "check=item:K", p])
        check("a trailing .bib on --add is REFUSED", _rc_trailing, 2)
        # ⚑ `C` IS EXPECTED HERE — an earlier case adds it to this shared temp bib.  My
        # first version of both assertions said ["A", "B"] from memory of the fixture's
        # OPENING state and went red, which is the case working: a literal population is
        # only a real assertion if you check what the fixture has become.
        check("...and the refusal writes nothing", sorted(entries(p)),
              ["A", "B", "C"])
        # ⚑ THE POSITIVE HALF, because a refusal alone would be satisfied by a mode that
        # refuses EVERYTHING.  `--bib` must actually retarget: this writes to a second
        # file and the FIRST must be untouched, which is the property the whole flag
        # exists for and the one a cross-repo filing depends on.
        p2 = os.path.join(d, "other.bib")
        with open(p2, "w", encoding="utf-8") as fh:
            fh.write("@misc{Z,\n  section = {s},\n  claim = {zeta},\n"
                     "  check = {item:Z}\n}\n")
        # ⚑ `item:T27` AND NOT `item:NEW`: `--add` verifies the witness EXISTS before it
        # writes, so an invented key makes this case die inside the tool — SystemExit,
        # which aborts the whole selftest and reports a smaller population instead of one
        # red row.  Measured while writing this case; the same shape the mdstruct
        # frontmatter case is wrapped against.
        try:
            main(["--add", "NEW", "section=s", "claim=n", "check=item:T27",
                  "--bib", p2, "--apply"], intent="apply")
        except SystemExit as exc:
            check("--bib write completes", f"SystemExit: {exc}", "no exit")
        check("--bib retargets the write", sorted(entries(p2)), ["NEW", "Z"])
        check("...and the default-side file is untouched", sorted(entries(p)),
              ["A", "B", "C"])
        # ⚑⚑ AND THE SAME FOR `--set` — the half the first version of this case MISSED,
        # and the miss SHIPPED.  `--bib` was threaded through `--add` only; `--set` went
        # on writing to DEFAULT while accepting the flag without complaint, which is
        # precisely the half-wired-flag defect `--bib` was added to fix, reproduced inside
        # the fix for it.  **One mode tested is not one capability tested** — the case
        # passed green over a broken sibling because it only ever exercised one verb.
        main(["--set", "Z", "claim", "zeta-edited", "--bib", p2, "--apply"],
             intent="apply")
        check("--bib retargets a --set too", entries(p2)["Z"]["claim"], "zeta-edited")
        check("...and --set leaves the default-side file alone",
              sorted(entries(p)), ["A", "B", "C"])

    bad = [c for c in cases if not c[1]]
    for label, _, got, want in bad:
        print(f"  FAIL {label}: got {got!r} want {want!r}")
    # ⚑ THE TYPED RECORD IS THE RUNNER'S READING; THE PROSE LINE IS THE HUMAN'S.
    # `run_selftests`' ⟡selftest-contract census keys on suites that report by the
    # `selftest: N/M` REGEX rather than by a machine-readable row, and its baseline is
    # EMPTY — zero-tolerance, so a prose-only suite is a NEW key and the gate REFUSES.
    # This suite was that key. Paid down by EMITTING, never by an exemption or a
    # baseline edit: the census may only be paid down (`run_selftests.py`'s own refusal
    # text says so), and a suite that reports its verdict in a form only a regex can
    # read is one rename away from reading SILENT.
    #
    # ⚑ BOTH LINES STAY, and that is not a regex fallback. `read_record` prefers the
    # record UNCONDITIONALLY and only falls back to the regex when no row is present,
    # so with the row emitted this suite is migrated by construction; the prose line is
    # what a human at a shell reads and costs the runner nothing.
    #
    # ⚑ `rungs` IS IMPORTED HERE, NOT AT MODULE LEVEL. It is a sibling in `scratch/`,
    # so it resolves off `sys.path[0]` when this file is run as a script — which is
    # exactly how the runner invokes it — but a module-level import would make every
    # non-selftest invocation of this tool depend on it, and `static_cases()` counts a
    # module-level sibling's `check(...)` sites as THIS suite's. `rungs` is itself a
    # 53-case suite; importing it up top would inflate this suite's static count by its
    # cases, and an inflated reach baseline is permanent (no honest run can reach it).
    try:
        import rungs as _rungs
        _rungs.emit_record(len(cases) - len(bad), len(cases),
                           key="scratch/bibstruct.py")
    except ImportError:
        # ⚑ ABSENT `rungs` IS REPORTED, NOT SWALLOWED INTO A GREEN. The prose line below
        # still prints, so the suite degrades to the legacy reading rather than to a
        # false pass — and the gate then names this suite again, which is the correct
        # next action rather than a silent regression.
        print("  ⚑ rungs unavailable — no typed record emitted (legacy prose reading)")
    print("selftest: %d/%d" % (len(cases) - len(bad), len(cases)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
