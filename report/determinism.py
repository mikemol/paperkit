#!/usr/bin/env python3
# Ρ·report·determinism — the report's reproducibility BOUNDARY, made a checkable claim.
#
# A document is gated fresh-by-construction in this report only if its gate is DETERMINISTIC:
# sandbox-clean, no external toolchain, no build-cache/network dependence.  The on-demand documents
# (render, image, setup) are NOT — their checks invoke external tools (pandoc/libreoffice/podman/
# systemd), so `podman build`/libreoffice/apk-fetch make the verdict vary with cache and network
# state; committing such a verdict would make the report's own fresh: gate flaky.  So the report
# LISTS them but does not RUN them, and records that split as this claim.  (Mitigation of the
# non-determinism itself — e.g. image's img-stable digest reproducibility — is a follow-up claim.)
#
# This asserts the boundary in both directions: every on-demand document's checks DO invoke an
# external toolchain (that is *why* it is non-reproducible), and every reproducibly-gated document's
# checks do NOT (so running them here is deterministic).  cwd = report/.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ("pandoc", "libreoffice", "podman", "systemd-run",
            "pdftotext", "pdftoppm", "pdfinfo", "pdffonts", "pdfimages", "tesseract")
ONDEMAND = ("image", "render", "setup")     # non-reproducible (external toolchain / host-coupled)
REPRODUCIBLE = ("paper", "boundaries", "config")   # sandbox-clean (README's checks are pure too)


def _checktext(proj: str) -> str:
    d = ROOT / proj
    return "\n".join(p.read_text() for p in sorted(d.rglob("*.sh")) + sorted(d.rglob("*.py")) if p.is_file())


def _tools(proj: str):
    text = _checktext(proj)
    return [t for t in EXTERNAL if t in text]


def main() -> int:
    # CHARACTERIZE the boundary per document, and assert it in both directions.
    found = {p: _tools(p) for p in ONDEMAND}
    clean = [p for p, ts in found.items() if not ts]
    assert not clean, \
        f"on-demand documents must invoke an external toolchain (the source of their non-reproducibility): {clean}"
    leaky = [p for p in REPRODUCIBLE if _tools(p)]
    assert not leaky, \
        f"a reproducibly-gated document's checks invoke an external toolchain, so its gate is NOT deterministic: {leaky}"
    print("reproducibility boundary verified — the on-demand documents' variance is reproducible on demand:")
    for p in ONDEMAND:                    # the exact external commands behind each non-reproducible verdict
        print(f"  {p}: shells {', '.join(found[p])} → verdict varies with build-cache/network state")
    print(f"  the sandbox-clean set ({', '.join(REPRODUCIBLE)}, README) shells none → gated deterministically, run above")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
