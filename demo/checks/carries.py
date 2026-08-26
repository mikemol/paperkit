#!/usr/bin/env python3
"""Ζ·consumer-fields·demo — paperkit consuming its OWN declared consumer field.

This project's paper.toml declares `consumer_fields = ["provenance"]`, and its warrants.bib carries a
`provenance` field on a claim.  This check PARSES the project's bib through the same owner every internal
caller uses (bib.load_bib, which binds the project's declared consumer_fields) and asserts the declared
field SURVIVED — carried verbatim, and quiet (no loud-drop) on stderr.  So paperkit is its own first
consumer of consumer_fields: the capability it documents (assets/knobs-style prose) and proves
(boundaries_bib.py) is here DEMONSTRATED end-to-end, in a project gated by //:hook.

Why this project has to exist: with NO paperkit project declaring a consumer field, the bug where a bare
`bib.parse` loud-drops a declared field is INVISIBLE from inside paperkit — it exhibits zero warnings on a
tree whose every project declares none (a vacuous pass, green under exhaustive search).  This project
supplies the missing EXERCISE, so a regression in the declared-field carry/suppress path fails a gate here.

cwd = demo/ (checks run from the project dir)."""
import io
import sys
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "paperkit"))
import bib  # noqa: E402


def main() -> int:
    demo_dir = Path(__file__).resolve().parents[1]       # the demo/ project dir (has paper.toml)
    declared = bib.load_config(demo_dir)["consumer_fields"]
    if "provenance" not in declared:
        print("demo: paper.toml must declare consumer_fields = [\"provenance\"]", file=sys.stderr)
        return 1

    # Parse the project's own bib through the OWNER (binds the declared consumer_fields), capturing stderr
    # so we can assert the declared field is carried QUIETLY (no loud-drop).
    err = io.StringIO()
    with redirect_stderr(err):
        recs = bib.load_bib(demo_dir / "warrants.bib", demo_dir)
    stderr = err.getvalue()

    carriers = [k for k, r in recs.items() if r.get("provenance")]
    if not carriers:
        print("demo: no claim carries the declared `provenance` field — the demonstration is empty",
              file=sys.stderr)
        return 1
    # the declared field must be QUIET: a loud-drop of a DECLARED field is the exact bug this demonstrates
    if "provenance" in stderr and "DROPPED" in stderr:
        print("demo: the DECLARED field `provenance` was loud-dropped — the consumer_fields carry/suppress "
              "path is broken:\n" + stderr, file=sys.stderr)
        return 1
    print(f"demo: paperkit carried its own declared consumer field `provenance` on {len(carriers)} "
          f"claim(s), quietly — the feature is demonstrated end-to-end")
    return 0


if __name__ == "__main__":
    sys.exit(main())
