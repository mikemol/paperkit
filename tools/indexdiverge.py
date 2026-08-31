r"""Ζ·hook·index — the PURE predicate: which paths make worktree ≠ index.

Extracted from `tools/hook_index.py`, which keeps the hook layer (the live `git status`, the
refusal, the self-proof).  This is the part with no I/O and no environment: given a
`git status --porcelain=v1 -z` transcript, decide which paths diverge.

⚑ THE SPLIT IS THE GATE'S OWN PRESCRIPTION.  `hook_index.py` carries 47 lint findings and the
per-file gate has no partial-credit path, so the boundary suite that imports `divergent` could
not be edited at all — the declared dependency's debt blocks the DECLARER.  Rather than pay down
a monolith to move one function, the concern moves to a module written clean in one pass.

⚑⚑ AND THE SEPARATION IS REAL, NOT A LINT DODGE.  `divergent` is a total function from a string
to a sorted list; everything around it in `hook_index` spawns git, reads the environment, and
prints refusals.  The boundary suite exercises exactly this half over porcelain FIXTURES — which
is why it can be gated in the hermetic sandbox at all, where the other half cannot run (no git).
"""
from __future__ import annotations

# Each entry is a path PREFIX, and each earns its place by OWNERSHIP: bazel-invisible (zero
# references in any BUILD/bib/bzl) AND index-gated by its own check (cotype-monotone).
ALLOW = ("cotype/",)

_MIN_ENTRY = 4          # "XY path" — two status columns, a space, at least one path character


def divergent(porcelain: str, allow: tuple[str, ...] = ALLOW) -> list[str]:
    """Return the paths where worktree ≠ index (unstaged edits, `??` untracked), outside `allow`.

    Parsed from `git status --porcelain=v1 -z` output: NUL-separated, and a rename entry carries
    a SECOND NUL-terminated origin path which is consumed and ignored — the NEW path is what a
    commit lands, so it is the one that can diverge.
    """
    out: list[str] = []
    fields = porcelain.split("\0")
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < _MIN_ENTRY:
            continue
        xy, path = entry[:2], entry[3:]
        if xy[0] in "RC":
            i += 1                                   # the rename/copy origin path field
        dirty = xy == "??" or xy[1] != " "           # untracked, or the worktree column is live
        if dirty and not any(path.startswith(a) for a in allow):
            out.append(path)
    return sorted(out)
