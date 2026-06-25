#!/usr/bin/env python3
# Ω·config·project witnesses — the registry is well-formed, coverage is total, the knobs table is
# generated from the registry (cannot drift), and resolve honours the precedence.  cwd = config/.
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path("../paperkit").resolve()))
import config as C  # noqa: E402


def precedence():
    p = C.RESOLUTION
    C._ARGS.clear(); os.environ.pop(p.env, None)
    assert C.resolve(p) == "file", "default"
    assert C.resolve(p, {"resolution": "def"}) == "def", "config over default"
    os.environ[p.env] = "file"
    assert C.resolve(p, {"resolution": "def"}) == "file", "env over config"
    C.apply_args(["--resolution", "def"])
    assert C.resolve(p, {"resolution": "def"}) == "def", "arg over env"
    C._ARGS.clear(); os.environ.pop(p.env, None)


def well_formed():
    names = [p.name for p in C.REGISTRY]
    envs = [p.env for p in C.REGISTRY]
    assert len(names) == len(set(names)), "duplicate knob name"
    assert len(envs) == len(set(envs)), "duplicate env var"
    for p in C.REGISTRY:
        assert p.env.startswith("PAPERKIT_"), f"{p.name}: env is not PAPERKIT_*"
        assert not (p.flag and p.choices), f"{p.name}: a flag declares choices"
        assert p.help, f"{p.name}: no help"


def covers():
    # total coverage: every knob is reachable by BOTH a CLI flag and an env var (container + ad-hoc)
    for p in C.REGISTRY:
        assert p.cli and p.env, f"{p.name}: not reachable by both flag and env"


def fresh():
    gen = subprocess.run([sys.executable, "checks/gen_knobs.py"], capture_output=True, text=True, check=True).stdout
    assert Path("assets/knobs.md").read_text().strip() == gen.strip(), \
        "assets/knobs.md drifted from the registry — regenerate (checks/gen_knobs.py)"


CHECKS = {"precedence": precedence, "well-formed": well_formed, "covers": covers, "fresh": fresh}


def main(argv):
    if len(argv) != 2 or argv[1] not in CHECKS:
        print(f"usage: registry.py <{'|'.join(CHECKS)}>", file=sys.stderr)
        return 2
    try:
        CHECKS[argv[1]]()
    except AssertionError as e:
        print(f"config {argv[1]}: FAIL — {e}", file=sys.stderr)
        return 1
    print(f"config {argv[1]}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
