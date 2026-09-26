#!/usr/bin/env python3
# Ρ·report·mitigation — the non-reproducibility that determinism.py characterizes is BOUNDED and
# DISCLOSED, and both mitigations are proven in place here (deterministically, without running the
# flaky builds):
#
#   1. CONTENT-reproducibility.  image's img-stable builds the proof image twice, each `--no-cache`,
#      and asserts the two independent builds yield the SAME content digest — so the non-determinism
#      is confined to build COST/availability, not to WHAT is verified (the artifact is byte-
#      reproducible even when building it is slow/network-dependent).  Proven on-demand by image's
#      gate; here we prove the mechanism is present and intact.
#   2. Deterministic DISCLOSURE.  the report reads each document's gate VERDICT from its gate_rec
#      (Ζ·report·records — it runs no gate itself), and a verdict of `cannot-run` (a check whose
#      toolchain is absent, typed rc 3) is rendered `n/a`, never a false verification FAIL.  We
#      drive that path deterministically with synthetic staged records.  cwd = report/.
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _content_mitigation():
    stable = (ROOT / "image" / "checks" / "stable.sh").read_text()
    assert "--no-cache" in stable, "img-stable no longer forces cache-independent builds"
    assert stable.count("podman build") >= 2, "img-stable no longer builds twice independently"
    assert '"$d1" = "$d2"' in stable, "img-stable no longer asserts the two builds' digests are equal"
    warrants = (ROOT / "image" / "warrants.bib").read_text()
    assert "img-stable" in warrants and "digest" in warrants.lower(), \
        "image no longer claims build digest-reproducibility (the content mitigation)"


def _disclosure_mitigation():
    # ⚑ Ζ·report·records — the report no longer RUNS gates, so there is no timeout to bound: each
    # verdict is the project's gate_rec (what //:hook asserts), and a check that CANNOT RUN reaches
    # it as `cannot-run` — distinct from `fail` by verb.bzl's typed exit (rc 3).  This witness used
    # to grep gen.py for `timeout=`/`TimeoutExpired` and spawn gate.py on the host; it now drives the
    # REAL path with synthetic staged records, both ways: cannot-run must render n/a, and fail must
    # still render FAIL (so the arm can go red).
    import json
    import os
    import tempfile
    sys.path.insert(0, str(ROOT / "report"))
    import gen
    with tempfile.TemporaryDirectory() as d:
        struct = Path(d) / "rec_struct.json"
        struct.write_text(json.dumps({"pass": True, "project_ok": True, "verified": 1,
                                      "sections": 1, "collapses": {}}))
        rows = {}
        for verdict in ("cannot-run", "fail", "pass"):
            rec = Path(d) / f"{verdict}.verdict.json"
            rec.write_text(json.dumps({"verdict": verdict}))
            os.environ["PAPERKIT_CONSUMED_RECORDS"] = (f"paperkit_paper/rec_struct.json={struct} "
                                                       f"paperkit_paper/gate_rec={rec}")
            gen._GATE.clear()
            g = gen._gate("paper", "--safe")
            rows[verdict] = (f"n/a — {g['error']}" if "error" in g
                             else ("PASS" if g.get("pass") else "FAIL"))
        os.environ.pop("PAPERKIT_CONSUMED_RECORDS", None)
    assert rows["cannot-run"].startswith("n/a"), \
        f"a document that cannot run here renders {rows['cannot-run']!r}, not n/a — a false FAIL"
    assert rows["fail"] == "FAIL", f"a failing gate renders {rows['fail']!r} — the arm cannot go red"
    assert rows["pass"] == "PASS", f"a passing gate renders {rows['pass']!r}"
    src = (ROOT / "report" / "gen.py").read_text()
    assert '"on-demand"' in src, "the report no longer renders a non-reproducible document as on-demand"


def _fixpoint_mitigation():
    # the cache-warmth variance is stabilized by retrying to a warm fixpoint — proven deterministically
    # by driving the runner's fixpoint over synthetic verdict sequences (no flaky build needed):
    sys.path.insert(0, str(ROOT / "report"))
    import gen
    # cold→warm→warm: a verdict that changes once (cold build too slow) then holds (cache hit) must
    # converge to the WARM result, marked stable:
    warm_seq = iter([{"error": "timed out (>300s)"}, {"pass": True, "verified": 5}, {"pass": True, "verified": 5}])
    warm = gen._gate_stable("image", "--safe", runner=lambda: next(warm_seq))
    assert warm.get("pass") and warm.get("_stable"), \
        f"retry did not converge to the warm verdict (cache-warmth not mitigated): {warm}"
    # a verdict that never settles is NOT cache-warmth (a clock/threshold cause) — it must be FLAGGED,
    # not laundered as reproducible:
    osc_seq = iter([{"pass": True}, {"pass": False}, {"pass": True}])
    flaky = gen._gate_stable("x", runner=lambda: next(osc_seq))
    assert flaky.get("_stable") is False, \
        "a non-converging (clock/threshold) verdict must be flagged for characterization, not accepted"


def main() -> int:
    _content_mitigation()
    _disclosure_mitigation()
    _fixpoint_mitigation()
    print("mitigations proven in place: (1) content digest-reproducibility (image img-stable — two "
          "--no-cache builds → same digest); (2) deterministic disclosure (a gate_rec that reads "
          "cannot-run renders n/a and a fail still renders FAIL, driven here with staged records; "
          "on-demand labels; never a false FAIL) — variance confined to build cost")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
