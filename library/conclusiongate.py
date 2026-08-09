#!/usr/bin/env python3
"""library/conclusiongate.py — Λ·conclusion·backed: gate PRINTED conclusions on ASSERTIONS.

The check apparatus covers LANDED CLAIMS: every one carries a command that must pass.  Printed
reasoning carries nothing.  An analysis script prints a conclusion beside output from the same run
that refutes it, and nothing in the gate notices, because the conclusion was never a claim.

No amount of re-reading closes that set — a stochastic process needs a mechanical gate.  This is
one: in an analysis script, a line that PRINTS a conclusion must be backed by an ASSERTION that
would fail if the conclusion were false.  Conclusions are recognised by their markers ("=>",
"therefore", "so the", "which means"); backing is any assert in the same script whose expression
mentions a name the conclusion's own computation binds.

    python3 conclusiongate.py FILE.py [FILE.py ...]   # gate scripts
    python3 conclusiongate.py --demo                  # show the shapes it catches

DELIBERATELY WEAK IN ONE DIRECTION, STRONG IN THE OTHER.  It cannot tell whether an assertion is
the RIGHT one, only that a conclusion was staked with NOTHING behind it.  That is the failure it
was built for, and the asymmetry is the design: a gate that tried to judge relevance would have to
be right about meaning, and would fail open when it was not.  A conclusion naming no computed value
at all passes — pure prose is outside its reach, and it says so rather than guessing.

WHERE IT SITS.  In library/, beside the other machinery a concept witness imports — the
`conclusion-backed` concept exercises it, and the hermetic sandbox stages only what library's
BUILD manifest lists, so a module a witness imports must live where the manifest can name it.
Its SIBLING in spirit is cotype/check.py (which holds the ledger's entries monotone): both gate
REASONING rather than claims, and neither is a paperkit check verb — they are the layer that
keeps the record honest before anything reaches the bib.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# English-prose heuristics, not domain vocabulary — pass your own to gate()/findings() to tune.
#
# `conclusion` is the LOOSEST of the eight: the others are connectives that only appear when
# something is being inferred, but this one is a bare noun, so any script that REPORTS ON reasoning
# emits it without staking anything.  This module is the reference case — it flags its own report
# strings — which is why the list is a parameter.  A false positive here costs an argument;
# dropping the marker would cost the plainest phrasing there is ("conclusion: X"), so it stays in
# the default and callers whose subject matter IS conclusions pass PROSE_MARKERS instead.
MARKERS = ("=>", "therefore", "so the ", "which means", "so it is",
           "the answer", "conclusion", "it follows")

# The default minus the bare noun — for scripts that write ABOUT conclusions rather than staking any.
PROSE_MARKERS = tuple(m for m in MARKERS if m != "conclusion")

_WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


def conclusion_lines(src: str, markers=MARKERS) -> list[tuple[int, str]]:
    """Printed lines that stake a conclusion."""
    out = []
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            continue
        text = " ".join(
            a.value if isinstance(a, ast.Constant) and isinstance(a.value, str)
            else (ast.get_source_segment(src, a) or "")
            for a in node.args)
        if any(m in text.lower() for m in markers):
            out.append((node.lineno, text.strip()[:78]))
    return out


def assertions(src: str) -> list[tuple[int, str]]:
    return [(n.lineno, ast.get_source_segment(src, n.test) or "")
            for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Assert)]


def bound_names(src: str) -> set[str]:
    """Names the script binds — the vocabulary a conclusion can be ABOUT."""
    out = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            out.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.add(n.name)
    return out


def findings(src: str, markers=MARKERS) -> dict:
    """The verdict as DATA — `{conclusions, assertions, unbacked, ungated}`.

    Separated from reporting so a caller can consume the result (a witness asserting over it, a
    ledger recording it) instead of parsing printed lines."""
    concl, asserts, names = conclusion_lines(src, markers), assertions(src), bound_names(src)
    out = {"conclusions": concl, "assertions": asserts, "unbacked": [], "ungated": False}
    if not concl:
        return out
    if not asserts:
        out["ungated"] = True                       # conclusions staked, no assertion anywhere
        return out
    for ln, text in concl:
        subj = {w for w in _WORD.findall(text) if w in names}
        if not subj:
            continue                                # pure prose — the weak direction, by design
        if not any(subj & set(_WORD.findall(a)) for _l, a in asserts):
            out["unbacked"].append((ln, text, sorted(subj)[:4]))
    return out


def gate(path: Path, markers=MARKERS, report=True) -> int:
    """0 = every conclusion naming a computed value is backed; 1 = at least one is not."""
    f = findings(path.read_text(), markers)
    if report:
        print(f"   {path.name}: {len(f['conclusions'])} conclusion(s), "
              f"{len(f['assertions'])} assertion(s)")
    if not f["conclusions"]:
        if report:
            print("   no conclusions staked — nothing to gate")
        return 0
    if f["ungated"]:
        if report:
            print(f"   UNGATED: {len(f['conclusions'])} conclusion(s) with NO assertion in the script")
            for ln, t in f["conclusions"][:6]:
                print(f"      line {ln}: {t}")
        return 1
    if f["unbacked"]:
        if report:
            print(f"   UNBACKED: {len(f['unbacked'])} conclusion(s) name a computed value "
                  f"that no assertion touches")
            for ln, t, s in f["unbacked"][:6]:
                print(f"      line {ln}: {t}")
                print(f"         names {s} — absent from every assert")
        return 1
    if report:
        print("   all conclusions naming a computed value are backed by an assertion")
    return 0


DEMO_BAD = '''
rows = [(1, 2), (1, 2)]
ties = sum(1 for a, b in rows if a == b)
print(f"ties found: {ties}")
print("=> the two are history-dependent")
'''

DEMO_GOOD = '''
rows = [(1, 2), (1, 3)]
ties = sum(1 for a, b in rows if a == b)
print(f"ties found: {ties}")
assert ties == 0, "a tie appeared"
print("=> the ties count is zero, so no dependence is shown")
'''


def demo() -> int:
    import tempfile
    for label, code in (("a conclusion with no backing", DEMO_BAD),
                        ("the same conclusion, backed", DEMO_GOOD)):
        p = Path(tempfile.mkdtemp()) / "s.py"
        p.write_text(code)
        print(f"\n   {label}:")
        gate(p)
    return 0


def main(argv) -> int:
    if "--demo" in argv or not argv:
        return demo()
    return max(gate(Path(a)) for a in argv if not a.startswith("-"))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
