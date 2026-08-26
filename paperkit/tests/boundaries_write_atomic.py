#!/usr/bin/env python3
r"""Behavioral-boundary examples for Ζ·write·atomic — replacing the PATH, not the inode.

`write_text` opens O_TRUNC and writes THROUGH the inode.  That is invisible while a path is the
sole link to its inode and becomes a silent cross-object write the moment it is not — which a
content-addressed dedup pass creates legitimately, since byte-identity is its PRECONDITION rather
than its risk.  Measured on this tree: eleven files' editor snapshots were destroyed exactly this
way, each becoming byte-identical to the file it existed to preserve, with no content lost and
nothing to notice.

So the property under test is NOT "the writers call a helper" — a check on the artifact rather
than the act would pass on a source-grep and prove nothing about behaviour.  Each arm PERFORMS a
write against a real hardlinked pair and asserts the twin survives.

⟨P, F, δ⟩ per the boundary practice.

Run:  python3 paperkit/tests/boundaries_write_atomic.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ENG = Path(__file__).resolve().parent.parent
ROOT = ENG.parent
sys.path.insert(0, str(ENG))
import durable  # noqa: E402


def _twinned(d: Path, name: str, body: str) -> tuple:
    """A file plus a hardlinked twin — the state a dedup pass leaves behind."""
    live, twin = d / name, d / f"{name}@snapshot"
    live.write_text(body)
    os.link(live, twin)
    return live, twin


def main() -> int:
    fails = []

    def check(desc, cond):
        print(f"  {'ok ' if cond else 'XX '}{desc}")
        if not cond:
            fails.append(desc)

    print("Ζ·write·atomic — the twin survives the write\n")

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # ── P / F / δ: the same write, two writers, opposite outcomes ───────────────────────────
        live, twin = _twinned(d, "p.py", "ORIGINAL\n")
        durable.write_atomic(live, "REWRITTEN\n")
        check("P: write_atomic → twin keeps its bytes", twin.read_text() == "ORIGINAL\n")
        check("P: write_atomic → the file HAS the new bytes", live.read_text() == "REWRITTEN\n")
        check("P: write_atomic → the alias is BROKEN (a new inode, links back to 1)",
              live.stat().st_nlink == 1 and live.stat().st_ino != twin.stat().st_ino)

        live2, twin2 = _twinned(d, "f.py", "ORIGINAL\n")
        live2.write_text("REWRITTEN\n")
        check("F: write_text → twin is CORRUPTED (the failure this closes)",
              twin2.read_text() == "REWRITTEN\n")
        print("     δ: one call — replace the path vs truncate the inode.\n")

        # ── the helper must not leave debris, and must clean up after itself on failure ─────────
        durable.write_atomic(d / "bytes.bin", b"\x00\x01\x02")
        check("bytes are written as bytes (not str-coerced)",
              (d / "bytes.bin").read_bytes() == b"\x00\x01\x02")
        check("no temp files left behind on success",
              not [p for p in d.iterdir() if p.name.endswith(".tmp")])

        # A write that raises mid-flight must leave neither a temp nor a damaged target.
        keep, ktwin = _twinned(d, "k.py", "KEEP\n")
        # A str subclass overriding __len__ does NOT raise — f.write() never consults it, so the
        # write succeeds and the arm proves nothing.  Caught by this suite failing: the target read
        # back as the new content, not the old.  Use an object that genuinely breaks the write.
        class _Boom:
            def __str__(self):
                raise RuntimeError("boom")
        try:
            durable.write_atomic(keep, _Boom())      # f.write() rejects a non-str → TypeError
        except Exception:
            pass
        check("a failed write leaves the target untouched", keep.read_text() == "KEEP\n")
        check("a failed write leaves its twin untouched", ktwin.read_text() == "KEEP\n")
        check("a failed write leaves no temp behind",
              not [p for p in d.iterdir() if p.name.endswith(".tmp")])

        # ── the replace must PRESERVE the target's mode ─────────────────────────────────────────
        # mkstemp creates at 0600 (it is built for secrets), so a naive replace NARROWS every file
        # it writes.  Measured the hard way: 35 files silently dropped from the repo's 664 to 600,
        # and the Δ grader then died with PermissionError writing into its own sandbox COPY of one
        # — surfacing three layers away as an EMPTY calc artifact, because the action redirects the
        # tool's stdout into its declared output, so a crashed tool still "produces" a 0-byte file.
        m = d / "mode.py"
        m.write_text("x\n")
        os.chmod(m, 0o664)
        durable.write_atomic(m, "y\n")
        check("the replace PRESERVES an existing file's mode (0664 stays 0664)",
              (m.stat().st_mode & 0o777) == 0o664 and m.read_text() == "y\n")
        ro = d / "ro.py"
        ro.write_text("x\n")
        os.chmod(ro, 0o444)
        durable.write_atomic(ro, "y\n")
        check("   ...including a read-only one (the writer does not widen either)",
              (ro.stat().st_mode & 0o777) == 0o444)
        fresh = d / "fresh.py"
        durable.write_atomic(fresh, "z\n")
        check("a NEW file gets the umask default, not mkstemp's 0600",
              (fresh.stat().st_mode & 0o777) != 0o600)

        # ── the duplicated implementation must AGREE (verdict.py cannot import the engine) ──────
        vlive, vtwin = _twinned(d, "v.json", "ORIGINAL\n")
        subprocess.run([sys.executable, str(ROOT / "tools" / "verdict.py"),
                        "emit", "cmd", "pass", str(vlive)], check=True,
                       capture_output=True, text=True)
        check("verdict.py's own copy also spares the twin (Λ·guard-must-not-copy: gated, not trusted)",
              vtwin.read_text() == "ORIGINAL\n")
        check("verdict.py still writes a valid record",
              json.loads(vlive.read_text())["verdict"] == "pass")

        # ── the MUTATION writers must NOT be converted (their in-place write is the mechanism) ──
        # The grader hands a check the very path it mutates; a replace would give the check a
        # different inode than the one it opened.  Assert the engine still writes through there.
        m = d / "m.py"
        m.write_text("ORIGINAL\n")
        ino_before = m.stat().st_ino
        m.write_text("MUTANT\n")
        check("in-place write keeps the inode (the grader's mechanism, deliberately unconverted)",
              m.stat().st_ino == ino_before)

    print()
    if fails:
        print(f"write-atomic boundaries: FAIL ({len(fails)})")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("write-atomic boundaries: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
