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
  emit   <verb> <pass|fail> <out>          — record a verdict the caller already computed (pk_cmd)
  exists <verb> <path> <out>               — pass iff <path> is present (pk_file)
  agg    <verb> <out> <record.json>...     — pass iff NO input record reads fail (pk_result=1, pk_gate=N)
  agree  <verb> <out> <produced>...        — pass iff >=2 produced outputs, all byte-equal, none failed
  calc   <verb> <calc.json> <out>          — pass iff the calc record's baseline holds (pk_verdict)
  cohere <verb> <project> <out> <calc>...  — pass iff coherence.py passes over the calcs (pk_cohere)
"""
import argparse
import json
import pathlib
import subprocess
import sys


def _write(out, verb, ok):
    pathlib.Path(out).write_text(
        json.dumps({"verb": verb, "verdict": "pass" if ok else "fail"}, separators=(",", ":")) + "\n")


def _verdict(record):
    return json.loads(pathlib.Path(record).read_text()).get("verdict")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, extra in [("emit", ["ok"]), ("exists", ["path"]), ("calc", ["calc"])]:
        p = sub.add_parser(name)
        p.add_argument("verb")
        for e in extra:
            p.add_argument(e)
        p.add_argument("out")
    for name, rest in [("agg", "records"), ("agree", "produced")]:
        p = sub.add_parser(name)
        p.add_argument("verb")
        p.add_argument("out")
        p.add_argument(rest, nargs="*")
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
        _write(a.out, a.verb, all(_verdict(r) != "fail" for r in a.records))
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
