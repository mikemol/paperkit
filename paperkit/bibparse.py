#!/usr/bin/env python3
"""Ζ·bib·parser — a REAL parser for paperkit's bibliography format.

⚑ WHY THIS EXISTS, AND WHY A SCANNER WAS NOT ENOUGH.  `bib.parse` read entries with a regex
(`@\\w+\\{...(.*?)\\n\\}`), which TRUNCATED an entry at the first line-initial `}`: an entry whose
value held a brace at column 0 parsed with ZERO FIELDS while a reader reported `2 of 2 entries`.
A claim with no `check` is excluded from gate.py's `warrants` set, so the defect DISARMED a claim
while the gate stayed green.  Replacing the regex with brace-counting fixed that — and then had
no answer for the next question, because a scanner has no grammar to answer from:

    a `claim` value whose brace never closes swallows the fields after it.  Is that
    (a) an entry with a long claim and no check, (b) an entry to skip, or (c) an error?

I tried (b) and (a) by patching the scanner.  (b) traded a caught defect for a silent one — the
gate simply saw one fewer claim and passed.  (a) was measured wrong: `_scalar_value` finds the
swallowed `check` INSIDE the runaway claim's text, so the gate saw a claim with prose and a
passing check and had nothing to refuse.  Both attempts were deciding SEMANTICS by editing a
scanner, which is how the old regex's truncation came to be load-bearing in the first place —
`boundaries_grounding` pins the gate's bare-KEY refusal against an ACCIDENT of that truncation.

A parser answers (c) by construction: a value that never closes is a SYNTAX ERROR AT A POSITION.
Not a swallowed field, not a silent skip, not an accident a downstream check happens to trip.

⚑ THE GRAMMAR IS THE CORPUS'S, NOT BIBTEX'S.  Censused across all 28 bibs before writing a line
(scratchpad/grammar_census.py).  ABSENT from the entire corpus: `@string`, `@preamble`,
`@comment`, paren-delimited entries `@misc(...)`, `#` concatenation, and — measured by
brace-counting, not by regex — any value spanning a newline.  Present: brace values (all of
them), nested braces (6), LaTeX-escaped braces (4), trailing commas (34), one `@` inside a value
(`cmd:grep -q "python@sha256:"`).  Every apparent quoted/bare value was a false positive: an `=`
inside prose (`P <= P_sigma`, `"refinement operator"`).

So the language is small and the parser refuses everything outside it BY NAME rather than
mis-parsing it.  Supporting `@string` on the grounds that BibTeX has it would be inheriting an
assumption; refusing it with a message that says "no bib in this corpus uses it" is a decision.

⚑ THE `%` COMMENT IS PAPERKIT'S, NOT BIBTEX'S, and it is stripped by the LEXER — before any
entry is seen.  Real BibTeX has no comment syntax; text between entries is simply ignored, which
is why a bare `@` in that text starts an entry and a conforming parser then demands a brace
(measured: pybtex refuses the root warrants.bib over one `[@key]` in a comment, while
bibtexparser accepts it — only the second oracle found it).  Ζ·bib·strict.
"""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as _dcfield


class BibSyntaxError(SyntaxError):
    """A parse failure that NAMES ITS POSITION.

    ⚑ A SyntaxError subclass on purpose: a malformed bib is a broken FILE, and the engine's own
    doctrine is that a cannot-parse must not be reported as a result.  Callers that want the old
    permissive behaviour must ask for it explicitly rather than getting it by accident.
    """

    def __init__(self, msg: str, path, line: int, col: int, excerpt: str = ""):
        self.path, self.lineno, self.offset = str(path), line, col
        detail = f"{path}:{line}:{col}: {msg}"
        if excerpt:
            detail += f"\n    {excerpt.strip()[:100]}"
        super().__init__(detail)


@dataclass
class Entry:
    """One parsed entry: its type, key, fields, and where it started."""

    typ: str
    key: str
    fields: dict = _dcfield(default_factory=dict)
    line: int = 0

    # Field ORDER is preserved (dicts are ordered): the projector renders in the file's order,
    # and a parser that returned an unordered mapping would make the projection depend on hash
    # seeding — the reproducibility this engine gates for.


class _Lexer:
    """Position-tracking character reader.  Owns line/col so every error can name its place."""

    def __init__(self, text: str, path="<bib>"):
        self.t, self.path, self.i = text, path, 0
        self.line, self.col = 1, 1

    def eof(self) -> bool:
        return self.i >= len(self.t)

    def peek(self) -> str:
        return self.t[self.i] if self.i < len(self.t) else ""

    def next(self) -> str:
        c = self.t[self.i]
        self.i += 1
        if c == "\n":
            self.line, self.col = self.line + 1, 1
        else:
            self.col += 1
        return c

    def err(self, msg: str) -> BibSyntaxError:
        nl = self.t.rfind("\n", 0, self.i) + 1
        end = self.t.find("\n", self.i)
        return BibSyntaxError(msg, self.path, self.line, self.col,
                              self.t[nl:end if end >= 0 else len(self.t)])

    def skip_trivia(self) -> None:
        """Whitespace and `%` comments — the only things allowed between entries.

        ⚑ A `%` comment is consumed HERE, in the lexer, so the entry grammar never sees one.
        That is what makes `% … [@key] …` harmless to THIS parser while a conforming BibTeX
        parser refuses it: the comment is paperkit's extension, and the lexer is where an
        extension belongs.
        """
        while not self.eof():
            c = self.peek()
            if c in " \t\r\n":
                self.next()
            elif c == "%":
                while not self.eof() and self.peek() != "\n":
                    self.next()
            else:
                return

    def escaped(self) -> bool:
        """True if the char at `i` is preceded by an ODD run of backslashes (LaTeX-escaped)."""
        n, j = 0, self.i - 1
        while j >= 0 and self.t[j] == "\\":
            n += 1
            j -= 1
        return n % 2 == 1


def _name(lx: _Lexer, what: str) -> str:
    """An identifier: entry type, key, or field name."""
    start = lx.i
    while not lx.eof() and (lx.peek().isalnum() or lx.peek() in "-_.:/+"):
        lx.next()
    if lx.i == start:
        raise lx.err(f"expected {what}")
    return lx.t[start:lx.i]


def _brace_value(lx: _Lexer) -> str:
    """A `{…}` value, brace-counted, LaTeX-escapes skipped.

    ⚑ THIS IS WHERE THE RUNAWAY CASE IS DECIDED.  If the braces never balance we reach EOF, and
    that is a syntax error naming the line the value OPENED on — not a value that silently
    swallowed every field after it.  The old regex ended such a value at the next line-initial
    `}`, which produced a mangled record the gate happened to refuse; the honest report is that
    the file is broken and where.
    """
    open_line, open_col = lx.line, lx.col
    assert lx.next() == "{"
    depth, start = 1, lx.i
    while not lx.eof():
        c = lx.peek()
        if c in "{}" and not lx.escaped():
            if c == "{":
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    v = lx.t[start:lx.i]
                    lx.next()
                    return v
        lx.next()
    raise BibSyntaxError(
        "unterminated value — the `{` opened here is never closed, so every field after it is "
        "swallowed into this one", lx.path, open_line, open_col)


def _entry(lx: _Lexer) -> Entry:
    assert lx.next() == "@"
    line = lx.line
    typ = _name(lx, "an entry type after `@`")
    lx.skip_trivia()
    if lx.peek() == "(":
        raise lx.err("paren-delimited entries `@type(...)` are not supported — no bib in this "
                     "corpus uses one; write `@%s{...}` instead" % typ)
    if lx.peek() != "{":
        raise lx.err(f"expected `{{` after `@{typ}`")
    lx.next()
    lx.skip_trivia()
    low = typ.lower()
    if low in ("string", "preamble", "comment"):
        raise lx.err(f"`@{low}` is not supported — no bib in this corpus uses one, and "
                     "supporting it silently would inherit a BibTeX feature paperkit has never "
                     "needed; remove it or state the case for it")
    key = _name(lx, "an entry key")
    lx.skip_trivia()
    if lx.peek() != ",":
        raise lx.err(f"expected `,` after the key `{key}`")
    lx.next()

    e = Entry(typ=low, key=key, line=line)
    while True:
        lx.skip_trivia()
        if lx.eof():
            raise BibSyntaxError(f"unterminated entry `{key}` — no closing `}}`",
                                 lx.path, line, 1)
        if lx.peek() == "}":
            lx.next()
            return e
        fline, fcol = lx.line, lx.col
        fname = _name(lx, f"a field name in `{key}`")
        lx.skip_trivia()
        if lx.peek() != "=":
            raise lx.err(f"expected `=` after field `{fname}` in `{key}`")
        lx.next()
        lx.skip_trivia()
        if lx.peek() != "{":
            raise lx.err(
                f"field `{fname}` in `{key}` must have a `{{…}}` value — quoted, bare and "
                "concatenated values are not supported (no bib in this corpus uses one)")
        val = _brace_value(lx)
        if fname in e.fields:
            raise BibSyntaxError(
                f"field `{fname}` is given twice in `{key}` — the second would silently replace "
                "the first", lx.path, fline, fcol)
        # ⚑ THE VALUE IS CARRIED VERBATIM — no whitespace normalisation.  A first cut did
        # `" ".join(val.split())`, which strips trailing space, and `join = {. }` MEANS the
        # trailing space: it is the connector rendered between two clauses.  Normalising would
        # have silently rewritten every projection in the corpus.  Measured against the
        # incumbent across all 28 bibs — this was the only class of divergence, and it was mine.
        e.fields[fname] = val
        lx.skip_trivia()
        if lx.peek() == ",":
            lx.next()          # trailing comma before `}` is fine (34 in the corpus)
        elif lx.peek() != "}":
            raise lx.err(f"expected `,` or `}}` after field `{fname}` in `{key}`")


def parse(text: str, path="<bib>") -> list:
    """Every entry in `text`, in file order.  Raises BibSyntaxError on any malformed input."""
    lx = _Lexer(text, path)
    out = []
    while True:
        lx.skip_trivia()
        if lx.eof():
            return out
        if lx.peek() != "@":
            raise lx.err("expected `@` to start an entry — text between entries must be a `%` "
                         "comment (paperkit's extension) or whitespace; a bare `@` in prose "
                         "starts an entry for a conforming BibTeX parser (Ζ·bib·strict)")
        out.append(_entry(lx))
