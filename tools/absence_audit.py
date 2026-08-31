#!/usr/bin/env python3
"""absence_audit.py — refuse an unverified "nothing gates this" claim.

⚑ ADOPTED, NOT INVENTED.  This is an instance of mat260's `watchword-audit` capability —
*"a Stop hook fails the turn when an agent asserts a limitation or an absence it never checked:
watchword × context × search-evidence as three independent regexes"* — not a second
implementation of it.  The transcript-walking machinery is mat260's, HELD HERE as code rather
than symlinked, because only the three regexes differ and editing a shared inode would rewrite
linux-sources' and memmesh's hooks (the write-through hazard this repo gates as
`bnd-write-atomic`).  freecell, linux-sources, memmesh and cassian adopted it the same way for
their own domains; this is the sixth instance.  **Ownership is not claimed.**

⚑ WHY THIS REPO NEEDS IT, AND WHY THE NEED IS EMBARRASSING.  paperkit's central type is a
TRISTATE — PASS / UNAVAILABLE / FAIL — and `resolver.Verdict`'s docstring exists to refuse
exactly one fold: *"UNAVAILABLE means the check could not be EVALUATED ... across a repo
boundary that must NOT read as a REFUTATION"*.  The engine will not let a check say "I could not
run it" and have that scored as "it is false".  The agent working on the engine did precisely
that fold four times in one session (2026-08-28):

  1. a hand-rolled regex census reported 2 suites hardcoding a count; the true answer is 4 —
     the pattern required `behavio|arm|check` and missed `PASS (6 structural, 1 delta)`.
  2. "`as = image` appears nowhere" — relayed from an agent; `as =` appears twice.
  3. "`result:` selects which stored verdict to read out" — read the DISPATCH site and never
     opened `gate.py`'s `v = resolves(F[only]["check"], ...)`, which resolves it LIVE.
  4. "the generator produced a broken BUILD instead of refusing" — asserted from reading
     generated output, never from testing the hypothesis it blamed.

Each is "my query did not find it" scored as "it is not there".  The engine refuses that fold
in its own verdicts and had no layer that could refuse it in the agent's prose.

⚑ AND THE SEARCH THAT CLEARS A CLAIM HERE IS A MUTATION, NOT A GREP.  Upstream clears on an
exhaustive filesystem sweep; that is the WRONG evidence in this tree, because the question a
paperkit absence claim asks is almost always *"can this check fail?"* — and a grep cannot answer
it.  `Λ·audit·provenance` already states the rule: *mutate the mechanism out, don't source-scan*.
A witness that survives its own δ is VACUOUS however many greps agree with it, and both vacuous
witnesses caught on 2026-08-28 were caught by mutating, after passing inspection.

Weakness, stated: this greps the assistant's TEXT for an absence claim and the turn's TOOL CALLS
for clearing evidence.  It cannot tell a SOUND mutation from a mis-aimed one — the first δ tried
that day mutated `coherence.structure_residual`, a function the witness under test never calls,
and would have cleared this gate.  It refuses the unexamined claim, not the under-examined one.

Usage:
  absence_audit.py --transcript PATH   # audit the last turn
  echo '<hookjson>' | absence_audit.py # Stop-hook mode
  absence_audit.py --selftest          # prove it can SEE what it looks for
Exit: 0 clean, 2 if an unverified absence claim is found.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# ⚑ THE WATCHWORDS ARE ABSENCE PHRASINGS, and the dangerous ones are the CONFIDENT ones.
# These are the verdicts a queue/warrant audit reaches for, each of which asserts about the
# ENGINE what a query can only assert about ITSELF.  "UNAVAILABLE" and "cannot-run" are
# deliberately NOT here: they are the correct forms and must never be flagged.
WATCHWORDS = re.compile(
    r"\b(nothing (?:gates|asserts|checks|witnesses|covers|reads|calls|invokes)|"
    r"no (?:warrant|claim|check|witness|gate|owner|bib entry|caller|consumer) (?:covers|asserts|"
    r"names|exists|reads|invokes)|"
    r"(?:is|are|grades?) vacuous|cannot (?:fail|red|flip)|can'?t (?:fail|red|flip)|"
    r"unwarranted|ungated|unwitnessed|un(?:der)?tested|"
    r"does(?:n'?t| not) exist|there is no \w+|there'?s no \w+|no such (?:verb|key|field|claim|"
    r"warrant|target|rule)|never (?:runs|ran|fires|fired|invoked)|"
    r"already gated|already covered|duplicate of|"
    r"the engine (?:does(?:n'?t| not)|has no|lacks)|not implemented|"
    r"tautolog\w*|dangling|silently (?:drops|passes|skips))",
    re.IGNORECASE)

# A watchword only matters when the claim is ABOUT the engine or its claim-DAG.
CONTEXT = re.compile(
    r"warrant|claim|witness|bib\b|check\b|gate\b|verdict|grade|vacuous|behavioral|"
    r"concept:|result:|cmd:|file:|agree:|sweep|mutation|delta|\bdcalc\b|adequacy|"
    r"resolver|projector|paperkit|\.bib\b|boundaries_|//:hook|bazel|dep_order|rests-on",
    re.IGNORECASE)

# ⚑ CLEARING EVIDENCE IS A MUTATION OR THE OWNING TOOL, never a textual sweep.
# `Λ·audit·provenance`: mutate the mechanism out, don't source-scan.  A grep cannot answer
# "can this check fail?", which is what a paperkit absence claim almost always asks.
SEARCH = re.compile(
    r"bazel\s+(?:test|build|query|cquery)|"                 # the owning build system
    r"paperkit/gate\.py|paperkit/discriminate\.py|paperkit/project\.py|"
    r"tools/(?:read_grade|sens|def_sites|closure|imports|effective|decisions)\.py|"
    r"checks/\w+\.py|boundaries_\w+\.py|concepts\.py\s+\S|"  # running a witness
    r"--check\b|--observe\b|--json\b|--only\b|--prove\b|--selftest\b|"
    r"(?:cp|rsync)\s+-r?[a-z]*\s+\S*paperkit|mkdtemp|scratchpad/fx|"  # a mutation fixture
    r"sed\s+-i|\.replace\(|git\s+checkout\s+\S+\.py",  # the δ itself
    re.IGNORECASE)

LOG = Path(os.environ.get("ABSENCE_AUDIT_LOG",
                          Path.home() / ".claude" / "absence-audit.log"))


def rows(path: str) -> list:
    return [json.loads(ln) for ln in open(path) if ln.strip()]


def is_user(r: dict) -> bool:
    return r.get("type") == "user" or (r.get("message", {}) or {}).get("role") == "user"


def last_turn(rs: list) -> list:
    start = 0
    for i, r in enumerate(rs):
        if is_user(r):
            start = i
    return rs[start:]


def scan_turn(turn: list) -> tuple[str, bool]:
    """(assistant text asserted this turn, whether an owning tool was invoked).

    Reads the assistant's TEXT — what it asserts to a peer — and the turn's TOOL CALLS.
    Thinking is not scanned: a hypothesis considered is not a claim made.
    """
    texts, searched = [], False
    for r in turn:
        cs = (r.get("message", r) or {}).get("content")
        if not isinstance(cs, list):
            continue
        for c in cs:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "text":
                texts.append(c.get("text", ""))
            elif c.get("type") == "tool_use":
                blob = c.get("name", "") + " " + json.dumps(c.get("input", {}) or {})
                if SEARCH.search(blob):
                    searched = True
    return "\n".join(texts), searched


def flags_in(text: str) -> list:
    out = []
    for line in text.splitlines():
        if not CONTEXT.search(line):
            continue
        # ⚑ A LINE THAT ALREADY SAYS UNAVAILABLE IS THE CORRECT FORM, NOT A VIOLATION.
        # Without this the audit would flag its own remedy, which is the predicate-matches-
        # its-own-documentation defect this tree has hit three times.
        if re.search(r"\bUNAVAILABLE\b", line):
            continue
        for m in WATCHWORDS.finditer(line):
            out.append((m.group(0), line.strip()[:140]))
    return out


def report(flags: list) -> int:
    msg = ("absence-audit — an absence was asserted this turn with NO invocation of the tool "
           "that owns the question. This corpus can say UNAVAILABLE (not in this version / not "
           "fetched); it cannot say DOES NOT EXIST. Verify or requalify:\n"
           + "\n".join(f"  • {w!r}: {ln}" for w, ln in flags[:8]))
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as fh:
        fh.write(msg + "\n---\n")
    print(msg, file=sys.stderr)
    return 2


def selftest() -> int:
    """⚑ PROVE THE AUDIT SEPARATES ITS CASES — both arms, or it certifies nothing.

    An audit that flagged everything would look identical to a strict one, and an audit that
    flagged nothing would look identical to a clean tree.
    """
    arms = [
        # ⚑ THE T-ARMS ARE REAL CLAIMS MADE ON 2026-08-28, not invented fixtures.
        ("T: an unqualified 'nothing gates this' about a warrant is flagged",
         bool(flags_in("No warrant covers the WITNESSES dispatch table's domain."))),
        ("T: a vacuity verdict asserted without a mutation is flagged",
         bool(flags_in("That witness is vacuous — the check cannot fail under any delta."))),
        ("T: 'already gated' (the duplicate verdict) is flagged",
         bool(flags_in("This claim is already gated by bnd-verdict; the row is a duplicate."))),
        ("F: the same claim qualified as cannot-run is NOT flagged",
         not flags_in("The concept resolves to cannot-run here — UNAVAILABLE, not refuted.")),
        ("F: an absence claim with no engine context is NOT flagged",
         not flags_in("There is no meeting scheduled for Thursday.")),
        ("F: running a witness counts as clearing evidence",
         bool(SEARCH.search("python3 checks/claims.py depth-annotates-without-reordering"))),
        ("F: a mutation fixture counts as clearing evidence",
         bool(SEARCH.search("sed -i '203s/rests-on/from/' paperkit/genre.py"))),
        ("F: a bare recursive grep does NOT count — it is the refused move",
         not SEARCH.search("grep -rn 'rests-on' paperkit/")),
    ]
    for name, ok in arms:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    bad = [n for n, ok in arms if not ok]
    print(f"absence-audit --selftest: {'PASS' if not bad else 'FAIL'} "
          f"({len(arms) - len(bad)} of {len(arms)} arms)")
    return 1 if bad else 0


def main(argv: list) -> int:
    if "--selftest" in argv:
        return selftest()
    if "--files" in argv:
        bad = []
        for f in argv[argv.index("--files") + 1:]:
            try:
                bad += [(w, f"{f}: {ln}") for w, ln in flags_in(open(f).read())]
            except OSError:
                pass
        return report(bad) if bad else 0

    advisory = False
    if "--transcript" in argv:
        tpath = argv[argv.index("--transcript") + 1]
    else:
        # ⚑ HOOK MODE IS ADVISORY: it LOGS and returns 0. A regex over prose has false
        # positives, and a Stop hook that fails a turn on one would make the guard's cost
        # exceed its value — upstream reached the same disposition for the same reason.
        advisory = True
        try:
            tpath = json.load(sys.stdin).get("transcript_path")
        except Exception:
            return 0
    if not tpath or not Path(tpath).exists():
        return 0

    text, searched = scan_turn(last_turn(rows(tpath)))
    flags = flags_in(text)
    if flags and not searched:
        report(flags)
        return 0 if advisory else 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
