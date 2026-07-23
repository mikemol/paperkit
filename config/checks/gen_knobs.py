#!/usr/bin/env python3
# Ω·config·project — emit the knobs table FROM the introspected knob union, so the documentation
# CANNOT drift from the code (each knob is declared in the module that resolves it —
# Μ·kernel·shrink·registry; registry.union() derives the host list from components.bzl).
# cwd = config/ ; ../paperkit = engine.
import sys
from pathlib import Path
sys.path.insert(0, str(Path("checks").resolve()))
from registry import union  # noqa: E402

rows = ["| knob | flag | env var | config | default |", "| --- | --- | --- | --- | --- |"]
for p in union():
    d = "—" if p.default is None else (p.default() if callable(p.default) else p.default)
    cfg = f"`{p.config}`" if p.config else "—"
    rows.append(f"| `{p.name}` ({'flag' if p.flag else 'value'}) | `{p.cli}` | `{p.env}` | {cfg} | `{d}` |")
print("\n".join(rows))
