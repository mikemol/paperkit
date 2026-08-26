#!/usr/bin/env bash
# Ζ·hook·assert — the thin TEST that puts a pk_gate RECORD into the live gate: pass iff the
# aggregate verdict record reads pass.  The gate is a build artifact (a record); this asserts it.
set -euo pipefail
f="$1"
for c in "$1" "${TEST_SRCDIR:-}/${TEST_WORKSPACE:-}/$1" "${TEST_SRCDIR:-}/$1" "${RUNFILES_DIR:-}/$1"; do
  [ -f "$c" ] && { f="$c"; break; }
done
[ -f "$f" ] || { echo "assert_pass: record not found: $1" >&2; exit 2; }
# Ζ·gate·detail — a RED must NAME the claims that failed.  The aggregate record holds only
# {"verb":"gate","verdict":"fail"}, so a red test log said nothing about WHICH claim, and every
# diagnosis meant reconstructing it by hand from sibling *.verdict.json artifacts (measured: four
# red targets in one hook run, four hand reconstructions, each from file timestamps).  The
# per-claim records are staged beside the aggregate, so the reds are one scan away.
if ! grep -q '"verdict":"pass"' "$f"; then
  echo "GATE RED: $(cat "$f")" >&2
  d=$(dirname "$f")
  n=0
  for r in "$d"/*.verdict.json "$d"/*.grade.json; do
    [ -f "$r" ] || continue
    case "$r" in *"$(basename "$f")") continue;; esac      # skip the aggregate itself
    case "$r" in
      *.grade.json)
        # a GRADE record names a rung; the under-floor rungs are the reds
        grep -qE '"grade": ?"(broken|vacuous|indeterminate)"' "$r" || continue
        echo "  RED  $(basename "$r" .grade.json): $(cat "$r")" >&2 ;;
      *)
        grep -q '"verdict":"pass"' "$r" && continue
        echo "  RED  $(basename "$r" .verdict.json): $(cat "$r")" >&2 ;;
    esac
    n=$((n+1))
  done
  [ "$n" = 0 ] && echo "  (no per-claim record names a failure — the aggregate is the only signal;" \
                       "the records may not be staged as runfiles for this target)" >&2
  exit 1
fi
echo "GATE GREEN: $(cat "$f")"
