#!/usr/bin/env python3
"""paperkit driver — a domain-free liveness driver for pump()/parse() witnesses.

The pump-ask protocol (received as a self-demonstrating paperkit Ask): a witness is
resumable in short increments, so a slow-but-sound check is never indistinguishable
from a broken one — it reads as "resume me", not as a falsified claim.  A witness
exposes five things:

    initial()            -> opaque, serializable state
    pump(state)          -> advanced state   (ONE natural increment; NO verdict)
    parse(state)         -> meaning          (done? / verdict / progress; lazy)
    serialize(state)     -> str              (the resumption token)
    deserialize(str)     -> state

The driver only ever: load-or-initialize -> pump -> serialize -> persist, repeat,
each call honoring a short budget and never blocking past one increment.  It never
inspects the state's internals (opaque token), and verdict policy lives in parse(),
not in the advance step.  Soundness obligation: deserialize(serialize(s)) == s.

    paperkit-driver <witness.py> [--state FILE] [--budget SECONDS]

DEGRADES GRACEFULLY: a witness that does not implement pump() is just run cold by
the existing cmd: contract; this driver is the optional resumable refinement.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path


def drive(w, state_path: str | None = None, budget: float = 0.0):
    """Advance witness `w` to done or budget.  Returns (meaning, steps, done).
    Persists the opaque resumption token to state_path between increments.
    budget <= 0 means run to completion (one blocking call — the cold fallback)."""
    if state_path and Path(state_path).exists():
        state = w.deserialize(Path(state_path).read_text())
    else:
        state = w.initial()
    # the one soundness obligation — a resumed run must equal an uninterrupted one
    assert w.deserialize(w.serialize(state)) == state, "state does not round-trip"
    start, steps = time.monotonic(), 0
    meaning = w.parse(state)
    while not meaning.get("done"):
        state = w.pump(state)               # advance exactly one increment
        steps += 1
        if state_path:                      # persist the opaque token; never inspected
            Path(state_path).write_text(w.serialize(state))
        meaning = w.parse(state)
        if budget and time.monotonic() - start >= budget:
            break                           # liveness: never block past the budget
    return meaning, steps, bool(meaning.get("done"))


def load(path: str):
    """Load an external witness module (initial/pump/parse/serialize/deserialize)."""
    spec = importlib.util.spec_from_file_location("paperkit_witness", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main(argv: list) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Drive a pump()/parse() witness in resumable increments.")
    ap.add_argument("witness", help="path to a witness module")
    ap.add_argument("--state", help="resumption-token file (persisted between calls)")
    ap.add_argument("--budget", type=float, default=0.0, help="seconds; <=0 = run to completion")
    a = ap.parse_args(argv)
    meaning, steps, done = drive(load(a.witness), a.state, a.budget)
    shown = {k: v for k, v in meaning.items() if k != "graded"}      # keep output small
    print(json.dumps({"steps": steps, "done": done, **shown}))
    return 0 if done else 2                  # 2 = not done → resume (NOT a failure)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
