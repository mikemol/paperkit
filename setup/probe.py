#!/usr/bin/env python3
"""Two-phase probes for the setup project.

The probe is split the way a paperkit witness is — pump / interpret:

  pump()              RETRIEVES the machine's readings from /proc and /sys and
                      INTERNS them into one state object (a plain dict).  This is
                      the side-effecting half: it touches the live kernel.
  FACTS[name](state)  INTERPRETS that interned state into a yes/no verdict.  Pure
                      functions of the dict — they never touch the kernel.

Because interpretation is a pure function of the interned state, the same facts
can be checked two ways:

    probe.py <fact>                  pump() live, then interpret   (machine-bound)
    probe.py <fact> --from ref.json  interpret a SHIPPED snapshot   (portable)

so paperkit can ship setup/reference.json — "this is the data that ran on my
machine" — and a reader re-interprets it anywhere.  `--fresh ref.json` then
certifies PROVENANCE: it re-pumps and checks the snapshot's STRUCTURAL readings
still match this box (dynamic readings — pressure, swap fill — are a frozen
measurement and excluded from the match).

    probe.py --capture > reference.json    # regenerate the shipped dataset
    probe.py --fresh reference.json        # provenance: does it match this box?
    probe.py cores10 --from reference.json # interpret one fact from the snapshot
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

COMPRESSORS = {"zstd", "lzo", "lzo-rle", "lz4", "lz4hc", "842"}

# the interned readings that are STABLE across captures (hardware + configured
# topology); the rest (pressure, swap fill, compression fill) are a frozen
# measurement, so freshness/provenance compares only these.
STRUCTURAL = ("cpu", "swap_devices", "zram_algorithm", "zram_disksize",
              "root", "swappiness", "mem_total_kb", "zswap")


# ── pump: retrieve + intern ───────────────────────────────────────────────────
def pump() -> dict:
    """Read the live machine into one interned state object."""
    src: list[str] = []

    def rd(p: str) -> str:
        src.append(p)
        return Path(p).read_text()

    def has(p: str) -> bool:
        src.append(p)
        return Path(p).exists()

    # swap devices + fill
    swaps = []
    for row in rd("/proc/swaps").splitlines()[1:]:
        f = row.split()
        if len(f) >= 5:
            swaps.append({"name": f[0], "type": f[1], "used_kb": int(f[3]), "prio": int(f[4])})

    # root block device + rotational
    rootdev = ""
    for line in rd("/proc/mounts").splitlines():
        dev, mnt, *_ = line.split()
        if mnt == "/" and dev.startswith("/dev/"):
            rootdev = dev.removeprefix("/dev/")
            break
    base = rootdev.rsplit("p", 1)[0] if ("nvme" in rootdev and "p" in rootdev) else rootdev.rstrip("0123456789")
    rota = rd(f"/sys/block/{base}/queue/rotational").strip() if has(f"/sys/block/{base}/queue/rotational") else None

    # zram
    algo = ""
    for tok in rd("/sys/block/zram0/comp_algorithm").split():
        if tok.startswith("[") and tok.endswith("]"):
            algo = tok.strip("[]")
    mm = rd("/sys/block/zram0/mm_stat").split()

    # cpu topology
    logical = len(list(Path("/sys/devices/system/cpu").glob("cpu[0-9]*")))
    src.append("/sys/devices/system/cpu")
    nodes = len(list(Path("/sys/devices/system/node").glob("node[0-9]*")))
    src.append("/sys/devices/system/node")
    model = ""
    for line in rd("/proc/cpuinfo").splitlines():
        if line.startswith("model name"):
            model = line.split(":", 1)[1].strip()
            break

    def psi(resource: str) -> float:
        for line in rd(f"/proc/pressure/{resource}").splitlines():
            if line.startswith("some"):
                for t in line.split():
                    if t.startswith("avg300="):
                        return float(t.split("=", 1)[1])
        raise ValueError(resource)

    mem_total = int(next(l.split()[1] for l in rd("/proc/meminfo").splitlines() if l.startswith("MemTotal")))

    # zswap: the compressed write-back CACHE in front of the disk-swap path (lz4,
    # bounded to max_pool_percent of RAM) — the second compression layer above zram.
    zswap = {p: rd(f"/sys/module/zswap/parameters/{p}").strip()
             for p in ("enabled", "compressor", "max_pool_percent", "shrinker_enabled")}

    state = {
        "cpu": {"logical": logical, "numa_nodes": nodes, "model": model},
        "swap_devices": [{"name": s["name"], "type": s["type"], "prio": s["prio"]} for s in swaps],
        "swap_fill_kb": {s["name"]: s["used_kb"] for s in swaps},
        "root": {"device": rootdev, "rotational": rota},
        "zram_algorithm": algo,
        "zram_disksize": int(rd("/sys/block/zram0/disksize").strip()),
        "zram_orig_bytes": int(mm[0]), "zram_compr_bytes": int(mm[1]), "zram_same_pages": int(mm[5]),
        "zswap": zswap,
        "swappiness": int(rd("/proc/sys/vm/swappiness").strip()),
        "mem_total_kb": mem_total,
        "psi": {"io_avg300": psi("io"), "memory_avg300": psi("memory")},
        "_sources": sorted(set(src)),
    }
    return state


def _structural(state: dict) -> dict:
    return {k: state[k] for k in STRUCTURAL if k in state}


# ── interpret: pure functions of the interned state ───────────────────────────
def _zram(s: dict) -> dict | None:
    z = [d for d in s["swap_devices"] if "zram" in d["name"]]
    return z[0] if z else None


def cores10(s):       return s["cpu"]["logical"] == 10
def numa1(s):         return s["cpu"]["numa_nodes"] == 1
def hybrid(s):        return "12650H" in s["cpu"]["model"] or "12th Gen" in s["cpu"]["model"]
def zram_zstd(s):     return s["zram_algorithm"] == "zstd"
def compressor(s):    return s["zram_algorithm"] in COMPRESSORS
def zram_in_ram(s):   return _zram(s) is not None and s["zram_disksize"] > 0
def zram_size(s):     return s["zram_disksize"] / (s["mem_total_kb"] * 1024) >= 0.4
def zram_ratio(s):    return s["zram_compr_bytes"] > 0 and s["zram_orig_bytes"] / s["zram_compr_bytes"] >= 3.0
def swappiness(s):    return s["swappiness"] >= 60
def zswap_enabled(s): return s["zswap"]["enabled"] == "Y"
def zswap_lz4(s):     return s["zswap"]["compressor"] == "lz4"           # speed-favouring, for the cache path
def zswap_bounded(s): return 0 < int(s["zswap"]["max_pool_percent"]) <= 20  # the cache can't eat RAM unbounded
def zswap_shrinker(s): return s["zswap"]["shrinker_enabled"] == "Y"     # writes back to disk under pressure
def psi_io_low(s):    return s["psi"]["io_avg300"] < 5.0
def psi_mem_low(s):   return s["psi"]["memory_avg300"] < 10.0
def psi_readable(s):  return "io_avg300" in s["psi"]
def env_bound(s):     return bool(s["_sources"]) and all(p.startswith(("/proc/", "/sys/")) for p in s["_sources"])


def zram_primary(s):
    z = _zram(s)
    return z is not None and max(d["prio"] for d in s["swap_devices"]) == z["prio"]


def nvme_overflow(s):
    z = _zram(s)
    files = [d for d in s["swap_devices"] if d["type"] == "file"]
    return bool(files) and z is not None and all(f["prio"] < z["prio"] for f in files) \
        and s["root"]["rotational"] == "0"


def tiered(s):        return zram_primary(s) and nvme_overflow(s)


FACTS = {
    "cores10": cores10, "numa1": numa1, "hybrid": hybrid,
    "zram-primary": zram_primary, "zram-zstd": zram_zstd, "compressor": compressor,
    "zram-in-ram": zram_in_ram, "zram-size": zram_size, "zram-ratio": zram_ratio,
    "nvme-overflow": nvme_overflow, "tiered": tiered, "swappiness": swappiness,
    "zswap-enabled": zswap_enabled, "zswap-lz4": zswap_lz4,
    "zswap-bounded": zswap_bounded, "zswap-shrinker": zswap_shrinker,
    "psi-readable": psi_readable, "psi-io-low": psi_io_low, "psi-mem-low": psi_mem_low,
    "env-bound": env_bound,
}


# ── CLI ───────────────────────────────────────────────────────────────────────
def main(argv: list[str]) -> int:
    if argv[:1] == ["--capture"]:
        print(json.dumps(pump(), indent=2, sort_keys=True))
        return 0
    if argv[:1] == ["--fresh"]:
        ref = json.loads(Path(argv[1]).read_text())
        live = pump()
        ok = _structural(live) == _structural(ref)
        if not ok:
            print("probe: reference dataset does NOT match this machine (structural drift)", file=sys.stderr)
        return 0 if ok else 1

    fact = argv[0] if argv else None
    if fact not in FACTS:
        sys.exit(f"usage: probe.py <{' | '.join(FACTS)}> [--from ref.json] | --capture | --fresh ref.json")
    if "--from" in argv:
        state = json.loads(Path(argv[argv.index("--from") + 1]).read_text())
    else:
        state = pump()
    ok = bool(FACTS[fact](state))
    if not ok:
        print(f"probe: {fact} does NOT hold for the {'snapshot' if '--from' in argv else 'live machine'}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
