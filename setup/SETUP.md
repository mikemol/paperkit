# Graceful Under Pressure

*A self-verifying note on one machine's swap stack. The claims read a SHIPPED reference dataset (setup/reference.json), interned from /proc and /sys by setup/probe.py's pump() and interpreted by pure functions of that state — so anyone can re-verify them anywhere (machine-readable, no regex, no model in the loop). A separate freshness check certifies provenance: the dataset's structural readings still match THIS box. Body travels; provenance stays home.*

## The machine

This machine exposes ten logical cores [@mach-cores], and all ten share a single NUMA node, so memory is uniform and a worker may land on any core without a cross-node penalty [@mach-numa]. The ten are not uniform: six are performance cores and four are efficiency cores, an Intel 12th-generation hybrid part [@mach-hybrid] (grounded above in [@mach-cores]).

## The swap stack

Swap is served first from a block device that lives in RAM and compresses every page it stores [@swap-zram], using the zstd compressor, which favours ratio over raw speed [@swap-zstd]. That device is RAM-backed, not a disk partition [@swap-inram] (grounded above in [@swap-zram]), and it is sized to roughly sixty percent of total memory, generous headroom for the compressed tier [@swap-size]. Behind it, a swapfile on a non-rotational NVMe disk catches the overflow at a lower priority [@swap-nvme]. Because the in-RAM device outranks the swapfile, the kernel fills the fast compressed tier completely before it writes a single page to disk [@swap-tier] (grounded above in [@swap-zram]). And the kernel is tuned to reach for that tier early — swappiness sits well above its timid default [@swap-swappy].

## What the stack buys

A fan-out workload spawns many near-identical processes, and their duplicate pages — shared interpreter, shared imports — are exactly what a compressor collapses [@grace-dedup] (grounded above in [@swap-zstd]). So memory oversubscription that would thrash a single-tier machine instead stays cheap here: it is paid in CPU cycles to compress, not in milliseconds to seek [@grace-cheap] (grounded above in [@swap-tier]). The overload converts into useful work — the cores stay saturated rather than blocking on disk [@grace-cpu] (grounded above in [@mach-cores]).

## Witnessed under load

This is measured, not assumed: a twenty-five-way grader fan-out drove RAM to full and roughly twenty gigabytes into swap, yet the box never stalled — the dataset's own pressure reading puts memory contention near one percent, far below the threshold where work would block [@wit-episode] (grounded above in [@grace-cheap]). The recorded snapshot shows the compressed tier holding three and a half times its own footprint — anonymous interpreter pages deduplicated across the identical workers — while the NVMe tier absorbed the remainder without a stall [@wit-compress] (grounded above in [@swap-zstd]).

## The data, and where it came from

None of these numbers were retyped from memory: probe.py's pump() interned them from the live kernel, and the dataset records its own sources — every one a path under /proc or /sys [@prov-source]. And the shipped dataset is certified against this very box: a fresh capture's structural readings still match it, so the snapshot genuinely ran here — re-gate on other hardware and the body still verifies from the data while this provenance check, alone, fails. The claims travel; the proof that they are mine stays home [@prov-fresh].

