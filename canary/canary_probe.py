"""Ζ·canary — the PROBE: one def whose body the pos cell drops.  Deliberately OUTSIDE
//paperkit:engine (not in components.bzl), so ·gen·surface never sweeps it and no claim's
closure ever stages it — it exists only for the harness's positive control."""


def truth():
    return 42
