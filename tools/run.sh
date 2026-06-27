#!/usr/bin/env bash
# Run a paperkit verdict from the runfiles root, so the project + engine resolve at their
# workspace paths.  Host toolchain (Phase 1): tools from the host PATH.
set -euo pipefail
mode="$1"; proj="$2"
main="${TEST_SRCDIR}/${TEST_WORKSPACE}"
# A Ζ·starlark check target lives in a GENERATED external repo, so the engine + project it
# depends on are MAIN-repo data — which land under $TEST_SRCDIR/_main, not the test's own
# workspace dir.  Detect that and cd to the main repo so relative paths (../paperkit) resolve.
[ -d "${TEST_SRCDIR}/_main/paperkit" ] && main="${TEST_SRCDIR}/_main"
cd "$main"
case "$mode" in
  gate)     exec python3 paperkit/gate.py --safe --without-K "$proj" ;;
  adequacy) exec python3 paperkit/discriminate.py --min-strength behavioral "$proj" ;;
  check)      exec python3 paperkit/gate.py --only "$3" "$proj" ;;          # the recursive leaf
  invariants) exec python3 paperkit/gate.py --invariants --safe --without-K "$proj" ;;  # the node
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac
