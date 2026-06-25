# The paper's proof object, held in an IMMUTABLE, REPRODUCIBLE image (Κ·image).
#
# paperkit turns a paper into a proof object — a claim-DAG the gate verifies.  This image
# expands the proof object to hold its OWN toolchain (the pinned base, Containerfile.base)
# and the whole repository, with the gate as its entrypoint.  Because the toolchain lives
# in the pinned base, THIS build is COPY-only; with --timestamp it is byte-reproducible —
# the same source yields the same image digest, a stable content-address (the proof's
# checksum).  `podman run` then re-verifies the paper HERMETICALLY: the same green verdict
# on any machine, with no host dependency.
#
#   podman build --timestamp 0 -t paperkit-base:proof  -f Containerfile.base .   # once
#   podman build --timestamp 0 -t paperkit-proof:paper -f Containerfile .
#   podman run --rm --network=none paperkit-proof:paper                          # exit 0 == proof
FROM localhost/paperkit-base:proof

# No systemd in the container, so the membudget lease degrades to a plain subprocess;
# podman bounds resources from outside (--memory) — one mechanism, not two.
ENV PAPERKIT_NO_MEMBUDGET=1

# The whole repository — engine + every project + the githook — laid out as on the host, so
# the paper's checks resolve their siblings (../paperkit, ../boundaries, .githooks) exactly.
COPY . /work
WORKDIR /work

# Two modes from one image (image/entrypoint.sh, COPY-only so the build stays reproducible):
#   podman run <img>            → gate  (PROVE: verify the paper hermetically, exit 0)
#   podman run -p 8000:8000 <img> serve → PRESENT: serve the repository over HTTP
ENTRYPOINT ["sh", "/work/image/entrypoint.sh"]
CMD ["gate"]
