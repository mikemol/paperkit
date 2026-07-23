#!/usr/bin/env python3
"""Ζ·verb — the VERDICT-RECORD authority: the ONE place that knows the {verb, verdict} record's
format and every way to construct one.  A verdict is `oracle → {verb, verdict}`; the oracle differs
per verb (does a file exist, does a command exit 0, do N producers agree, does a calc's baseline
hold, do sibling records read pass), but the RECORD is one type.

Centralizing it kills the format-drift class.  Every emit is COMPACT and stable
(separators no spaces), and every consumer PARSES the record (json.load) — it never greps the bytes.
A grep-vs-emit spacing mismatch is exactly what silently dropped fails once: a `{"verdict": "fail"}`
record (json.dumps default spacing) that pk_gate's `grep '"verdict":"fail"'` (no space) never matched,
so a failed check went green.  One emitter + parsing consumers makes that unrepresentable.

Subcommands — each writes one compact {verb, verdict} record to <out>:
  emit   <verb> <pass|fail> <out>                  — record a verdict the caller computed (pk_cmd)
  exists <verb> <path> <out>                       — pass iff <path> is present (pk_file)
  agg    <verb> <out> <field> <bad> <record>...    — pass iff NO record has record[field] in <bad>
                                                     (a comma list).  The ONE aggregator: pk_gate /
                                                     pk_result = (verdict, fail); pk_footaudit =
                                                     (ok, false).  For an ADEQUACY floor use
                                                     `<bad>` = `below:<grade>` (see below).
  agree  <verb> <out> <produced>...                — pass iff >=2 produced outputs, all byte-equal, none failed
  calc   <verb> <calc.json> <out>                  — pass iff the calc record's baseline holds (pk_verdict)
  cohere <verb> <project> <out> <calc>...          — pass iff coherence.py passes over the calcs (pk_cohere)
  canary <pos.json> <nul.json> <out>               — Ζ·canary: pass iff the guaranteed-flip eval
                                                     FLIPPED and the ∅ identity did NOT; anything
                                                     else = the harness itself is degraded (a
                                                     non-hermetic sandbox lets checks resolve()
                                                     out to the real unmutated tree) → fail LOUD
                                                     with a NAMED error, never a silent green.
"""
import argparse
import json
import pathlib
import subprocess
import sys


def _write(out, verb, ok):
    pathlib.Path(out).write_text(
        json.dumps({"verb": verb, "verdict": "pass" if ok else "fail"}, separators=(",", ":")) + "\n")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, extra in [("emit", ["ok"]), ("exists", ["path"]), ("calc", ["calc"])]:
        p = sub.add_parser(name)
        p.add_argument("verb")
        for e in extra:
            p.add_argument(e)
        p.add_argument("out")
    pg = sub.add_parser("agg")
    pg.add_argument("verb")
    pg.add_argument("out")
    pg.add_argument("field")
    pg.add_argument("bad")
    pg.add_argument("records", nargs="*")
    pr = sub.add_parser("agree")
    pr.add_argument("verb")
    pr.add_argument("out")
    pr.add_argument("produced", nargs="*")
    pc = sub.add_parser("cohere")
    pc.add_argument("verb")
    pc.add_argument("project")
    pc.add_argument("out")
    pc.add_argument("calcs", nargs="*")
    pn = sub.add_parser("canary")
    pn.add_argument("pos")
    pn.add_argument("nul")
    pn.add_argument("out")
    a = ap.parse_args(argv)

    if a.cmd == "emit":
        _write(a.out, a.verb, a.ok == "pass")
    elif a.cmd == "exists":
        _write(a.out, a.verb, pathlib.Path(a.path).exists())
    elif a.cmd == "agg":
        # Ζ·ladder — `below:<floor>` DERIVES the failing set from the engine's ladder instead of
        # naming it.  This used to be a literal list of the failing grades, which makes an adequacy
        # gate FAIL OPEN: every rung added to the ladder afterwards is absent from the list, so it
        # passes by default — the one direction a gate must never fail.  (The list is not repeated
        # here either; enumerating a set this file cannot see is how it went stale in the first
        # place.)  Asking grade.below() judges a new rung the moment it exists, and a floor that is
        # not a rung raises rather than quietly grading everything green.
        if a.bad.startswith("below:"):
            sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "paperkit"))
            import grade
            bad = set(grade.below(a.bad.split(":", 1)[1]))
        else:
            bad = {b.lower() for b in a.bad.split(",")}

        def field_val(r):
            return str(json.loads(pathlib.Path(r).read_text()).get(a.field)).lower()

        _write(a.out, a.verb, all(field_val(r) not in bad for r in a.records))
    elif a.cmd == "agree":
        texts = [pathlib.Path(p).read_text() for p in a.produced]
        lines = {ln for t in texts for ln in t.splitlines()}
        _write(a.out, a.verb, len(texts) >= 2 and len(lines) == 1 and "__FAIL__" not in lines)
    elif a.cmd == "calc":
        _write(a.out, a.verb, bool(json.loads(pathlib.Path(a.calc).read_text()).get("baseline")))
    elif a.cmd == "cohere":
        rc = subprocess.run([sys.executable, "paperkit/coherence.py", "--from-calcs", a.project, *a.calcs],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        _write(a.out, a.verb, rc == 0)
    elif a.cmd == "canary":
        # Ζ·canary — the positive control's verdict.  Both directions asserted (a gate is sound
        # both ways, [[instrument-vs-gate]]): the guaranteed-flip cell MUST flip, the ∅ identity
        # MUST NOT.  Failure is NAMED — the degraded state says it degraded.
        pos = json.loads(pathlib.Path(a.pos).read_text())
        nul = json.loads(pathlib.Path(a.nul).read_text())
        ok = pos.get("flipped") is True and nul.get("flipped") is False
        if not ok:
            print("verdict canary: HARNESS DEGRADED — guaranteed-flip mutation flipped=%s, "
                  "∅ identity flipped=%s.  A non-hermetic sandbox (processwrapper fallback) lets "
                  "checks resolve() out to the real unmutated tree; run under --config=mutant "
                  "(hermetic linux-sandbox)." % (pos.get("flipped"), nul.get("flipped")),
                  file=sys.stderr)
        _write(a.out, "canary", ok)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
