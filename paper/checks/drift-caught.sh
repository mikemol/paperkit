#!/bin/sh
# The gate REJECTS prose that has drifted from its projection.  Runs on a throwaway
# COPY of a minimal fixture (never the live paper, and the fixture's own checks are
# trivial), so gating it does not recurse.  Exit 0 iff the gate correctly fails.
set -eu
tmp=$(mktemp -d)
cp -R checks/fixture/. "$tmp/"
printf '\nHAND-EDITED DRIFT — not in the warrant set\n' >> "$tmp/paper.md"
if python3 ../paperkit/gate.py "$tmp" >/dev/null 2>&1; then
  echo "drift-caught: FAIL — gate ACCEPTED drifted prose" >&2
  rm -rf "$tmp"; exit 1
fi
rm -rf "$tmp"
echo "drift-caught: OK — gate rejected drifted prose"
