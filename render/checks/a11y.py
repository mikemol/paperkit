#!/usr/bin/env python3
r"""Ρ·render·a11y — accessible-PDF gate: assert a rendered PDF is accessible BY CONSTRUCTION
on four INDEPENDENT, MEASURED axes.  Each is measured (never assumed), printed, and bite-able;
exit 0 iff every axis passes, exit 1 otherwise (naming the axis that failed).

Where the sibling checks stop at font-embedding and tofu, this fills the PDF/UA + WCAG gap the
render narrative reaches for ("what the reader hears through a screen reader").  Parametrized on
the PDF path (a downstream project points it at its own accessible deliverable) — the paperkit
paper's own pandoc→LibreOffice PDF is NOT PDF/UA-tagged, so this ships as an opt-in tool, not a
warrant of the render project itself.

  (1) PDF/UA-2   — veraPDF --flavour ua2 → require failedChecks==0 AND passedChecks>0 (a "0 of 0"
                   empty run cannot pass vacuously).  veraPDF absent ⇒ FAIL LOUD, never skip-green.
  (2) Tagged     — pdfinfo reports Tagged: yes.  With --mathml, a MathML sidecar must also exist
                   (the math is recoverable structure, not ink); without it, Tagged alone.
  (3) Measure    — WCAG 2.2 SC 1.4.8: glyphs-per-line (pdftotext -layout, non-blank body lines);
                   require median ≤ --cpl-median and p90 ≤ --cpl-p90.  Prints the distribution.
  (4) Not just.  — WCAG 2.2 SC 1.4.8 forbids full justification.  MEASURED from real glyph
                   coordinates (pdftotext -bbox): the fraction of text lines flush at the modal
                   right margin.  Justified text clusters high; ragged text spreads.  The
                   by-construction LaTeX-source \RaggedRight marker is a producer-specific detector
                   and is intentionally NOT part of this de-coursed, format-agnostic gate.

    python3 checks/a11y.py DELIVERABLE.pdf [--mathml SIDECAR.html]
                           [--cpl-median 70] [--cpl-p90 80] [--flush-frac 0.38]
                           [--verapdf /path/to/verapdf]

Thresholds are parameters with WCAG-derived defaults; --flush-frac separates justified (~0.45)
from ragged (~0.28) — calibrate it against your producer if your body geometry differs.
"""
from __future__ import annotations

import argparse
import re
import shutil
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


class Result:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.rows.append((name, ok, detail))

    def ok(self) -> bool:
        return all(ok for _, ok, _ in self.rows)


def _run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def _find_verapdf(explicit: str | None) -> Path | None:
    """Resolve the veraPDF binary.  An EXPLICIT --verapdf is authoritative: if it does not exist we
    return None (fail loud — do NOT silently hunt elsewhere for a binary the caller did not name).
    Otherwise try `verapdf` on PATH, then the conventional ~/.local/bin/verapdf.  None if unresolved."""
    if explicit is not None:
        return Path(explicit) if Path(explicit).exists() else None
    for cand in (shutil.which("verapdf"), str(Path.home() / ".local" / "bin" / "verapdf")):
        if cand and Path(cand).exists():
            return Path(cand)
    return None


# ── (1) PDF/UA-2 via veraPDF ─────────────────────────────────────────────────────────────────────
def check_ua2(r: Result, pdf: Path, verapdf: str | None) -> None:
    binp = _find_verapdf(verapdf)
    if binp is None:
        r.add("(1) PDF/UA-2 (veraPDF)", False,
              "veraPDF not found (looked at --verapdf, PATH, ~/.local/bin) — "
              "cannot verify; refusing to skip-green")
        return
    rc, out = _run([str(binp), "--flavour", "ua2", str(pdf)])
    m = re.search(r'<details[^>]*passedChecks="(\d+)"[^>]*failedChecks="(\d+)"', out)
    if not m:
        r.add("(1) PDF/UA-2 (veraPDF)", False, f"could not parse veraPDF report (rc={rc})")
        return
    passed, failed = int(m.group(1)), int(m.group(2))
    ok = failed == 0 and passed > 0            # a "0 of 0" empty run cannot pass vacuously
    r.add("(1) PDF/UA-2 (veraPDF)", ok, f"passedChecks={passed} failedChecks={failed}")


# ── (2) Tagged + optional MathML sidecar ───────────────────────────────────────────────────────────
def check_tagged(r: Result, pdf: Path, mathml: Path | None) -> None:
    _, out = _run(["pdfinfo", str(pdf)])
    tagged = bool(re.search(r"Tagged:\s+yes", out))
    if mathml is not None:
        sidecar = mathml.exists()
        ok = tagged and sidecar
        r.add("(2) Tagged + MathML sidecar", ok,
              f"pdfinfo Tagged={'yes' if tagged else 'NO'}; "
              f"sidecar={'present' if sidecar else 'MISSING'}")
    else:
        r.add("(2) Tagged", tagged, f"pdfinfo Tagged={'yes' if tagged else 'NO'} (no --mathml given)")


# ── (3) CPL measure (WCAG 1.4.8) ─────────────────────────────────────────────────────────────────
def _cpl(pdf: Path) -> list[int]:
    _, out = _run(["pdftotext", "-layout", str(pdf), "-"])
    # glyphs per line: strip the margin padding -layout inserts; count non-blank body lines only.
    return sorted(len(ln.strip()) for ln in out.splitlines() if ln.strip())


def check_measure(r: Result, pdf: Path, median_max: int, p90_max: int) -> None:
    lens = _cpl(pdf)
    if not lens:
        r.add(f"(3) CPL median≤{median_max}, p90≤{p90_max}", False, "no text extracted")
        return
    n = len(lens)
    median = statistics.median(lens)
    p90 = lens[min(n - 1, int(0.9 * n))]
    ok = median <= median_max and p90 <= p90_max
    r.add(f"(3) CPL median≤{median_max}, p90≤{p90_max}", ok,
          f"n={n} median={median:.0f} p90={p90} max={max(lens)}")
    # print the distribution (deciles)
    print("    CPL distribution (glyphs/line, non-blank body lines):")
    print("      " + "  ".join(f"p{d*10}={lens[min(n-1,int(d/10*n))]}" for d in range(1, 10)))
    print(f"      min={min(lens)} max={max(lens)}")


# ── (4) Not justified — measured modal-right-edge flush fraction ────────────────────────────────────
def _flush_fraction(pdf: Path) -> tuple[float, int]:
    """Fraction of text lines whose right edge sits within 5pt of the modal right margin.
    Real glyph coordinates (pdftotext -bbox) — grid-snapped -layout columns are unreliable here."""
    _, xml = _run(["pdftotext", "-bbox", str(pdf), "-"])
    lines: dict[tuple[int, int], list[float]] = defaultdict(lambda: [1e9, -1e9])
    pg = 0
    for chunk in xml.split("</page>"):
        if "<word" not in chunk:
            continue
        pg += 1
        for m in re.finditer(
                r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">', chunk):
            xmin, ymin, xmax, _ = (float(g) for g in m.groups())
            key = (pg, round(ymin / 2))          # 2pt vertical buckets → one entry per text line
            box = lines[key]
            box[0] = min(box[0], xmin)
            box[1] = max(box[1], xmax)
    rights = [box[1] for box in lines.values()]
    if not rights:
        return 0.0, 0
    # modal right edge over 5pt bins
    bins: dict[int, int] = defaultdict(int)
    for x in rights:
        bins[round(x / 5) * 5] += 1
    mode_edge = max(bins, key=lambda k: bins[k])
    flush = sum(1 for x in rights if abs(x - mode_edge) <= 5)
    return flush / len(rights), len(rights)


def check_not_justified(r: Result, pdf: Path, flush_max: float) -> None:
    frac, nlines = _flush_fraction(pdf)
    ok = frac < flush_max
    r.add("(4) Not justified (ragged-right)", ok,
          f"flush_frac={frac:.2f} (<{flush_max} ragged) over {nlines} lines")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="accessible-PDF gate (WCAG 2.2 SC 1.4.8 + PDF/UA-2)")
    ap.add_argument("pdf", type=Path, help="the rendered PDF deliverable to gate")
    ap.add_argument("--mathml", type=Path, default=None,
                    help="a MathML sidecar that must exist (math is recoverable structure)")
    ap.add_argument("--cpl-median", type=int, default=70, help="max median glyphs/line (WCAG)")
    ap.add_argument("--cpl-p90", type=int, default=80, help="max p90 glyphs/line (WCAG ceiling)")
    ap.add_argument("--flush-frac", type=float, default=0.38,
                    help="max modal-right-edge flush fraction (<this = ragged)")
    ap.add_argument("--verapdf", default=None, help="path to the veraPDF binary")
    args = ap.parse_args(argv)

    if not args.pdf.exists():
        print(f"a11y: PDF not found at {args.pdf} — build the deliverable first", file=sys.stderr)
        return 1
    r = Result()
    check_ua2(r, args.pdf, args.verapdf)
    check_tagged(r, args.pdf, args.mathml)
    check_measure(r, args.pdf, args.cpl_median, args.cpl_p90)
    check_not_justified(r, args.pdf, args.flush_frac)

    print(f"\n  a11y gate — {args.pdf.name}")
    print("  " + "-" * 66)
    for name, ok, detail in r.rows:
        print(f"  {'✓' if ok else '✗'} {name:<34} {detail}")
    print("  " + "-" * 66)
    if r.ok():
        print("  a11y: PASS — WCAG 2.2 SC 1.4.8 + PDF/UA-2 verified")
        return 0
    print("  a11y: FAIL — one or more accessibility criteria not met", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
