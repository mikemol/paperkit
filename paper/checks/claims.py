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
import gate  # noqa: E402

GATE_SRC = (ENGINE / "gate.py").read_text()


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


CLAIMS = {
    "verifier-named": verifier_named,
    "gate-dispatches": gate_dispatches,
    "new-domain-adds": new_domain_adds,
    "two-builtins": two_builtins,
    "file-builtin": file_builtin,
    "cmd-builtin": cmd_builtin,
    "cmd-escape": cmd_escape,
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
