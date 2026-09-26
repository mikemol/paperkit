#!/usr/bin/env python3
"""Ρ·report·status — the witness for rpt-status: every document the local CI gates passes its gate.

⚑ Ζ·report·records — IT READS RECORDS, IT DOES NOT RUN GATES.  The check was a shell loop,
`for d in ../paper .. ../boundaries; do gate.py --safe "$d"; done`, which (a) RE-RAN three
sibling gates inside this one check, so its footprint was every file those gates read — measured
2026-09-25 once strace reached luthen — and (b) HAND-LISTED three documents while the claim says
"every document the local CI gates".  Bazel now runs each project's `gate.py --json --safe` once as
a cached cell and stages the result; this reads those records for the //:hook set (the CI-gated
documents, derived from BUILD.bazel by gen._graded, never listed here).

Exit 0 iff every such record reports pass; 1 on any fail; 3 (cannot run) when the records are not
staged — e.g. the footprint audit tracing this on the host.
"""
import sys

import gen


def main() -> int:
    try:
        rows = [(name, gen._gate(proj, "--safe")) for name, proj in gen._graded()]
    except gen.CannotGrade as e:
        print(f"rpt-status: cannot run — {e}", file=sys.stderr)
        return 3
    bad = [name for name, g in rows if "error" in g or not g.get("pass")]
    for name, g in rows:
        print(f"  {name}: {'PASS' if name not in bad else 'FAIL — ' + str(g.get('error', 'gate failed'))}")
    if bad:
        print(f"rpt-status: {len(bad)} CI-gated document(s) do not pass: {', '.join(bad)}", file=sys.stderr)
        return 1
    print(f"rpt-status: all {len(rows)} CI-gated documents pass their gate (--safe)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
