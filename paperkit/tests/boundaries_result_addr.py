#!/usr/bin/env python3
r"""Behavioral-boundary examples for Λ·reduce — `result:<project>[#<claim>]` PER-WARRANT delegation.

A claim naming a SPECIFIC sibling guarantee ("render gates PDF/UA") cannot honestly check the
sibling's whole gate.  Bare `result:render` is green only when EVERY render warrant holds — it
asserts far more than the importing claim needs — and red for a failure in an unrelated warrant.
Both directions are overclaims, so a claim that is finer than a project needed an address that is
finer than a project.

The sibling's gate ALREADY had that address: `--only`, the Ζ·starlark leaf.  What it lacked was an
ANSWER — the leaf returned before the --json block and reported through info() (suppressed under
--json), so a machine consumer saw an exit code and empty stdout.  It was addressable but MUTE.
This suite pins both halves: the leaf SPEAKS, and result: can address it.

The tristate is preserved end-to-end (ask-result-tristate): a claim key naming no check is a caller
BUG (_REFUSE), never a refutation of the importing claim — collapsing that to FAIL would make a
typo'd address look like a failing sibling.

⟨P, F, δ⟩ per the boundary practice.

Run:  python3 paperkit/tests/boundaries_result_addr.py
"""
from __future__ import annotations

import json
import shutil
import pathlib
import subprocess
import sys
import tempfile
from pathlib import Path

ENG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENG))
import resolver  # noqa: E402

GATE = str(ENG / "gate.py")


def _sib(tmp: Path, green: bool = True) -> Path:
    """A minimal sibling project 'g' with ONE claim `c`, green or red, plus a SECOND claim `d`
    that is always green — so a per-warrant address can be shown to differ from the whole gate."""
    g = tmp / "g"
    (g / "").mkdir(parents=True, exist_ok=True)
    (g / "paper.toml").write_text(
        '[paper]\ntitle = "t"\nwarrants = ["w.bib"]\nrubric = "r.tsv"\n'
        'out = "out.md"\nnumbered = false\nreferences = false\n')
    (g / "r.tsv").write_text("s\tSec\n")
    (g / "w.bib").write_text(
        "@misc{c,\n  section = {s}, claim = {a sibling claim},\n"
        f"  check = {{{'file:w.bib' if green else 'cmd:false'}}}\n}}\n"
        "@misc{d,\n  section = {s}, claim = {a second sibling claim},\n"
        "  check = {file:r.tsv}\n}\n")
    # c and d must not share a witness: --without-K forbids two cited claims collapsing onto one
    # (proof-irrelevance refused -- K-and-without-K-in-paperkit), and result: passes --without-K.
    # The WHOLE-project gate additionally enforces PROJECT (committed prose == the projection), so
    # the sibling must ship its out.md.  The --only leaf does NOT need it -- it returns before that
    # invariant -- which is itself the asymmetry this suite pins: the leaf answers about ONE claim,
    # the node answers about the document.  Built by running the projector (Φ: reuse the validated
    # path, do not hand-write prose that drifts when the format moves).
    subprocess.run([sys.executable, str(ENG / "project.py"), str(g)],
                   check=True, capture_output=True, text=True)
    return g


def _leaf(project: Path, claim: str) -> dict:
    """The sibling gate's --only leaf, as a machine consumer sees it."""
    r = subprocess.run([sys.executable, GATE, "--json", "--safe", "--without-K",
                        "--only", claim, str(project)],
                       capture_output=True, text=True)          # Λ·separate-filehandles
    return {"rc": r.returncode, "rec": json.loads(r.stdout or "{}")}


def _resolve(check: str, frm: Path) -> str:
    v = resolver.resolves(check, frm, {})
    return "cannot-run" if v.is_unavailable() else ("pass" if v.passed else "fail")


CASES = []


def case(name, axis, P, F, delta):
    CASES.append({"name": name, "axis": axis, "P": P, "F": F, "delta": delta})


def main() -> int:
    fails = []
    print("result: per-warrant addressing — ⟨P, F, δ⟩ examples\n")

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        here = tmp / "here"; here.mkdir()

        # ── 1. the leaf SPEAKS: pass / fail / refuse are three distinct machine-readable answers ──
        g_ok = _sib(tmp / "ok", green=True)
        g_bad = _sib(tmp / "bad", green=False)

        p = _leaf(g_ok, "c")
        f = _leaf(g_bad, "c")
        r = _leaf(g_ok, "no-such-key")

        checks = [
            ("leaf pass  → rc 0, available, pass",
             p["rc"] == 0 and p["rec"].get("available") is True and p["rec"].get("pass") is True, p),
            ("leaf fail  → rc 1, available, NOT pass",
             f["rc"] == 1 and f["rec"].get("available") is True and f["rec"].get("pass") is False, f),
            ("leaf refuse→ rc 3, NOT available (a typo'd key is a caller bug)",
             r["rc"] == 3 and r["rec"].get("available") is False, r),
            ("leaf names WHICH claim it answered (an answer without its question is unusable)",
             p["rec"].get("only") == "c" and p["rec"].get("check") == "file:w.bib", p),
        ]
        print("  ⟨leaf⟩ the --only leaf answers in machine-readable form")
        for label, ok, got in checks:
            print(f"    {'ok  ' if ok else 'FAIL'} {label}")
            if not ok:
                fails.append(f"{label} — got {got}")

        # ── 2. the ADDRESS discriminates: same sibling, two claims, different verdicts ──────────
        print("\n  ⟨address⟩ per-warrant delegation is FINER than the whole gate")
        rel_bad = Path("..") / g_bad.relative_to(tmp).parts[0] / "g"
        addr = [
            ("P: result:<sib>#d  → pass  (the named warrant holds)",
             _resolve(f"result:{rel_bad}#d", here), "pass"),
            ("F: result:<sib>#c  → fail  (the named warrant does not)",
             _resolve(f"result:{rel_bad}#c", here), "fail"),
            ("δ: result:<sib>    → fail  (whole gate: c reds it, so #d's truth is INVISIBLE)",
             _resolve(f"result:{rel_bad}", here), "fail"),
        ]
        for label, got, want in addr:
            ok = got == want
            print(f"    {'ok  ' if ok else 'FAIL'} {label:<62} got={got}")
            if not ok:
                fails.append(f"{label} — got {got}, want {want}")
        print("    δ is the POINT: #d is green while the project is red — bare result: cannot say so.")

        # ── 3. the tristate survives the address ────────────────────────────────────────────────
        print("\n  ⟨tristate⟩ cannot-run is preserved, never collapsed to fail")
        tri = [
            ("a claim key naming no check → cannot-run (caller bug, not a refutation)",
             _resolve(f"result:{rel_bad}#no-such-key", here), "cannot-run"),
            ("an unreachable sibling → cannot-run",
             _resolve("result:../nonexistent#c", here), "cannot-run"),
        ]
        for label, got, want in tri:
            ok = got == want
            print(f"    {'ok  ' if ok else 'FAIL'} {label:<62} got={got}")
            if not ok:
                fails.append(f"{label} — got {got}, want {want}")

        # ── 4. bare result: is UNCHANGED (the extension is additive) ────────────────────────────
        print("\n  ⟨compat⟩ the bare form keeps whole-project semantics")
        rel_ok = Path("..") / g_ok.relative_to(tmp).parts[0] / "g"
        got = _resolve(f"result:{rel_ok}", here)
        ok = got == "pass"
        print(f"    {'ok  ' if ok else 'FAIL'} result:<green sibling> → pass                        got={got}")
        if not ok:
            fails.append(f"bare result: on a green sibling — got {got}")

        # ── 5. the trace matches what RUNS (Λ·trace·quote) ──────────────────────────────────────
        print("\n  ⟨trace⟩ footprint's command is the command resolves() runs")
        cmd = resolver._check_cmd(f"result:{rel_bad}#c", {}, here)
        # shlex.quote leaves a shell-safe token BARE, so assert the address is CARRIED, and that a
        # metacharacter-bearing key would be QUOTED -- the injection seam Λ·trace·quote closed.
        nasty = resolver._check_cmd(f"result:{rel_bad}#a b;rm", {}, here)
        ok = ("--only" in cmd and " c " in f" {cmd} "
              and ("'a b;rm'" in nasty or '"a b;rm"' in nasty))
        print(f"    {'ok  ' if ok else 'FAIL'} traced command carries the --only address; a "
              f"metacharacter key is quoted")
        if not ok:
            fails.append(f"trace address/quoting: {cmd} || {nasty}")

    # ---- Ζ·result·seam: the target is a NAME, resolved consumer-first ----
    # The two paths disagreed on what the string IS: bibtex.bzl makes `result:render#k` a dep on
    # @paperkit_render//:k (a repo NAME), while the CLI appended it as a DIRECTORY with cwd set to
    # the CITING project — so `result:render` from talk/ looked for talk/render/paper.toml and all
    # five of talk's delegations came back UNAVAILABLE.  Same bib, same string, two meanings.
    # A SYNTHETIC tree, not this repo's.  The first version asserted
    # `_sibling_for(root/"talk", "render") == root/"render"` — true where talk/ and render/ are
    # on disk, FALSE in a sandbox staging only `reads = {.}`, where the lookup falls through to
    # the engine-relative fallback and resolves OUT of the sandbox to the real repo.  That is the
    # Λ·location mistake resolver.py:92-118 documents, and the arm asserting the fix reintroduced
    # it: the suite was testing the machine it ran on rather than the rule.
    _d = pathlib.Path(tempfile.mkdtemp())
    (_d / "sib").mkdir()
    (_d / "sib" / "paper.toml").write_text("[paper]\n")
    (_d / "citer").mkdir()
    for label, got, want in [
        ("a sibling NAME resolves to the sibling, not <citer>/<name>",
         resolver._sibling_for(_d / "citer", "sib"), (_d / "sib").resolve()),
        ("the same name resolves from the tree root too",
         resolver._sibling_for(_d, "sib"), (_d / "sib").resolve()),
        ("an unresolvable name is returned UNCHANGED (the gate reports its own cannot-run)",
         pathlib.Path(str(resolver._sibling_for(_d / "citer", "no-such-project"))),
         pathlib.Path("no-such-project")),
    ]:
        ok = got == want
        print(f"    {'ok  ' if ok else 'FAIL'} seam: {label}")
        if not ok:
            fails.append(f"seam {label}: got={got} want={want}")

    # Λ·location — the ladder must be CONSUMER-first.  Engine-relative alone is invisible in this
    # repo (every project sits beside the engine) and fatal outside it, where a downstream
    # `result:theirproject` would resolve into paperkit's own tree.
    try:
        (_d / "mine").mkdir()
        (_d / "mine" / "paper.toml").write_text("[paper]\n")
        ok = resolver._sibling_for(_d / "citer", "mine") == (_d / "mine").resolve()
        print(f"    {'ok  ' if ok else 'FAIL'} seam: a consumer's OWN sibling wins over the engine tree")
        if not ok:
            fails.append("seam: consumer-first ladder")
    finally:
        shutil.rmtree(_d, ignore_errors=True)

    print()
    if fails:
        print(f"result-addr boundaries: FAIL ({len(fails)})")
        for f_ in fails:
            print(f"  - {f_}")
        return 1
    print("result-addr boundaries: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
