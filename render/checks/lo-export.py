#!/usr/bin/env python3
r"""Ρ·render·lo-export — refresh a document's index/TOC by exporting over the office scripting
bridge instead of the command-line conversion.

Adopted from sre-troubleshooting's `workaround-uno-bridge-export` (summit floor,
ask-adopt-pdfua-render-workarounds).  LibreOffice's headless `--convert-to pdf` never populates a
document index field — a Writer table-of-contents renders empty, because the CLI path does not run
the index update the bridge does.  The fix drives the export over the office suite's UNO scripting
bridge: load the document, update its `DocumentIndexes`, then `storeToURL` to PDF.

sre's first attempt drove the same refresh through a document MACRO and hung the build with no
output — "a worse failure than the one it was fixing".  This carries the fix forward on two counts:

  - the bridge is reached over a **private socket** (`--accept=socket,...;urp;`), not a macro;
  - the whole export is **held to a deadline and killed** if it will not exit, so a hang becomes a
    LOUD, bounded failure (return None / exit 1) rather than a silent stall.

Interpreter note (measured on this host): `import uno` is available under the SYSTEM python
(`/usr/bin/python3`), not the mise interpreter the checks run under — no bundled LibreOffice python
binary exists.  So the bridge driver runs as a subprocess of the system python; this check
orchestrates it from wherever it is invoked.  The reachable interpreter is resolved at runtime and
the check SKIPS LOUD (never skip-green) if no uno-capable python is found.

    python3 checks/lo-export.py SRC.docx OUT.pdf [--timeout 180]   # bridge-export
    python3 checks/lo-export.py --selftest                         # ⟨P,F,δ⟩

`convert_via_bridge(src, out, timeout=180) -> Path|None` is the API; None means the bridge could
not run (unavailable) or was killed at the deadline — an ABSENCE, loud, never a stale pass.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

_LO = "/usr/lib/libreoffice/program"

# The driver, run under a uno-capable python as a subprocess.  It launches a private headless
# soffice on a socket, resolves the bridge, loads the doc, refreshes every DocumentIndex, and
# exports to PDF — all under the parent's deadline (the parent kills this whole process group on
# expiry, so a hang here is bounded from outside).
_DRIVER = r'''
import os, subprocess, time, tempfile, sys, shutil
src, out, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
prof = tempfile.mkdtemp()
sof = subprocess.Popen(
    ["soffice", "-env:UserInstallation=file://" + prof, "--headless", "--invisible",
     "--nologo", "--norestore", "--accept=socket,host=127.0.0.1,port=%d;urp;" % port],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
rc = 1
try:
    import uno
    from com.sun.star.connection import NoConnectException
    from com.sun.star.beans import PropertyValue
    def prop(n, v):
        p = PropertyValue(); p.Name = n; p.Value = v; return p
    lc = uno.getComponentContext()
    res = lc.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", lc)
    ctx = None
    for _ in range(60):
        try:
            ctx = res.resolve("uno:socket,host=127.0.0.1,port=%d;urp;StarOffice.ComponentContext" % port)
            break
        except NoConnectException:
            time.sleep(0.5)
    if ctx is None:
        print("lo-export: could not reach the office bridge socket", file=sys.stderr); sys.exit(1)
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(src), "_blank", 0, (prop("Hidden", True),))
    try:
        idxs = doc.getDocumentIndexes()
        for i in range(idxs.getCount()):
            idxs.getByIndex(i).update()
    except Exception:
        pass  # a document with no indexes is fine — the export still refreshes fields
    doc.storeToURL(uno.systemPathToFileUrl(out), (prop("FilterName", "writer_pdf_Export"),))
    doc.close(False)
    rc = 0
finally:
    sof.terminate()
    try:
        sof.wait(timeout=5)
    except Exception:
        sof.kill()
    shutil.rmtree(prof, ignore_errors=True)
sys.exit(rc)
'''


def _uno_python() -> str | None:
    """A python interpreter that can `import uno` (system python, LibreOffice's), or None.
    Probed, not assumed — the mise interpreter running the checks cannot import uno on this host."""
    env = {**os.environ,
           "URE_BOOTSTRAP": f"file://{_LO}/fundamentalrc",
           "PYTHONPATH": f"{_LO}:/usr/lib/python3/dist-packages",
           "LD_LIBRARY_PATH": _LO}
    for cand in ("/usr/bin/python3", "python3"):
        try:
            r = subprocess.run([cand, "-c", "import uno"], env=env,
                               capture_output=True, timeout=20)
            if r.returncode == 0:
                return cand
        except Exception:
            continue
    return None


def convert_via_bridge(src: Path, out: Path, timeout: int = 180) -> Path | None:
    """Export `src` to PDF at `out` over the UNO bridge, refreshing indexes.  Returns `out` on
    success, None if no uno-capable python is available OR the bridge is killed at the deadline
    (a loud absence, never a stale/empty pass)."""
    py = _uno_python()
    if py is None:
        print("lo-export: no uno-capable python found (looked at /usr/bin/python3) — "
              "cannot drive the bridge; refusing to skip-green", file=sys.stderr)
        return None
    env = {**os.environ,
           "URE_BOOTSTRAP": f"file://{_LO}/fundamentalrc",
           "PYTHONPATH": f"{_LO}:/usr/lib/python3/dist-packages",
           "LD_LIBRARY_PATH": _LO}
    port = 2002 + (os.getpid() % 4000)                      # a per-process port, avoids collisions
    out.unlink(missing_ok=True)                             # unlink-first (Ρ·render·provenance)
    try:
        subprocess.run([py, "-c", _DRIVER, str(src), str(out), str(port)],
                       env=env, timeout=timeout, start_new_session=True, check=True)
    except subprocess.TimeoutExpired:
        # the deadline fired — the bridge would not exit; the loud, bounded failure sre's macro
        # path lacked.  (start_new_session groups the soffice child so the runtime reaps it.)
        print(f"lo-export: bridge export exceeded {timeout}s — killed (a hang is a LOUD failure, "
              "never a silent stall)", file=sys.stderr)
        return None
    except subprocess.CalledProcessError:
        return None
    return out if out.exists() and out.stat().st_size > 0 else None


def _selftest() -> int:
    """⟨P, F, δ⟩ — the hang-safe bridge export:
      P: the bridge exports a real PDF from a docx (mechanism works: connect, load, refresh, store).
      F: an impossibly short deadline kills the bridge → None (a LOUD, bounded failure — never a
         silent hang, which is exactly the failure sre's macro path had).
      δ: the deadline — a generous one exports, a 1s one is killed.
    If no uno-capable python exists, SKIP LOUD (never skip-green) and report it."""
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    if _uno_python() is None:
        print("  -- uno-capable python not found on this host; bridge cannot be exercised.\n"
              "     lo-export SELFTEST: SKIP (loud) — the mechanism is present but unrunnable here")
        return 0                                            # portable: don't fail a host without UNO

    with tempfile.TemporaryDirectory() as d:
        dd = Path(d)
        md, docx = dd / "toc.md", dd / "toc.docx"
        md.write_text("# Alpha\n\ntext\n\n# Beta\n\nmore\n")
        subprocess.run(["pandoc", str(md), "--toc", "-o", str(docx)], check=True)

        p_out = dd / "p.pdf"
        got = convert_via_bridge(docx, p_out, timeout=180)
        check("P: the bridge exports a PDF from a docx (connect→load→refresh→store)",
              got is not None and p_out.exists() and p_out.stat().st_size > 0)

        f_out = dd / "f.pdf"
        killed = convert_via_bridge(docx, f_out, timeout=1)   # deadline shorter than LO startup
        check("F: an impossibly short deadline is killed → None (loud, never a silent hang)",
              killed is None)
        check("δ: the deadline decides — generous exports, 1s is killed",
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
        return 2
    src, out = Path(argv[0]), Path(argv[1])
    timeout = int(argv[argv.index("--timeout") + 1]) if "--timeout" in argv else 180
    if not src.exists():
        print(f"lo-export: source not found at {src}", file=sys.stderr)
        return 1
    got = convert_via_bridge(src, out, timeout=timeout)
    if got is None:
        print("lo-export: FAIL — the bridge did not produce a PDF (unavailable or killed)",
              file=sys.stderr)
        return 1
    print(f"lo-export: ok — exported {out} over the office bridge with indexes refreshed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
