#!/usr/bin/env bash
# Ζ·hook·assert — the thin TEST that puts a pk_gate RECORD into the live gate: pass iff the
# aggregate verdict record reads pass.  The gate is a build artifact (a record); this asserts it.
set -euo pipefail
f="$1"
for c in "$1" "${TEST_SRCDIR:-}/${TEST_WORKSPACE:-}/$1" "${TEST_SRCDIR:-}/$1" "${RUNFILES_DIR:-}/$1"; do
  [ -f "$c" ] && { f="$c"; break; }
done
[ -f "$f" ] || { echo "assert_pass: record not found: $1" >&2; exit 2; }
grep -q '"verdict":"pass"' "$f" || { echo "GATE RED: $(cat "$f")" >&2; exit 1; }
echo "GATE GREEN: $(cat "$f")"
