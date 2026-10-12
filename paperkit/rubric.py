"""The rubric reader -- the ONE reader of the section-order file, in either format (paperkit:W295).

A rubric lists a project's sections in order: `key`, `title`, and an optional `scheme`.  It was a
TSV (`key<TAB>title[<TAB>scheme]`), and a TAB lost in an edit broke a commit gate twice in one day
(operator, 2026-10-06), so the file moves to JSON Lines: one object per line, no positional columns
to lose.  Both formats parse to the SAME shape -- a list of `[key, title]` or `[key, title, scheme]`
rows -- so every consumer (bib.rubric, rhetoric.schemes_from_rubric) is unchanged; the format is
chosen by the file's suffix, and TSV support is dropped last, once the fleet has moved.

    paperkit-rubric --to-jsonl FILE   convert a rubric (either format) to JSON Lines on stdout
    paperkit-rubric --keys FILE       the section keys, sorted and unique, one per line

A malformed row is REFUSED by name and line, never crashed on an index, in both formats.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

Row = list[str]

_MIN_COLS = 2
_ARGC = 2
_FIELDS = frozenset({"key", "title", "scheme"})
_USAGE = "usage: paperkit-rubric (--to-jsonl | --keys) FILE"


class _Obj:
    """A parsed JSON object as its ordered (name, value) pairs -- typed, unlike a dict of Any."""

    def __init__(self, pairs: list[tuple[str, object]]) -> None:
        self.pairs = pairs


def _refuse(path: Path, line: int, why: str) -> SystemExit:
    return SystemExit(f"paperkit-bib: {path.name}:{line}: {why}")


def _tsv_rows(path: Path) -> list[Row]:
    """Return the data rows of a TSV rubric, parsed by the csv module.

    A row is skipped when blank or comment-led; a data row must carry at least a key and a
    title, and one that does not is refused by name rather than crashing on an index.  The full
    row is returned so every consumer reads the same parse and takes the columns it owns.
    """
    rows: list[Row] = []
    with path.open(newline="") as fh:
        for n, row in enumerate(csv.reader(fh, delimiter="\t"), 1):
            if not row or not row[0].strip() or row[0].lstrip().startswith("#"):
                continue
            if len(row) < _MIN_COLS or not row[1].strip():
                why = (
                    f"rubric row '{row[0].strip()}' has no title -- a row is "
                    "`key<TAB>title[<TAB>scheme]`"
                )
                raise _refuse(path, n, why)
            rows.append([c.strip() for c in row])
    return rows


def _text(value: object) -> str:
    """Return a stripped string value, or "" for anything that is not a non-blank string."""
    return value.strip() if isinstance(value, str) else ""


def _jsonl_row(path: Path, n: int, text: str) -> Row:
    """Return one JSON Lines rubric row as `[key, title]` or `[key, title, scheme]`."""
    try:
        obj: object = json.loads(text, object_pairs_hook=_Obj)
    except json.JSONDecodeError as exc:
        raise _refuse(path, n, f"not valid JSON ({exc.msg}); comments are not allowed") from exc
    if not isinstance(obj, _Obj):
        raise _refuse(path, n, "a row is a JSON object {key, title[, scheme]}")
    names = [name for name, _ in obj.pairs]
    unknown = sorted(set(names) - _FIELDS)
    if unknown:
        raise _refuse(path, n, f"unknown field(s) {unknown} -- a row is {{key, title[, scheme]}}")
    if len(names) != len(set(names)):
        raise _refuse(path, n, "a field appears twice in one row")
    fields = dict(obj.pairs)
    key, title = _text(fields.get("key")), _text(fields.get("title"))
    if not key:
        raise _refuse(path, n, "a row needs a non-empty string `key`")
    if not title:
        raise _refuse(path, n, f"rubric row '{key}' has no title")
    if "scheme" not in fields:
        return [key, title]
    scheme = _text(fields["scheme"])
    if not scheme:
        raise _refuse(path, n, f"rubric row '{key}' has an empty `scheme`")
    return [key, title, scheme]


def _jsonl_rows(path: Path) -> list[Row]:
    """Return the rows of a JSON Lines rubric; blank lines are skipped, a duplicate key refused."""
    rows: list[Row] = []
    seen: dict[str, int] = {}
    for n, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not text.strip():
            continue
        row = _jsonl_row(path, n, text)
        if row[0] in seen:
            raise _refuse(path, n, f"duplicate key '{row[0]}' (first at line {seen[row[0]]})")
        seen[row[0]] = n
        rows.append(row)
    return rows


def rows(path: Path) -> list[Row]:
    """Return the rubric's data rows; `.jsonl` is JSON Lines, anything else is the TSV."""
    return _jsonl_rows(path) if path.suffix == ".jsonl" else _tsv_rows(path)


def to_jsonl(rubric: list[Row]) -> str:
    """Render rows as JSON Lines, keeping their order; the scheme appears only when present."""
    lines = []
    for row in rubric:
        obj = {"key": row[0], "title": row[1]}
        if len(row) > _MIN_COLS and row[2]:
            obj["scheme"] = row[2]
        lines.append(json.dumps(obj, ensure_ascii=False))
    return "".join(f"{line}\n" for line in lines)


def keys(rubric: list[Row]) -> list[str]:
    """Return the section keys, sorted and unique."""
    return sorted({row[0] for row in rubric})


def main(argv: list[str] | None = None) -> int:
    """Run paperkit-rubric: strict argv, one verb and one FILE, anything else is a usage error."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != _ARGC or args[0] not in {"--to-jsonl", "--keys"}:
        sys.stderr.write(f"{_USAGE}\n")
        return 2
    source = rows(Path(args[1]))
    if args[0] == "--to-jsonl":
        sys.stdout.write(to_jsonl(source))
    else:
        sys.stdout.write("".join(f"{key}\n" for key in keys(source)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
