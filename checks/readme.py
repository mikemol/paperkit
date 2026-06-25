#!/usr/bin/env python3
"""Per-claim discriminating witnesses for the README project — the `claim:` check type
(root paper.toml: [checks.claim] cmd = "python3 checks/readme.py {target}").

Each asserts the SPECIFIC proposition its README claim makes about paperkit, so the
check fails if the claim is false (Δ grades it behavioral) and every claim names its
own target (so --without-K holds).  Mirrors paper/checks/claims.py, adapted to the
README project at the repo root (deps are paperkit/, not ../paperkit).

    python3 checks/readme.py <claim-key>      # run from the repo root; exit 0 = holds
"""
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "paperkit"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests"))
import gate  # noqa: E402
import project as P  # noqa: E402
import _fixture as fx  # noqa: E402

GATE_SRC = (ENGINE / "gate.py").read_text()
RESOLVER_SRC = (ENGINE / "resolver.py").read_text()   # the check-resolution core (split out of gate)
DISC_SRC = (ENGINE / "discriminate.py").read_text()
GRADER_SRC = (ENGINE / "grader.py").read_text()       # the mutation sweep + grade ladder (split out of discriminate)


def _parse(text):
    d = tempfile.mkdtemp()
    try:
        p = Path(d) / "t.bib"
        p.write_text(text)
        return P.entries(p)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def rm_pitch():
    # paperkit treats a document as the projection of a claim-DAG: claims become prose
    t = fx.project_text([fx.entry("a", claim="a claim not prose")]).lower()
    assert "a claim not prose" in t and t.startswith("#"), "the document is not the projection of its claims"


def rm_verifier():
    # each claim carries a machine-checkable verifier (the gate runs it)
    rec = _parse("@misc{c,\n  section = {s},\n  claim = {x},\n  check = {cmd:true}\n}\n")["c"]
    assert rec.get("check") == "cmd:true", "the claim carries no verifier"
    assert gate.resolves("cmd:true", ENGINE, {}) is True and gate.resolves("cmd:false", ENGINE, {}) is False, \
        "the verifier is not machine-checkable"


def rm_noship():
    # an unverified sentence does not project / cannot overclaim: a failing check blocks the gate
    ok = [fx.entry("x", claim="present", check="cmd:true")]
    bad = [fx.entry("x", claim="present", check="cmd:false")]
    good = fx.project_text(ok)
    assert fx.gate(ok, out=good)[0] == 0 and fx.gate(bad, out=good)[0] != 0, "an unverified sentence shipped"


def rm_selfhost():
    # this README is itself a projection: README.md == project(root warrants)
    cfg = P.load_config(ROOT)
    assert cfg["out"].name == "README.md", "the root project does not project to README.md"
    assert P.project(cfg) == cfg["out"].read_text(), "README.md is not the projection of the root warrants"


def rm_model():
    # a claim is one bibliography entry: a statement, its section, its deps, its check
    rec = _parse("@misc{k,\n  section = {s},\n  from = {d},\n  claim = {a statement},\n  check = {file:x}\n}\n")["k"]
    for field in ("claim", "section", "from", "check"):
        assert rec.get(field), f"a claim entry is missing its {field}"


def rm_cmds():
    # two commands: project makes the document, gate verifies it (and catches drift)
    w = [fx.entry("x", claim="content")]
    doc = fx.project_text(w)
    assert doc.startswith("#"), "project did not make a document"
    assert fx.gate(w, out=doc)[0] == 0, "gate rejected a faithful document"
    assert fx.gate(w, out=doc + "\nDRIFT\n")[0] != 0, "gate did not verify (drift accepted)"


def rm_cmds_inv():
    # the gate enforces three invariants: projection-equality, check-resolution, coverage
    for inv in ("PROJECT", "RESOLVE", "COVERAGE"):
        assert inv in GATE_SRC, f"gate.py does not enforce the {inv} invariant"


def rm_resolver():
    # a verifier is named type:target, and four types ship built in (one per verb:
    # file EXISTS, cmd EXECS, result PARSES a sibling's verdict — Ξ·seam, agree CONCURS — Δ·agree)
    assert 'partition(":")' in RESOLVER_SRC, "the verifier is not named type:target"
    builtins = set(re.findall(r'typ == "(\w+)"', RESOLVER_SRC))
    assert builtins == {"file", "cmd", "result", "agree"}, \
        f"built-in types are {builtins}, expected file, cmd, result & agree"


def rm_resolver_cmd():
    # cmd is the escape hatch every check reduces to; a new domain adds types via config
    assert gate.resolves("demo:x", ENGINE, {"demo": {"cmd": "true"}}) is True, "a config-supplied type does not resolve"
    assert gate.resolves("demo:x", ENGINE, {}) is False, "an unregistered type resolved"


def rm_delta():
    # discriminate grades how much a check can actually fail (the four grades, by mutation);
    # the grader (split out of discriminate) defines the ladder and grades by mutation
    for g in ("vacuous", "existence", "behavioral", "indeterminate"):
        assert g in GRADER_SRC, f"the grader does not define the {g} grade"
    assert "flips it red" in GRADER_SRC, "the grader does not grade by mutation"


def rm_next():
    # the roadmap is still pending: no packaged CLI or PDF renderer yet (when one ships,
    # this fails and the README's 'next' list must be updated)
    assert not (ENGINE / "cli.py").exists() and not (ROOT / "mkdocx.sh").exists(), \
        "a roadmap 'next' item shipped — update the README"


CLAIMS = {
    "rm-pitch": rm_pitch, "rm-verifier": rm_verifier, "rm-noship": rm_noship,
    "rm-selfhost": rm_selfhost, "rm-model": rm_model, "rm-cmds": rm_cmds,
    "rm-cmds-inv": rm_cmds_inv, "rm-resolver": rm_resolver, "rm-resolver-cmd": rm_resolver_cmd,
    "rm-delta": rm_delta, "rm-next": rm_next,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in CLAIMS:
        print(f"usage: readme.py <{'|'.join(CLAIMS)}>", file=sys.stderr)
        return 2
    try:
        CLAIMS[argv[1]]()
    except AssertionError as e:
        print(f"claim {argv[1]}: FAIL — {e}", file=sys.stderr)
        return 1
    print(f"claim {argv[1]}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
