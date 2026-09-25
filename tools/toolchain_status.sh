#!/bin/sh
# Ζ·tier·toolchain — the toolchain fingerprint, emitted as a Bazel STABLE workspace-status key.
#
# A `toolchain`-tier check (verb.bzl) runs in the executor pool whose IMAGE carries its tools
# (tools/pool.bzl, image/executor/Containerfile) — deterministic GIVEN THAT IMAGE.  Its verdict
# should re-run exactly when the image CHANGES and be cached otherwise, and Bazel's stamping gives
# precisely that: a STABLE_ key whose value changes invalidates every stamped action depending on
# it (`bazel-out/stable-status.txt`), an unchanged value is a cache hit — measured, not assumed
# (the Ζ·tier·toolchain probe).  So the ONE key is the image digest.
#
# ⚑ WHAT THIS REPLACED, 2026-09-21.  Until today this script emitted the CLIENT HOST's pandoc /
# veraPDF / lualatex / soffice version banners plus a sha256 of a jar under $HOME.  Those keyed a
# verdict on the box the `bazel` command was typed on, while the verdict itself ran in the pool:
# an image rebuild left every toolchain verdict cached (measured: rnd-pdf/rnd-a11y did not
# invalidate on the python3-uno re-declare by any key of ours), and a host without the tools
# stamped `absent` over verdicts that had run somewhere else entirely.  The digest is what the
# pool's pod template rolls on, so "the image my verdict ran in" and "the image the pool runs now"
# compare on the same value.
#
# `absent` is a STABLE value, never a failing status command (which would abort every build,
# sandbox cells included): on a host without the pool the toolchain checks cannot run at all
# under --noremote_local_fallback, so nothing is ever cached under it.
#
#   bazel build --stamp --workspace_status_command=tools/toolchain_status.sh …
# (wired in .bazelrc).
# ⚑ TWO KEYS, ONE PER POOL (tools/pool.bzl).  STABLE_EXECUTOR_IMAGE is the DEFAULT pool's thin
# image — the sweep's substrate, which every sandbox cell depends on (calc.bzl stages
# ctx.info_file).  Measured 2026-09-21: strace was added to it and the refuted footprint
# baselines came back as 113 cache hits, because nothing in a cell's key named the image.
set -u
echo "STABLE_TOOLCHAIN_IMAGE $(python3 tools/image_digest.py paperkit-executor)"
echo "STABLE_EXECUTOR_IMAGE $(python3 tools/image_digest.py buildbuddy-executor)"
