#!/bin/sh
# The committed prose IS the projection (no hand-edit has drifted it).
# Non-recursive: invokes `project --check`, never the gate.
exec python3 ../paperkit/project.py --check .
