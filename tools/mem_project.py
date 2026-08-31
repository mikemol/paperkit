#!/usr/bin/env python3
"""Τ·mem·project — project mem.sqlite → mem.json, the Starlark-readable build input.

Ζ·mem·wire — WHY TWO ARTIFACTS.  The store keeps one row per observation so a bucket can say what
it rests on; the generator in tools/bibtex.bzl reads a repo-rule input at FETCH time and only ever
wants the number.  Measured before splitting them: a new cell changes the DB's bytes but not the
manifest it projects to, and one sweep deposits ~163 observations — so `repository_ctx.watch` on
the DB would re-fetch the rule 163 times to regenerate a BUILD file whose content never moved
(paper's is 52,584 pk_eval targets).  Watching the projection invalidates exactly when a
RESERVATION changes.

GENERATED, never authored (project-dont-author): mem.json is derived state, and the freshness
check is `--check` — regenerate and byte-compare, so a drifted projection is named rather than
silently trusted.

    mem_project.py <db> <project> <out.json>     write the projection
    mem_project.py <db> <project> <out.json> --check   exit 1 if it would change
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mem_db as D


def render(db: Path, project: str) -> str:
    c = D.connect(db)
    m = D.manifest(c, project)
    if not m.get("claims") and len(m) == 1:
        return ""                                  # no observations: emit nothing, not a false {}
    return json.dumps(m, indent=2, sort_keys=True) + "\n"


def main(argv: list) -> int:
    if len(argv) < 3:
        print("usage: mem_project.py <db> <project> <out.json> [--check]", file=sys.stderr)
        return 2
    db, project, out = Path(argv[0]), argv[1], Path(argv[2])
    text = render(db, project)
    if not text:
        print(f"mem-project: {project}: no observations in {db} — leaving {out} alone",
              file=sys.stderr)
        return 0
    if "--check" in argv:
        cur = out.read_text() if out.exists() else ""
        if cur != text:
            print(f"mem-project: {out} is STALE against {db} — regenerate with:\n"
                  f"  python3 tools/mem_project.py {db} {project} {out}", file=sys.stderr)
            return 1
        return 0
    out.write_text(text)
    print(f"mem-project: {project} → {out} "
          f"({ {k: v for k, v in json.loads(text).items() if k != 'claims'} })", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
