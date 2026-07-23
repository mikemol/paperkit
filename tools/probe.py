#!/usr/bin/env python3
"""Ζ·probe — the invalidation-probe protocol, mechanized (an INSTRUMENT, not a gate:
re-verify its number each use, [[instrument-vs-gate]]).

Measures what editing ONE file re-executes: append a semantically-null marker line, re-run
//:hook under --config=mutant, read the executed-action count, revert, and RE-SYNC the build
state.  Each step is a banked probe-hygiene rule made structural:

  1. the marker is VERIFIED present before the build runs — a silent no-match (the sed that
     missed) otherwise fakes a near-zero "win" out of pure cache hits;
  2. the count is read from bazel's own process line, never inferred;
  3. the revert is VERIFIED gone, and runs in a finally: a crashed probe never strands a
     marker in the tree;
  4. the build state is RE-SYNCED after the revert (a probe build records the marker-hash
     into MODULE.bazel.lock; reverting only the FILE leaves lock ≠ tree, which stalls the
     next pre-commit — revert the BUILD STATE, not just the file).

    python3 tools/probe.py paperkit/grade.py
    python3 tools/probe.py paperkit/coherence.py --no-resync   # skip step 4 (chained probes)
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

_LINE = re.compile(r"INFO: (\d+) processes: (.*)\.")


def _hook(label):
    """Run //:hook --config=mutant, streaming stderr live; return (rc, processes-line)."""
    print(f"probe: {label} — bazel test //:hook --config=mutant …", flush=True)
    proc = subprocess.Popen(["bazel", "test", "//:hook", "--config=mutant"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    line = ""
    for ln in proc.stderr:
        sys.stderr.write(ln)
        if _LINE.search(ln):
            line = ln.strip()
    proc.wait()
    return proc.returncode, line


def _executed(line):
    """The EXECUTED action count from bazel's process line (everything that is not a cache
    hit and not internal — the number every measured payoff in the plan is quoted in)."""
    m = _LINE.search(line or "")
    if not m:
        return None
    executed = 0
    for part in m.group(2).split(","):
        part = part.strip()
        n = int(part.split()[0])
        if "action cache hit" not in part and "internal" not in part:
            executed += n
    return executed


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", help="the tracked .py (or any text) file to null-edit")
    ap.add_argument("--no-resync", action="store_true",
                    help="skip the post-revert build-state resync (chained probes only — the LAST probe must resync)")
    a = ap.parse_args(argv)

    f = Path(a.file)
    if not f.is_file():
        print(f"probe: no such file {f}", file=sys.stderr)
        return 2
    marker = f"# PROBE-MARKER {os.urandom(4).hex()} (tools/probe.py — semantically null; auto-reverted)\n"
    orig = f.read_text()

    f.write_text(orig + marker)
    if f.read_text().count(marker) != 1:                       # rule 1: verify the edit LANDED
        f.write_text(orig)
        print("probe: marker failed to land — aborted, file restored", file=sys.stderr)
        return 1
    print(f"probe: marker verified in {f}")

    try:
        rc, line = _hook("marker build")
        n = _executed(line)
    finally:
        f.write_text(orig)                                     # rule 3: revert in a finally
        if f.read_text() != orig:
            print(f"probe: REVERT FAILED — restore {f} by hand!", file=sys.stderr)
            return 1
        print(f"probe: marker reverted from {f}")

    if rc != 0:
        print(f"probe: hook FAILED under the marker (rc={rc}) — the count below is not a clean probe", file=sys.stderr)

    if not a.no_resync:                                        # rule 4: revert the BUILD STATE too
        rc2, line2 = _hook("build-state resync")
        if rc2 != 0:
            print(f"probe: resync hook FAILED (rc={rc2})", file=sys.stderr)
            return 1

    print(f"\nprobe: {f} → EXECUTED {n if n is not None else '?'} actions")
    print(f"probe:   {line}")
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
