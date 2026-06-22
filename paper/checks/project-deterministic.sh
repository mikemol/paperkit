#!/bin/sh
# Projection is a pure function of the warrant set: the same input gives the same
# document.  Non-recursive: invokes `project`, never the gate.
set -eu
a=$(python3 ../paperkit/project.py -o - .)
b=$(python3 ../paperkit/project.py -o - .)
if [ "$a" = "$b" ]; then
  echo "project-deterministic: OK (two projections identical)"
else
  echo "project-deterministic: FAIL (projection not deterministic)" >&2
  exit 1
fi
