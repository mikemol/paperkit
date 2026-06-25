# The paper's proof object, held in an IMMUTABLE image (Κ·image).
#
# paperkit turns a paper into a proof object — a claim-DAG the gate verifies.  But that
# verification still leans on the host's toolchain (python, grep, strace — the Τ·path
# residual).  This image expands the proof object to hold its OWN toolchain: a digest-pinned
# base + strace + the whole repository (the engine and every project), with the gate as its
# entrypoint.  The paper's claims are about the SYSTEM (the project DAG, the local CI hook,
# the boundaries project, the live report), so the proof object is the whole repo, not the
# paper alone.
#
# Built green, the image is content-addressed and immutable, so `podman run` re-verifies the
# paper HERMETICALLY — the same green verdict on any machine, durably, with no host
# dependency.  The image digest is the proof's checksum.
#
#   podman build -t paperkit-proof:paper -f Containerfile .
#   podman run --rm --network=none paperkit-proof:paper   # exit 0 == proof verified
FROM docker.io/library/python@sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0

# strace backs Φ·footprint (the read-footprint tracer the grader's witnesses exercise); it
# is part of the pinned toolchain the proof object carries, not the host's to provide.
RUN apk add --no-cache strace

# No systemd in the container, so the membudget lease degrades to a plain subprocess;
# podman bounds resources from outside (--memory) — one mechanism, not two.
ENV PAPERKIT_NO_MEMBUDGET=1

# The whole repository — engine + every project + the githook — laid out as on the host, so
# the paper's checks resolve their siblings (../paperkit, ../boundaries, .githooks) exactly.
COPY . /work
WORKDIR /work

# The entrypoint IS the proof: gate the paper, hermetically, under --safe --without-K.
CMD ["python3", "paperkit/gate.py", "--safe", "--without-K", "paper"]
