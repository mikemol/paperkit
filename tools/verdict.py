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
                                                     pk_result = (verdict, fail); pk_adequacy =
                                                     (grade, vacuous,existence,indeterminate,broken);
                                                     pk_footaudit = (ok, false).
  agree  <verb> <out> <produced>...                — pass iff >=2 produced outputs, all byte-equal, none failed
  calc   <verb> <calc.json> <out>                  — pass iff the calc record's baseline holds (pk_verdict)
  cohere <verb> <project> <out> <calc>...          — pass iff coherence.py passes over the calcs (pk_cohere)
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
    a = ap.parse_args(argv)

    if a.cmd == "emit":
        _write(a.out, a.verb, a.ok == "pass")
    elif a.cmd == "exists":
        _write(a.out, a.verb, pathlib.Path(a.path).exists())
    elif a.cmd == "agg":
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
