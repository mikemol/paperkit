"""Behavioral-boundary examples for the .bzl lint -- mikemol.gatecheck.lint_bzl (paperkit:W309).

⟨P, F, δ⟩ per the boundary practice.  The lint tool moved to mtools (a pinned dist), so mutating a
paperkit source can no longer flip the claim and the Δ grader called it INDETERMINATE: a check that
runs a tool nothing in this repo can break proves nothing about the tool.  This suite is the
targeted counter-fixture that grader asked for.  It pins both sides of the lint's contract:

  P  the build rules actually in this repository are clean (a bare interpreter, a printf-built
     JSON record or a grep-parsed JSON field has not entered a command string);
  F  each forbidden pattern, in a fixture, IS caught -- so a green on the real files is a
     measurement and not a lint that sees nothing;
  δ  the sanctioned `command -v python3` resolution differs from the bare invocation by exactly
     that resolution, and only the bare one is flagged.

    python3 paperkit/tests/boundaries_lint.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from mikemol.gatecheck import lint_bzl

from paperkit.tests._boundary import Suite

ROOT = Path(__file__).resolve().parents[2]
RULES = ("calc.bzl", "verb.bzl", "grade.bzl", "bibtex.bzl", "witness.bzl")
BARE = 'command = "python3 tools/verdict.py emit"'
BARE_C = "command = \"python3 -c 'print(1)'\""
PRINTF = 'command = "printf \'{\\"verb\\": 1}\'"'
GREP = 'command = "grep -q \\":\\"true\\" record.json"'
SANCTIONED = 'command = "\\"$(command -v python3)\\" tools/verdict.py emit"'


def _found(directory: Path, line: str) -> list[str]:
    """Return the pattern names the lint reports for a one-line .bzl fixture."""
    path = directory / "fixture.bzl"
    path.write_text(f"{line}\n", encoding="utf-8")
    return [name for _, _, name, _ in lint_bzl.findings([str(path)])]


def main() -> int:
    """Assert the lint is clean on the real rules and catches each forbidden pattern."""
    s = Suite("LINT", "Ξ·lint -- the build rules hold to the shell-string boundary")
    real = lint_bzl.findings([str(ROOT / "tools" / name) for name in RULES])
    s.check(f"the {len(RULES)} real build-rule files carry no forbidden pattern", real == [])
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        s.check("a bare `python3 script.py` is caught", _found(d, BARE) == ["bare-python3"])
        s.check("a bare `python3 -c` is caught", _found(d, BARE_C) == ["bare-python3"])
        s.check("a printf-built JSON record is caught", _found(d, PRINTF) == ["printf-json"])
        s.check("a grep-parsed JSON field is caught", _found(d, GREP) == ["grep-json"])
        s.check(
            "the sanctioned `command -v python3` resolution is NOT flagged",
            _found(d, SANCTIONED) == [],
        )
        s.section("P, F, δ minimum-delta pair")
        s.delta(
            "resolving the interpreter through `command -v` flips the verdict",
            _found(d, SANCTIONED) == [],
            _found(d, BARE) == ["bare-python3"],
            p='"$(command -v python3)" script -> sanctioned, not flagged',
            f="python3 script -> the ambient interpreter, flagged",
            d="one `command -v` resolution",
        )
    return s.finish()


if __name__ == "__main__":
    raise SystemExit(main())
