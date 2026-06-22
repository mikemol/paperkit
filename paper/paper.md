# Paperkit: A Paper Is a Projection of a Verified Claim-DAG

*A self-hosting document toolkit — this paper is projected and gated by the tool it describes.*

## 1. The Problem: Papers Assert, Nothing Checks

Paperkit treats a scholarly paper as the projection of a claim-DAG — each sentence is a claim carrying a machine-checkable verifier, and a claim whose verifier fails simply does not appear in the prose [@thesis].

## 2. The Model: A Paper as a Projected Claim-DAG

A claim is a single record — a statement, the rubric section it belongs to, its dependencies, and its verifier — which is exactly the shape of a bibliography entry [@claim-rec]; and from that, the prose is projected, not authored: within each section the claims are ordered by their dependency edges and joined with connective glue, the same input always giving the same document [@projection].

## 3. The Engine: Projection and Gate

The projector emits the whole document from the warrant set, so the committed prose is a build artifact rather than a source any hand should edit [@projector]; and from that, the gate rejects any prose that has drifted from its projection, so a hand-edit cannot survive a build [@drift]; so coverage is enforced from both sides — every required section must appear, and every claim tagged for a section must be cited within it [@coverage].

## 4. The Check-Resolver: One Pluggable Seam

A claim's verifier is named type:target, and the gate dispatches it through a small registry of check types, so supporting a new domain means adding verifiers rather than editing the engine [@resolver]; out of the box, two verifiers ship built in — file, that an artifact exists, and cmd, that a script exits zero — and cmd is the universal escape hatch every other check reduces to [@builtins].

## 5. Self-Hosting: This Paper Verifies Itself

This paper is itself a paperkit project — its claims are these warrants, its prose is their projection, and the gate that accepts it is the very subject it describes [@selfhost]; underneath, the verifiers behind this section run paperkit on paperkit — projecting a fixture, drifting it, and confirming the gate rejects the drift — so the document's correctness and the tool's are one green check [@bootstrap].

## 6. Related Work

Literate programming interleaves a program with the prose that explains it, so code and explanation are kept in one source and cannot drift apart [@knuth-lit]; in a parallel spirit, reproducible-research practice ships the code and data that regenerate every figure and number, so a published result can be re-run rather than trusted [@buckheit-donoho]; and on the engine side, build-systems theory frames a build as the demand-driven computation of verified targets from their dependencies — the same shape paperkit gives to a claim-DAG [@mokhov-build].

## 7. Conclusion

By making every claim a verifier and the document their projection, paperkit closes the gap between what a paper says and what has been checked: an unverified sentence cannot ship, because it does not project [@synthesis].

## References

