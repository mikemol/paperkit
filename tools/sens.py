#!/usr/bin/env python3
"""Ζ·mutant·sens — aggregate per-(claim, site) pk_eval `{flipped}` records into the claim's
SENSITIVITY set: the sites whose mutation flips the check.  The Bazel-graph counterpart of
grader.sensitivity's in-process group-testing — there one action group-tests the sites; here the
fanout IS the build graph (one pk_eval per site, parallel + cached) and this just READS the results.

VALIDITY WITNESS (--baseline): the ∅-mutation eval (mutate.py with the empty qualname = the identity
point of the mutation set) runs the UNMUTATED check in the very same sandbox.  It MUST be
flipped=false: if it flipped, the failure is in the HARNESS (the environment, the delivery), not in
any mutation — and every site would then read as sensitive (the degenerate all-flip that hid a
non-idempotent eval).  So a flipped baseline makes this action FAIL LOUD rather than emit a
plausible-but-wrong sens set.  The baseline is excluded from `sens` (∅ is not a site)."""
import argparse
import json
import sys


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", required=True, help="the ∅-mutation eval record — MUST be flipped=false")
    ap.add_argument("evals", nargs="*", help="the per-site pk_eval records")
    a = ap.parse_args(argv)

    base = json.load(open(a.baseline))
    if base.get("flipped"):
        sys.stderr.write(
            "Ζ·sens: the ∅ BASELINE check flipped — the harness is broken (environment/delivery), "
            "not the engine; every site would read as sensitive. Refusing to emit a sens set.\n")
        return 1

    sens = [r["site"] for r in (json.load(open(f)) for f in a.evals) if r["flipped"]]
    print(json.dumps({"claim": base["claim"], "sens": sorted(sens)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
