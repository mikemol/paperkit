#!/usr/bin/env python3
"""Behavioral-boundary examples for emit: placement and the --safe postulate gate.

Per the boundary practice, every capability ships ⟨P, F, δ⟩: a minimal input it
passes, a minimal input it flags, and the minimum delta that flips the verdict.
This file bounds the engine surface added for README-as-projection:

  emit:     a warrant places a verbatim asset (fence inferred from extension);
            additive to a claim, so a healthy example stays CITED.
  --safe:   an uncited placement is a postulate — advised against by default,
            rejected under --safe (a zero-postulate document).

Both documentation (read it to see exactly where the lines fall) and a test
(run it; exit 0 iff every boundary holds).

    python3 paperkit/tests/boundaries_emit.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
PROJECT, GATE = ENGINE / "project.py", ENGINE / "gate.py"

PAPER_TOML = ('[paper]\ntitle = "t"\nwarrants = ["w.bib"]\nrubric = "r.tsv"\n'
              'out = "out.md"\nnumbered = false\nreferences = false\n')
RUBRIC = "s\tSec\n"


def entry(key, claim=None, emit=None, frm=None, check="file:w.bib"):
    fs = ["  section = {s}"]
    if frm:
        fs.append(f"  from = {{{frm}}}")
    if claim:
        fs.append(f"  claim = {{{claim}}}")
    if emit:
        fs.append(f"  emit = {{{emit}}}")
    fs.append(f"  check = {{{check}}}")
    return "@misc{%s,\n%s\n}\n" % (key, ",\n".join(fs))


def build(tmp, warrants, assets):
    proj = Path(tmp) / "proj"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "paper.toml").write_text(PAPER_TOML)
    (proj / "r.tsv").write_text(RUBRIC)
    (proj / "w.bib").write_text("".join(warrants))
    for name, content in assets.items():
        (proj / name).write_text(content)
    return proj


def projection(warrants, assets):
    with tempfile.TemporaryDirectory() as t:
        proj = build(t, warrants, assets)
        return subprocess.run([sys.executable, str(PROJECT), "-o", "-", str(proj)],
                              capture_output=True, text=True).stdout


def gate(warrants, assets, safe=False):
    with tempfile.TemporaryDirectory() as t:
        proj = build(t, warrants, assets)
        subprocess.run([sys.executable, str(PROJECT), str(proj)], capture_output=True)  # write out.md
        cmd = [sys.executable, str(GATE)] + (["--safe"] if safe else []) + [str(proj)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode, r.stderr


# warrants & assets used across cases
C = entry("c", claim="a cited claim")                                   # base prose
P_CITE = entry("p", claim="an example", emit="x.sh", frm="c", check="file:x.sh")  # derived term
P_POST = entry("p", emit="x.sh", frm="c", check="file:x.sh")            # postulate (no claim)
P_MD = entry("p", claim="an example", emit="x.md", frm="c", check="file:x.md")
SH = {"x.sh": "echo hi\n"}
MD = {"x.md": "| a | b |\n| - | - |\n"}
BOTH = {**SH, **MD}


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("emit / --safe behaviors\n")
    proj_sh = projection([C, P_CITE], SH)
    proj_md = projection([C, P_MD], MD)
    rc_post_default, err_default = gate([C, P_POST], SH, safe=False)
    check("emit places a fenced block, fence from extension (.sh)",
          "```sh" in proj_sh and "echo hi" in proj_sh)
    check("additive: the example is CITED ([@p] in prose)", "[@p]" in proj_sh)
    check(".md asset is a raw include (no code fence)",
          "| a | b |" in proj_md and "```" not in proj_md)
    check("uncited placement passes by default but raises a postulate advisory",
          rc_post_default == 0 and "postulate" in err_default)
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("postulate vs derived term (gate --safe)",
         "the claim field on the emit warrant",
         "claim+emit → exit 0", gate([C, P_CITE], SH, safe=True)[0] == 0,
         "emit only  → exit 1", gate([C, P_POST], SH, safe=True)[0] == 1),
        ("--safe toggles the postulate (same uncited placement)",
         "the --safe flag",
         "default → exit 0", gate([C, P_POST], SH, safe=False)[0] == 0,
         "--safe  → exit 1", gate([C, P_POST], SH, safe=True)[0] == 1),
        ("fence inferred from the asset extension",
         "the emit target extension (.sh → .md)",
         ".sh → ```sh fence", "```sh" in projection([C, P_CITE], SH),
         ".md → raw, no fence", "```sh" not in projection([C, P_MD], MD)),
    ]
    for name, axis, p_lbl, p_ok, f_lbl, f_ok in pairs:
        ok = p_ok and f_ok
        fails.append(name) if not ok else None
        print(f"  {'ok ' if ok else 'XX '}{name}")
        print(f"      P (pass side): {p_lbl}")
        print(f"      F (flag side): {f_lbl}")
        print(f"      δ (min delta): {axis}\n")

    if fails:
        print(f"BOUNDARIES: FAIL ({len(fails)} drifted)")
        return 1
    print("BOUNDARIES: PASS (4 behaviors, 3 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
