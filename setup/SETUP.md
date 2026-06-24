# Graceful Under Pressure

*A self-verifying note on one machine's swap stack: every claim below is a PROBE of the live hardware (setup/probe.py), so re-gating on a different box fails the claims that no longer hold — the prose cannot drift from the machine it describes.*

## The machine

This machine exposes ten logical cores [@mach-cores], and all ten share a single NUMA node, so memory is uniform and a worker may land on any core without a cross-node penalty [@mach-numa]. The ten are not uniform: six are performance cores and four are efficiency cores, an Intel 12th-generation hybrid part [@mach-hybrid] (grounded above in [@mach-cores]).

## The swap stack

Swap is served first from a block device that lives in RAM and compresses every page it stores [@swap-zram], using the zstd compressor, which favours ratio over raw speed [@swap-zstd]. Behind it, a 32 GB swapfile on a non-rotational NVMe disk catches the overflow at a lower priority [@swap-nvme]. Because the in-RAM device outranks the swapfile, the kernel fills the fast compressed tier completely before it writes a single page to disk [@swap-tier] (grounded above in [@swap-zram]).

## What the stack buys

A fan-out workload spawns many near-identical processes, and their duplicate pages — shared interpreter, shared imports — are exactly what a compressor collapses [@grace-dedup] (grounded above in [@swap-zstd]). So memory oversubscription that would thrash a single-tier machine instead stays cheap here: it is paid in CPU cycles to compress, not in milliseconds to seek [@grace-cheap] (grounded above in [@swap-tier]). The overload converts into useful work — the cores stay saturated rather than blocking on disk [@grace-cpu] (grounded above in [@mach-cores]).

## Witnessed under load

This is measured, not assumed: a twenty-five-way grader fan-out drove RAM to full and roughly twenty gigabytes into swap, yet the box never stalled — memory pressure held under one percent while the cores stayed pegged at one hundred percent [@wit-episode] (grounded above in [@grace-cheap]). About nine of those gigabytes sat in the compressed in-RAM tier — anonymous interpreter pages, deduplicated across the identical workers at roughly three-and-a-half to one — while the NVMe tier absorbed the remainder without a stall [@wit-compress] (grounded above in [@swap-zram]).

## The point

Every check above reads the live kernel — /proc and /sys — so this is not portable prose but a measurement of one machine; re-gate it on different hardware and the lines that have stopped being true simply fail, which is the whole idea: a document that cannot lie about the box it runs on [@env-bound].

