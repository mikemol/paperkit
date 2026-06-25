# Paperkit — The Proof Object as an Immutable Image

*Built and verified fresh-by-construction: the image is rebuilt from this repository and its gate run network-isolated, so a green verdict here is the proof reproducing itself.*

## The Proof Object, Reproduced

Paperkit's proof object reproduces as an immutable container image — building the pinned image from this repository and running its gate inside it, network-isolated, verifies the paper HERMETICALLY: the same green verdict with no host toolchain, fresh-by-construction each build [@img-repro].

## Pinned and Hermetic

The image's toolchain is pinned by content digest, not a moving tag, so the proof object reproduces and is not at the mercy of a re-tagged base [@img-pinned], and the verification runs with the network disabled, so a check cannot reach beyond the image and the proof depends on nothing outside it [@img-hermetic].

