#!/bin/sh
# Κ·image·repro — the build is REPRODUCIBLE: from the pinned toolchain base, building the
# proof image twice (forced, fixed timestamp) yields the SAME content digest.  The digest is
# a stable content-address — the proof's checksum.  (cwd = the image/ project; .. = repo root.)
set -eu
cd ..
podman build -q --timestamp 0 -t paperkit-base:proof -f Containerfile.base . >/dev/null
trap 'podman rmi -f paperkit-proof-repro1 paperkit-proof-repro2 >/dev/null 2>&1 || true' EXIT
podman build -q --no-cache --timestamp 0 -t paperkit-proof-repro1 -f Containerfile . >/dev/null
podman build -q --no-cache --timestamp 0 -t paperkit-proof-repro2 -f Containerfile . >/dev/null
d1=$(podman image inspect paperkit-proof-repro1 --format '{{.Id}}')
d2=$(podman image inspect paperkit-proof-repro2 --format '{{.Id}}')
[ "$d1" = "$d2" ]   # exit 0 iff the two independent builds produced the same digest
