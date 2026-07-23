#!/usr/bin/env python3
"""Ρ·telemetry — push paperkit's build-loop timing to an OTLP metrics store (a WRAPPER
concern, OUTSIDE the engine; NOT a gate — telemetry is observation, a down endpoint must
never block a commit).

paperkit-under-bazel has no single "gate run": //:hook is thousands of per-claim actions.
So we do NOT emit per-action (a hermetic linux-sandbox cell has no network — an OTLP POST
from inside a cell is impossible).  Instead the wrapper PARSES bazel's own per-spawn timing
(`--execution_log_json_file`) AFTER the run and pushes it.  Bazel logs only spawns that
EXECUTED (cache hits are absent), so the series reflects exactly the work a commit re-ran —
the desired cycle-time signal (warm commit ⇒ mostly the per-project test wall; an engine
edit ⇒ the PkCalc/PkEval grid appears).

Schema (cassian's, OTLP gauges labeled by project/check_type/target):
  paperkit_check_seconds{project,check_type,target}  per (mnemonic, target) executed wall
  paperkit_gate_seconds{project}                     per-project work-sum (honest: NOT
                                                     isolated wall — bazel overlaps projects)
  paperkit_discriminate_seconds{project}             the Δ sweep subset (PkCalc/PkEval/…)
  paperkit_build_seconds                             whole-//:hook wall (--build-seconds)

Endpoint: PAPERKIT_OTLP_METRICS (a plain env read HERE, NOT an engine config.Param — the
engine resolves no endpoint; threading it through the config registry would be the coupling
Μ·kernel·shrink·registry forbids).  Unset ⇒ no-op, exit 0, default OFF.

Verify by the COUNTER, never the 200 (an empty/malformed OTLP POST returns 200 ingesting
zero rows): read vm_rows_inserted_total before/after and settle-poll (cassian's two-oracles
= agree: on the wire).  Best-effort: exit 0 even on push failure (a WARN, never a block);
--strict flips that for the ⟨P,F,δ⟩ proof.

Wire (dependency-free by construction): the OTLP protobuf is built with the ephemeral
opentelemetry-proto lib (`uv run --with opentelemetry-proto` — leaves no venv, the
sched-batch lazy-provision precedent); the counter GET is stdlib urllib; absent the proto
lib the push is a warned no-op.  The offline half (parse → map → families) is pure stdlib
and self-proves under --selftest.

    uv run --with opentelemetry-proto tools/otlp_push.py execlog.json --build-seconds 402
    python3 tools/otlp_push.py execlog.json --dry-run     # parse+map, no network
    python3 tools/otlp_push.py --selftest                 # pure-function ⟨P,F,δ⟩
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from collections import defaultdict

_PROJECT = re.compile(r"paperkit_([A-Za-z0-9_]+)//")
_LOCAL = re.compile(r"@*//([^/:]+)")
# the Δ (discriminate) sweep mnemonics — calc.bzl / the grid; the second-heaviest phase.
DELTA = {"PkCalc", "PkEval", "PkMutant", "PkSens", "PkMutate", "PkPyc"}


class Spawn:
    __slots__ = ("mnemonic", "label", "wall")

    def __init__(self, mnemonic, label, wall):
        self.mnemonic = mnemonic
        self.label = label
        self.wall = wall

    @property
    def project(self):
        return project_of(self.label)

    @property
    def target(self):
        return target_of(self.label)


def duration_seconds(s):
    """Parse a protobuf Duration JSON string ('6.904s', '0.005s') to float seconds.
    Duration JSON is always seconds with a trailing 's'; guard other shapes defensively."""
    if s is None:
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if s.endswith("ms"):
        return float(s[:-2]) / 1000.0
    if s.endswith("s"):
        s = s[:-1]
    try:
        return float(s)
    except ValueError:
        return 0.0


def project_of(label):
    """@@+bib+paperkit_<name>//:t → <name>; //<pkg>:t → <pkg>; else the label."""
    if not label:
        return "?"
    m = _PROJECT.search(label)
    if m:
        return m.group(1)
    m = _LOCAL.match(label)
    if m:
        return m.group(1)
    return label


def target_of(label):
    if label and ":" in label:
        return label.rsplit(":", 1)[1]
    return label or "?"


def parse_execlog(text):
    """The execution log is CONCATENATED JSON objects (one SpawnExec each), NOT an array.
    Only EXECUTED spawns are present — cache hits are absent (so this is 'what re-ran')."""
    dec = json.JSONDecoder()
    spawns = []
    i, n = 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        obj, i = dec.raw_decode(text, i)
        met = obj.get("metrics") or {}
        spawns.append(Spawn(
            obj.get("mnemonic") or "?",
            obj.get("targetLabel") or "",
            duration_seconds(met.get("executionWallTime")),
        ))
    return spawns


def _family(name, points):
    """points = list of (value, {label:val}).  A gauge family (a per-run snapshot)."""
    return {"name": name, "unit": "s", "points": points}


def metric_families(spawns, build_seconds=None):
    """Aggregate spawns into the cassian schema.  check_seconds is summed per
    (project,check_type,target) so a target is ONE point (bazel may split a test into
    execute+xml spawns — summing their wall is the honest total for that target)."""
    check = defaultdict(float)   # (project, check_type, target) -> wall
    gate = defaultdict(float)    # project -> wall
    disc = defaultdict(float)    # project -> wall
    for s in spawns:
        check[(s.project, s.mnemonic, s.target)] += s.wall
        gate[s.project] += s.wall
        if s.mnemonic in DELTA:
            disc[s.project] += s.wall
    fams = [
        _family("paperkit_check_seconds", [
            (w, {"project": p, "check_type": ct, "target": t})
            for (p, ct, t), w in sorted(check.items())
        ]),
        _family("paperkit_gate_seconds", [
            (w, {"project": p}) for p, w in sorted(gate.items())
        ]),
        _family("paperkit_discriminate_seconds", [
            (w, {"project": p}) for p, w in sorted(disc.items())
        ]),
    ]
    if build_seconds is not None:
        fams.append(_family("paperkit_build_seconds", [(float(build_seconds), {})]))
    return fams


def _point_count(fams):
    return sum(len(f["points"]) for f in fams)


# --- the network half (best-effort; imports the proto lib LAZILY) --------------------

def _build_request(fams, now_ns):
    """Build an ExportMetricsServiceRequest with the opentelemetry-proto classes.
    Raises ImportError if the lib is absent (caller falls back to a warned no-op)."""
    from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
        ExportMetricsServiceRequest)
    from opentelemetry.proto.metrics.v1.metrics_pb2 import (
        ResourceMetrics, ScopeMetrics, Metric, Gauge, NumberDataPoint)
    from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue

    def kv(k, v):
        return KeyValue(key=k, value=AnyValue(string_value=str(v)))

    scope = ScopeMetrics()
    for fam in fams:
        m = Metric(name=fam["name"], unit=fam["unit"])
        g = Gauge()
        for value, attrs in fam["points"]:
            dp = NumberDataPoint(time_unix_nano=now_ns, as_double=float(value))
            dp.attributes.extend([kv(k, v) for k, v in sorted(attrs.items())])
            g.data_points.append(dp)
        m.gauge.CopyFrom(g)
        scope.metrics.append(m)
    res = ResourceMetrics()
    res.resource.attributes.append(kv("service.name", "paperkit"))
    res.scope_metrics.append(scope)
    return ExportMetricsServiceRequest(resource_metrics=[res])


def _post_protobuf(endpoint, payload):
    req = urllib.request.Request(
        endpoint, data=payload,
        headers={"Content-Type": "application/x-protobuf"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status


_COUNTER = re.compile(
    r'^vm_rows_inserted_total\{[^}]*type="opentelemetry"[^}]*\}\s+([0-9.eE+]+)', re.M)


def read_counter(counter_url):
    """GET the /metrics text and return vm_rows_inserted_total{type=opentelemetry}, or None.
    The counter is GLOBAL (all OTLP ingest), so a delta is a NECESSARY lower bound, not
    sufficient — cassian's own rule is >=, not ==.  Its own filehandle; never merged."""
    try:
        with urllib.request.urlopen(counter_url, timeout=10) as r:
            text = r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 — best-effort probe
        print(f"otlp: counter GET failed ({e})", file=sys.stderr)
        return None
    m = _COUNTER.search(text)
    return float(m.group(1)) if m else 0.0


def _default_counter_url(endpoint):
    """Derive the VM counter endpoint (scheme://host:port/metrics) from the OTLP URL."""
    m = re.match(r"(https?://[^/]+)", endpoint)
    return (m.group(1) if m else endpoint.rstrip("/")) + "/metrics"


def push(fams, endpoint, counter_url, deadline=15.0):
    """Best-effort push + counter-guard (the agree: two-oracles).  Returns True iff the
    consumer counter advanced by >= the rows sent within the deadline."""
    expected = _point_count(fams)
    before = read_counter(counter_url)
    try:
        payload = _build_request(fams, time.time_ns()).SerializeToString()
    except ImportError:
        print("otlp: opentelemetry-proto absent — run under "
              "`uv run --with opentelemetry-proto`; push skipped (no-op)", file=sys.stderr)
        return False
    try:
        status = _post_protobuf(endpoint, payload)
    except Exception as e:  # noqa: BLE001
        print(f"otlp: POST to {endpoint} failed ({e})", file=sys.stderr)
        return False
    print(f"otlp: POST {endpoint} -> {status}; {expected} data points; "
          f"counter before={before}", file=sys.stderr)
    if before is None:
        print("otlp: no counter to verify against — transport-acked, ingest UNVERIFIED",
              file=sys.stderr)
        return False
    # settle-poll: rows lag the push ~1s; verify by the counter, not the 200.
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        after = read_counter(counter_url)
        if after is not None and after - before >= expected:
            print(f"otlp: verified — counter {before} -> {after} (>= +{expected})",
                  file=sys.stderr)
            return True
        time.sleep(1.0)
    after = read_counter(counter_url)
    print(f"otlp: NOT verified — counter {before} -> {after}, expected +{expected} "
          f"(200 can ingest 0 rows on a schema slip)", file=sys.stderr)
    return False


# --- self-proof (pure functions; git-free, dep-free) ---------------------------------

def _selftest():
    # P: a warm TestRunner spawn + a cold PkEval spawn map to the right project/target.
    warm = Spawn("TestRunner", "@@+bib+paperkit_paper//:gate", 3.5)
    cold = Spawn("PkEval", "@@+bib+paperkit_paper//:some-claim__eval", 0.4)
    canary = Spawn("TestRunner", "//canary:canary", 1.0)
    assert warm.project == "paper" and warm.target == "gate", (warm.project, warm.target)
    assert cold.project == "paper" and cold.target == "some-claim__eval"
    assert canary.project == "canary" and canary.target == "canary"
    # duration parsing (protobuf Duration JSON + defensive shapes)
    assert duration_seconds("6.904s") == 6.904
    assert duration_seconds("0.005s") == 0.005
    assert duration_seconds("500ms") == 0.5
    assert duration_seconds(None) == 0.0
    # families: gate_seconds rolls up check_seconds; discriminate_seconds is the Δ subset.
    fams = metric_families([warm, cold, canary], build_seconds=402.0)
    byname = {f["name"]: f for f in fams}
    gate = dict((tuple(sorted(a.items())), v) for v, a in byname["paperkit_gate_seconds"]["points"])
    assert gate[(("project", "paper"),)] == 3.9, gate     # 3.5 + 0.4
    assert gate[(("project", "canary"),)] == 1.0, gate
    disc = dict((tuple(sorted(a.items())), v) for v, a in byname["paperkit_discriminate_seconds"]["points"])
    assert disc[(("project", "paper"),)] == 0.4, disc     # only the PkEval spawn
    assert byname["paperkit_build_seconds"]["points"] == [(402.0, {})]
    # F: an empty execlog yields empty families (no vacuous points) and zero rows.
    empty = metric_families([])
    assert _point_count(empty) == 0, empty
    # counter regex extracts the labeled series only.
    txt = ('vm_rows_inserted_total{type="graphite"} 5\n'
           'vm_rows_inserted_total{path="/x",type="opentelemetry"} 42\n')
    assert _COUNTER.search(txt).group(1) == "42"
    # δ: dropping the label leaves the wrong series unmatched → guard cannot false-verify.
    assert _COUNTER.search('vm_rows_inserted_total{type="influx"} 7\n') is None
    print("otlp: selftest OK", file=sys.stderr)
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="Ρ·telemetry OTLP build-timing pusher")
    ap.add_argument("execlog", nargs="?", help="bazel --execution_log_json_file output")
    ap.add_argument("--build-seconds", type=float, default=None,
                    help="whole-//:hook wall (the wrapper times the bazel run)")
    ap.add_argument("--endpoint", default=os.environ.get("PAPERKIT_OTLP_METRICS"),
                    help="OTLP metrics URL (default env PAPERKIT_OTLP_METRICS; unset ⇒ no-op)")
    ap.add_argument("--counter", default=None,
                    help="VM counter /metrics URL (default derived from --endpoint)")
    ap.add_argument("--deadline", type=float, default=15.0, help="counter settle-poll seconds")
    ap.add_argument("--dry-run", action="store_true", help="parse+map, print, no network")
    ap.add_argument("--selftest", action="store_true", help="run the pure-function ⟨P,F,δ⟩")
    ap.add_argument("--strict", action="store_true",
                    help="exit nonzero if the counter-guard does not verify (for ⟨P,F,δ⟩)")
    a = ap.parse_args(argv)

    if a.selftest:
        return _selftest()
    if not a.execlog:
        ap.error("execlog path required (or --selftest)")

    try:
        text = open(a.execlog, encoding="utf-8").read()
    except OSError as e:
        print(f"otlp: cannot read execlog {a.execlog} ({e})", file=sys.stderr)
        return 0  # best-effort: a missing log never blocks
    fams = metric_families(parse_execlog(text), build_seconds=a.build_seconds)

    if a.dry_run or not a.endpoint:
        if not a.endpoint and not a.dry_run:
            print("otlp: PAPERKIT_OTLP_METRICS unset — no-op (default OFF)", file=sys.stderr)
        json.dump({"data_points": _point_count(fams), "families": fams}, sys.stdout, indent=1)
        sys.stdout.write("\n")
        return 0

    counter_url = a.counter or _default_counter_url(a.endpoint)
    ok = push(fams, a.endpoint, counter_url, deadline=a.deadline)
    return (0 if ok else 1) if a.strict else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
