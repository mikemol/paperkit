#!/usr/bin/env python3
"""experiment.py — a memory-oversubscription run that is BOUNDED BY CONSTRUCTION.

It does not try to be "considerate" by being small.  It re-execs itself under
membudget (vendored from substrate: a `systemd-run --scope` with MemoryMax), so
the kernel caps its cgroup and isolates it from the rest of the box — then it
deliberately allocates ~2x that cap across worker processes.  The overflow spills
to swap (zram, then NVMe) WITHIN the scope; the desktop never feels it.

It measures its OWN cgroup: memory.current (held), memory.swap.current (spilled),
and memory.pressure (how long its tasks actually stalled).  The headline fact is
that memory.current never exceeds memory.max — graceful degradation that is
bounded by construction, not by restraint.  Two-phase like probe.py (run pumps
the loaded cgroup; FACTS interpret the interned result), LLM-free, regex-free.

  experiment.py --run     run bounded (re-exec under membudget if uncapped)
  experiment.py --ensure   run only if loadtest.json is absent
  experiment.py <fact>     --ensure, then interpret one under-load fact
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "loadtest.json"
GB = 1024 ** 3
CAP_MB = int(os.environ.get("PAPERKIT_LOAD_CAP_MB", "4096"))   # cgroup MemoryMax (RAM cap)
SWAP_MB = int(os.environ.get("PAPERKIT_LOAD_SWAP_MB", "10240"))  # cgroup MemorySwapMax (swap allowed)
OVERSUB = float(os.environ.get("PAPERKIT_LOAD_OVERSUB", "3.0"))  # allocate this x the cap (12 GB at 4 GB cap)
WORKERS = int(os.environ.get("PAPERKIT_LOAD_WORKERS", "16"))
RAMP_S = float(os.environ.get("PAPERKIT_LOAD_RAMP", "20"))     # let the load build + spill before sampling


# ── cgroup introspection (this process's own scope) ───────────────────────────
def _cg_base() -> Path:
    rel = Path("/proc/self/cgroup").read_text().strip().split(":")[-1]
    return Path("/sys/fs/cgroup") / rel.lstrip("/")


def _cg_int(base: Path, name: str) -> int:
    return int((base / name).read_text().strip())


def _psi_full_total(base: Path, resource: str) -> int:
    for line in (base / f"{resource}.pressure").read_text().splitlines():
        if line.startswith("full"):
            for t in line.split():
                if t.startswith("total="):
                    return int(t.split("=", 1)[1])
    return 0


def _capped() -> bool:
    try:
        return (_cg_base() / "memory.max").read_text().strip().isdigit()
    except Exception:
        return False


def _zram() -> dict:
    mm = Path("/sys/block/zram0/mm_stat").read_text().split()
    return {"zram_orig_bytes": int(mm[0]), "zram_compr_bytes": int(mm[1])}


# ── the load ──────────────────────────────────────────────────────────────────
def _worker(per: int, seed: int) -> None:
    buf = bytearray(per)                                   # anonymous → swap-eligible
    pat = (f"PAPERKIT-{seed}-".encode() * 256)             # per-worker, compressible
    block = (pat * (1024 * 1024 // len(pat) + 1))[:1024 * 1024]   # 1 MB stride (fast fill)
    for off in range(0, per, len(block)):
        n = min(len(block), per - off)
        buf[off:off + n] = block[:n]                       # write non-zero so it can't dedup to nothing
    time.sleep(300)                                        # hold; the parent SIGKILLs after sampling


def _loaded() -> dict:
    base = _cg_base()
    cap = _cg_int(base, "memory.max")
    alloc = int(cap * OVERSUB)
    per = alloc // WORKERS
    ctx = mp.get_context("fork")
    t0 = time.time()
    b_mem, b_io = _psi_full_total(base, "memory"), _psi_full_total(base, "io")
    procs = [ctx.Process(target=_worker, args=(per, i)) for i in range(WORKERS)]
    for p in procs:
        p.start()
    time.sleep(RAMP_S)                                     # fixed: let the load build + spill to swap
    peak = {
        "mem_current_bytes": _cg_int(base, "memory.current"),
        "swap_current_bytes": _cg_int(base, "memory.swap.current"),
        **_zram(),
    }
    p_mem, p_io = _psi_full_total(base, "memory"), _psi_full_total(base, "io")
    for p in procs:                                        # SIGKILL — no graceful-join stall
        p.kill()
    for p in procs:
        p.join(timeout=5)
    elapsed_us = (time.time() - t0) * 1e6
    data = {
        "cap_bytes": cap,
        "allocated_bytes": per * WORKERS,
        "workers": WORKERS,
        "elapsed_s": round(time.time() - t0, 2),
        "peak": peak,
        # memory.current is capped at memory.max by the kernel; the overflow is swap
        "mem_full_stall_fraction": round((p_mem - b_mem) / elapsed_us, 5),
        "io_full_stall_fraction": round((p_io - b_io) / elapsed_us, 5),
        "_sources": ["cgroup memory.max/current/swap.current/{memory,io}.pressure",
                     "/sys/block/zram0/mm_stat"],
    }
    OUT.write_text(json.dumps(data, indent=2, sort_keys=True))
    return data


def run() -> dict:
    if _capped():
        return _loaded()
    # Re-exec inside a memory-capped cgroup scope: bounded by construction, isolated
    # from the rest of the box.  Unlike membudget (MemorySwapMax=0, a stay-in-RAM hard
    # cap), this ALLOWS swap — the whole point is to watch the overflow degrade
    # gracefully through the swap tiers rather than be OOM-refused.
    r = subprocess.run(["systemd-run", "--user", "--scope", "-q", "--slice=paperkit-load",
                        "-p", f"MemoryMax={CAP_MB}M", "-p", f"MemorySwapMax={SWAP_MB}M",
                        sys.executable, str(Path(__file__).resolve()), "--run"])
    if r.returncode != 0 or not OUT.exists():
        sys.exit(f"experiment: bounded run failed (rc={r.returncode}) — is `systemd-run --user` available?")
    return json.loads(OUT.read_text())


# ── interpret: pure functions of the interned load result ─────────────────────
def load_oversubscribed(s): return s["allocated_bytes"] > s["cap_bytes"]                       # asked for > the cap
def load_bounded(s):        return s["peak"]["mem_current_bytes"] <= int(s["cap_bytes"] * 1.05)  # held AT the cap
def load_swap_spilled(s):   return s["peak"]["swap_current_bytes"] > 64 * 1024 * 1024            # overflow swapped, not OOM
def load_io_quiet(s):       return s["io_full_stall_fraction"] < 0.01                            # the DISK never blocked
def load_not_io_bound(s):   return s["io_full_stall_fraction"] < 0.1 * s["mem_full_stall_fraction"]  # cost is CPU/mem, not disk
def load_compressed(s):     return s["peak"]["zram_compr_bytes"] > 0 and \
    s["peak"]["zram_orig_bytes"] / s["peak"]["zram_compr_bytes"] >= 1.5


FACTS = {
    "load-oversubscribed": load_oversubscribed, "load-bounded": load_bounded,
    "load-swap-spilled": load_swap_spilled, "load-io-quiet": load_io_quiet,
    "load-not-io-bound": load_not_io_bound, "load-compressed": load_compressed,
}


def _ensure() -> None:
    # produce loadtest.json once, even if many `load:` checks race: the first to
    # take the lock runs the (bounded) experiment, the rest wait and reuse it.
    if OUT.exists():
        return
    import fcntl
    with open(HERE / ".loadtest.lock", "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        if not OUT.exists():
            run()


def main(argv: list[str]) -> int:
    if argv[:1] == ["--run"]:
        print(json.dumps(run(), indent=2, sort_keys=True))
        return 0
    if argv[:1] == ["--ensure"]:
        _ensure()
        return 0
    fact = argv[0] if argv else None
    if fact not in FACTS:
        sys.exit(f"usage: experiment.py <{' | '.join(FACTS)}> | --run | --ensure")
    _ensure()
    ok = bool(FACTS[fact](json.loads(OUT.read_text())))
    if not ok:
        print(f"experiment: {fact} does NOT hold for the load snapshot", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
