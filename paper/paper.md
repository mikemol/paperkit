# Paperkit: A Paper Is a Projection of a Verified Claim-DAG

*A self-hosting document toolkit — this paper is projected and gated by the tool it describes.*

## 1. The Problem: Papers Assert, Nothing Checks

Paperkit treats a scholarly paper as the projection of a claim-DAG [@paper-is-projection] — each node a single claim [@node-is-claim], each claim carrying a machine-checkable verifier [@claim-bears-check]; and a claim whose verifier fails simply does not appear in the prose [@fail-omits].

## 2. The Model: A Paper as a Projected Claim-DAG

A claim is a single record — a statement, the rubric section it belongs to, its dependencies, and its verifier [@claim-is-record] — which is exactly the shape of a bibliography entry [@record-is-bibentry]. The prose is projected, not authored [@prose-projected]: within each section the claims are ordered by their dependency edges [@ordered-by-deps] and joined by connective glue [@joined-by-glue], the same warrant set always giving the same document [@deterministic].

## 3. The Engine: Projection and Gate

The projector emits the whole document from the warrant set [@projector-emits], so the committed prose is a build artifact, not a source any hand should edit [@prose-is-artifact]. The gate rejects any prose that has drifted from its projection [@gate-rejects-drift], so a hand-edit cannot survive a build [@edit-cant-survive]. Coverage is enforced from both sides [@coverage-both-sides] — every required section must appear [@every-section-appears], and every claim tagged for a section must be cited within it [@every-claim-cited].

## 4. The Check-Resolver: One Pluggable Seam

A claim's verifier is named type:target [@verifier-named], and the gate dispatches it through a small registry of check types [@gate-dispatches], so supporting a new domain means adding verifiers, not editing the engine [@new-domain-adds]. Two verifiers ship built in [@two-builtins] — file, that an artifact exists [@file-builtin], and cmd, that a script exits zero [@cmd-builtin]; and cmd is the universal escape hatch every other check reduces to [@cmd-escape].

## 5. Self-Hosting: This Paper Verifies Itself

This paper is itself a paperkit project [@paper-is-paperkit] — its claims are these warrants [@claims-are-warrants], its prose is their projection [@prose-is-projection], and the gate that accepts it is the very subject it describes [@gate-is-subject]. The verifiers behind this section run paperkit on paperkit — projecting a fixture, drifting it, and confirming the gate rejects the drift [@paperkit-on-paperkit], so the document's correctness and the tool's are one green check [@one-green-check].

## 6. Related Work

Literate programming interleaves a program with the prose that explains it, so code and explanation are kept in one source and cannot drift apart [@knuth-lit]; in a parallel spirit, reproducible-research practice ships the code and data that regenerate every figure and number, so a published result can be re-run rather than trusted [@buckheit-donoho]; and on the engine side, build-systems theory frames a build as the demand-driven computation of verified targets from their dependencies — the same shape paperkit gives to a claim-DAG [@mokhov-build].

## 7. Conclusion

By making every claim a verifier and the document their projection, paperkit closes the gap between what a paper says and what has been checked [@closes-gap]: an unverified sentence cannot ship [@unverified-cant-ship], because it does not project [@not-project].

## References

