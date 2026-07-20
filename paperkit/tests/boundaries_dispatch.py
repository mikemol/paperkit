#!/usr/bin/env python3
"""Λ·registry·gate — the VERB SET's boundary: one owner, every dispatch site derived from it.

A check type is not MIGRATED when its verdict works; it is migrated when EVERY site that
dispatches on check type has been migrated.  paperkit has five such sites, and they used to
carry five independent hardcoded lists — so adding `concept:` updated some and silently missed
others.  The misses were invisible: `//:hook` grades concept: through the Bazel certificate
import, so the direct-CLI grade path stayed wrong while every gate read green, and the footprint
audit kept stracing a whole library witness because its skip-set still read `result:` alone.

resolver.VERBS is now the one declaration, and `crosses` is the bit the sites actually branch on
(does this verb resolve against something ANOTHER project owns and separately gates?).  This
check asserts every site agrees with the datum — behaviorally where the site is Python, by
set-equality over source where it is Starlark.

    python3 paperkit/tests/boundaries_dispatch.py     # exit 0 = every site derives from VERBS
"""
from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
ROOT = ENGINE.parent
sys.path.insert(0, str(ENGINE))

import grader  # noqa: E402
import resolver  # noqa: E402

BIBTEX_SRC = (ROOT / "tools" / "bibtex.bzl").read_text()
FOOTDEPS_SRC = (ENGINE / "footdeps.py").read_text()
CROSSING = {v for v, s in resolver.VERBS.items() if s["crosses"]}
LOCAL = set(resolver.VERBS) - CROSSING


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("Λ·registry — the verb set's dispatch boundary\n")
    print("⟨one owner⟩\n")
    check("resolver.VERBS declares the built-in set, and every entry is fully specified",
          bool(resolver.VERBS) and all(
              {"arg", "verb", "passes", "crosses"} <= set(s) for s in resolver.VERBS.values()))
    check(f"the crossing verbs are DERIVED, not re-listed: {', '.join(sorted(CROSSING))}",
          set(resolver.CROSSING) == {f"{v}:" for v in CROSSING} and bool(CROSSING))

    print("\n⟨every site derives⟩\n")
    # 1. the VERDICT path — every declared verb reaches a real branch.  An unknown TARGET under a
    #    declared verb resolves False (ran, failed); an undeclared TYPE also returns False but is
    #    refused, so the discriminating assertion is that no verb RAISES and the set stays closed.
    dispatched = all(
        resolver.resolves(f"{v}:no-such-target-{v}", ENGINE, {}) is False for v in resolver.VERBS)
    check("resolver.resolves dispatches every declared verb (no fallthrough, no raise)", dispatched)
    check("the built-in set is CLOSED — an undeclared type does not resolve",
          resolver.resolves("nosuchverb:x", ENGINE, {}) is False)

    # 2. the FOOTPRINT command — file: opens only its target (None); every other verb runs something.
    cmds = {v: resolver._check_cmd(f"{v}:t", {}) for v in resolver.VERBS}
    check("resolver._check_cmd covers every verb (None only for the verb that runs nothing)",
          cmds["file"] is None and all(c for v, c in cmds.items() if v != "file"))

    # 3. the GRADE path — a crossing verb is DELEGATED to its owner, never swept locally.  This is
    #    the one that was silently wrong: a missing arm falls through to a local sweep, which cannot
    #    see a witness outside this project's mutation surface and can only read `indeterminate`.
    for v in sorted(CROSSING):
        rec = grader.grade_check(f"{v}:t", ROOT, set(), {}, ROOT)
        check(f"grader.grade_check delegates {v}: (crosses=True → imported, not a local sweep)",
              rec.get("grade") == "imported")
    # ...and a LOCAL verb must NOT be delegated: stamping `imported` on a check this project owns
    # would assert a grade nothing ever measured.  Read the arms out of grade_check itself, so the
    # assertion is set-EQUALITY against VERBS rather than a list maintained here.
    src = inspect.getsource(grader.grade_check)
    chunks = re.split(r'\n    if typ == "(\w+)":', src)
    delegated = {chunks[i] for i in range(1, len(chunks), 2)
                 if '"grade": "imported"' in chunks[i + 1]}
    check(f"delegation is EXACTLY the crossing set (grade_check delegates {delegated or '{}'})",
          delegated == CROSSING)

    # 4. the FOOTPRINT AUDIT — skips exactly the crossing verbs, by asking the verb.  Count the
    #    code SHAPE (`startswith(resolver.CROSSING)`), never a bare substring: a mention in a
    #    comment would inflate the tally, and a magic expected-count is the very defect at issue.
    skips = FOOTDEPS_SRC.count("startswith(resolver.CROSSING)")
    hardcoded = re.findall(r'startswith\(\s*[\'"](\w+):', FOOTDEPS_SRC)
    check(f"footdeps' {skips} skip sites ask resolver.CROSSING, and none hardcodes a verb"
          + (f" (found {hardcoded})" if hardcoded else ""),
          skips >= 2 and not hardcoded)

    # 5. the GENERATOR — Starlark cannot import the engine, so assert by set-equality over source
    #    that every crossing verb is wired to a cross-repo RECORD dep, and no local verb is.
    for v in sorted(CROSSING):
        check(f"tools/bibtex.bzl branches on {v}: (a cross-repo record dep, not a local action)",
              f'startswith("{v}:")' in BIBTEX_SRC)
    check("...and skips their local footprint, as footdeps does",
          all(f'"{v}:"' in BIBTEX_SRC for v in CROSSING) and "no local footprint" in BIBTEX_SRC)

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    # The exact drift that shipped: a new crossing verb whose skip-set was never updated.  F is
    # built by reverting footdeps to the hardcoded literal — one token — and must be CAUGHT.
    f_src = FOOTDEPS_SRC.replace("startswith(resolver.CROSSING)", 'startswith("result:")')
    caught = (not re.findall(r'startswith\(\s*[\'"](\w+):', FOOTDEPS_SRC)
              and re.findall(r'startswith\(\s*[\'"](\w+):', f_src) == ["result"] * skips)
    fails.append("dispatch-delta") if not caught else None
    print(f"  {'ok ' if caught else 'XX '}re-hardcoding footdeps' skip-set to `result:` is CAUGHT")
    print("      P (intact):  footdeps asks resolver.CROSSING → concept: is skipped by construction")
    print("      F (reverted): the literal returns → concept: is straced, a whole library witness reruns")
    print("      δ (min delta): one token, `resolver.CROSSING` → `\"result:\"`\n")

    if fails:
        print(f"DISPATCH: FAIL ({len(fails)} sites drifted from resolver.VERBS)")
        return 1
    print(f"DISPATCH: PASS ({len(resolver.VERBS)} verbs, {len(CROSSING)} crossing, 5 sites, 1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
