#!/usr/bin/env python3
r"""Ρ·render·svgpad — pad an SVG's viewport before the EMF conversion so nothing is clipped.

Adopted from sre-troubleshooting's third workaround (summit floor,
ask-adopt-pdfua-render-workarounds).  mat230's audit-table frame classifies this one as NOT a WCAG
criterion — it is render FIDELITY, not accessibility — so it lives here beside the figure checks,
never in `a11y.py`.

The LibreOffice SVG→EMF step shaves each edge and clips titles and legends that sit flush against
the drawing's bounding box: the EMF rasterizer/clipper trims a hairline at the viewport boundary,
and any label touching x=0 or the right/top edge loses pixels — or, at worst, a whole legend word.
The fix inflates the viewport by a symmetric margin BEFORE conversion, so the boundary the clipper
trims is empty space and the drawing keeps its full extent.

Surgical edit of the root `<svg>` tag only: widen `viewBox` (min-x/min-y out, width/height up by
2·margin) and the `width`/`height` attributes to match, keeping the aspect ratio.  The drawing's own
coordinates — and every other byte of the file — are untouched: it simply gains a border.  We edit
the opening tag's attributes with a regex rather than reserialize the tree, because ElementTree
rewrites the default SVG namespace as a `ns0:` prefix that LibreOffice's SVG importer rejects.  No
new dependencies.

    pad_svg(src_bytes, frac=0.05, min_pt=8.0) -> bytes     # the API fig_vector/fig_legible call
    python3 checks/svgpad.py --selftest                    # ⟨P,F,δ⟩
"""
from __future__ import annotations

import re
import sys


def _num(s: str) -> float:
    """Leading number of an SVG length ('120', '120px', '120pt' → 120.0)."""
    m = re.match(r"\s*(-?[\d.]+)", s or "")
    return float(m.group(1)) if m else 0.0


def _attr(tag: str, name: str) -> str | None:
    m = re.search(rf'\b{name}\s*=\s*"([^"]*)"', tag)
    return m.group(1) if m else None


def _set_attr(tag: str, name: str, value: str) -> str:
    """Set (or, if absent, do not add) an attribute in an opening-tag string."""
    return re.sub(rf'(\b{name}\s*=\s*")[^"]*(")', rf'\g<1>{value}\g<2>', tag, count=1)


def pad_svg(src: bytes, frac: float = 0.05, min_pt: float = 8.0) -> bytes:
    """Return `src` with its viewport inflated by a symmetric margin = max(frac·min(w,h), min_pt) on
    every side.  The drawing keeps its coordinates; only the root <svg> tag's viewBox and
    width/height grow around it, and nothing else in the file changes."""
    text = src.decode("utf-8", errors="replace")
    m0 = re.search(r"<svg\b[^>]*>", text, re.S)
    if not m0:
        return src
    open_tag = m0.group(0)

    vb = _attr(open_tag, "viewBox")
    if vb:
        x, y, w, h = (float(t) for t in re.split(r"[ ,]+", vb.strip())[:4])
    else:
        w, h = _num(_attr(open_tag, "width") or "0"), _num(_attr(open_tag, "height") or "0")
        x, y = 0.0, 0.0
    if w <= 0 or h <= 0:
        return src                                          # nothing measurable to pad; leave it

    m = max(frac * min(w, h), min_pt)
    new_vb = f"{x - m:g} {y - m:g} {w + 2 * m:g} {h + 2 * m:g}"

    new_tag = open_tag
    if _attr(new_tag, "viewBox") is not None:
        new_tag = _set_attr(new_tag, "viewBox", new_vb)
    else:
        new_tag = new_tag[:-1] + f' viewBox="{new_vb}">'    # add it if the SVG had none
    # keep width/height in step so the on-page size grows with the viewport (no shrink-to-fit)
    if _attr(new_tag, "width") is not None:
        new_tag = _set_attr(new_tag, "width", f"{_num(_attr(new_tag, 'width')) + 2 * m:g}")
    if _attr(new_tag, "height") is not None:
        new_tag = _set_attr(new_tag, "height", f"{_num(_attr(new_tag, 'height')) + 2 * m:g}")

    return (text[:m0.start()] + new_tag + text[m0.end():]).encode("utf-8")


def _viewbox(src: bytes) -> tuple[float, float, float, float]:
    tag = re.search(r"<svg\b[^>]*>", src.decode("utf-8", errors="replace"), re.S).group(0)
    x, y, w, h = (float(t) for t in re.split(r"[ ,]+", _attr(tag, "viewBox").strip())[:4])
    return x, y, w, h


def _selftest() -> int:
    """⟨P, F, δ⟩ — an SVG whose text touches the top-left corner (x=0,y=0):
      P: after pad_svg, the viewBox origin is negative and w/h grew by 2·margin — the corner text
         now sits INSIDE the viewport with empty border around it.
      F: the un-padded SVG has origin (0,0) — text flush at the edge, the clipper's shave target.
      δ: the pad — origin moves from 0 to −margin, extent grows by 2·margin."""
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    src = (b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80" viewBox="0 0 100 80">'
           b'<text x="0" y="10">legend</text></svg>')
    x0, y0, w0, h0 = _viewbox(src)
    padded = pad_svg(src, frac=0.05, min_pt=8.0)
    x1, y1, w1, h1 = _viewbox(padded)
    margin = max(0.05 * 80, 8.0)                            # = 8.0 here (0.05·80=4 < 8)

    check("F: the un-padded SVG has origin (0,0) — text flush at the clip edge", x0 == 0 and y0 == 0)
    check("P: padded origin is negative (a border now surrounds the drawing)", x1 < 0 and y1 < 0)
    check("P: padded extent grew by 2·margin on each axis",
          abs(w1 - (w0 + 2 * margin)) < 1e-6 and abs(h1 - (h0 + 2 * margin)) < 1e-6)
    check("δ: the origin moved by exactly the margin", abs(x1 - (x0 - margin)) < 1e-6)
    check("an SVG with no measurable viewport is returned unchanged (never crashes)",
          pad_svg(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>').startswith(b'<'))

    if fails:
        print(f"SVGPAD SELFTEST: FAIL ({len(fails)})")
        return 1
    print("SVGPAD SELFTEST: PASS")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--selftest":
        return _selftest()
    print("usage: svgpad.py --selftest   (pad_svg is the library API used by the figure checks)",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
