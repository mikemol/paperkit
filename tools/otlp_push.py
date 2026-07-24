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

Verify by READ-YOUR-WRITE, never the 200, and NOT the shared counter (cassian's correction,
2026-07-23): a malformed POST returns 200 ingesting zero rows, AND vm_rows_inserted_total is
GLOBAL across producers — with substrate/cassian/us on one store a concurrent push satisfies a
counter delta while our own rows dropped (a masking false-PASS).  So emit a heartbeat gauge
(paperkit_emit_unixtime) whose VALUE is the run's start-unix-time — a token WE control — then poll
/api/v1/query until that exact value queries back.  Still two-oracles / agree: (the send is
determinism, the value querying back is correctness), only the oracle is producer-local, not shared.
Per-commit is FIRE-AND-FORGET (POST, no wait — a fresh sample isn't queryable until the store's
search.latencyOffset ~30s passes, and blocking on it would tax the cycle time we measure); --strict
does the read-your-write poll (deadline clears that offset + first-run name-index) and gates the exit
code for the ⟨P,F,δ⟩ proof.  Best-effort throughout: a down endpoint WARNs, never blocks a commit.

Wire (dependency-free by construction): the OTLP protobuf is built with the ephemeral
opentelemetry-proto lib (`uv run --with opentelemetry-proto` — leaves no venv, the
sched-batch lazy-provision precedent); the /api/v1/query GET is stdlib urllib; absent the proto
lib the push is a warned no-op.  The offline half (parse → map → families → the query-response
value extractor) is pure stdlib and self-proves under --selftest.

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
import urllib.parse
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


EMIT_METRIC = "paperkit_emit_unixtime"  # the read-your-write heartbeat (value = run start-unix-time)


def _extract_values(query_json_text):
    """PURE: pull the sample VALUES out of a VM /api/v1/query JSON response — the read-your-write
    oracle's parse.  Returns a list of floats (one per result series), [] on empty/garbage (so a
    malformed response can never false-verify)."""
    try:
        data = json.loads(query_json_text)
    except (ValueError, TypeError):
        return []
    out = []
    for series in data.get("data", {}).get("result", []):
        v = series.get("value")  # [timestamp, "<value>"]
        if isinstance(v, list) and len(v) == 2:
            try:
                out.append(float(v[1]))
            except (ValueError, TypeError):
                pass
    return out


def query_values(query_url, metric):
    """GET /api/v1/query?query=<metric> and return the queried sample values (best-effort, []
    on failure).  Its own filehandle; the parse is the pure _extract_values."""
    try:
        url = query_url + "?query=" + urllib.parse.quote(metric)
        with urllib.request.urlopen(url, timeout=10) as r:
            return _extract_values(r.read().decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001 — best-effort probe
        print(f"otlp: /api/v1/query GET failed ({e})", file=sys.stderr)
        return []


def _default_query_url(endpoint):
    """Derive the VM query endpoint (scheme://host:port/api/v1/query) from the OTLP URL."""
    m = re.match(r"(https?://[^/]+)", endpoint)
    return (m.group(1) if m else endpoint.rstrip("/")) + "/api/v1/query"


def push(fams, endpoint, query_url, token, deadline=45.0, verify=False):
    """Best-effort push.  `fams` must carry the heartbeat gauge whose value is `token`.  Per-commit
    is FIRE-AND-FORGET (verify=False): POST and return — never wait, since read-your-write can't
    confirm until the store's search.latencyOffset (~30s default) passes and blocking on it would
    tax the very cycle time we measure.  verify=True (--strict / the proof) polls /api/v1/query
    until OUR EXACT token value queries back — ingestion AND queryability of our own data, never
    the shared vm_rows_inserted_total counter (which a concurrent producer can false-pass)."""
    expected = _point_count(fams)
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
          f"heartbeat {EMIT_METRIC}={token}", file=sys.stderr)
    if not verify:
        print("otlp: fire-and-forget (best-effort, unverified — --strict to read-your-write)",
              file=sys.stderr)
        return True
    # poll until OUR heartbeat value queries back.  Value-equality on a token WE chose, so neither
    # a stale value nor another producer's push can verify us.  Deadline must clear the store's
    # search.latencyOffset (default ~30s: instant queries evaluate at now-offset) plus, on the very
    # first push of a new metric name, name-index creation.
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        if any(abs(v - token) < 0.5 for v in query_values(query_url, EMIT_METRIC)):
            print(f"otlp: verified — {EMIT_METRIC} == {token} queried back (our own write)",
                  file=sys.stderr)
            return True
        time.sleep(1.0)
    print(f"otlp: NOT verified — {EMIT_METRIC} == {token} did not query back within {deadline}s "
          f"(a fresh sample isn't queryable until search.latencyOffset ~30s passes)", file=sys.stderr)
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
    # read-your-write oracle: the /api/v1/query value extractor (pure).
    resp = ('{"status":"success","data":{"resultType":"vector","result":'
            '[{"metric":{"__name__":"paperkit_emit_unixtime"},"value":[1690000000.1,"1690000000"]}]}}')
    assert _extract_values(resp) == [1690000000.0], _extract_values(resp)
    # a malformed or empty response yields [] → can NEVER false-verify a token.
    assert _extract_values('{"data":{"result":[]}}') == []
    assert _extract_values("not json") == []
    print("otlp: selftest OK", file=sys.stderr)
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="Ρ·telemetry OTLP build-timing pusher")
    ap.add_argument("execlog", nargs="?", help="bazel --execution_log_json_file output")
    ap.add_argument("--build-seconds", type=float, default=None,
                    help="whole-//:hook wall (the wrapper times the bazel run)")
    ap.add_argument("--endpoint", default=os.environ.get("PAPERKIT_OTLP_METRICS"),
                    help="OTLP metrics URL (default env PAPERKIT_OTLP_METRICS; unset ⇒ no-op)")
    ap.add_argument("--query-url", default=None,
                    help="VM /api/v1/query URL for read-your-write (default derived from --endpoint)")
    ap.add_argument("--deadline", type=float, default=45.0,
                    help="--strict read-your-write poll seconds (must clear the store's "
                         "search.latencyOffset, ~30s default, + first-run name-index)")
    ap.add_argument("--dry-run", action="store_true", help="parse+map, print, no network")
    ap.add_argument("--selftest", action="store_true", help="run the pure-function ⟨P,F,δ⟩")
    ap.add_argument("--strict", action="store_true",
                    help="exit nonzero if read-your-write does not verify (for the ⟨P,F,δ⟩ proof)")
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

    # the read-your-write token: a value WE control (the run's start-unix-time), emitted as a
    # heartbeat gauge and polled back over /api/v1/query — never the shared counter.
    start_unix = int(time.time())
    heartbeat = _family(EMIT_METRIC, [(float(start_unix), {})])
    query_url = a.query_url or _default_query_url(a.endpoint)
    ok = push(fams + [heartbeat], a.endpoint, query_url, start_unix,
              deadline=a.deadline, verify=a.strict)
    return (0 if ok else 1) if a.strict else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
