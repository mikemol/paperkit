#!/usr/bin/env python3
"""Ζ·sweep·budget — the RAM budget for the mutation sweep (--local_ram_resources), resolved
arg > env > topology-derived default.  A BUILD-ORCHESTRATION value (a Bazel scheduler flag), so it
lives here and is passed to the `bazel test //:hook` line by the pre-commit — NOT an engine
config.Param (the engine grades documents; it does not schedule the build).

WHY A KNOB, NOT A RUNTIME READ.  The sweep's def-resolution cells each reserve ~2GB (Τ·mem _RS), so a
budget of B MB runs ~B/2048 concurrent cells.  The right B is a FORWARD claim about a workload that has
not run, on a machine that leans on zram/zswap.  On such a box MemAvailable is deliberately low (zram
absorbs pressure), so budgeting against it would serialize the sweep to ~1 cell on a box that is fine;
and no /proc number expresses "how much can this box's compressed swap absorb before real thrash" —
that is future-workload compressibility × the operator's thrash tolerance, which is CONFIG.

DERIVE THE DEFAULT, CONFIG THE VALUE.  A backward-looking measurement (this box's real RAM) FLOORS the
forward budget: a conservative fraction of MemTotal that leaves headroom for the OS + baseline working
sets, counting only REAL RAM (zram is the SAFETY the cgroup cap spends, never budget the scheduler
does).  The operator RAISES that floor via PAPERKIT_SWEEP_RAM_MB when their box tolerates more — that
override is where the un-derivable forward judgment lives.  (The derive-default discipline holds here
because the measurement floors the value; where no proxy floors it, the default would be a labelled
guess, not a derivation.)

    sweep_budget.py                         # the resolved budget in MB (for --local_ram_resources)
    PAPERKIT_SWEEP_RAM_MB=9000 sweep_budget.py   # operator override wins
"""
import os
import sys


def _mem_total_mb() -> int:
    """This box's real RAM in MB (the backward measurement that floors the forward budget)."""
    for line in open("/proc/meminfo"):
        if line.startswith("MemTotal"):
            return int(line.split()[1]) // 1024
    return 0


# The conservative fraction of real RAM the sweep may claim by default: enough for a few concurrent
# def-cells, leaving the rest for the OS + whatever else shares the box.  Deliberately a FLOOR — the
# operator raises it.  0.4 of MemTotal ≈ the 6GB that was independently measured-safe on the dev box.
_DEFAULT_FRACTION = 0.4


def budget_mb() -> int:
    """The mutation-sweep RAM budget in MB: PAPERKIT_SWEEP_RAM_MB if set (the operator's forward
    judgment), else the topology-derived conservative floor (MemTotal × the default fraction).
    """
    override = os.environ.get("PAPERKIT_SWEEP_RAM_MB")
    if override:
        return int(override)
    return int(_mem_total_mb() * _DEFAULT_FRACTION)


if __name__ == "__main__":
    print(budget_mb())
