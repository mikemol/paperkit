#!/usr/bin/env python3
"""Behavioral-boundary examples for emit: placement and the --safe postulate gate.

⟨P, F, δ⟩ per the boundary practice.  Bounds the README-as-projection engine surface:
emit places a verbatim asset (fence inferred from extension), additive to a claim so
the example stays CITED; an uncited placement is a postulate — advised against by
default, rejected under --safe.  Both documentation and a test (exit 0 iff all hold).

    python3 paperkit/tests/boundaries_emit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixture_gate import gate  # noqa: E402
from _fixture_model import entry  # noqa: E402
from _fixture_project import project_text  # noqa: E402

C = entry("c", claim="a cited claim")                                       # base prose
P_CITE = entry("p", claim="an example", emit="x.sh", frm="c", check="file:x.sh")  # derived term
P_POST = entry("p", emit="x.sh", frm="c", check="file:x.sh")                # postulate (no claim)
P_MD = entry("p", claim="an example", emit="x.md", frm="c", check="file:x.md")
SH = {"x.sh": "echo hi\n"}
MD = {"x.md": "| a | b |\n| - | - |\n"}


def main() -> int:
    fails = []

    def check(desc, cond):
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("emit / --safe behaviors\n")
    proj_sh = project_text([C, P_CITE], assets=SH)
    proj_md = project_text([C, P_MD], assets=MD)
    rc_default, err_default = gate([C, P_POST], assets=SH)
    check("emit places a fenced block, fence from extension (.sh)",
          "```sh" in proj_sh and "echo hi" in proj_sh)
    check("additive: the example is CITED ([@p] in prose)", "[@p]" in proj_sh)
    check(".md asset is a raw include (no code fence)",
          "| a | b |" in proj_md and "```" not in proj_md)
    proj_svg = project_text([entry("a", claim="a cited claim"),
                             entry("p", claim="a figure", emit="fig.svg", frm="a", check="file:fig.svg")],
                            assets={"fig.svg": "<svg/>\n"})
    check("image asset renders as a markdown image, not a fenced block",
          "![a figure](fig.svg)" in proj_svg and "```" not in proj_svg)
    check("uncited placement passes by default but raises a postulate advisory",
          rc_default == 0 and "postulate" in err_default)
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        ("postulate vs derived term (gate --safe)", "the claim field on the emit warrant",
         "claim+emit → exit 0", gate([C, P_CITE], "--safe", assets=SH)[0] == 0,
         "emit only  → exit 1", gate([C, P_POST], "--safe", assets=SH)[0] == 1),
        ("--safe toggles the postulate (same uncited placement)", "the --safe flag",
         "default → exit 0", gate([C, P_POST], assets=SH)[0] == 0,
         "--safe  → exit 1", gate([C, P_POST], "--safe", assets=SH)[0] == 1),
        ("fence inferred from the asset extension", "the emit target extension (.sh → .md)",
         ".sh → ```sh fence", "```sh" in project_text([C, P_CITE], assets=SH),
         ".md → raw, no fence", "```sh" not in project_text([C, P_MD], assets=MD)),
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
    print("BOUNDARIES: PASS (5 behaviors, 3 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
