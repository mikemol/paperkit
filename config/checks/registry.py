#!/usr/bin/env python3
# Ω·config·project witnesses — the knob union is well-formed, coverage is total, the knobs table
# is generated from the union (cannot drift), and resolve honours the precedence.  cwd = config/.
#
# Μ·kernel·shrink·registry: the knobs are DECLARED in the modules that RESOLVE them (the kernel
# hosts the mechanism only), so the union is INTROSPECTED — the host list comes from
# components.bzl (the partition's owner), never a hand-list, and the mechanism's precedence is
# proven on a SYNTHETIC Param (no coupling to any real knob).
import ast
import importlib
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path("../paperkit").resolve()))
import config as C  # noqa: E402


def union():
    """Every hosted Param, introspected over the engine's non-test modules (components.bzl is
    the owner of that list), in canonical order (by knob name)."""
    src = Path("../paperkit/components.bzl").read_text()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "COMPONENTS" for t in node.targets):
            comps = ast.literal_eval(node.value)
            break
    else:
        raise SystemExit("registry.py: no COMPONENTS literal in components.bzl")
    out = []
    for stem in (f[:-3] for c, fs in comps.items() if c != "tests" for f in fs):
        out += [v for v in vars(importlib.import_module(stem)).values() if isinstance(v, C.Param)]
    return sorted(out, key=lambda p: p.name)


def precedence():
    p = C.Param("syn-val", "PAPERKIT_SYN_VAL", config="syn_val", default="file", choices=("file", "def"))
    C._ARGS.clear(); os.environ.pop(p.env, None)
    assert C.resolve(p) == "file", "default"
    assert C.resolve(p, {"syn_val": "def"}) == "def", "config over default"
    os.environ[p.env] = "file"
    assert C.resolve(p, {"syn_val": "def"}) == "file", "env over config"
    C.apply_args(["--syn-val", "def"], [p])
    assert C.resolve(p, {"syn_val": "def"}) == "def", "arg over env"
    C._ARGS.clear(); os.environ.pop(p.env, None)


def well_formed():
    knobs = union()
    names = [p.name for p in knobs]
    envs = [p.env for p in knobs]
    assert len(names) == len(set(names)), "duplicate knob name"
    assert len(envs) == len(set(envs)), "duplicate env var"
    for p in knobs:
        assert p.env.startswith("PAPERKIT_"), f"{p.name}: env is not PAPERKIT_*"
        assert not (p.flag and p.choices), f"{p.name}: a flag declares choices"
        assert p.help, f"{p.name}: no help"


def covers():
    # total coverage: every knob is reachable by BOTH a CLI flag and an env var (container + ad-hoc)
    for p in union():
        assert p.cli and p.env, f"{p.name}: not reachable by both flag and env"


def fresh():
    gen = subprocess.run([sys.executable, "checks/gen_knobs.py"], capture_output=True, text=True, check=True).stdout
    assert Path("assets/knobs.md").read_text().strip() == gen.strip(), \
        "assets/knobs.md drifted from the knob union — regenerate (checks/gen_knobs.py)"


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
