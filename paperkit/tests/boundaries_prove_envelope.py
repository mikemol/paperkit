#!/usr/bin/env python3
"""Ζ·prove-gate — the --prove face and the build's cached __dcalc run the SAME oracle.

A concept witness's --prove face (paperkit/prove.py certificate()) emits ⟨verdict, baseline, sens,
grade, …⟩; the build caches the identical measurement as @paperkit_library//:<key>__dcalc.  Their
byte-equivalence was HAND-verified once (Λ·prove @ab386b4, 63 sites).  This gates the structural
ground of that equivalence in //:hook, WITHOUT re-running any sweep (the ~40s×N nesting the
runtime form would cost): the certificate PROJECTS the __dcalc record — it runs the byte-identical
oracle command and wraps it with the shared grade leaf — so if the two commands and the one ladder
agree by SOURCE, their {claim,baseline,sens,grade} agree by construction.

What this PROVES (structural equivalence, gated): --prove and __dcalc invoke the same discriminate
oracle (identical flags, same def frame) and grade via the same _grade_from_sens leaf.
What it does NOT prove (names-not-entails, a declared residue): that the two independent EXECUTIONS
emit byte-identical output — that is entailed by action idempotency (result = f(inputs)), an engine
invariant owned elsewhere, not re-checked here.  So the plumbing can no longer silently diverge;
only idempotency itself breaking could split them.

    python3 paperkit/tests/boundaries_prove_envelope.py
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROVE = ROOT / "paperkit" / "prove.py"
CALC = ROOT / "tools" / "calc.bzl"
BIBTEX = ROOT / "tools" / "bibtex.bzl"


def prove_oracle_flags():
    """The flag tokens library/prove.py's certificate() builds after discriminate.py — derived
    from the source (never a hardcoded canonical string), so the gate cannot drift from it.
    """
    tree = ast.parse(PROVE.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "argv" for t in node.targets) \
                and isinstance(node.value, ast.List):
            out = []
            for el in node.value.elts:
                if isinstance(el, ast.Constant):
                    out.append(el.value)                      # a literal flag ("--only", "--calc", …)
                elif isinstance(el, ast.Name):
                    out.append("<" + el.id + ">")             # a variable (key, resolution)
                else:
                    out.append("<expr>")                      # sys.executable, ENGINE/…, str(OWNER)
            return out
    return []


def prove_resolution():
    """certificate()'s resolution literal (prove.py: `resolution = "def"`), derived from source."""
    for node in ast.walk(ast.parse(PROVE.read_text())):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "resolution" for t in node.targets) \
                and isinstance(node.value, ast.Constant):
            return node.value.value
    return None


def dcalc_resolution():
    """The resolution the build emits __dcalc with (bibtex.bzl's non-witness emerge pk_calc) —
    the frame the cached record was measured in.  Derived from the generator source.
    """
    for line in BIBTEX.read_text().splitlines():
        if "__dcalc" in line and "resolution" in line:
            m = re.search(r'resolution\s*=\s*"(\w+)"', line)
            if m:
                return m.group(1)
    # the resolution may be on the continuation line of the __dcalc emit; scan the emit block
    m = re.search(r'_lit\(k \+ "__dcalc"\).*?resolution = "(\w+)"', BIBTEX.read_text(), re.S)
    return m.group(1) if m else None


def main() -> int:
    # Ζ·suite·count — the SHARED recorder owns the summary (see tests/_boundary.py).  The local
    # closure recorded only failures, so "6 structural, 1 delta" was a literal beside the set it
    # described — and its vocabulary ("structural") is why a census keyed on the word "behaviors"
    # missed this file entirely.  A derived count has no vocabulary to miss.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _boundary import Suite
    s = Suite("PROVE-ENVELOPE", "Ζ·prove-gate — --prove and __dcalc run the same oracle")
    check = s.check

    # ⟨same oracle command⟩ — prove.py's argv IS the discriminate --calc def command pk_calc runs.
    flags = prove_oracle_flags()
    # the meaningful sequence: --only <key> --calc --resolution <res> (the project path is the last <expr>)
    seq = [f for f in flags if f.startswith("--") or f in ("<key>", "<resolution>")]
    check(f"prove.py runs `--only <key> --calc --resolution <res>` (derived argv: {seq})",
          seq == ["--only", "<key>", "--calc", "--resolution", "<resolution>"])

    # pk_calc (calc.bzl) builds `discriminate.py --only <claim> --calc [ --resolution <attr> ]`
    calc_src = CALC.read_text()
    check("pk_calc emits the SAME oracle: `discriminate.py --only <claim> --calc` + `--resolution <attr>`",
          "discriminate.py --only " in calc_src and "--calc" in calc_src
          and '" --resolution " + ctx.attr.resolution' in calc_src)

    # ⟨same def frame⟩ — prove.py measures resolution="def"; the build emits __dcalc at resolution="def".
    pr, dr = prove_resolution(), dcalc_resolution()
    check(f"prove.py's frame is def ({pr!r})", pr == "def")
    check(f"the build caches __dcalc at the SAME frame ({dr!r}) — prove's def ≡ __dcalc's def", dr == "def")

    # ⟨same ladder⟩ — prove.py grades via the shared leaf, re-declares no rung order.
    prove_src = PROVE.read_text()
    check("prove.py grades via the imported grade._grade_from_sens (the shared ladder leaf)",
          "from grade import _grade_from_sens" in prove_src and "_grade_from_sens(baseline, sens)" in prove_src)
    check("prove.py re-declares NO ladder (no STRENGTH/RANK_C/ORDER of its own — the boundaries_ladder rule)",
          not any(re.search(rf"\b{n}\s*=", prove_src) for n in ("STRENGTH", "RANK_C", "GRADE_C")))

    print("\n⟨P, F, δ⟩ minimum-delta pair\n")
    # F = certificate silently measures FILE resolution (≠ __dcalc's def) — one token.
    f_src = prove_src.replace('resolution = "def"', 'resolution = "file"')
    f_res = None
    for node in ast.walk(ast.parse(f_src)):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "resolution" for t in node.targets) \
                and isinstance(node.value, ast.Constant):
            f_res = node.value.value
    s.delta("a cert that silently measures a DIFFERENT frame than __dcalc is CAUGHT",
            pr == "def", (f_res == "file") and (f_res != dr),
            p="intact:  prove resolution == 'def' == __dcalc's frame → same oracle",
            f="drifted: resolution → 'file' → cert measures a weaker frame than the cached record",
            d="one token, the resolution literal (prove.py) — or the _grade_from_sens import")
    return s.finish()


if __name__ == "__main__":
    raise SystemExit(main())
