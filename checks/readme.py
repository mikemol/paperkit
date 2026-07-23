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

# (Μ·kernel·fixture·reads — no module-level source reads: a witness that inspects a module's
# SOURCE reads it inside its own body, so only that witness stages the module and sweeps its
# sites.  Four of the five constants that used to sit here were DEAD reads — staged inputs of
# every row, used by none.)


def _parse(text):
    d = tempfile.mkdtemp()
    try:
        p = Path(d) / "t.bib"
        p.write_text(text)
        return P.entries(p)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def rm_selfhost():
    # this README is itself a projection: README.md == project(root warrants)
    cfg = P.load_config(ROOT)
    assert cfg["out"].name == "README.md", "the root project does not project to README.md"
    assert P.project(cfg) == cfg["out"].read_text(), "README.md is not the projection of the root warrants"


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
    assert "--min-strength" in cmds and "--min-strength" in (ENGINE / "discriminate.py").read_text(), \
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
    # the grade table lists EXACTLY the rungs the engine's ladder defines, in RANK ORDER.
    # Ζ·ladder: read from grade.py, never re-listed here.  The old form hardcoded its own 4-tuple
    # and asserted only membership, so it was green while the table omitted `broken` and
    # `imported` — a witness that carries its own copy of the set it guards proves a tautology.
    import grade  # noqa: E402
    tbl = (ROOT / "assets" / "grades.md").read_text()
    tabled = re.findall(r"\| `(\w+)` \|", tbl)
    assert tabled == grade.rungs(), \
        f"the grade table and the engine's ladder disagree: table={tabled} ladder={grade.rungs()}"


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
    "rm-selfhost": rm_selfhost,
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
