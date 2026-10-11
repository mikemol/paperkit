"""Ζ·debt·idiom — group mypy's errors across files by IDIOM, so a codemod is chosen by count.

A typing-debt card says "N findings in file F"; that number names no fix.  The same few shapes
repeat across files (a missing return annotation, `Expression has type "Any"`, bare generics), and
a shape that dominates is a codemod target worth writing once.  This tool runs mypy over the named
files with the repo's own configuration and groups every error by its IDIOM: the error code plus
the message with its quoted names and numbers normalised away, so `Missing type arguments for
generic type "dict"` and `... "list"` are one idiom.

    python3 tools/mypy_idioms.py paperkit/gate.py tools/vfs.py     # idioms by count, then by file
    python3 tools/mypy_idioms.py --selftest                        # the ⟨P, F, δ⟩ arm
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

from mypy import api

ROOT = Path(__file__).resolve().parents[1]
_ERROR = re.compile(r"^(?P<file>[^:]+):\d+: error: (?P<msg>.*?)(?:\s+\[(?P<code>[\w-]+)\])?$")
_QUOTED = re.compile(r'"[^"]*"')
_NUMBER = re.compile(r"\d+")
_USAGE_EXIT = 2
# the selftest fixture below holds exactly three distinct idioms (two fold into one)
_FIXTURE_IDIOMS = 3


def idiom_of(message: str, code: str) -> str:
    """Return the idiom key: the code plus the message with names and numbers normalised."""
    shape = _NUMBER.sub("N", _QUOTED.sub('"_"', message))
    return f"[{code or 'no-code'}] {shape}"


def parse(output: str) -> list[tuple[str, str]]:
    """Return (file, idiom) for every `file:line: error:` line in mypy's output."""
    found: list[tuple[str, str]] = []
    for line in output.splitlines():
        m = _ERROR.match(line)
        if m:
            found.append((m.group("file"), idiom_of(m.group("msg"), m.group("code") or "")))
    return found


def run_mypy(files: list[str]) -> str:
    """Run mypy in-process over `files` with the repo's configuration and return its output."""
    stdout, _stderr, _status = api.run(
        [
            "--config-file",
            str(ROOT / "pyproject.toml"),
            "--follow-imports=silent",
            "--no-error-summary",
            "--no-pretty",
            *files,
        ]
    )
    return stdout


def report(found: list[tuple[str, str]]) -> str:
    """Render the idioms by count (with how many files each spans), then the files by count."""
    by_idiom = Counter(idiom for _, idiom in found)
    files_of: dict[str, set[str]] = {}
    for f, idiom in found:
        files_of.setdefault(idiom, set()).add(f)
    lines = [f"{len(found)} error(s), {len(by_idiom)} idiom(s)\n"]
    for idiom, n in by_idiom.most_common():
        lines.append(f"{n:5d}  {len(files_of[idiom]):3d} file(s)  {idiom}\n")
    lines.append("\nby file:\n")
    for f, n in Counter(f for f, _ in found).most_common():
        lines.append(f"{n:5d}  {f}\n")
    return "".join(lines)


def selftest() -> int:
    """⟨P, F, δ⟩: names and numbers fold into one idiom; a different code does not."""
    out = (
        'a.py:1: error: Missing type arguments for generic type "dict"  [type-arg]\n'
        'b.py:9: error: Missing type arguments for generic type "list"  [type-arg]\n'
        "a.py:3: error: Function is missing a return type annotation  [no-untyped-def]\n"
        'a.py:5: error: Expression has type "Any"  [misc]\n'
    )
    got = parse(out)
    p_same = got[0][1] == got[1][1]
    f_diff = got[0][1] != got[2][1] and got[2][1] != got[3][1]
    d_count = len({i for _, i in got}) == _FIXTURE_IDIOMS
    ok = p_same and f_diff and d_count
    sys.stdout.write(f"mypy_idioms selftest: {'PASS' if ok else 'FAIL'}\n")
    sys.stdout.write(f"  P (same shape, other name): folds -> {p_same}\n")
    sys.stdout.write(f"  F (other code/shape): stays apart -> {f_diff}\n")
    sys.stdout.write(f"  δ (min delta): the quoted name only -> {d_count}\n")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    """Group the named files' mypy errors by idiom; refuse an unknown flag."""
    if argv == ["--selftest"]:
        return selftest()
    flags = [a for a in argv if a.startswith("-")]
    if flags or not argv:
        sys.stderr.write(f"mypy_idioms: usage: FILE... | --selftest (got {flags or 'no files'})\n")
        return _USAGE_EXIT
    sys.stdout.write(report(parse(run_mypy(argv))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
