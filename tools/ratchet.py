#!/usr/bin/env python3
r"""ratchet — a reusable paydown-only census gate: a set may only SHRINK, never grow.

The shape a prohibition takes as a check.  A flag saying "the predecessor did X and it broke" is a
prohibition on returning to X; spelled as a checkable proposition it is "the census of X may only
shrink."  cotype/check.py is one instance (ledger entry-keys never vanish — a monotone-GROW variant);
substrate runs fourteen bespoke ones, summit one.  Every project reimplementing the census is a graded
census rebuilt locally, waiting to drift — so the ENGINE owns the mechanism (extract a census, compare
to a committed baseline, refuse a regression) and the PROJECT declares the POLICY: which pattern is
the census, and which direction is the ratchet.

The census is whatever the project points at: the count of matches of a regex (occurrences of a
forbidden construct), or the SET of keys the regex captures (a group-1 capture makes it a set-shrink
rather than a count-shrink).  The baseline is a committed file; the current file must not regress
against it.

Two properties this floor earned and every ratchet must carry:
  n OF m, never a bare count.  The verdict NAMES the baseline it read (`34 of a baseline 86`), because
    a census reporting a bare total is how a snapshot gets counted as live corpus.
  A T-ARM AND AN F-ARM.  A scan whose all-clear has never been shown to differ from its found-something
    is not a measurement — so every run PROVES its own ⟨P,F,δ⟩ on in-memory copies (never the tree): a
    synthetic regression against the baseline MUST be caught, or the gate refuses to pass (unsound).

    python3 tools/ratchet.py --pattern <regex> [--set] [--grow] <baseline-file> <current-file>
      --pattern  the census: a Python regex.  Without --set the census is the COUNT of matches;
                 with --set it is the SET of the regex's group-1 captures (a keyed census).
      --set      census is the captured-key SET (may-only-shrink as a set); default is the match COUNT.
      --grow     invert the ratchet to may-only-GROW (an append-only ledger: nothing may vanish).
                 Default is may-only-SHRINK (a paydown census: nothing may be added).
    exit 0 = the ratchet holds (+ the F-arm self-proof passes); 1 = a regression (named); 2 = usage.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def census(text: str, pattern: str, as_set: bool):
    """The census of `text` under `pattern`: the SET of group-1 captures (as_set) or the multiset
    COUNT of matches.  Returns (kind, value) — ("set", frozenset) or ("count", int)."""
    rx = re.compile(pattern, re.M)
    if as_set:
        return "set", frozenset(rx.findall(text))
    return "count", len(rx.findall(text))


def regressed(base, cur, grow: bool):
    """The regression, if any, of `cur`'s census vs `base`'s under the ratchet direction.  For a SET
    census: (shrink) the keys ADDED, or (grow) the keys REMOVED.  For a COUNT: the signed overage.
    Returns a truthy description of the regression, or a falsey empty value if the ratchet holds."""
    bkind, bval = base
    ckind, cval = cur
    assert bkind == ckind, "baseline and current census kinds differ"
    if bkind == "set":
        # shrink ⇒ nothing may be ADDED; grow ⇒ nothing may be REMOVED.
        return sorted(cval - bval) if not grow else sorted(bval - cval)
    # count: shrink ⇒ cur may not exceed base; grow ⇒ cur may not fall below base.
    over = (cval - bval) if not grow else (bval - cval)
    return over if over > 0 else 0


def _fmt(kind, val) -> str:
    return f"{len(val)} keys" if kind == "set" else str(val)


def check(base_text: str, cur_text: str, pattern: str, as_set: bool, grow: bool):
    """(ok, message) for the ratchet, with the n-of-m verdict and the F-arm self-proof.  ok is False
    on a real regression OR on a failed self-proof (an unsound ratchet must not pass)."""
    base = census(base_text, pattern, as_set)
    cur = census(cur_text, pattern, as_set)
    direction = "grow" if grow else "shrink"
    forbidden = "added" if not grow else "removed"

    reg = regressed(base, cur, grow)
    if reg:
        detail = ("\n".join(f"  - {k}" for k in reg) if as_set
                  else f"  census {_fmt(*cur)} vs a baseline {_fmt(*base)} — {reg} over the ratchet")
        return False, (f"ratchet: FAIL — the census {forbidden} against its baseline (may-only-"
                       f"{direction}); {_fmt(*cur)} vs a baseline {_fmt(*base)}:\n{detail}")

    # ⟨P,F,δ⟩ self-proof on an in-memory copy (never the tree): a SYNTHETIC regression against the
    # baseline MUST be caught, or the gate is unsound and refuses to pass.  δ = one census element.
    #   shrink ⇒ inject one forbidden addition;  grow ⇒ delete one baseline element.
    if grow:
        m = re.compile(pattern, re.M).search(base_text)
        probe = base_text.replace(m.group(0), "", 1) if m else base_text  # drop one → must be caught
        caught = bool(regressed(base, census(probe, pattern, as_set), grow))
    else:
        # inject a synthetic match the census will COUNT/CAPTURE.  Re-use a match from the baseline
        # itself so the pattern is guaranteed to match the injected line; for a keyed (--set) census
        # a bare re-inject of the same key does not grow the SET (it is already present), so a keyed
        # shrink-ratchet is proven by injecting a FRESH key derived from the pattern's own shape.
        rx = re.compile(pattern, re.M)
        m = rx.search(base_text) or rx.search(cur_text)
        if m is None:
            # nothing matches anywhere — a vacuous census; state it rather than pass an untested gate.
            return False, ("ratchet: SELF-PROOF VACUOUS — the pattern matches nothing in the baseline "
                           "or current file, so the F-arm cannot be exercised; refusing to pass an "
                           "untested ratchet (name a pattern that matches, or the census is empty).")
        if as_set:
            # a fresh key: perturb the captured group's text so it is a NEW set element.  Rebuild the
            # matched text with the capture suffixed, so the whole line still matches the pattern.
            fresh = m.group(0).replace(m.group(1), m.group(1) + "ZZZprobe", 1)
            probe = base_text + "\n" + fresh
            caught = (m.group(1) + "ZZZprobe") in census(probe, pattern, as_set)[1] and \
                     bool(regressed(base, census(probe, pattern, as_set), grow))
        else:
            # a count census: injecting the exact matched text adds one countable match by construction.
            probe = base_text + "\n" + m.group(0)
            caught = bool(regressed(base, census(probe, pattern, as_set), grow))
    if not caught:
        return False, ("ratchet: SELF-PROOF FAIL — a synthetic regression against the baseline went "
                       "uncaught; the gate is unsound, refusing to pass.")

    return True, (f"ratchet: OK — census {_fmt(*cur)} of a baseline {_fmt(*base)}, may-only-{direction} "
                  f"holds (F-arm: a synthetic regression ({forbidden}) is caught)")


def main(argv) -> int:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--pattern", required=True)
    ap.add_argument("--set", dest="as_set", action="store_true")
    ap.add_argument("--grow", action="store_true")
    ap.add_argument("files", nargs="*")
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        print(__doc__, file=sys.stderr)
        return 2
    if len(a.files) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    base_text, cur_text = Path(a.files[0]).read_text(), Path(a.files[1]).read_text()
    ok, msg = check(base_text, cur_text, a.pattern, a.as_set, a.grow)
    print(msg, file=(sys.stdout if ok else sys.stderr))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
