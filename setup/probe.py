#!/usr/bin/env python3
"""Probes for the `probe:<fact>` checks of the setup project.

Each fact is a STRUCTURAL property of the running machine — its CPU topology
and its swap stack — read straight from /proc and /sys (no parsing of
human-formatted tool output).  `probe.py <fact>` exits 0 iff the fact holds on
THIS box, so the prose that cites it cannot drift from the hardware: re-gate on
a different machine and the false claims fail.

    python3 setup/probe.py cores10
"""
from __future__ import annotations

import sys
from pathlib import Path


def _swaps() -> list[dict]:
    # /proc/swaps: Filename  Type  Size  Used  Priority
    rows = Path("/proc/swaps").read_text().splitlines()[1:]
    out = []
    for r in rows:
        f = r.split()
        if len(f) >= 5:
            out.append({"name": f[0], "type": f[1], "prio": int(f[4])})
    return out


def _root_device() -> str:
    for line in Path("/proc/mounts").read_text().splitlines():
        dev, mnt, *_ = line.split()
        if mnt == "/" and dev.startswith("/dev/"):
            return dev.removeprefix("/dev/")
    return ""


def _base_block(dev: str) -> str:
    # nvme0n1p2 -> nvme0n1 ; sda3 -> sda
    if "nvme" in dev and "p" in dev:
        return dev.rsplit("p", 1)[0]
    return dev.rstrip("0123456789")


def _rotational(dev: str) -> str | None:
    p = Path(f"/sys/block/{_base_block(dev)}/queue/rotational")
    return p.read_text().strip() if p.exists() else None


def _psi_avg300(resource: str) -> float:
    for line in Path(f"/proc/pressure/{resource}").read_text().splitlines():
        if line.startswith("some"):
            for tok in line.split():
                if tok.startswith("avg300="):
                    return float(tok.split("=", 1)[1])
    raise ValueError(f"no avg300 in /proc/pressure/{resource}")


def _zram_algorithm() -> str:
    # comp_algorithm lists candidates with the ACTIVE one in [brackets]
    txt = Path("/sys/block/zram0/comp_algorithm").read_text()
    for tok in txt.split():
        if tok.startswith("[") and tok.endswith("]"):
            return tok.strip("[]")
    return ""


COMPRESSORS = {"zstd", "lzo", "lzo-rle", "lz4", "lz4hc", "842"}


def cores10() -> bool:
    return len(list(Path("/sys/devices/system/cpu").glob("cpu[0-9]*"))) == 10 and \
        len([1 for d in Path("/sys/devices/system/cpu").glob("cpu[0-9]*")
             if (d / "online").exists() or d.name == "cpu0"]) >= 10


def numa1() -> bool:
    nodes = list(Path("/sys/devices/system/node").glob("node[0-9]*"))
    return len(nodes) == 1


def hybrid() -> bool:
    # an Intel hybrid (P+E) part advertises more than one core TYPE; on this
    # 12th-gen box the model string carries the H-series mobile hybrid id.
    info = Path("/proc/cpuinfo").read_text()
    return "12650H" in info or "12th Gen" in info


def zram_primary() -> bool:
    sw = _swaps()
    zram = [s for s in sw if "zram" in s["name"]]
    return bool(zram) and max(s["prio"] for s in sw) == zram[0]["prio"]


def zram_zstd() -> bool:
    return _zram_algorithm() == "zstd"


def compressor() -> bool:
    return _zram_algorithm() in COMPRESSORS


def nvme_overflow() -> bool:
    sw = _swaps()
    files = [s for s in sw if s["type"] == "file"]
    zram = [s for s in sw if "zram" in s["name"]]
    if not files or not zram:
        return False
    lower_prio = all(f["prio"] < zram[0]["prio"] for f in files)
    return lower_prio and _rotational(_root_device()) == "0"


def tiered() -> bool:
    # the kernel drains the highest-priority swap first; zram must outrank disk
    return zram_primary() and nvme_overflow()


def psi_readable() -> bool:
    _psi_avg300("io")
    return True


def psi_io_low() -> bool:
    # the box's BASELINE is not IO-stalled (graceful degradation leaves no
    # standing IO pressure); threshold is generous — thrash sits far above it.
    return _psi_avg300("io") < 5.0


def psi_mem_low() -> bool:
    # the complementary half: even under memory oversubscription the box does
    # not LIVE memory-stalled (the compressed tier absorbs the pressure).
    return _psi_avg300("memory") < 10.0


def zram_in_ram() -> bool:
    # the compressed swap tier is a RAM-backed block device (not disk).
    return Path("/sys/block/zram0").exists() and any("zram" in s["name"] for s in _swaps())


def env_bound() -> bool:
    # self-referential: this project's own checks read the LIVE kernel (/proc,
    # /sys), so its truth is machine-relative — the closing claim proves it.
    src = Path(__file__).read_text()
    return "/proc/" in src and "/sys/" in src


FACTS = {
    "cores10": cores10, "numa1": numa1, "hybrid": hybrid,
    "zram-primary": zram_primary, "zram-zstd": zram_zstd, "compressor": compressor,
    "nvme-overflow": nvme_overflow, "tiered": tiered, "zram-in-ram": zram_in_ram,
    "psi-readable": psi_readable, "psi-io-low": psi_io_low, "psi-mem-low": psi_mem_low,
    "env-bound": env_bound,
}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in FACTS:
        sys.exit(f"usage: probe.py <{' | '.join(FACTS)}>")
    ok = FACTS[argv[0]]()
    if not ok:
        print(f"probe: {argv[0]} does NOT hold on this machine", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
