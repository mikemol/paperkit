#!/usr/bin/env python3
"""lo.py — LibreOffice headless conversion with an ISOLATED, ephemeral user profile
that also REMOVES its target first, so an absence is loud rather than a stale pass.

Adopted from mat260's estate (ask-render-provenance-unlink-first, summit floor) — the
capability paperkit's six render checks each hand-wrote and none of which removed the
output first.  Where it lives in the render layer is the owner's call; it lives beside
its only consumers (render/checks/), the checks that own the office-convert idiom.

Two coupled hazards this closes:

  RACE / ISOLATION.  LibreOffice's default user profile (~/.config/libreoffice) is
  shared, process-global state.  A second soffice attaching to it — figure generation,
  a companion-PDF convert, an open GUI, a concurrent build — can make a conversion read
  cached state or silently no-op.  Each conversion runs under its OWN throwaway profile
  (-env:UserInstallation), so no two ever share mutable state.

  PROVENANCE.  Even isolated, a *failed* convert that leaves the previous output in
  place reads as success — soffice exits 0 without writing, the previous file survives,
  and the check certifies an artifact it did not rebuild.  So the target is removed
  first: if the convert does not produce it, there is simply no file — a loud absence,
  never a stale file passing for fresh.  A file at the path is then, BY CONSTRUCTION,
  the conversion of the CURRENT input.

Every render check that shells out to libreoffice should convert through here.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path


def convert(src, fmt, outdir, timeout=180):
    """Convert one file `src` to `fmt` (e.g. 'pdf', 'emf') into `outdir`, under a
    unique ephemeral profile, removing any stale target first.  Returns the output
    Path, or None if libreoffice did not produce it.
    """
    return convert_many([src], fmt, outdir, timeout)[0]


def convert_many(srcs, fmt, outdir, timeout=180):
    """Batch form: convert each of `srcs` to `fmt` in `outdir` under ONE ephemeral
    profile (one soffice startup).  Removes every target first.  Returns a list of
    output Paths aligned with `srcs`, each None if not produced.
    """
    outdir = Path(outdir)
    srcs = [Path(s) for s in srcs]
    ext = fmt.split(":")[0]
    outs = [outdir / (s.stem + "." + ext) for s in srcs]
    for o in outs:
        try:
            o.unlink()
        except FileNotFoundError:
            pass
    if srcs:
        prof = tempfile.mkdtemp(prefix="lo.")
        try:
            subprocess.run(
                ["libreoffice", "-env:UserInstallation=file://" + prof,
                 "--headless", "--convert-to", fmt, "--outdir", str(outdir)]
                + [str(s) for s in srcs],
                capture_output=True, timeout=timeout)
        finally:
            shutil.rmtree(prof, ignore_errors=True)
    return [o if o.exists() else None for o in outs]


if __name__ == "__main__":   # lo.py SRC FMT OUTDIR — convert one file
    import sys
    out = convert(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if out else 1)
