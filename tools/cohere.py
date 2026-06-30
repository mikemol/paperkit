#!/usr/bin/env python3
"""Ζ·emerge·gate — the COHERENCE reading: run coherence.py over the cached calc records and emit the
verdict (pass iff grounding sound).  A cheap read — coherence.py reads the calcs, it does not
re-sweep.  Usage: cohere.py <project> <out.json> <calc.json>…

Invoke this tool by an ABSOLUTE interpreter path so sys.executable is populated: coherence.py is
spawned as [sys.executable, …] and would exec '' under a bare-`python3` invocation (see eval.py)."""
import json
import pathlib
import subprocess
import sys


def main(argv):
    project, out, calcs = argv[0], argv[1], argv[2:]
    rc = subprocess.run([sys.executable, "paperkit/coherence.py", "--from-calcs", project, *calcs],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    pathlib.Path(out).write_text(
        json.dumps({"verb": "cohere", "verdict": "pass" if rc == 0 else "fail"}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
