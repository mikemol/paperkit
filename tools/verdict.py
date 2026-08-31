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


# Ζ·tier·exit — the verdict is a TRISTATE, not a boolean: pass / fail / cannot-run.  `cannot-run`
# (a toolchain-tier check whose host toolchain is absent — the render checks' explicit `_REFUSE`
# exit, mirrored here) is NOT a failure: the aggregator's bad-set is {fail} alone, so a cannot-run
# does NOT red the gate (no false-red on a toolchain-less box) yet stays distinguishable from pass
# (no false-green — it is honestly "not verified here", the ask-result-tristate shape at the record
# layer).  A bool `ok` still maps pass/fail (the common path); a str verdict passes through verbatim.
def _write_atomic(path, data):
    """Ζ·write·atomic — write a sibling temp, then rename over `path`.

    DUPLICATED from durable.write_atomic on purpose, and gated for agreement rather than trusted:
    this tool is staged into the Bazel sandbox as a LONE FILE (verb.bzl passes it as `_tool`), so
    `paperkit/` is not on disk beside it and an engine import would fail in the one environment
    that matters most.  boundaries_write_atomic.py asserts the two implementations behave
    identically, so the copy cannot drift into a second behaviour unnoticed.

    Why it matters here: a verdict record is the artifact every other verdict is aggregated from,
    so a torn or twin-corrupted one is a wrong ANSWER rather than a broken file.
    """
    import os
    import tempfile
    path = pathlib.Path(path)
    try:                               # preserve the target's mode — mkstemp creates at 0600
        keep = os.stat(path).st_mode & 0o7777
    except FileNotFoundError:
        u = os.umask(0)
        os.umask(u)
        keep = 0o666 & ~u
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data)
        os.chmod(tmp, keep)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write(out, verb, verdict, why=""):
    """Ζ·cohere·mute — the record may CARRY ITS REASON, and omitting it is a lossy verdict.

    `why` is optional and absent from the JSON when empty, so every existing record is
    byte-identical and every consumer that reads `verdict` alone is unaffected — the same
    non-breaking widening `resolver.Verdict` took for UNAVAILABLE ("if a consumer ever measures a
    need, it widens WITHOUT touching pass/fail").

    ⚑ WHY A RECORD AND NOT JUST STDERR.  `:cohere`'s stderr already reaches the build log, and
    that was not enough: a red `@paperkit_paper//:cohere` wrote `{"verb":"cohere","verdict":"fail"}`
    and the test log said, in as many words, "no per-claim record names a failure — the aggregate
    is the only signal".  Six faces and ~90 claims behind one bit.  Diagnosing it meant hand-
    diffing two `.sens.json` fingerprints to find which grounding edge was disjoint — a
    measurement the tool had already made and discarded at the layer that records it.  A log line
    is read by whoever is watching; a record is read by whatever comes next.
    """
    if verdict is True or verdict is False:
        verdict = "pass" if verdict else "fail"
    rec = {"verb": verb, "verdict": verdict}
    if why:
        rec["why"] = why
    _write_atomic(out, json.dumps(rec, separators=(",", ":")) + "\n")


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
        # Ζ·tier·exit — pk_cmd passes pass|fail|cannot-run; anything else is a caller bug → fail closed.
        v = a.ok if a.ok in ("pass", "fail", "cannot-run") else "fail"
        _write(a.out, a.verb, v)
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
        # CONCURS — the producers' full outputs are all byte-equal (one distinct TEXT), none failed.
        # (Not one distinct LINE: a producer output is a whole document; collapsing to lines would
        # demand every producer be a single line — which reds two byte-identical multi-line documents.)
        texts = [pathlib.Path(p).read_text() for p in a.produced]
        distinct = set(texts)
        _write(a.out, a.verb, len(texts) >= 2 and len(distinct) == 1 and "__FAIL__" not in next(iter(distinct)))
    elif a.cmd == "calc":
        _write(a.out, a.verb, bool(json.loads(pathlib.Path(a.calc).read_text()).get("baseline")))
    elif a.cmd == "cohere":
        # Ζ·cohere·mute — let coherence's stderr through.  DEVNULL on BOTH streams meant a red
        # :cohere could only ever say {"verdict":"fail"}: the named misses were computed and
        # thrown away at the one layer that reads them.  stdout stays muted (the --from-calcs arm
        # prints no report there), stderr carries the residual, on its own handle — never merged,
        # since the caller parses this process's own stdout ([[separate-filehandles]]).
        #
        # ⚑⚑ AND THE RECORD CARRIES IT TOO.  Letting stderr through fixed the LOG; the RECORD
        # still said only `{"verdict":"fail"}`, so a red :cohere named neither the face nor the
        # edge to anything that reads records rather than watches a build.  stderr is TEE'd — it
        # still reaches the terminal (a caller watching the build must not lose it) AND lands in
        # the verdict's `why`, capped, so the failure travels with the artifact.
        p = subprocess.run([sys.executable, "paperkit/coherence.py", "--from-calcs", a.project, *a.calcs],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if p.stderr:
            print(p.stderr, end="", file=sys.stderr)
        # The LAST lines carry the diagnosis (the faces print progress before the residual), and a
        # record is not a transcript — 2000 chars is enough for the named misses and bounded
        # enough that a verdict stays a verdict.
        why = p.stderr.strip()[-2000:] if p.returncode != 0 else ""
        # ⚑ Ζ·verdict·tristate — 0/1/2 ARE THREE STATES, AND `rc == 0` KEPT TWO.  coherence.py
        # returns 1 for a real refutation (`_grounding_exit`: N un-acknowledged rests-on edges)
        # and 2 for a reading it could not honestly make (`Ν·partial`, a calc set covering part
        # of the graph; `_vacuous_exit`).  Collapsing those to "fail" scores a CANNOT-RUN as a
        # refutation — the exact fold this file's own header refuses for `pk_cmd` ("a cannot-run
        # is NOT a failure ... no false-red on a toolchain-less box, no false-green"), applied
        # everywhere except here.  Found while fixing the mute record: the partial-reading probe
        # wrote `"verdict":"fail"` for a run that had explicitly declined to judge.
        verdict = "pass" if p.returncode == 0 else ("cannot-run" if p.returncode == 2 else "fail")
        _write(a.out, a.verb, verdict, why)
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
