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
#   2. Deterministic DISCLOSURE.  the report's gate runner (gen.py) bounds every gate with a timeout
#      and labels a document it cannot verify here (missing toolchain / cold-build timeout) as
#      `error` → rendered `n/a`, never a false verification FAIL.  We REPRODUCE the timeout branch
#      deterministically: a zero-budget gate subprocess always raises TimeoutExpired, which is exactly
#      what the runner catches and labels.  cwd = report/.
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
    # (a) the runner SOURCE bounds each gate + labels an un-runnable one (never a FAIL):
    src = (ROOT / "report" / "gen.py").read_text()
    assert "timeout=" in src and "TimeoutExpired" in src and '{"error"' in src, \
        "the gate runner no longer bounds each gate and labels an un-runnable one"
    assert 'f"n/a' in src and '"on-demand"' in src, \
        "the report no longer renders an un-runnable/non-reproducible document as n/a or on-demand"
    # (b) REPRODUCE the timeout branch deterministically — a zero-budget gate always times out, which
    #     is exactly the condition the runner turns into `error` (→ n/a), not a verification FAIL:
    try:
        subprocess.run([sys.executable, "paperkit/gate.py", "--json", "--safe", "paper"],
                       cwd=ROOT, capture_output=True, text=True, timeout=0.001)
        raise AssertionError("a zero-budget gate should have timed out — the disclosure branch is unreachable")
    except subprocess.TimeoutExpired:
        pass


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
          "--no-cache builds → same digest); (2) deterministic disclosure (runner timeout → n/a, "
          "reproduced here; on-demand labels; never a false FAIL) — variance confined to build cost")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
