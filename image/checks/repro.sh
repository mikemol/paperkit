#!/bin/sh
# Κ·image·claim — build the proof image (from the pinned toolchain base) and run its gate
# HERMETICALLY.  Exit 0 iff the paper's proof object verifies itself inside an immutable,
# network-isolated container.  Fresh-by-construction.  (cwd = the image/ project; .. = repo root.)
set -eu
cd ..
podman build -q --timestamp 0 -t paperkit-base:proof -f Containerfile.base . >/dev/null
tag="paperkit-proof-verify:$$"
trap 'podman rmi -f "$tag" >/dev/null 2>&1 || true' EXIT
podman build -q --timestamp 0 -t "$tag" -f Containerfile . >/dev/null
podman run --rm --network=none "$tag" >/dev/null
