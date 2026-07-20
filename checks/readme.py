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
import resolver  # noqa: E402  — for VERBS, the engine's OWN verb set (never re-listed here)
import project as P  # noqa: E402
import _fixture as fx  # noqa: E402

GATE_SRC = (ENGINE / "gate.py").read_text()
RESOLVER_SRC = (ENGINE / "resolver.py").read_text()   # the check-resolution core (split out of gate)
DISC_SRC = (ENGINE / "discriminate.py").read_text()
GRADER_SRC = (ENGINE / "grader.py").read_text()       # the mutation sweep (split out of discriminate)
GRADE_SRC = (ENGINE / "grade.py").read_text()         # the grade ladder + interpretation (Μ·grade, split out of grader)


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
    # the gate ENFORCES three invariants — violating each makes it RED (projection-equality,
    # check-resolution; coverage is entailed by a faithful projection).  Behavioral (Ε·behavioral).
    w = [fx.entry("x", claim="content", check="cmd:true")]
    good = fx.project_text(w)
    assert fx.gate(w, out=good)[0] == 0, "a faithful, verified document should pass"
    assert fx.gate(w, out=good + "\nDRIFT\n")[0] != 0, "projection-equality not enforced"
    bad = [fx.entry("x", claim="content", check="cmd:false")]
    assert fx.gate(bad, out=fx.project_text(bad))[0] != 0, "check-resolution not enforced"


def rm_resolver():
    # a verifier is NAMED type:target (the type prefix selects the verb), one verb ships per
    # resolution KIND, and an unregistered type resolves through none (the set is CLOSED).
    # Λ·registry: the verbs are READ from resolver.VERBS — no count, no list, nothing to drift.
    # Behavioral (Ε·behavioral).
    assert gate.resolves("cmd:true", ENGINE, {}) is True and gate.resolves("file:true", ENGINE, {}) is False, \
        "the type prefix does not select the verb (a verifier is named type:target)"
    assert gate.resolves("file:gate.py", ENGINE, {}) is True, "file: verb"
    assert gate.resolves("agree:printf 42 ||| printf 42", ENGINE, {}) is True, "agree: verb"
    # every DECLARED verb is a real dispatch: an unknown target under a declared verb must come back
    # False (resolved and failed), never crash — whereas an undeclared TYPE is refused outright.
    for typ in resolver.VERBS:
        assert gate.resolves(f"{typ}:no-such-target-{typ}", ENGINE, {}) is False, \
            f"{typ}: is declared in VERBS but does not dispatch to a real branch"
    assert gate.resolves("nosuchverb:x", ENGINE, {}) is False, "an unregistered type resolved — the built-in set is not closed"


def rm_resolver_cmd():
    # cmd is the escape hatch every check reduces to; a new domain adds types via config
    assert gate.resolves("demo:x", ENGINE, {"demo": {"cmd": "true"}}) is True, "a config-supplied type does not resolve"
    assert gate.resolves("demo:x", ENGINE, {}) is False, "an unregistered type resolved"


def rm_resolver_premise():
    # `premise` is a PROVENANCE kind the footnote/plain render reads off a check (project._verify_note),
    # NOT one of the built-in resolving verbs — it surfaces an honest "not machine-checked" note and does
    # NOT dispatch in the gate's CLOSED built-in set.  Behavioral: drop the premise branch from
    # _verify_note, or let premise sneak in as a resolving verb, and this flips.
    assert "not machine-checked" in P._verify_note("premise:the-axiom"), \
        "the premise provenance note does not surface 'not machine-checked'"
    assert "Machine-verified" in P._verify_note("cmd:true"), "the cmd provenance note regressed"
    assert "Agda-proved" in P._verify_note("agda:Foo.bar"), "the agda provenance note regressed"
    assert gate.resolves("premise:x", ENGINE, {}) is False, \
        "premise resolved as a built-in gate verb — it must be a provenance KIND, not a verb"


# rm_delta REMOVED — the adequacy pitch is now imported from the concept library as [@adequacy-pitch]
# and witnessed by the SHARED checks/concepts.py (which RUNS the grader over a fixture, a stronger
# witness than this used to be by grepping engine source).

def rm_next():
    # the roadmap is still pending: no packaged CLI or PDF renderer yet (when one ships,
    # this fails and the README's 'next' list must be updated)
    assert not (ENGINE / "cli.py").exists() and not (ROOT / "mkdocx.sh").exists(), \
        "a roadmap 'next' item shipped — update the README"


# ── the local-CI + example-asset claims: each EXERCISES its proposition against the engine's
#    reality (parse the example, dispatch through the resolver, resolve real entrypoints), never a
#    `cmd:grep TOKEN FILE` over the asset — a grep proves a string appears, not that the example is
#    TRUE.  Each is falsifiable at the grid: a content-drop of the tabled token, a def-drop of the
#    exercised parser/resolver, or a drop of the referenced file flips it.
def rm_ci():
    # the local CI is the pre-commit githook: every commit runs `bazel test //:hook` (the one gate)
    hook = (ROOT / ".githooks" / "pre-commit").read_text()
    assert "bazel test //:hook" in hook, "the pre-commit hook does not run `bazel test //:hook`"


def rm_ci_enable():
    # the enable script configures git's hooksPath at the .githooks dir, where the real hook lives
    script = (ROOT / "assets" / "enable-hooks.sh").read_text()
    assert "core.hooksPath" in script and ".githooks" in script, \
        "the enable script does not configure core.hooksPath .githooks"
    assert (ROOT / ".githooks" / "pre-commit").exists(), \
        "the enabled hooks dir has no pre-commit hook"


def rm_cmds_eg():
    # the example commands invoke real engine entrypoints (project makes, gate verifies)
    cmds = (ROOT / "assets" / "commands.sh").read_text()
    assert "paperkit/project.py" in cmds and "paperkit/gate.py" in cmds, \
        "the commands example does not show the project + gate entrypoints"
    for tool in re.findall(r"paperkit/\S+\.py", cmds):
        assert (ROOT / tool).exists(), f"the example runs a non-existent entrypoint {tool}"


def rm_delta_cmds():
    # the Δ example runs the real discriminate entrypoint with a flag it actually defines
    cmds = (ROOT / "assets" / "delta-cmds.sh").read_text()
    assert "paperkit/discriminate.py" in cmds, "the Δ example does not run discriminate.py"
    assert (ENGINE / "discriminate.py").exists(), "discriminate.py (the Δ tool) is missing"
    assert "--min-strength" in cmds and "--min-strength" in DISC_SRC, \
        "the example uses a --min-strength flag discriminate.py does not define"


def rm_layout():
    # the layout doc names the real top-level components — each string is in the doc AND on disk
    # (a FILE per component, so the on-disk half is a clean single-artifact toggle, not a dir)
    layout = (ROOT / "assets" / "layout.txt").read_text()
    assert "paperkit/" in layout and "paper/" in layout and "README.md" in layout, \
        "the layout omits a top-level component"
    assert (ROOT / "paperkit" / "gate.py").exists() and (ROOT / "README.md").exists(), \
        "the layout describes components that are not on disk"


def rm_model_eg():
    # the example entry parses as a valid claim record through the engine's OWN bib parser
    recs = _parse((ROOT / "assets" / "claim.bib").read_text())
    assert len(recs) == 1, "the example is not a single claim record"
    rec = next(iter(recs.values()))
    for field in ("section", "from", "claim", "check"):
        assert rec.get(field), f"the example claim record is missing its {field}"


def rm_delta_tbl():
    # the grade table lists the grades the engine's ladder actually defines (each is in the doc AND
    # a real rung of grade.STRENGTH — drop one from the doc, or rename it in the ladder, and this fails)
    import grade  # noqa: E402
    tbl = (ROOT / "assets" / "grades.md").read_text()
    assert "vacuous" in tbl and "existence" in tbl and "behavioral" in tbl and "indeterminate" in tbl, \
        "the grade table omits a grade"
    for g in ("vacuous", "existence", "behavioral", "indeterminate"):
        assert g in grade.STRENGTH, f"the table lists {g} but the ladder does not define it"


def rm_resolver_tbl():
    # the table lists EXACTLY the engine's built-in verbs, and each is a REAL dispatch (not table text).
    # Λ·registry: the set is READ from resolver.VERBS, never re-listed here.  A witness that hardcodes
    # its own copy of the set it guards certifies a TAUTOLOGY — it stays green through exactly the drift
    # it exists to catch (this one did: after concept: shipped, deleting its table row kept it green).
    # So the assertion is set-EQUALITY, which fails on an omitted row AND on a row for a dead verb.
    tbl = (ROOT / "assets" / "resolver.md").read_text()
    tabled = set(re.findall(r"\|\s*`(\w+):", tbl))
    assert tabled == set(resolver.VERBS), \
        f"the resolver table and the engine's verb set disagree: {tabled ^ set(resolver.VERBS)}"
    # every COLUMN is derived too, not just the key — otherwise VERBS' arg/passes would be declared
    # data that nothing reads, and the table's gloss could drift while the row stayed present.
    for typ, spec in resolver.VERBS.items():
        arg = spec["arg"].replace("|", r"\|")          # markdown escapes agree:'s ||| separator
        row = f"| `{typ}:{arg}` | {spec['verb']} | {spec['passes']} |"
        assert row in tbl, f"the table's {typ}: row does not match the engine's declaration\n  want: {row}"
    assert gate.resolves("cmd:true", ENGINE, {}) is True and gate.resolves("file:gate.py", ENGINE, {}) is True, \
        "the tabled built-in verbs do not dispatch"
    assert gate.resolves("nosuchverb:x", ENGINE, {}) is False, "the built-in set is not closed"


def rm_resolver_eg():
    # the example config declares custom check types in the shape the resolver consumes, and the
    # engine dispatches a type declared that way
    import tomllib  # noqa: E402
    checks = tomllib.loads((ROOT / "assets" / "resolver.toml").read_text()).get("checks", {})
    assert checks, "the example declares no [checks.<type>]"
    for typ, spec in checks.items():
        assert "{target}" in spec.get("cmd", ""), f"[checks.{typ}] has no {{target}} cmd template"
    assert gate.resolves("demo:x", ENGINE, {"demo": {"cmd": "true {target}"}}) is True, \
        "the resolver does not dispatch a config-declared custom type"


CLAIMS = {
    "rm-pitch": rm_pitch, "rm-verifier": rm_verifier, "rm-noship": rm_noship,
    "rm-selfhost": rm_selfhost, "rm-model": rm_model, "rm-cmds": rm_cmds,
    "rm-cmds-inv": rm_cmds_inv, "rm-resolver": rm_resolver, "rm-resolver-cmd": rm_resolver_cmd,
    "rm-resolver-premise": rm_resolver_premise,
    "rm-next": rm_next,
    "rm-ci": rm_ci, "rm-ci-enable": rm_ci_enable, "rm-cmds-eg": rm_cmds_eg,
    "rm-delta-cmds": rm_delta_cmds, "rm-layout": rm_layout, "rm-model-eg": rm_model_eg,
    "rm-delta-tbl": rm_delta_tbl, "rm-resolver-tbl": rm_resolver_tbl, "rm-resolver-eg": rm_resolver_eg,
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
