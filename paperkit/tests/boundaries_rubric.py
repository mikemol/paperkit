"""Behavioral-boundary examples for the rubric reader -- paperkit.rubric (paperkit:W295).

⟨P, F, δ⟩ per the boundary practice.  The rubric is read in TWO formats, TSV and JSON Lines, and the
point of the move is that a lost TAB can no longer break a commit gate.  So the bounds are:

  1. both formats parse to the SAME rows;
  2. every malformed JSON Lines row is REFUSED by file and line, never crashed on an index and never
     silently half-read;
  3. the converter and the key lister are strict about argv: an unknown flag is a usage error, and
     it writes nothing.

    python3 paperkit/tests/boundaries_rubric.py
"""

from __future__ import annotations

import io
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import NamedTuple

import paperkit.bib
import paperkit.rubric

TSV = "# rubric\nintro\tIntroduction\nmodel\tThe Model\tladder\n\nend\tConclusion\n"
JSONL = (
    '{"key": "intro", "title": "Introduction"}\n'
    '{"key": "model", "title": "The Model", "scheme": "ladder"}\n'
    "\n"
    '{"key": "end", "title": "Conclusion"}\n'
)
EXPECTED = [["intro", "Introduction"], ["model", "The Model", "ladder"], ["end", "Conclusion"]]
ONE = '{"key": "a", "title": "A"}\n'
TWO = ONE + '{"key": "b", "title": "B"}\n'
DUPLICATE = ONE + '{"key": "a", "title": "B"}\n'
UNKNOWN = '{"key": "a", "title": "A", "colour": "red"}\n'

Result = tuple[str, bool]


class Pair(NamedTuple):
    """One minimum-delta pair: a passing and a failing input that differ on one axis."""

    name: str
    axis: str
    pass_label: str
    pass_ok: bool
    flag_label: str
    flag_ok: bool


# (description, the offending file text, a fragment the refusal must name)
REFUSALS = [
    ("invalid JSON", '{"key": "a", "title": }\n', "not valid JSON"),
    ("a comment line (JSON Lines has none)", "# a comment\n", "comments are not allowed"),
    ("a row that is not an object", '["a", "b"]\n', "JSON object"),
    ("an unknown field", UNKNOWN, "unknown field"),
    ("a field repeated in one row", '{"key": "a", "key": "b", "title": "A"}\n', "appears twice"),
    ("a missing key", '{"title": "A"}\n', "non-empty string `key`"),
    ("a missing title", '{"key": "a"}\n', "has no title"),
    ("an empty scheme", '{"key": "a", "title": "A", "scheme": " "}\n', "empty `scheme`"),
    ("a duplicate key", DUPLICATE, "duplicate key"),
]


def _scratch(directory: Path, text: str) -> Path:
    """Write `text` as a fresh JSON Lines rubric in `directory`; return its path."""
    path = directory / "scratch.jsonl"
    path.write_text(text, encoding="utf-8")
    return path


def _refusal(directory: Path, text: str) -> str:
    """Return the message `rows` refuses `text` with, or "" when it was (wrongly) accepted."""
    try:
        paperkit.rubric.rows(_scratch(directory, text))
    except SystemExit as exc:
        return str(exc.code)
    return ""


def _run(*args: str) -> tuple[int, str]:
    """Run the CLI with `args`; return (exit code, stdout)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = paperkit.rubric.main(list(args))
    return code, out.getvalue()


def _reads(directory: Path) -> list[Result]:
    """Both formats parse to the same key/title[/scheme] rows, in file order."""
    tsv = paperkit.rubric.rows(directory / "rubric.tsv")
    jsonl = paperkit.rubric.rows(directory / "rubric.jsonl")
    return [
        ("a TSV rubric parses to rows, skipping comments and blanks", tsv == EXPECTED),
        ("a JSON Lines rubric parses to the SAME rows as the TSV", jsonl == tsv),
        (
            "the rows keep file order, and a row without a scheme has no third column",
            [row[0] for row in jsonl] == ["intro", "model", "end"] and jsonl[0] == EXPECTED[0],
        ),
    ]


def _refusals(directory: Path) -> list[Result]:
    """Each malformed JSON Lines input is refused, naming the file and the line."""
    out = []
    for desc, text, needle in REFUSALS:
        message = _refusal(directory, text)
        named = needle in message and "scratch.jsonl:" in message
        out.append((f"JSON Lines REFUSES {desc}, naming the file and line", named))
    return out


def _conversion(directory: Path) -> list[Result]:
    """Check that the converter loses nothing and the key lister sorts and de-duplicates."""
    tsv = paperkit.rubric.rows(directory / "rubric.tsv")
    again = paperkit.rubric.rows(_scratch(directory, paperkit.rubric.to_jsonl(tsv)))
    return [
        ("to_jsonl then rows is the identity (the converter loses nothing)", again == tsv),
        (
            "keys are sorted and unique",
            paperkit.rubric.keys([["b", "B"], ["a", "A"], ["b", "B2"]]) == ["a", "b"],
        ),
    ]


def _bib(directory: Path) -> list[Result]:
    """Check that bib delegates to the reader and picks the default rubric file by what exists."""
    project = directory / "proj"
    project.mkdir()
    before = paperkit.bib.rubric_path(project, None)
    (project / "rubric.jsonl").write_text(JSONL, encoding="utf-8")
    after = paperkit.bib.rubric_path(project, None)
    tsv, jsonl = directory / "rubric.tsv", directory / "rubric.jsonl"
    return [
        (
            "bib.rubric_rows delegates to the reader (both formats agree)",
            paperkit.bib.rubric_rows(jsonl) == paperkit.bib.rubric_rows(tsv),
        ),
        (
            "bib.rubric returns (key, title) pairs from a JSON Lines file",
            paperkit.bib.rubric(jsonl)[1] == ("model", "The Model"),
        ),
        (
            "the default rubric is rubric.tsv when no rubric.jsonl exists",
            before == project / "rubric.tsv",
        ),
        (
            "the default rubric becomes rubric.jsonl once it exists",
            after == project / "rubric.jsonl",
        ),
        (
            "a declared [paper] rubric always wins over the default",
            paperkit.bib.rubric_path(project, "x.tsv") == project / "x.tsv",
        ),
    ]


def _cli(directory: Path) -> list[Result]:
    """Check that the CLI prints what it promises and refuses anything else, writing nothing."""
    code_keys, out_keys = _run("--keys", str(directory / "rubric.jsonl"))
    code_conv, out_conv = _run("--to-jsonl", str(directory / "rubric.tsv"))
    tsv = paperkit.rubric.rows(directory / "rubric.tsv")
    before = sorted(path.name for path in directory.iterdir())
    usage = [_run("--help")[0], _run("--bogus", "x")[0], _run()[0], _run("--keys")[0]]
    return [
        (
            "--keys prints the sorted keys, one per line",
            (code_keys, out_keys) == (0, "end\nintro\nmodel\n"),
        ),
        (
            "--to-jsonl prints JSON Lines that read back as the same rows",
            code_conv == 0 and paperkit.rubric.rows(_scratch(directory, out_conv)) == tsv,
        ),
        (
            "an unknown flag or the wrong arity is a usage error (rc 2) and writes nothing",
            set(usage) == {2} and sorted(path.name for path in directory.iterdir()) == before,
        ),
    ]


def _pairs(directory: Path) -> list[Pair]:
    """Return the minimum-delta pairs: one passing and one failing input per axis."""
    return [
        Pair(
            "a row survives iff it names only the three rubric fields",
            "the field's name (title vs colour)",
            "{key, title} -> read",
            paperkit.rubric.rows(_scratch(directory, ONE)) == [["a", "A"]],
            "{key, title, colour} -> refused",
            "unknown field" in _refusal(directory, UNKNOWN),
        ),
        Pair(
            "a key survives iff it is unique in the file",
            "whether the second key repeats the first",
            "a then b -> read",
            len(paperkit.rubric.rows(_scratch(directory, TWO))) == len(TWO.splitlines()),
            "a then a -> refused",
            "duplicate key" in _refusal(directory, DUPLICATE),
        ),
    ]


def main() -> int:
    """Run every behavior and pair; write one line each and an OK/FAIL summary."""
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        (directory / "rubric.tsv").write_text(TSV, encoding="utf-8")
        (directory / "rubric.jsonl").write_text(JSONL, encoding="utf-8")
        sys.stdout.write("rubric reader behaviors\n\n")
        results = (
            _reads(directory)
            + _refusals(directory)
            + _conversion(directory)
            + _bib(directory)
            + _cli(directory)
        )
        for desc, ok in results:
            sys.stdout.write(f"  {'ok ' if ok else 'XX '}{desc}\n")
        sys.stdout.write("\n⟨P, F, δ⟩ minimum-delta pairs\n\n")
        pairs = _pairs(directory)
    for pair in pairs:
        ok = pair.pass_ok and pair.flag_ok
        results.append((pair.name, ok))
        sys.stdout.write(f"  {'ok ' if ok else 'XX '}{pair.name}\n")
        sys.stdout.write(f"      P (pass side): {pair.pass_label}\n")
        sys.stdout.write(f"      F (flag side): {pair.flag_label}\n")
        sys.stdout.write(f"      δ (min delta): {pair.axis}\n\n")
    failed = [desc for desc, ok in results if not ok]
    if failed:
        sys.stdout.write(f"rubric boundaries: FAIL ({len(failed)} of {len(results)} drifted)\n")
        sys.stdout.write("".join(f"  - {desc}\n" for desc in failed))
        return 1
    sys.stdout.write(f"rubric boundaries: OK ({len(results)} behaviors)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
