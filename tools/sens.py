#!/usr/bin/env python3
"""Ζ·mutant·sens — aggregate per-(claim, site) pk_eval `{flipped}` records into the claim's
SENSITIVITY set: the sites whose mutation flips the check.  This is the Bazel-graph counterpart of
grader.sensitivity's in-process group-testing — there one action group-tests the sites; here the
fanout IS the build graph (one pk_eval action per site, parallel + cached) and this just READS the
results.  Each arg is a pk_eval `.eval.json` ({claim, site, flipped}); stdout is {claim, sens:[…]}."""
import json
import sys

claim = None
sens = []
for f in sys.argv[1:]:
    r = json.load(open(f))
    claim = r["claim"]
    if r["flipped"]:
        sens.append(r["site"])
print(json.dumps({"claim": claim, "sens": sorted(sens)}))
