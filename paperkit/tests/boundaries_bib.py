#!/usr/bin/env python3
"""Behavioral-boundary examples for the bib PARSER — paperkit/bib.py.

⟨P, F, δ⟩ per the boundary practice.  The parser carries the known fields (_SCALAR, _LIST) and
NAMES any OTHER field loudly rather than dropping it in silence — a field paperkit does not
consume is otherwise a silent drop (a downstream author's `points` vanished on 14 entries).  It
stays quiet only on standard BibTeX metadata a `references.bib` citation is expected to carry.
The top-level field scan tracks brace depth, so an `=` inside a value is not mistaken for a field.

    python3 paperkit/tests/boundaries_bib.py
"""
from __future__ import annotations

import io
import pathlib
import shutil
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bib


def _warns(body: str, consumer_fields: tuple = ()) -> str:
    """Parse a one-entry bib with this body (and optional declared consumer fields); return the
    parser's stderr and the parsed record.
    """
    bib._WARNED.clear()                          # the dedup is per build, not per probe
    p = Path(tempfile.mkdtemp()) / "t.bib"
    p.write_text("@misc{k,\n" + body + "\n}\n")
    err = io.StringIO()
    with redirect_stderr(err):
        parsed = bib.parse(p, consumer_fields)
    return err.getvalue(), parsed["k"]


def main() -> int:
    fails = []

    ran = []

    def check(desc, cond):
        # Λ·guard-must-not-copy — `ran` COUNTS the arms.  The summary line used to restate a
        # number authored beside the set it describes, and every one of the 26 suites carrying
        # such a line UNDERSTATED it (24 mismatched, none overstated): arms were added and the
        # literal never moved, so it tracked the suite's authoring history rather than its
        # content — and would have read a SHRINKING suite as an unchanged one.
        ran.append(desc)
        fails.append(desc) if not cond else None
        print(f"  {'ok ' if cond else 'XX '}{desc}")

    print("bib parser behaviors\n")
    check("_top_fields finds the top-level fields",
          bib._top_fields("claim = {a}, check = {cmd:true}") == ["claim", "check"])
    check("_top_fields ignores an `=` INSIDE a value (set notation is not a field)",
          bib._top_fields("claim = {x = {1,2}}, check = {cmd:true}") == ["claim", "check"])
    known_err, known = _warns("  claim = {a claim},\n  check = {cmd:true}")
    check("a known field is carried (claim + check parsed)",
          known.get("claim") == "a claim" and known.get("check") == "cmd:true")
    check("a known-field entry warns about nothing", known_err == "")
    pts_err, pts = _warns("  claim = {c},\n  points = {q, r},\n  check = {cmd:true}")
    check("an unknown field is NAMED loud on stderr (not silently dropped)",
          "points" in pts_err and "DROPPED" in pts_err)
    check("the unknown field is still absent from the parsed record (dropped, as said)",
          "points" not in pts)
    # Ζ·bib·declare — STANDARD BIBTEX METADATA TAKES THE SAME ROUTE AS EVERY OTHER NON-ENGINE
    # FIELD.  A 24-name `_BIBTEX` roster used to exempt `journal`/`doi`/`publisher` from the
    # warning while the extraction loop still never read them, so they were SILENT AND DROPPED —
    # the engine claiming to know a field and discarding it.  Both halves are asserted here,
    # because the old design passed the first and failed the second.
    bibtex_err, bibtex_rec = _warns("  title = {T},\n  author = {A},\n  journal = {J},\n  year = {2020}")
    check("UNDECLARED BibTeX metadata is NAMED, not silently swallowed by an engine roster",
          "journal" in bibtex_err and "DROPPED" in bibtex_err)
    check("...and the warning names consumer_fields as the remedy (not just 'remove it')",
          "consumer_fields" in bibtex_err)
    check("an undeclared BibTeX field is absent from the record — silence never implied carriage",
          "journal" not in bibtex_rec)
    # And DECLARING it is what carries it: the access the old roster never granted.
    dec_err, dec_rec = _warns("  title = {T},\n  author = {A},\n  journal = {J},\n  doi = {10.1/x}",
                              ("journal", "doi"))
    check("a DECLARED BibTeX field is carried on the record (engine-inert, like `note`)",
          dec_rec.get("journal") == "J" and dec_rec.get("doi") == "10.1/x")
    check("...and declaring it is quiet", dec_err == "")
    # A claim carrying inline math extracts INTACT: the value is brace-counted to arbitrary depth
    # (a set-builder \min\{ … \mathrm{eff}(d) : … \} nests deeper than one level) and LaTeX-escaped
    # braces \{ \} are literal CONTENT, not structure — the one-level regex this replaced stopped
    # at the first inner `}` and returned a truncated/empty claim (the projector then fell back to
    # the bare key — the degenerate-claim class one layer down).
    _, math = _warns(r"  claim = {clamp: $\mathrm{eff}(c) = \min\{\, \mathrm{grade}(c)\,\} \cup \{\, \mathrm{eff}(d) : d \in S\,\}$ holds},"
                     "\n  check = {cmd:true}")
    check("a claim with DEEP-nested inline math extracts intact (not truncated to empty)",
          math.get("claim", "").startswith("clamp:") and math["claim"].endswith("holds")
          and "$" in math["claim"])
    check("_scalar_value counts to arbitrary depth (nested \\mathrm{} inside \\{ \\})",
          bib._scalar_value(r"claim = {a \min\{\mathrm{x}\} b}", "claim") == r"a \min\{\mathrm{x}\} b")
    check("_top_fields ignores escaped braces in math (they are not structural depth)",
          bib._top_fields(r"claim = {$\{x\}$ text}, check = {cmd:true}") == ["claim", "check"])
    # A project DECLARES the extra scalar fields it tolerates (its downstream consumer's vocabulary);
    # paperkit carries them but consumes them in no invariant.  A DECLARED field is carried AND quiet;
    # an UNdeclared unknown is still named loud — the declaration is what tells a consumer's field
    # from a typo, which a hardcoded whitelist could not (one consumer's words must not be baked into
    # a domain-and-location-free engine).
    cf = ("kind", "by", "of")
    decl_err, decl = _warns("  claim = {c},\n  kind = {friction},\n  by = {paperkit}", cf)
    check("a DECLARED consumer field is carried verbatim (kind, by parsed)",
          decl.get("kind") == "friction" and decl.get("by") == "paperkit")
    check("a declared consumer field warns about nothing (quiet)", decl_err == "")
    mixed_err, mixed = _warns("  claim = {c},\n  kind = {friction},\n  bogus = {x}", cf)
    check("an UNdeclared unknown field is still NAMED loud even when others are declared",
          "'bogus'" in mixed_err and "DROPPED" in mixed_err        # bogus reported dropped
          and "'kind'" not in mixed_err and mixed.get("kind") == "friction")  # kind carried, not dropped
    undecl_err, undecl = _warns("  claim = {c},\n  kind = {friction}")
    check("WITHOUT the declaration the same field is a loud-drop, not carried",
          "kind" in undecl_err and "kind" not in undecl)
    print()

    # Ζ·consumer-fields — the CONFIG-RESOLVED path (bib.load_bib), the one the two bare parse sites broke.
    # The block above passes consumer_fields as a TUPLE directly; this resolves them from a real paper.toml
    # ON DISK via load_config — the path a caller reading a lone project bib actually takes.  A caller that
    # forgets the owner (a bare bib.parse) loud-drops a declared field; load_bib binds it.  (The standing
    # in-tree exercise is the demo/ project; this is the targeted unit — with an F-arm so it is not vacuous.)
    def _load_bib_from_toml(cf_line: str) -> tuple:
        d = Path(tempfile.mkdtemp())
        (d / "paper.toml").write_text(
            '[paper]\ntitle="t"\nrubric="r.tsv"\nwarrants=["w.bib"]\nout="o.md"\n' + cf_line)
        (d / "w.bib").write_text("@misc{k,\n  claim = {c},\n  provenance = {p},\n  check = {cmd:true}\n}\n")
        bib._WARNED.clear()
        err = io.StringIO()
        with redirect_stderr(err):
            recs = bib.load_bib(d / "w.bib", d)
        return err.getvalue(), recs["k"]
    lb_err, lb = _load_bib_from_toml('consumer_fields=["provenance"]\n')
    check("load_bib resolves consumer_fields from paper.toml on disk — a DECLARED field carried + quiet",
          lb.get("provenance") == "p" and lb_err == "")

    # Ζ·bib·parser — AN ENTRY IS BRACE-COUNTED, NOT MATCHED TO THE FIRST LINE-INITIAL `}`.
    # The scanner this replaces was `re.finditer(r"@\w+\{...(.*?)\n\}")`: non-greedy to the first
    # `\n}`, so a value holding a brace at column 0 ended the entry early.  MEASURED before the
    # fix: the entry below parsed with ZERO FIELDS while a reader reported `2 of 2 entries` — an
    # honest count over empty content.  And a claim with no `check` is excluded from gate.py's
    # `warrants` set, so the truncation DISARMS a claim while the gate stays green.
    # ⚑ The brace pair inside the value is BALANCED and its closer sits at column 0 — which is
    # what a code block, a JSON fragment or a set-builder broken across lines looks like.  The old
    # non-greedy `(.*?)\n\}` ended the entry THERE; brace-counting carries through it.
    _brace = _warns("  claim = {a block: {\nnested\n} and the tail},\n  check = {cmd:true}")[1]
    check("an entry survives a line-initial `}` inside a value (was: silently emptied)",
          _brace.get("check") == "cmd:true")
    check("...and the value itself is intact, not truncated at the bare brace",
          "the tail" in (_brace.get("claim") or ""))
    # The entry TYPE is carried.  `@\w+` matched and discarded it, so @book and @misc were
    # indistinguishable to the engine and no reader could answer what types a file uses.
    check("the entry type is captured, not discarded", _brace.get("_type") == "misc")

    # Ζ·bib·shadow — a key defined in TWO of a project's composed bibs is REFUSED, not merged.
    # The dangerous direction is asserted directly: the second entry carries NO `check`, so under
    # the old bare `F.update` it replaced a checked warrant with an unchecked one — gate.py's
    # `warrants = {k for k, f in F.items() if f.get("check")}` then dropped the key entirely and
    # the claim stayed cited, unverified, green.
    def _two_bibs(second_body: str) -> tuple:
        d = Path(tempfile.mkdtemp())
        (d / "paper.toml").write_text(
            '[paper]\ntitle="t"\nrubric="r.tsv"\nwarrants=["a.bib","b.bib"]\nout="o.md"\n')
        (d / "a.bib").write_text("@misc{dup,\n  claim = {first},\n  check = {cmd:true}\n}\n")
        (d / "b.bib").write_text(second_body)
        bib._WARNED.clear()
        try:
            return True, bib.parse_project(d)
        except SystemExit as e:
            return False, str(e)
    ok_dup, dup_msg = _two_bibs("@misc{dup,\n  claim = {second}\n}\n")
    check("a key defined in TWO composed bibs REFUSES (the silent last-wins is unrepresentable)",
          not ok_dup)
    check("...and the refusal names BOTH files, which is the whole diagnosis",
          "a.bib" in dup_msg and "b.bib" in dup_msg)
    ok_uniq, uniq_recs = _two_bibs("@misc{other,\n  claim = {second},\n  check = {cmd:true}\n}\n")
    check("δ: the same two bibs with DISTINCT keys compose normally",
          ok_uniq and sorted(uniq_recs) == ["dup", "other"])
    print()

    print("⟨P, F, δ⟩ minimum-delta pairs\n")
    pairs = [
        # Ζ·bib·declare — THE DELTA IS THE DECLARATION, NOT THE FIELD'S NAME.  This pair used to
        # read `journal → tolerated, points → named`, making the engine's opinion about which
        # names are "real bibliography" the discriminator — a roster that drifted from actual
        # BibTeX (`type = {RFC}` was absent from it) and that bought silence without carriage.
        # One field, two projects: the SAME `journal` is quiet-and-carried where declared and
        # named where not, so nothing about the name itself decides.
        ("a BibTeX field is carried-and-quiet iff the PROJECT declared it — the engine holds no roster",
         "whether this project declared the field, NOT whether the engine considers the name bibliographic",
         "declared → carried + quiet",
         _warns("  journal = {J}", ("journal",))[1].get("journal") == "J"
         and _warns("  journal = {J}", ("journal",))[0] == "",
         "undeclared → dropped + named", "journal" in _warns("  journal = {J}")[0]),
        ("a top-level field is named, an `=` inside a value is not (brace depth)",
         "whether the `= {` sits at brace depth 0 or inside a value",
         "top level → a field", bib._top_fields("points = {q}") == ["points"],
         "inside a value → not", bib._top_fields("claim = {a points = {q} b}") == ["claim"]),
        ("a claim's value is brace-counted, and an escaped brace is content not structure",
         "whether a `}` is a real closing brace or a LaTeX-escaped literal `\\}`",
         "unescaped } closes the value",
         bib._scalar_value(r"claim = {a {b} c}", "claim") == "a {b} c",
         "escaped \\} does NOT close it early",
         bib._scalar_value(r"claim = {a \} b}", "claim") == r"a \} b"),
        ("a consumer field is carried-and-quiet iff the project DECLARED it",
         "whether the field name is in this project's declared consumer_fields",
         "declared → carried + quiet",
         _warns("  kind = {x}", ("kind",))[1].get("kind") == "x" and _warns("  kind = {x}", ("kind",))[0] == "",
         "undeclared → dropped + named", "kind" in _warns("  kind = {x}")[0]),
        ("load_bib carries-and-quiets a field iff the project's paper.toml DECLARES it (config-resolved)",
         "whether the paper.toml on disk lists the field in consumer_fields — the path the bare parse sites bypassed",
         "declared in paper.toml → carried + quiet",
         _load_bib_from_toml('consumer_fields=["provenance"]\n')[1].get("provenance") == "p"
         and _load_bib_from_toml('consumer_fields=["provenance"]\n')[0] == "",
         "not declared in paper.toml → dropped + named",
         "provenance" in _load_bib_from_toml("")[0] and "provenance" not in _load_bib_from_toml("")[1]),
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
    # ---- Ζ·talk·tier: a project DECLARES which check types are non-mechanical ----
    # A `premise:`/`definition:` resolves by `cmd = "true"` — unfalsifiable by construction, so a
    # sweep measures sens=∅ and the grade lands below the adequacy floor.  That is a TRUE
    # measurement of a claim that was never a sweep candidate; failing adequacy on it would force
    # a project to delete its honest premises or dress them in a fake mechanism.
    d = pathlib.Path(tempfile.mkdtemp())
    try:
        (d / "paper.toml").write_text(
            '[paper]\ntitle = "t"\nwarrants = ["w.bib"]\nrubric = "r.tsv"\nout = "o.md"\n'
            '[checks.premise]\ncmd = "true"\nmechanical = false\n'
            '[checks.oracle]\ncmd = "python3 x.py {target}"\n')
        cfg = bib.load_config(d)
        ok = cfg["nonmechanical"] == ("premise",)
        print(f"  {'ok' if ok else 'XX'} a declared `mechanical = false` type is reported "
              f"non-mechanical")
        ran.append(ok)
        # δ: the SAME file without the flag — one line is the whole difference
        (d / "paper.toml").write_text(
            '[paper]\ntitle = "t"\nwarrants = ["w.bib"]\nrubric = "r.tsv"\nout = "o.md"\n'
            '[checks.premise]\ncmd = "true"\n')
        ok2 = bib.load_config(d)["nonmechanical"] == ()
        print(f"  {'ok' if ok2 else 'XX'} δ: the same type WITHOUT the flag is mechanical — "
              f"declared, never inferred from `cmd = \"true\"`")
        ran.append(ok2)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ---- Ζ·toml·scope: the guard is TOTAL over the key set, and the set has TWO owners ----
    # Ζ·consumer·scope guarded ONE key and looked only in sibling tables.  The instance that
    # prompted the generalisation — summit, against memmesh — was `root` declared ABOVE the
    # [paper] header, which is neither: a different owner (an Ω·config Param, not a load_config
    # p.get) in a place the old guard never looked.  So this witnesses the key the old guard
    # could not see, in the position it could not see.
    d3 = pathlib.Path(tempfile.mkdtemp())
    try:
        body = 'title="t"\nwarrants=["w.bib"]\nrubric="r.tsv"\nout="O.md"\n'
        # F: above the header — TOML puts it at the top level, outside .get("paper", {})
        (d3 / "paper.toml").write_text('root="."\n[paper]\n' + body)
        try:
            bib.load_config(d3)
            ok = False
        except SystemExit as e:
            ok = "belongs under [paper]" in str(e) and "root" in str(e)
        print(f"  {'ok' if ok else 'XX'} a [paper] key declared ABOVE [paper] REFUSES — the "
              f"top level is a table too, and the engine reads none of it")
        ran.append(ok)
        # δ: the SAME line, one header later.  Same three characters, opposite effect.
        (d3 / "paper.toml").write_text("[paper]\n" + body + 'root="."\n')
        ok2 = bib.load_config(d3) is not None
        print(f"  {'ok' if ok2 else 'XX'} δ: the same line BELOW the header is accepted — "
              f"placement is the whole difference, and it is invisible by eye")
        ran.append(ok2)
        # the set is DERIVED from both owners, never copied: a guard carrying its own list
        # would certify a tautology the moment a key was added to one owner and not the guard.
        keys = set(bib.paper_keys()) | set(bib._param_config_keys())
        ok3 = "root" in keys and "consumer_fields" in keys and "title" in keys
        print(f"  {'ok' if ok3 else 'XX'} the guarded set is derived from BOTH owners "
              f"(load_config's p.get calls + Param config= declarations): {len(keys)} keys")
        ran.append(ok3)
    finally:
        shutil.rmtree(d3, ignore_errors=True)

    # ---- Ζ·consumer·scope: a misplaced consumer_fields REFUSES, it does not degrade ----
    # Put it after a [checks.X] header and TOML scopes it into THAT table, so the engine sees
    # none, every declared field loud-drops, and the build still exits 0.  Reported by a
    # downstream consumer who lost six fields exactly that way.
    d2 = pathlib.Path(tempfile.mkdtemp())
    try:
        base = ('[paper]\ntitle="t"\nwarrants=["w.bib"]\nrubric="r.tsv"\nout="O.md"\n')
        (d2 / "paper.toml").write_text(base + '[checks.claim]\ncmd="x {target}"\n'
                                              'consumer_fields=["upstream_doc"]\n')
        try:
            bib.load_config(d2)
            ok = False                       # reached => it accepted a misplaced declaration
        except SystemExit as e:
            ok = "belongs under [paper]" in str(e)
        print(f"  {'ok' if ok else 'XX'} a consumer_fields under [checks.X] REFUSES, naming the "
              f"table and the consequence")
        ran.append(ok)
        # δ: the SAME key, one table up, is accepted — placement is the whole difference
        (d2 / "paper.toml").write_text(base + 'consumer_fields=["upstream_doc"]\n'
                                              '[checks.claim]\ncmd="x {target}"\n')
        ok2 = bib.load_config(d2)["consumer_fields"] == ("upstream_doc",)
        print(f"  {'ok' if ok2 else 'XX'} δ: the same declaration under [paper] is accepted")
        ran.append(ok2)
    finally:
        shutil.rmtree(d2, ignore_errors=True)

    # Ζ·bib·verdict — `ran` collects each behaviour's PASS/FAIL, and the verdict is the
    # conjunction.  It used to be `len(ran)`: every assertion printed `ok`/`XX` and the suite
    # returned 0 REGARDLESS, so a `XX` line scrolled past a green exit and the whole file was
    # decorative.  Caught by mutating out the guard this suite exists to witness — the mutant
    # was live (a misplaced key was accepted) and the suite still passed.  A witness that
    # cannot fail is an instrument, not a gate.
    bad = len([b for b in ran if not b])
    if bad:
        print(f"BOUNDARIES: FAIL ({bad} of {len(ran)} behaviors drifted)")
        return 1
    bad = len([b for b in ran if not b])
    if bad:
        print(f"BOUNDARIES: FAIL ({bad} of {len(ran)} behaviors drifted)")
        return 1
    print(f"BOUNDARIES: PASS ({len(ran)} behaviors, 5 deltas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
