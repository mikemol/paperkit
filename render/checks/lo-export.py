#!/usr/bin/env python3
r"""Ρ·render·lo-export — docx → tagged PDF/UA-1, driven over the office scripting bridge.

Vendored from sre-troubleshooting's lo-export.py (summit floor, ask-adopt-pdfua-render-workarounds)
— the authoritative method, preserved before that tree is retired.  The office suite's command-line
`--convert-to pdf` cannot produce a conformant deliverable two ways:

  - it exports a PLAIN PDF, not a PDF/UA one — no `pdfuaid` identification schema, no
    DisplayDocTitle, no tag structure the standard requires;
  - pandoc writes a table of contents as a Writer index FIELD, and headless conversion never
    populates it, so the heading ships with nothing under it.

Driving the export over UNO instead fixes both: `storeToURL` with a `writer_pdf_Export` filter and
`FilterData` of `PDFUACompliance=True, UseTaggedPDF=True, ExportBookmarks=True` writes a tagged
PDF/UA file with the identification metadata LibreOffice owns, and `doc.refresh()` + each index's
`.update()` (before AND after — an index has no pages to cite until the layout exists) populates the
TOC.  The document title carried in the docx core properties (pandoc `--metadata title=…`)
propagates into the PDF's `dc:title` through this export — so the title, the pdfuaid schema and
DisplayDocTitle all come from the RIGHT layer (the export), not a post-hoc stamp.

sre's first attempt drove the refresh through a Basic macro over `macro:///` and hung the build with
no output — the process stayed resident and the build blocked.  This carries the fix forward: the
office process is owned explicitly — started on a PRIVATE PIPE, waited for under a deadline, used,
terminated, and KILLED if it will not leave.  A build step that can hang forever is worse than one
that fails, so every step has a deadline.

Interpreter note (measured on this host): `import uno` is available under the SYSTEM python
(`/usr/bin/python3`), not the interpreter the checks run under — no bundled LibreOffice python binary
exists.  So the UNO driver runs as a subprocess of a uno-capable python; this check resolves one at
runtime and SKIPS LOUD (never skip-green) if none is found.

    python3 checks/lo-export.py SRC.docx OUT.pdf [--timeout 900]   # tagged-PDF/UA export
    python3 checks/lo-export.py --selftest                         # ⟨P,F,δ⟩

`export_pdfua(src, out, timeout=900) -> Path|None` is the API; None means no uno-capable python, or
the bridge was killed at the deadline — a loud absence, never a stale pass.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_LO = "/usr/lib/libreoffice/program"

# The driver, run under a uno-capable python (sre's lo-export.py, adapted to take a private-pipe
# name and a deadline from the parent).  It owns the office process explicitly and exports a tagged
# PDF/UA file with indexes refreshed.
_DRIVER = r'''
import os, subprocess, sys, time, uuid, shutil, tempfile
src, dst, timeout = sys.argv[1], sys.argv[2], float(sys.argv[3])
import uno
from com.sun.star.beans import PropertyValue
def prop(name, value):
    p = PropertyValue(); p.Name, p.Value = name, value; return p
def connect(pipe, deadline):
    ctx = uno.getComponentContext()
    resolver = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", ctx)
    url = "uno:pipe,name=%s;urp;StarOffice.ComponentContext" % pipe
    while time.time() < deadline:
        try:
            return resolver.resolve(url)
        except Exception:
            time.sleep(0.5)
    raise SystemExit("lo-export: office did not accept a connection in time")
profile = tempfile.mkdtemp()
pipe = "pk" + uuid.uuid4().hex[:12]
proc = subprocess.Popen(
    ["soffice", "--headless", "--norestore", "--invisible", "--nologo",
     "-env:UserInstallation=file://" + os.path.abspath(profile),
     "--accept=pipe,name=%s;urp;" % pipe],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
deadline = time.time() + timeout
try:
    ctx = connect(pipe, deadline)
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.loadComponentFromURL(
        uno.systemPathToFileUrl(os.path.abspath(src)), "_blank", 0,
        (prop("Hidden", True), prop("ReadOnly", False)))
    if doc is None:
        raise SystemExit("lo-export: could not open " + src)
    # fill in the index the field only declares — each index updates itself, after the layout
    # exists, or the entries have no pages to cite.
    doc.refresh()
    indexes = doc.getDocumentIndexes()
    for i in range(indexes.getCount()):
        indexes.getByIndex(i).update()
    doc.refresh()
    filt = uno.Any("[]com.sun.star.beans.PropertyValue",
                   (prop("PDFUACompliance", True), prop("UseTaggedPDF", True),
                    prop("ExportBookmarks", True)))
    doc.storeToURL(
        uno.systemPathToFileUrl(os.path.abspath(dst)),
        (prop("FilterName", "writer_pdf_Export"), prop("FilterData", filt)))
    doc.close(False)
    try:
        desktop.terminate()
    except Exception:
        pass
finally:
    try:
        proc.wait(timeout=max(5.0, min(60.0, deadline - time.time())))
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=30)
    shutil.rmtree(profile, ignore_errors=True)
if not (os.path.exists(dst) and os.path.getsize(dst) > 0):
    raise SystemExit("lo-export: no PDF produced")
'''


def _uno_python() -> str | None:
    """A python interpreter that can `import uno` (system python, LibreOffice's), or None — probed,
    not assumed.  The mise interpreter running the checks cannot import uno on this host."""
    env = {**os.environ,
           "URE_BOOTSTRAP": f"file://{_LO}/fundamentalrc",
           "PYTHONPATH": f"{_LO}:/usr/lib/python3/dist-packages",
           "LD_LIBRARY_PATH": _LO}
    for cand in ("/usr/bin/python3", "python3"):
        try:
            if subprocess.run([cand, "-c", "import uno"], env=env,
                              capture_output=True, timeout=20).returncode == 0:
                return cand
        except Exception:
            continue
    return None


def export_pdfua(src: Path, out: Path, timeout: int = 900) -> Path | None:
    """Export `src` (docx) to a tagged PDF/UA-1 at `out` over the UNO bridge, indexes refreshed.
    Returns `out` on success, None if no uno-capable python is available OR the bridge is killed at
    the deadline (a loud absence, never a stale/empty pass)."""
    py = _uno_python()
    if py is None:
        print("lo-export: no uno-capable python found (looked at /usr/bin/python3) — "
              "cannot drive the tagged-PDF export; refusing to skip-green", file=sys.stderr)
        return None
    env = {**os.environ,
           "URE_BOOTSTRAP": f"file://{_LO}/fundamentalrc",
           "PYTHONPATH": f"{_LO}:/usr/lib/python3/dist-packages",
           "LD_LIBRARY_PATH": _LO}
    out.unlink(missing_ok=True)                                # unlink-first (Ρ·render·provenance)
    try:
        subprocess.run([py, "-c", _DRIVER, str(src), str(out), str(timeout)],
                       env=env, timeout=timeout + 30, start_new_session=True, check=True)
    except subprocess.TimeoutExpired:
        print(f"lo-export: export exceeded {timeout}s — killed (a hang is a LOUD failure, never a "
              "silent stall)", file=sys.stderr)
        return None
    except subprocess.CalledProcessError:
        return None
    return out if out.exists() and out.stat().st_size > 0 else None


def _selftest() -> int:
    """⟨P, F, δ⟩ — the tagged-PDF/UA export over the hang-safe bridge:
      P: the bridge exports a Tagged PDF from a docx (connect→refresh→UA export→store).
      F: an impossibly short deadline kills the bridge → None (a LOUD, bounded failure — the failure
         sre's macro path lacked, a silent hang).
      δ: the deadline — a generous one exports a Tagged PDF, a 1s one is killed.
    If no uno-capable python exists, SKIP LOUD (never skip-green)."""
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    if _uno_python() is None:
        print("  -- uno-capable python not found on this host; bridge cannot be exercised.\n"
              "     LO-EXPORT SELFTEST: SKIP (loud) — the method is present but unrunnable here")
        return 0

    import re
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d)
        md, docx = dd / "toc.md", dd / "toc.docx"
        md.write_text("# Alpha\n\ntext\n\n# Beta\n\nmore\n")
        subprocess.run(["pandoc", str(md), "--toc", "-o", str(docx)], check=True)

        p_out = dd / "p.pdf"
        t0 = time.monotonic()
        got = export_pdfua(docx, p_out, timeout=180)
        p_secs = time.monotonic() - t0
        tagged = False
        if got is not None and p_out.exists():
            info = subprocess.run(["pdfinfo", str(p_out)], capture_output=True, text=True).stdout
            tagged = bool(re.search(r"Tagged:\s+yes", info))
        check("P: the bridge exports a Tagged PDF from a docx (UA export path)",
              got is not None and tagged)

        # Ζ·lo·deadline — the F arm's deadline is DERIVED from the P arm's measured export, not
        # hardcoded.  It was `timeout=1` with the comment "shorter than LO startup", and that
        # premise DECAYED: this host now exports in 0.96s, so a 1s deadline no longer kills
        # anything and the arm went red while the mechanism it tests was working perfectly.  A
        # wall-clock constant in a fixture is a claim about the machine, and machines get faster.
        #
        # The deadline reaches the bridge as a FLOAT (the worker reads `float(sys.argv[3])`), so a
        # sub-second fraction is expressible however fast the host is — the `int` annotation on
        # export_pdfua is cosmetic.  A tenth of the measured time cannot outlive an export that
        # actually took that time, on any machine, which is what makes the arm portable.
        f_out = dd / "f.pdf"
        f_deadline = round(p_secs / 10, 3)
        killed = export_pdfua(docx, f_out, timeout=f_deadline)
        check(f"F: a deadline of {f_deadline}s (a tenth of the measured {p_secs:.2f}s) is killed → None",
              killed is None)
        check("δ: the deadline decides — the measured time exports a Tagged PDF, a tenth of it is killed",
              got is not None and killed is None)

    if fails:
        print(f"LO-EXPORT SELFTEST: FAIL ({len(fails)})")
        return 1
    print("LO-EXPORT SELFTEST: PASS")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--selftest":
        return _selftest()
    if len(argv) < 2:
        print("usage: lo-export.py SRC.docx OUT.pdf [--timeout N] | --selftest", file=sys.stderr)
        return 3
    src, out = Path(argv[0]), Path(argv[1])
    timeout = int(argv[argv.index("--timeout") + 1]) if "--timeout" in argv else 900
    if not src.exists():
        print(f"lo-export: source not found at {src}", file=sys.stderr)
        return 1
    got = export_pdfua(src, out, timeout=timeout)
    if got is None:
        print("lo-export: FAIL — no tagged PDF produced (unavailable or killed)", file=sys.stderr)
        return 1
    print(f"lo-export: ok — exported {out} as a tagged PDF/UA over the office bridge, indexes refreshed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
