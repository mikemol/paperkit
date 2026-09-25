#!/bin/sh
# Ρ·render·format — the consumer-facing shim.  The selector lives in checks/route.py (a python
# check has a def-site surface the mutation sweep can grade; this script had none — 2026-09-21).
#   PAPERKIT_FORMAT=latex sh checks/render.sh   # build the paper's PDF via the chosen route
exec python3 "$(dirname "$0")/route.py" "$@"
