#!/usr/bin/env python3
"""Ξ·lint — the STATIC witness of the verdict/idempotency invariant: a .bzl run_shell command must
INVOKE tools, never embed program logic or construct/parse data in a shell string.  Fails the build
if any .bzl (passed as args) contains a forbidden pattern:

  bare-python3 : `python3 <script>.py|.sh` or `python3 -c` NOT resolved via `command -v` — the
                 ambient-interpreter dependence that left sys.executable='' and made every
                 subprocess-spawning check spuriously flip (see tools/eval.py, the idempotency bug).
  printf-json  : building a JSON record with printf — the data-construction-in-shell whose spacing
                 drifted from its grep consumer and silently passed a FAILING gate (tools/verdict.py
                 is the one owner of the {verb,verdict} format).
  grep-json    : reading a JSON field with grep (`grep … "field":`) — fragile to spacing; PARSE it.

The build-time pair of the runtime ∅-baseline witness (tools/sens.py): together they make "a verdict
is entailed by its inputs and witnesses its own validity" correct-by-construction.  Legit inline
shell stays — env exports, /sys reads, `[ -f ]`, and running an ARBITRARY command (pk_cmd's `sh -c`).
`command -v python3 …` is the sanctioned resolution and is NOT flagged."""
import re
import sys

# `python3` immediately followed by whitespace + (-c | a script path) is a BARE invocation.  The
# sanctioned `"$(command -v python3)" script.py` has `python3` followed by `)`, so it never matches.
CHECKS = [
    ("bare-python3", re.compile(r"python3\s+(-c\b|[^\s'\"]+\.(py|sh)\b)")),
    ("printf-json", re.compile(r"printf\s+['\"]\\?\{")),
    ("grep-json", re.compile(r"grep\b[^\n|;]*\\\":")),
]


def main(argv):
    bad = []
    for path in argv:
        with open(path) as f:
            for n, line in enumerate(f, 1):
                for name, rx in CHECKS:
                    if rx.search(line):
                        bad.append((path, n, name, line.strip()))
    for path, n, name, text in bad:
        sys.stderr.write("{}:{}: Ξ·lint [{}] {}\n".format(path, n, name, text))
    if bad:
        sys.stderr.write("\nΞ·lint: {} forbidden pattern(s) — lift logic/JSON into a tool "
                         "(tools/verdict.py owns the verdict record), resolve python via "
                         "`command -v`.\n".format(len(bad)))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
