#!/usr/bin/env python3
"""Ζ·write·atomic — the DURABLE-WRITE primitive: replace the path, never the inode's contents.

Its own module rather than a function on layout.py, because the two answer to different layers.
layout owns Δ's filesystem TOPOLOGY (which files are mutable, where a sandbox roots, which
directories are other projects) and sits in the `delta` component; this owns how ANY writer commits
bytes, and the projector needs it — an edge `project → delta` the component DAG forbids, and
rightly: a projection must not depend on the mutation machinery to write its own output.

So it sits beside bib/rhetoric in `model`, depending on nothing but the standard library.  Placed
where it is OWNED rather than where it was first needed (the boundary check named the breach; the
first draft put it on layout because that is where the caller happened to be)."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _umask() -> int:
    """Read the process umask without leaving it changed (there is no read-only syscall)."""
    u = os.umask(0)
    os.umask(u)
    return u


def write_atomic(path: Path, data: str | bytes) -> None:
    """Replace `path`'s CONTENT by replacing the PATH — write a sibling temp, then rename over it.

    Ζ·write·atomic.  `write_text` opens O_TRUNC and writes THROUGH the inode, which has two
    consequences that only diverge once a path is not the sole link to its inode:

      * a hardlinked twin sees the new bytes, because there is only one inode and the twin was
        never a copy.  A content-addressed dedup pass creates exactly this state, silently and
        legitimately: byte-identity is its PRECONDITION, so every merge is harmless when made and
        the exposure begins at the first write.  Measured on this tree: eleven files' editor
        snapshots were destroyed this way, each becoming byte-identical to the file it was
        supposed to preserve.
      * a reader concurrent with the write sees a torn file, and a crash mid-write leaves one.

    `os.replace` is atomic within a filesystem, so a reader sees either the whole old file or the
    whole new one, and the rename BREAKS the alias rather than following it — the new content
    lands on a NEW inode and every twin keeps the bytes it had.  The temp is a sibling because
    rename cannot cross filesystems, and it is cleaned up if the rename never happens.

    NOT for the mutation writers.  The grader and probe.py write THROUGH a path deliberately: the
    check under test reads that exact file, and a replace would hand it a different inode from the
    one it opened.  Their in-place write is the mechanism, not an oversight (and their sandbox is
    a fresh copytree, so no twin exists to protect)."""
    mode = "wb" if isinstance(data, bytes) else "w"
    # PRESERVE the target's permissions.  mkstemp creates at 0600 by design (it is built for secrets),
    # so a replace-based write silently NARROWS every file it touches -- measured the hard way: 35
    # files dropped from the repo's 664 to 600, and the Delta grader then failed with PermissionError
    # writing into its own sandbox COPY of one, surfacing as an empty calc artifact three layers away.
    # A new file gets the process umask, exactly as an ordinary open(path, "w") would.
    try:
        keep = os.stat(path).st_mode & 0o7777
    except FileNotFoundError:
        keep = 0o666 & ~_umask()
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, mode) as f:
            f.write(data)
        os.chmod(tmp, keep)            # before the rename, so the target is never briefly 0600
        os.replace(tmp, path)          # atomic within the filesystem; breaks any hardlink alias
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
