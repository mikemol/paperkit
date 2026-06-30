#!/usr/bin/env python3
"""Ζ·mutant·eval — run a claim's check against the engine with ONE module replaced by its mutant,
and report whether the mutation FLIPS the check (makes it fail).  The Bazel-graph atom of the
def-sweep: one (claim, site) probe per action, parallel + per-site cached; pk_sens aggregates the
{flipped} records into the claim's sensitivity set.

Delivery: the staged engine is read-only at its canonical path (paperkit/…); we replace the one
mutated module in place (unlink the sandbox hardlink — never the source inode — then copy the
mutant).  The check then imports the mutated engine at the path it resolves to.  This runs as a
NORMAL action under the hermetic linux-sandbox (or the OCI sandbox), so the check's Path.resolve()
and its subprocesses cannot escape to the source tree.

Idempotency: the check spawns the projector as [sys.executable, …] (tests/_fixture.py).  This tool
MUST be invoked by an absolute interpreter path so sys.executable is populated — invoked as bare
`python3`, the sandbox interpreter leaves sys.executable='' and EVERY subprocess-spawning check
"flips" regardless of the mutation (a non-idempotent verdict that depended on the ambient env).
With sys.executable pinned, the verdict is a function of the INPUTS alone."""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--module", required=True, help="engine module path to replace, e.g. paperkit/bib.py")
    ap.add_argument("--mutant", required=True, help="the pk_mutate'd module to put in its place")
    ap.add_argument("--check", required=True, help="the check script, e.g. paper/checks/claims.py")
    ap.add_argument("--claim", required=True, help="the claim key passed to the check")
    ap.add_argument("--site", required=True, help="the def-site label, recorded in the result")
    ap.add_argument("--out", required=True, help="where to write the {claim, site, flipped} record")
    a = ap.parse_args(argv)

    module = pathlib.Path(a.module)
    module.unlink()                          # drop the read-only staged hardlink (not the source)
    shutil.copyfile(a.mutant, module)        # … and deliver the mutant at the canonical path

    flipped = subprocess.run([sys.executable, a.check, a.claim],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0

    pathlib.Path(a.out).write_text(
        json.dumps({"claim": a.claim, "site": a.site, "flipped": flipped}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
