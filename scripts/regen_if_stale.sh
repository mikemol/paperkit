#!/usr/bin/env bash
# Ζ·hook·regen — regenerate paperkit's DERIVED artifacts when their sources are newer.
#
# ⚑ ADOPTED, NOT INVENTED.  The shape is the ecosystem's global memory hook
# (~/.claude/projects/-home-mikemol-github-substrate/memory/regen_if_stale.sh, wired as a Stop +
# SessionStart hook): a cheap mtime GATE, a DETACHED single-instance run under `flock -n`, and
# `exit 0` always so a session is never blocked or broken by it.  Only the artifact table is
# paperkit's, because only the derivations differ.  Ownership is not claimed.
#
# ⚑ WHY THIS REPO NEEDS IT.  paperkit gates that every committed derivative matches a fresh
# regeneration (`derived-is-regenerated-not-trusted`), and the CHECKERS are excellent — each one
# prints the exact command that repairs it.  What is missing is anything that RUNS them.  So the
# loop is: edit a bib, forget one of the four regenerations, and learn about it from a red gate.
#
# Measured 2026-08-28: two claims added to paper/implications.bib changed paper's deck
# segmentation from 62 to 64 units.  `paper.md` was regenerated; `render/assets/paper-units.tsv`
# was not, because nothing said it was downstream of the same edit.  The miss surfaced as a red
# `@paperkit_render//:gate` after a full sweep — a two-hour cycle to learn what an mtime
# comparison answers in milliseconds.  A checker tells you AFTER the build; this runs BEFORE it.
#
# ⚑ IT REGENERATES, IT DOES NOT GATE.  The gate remains the authority on whether a derivative is
# fresh — this only removes the class of red that is "a regeneration nobody ran".  If a
# regeneration produces something the gate rejects, that is a real finding and the gate says so.
#
# ⚑ AND IT MUST NOT RUN DURING A SWEEP.  Writing a tracked file while `bazel test //:hook` reads
# it reds sandboxed cells with `input dependency modified during execution` — Λ·quiesce, the
# defect scripts/hook_gate_running.py exists to refuse for EDITS.  A regeneration is an edit, so
# the same check applies: if a gate is running against this tree, do nothing and let the next
# invocation catch it.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 0

# ── the gate-running check, by CWD and not by argv (hook_gate_running.py's finding: a sibling
# repo's bazel has its own cwd, and argv is the producer's account of itself while /proc/<pid>/cwd
# is what the kernel actually bound).
for pid in $(pgrep -x bazel 2>/dev/null); do
  cwd="$(readlink "/proc/$pid/cwd" 2>/dev/null)" || continue
  [ "$cwd" = "$ROOT" ] && exit 0
done

# ── the artifact table: OUT  SOURCE-GLOB  COMMAND.  Each command is the one the artifact's own
# checker prints on a drift red, so this file adds no third spelling of a derivation.
# ⚑ SC2329 (never invoked) IS A FALSE POSITIVE HERE, and shellcheck's own message says how:
# "or ignored if invoked indirectly".  Both functions are serialized into the flock subshell at
# the foot of this file via `$(declare -f newer_than regen); regen` — a string shellcheck cannot
# follow.  Deleting them on this advice would delete the script's entire body.
# shellcheck disable=SC2329
newer_than() {                       # $1 = artifact, $2… = sources; true if any source is newer
  local out="$1"; shift
  [ -f "$out" ] || return 0
  for s in "$@"; do [ -e "$s" ] && [ "$s" -nt "$out" ] && return 0; done
  return 1
}

# shellcheck disable=SC2329  # invoked indirectly via `declare -f` at the foot of this file
regen() {
  # paperkit projects: <project>/<out>.md is a projection of its bibs + rubric + the projector.
  for proj in . paper library talk config setup boundaries render report image; do
    [ -f "$proj/paper.toml" ] || continue
    out="$(python3 - "$proj" <<'PY' 2>/dev/null
import sys, tomllib, pathlib
p = pathlib.Path(sys.argv[1])
cfg = tomllib.loads((p / "paper.toml").read_text()).get("paper", {})
print(p / cfg.get("out", "paper.md"))
PY
)"
    [ -n "$out" ] || continue
    if newer_than "$out" "$proj"/*.bib "$proj/paper.toml" "$proj/rubric.tsv" paperkit/project.py; then
      python3 paperkit/project.py "$proj" >/dev/null 2>&1
    fi
  done
  # the deck segmentation manifests (render/checks/units.py --check owns the comparison)
  if newer_than render/assets/paper-units.tsv paper/*.bib paperkit/project.py paperkit/genre.py; then
    python3 paperkit/project.py --observe --genre talk paper > render/assets/paper-units.tsv 2>/dev/null
  fi
  # the generated field + knob tables
  if newer_than paper/assets/formulas.md paper/checks/gen_formulas.py; then
    python3 paper/checks/gen_formulas.py > paper/assets/formulas.md 2>/dev/null
  fi
  if newer_than assets/fields.md paperkit/bib.py paperkit/config.py checks/gen_fields.py; then
    python3 checks/gen_fields.py > assets/fields.md 2>/dev/null
  fi
  if newer_than config/assets/knobs.md paperkit/config.py config/checks/gen_knobs.py; then
    python3 config/checks/gen_knobs.py > config/assets/knobs.md 2>/dev/null
  fi
}

# ⚑ DETACHED + SINGLE-INSTANCE.  The hook returns immediately; a second trigger while one runs
# just skips (the next Stop re-gates and catches anything it missed).  Never blocks a turn, and
# `exit 0` unconditionally: a regeneration that fails is the GATE's business to report, not this
# hook's business to break a session over.
setsid flock -n "$ROOT/.regen.lock" -c "cd '$ROOT' && $(declare -f newer_than regen); regen" \
  >/dev/null 2>&1 &
exit 0
