# Paperkit — The Proof Object as an Immutable Image

*Built and verified fresh-by-construction: the image is rebuilt from this repository and its gate run network-isolated, so a green verdict here is the proof reproducing itself.*

## The Proof Object, Reproduced

Paperkit's proof object reproduces as an immutable container image — building the image from this repository and running its gate inside it, network-isolated, verifies the paper HERMETICALLY: the same green verdict with no host toolchain, fresh-by-construction each build [@img-repro]. And the build is REPRODUCIBLE: from the pinned toolchain base the proof image is COPY-only, so building it twice — forced, with a fixed timestamp — yields the same content digest, making the digest a stable content-address, the proof's checksum [@img-stable].

## Pinned and Hermetic

The toolchain base is pinned by content digest, not a moving tag, so the proof reproduces and is not at the mercy of a re-tagged base — the irreducibly non-deterministic package layer is isolated there, the way the python base isolates its own [@img-pinned], and the verification runs with the network disabled, so a check cannot reach beyond the image and the proof depends on nothing outside it [@img-hermetic].

## The Paper Hosts Itself (HTTP)

The same immutable image that PROVES the paper also PRESENTS it: run in serve mode it hosts the repository over HTTP, and the paper fetched from it is byte-for-byte the paper that was gated — the proof object serves itself, no host webserver [@img-serve].

