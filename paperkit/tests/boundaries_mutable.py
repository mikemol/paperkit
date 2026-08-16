#!/usr/bin/env python3
"""Ζ·delta·extensionless — the mutation surface keys on the FILE, not just its suffix.

`layout._mutable` decides which files Δ may corrupt.  Historically it keyed on the file's SUFFIX
(the `MUTABLE_SUFFIXES` set) with a single special-case for `.githooks/`.  So every extensionless
versioned command a witness reads — `scripts/summit`, `scripts/check`, `bin/pk`, a `.githooks/`
hook, a `Containerfile` — was a file Δ could not corrupt, and any witness reading one carried an
UNFALSIFIABLE component (summit's ask-delta-extensionless).  The exception was drawn around ONE
artifact (`.githooks`), not the CLASS it belonged to.

`_suffixless_text(f)` generalizes it: a file with NO suffix that decodes as text (a NUL byte ⇒
binary, excluded) is mutable.  Keyed on CONTENT because the Δ sandbox is a copy without `.git`
(git-tracked-ness is not testable there) and mode is not reliable — content is the only signal
always present.  MUTABLE_SUFFIXES still owns the SUFFIXED text files; this owns the suffixless
ones; together they are a closer proxy for "could this file's content change a claim's truth"
than suffix alone.

    python3 paperkit/tests/boundaries_mutable.py     # exit 0 = the surface admits the class
"""
from __future__ import annotations

import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))

import layout  # noqa: E402


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Ζ·delta·extensionless — the extensionless-text mutation class\n")

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        # A suffixless text command (the class the ask names) — a witness reads it, so Δ must
        # be able to corrupt it.
        cmd = root / "summit"
        cmd.write_text("#!/usr/bin/env bash\necho hi\n")
        # A suffixless BINARY (a compiled command) — content decides: a NUL byte excludes it.
        binary = root / "sched-batch"
        binary.write_bytes(b"\x7fELF\x00\x00\x00compiled\n")
        # A suffixed text source — unaffected, still mutable via MUTABLE_SUFFIXES.
        suffixed = root / "warrants.bib"
        suffixed.write_text("@misc{x}\n")
        # A suffixed binary — unaffected, still immutable.
        image = root / "fig.png"
        image.write_bytes(b"\x89PNG\r\n\x00\x00")

        print("⟨the class⟩\n")
        check("a suffixless TEXT command is mutable (Δ can corrupt what a witness reads)",
              layout._mutable(cmd))
        check("a suffixless BINARY is NOT mutable (a NUL byte ⇒ binary, excluded)",
              not layout._mutable(binary))
        check("the helper agrees: suffixless text is text, suffixless binary is not",
              layout._suffixless_text(cmd) and not layout._suffixless_text(binary))

        print("\n⟨the suffix path is untouched⟩\n")
        check("a suffixed text source is still mutable (MUTABLE_SUFFIXES owns it)",
              layout._mutable(suffixed))
        check("a suffixed binary is still immutable",
              not layout._mutable(image))
        check("_suffixless_text is FALSE for anything with a suffix (it owns only the bare ones)",
              not layout._suffixless_text(suffixed) and not layout._suffixless_text(image))

        print("\n⟨derived files stay out⟩\n")
        cache = root / ".delta-cache.json"
        cache.write_text("{}\n")
        check("a DERIVED name is never mutable, suffix or not (it is an output)",
              not layout._mutable(cache))

        print("\n⟨P, F, δ⟩ minimum-delta pair — δ is the NUL byte\n")
        # The whole class turns on ONE bit of content: the same suffixless file is mutable as
        # text and immutable the instant it carries a NUL.  This is the coverage whose absence
        # let the `.githooks`-only special-case stand as if it were the whole class.
        probe = root / "pk"
        probe.write_text("run\n")
        as_text = layout._mutable(probe)
        probe.write_bytes(b"ru\x00n\n")
        as_binary = layout._mutable(probe)
        ok = as_text and not as_binary
        fails.append("mutable-delta") if not ok else None
        print(f"  {'ok ' if ok else 'XX '}one NUL byte flips a suffixless command out of the surface")
        print("      P (as shipped): a suffixless text command → mutable")
        print("      F (one NUL added): the same file → immutable (binary)")
        print("      δ (min delta): a single NUL byte in the first 4096\n")

    if fails:
        print(f"MUTABLE: FAIL ({len(fails)})")
        return 1
    print("MUTABLE: PASS (8 behaviors, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
