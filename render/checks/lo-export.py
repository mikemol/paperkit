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
import contextlib
import io
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
def connect(pipe, proc):
    """⛑ Ζ·lo·connect — WAIT ON THE PROCESS, NOT ON A CLOCK.  This took a `deadline` and gave up
    when it expired, so on a loaded box a soffice that was still starting was declared a failure:
    the F arm's subject then died at CONNECTION rather than at the hang it exists to exercise,
    `killed is None` passed for the wrong reason and "the kill is LOUD" reddened against a message
    about the connection.  A slow box is not a broken one — the operator's ruling, twice: "time-based
    gates and deadlines are intrinsically unreliable and unsafe.  Unsound by construction."

    The countable event is our OWN child's liveness: we start soffice on a PRIVATE pipe, so an
    office that is alive is still coming up and one that has EXITED will never accept a connection.
    That terminates on the subject's own state at any speed, and says which of the two happened."""
    ctx = uno.getComponentContext()
    resolver = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", ctx)
    url = "uno:pipe,name=%s;urp;StarOffice.ComponentContext" % pipe
    while True:
        try:
            return resolver.resolve(url)
        except Exception:
            pass
        rc = proc.poll()
        if rc is not None:
            raise SystemExit(
                "lo-export: office EXITED (rc=%s) without accepting a connection on its pipe" % rc)
        time.sleep(0.5)
profile = tempfile.mkdtemp()
pipe = "pk" + uuid.uuid4().hex[:12]
proc = subprocess.Popen(
    ["soffice", "--headless", "--norestore", "--invisible", "--nologo",
     "-env:UserInstallation=file://" + os.path.abspath(profile),
     "--accept=pipe,name=%s;urp;" % pipe],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
deadline = time.time() + timeout
try:
    ctx = connect(pipe, proc)
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
    not assumed.  The mise interpreter running the checks cannot import uno on this host.
    """
    env = {**os.environ,
           "URE_BOOTSTRAP": f"file://{_LO}/fundamentalrc",
           "PYTHONPATH": f"{_LO}:/usr/lib/python3/dist-packages",
           "LD_LIBRARY_PATH": _LO}
    # Ζ·render·hermetic — the executor image carries The Document Foundation's build, whose pyuno
    # is compiled against its BUNDLED interpreter (program/python), not the system one; a Debian
    # build answers from /usr/bin/python3 via python3-uno.  Try the bundled one first: it is
    # right whenever it exists, and absent on a Debian install.
    for cand in (f"{_LO}/python", "/usr/bin/python3", "python3"):
        try:
            if subprocess.run([cand, "-c", "import uno"], env=env,
                              capture_output=True, timeout=20).returncode == 0:
                return cand
        except Exception:
            continue
    return None


# ⚑ Ζ·lo·unsound — A SUBJECT THAT CONNECTS AND THEN CANNOT FINISH.
#
# This is the F arm's subject, and it exists so the falsifier is a property of the SUBJECT rather
# than a race between two durations (the full reasoning is at the arm, in _selftest).  It performs
# the same connect the real driver does — same pipe, same resolver, same bootstrap — and then blocks
# forever instead of storing, which is precisely sre-troubleshooting's macro path: the office
# process is alive and responsive and the export never completes.
#
# It is NOT `sleep` and NOT a bad argument: either would test the wrapper's timeout plumbing while
# never reaching the bridge, and the claim is about owning an office process that WILL NOT EXIT.
# ⚑ NO DURATION APPEARS HERE, DELIBERATELY.  `threading.Event().wait()` with no argument blocks on
# an event nothing ever sets — an unsatisfiable wait, not a long one.  A `sleep(N)` would smuggle
# the refuted construction back in as the subject: N would have to exceed the budget, so the arm
# would once again depend on two durations comparing a particular way.
_HANG_DRIVER = _DRIVER.replace(
    "    doc.storeToURL(",
    "    import threading; threading.Event().wait()\n    doc.storeToURL(", 1)


def _export_via(driver: str, src: Path, out: Path, timeout: int) -> Path | None:
    """Run `driver` as the bridge worker — the ONE owner of the office process.

    ⚑ Factored out so the real export and the F arm's unfinishable subject share this code rather
    than each carrying their own copy: a falsifier that re-implements the mechanism it falsifies
    proves something about the copy (a guard must not copy what it guards).  The only difference
    between the two callers is WHICH driver runs, which is exactly the δ the selftest asserts.
    """
    py = _uno_python()
    if py is None:
        print(f"lo-export: no uno-capable python found (looked at {_LO}/python, /usr/bin/python3) — "
              "cannot drive the tagged-PDF export; refusing to skip-green", file=sys.stderr)
        return None
    env = {**os.environ,
           "URE_BOOTSTRAP": f"file://{_LO}/fundamentalrc",
           "PYTHONPATH": f"{_LO}:/usr/lib/python3/dist-packages",
           "LD_LIBRARY_PATH": _LO}
    out.unlink(missing_ok=True)                                # unlink-first (Ρ·render·provenance)
    try:
        subprocess.run([py, "-c", driver, str(src), str(out), str(timeout)],
                       env=env, timeout=timeout + 30, start_new_session=True, check=True)
    except subprocess.TimeoutExpired:
        # ⚑ The message is the LOUDNESS the claim promises, and the F arm asserts it: a silent kill
        # would satisfy a termination-only check while refuting "a LOUD bounded failure".
        print("lo-export: the bridge did not complete within its budget — killed "
              "(a hang is a LOUD failure, never a silent stall)", file=sys.stderr)
        out.unlink(missing_ok=True)                            # no partial artifact survives a kill
        return None
    except subprocess.CalledProcessError:
        return None
    return out if out.exists() and out.stat().st_size > 0 else None


def export_pdfua(src: Path, out: Path, timeout: int = 900) -> Path | None:
    """Export `src` (docx) to a tagged PDF/UA-1 at `out` over the UNO bridge, indexes refreshed.
    Returns `out` on success, None if no uno-capable python is available OR the bridge is killed at
    the deadline (a loud absence, never a stale/empty pass).
    """
    return _export_via(_DRIVER, src, out, timeout)


def _selftest() -> int:
    """⟨P, F, δ⟩ — the tagged-PDF/UA export over the hang-safe bridge:
      P: the bridge exports a Tagged PDF from a docx (connect→refresh→UA export→store).
      F: a bridge that CANNOT complete is killed → None, and the kill is REPORTED (a LOUD,
         bounded failure — the failure sre's macro path lacked, a silent hang).
      δ: whether the subject can finish at all — a real export yields a Tagged PDF, an
         unsatisfiable one is killed and says so.  NOT a duration: see Ζ·lo·unsound.
    If no uno-capable python exists, SKIP LOUD (never skip-green).
    """
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

        # ⚑ Ζ·lo·unsound — THE F ARM NO LONGER RACES A DURATION, AND THAT LADDER IS CLOSED.
        #
        # Two rungs of the same wrong construction stood here.  First `timeout=1` with the comment
        # "shorter than LO startup" — a premise that DECAYED when the host got faster.  Then a
        # deadline DERIVED as a tenth of the P arm's measured export, which decays more slowly and
        # decays the same way: it went red on 2026-09-12 reporting
        # `a deadline of 3.545s (a tenth of the measured 35.45s) is killed -> None`, with the P arm
        # PASSING.  Nothing about hang containment had changed; LibreOffice had got faster.
        #
        # ⚑⚑ THE OPERATOR'S RULING, AND IT IS THE GENERAL CASE: "time-based gates and deadlines are
        # intrinsically unreliable and unsafe.  Unsound by construction."  A deadline is the
        # MECHANISM this claim owns, but a deadline is not how you TEST it — racing one duration
        # against another measures the office suite's SPEED, which is host state, toolchain version
        # and cache warmth, none of which this claim is about.
        #
        # ⚑⚑⚑ SO THE SUBJECT IS MADE UNABLE TO FINISH, RATHER THAN MERELY RUSHED.  The subject is a
        # docx the bridge can open and then never complete on: `_HANG_DRIVER` connects exactly as
        # the real driver does and then blocks forever instead of storing.  Any budget kills it, so
        # the kill is a property of the SUBJECT and not of the host's speed.  report/mitigation.py
        # reasons this way already for the gate runner — "a zero-budget gate always times out, which
        # is exactly the condition the runner turns into `error`" — so the construction is the
        # repo's own, not a new one.
        #
        # ⚑ TWO PREMISES OF THE FIRST DRAFT WERE MEASURED AND BOTH WERE FALSE, WHICH IS WHY THE ARM
        # READS THE WAY IT DOES:
        #   * `timeout=0` does NOT make the parent give up immediately — `subprocess.run` is called
        #     with `timeout=timeout + 30`, so a zero budget still waits 30s and then the WORKER
        #     fails, raising CalledProcessError.  That is a different branch from the deadline kill
        #     this claim is about, and it returns None with NO message at all.
        #   * the killed notice goes to STDERR (`file=sys.stderr`), not stdout, so a
        #     redirect_stdout capture reads empty and "the kill is LOUD" would have been asserted
        #     against a silent path.
        # A `cannot` needs a probe, not a sentence: both were quoted from the source before the arm
        # was trusted, and both changed it.
        f_out = dd / "f.pdf"
        cap = io.StringIO()
        with contextlib.redirect_stderr(cap):
            killed = _export_via(_HANG_DRIVER, docx, f_out, timeout=5)
        said = cap.getvalue()
        print(said, end="")
        check("F: a bridge that connects and never completes is killed → None (no duration raced "
              "against another — the subject cannot finish at any budget)",
              killed is None)
        check("F: the kill is LOUD — the bridge reports it rather than stalling silently",
              "killed" in said)
        check("F: no partial artifact is left behind (never a stale pass)",
              not f_out.exists())
        check("δ: whether the subject CAN finish — a real export is Tagged, one that cannot "
              "complete is killed and reported",
              got is not None and tagged and killed is None and "killed" in said)

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
