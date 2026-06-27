#!/usr/bin/env bash
# Run a paperkit ADEQUACY sweep (the Δ grader) from the runfiles root, so the project + engine
# resolve at their workspace paths.  This is the ONLY surviving run.sh mode: every per-claim check
# is now a per-verb RECORD action (Ζ·verb·wire), and the gate/invariants are pk_gate/pk_cmd — only
# adequacy (discriminate.py) is still an engine sh_test, until Ζ·nest makes the whole-project Δ a
# nesting of per-claim pk_grade artifacts.
set -euo pipefail
mode="$1"; proj="$2"
main="${TEST_SRCDIR}/${TEST_WORKSPACE}"
# A generated check target's deps are MAIN-repo data — under $TEST_SRCDIR/_main, not the test's own
# workspace dir.  Detect that and cd to the main repo so relative paths (../paperkit) resolve.
[ -d "${TEST_SRCDIR}/_main/paperkit" ] && main="${TEST_SRCDIR}/_main"
cd "$main"
case "$mode" in
  adequacy) exec python3 paperkit/discriminate.py --min-strength behavioral "$proj" ;;
  *) echo "run.sh: only 'adequacy' remains (Ζ·verb·wire retired check/gate/invariants); got: $mode" >&2; exit 2 ;;
esac
