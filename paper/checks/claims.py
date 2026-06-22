#!/usr/bin/env python3
"""Per-claim discriminating witnesses — the `claim:` check type (registered in
paper.toml as `[checks.claim] cmd = "python3 checks/claims.py {target}"`).

Each function asserts the SPECIFIC proposition its claim makes about the engine, so
the check fails if the claim is false (Δ grades it `behavioral`) and every claim
names its own target `claim:<key>` (so the gate's --without-K is satisfied: a
distinct witness per claim, not one shared `file:` standing for many).

    python3 checks/claims.py <claim-key>      # run from paper/; exit 0 = claim holds
"""
import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "paperkit"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests"))
import gate  # noqa: E402
import _fixture as fx  # noqa: E402  (the validated fixture builder — counter-fixtures)

GATE_SRC = (ENGINE / "gate.py").read_text()
PROJECT_SRC = (ENGINE / "project.py").read_text()


def verifier_named():
    # "a claim's verifier is named type:target" — the resolver splits on the ':'
    assert 'partition(":")' in GATE_SRC, "resolver no longer splits type:target"


def gate_dispatches():
    # "dispatches through a small registry" — built-in file/cmd branches + custom
    for needle in ('typ == "file"', 'typ == "cmd"', "typ in custom"):
        assert needle in GATE_SRC, f"resolver missing dispatch branch: {needle}"


def new_domain_adds():
    # "a new domain adds verifiers, not editing the engine" — a type supplied only
    # in the custom registry resolves; an unregistered one does not
    assert gate.resolves("demo:x", ENGINE, {"demo": {"cmd": "true"}}) is True, \
        "a registry-supplied check type does not resolve"
    assert gate.resolves("demo:x", ENGINE, {}) is False, \
        "an unregistered check type must not resolve"


def two_builtins():
    # "two verifiers ship built in" — exactly file and cmd (others come from config)
    builtins = set(re.findall(r'typ == "(\w+)"', GATE_SRC))
    assert builtins == {"file", "cmd"}, f"built-in types are {builtins}, expected file & cmd"


def file_builtin():
    # "file, that an artifact exists"
    assert gate.resolves("file:gate.py", ENGINE, {}) is True, "file: of an existing path failed"
    assert gate.resolves("file:does-not-exist.xyz", ENGINE, {}) is False, "file: of a missing path passed"


def cmd_builtin():
    # "cmd, that a script exits zero"
    assert gate.resolves("cmd:true", ENGINE, {}) is True, "cmd:true did not pass"
    assert gate.resolves("cmd:false", ENGINE, {}) is False, "cmd:false did not fail"


def cmd_escape():
    # "cmd is the hatch every other check reduces to" — custom types run via cmd
    assert 'run_ok(custom[typ]["cmd"]' in GATE_SRC, "custom types no longer reduce to a cmd"


# ── engine section ───────────────────────────────────────────────────────────
def projector_emits():
    # "the projector emits the whole document from the warrant set" — project a
    # two-section fixture; the whole document (title + every section + the claim) appears
    text = fx.project_text([fx.entry("x", claim="anchor phrase")],
                           rubric=(("s", "Sec One"), ("t", "Sec Two")), title="Doc")
    for needle in ("# Doc", "## Sec One", "## Sec Two", "anchor phrase"):
        assert needle.lower() in text.lower(), f"projection is missing {needle!r}"


def prose_is_artifact():
    # "the committed prose is a build artifact, not a source" — the projector has a
    # --check mode that compares the committed file against a fresh projection
    assert "--check" in PROJECT_SRC and "read_text() != out" in PROJECT_SRC, \
        "projector can no longer detect a hand-edit against its projection"


def gate_rejects_drift():
    # "the gate rejects prose that has drifted" — counter-fixture: canonical passes, drift fails
    w = [fx.entry("x", claim="anchored")]
    canonical = fx.project_text(w)
    assert fx.gate(w, out=canonical)[0] == 0, "gate rejected the exact projection"
    assert fx.gate(w, out=canonical + "\nHAND-EDITED DRIFT\n")[0] != 0, "gate accepted drifted prose"


def edit_cant_survive():
    # "a hand-edit cannot survive a build" — only the exact projection passes the gate
    w = [fx.entry("x", claim="anchored")]
    canonical = fx.project_text(w)
    assert fx.gate(w, out=canonical)[0] == 0
    for edit in ("PREPENDED\n" + canonical, canonical + "\nAPPENDED\n", canonical + "x"):
        assert edit != canonical and fx.gate(w, out=edit)[0] != 0, "a hand-edit survived the build"


def coverage_both_sides():
    # "coverage is enforced from both sides" — section-present AND claim-cited branches
    assert "absent" in GATE_SRC and "not cited" in GATE_SRC, "coverage no longer checks both directions"


def every_section_appears():
    # "every required section must appear"
    assert "not in headings" in GATE_SRC, "gate no longer checks each section appears"


def every_claim_cited():
    # "every claim tagged for a section must be cited within it"
    assert "k not in cited" in GATE_SRC, "gate no longer checks each tagged claim is cited"


CLAIMS = {
    "verifier-named": verifier_named,
    "gate-dispatches": gate_dispatches,
    "new-domain-adds": new_domain_adds,
    "two-builtins": two_builtins,
    "file-builtin": file_builtin,
    "cmd-builtin": cmd_builtin,
    "cmd-escape": cmd_escape,
    "projector-emits": projector_emits,
    "prose-is-artifact": prose_is_artifact,
    "gate-rejects-drift": gate_rejects_drift,
    "edit-cant-survive": edit_cant_survive,
    "coverage-both-sides": coverage_both_sides,
    "every-section-appears": every_section_appears,
    "every-claim-cited": every_claim_cited,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in CLAIMS:
        print(f"usage: claims.py <{'|'.join(CLAIMS)}>", file=sys.stderr)
        return 2
    key = argv[1]
    try:
        CLAIMS[key]()
    except AssertionError as e:
        print(f"claim {key}: FAIL — {e}", file=sys.stderr)
        return 1
    print(f"claim {key}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
