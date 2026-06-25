#!/usr/bin/env python3
# Ω·config·project — emit the knobs table FROM the registry, so the documentation CANNOT drift
# from the code (the registry is the single source of truth).  cwd = config/ ; ../paperkit = engine.
import sys
from pathlib import Path
sys.path.insert(0, str(Path("../paperkit").resolve()))
import config as C  # noqa: E402

rows = ["| knob | flag | env var | config | default |", "| --- | --- | --- | --- | --- |"]
for p in C.REGISTRY:
    d = "—" if p.default is None else (p.default() if callable(p.default) else p.default)
    cfg = f"`{p.config}`" if p.config else "—"
    rows.append(f"| `{p.name}` ({'flag' if p.flag else 'value'}) | `{p.cli}` | `{p.env}` | {cfg} | `{d}` |")
print("\n".join(rows))
