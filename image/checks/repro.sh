#!/bin/sh
# Κ·image·claim — build the proof image from the current repo and run its gate HERMETICALLY.
# Exit 0 iff the paper's proof object verifies itself inside an immutable, network-isolated
# container.  Fresh-by-construction: the image is rebuilt from source each run, so any drift
# in an input the proof reads makes this fail.  (cwd = the image/ project; .. = repo root.)
set -eu
cd ..
tag="paperkit-proof-verify:$$"
trap 'podman rmi -f "$tag" >/dev/null 2>&1 || true' EXIT
podman build -q -t "$tag" -f Containerfile . >/dev/null
podman run --rm --network=none "$tag" >/dev/null
