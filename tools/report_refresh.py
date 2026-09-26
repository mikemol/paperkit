#!/usr/bin/env python3
"""Ζ·report·records — regenerate report/'s committed assets FROM THE BAZEL-BUILT RECORDS.

The report's tables are rendered from each project's run-once gate and Δ records (pk_json targets
the bib extension emits, `rec_gate` / `rec_gate_safe` / `rec_delta__<project>`).  The in-cell
`fresh:` checks compare the committed assets against those records, so the assets must be made
from the SAME records — never from a live host run, which measures a different environment (the
first host refresh after the records existed read boundaries, render and talk as FAIL while
//:hook was green in the executors).

    python3 tools/report_refresh.py

1. asks Bazel which records the report's claims consume (`labels(consumes, @paperkit_report//:all)`
   — the set the extension expanded from the roster, so nothing is listed here);
2. builds them (--config=remote, the only execution this repository trusts);
3. resolves their output files (cquery --output=files);
4. runs report/gen.py's refresh with PAPERKIT_CONSUMED_RECORDS naming them.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAZEL = os.environ.get("BAZEL", "bazel")


def _run(*cmd) -> str:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        raise SystemExit(f"report_refresh: `{' '.join(cmd[:3])} …` exited {r.returncode}")
    return r.stdout


def _key(path: str) -> str:
    """The SAME key tools/verb.bzl `_consume_key` exports for a record from another repo:
    `<repo apparent name>/<basename minus .verdict.json>`, e.g. `paperkit_paper/gate_rec`."""
    parts = Path(path).parts
    repo = parts[parts.index("external") + 1].split("+")[-1]
    base = Path(path).name
    return f"{repo}/{base[:-len('.verdict.json')] if base.endswith('.verdict.json') else base}"


def main() -> int:
    labels = sorted(l for l in _run(BAZEL, "query", "labels(consumes, @paperkit_report//:all)",
                                    "--output=label").split() if l.startswith("@"))
    if not labels:
        print("report_refresh: the report consumes no records — nothing to build", file=sys.stderr)
        return 2
    print(f"report_refresh: building {len(labels)} records", file=sys.stderr)
    _run(BAZEL, "build", "--config=remote", *labels)
    files = [f for f in _run(BAZEL, "cquery", "--config=remote", "--output=files",
                             " + ".join(labels)).split()                 # ONE query expression
             if f.endswith((".json", ".rc"))]
    env = dict(os.environ)
    env["PAPERKIT_CONSUMED_RECORDS"] = " ".join(f"{_key(f)}={ROOT / f}" for f in files)
    return subprocess.run([sys.executable, "report/gen.py"], cwd=ROOT, env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
