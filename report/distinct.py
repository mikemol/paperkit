#!/usr/bin/env python3
# Ρ·report·distinct — rpt-proof's DISCRIMINATING witness: --without-K is actually CLEAN.
#
# ⚑ WHY THIS EXISTS, AND WHY `fresh:without-k.md` COULD NOT SERVE.  rpt-proof claims "in every
# document, every cited claim carries a distinct witness, so --without-K passes".  It used to be
# checked by `fresh:all`, i.e. gen.py --check, which asserts the RENDERED TABLE matches the
# pipeline.  But without_k_md() (gen.py:187) renders collapses whenever they exist — a full table
# is a fresh table.  So the freshness check passes just as happily when the property the claim
# asserts is FALSE, and it would have kept passing while this very project carried seven claims
# collapsed onto one `fresh:all` string.
#
# That is the exact defect --without-K exists to name, occurring in the claim ABOUT --without-K:
# the claim asserted a PROPERTY and its check verified a RENDERING.  A witness that cannot fail
# when the proposition is false is not a witness for it (Δ grades this; see rpt-delta).
#
# This check reads the same `collapses` map the table is rendered from and FAILS if any document
# has one.  It is the proposition, not its picture.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen  # noqa: E402  — the pipeline reader; _graded()/_gate() are its public-enough seam


def main() -> int:
    dirty, unran = {}, {}
    for name, proj in gen._graded():
        verdict = gen._gate(proj)
        # ⚑ AN ERROR IS NOT A CLEAN VERDICT.  _gate_once (gen.py:39) reports a gate that could not
        # RUN as {"error": ...} — deliberately, so a missing toolchain is never read as a
        # verification FAIL.  But `.get("collapses", {})` maps that error to the EMPTY map, which
        # reads as "no collapses" — clean, in the UNSAFE direction.  Absent and empty are
        # opposites here: one is "nothing was measured", the other "everything was, and it is
        # fine".  Collapsing them would let this witness certify --without-K over a document
        # whose gate never ran.
        if "error" in verdict:
            unran[name] = verdict["error"]
            continue
        collapses = verdict.get("collapses", {})
        if collapses:
            dirty[name] = collapses

    if dirty:
        for name, groups in sorted(dirty.items()):
            for check, keys in sorted(groups.items()):
                print(f"{name}: {len(keys)} claims share one witness `{check}` — "
                      f"{', '.join(sorted(keys))}", file=sys.stderr)
        print("--without-K is NOT clean: rpt-proof claims every cited claim carries a distinct "
              "witness, and the collapses above refute it", file=sys.stderr)
        return 1

    if unran:
        for name, why in sorted(unran.items()):
            print(f"{name}: gate could not run — {why}", file=sys.stderr)
        print(f"{len(unran)} document(s) were NOT evaluated, so rpt-proof's 'in every document' "
              "cannot be witnessed here.  Not a refutation.", file=sys.stderr)
        return 3

    docs = [name for name, _ in gen._graded()]
    print(f"--without-K clean across {len(docs)} document(s): {', '.join(docs)} — "
          "every cited claim carries a distinct witness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
