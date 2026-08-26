#!/usr/bin/env python3
"""Τ·mem·zswap — sample a cgroup's memory + zswap counters in ONE pass.

Why one pass: linux-sources-30 measured cross-surface equality holding at rest and FAILING live
under reclaim — two selftest arms comparing /proc/vmstat against memory.stat skewed because they
sampled separately.  An exact comparison between counters is a claim about an idle box, so read
the pair together and treat the ratio as an observation, not an identity.

Emits one JSON object for the caller's OWN cgroup (leaf = the action's, under Bazel's
blaze_<pid>_spawns.slice/sandbox_N.scope):

    current      memory.current              bytes charged NOW
    peak         memory.peak                 high-water (per-fd semantics; see below)
    zswap        memory.stat `zswap`         bytes CONSUMED BY THE BACKEND (compressed)
    zswapped     memory.stat `zswapped`      bytes of APPLICATION memory swapped out
    zswap_max    memory.zswap.max            the pool ceiling, or "max"

`zswap` and `zswapped` are DIFFERENT UNITS and their pair gives the compression ratio directly.
The ratio matters because obj_cgroup_charge_zswap charges entry->length — the COMPRESSED size —
so a page moved to zswap is re-charged smaller rather than leaving the charge: memory.current
FALLS as pages compress, and two workloads with identical RSS report different peaks.

Scope: measured against linux-source 7.0.0-30.30.  These are claims about THIS pin.
"""
import json
import sys
from pathlib import Path


def cg_dir() -> Path:
    rel = Path("/proc/self/cgroup").read_text().strip().split("::")[-1]
    return Path("/sys/fs/cgroup") / rel.lstrip("/")


def read(d: Path, name: str):
    """A file's value, or an UNAVAILABLE reason — never a 0 standing in for a failed read."""
    f = d / name
    if not f.exists():
        return {"unavailable": "absent"}
    try:
        return f.read_text().strip()
    except OSError as e:
        return {"unavailable": f"unreadable:{e.errno}"}


def stat_keys(d: Path, keys):
    raw = read(d, "memory.stat")
    if isinstance(raw, dict):
        return {k: raw for k in keys}
    got = dict(l.split(" ", 1) for l in raw.splitlines() if " " in l)
    return {k: (int(got[k]) if k in got else {"unavailable": "key-absent"}) for k in keys}


# Ρ·mem·zswap·validity — a sample mixes TWO KINDS of reading and a later reader must not take the
# row as one kind.  current/zswap/zswapped are INSTANTANEOUS; peak is CUMULATIVE since cgroup
# creation on a never-written fd (per-fd reset semantics), so on a long-lived cgroup it spans
# unrelated history and is not comparable to a short-lived action's peak.  Labelled per FIELD.
_VALIDITY = {"current": "instantaneous", "zswap": "instantaneous", "zswapped": "instantaneous",
             "zswap_max": "config", "peak": "cumulative-since-cgroup-creation"}


def zswap_bound(leaf: Path) -> dict:
    """Ρ·mem·zswap·hierarchy — the EFFECTIVE zswap ceiling, walked leaf→root.

    obj_cgroup_may_zswap walks up to the root and refuses if ANY ancestor is at its zswap_max, so
    a parent's bound binds a child whose own file still reads "max".  Reading only the leaf can
    therefore report an unbounded pool while the pool is in fact bound one level up — and for a
    Bazel grid that is the operative case, since cells sit under blaze_<pid>_spawns.slice and
    inherit any bound placed above them without their own file changing.
    """
    levels, binding = [], None
    d = leaf
    root = Path("/sys/fs/cgroup")
    while True:
        v = read(d, "memory.zswap.max")
        cur = read(d, "memory.zswap.current")
        levels.append({"cgroup": str(d), "zswap_max": v, "zswap_current": cur})
        if isinstance(v, str) and v != "max" and binding is None:
            binding = str(d)                       # the nearest ancestor that can refuse a store
        if d == root:
            break
        d = d.parent
    return {"effective_bound_at": binding or "unbounded-to-root", "levels": levels}


def sample() -> dict:
    d = cg_dir()
    # ONE pass, in the tightest window available: stat first (it carries both zswap counters),
    # then the single-value files.  A wider window is a bigger skew under reclaim.
    st = stat_keys(d, ("zswap", "zswapped"))
    out = {"cgroup": str(d), "is_root": str(d) == "/sys/fs/cgroup",
           "current": read(d, "memory.current"), "peak": read(d, "memory.peak"),
           "zswap_max": read(d, "memory.zswap.max"), **st}
    z, zd = out.get("zswap"), out.get("zswapped")
    if isinstance(z, int) and isinstance(zd, int) and z > 0:
        # application bytes per backend byte.  UNBOUNDED this is compressibility; BOUNDED it also
        # encodes pool churn, because hitting the bound triggers writeback of existing entries
        # (shrink_memcg before declining) rather than a clean fall-through to the device.
        out["compression_ratio"] = round(zd / z, 3)
    # Ρ·mem·pinned — THE bit that makes a peak attributable.  memory.current PINS AT memory.max
    # under pressure while real demand keeps growing (measured: 704MB of demand reporting ~512MB
    # against a 512MB ceiling), so a reading taken while pinned says what the cell was GIVEN, not
    # what it NEEDED.  Without this one comparison every peak is ambiguous between those two, and
    # a reservation loop calibrating from it learns its own input back.
    cur, mx = out.get("current"), read(d, "memory.max")
    pinned = None
    if isinstance(cur, str) and cur.isdigit() and isinstance(mx, str) and mx.isdigit():
        c, m = int(cur), int(mx)
        # "at the ceiling" with a small tolerance: the charge sits a few pages under max while
        # reclaim keeps it there, so exact equality would miss the pinned case it exists to catch.
        pinned = m > 0 and (m - c) <= max(m // 100, 4096 * 64)
    out["memory_max"] = mx
    out["pinned_at_ceiling"] = pinned
    # a ratio's MEANING depends on whether the pool binds: unbounded it is compressibility,
    # bounded it is eviction churn.  Two quantities, one formula — so the state travels with it.
    hier = zswap_bound(d)
    if "compression_ratio" in out:
        out["ratio_means"] = ("compressibility" if hier["effective_bound_at"] == "unbounded-to-root"
                              else "eviction-churn-under-bound")
    # Ρ·mem·provenance — WHICH SETTINGS WERE IN EFFECT, recorded beside the number.  Three times in
    # one investigation a setting correct for its own purpose disabled a different capability with
    # no error: MemorySwapMax=0 made zswap unmeasurable, the observe flag living in the action key
    # made cached cells stale, and --experimental_sandbox_memory_limit_mb gated whether a per-action
    # cgroup existed to read at all.  Three is a population, not three accidents — so a reading
    # carries the conditions that decide whether it is a measurement or an artifact, the same way a
    # source quote carries its version pin.
    out["_conditions"] = {
        "swap_max": read(d, "memory.swap.max"),        # 0 ⇒ zswap can never be exercised here
        "own_cgroup": not str(d).endswith(".scope") or "sandbox" in str(d) or "run-p" in str(d),
        "cgroup_is_leaf": not any(x.is_dir() and (x / "cgroup.procs").exists()
                                  for x in d.iterdir()) if d.is_dir() else None,
    }
    out["hierarchy"] = hier
    out["_validity"] = dict(_VALIDITY, memory_max="config", pinned_at_ceiling="derived",
                            ratio_means="derived")
    return out


def _selftest() -> int:
    """⟨P, F, δ⟩ over the PINNED predicate — VALID mutants only.

    The trap (linux-sources-30): mutating the ceiling so the cgroup becomes genuinely pinned is an
    INVALID mutant — the field flipping is the predicate being RIGHT, not the check being
    sensitive.  A valid mutant leaves the world untouched and corrupts the COMPARISON, then asks
    whether the witness notices.  A surviving mutant means either a weak predicate or a mutation
    that failed to mutate, and only reading both sides says which.

      P: intact, a saturated pair reads pinned and an unsaturated pair does not
      F: sign-swapped gap / tolerance widened to 1GB / tolerance driven to 0 each destroy the
         separation, and the requirement (sat AND NOT unsat) catches all three
      δ: the comparison itself — no system state changes between the arms
    """
    SAT, UNSAT = ("402632704", "402653184"), ("100000000", "402653184")

    def pinned(cur, mx, tol_rel=100, tol_abs=4096 * 64, flip=False):
        c, m = int(cur), int(mx)
        gap = (c - m) if flip else (m - c)
        return m > 0 and gap <= max(m // tol_rel, tol_abs)

    def separates(**kw):
        return pinned(*SAT, **kw) and not pinned(*UNSAT, **kw)

    fails = []
    if not separates():
        fails.append("P: intact predicate does not separate saturated from unsaturated")
    for name, kw in (("sign-swapped gap", {"flip": True}),
                     ("tolerance widened to 1GB", {"tol_abs": 10 ** 9}),
                     ("tolerance driven to 0", {"tol_abs": 0, "tol_rel": 10 ** 9})):
        if separates(**kw):
            fails.append(f"F: mutant '{name}' SURVIVED — the predicate is not reading the gap")
    for f in fails:
        print(f"  XX {f}", file=sys.stderr)
    print("ZSWAP_PROBE SELFTEST: " + ("PASS (1 P-arm, 3 valid mutants caught)" if not fails
                                      else f"FAIL ({len(fails)})"))
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    print(json.dumps(sample(), indent=2))
