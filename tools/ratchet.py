#!/usr/bin/env python3
r"""ratchet — a reusable paydown-only census gate: a set may only SHRINK, never grow.

The shape a prohibition takes as a check.  A flag saying "the predecessor did X and it broke" is
a prohibition on returning to X; spelled as a checkable proposition it is "the census of X may
only shrink."  cotype/check.py is one instance (ledger entry-keys never vanish — a monotone-GROW
variant); substrate runs fourteen bespoke ones, summit one.  Every project reimplementing the
census is a graded census rebuilt locally, waiting to drift — so the ENGINE owns the mechanism
(extract a census, compare to a committed baseline, refuse a regression) and the PROJECT declares
the POLICY: which pattern is the census, and which direction is the ratchet.

The census is whatever the project points at: the count of matches of a regex (occurrences of a
forbidden construct), or the SET of keys the regex captures (a group-1 capture makes it a
set-shrink rather than a count-shrink).  The baseline is a committed file; the current file must
not regress against it.

Two properties this floor earned and every ratchet must carry:
  n OF m, never a bare count.  The verdict NAMES the baseline it read (`34 of a baseline 86`),
    because a census reporting a bare total is how a snapshot gets counted as live corpus.
  A T-ARM AND AN F-ARM.  A scan whose all-clear has never been shown to differ from its
    found-something is not a measurement — so every run PROVES its own ⟨P,F,δ⟩ on in-memory
    copies (never the tree): a synthetic regression against the baseline MUST be caught, or the
    gate refuses to pass (unsound).

    python3 tools/ratchet.py --pattern <regex> [--set] [--grow] [--replace OLD=NEW]...
                             <baseline-file> <current-file>
      --pattern  the census: a Python regex.  Without --set the census is the COUNT of matches;
                 with --set it is the SET of the regex's group-1 captures (a keyed census).
      --set      census is the captured-key SET (may-only-shrink as a set); default is the
                 match COUNT.
      --grow     invert the ratchet to may-only-GROW (an append-only ledger: nothing may
                 vanish).  Default is may-only-SHRINK (a paydown census: nothing may be added).
      --replace  repeatable; renames one BASELINE key before the comparison, so a refactor that
                 moves a key without changing coverage is paid as one AUDITABLE line instead of
                 a bulk re-baseline (which would also swallow a genuinely new gap).  Cardinality
                 is preserved, so a swap can never enlarge the allowance.  SET census only; a
                 stale `OLD` or an already-present `NEW` is REFUSED, never applied quietly.
    exit 0 = the ratchet holds (+ the F-arm self-proof passes); 1 = a regression (named) or a
    swap that describes no real move; 2 = usage.

⚑ THE CENSUS IS A TYPE, NOT A `(kind, value)` TUPLE.  An untyped pair is where `Any` enters and
fans out: every consumer unpacks it, every unpacked half is `Any`, and the narrowing that should
happen once at the boundary happens nowhere.  `Census` is a frozen discriminated union — `kind`
is a `Literal`, and the two payload slots are exclusive by construction — so the sum type is
stated where it is CREATED and every reader gets a real type without narrowing it again.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

_PROBE_SUFFIX = "ZZZprobe"      # the F-arm's synthetic key: absent from any real census
_ARGC = 2                       # baseline + current; a positional count, not a magic number


@dataclass(frozen=True)
class Census:
    """Hold one census reading: the captured-key SET, or the match COUNT.

    Exactly one payload is meaningful, discriminated by `kind` — so a reader never inspects the
    slot it was not given.
    """

    kind: Literal["set", "count"]
    keys: frozenset[str]
    count: int

    def describe(self) -> str:
        """Render the n-of-m half of a verdict: `6 keys`, or a bare total."""
        return f"{len(self.keys)} keys" if self.kind == "set" else str(self.count)


def census(text: str, pattern: str, *, as_set: bool) -> Census:
    """Take the census of `text` under `pattern`.

    The SET of group-1 captures (as_set), or the multiset COUNT of matches.
    """
    # ⚑ NARROWED AT THE EDGE.  `findall` is typed `list[Any]` (its element shape depends on the
    # pattern's group count, which is not knowable statically), so the Any stops HERE — a
    # group-1 census is str-keyed by construction, and carrying the Any inward would poison
    # every consumer of Census.
    rx = re.compile(pattern, re.MULTILINE)
    found: list[str] = [str(g) for g in cast("list[object]", rx.findall(text))]
    if as_set:
        return Census(kind="set", keys=frozenset(found), count=0)
    return Census(kind="count", keys=frozenset(), count=len(found))


def regressed(base: Census, cur: Census, *, grow: bool) -> list[str] | int:
    """Report the regression, if any, of `cur` vs `base` under the ratchet direction.

    For a SET census: (shrink) the keys ADDED, or (grow) the keys REMOVED.  For a COUNT: the
    signed overage.  Truthy describes the regression; a falsey empty value means it holds.
    """
    if base.kind != cur.kind:
        msg = "baseline and current census kinds differ"
        raise ValueError(msg)
    if base.kind == "set":
        # shrink ⇒ nothing may be ADDED; grow ⇒ nothing may be REMOVED.
        return sorted(base.keys - cur.keys) if grow else sorted(cur.keys - base.keys)
    # count: shrink ⇒ cur may not exceed base; grow ⇒ cur may not fall below base.
    over = (base.count - cur.count) if grow else (cur.count - base.count)
    return max(0, over)


def parse_replacement(spec: str) -> tuple[str, str]:
    """Split `old=new` into its two halves.

    A missing `=`, or an empty half, is a usage error: a mis-split spec would swap a key for the
    empty string and read as a paydown.
    """
    old, sep, new = spec.partition("=")
    if not sep or not old or not new:
        msg = f"--replace expects old=new, got {spec!r}"
        raise ValueError(msg)
    return old, new


def apply_replacements(base: Census, repl: Sequence[tuple[str, str]]) -> Census:
    """Rename baseline keys, one OUT and one IN per swap.

    CARDINALITY is preserved by construction, so no swap can enlarge the allowance.

    A swap is a DECLARED rename.  A keyed census over source positions (a qualname, a `#n`
    ordinal) churns on refactors that change no coverage: rename the def, or insert a branch
    above an existing one, and the key moves while the gap does not.  The alternatives are both
    worse — re-cutting the baseline is an unreviewed bulk overwrite that also swallows any
    genuinely NEW gap, and a COUNT census immune to renames is a scalar collapse of a richer
    reading (it reports that something regressed, never which).  So the key moves EXPLICITLY, one
    auditable line per rename, and the aggregate cannot worsen.

    Ν·loud on a swap that does not describe a real move.  `old` absent from the baseline is a
    stale rename (already paid down, or never there) and admitting `new` for it would GROW the
    allowance under cover of a refactor; `new` already present would DROP one key, hiding a real
    paydown as a rename and banking a slot of unearned headroom.  Both raise.

    SET only: a count has no keys to swap, so this would silently do nothing — REFUSED rather
    than no-opped, because a flag that reads as applied and did nothing is the silent-degradation
    shape this tool exists to refuse.
    """
    if base.kind != "set":
        msg = "--replace needs a keyed (--set) census; a count has no keys to swap"
        raise ValueError(msg)
    out = set(base.keys)
    for old, new in repl:
        if old not in out:
            msg = (f"--replace {old}={new}: {old!r} is not in the baseline census "
                   "(a stale rename — admitting its replacement would GROW the allowance)")
            raise ValueError(msg)
        if new in out:
            msg = (f"--replace {old}={new}: {new!r} is ALREADY in the baseline census "
                   "(the swap would shrink it by one, hiding a paydown as a rename)")
            raise ValueError(msg)
        out.discard(old)
        out.add(new)
    return Census(kind="set", keys=frozenset(out), count=0)


@dataclass(frozen=True)
class Policy:
    """Carry what the PROJECT declares: the census pattern, and the ratchet's direction.

    One object rather than four positionals — the parameters travel together through every layer,
    and a bare `(pattern, as_set, grow, repl)` tuple at each call site is where an argument gets
    transposed silently.
    """

    pattern: str
    as_set: bool = False
    grow: bool = False
    repl: tuple[tuple[str, str], ...] = ()


def _self_proof(base: Census, base_text: str, cur_text: str, policy: Policy) -> bool | None:
    """Prove the F arm on an in-memory copy, never the tree.

    A SYNTHETIC regression against `base` MUST be caught, or the gate is unsound.  δ = one census
    element.  True (caught), False (uncaught — unsound), or None when the pattern matches nothing
    anywhere, which is a VACUOUS census the caller must report rather than pass.
    """
    if policy.grow:
        m = re.compile(policy.pattern, re.MULTILINE).search(base_text)
        # drop one baseline element → must be caught
        probe = base_text.replace(str(m.group(0)), "", 1) if m else base_text
        return bool(regressed(base, census(probe, policy.pattern, as_set=policy.as_set),
                              grow=policy.grow))
    # inject a synthetic match the census will COUNT/CAPTURE.  Re-use a match from the baseline
    # itself so the pattern is guaranteed to match the injected line; for a keyed (--set) census
    # a bare re-inject of the same key does not grow the SET (it is already present), so a keyed
    # shrink-ratchet is proven by injecting a FRESH key derived from the pattern's own shape.
    rx = re.compile(policy.pattern, re.MULTILINE)
    m = rx.search(base_text) or rx.search(cur_text)
    if m is None:
        return None
    # `Match.group` is typed `str | Any` (a group may be optional); narrowed here, at the edge.
    whole = str(m.group(0))
    if policy.as_set:
        # a fresh key: perturb the captured group's text so it is a NEW set element.  Rebuild the
        # matched text with the capture suffixed, so the whole line still matches the pattern.
        captured = str(m.group(1))
        fresh_key = captured + _PROBE_SUFFIX
        probe = base_text + "\n" + whole.replace(captured, fresh_key, 1)
        probed = census(probe, policy.pattern, as_set=policy.as_set)
        return fresh_key in probed.keys and bool(regressed(base, probed, grow=policy.grow))
    # a count census: injecting the exact matched text adds one countable match by construction.
    probe = base_text + "\n" + whole
    return bool(regressed(base, census(probe, policy.pattern, as_set=policy.as_set),
                          grow=policy.grow))


def check(base_text: str, cur_text: str, policy: Policy) -> tuple[bool, str]:
    """Run the ratchet, returning (ok, message) with its n-of-m verdict and F-arm self-proof.

    `ok` is False on a real regression OR on a failed self-proof — an unsound ratchet must not
    pass.

    `policy.repl` renames baseline keys BEFORE the comparison, so the ratchet the F-arm proves is
    the ratchet that actually ran — a self-proof against the UNSWAPPED baseline would certify a
    gate no one invoked.
    """
    base = census(base_text, policy.pattern, as_set=policy.as_set)
    if policy.repl:
        base = apply_replacements(base, policy.repl)
    cur = census(cur_text, policy.pattern, as_set=policy.as_set)
    direction = "grow" if policy.grow else "shrink"
    forbidden = "removed" if policy.grow else "added"

    reg = regressed(base, cur, grow=policy.grow)
    if reg:
        detail = ("\n".join(f"  - {k}" for k in reg) if isinstance(reg, list)
                  else f"  census {cur.describe()} vs a baseline {base.describe()} — "
                       f"{reg} over the ratchet")
        return False, (f"ratchet: FAIL — the census {forbidden} against its baseline (may-only-"
                       f"{direction}); {cur.describe()} vs a baseline {base.describe()}:\n"
                       f"{detail}")

    caught = _self_proof(base, base_text, cur_text, policy)
    if caught is None:
        return False, ("ratchet: SELF-PROOF VACUOUS — the pattern matches nothing in the "
                       "baseline or current file, so the F-arm cannot be exercised; refusing to "
                       "pass an untested ratchet (name a pattern that matches, or the census is "
                       "empty).")
    if not caught:
        return False, ("ratchet: SELF-PROOF FAIL — a synthetic regression against the baseline "
                       "went uncaught; the gate is unsound, refusing to pass.")

    return True, (f"ratchet: OK — census {cur.describe()} of a baseline {base.describe()}, "
                  f"may-only-{direction} holds "
                  f"(F-arm: a synthetic regression ({forbidden}) is caught)")


def main(argv: Sequence[str]) -> int:
    """Parse the policy, read both files, run the ratchet."""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--pattern", required=True)
    ap.add_argument("--set", dest="as_set", action="store_true")
    ap.add_argument("--grow", action="store_true")
    empty: list[str] = []
    ap.add_argument("--replace", action="append", default=empty, metavar="OLD=NEW")
    ap.add_argument("files", nargs="*")
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        print(__doc__, file=sys.stderr)
        return 2
    # ⚑ THE OTHER UNTYPED EDGE.  Every `Namespace` attribute is `Any`; each is narrowed HERE, so
    # `Policy` downstream is fully typed and no Any reaches the mechanism.
    files: list[str] = [str(f) for f in cast("list[object]", a.files)]
    if len(files) != _ARGC:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        repl = tuple(parse_replacement(str(s)) for s in cast("list[object]", a.replace))
    except ValueError as e:
        print(f"ratchet: {e}", file=sys.stderr)
        return 2
    policy = Policy(pattern=str(cast("object", a.pattern)),
                    as_set=bool(cast("object", a.as_set)),
                    grow=bool(cast("object", a.grow)), repl=repl)
    base_text, cur_text = Path(files[0]).read_text(), Path(files[1]).read_text()
    try:
        ok, msg = check(base_text, cur_text, policy)
    except ValueError as e:
        # a swap that describes no real move — refused LOUD, never applied quietly.
        print(f"ratchet: FAIL — {e}", file=sys.stderr)
        return 1
    print(msg, file=(sys.stdout if ok else sys.stderr))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
