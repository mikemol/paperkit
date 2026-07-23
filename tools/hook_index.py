#!/usr/bin/env python3
"""Ζ·hook·index — the worktree≡index precondition that makes the hook's verdict THE commit's.

The bazel hook gates the WORKING TREE; a commit lands the INDEX, and the two diverge exactly
on a partial stage (an unstaged fix → a green hook blesses a red commit) or an untracked file
a staged BUILD/bib references (green locally, analysis-error on every fresh clone — the build
graph carries NO globs, so this is the whole untracked hole).  Materializing the index
(the downstream consumer's A50 pattern) is right for their 2-second CLI gates and DEAD here:
a second workspace costs bazel's cold output base, and the hook's entire value is warm-cache
locality.  The construct instead: verify the equivalence PRECONDITION — if worktree == index
on every non-allowlisted path, the worktree verdict IS the index verdict by substitution.

Refusal is instant (one `git status --porcelain=v1 -z` parse, BEFORE any build cost), NAMES
the divergent paths, and states both remedies.  PK_HOOK_ALLOW_DIRTY=1 downgrades refusal to a
loud advisory (the declared-residue mode for a deliberate split commit).  The allowlist is
OWNERSHIP-justified, never convenience: an entry qualifies only if it is bazel-invisible AND
carries its own index-native gate (cotype/ → cotype-monotone runs on `git show :` right below
in the same hook).  Honest bound: `git commit --no-verify` skips this, as it skips all local CI.

Every run self-proves on in-memory fixtures: a synthetic dirty line must refuse, a synthetic
allowlisted line must pass — a gate that cannot refuse is theater.

    python3 tools/hook_index.py        # exit 0 = worktree ≡ index (outside the allowlist)
"""
import os
import subprocess
import sys

# Each entry is a path PREFIX, and each earns its place by OWNERSHIP: bazel-invisible (zero
# references in any BUILD/bib/bzl) AND index-gated by its own check (cotype-monotone).
ALLOW = ("cotype/",)


def divergent(porcelain, allow=ALLOW):
    """The paths where worktree ≠ index (unstaged edits, `??` untracked), outside `allow` —
    parsed from `git status --porcelain=v1 -z` output (NUL-separated; a rename entry carries
    a second NUL-terminated origin path, consumed and ignored — the NEW path is what lands)."""
    out = []
    fields = porcelain.split("\0")
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        xy, path = entry[:2], entry[3:]
        if xy[0] in "RC":
            i += 1                                   # the rename/copy origin path field
        dirty = xy == "??" or xy[1] != " "           # untracked, or the worktree column is live
        if dirty and not any(path.startswith(a) for a in allow):
            out.append(path)
    return sorted(out)


def main():
    # Self-proof (in-memory, never the tree): the gate must refuse a dirty line and pass an
    # allowlisted one, every run — else it is unsound and refuses to bless anything.
    if divergent(" M paperkit/gate.py\0?? newfile.py\0") != ["newfile.py", "paperkit/gate.py"] \
            or divergent(" M cotype/ledger.md\0"):
        print("hook-index: SELF-PROOF FAIL — the divergence parser is unsound; refusing.", file=sys.stderr)
        return 1

    r = subprocess.run(["git", "status", "--porcelain=v1", "-z"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"hook-index: git status failed — {r.stderr.strip()}", file=sys.stderr)
        return 1
    bad = divergent(r.stdout)
    if not bad:
        print("hook-index: worktree ≡ index (outside cotype/) — the hook's verdict is the commit's")
        return 0
    mode_warn = os.environ.get("PK_HOOK_ALLOW_DIRTY") == "1"
    print(("hook-index: ADVISORY — " if mode_warn else "hook-index: REFUSED — ")
          + "worktree ≠ index; the bazel hook would gate bytes this commit does not land:",
          file=sys.stderr)
    for p in bad:
        print(f"  {p}", file=sys.stderr)
    if not mode_warn:
        print("  stage it (git add <path>) or drop it (git checkout -- <path>); "
              "PK_HOOK_ALLOW_DIRTY=1 downgrades this refusal to an advisory.", file=sys.stderr)
    return 0 if mode_warn else 1


if __name__ == "__main__":
    raise SystemExit(main())
