"""Ζ·calc·interp — separate the CALCULATION (the expensive measurement, computed once) from the
INTERPRETATIONS (cheap readings over it).  pk_calc runs the mutation sweep ONCE → a calc record
{baseline, sens}; pk_verdict and pk_grade are cheap READINGS of that record — the verdict is the
baseline, the grade is grader._grade_from_sens(baseline, sens).  Where the old families each
re-measured (pk_cmd runs the check, pk_grade_claim re-sweeps), here one sweep feeds both, and a
change re-runs only pk_calc; the readings are instant.  footaudit/emergence are the same shape.
"""

_PY = "@bazel_tools//tools/python:toolchain_type"

def _pypath(py):
    return 'export PATH="$(cd "$(dirname ' + py.interpreter.path + ')" && pwd):$PATH"; '

# Τ·mem·observe·clean — a native bool build setting (no skylib) gating the cgroup peak read.  Only
# under --config=memobserve (which sets --//tools:observe=True) is each action in its own cgroup, so
# memory.peak is tree-accurate; OFF, /proc/self/cgroup points at the SHARED bazel cgroup and the read
# is whole-build garbage.  So OFF the peak action writes a clean 0 (honest "not measured") instead.
# Because the flag value is spliced into the command string, it is part of the action KEY: observe
# and default builds cache as DISTINCT actions — a default build can never serve a stale measured
# peak, and an observe build re-measures rather than reusing a default 0.
ObserveInfo = provider(doc = "Τ·mem·observe·clean flag state", fields = ["enabled"])

def _observe_impl(ctx):
    return [ObserveInfo(enabled = ctx.build_setting_value)]

observe_setting = rule(implementation = _observe_impl, build_setting = config.bool(flag = True))

# Τ·mem (RESERVE+LEARN) — declare each sweep's memory so Bazel's local scheduler bounds CONCURRENT
# sweeps against --local_ram_resources (default HOST_RAM*.67) — PORTABLE memory-bounding for
# constrained / non-zswap machines, the substrate-membudget pool gone Bazel-native (NOT for this dev
# box, which zswap handles; for the general case).  resource_set MUST be a top-level def (Bazel
# forbids a closure), so the reservation is one top-level fn PER POW2 BUCKET; the bib generator
# resolves a claim's bucket down a (project,resolution,claim) specificity ladder (= the Ω·config
# ladder) and passes it as the `mem` attr.  mem=0 means "unmeasured" → the cold-start floor by
# resolution (a def sweep, project+engine mutation, is far heavier than a file sweep).  The learned
# layer (Τ·mem·observe → mem.json) overrides these floors per (project,resolution).
def _rs_128(_os, _inputs):
    return {"memory": 128}

def _rs_256(_os, _inputs):
    return {"memory": 256}

def _rs_512(_os, _inputs):
    return {"memory": 512}

def _rs_1024(_os, _inputs):
    return {"memory": 1024}

def _rs_2048(_os, _inputs):
    return {"memory": 2048}

def _rs_4096(_os, _inputs):
    return {"memory": 4096}

def _rs_768(_os, _inputs):
    return {"memory": 768}

# bucket (MB) → its top-level reservation fn.  Learned buckets are pure pow2 (mem_learn clamps to
# [128,4096]); 768 is the file cold-start floor only.  Add a level here if the distribution grows one.
_RS = {128: _rs_128, 256: _rs_256, 512: _rs_512, 1024: _rs_1024, 2048: _rs_2048, 4096: _rs_4096, 768: _rs_768}

def _calc_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    c = ctx.actions.declare_file(ctx.label.name + ".calc.json")
    p = ctx.actions.declare_file(ctx.label.name + ".peak")
    res = (" --resolution " + ctx.attr.resolution) if ctx.attr.resolution else ""
    # Τ·mem — the learned bucket (via the bib generator's ladder), or the cold-start floor by
    # resolution when unmeasured (mem == 0).
    bucket = ctx.attr.mem if ctx.attr.mem else (2048 if ctx.attr.resolution == "def" else 768)
    # Τ·mem·observe·clean — read the cgroup peak ONLY when observing (per-action cgroup ⇒ tree-accurate);
    # otherwise write a clean 0.  The branch makes the flag part of the action key (see ObserveInfo).
    if ctx.attr._observe[ObserveInfo].enabled:
        peak = " ; cat /sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup)/memory.peak > " + p.path + \
               " 2>/dev/null || echo 0 > " + p.path
    else:
        peak = " ; echo 0 > " + p.path
    ctx.actions.run_shell(
        outputs = [c, p],
        inputs = depset(ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + 'export PAPERKIT_ROOT="$PWD"; ' +
                  '"$(command -v python3)" paperkit/discriminate.py --only ' + ctx.attr.claim +
                  " --calc" + res + " " + ctx.attr.project + " > " + c.path + peak,
        mnemonic = "PkCalc",
        progress_message = "Ζ·calc " + ctx.label.name,
        # Τ·mem — bound concurrent sweeps against --local_ram_resources (Bazel-native, portable);
        # the reservation is the learned/floor bucket resolved above.
        resource_set = _RS[bucket],
    )
    # peak in a SEPARATE output group so consumers (verdict/grade/cohere) still see only the calc
    # record; the learned-mem manifest (Τ·mem·learn) reads the "peak" group.
    return [DefaultInfo(files = depset([c])), OutputGroupInfo(peak = depset([p]))]

pk_calc = rule(
    implementation = _calc_impl,
    doc = "The per-claim CALCULATION (one mutation sweep) → {claim, baseline, sens}; the cached measurement.",
    toolchains = [_PY],
    attrs = {
        "claim": attr.string(mandatory = True),
        "project": attr.string(mandatory = True),
        "resolution": attr.string(default = "", doc = "def = per-definition fingerprint (for emergence); else file"),
        "mem": attr.int(default = 0, doc = "Τ·mem learned reservation (MB, a pow2 bucket in _RS); 0 = unmeasured → cold-start floor by resolution"),
        "data": attr.label_list(allow_files = True),
        "_observe": attr.label(default = "@@//tools:observe"),
    },
)

# Τ·mem·learn — the manifest as a Bazel ACTION (orchestration → Bazel, not a hand-run): aggregate
# the `peak` output group of every calc in this project → mem.json, the projection consumed by the
# bib generator's reservation ladder.  Built under --config=memobserve in a clean output base
# (cold ⇒ real, cgroup-isolated peaks); mem_learn.py drops un-isolated reads, so a misrun yields an
# empty manifest, never a wrong one.  An ON-DEMAND projection (like report/, setup/) — the 44-min
# observe is too costly to hook-gate, and a stale mem.json is benign (a floor-bounded perf hint).
def _mem_learn_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    out = ctx.actions.declare_file("mem.json")
    peaks = []
    for t in ctx.attr.calcs:
        peaks += t[OutputGroupInfo].peak.to_list()
    ctx.actions.run_shell(
        outputs = [out],
        inputs = depset([ctx.file._tool] + peaks, transitive = [py.files]),
        command = _pypath(py) + '"$(command -v python3)" ' + ctx.file._tool.path + " " +
                  " ".join([p.path for p in peaks]) + " > " + out.path,
        mnemonic = "PkMemLearn",
        progress_message = "Τ·mem·learn " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([out]))]

pk_mem_learn = rule(
    implementation = _mem_learn_impl,
    doc = "Τ·mem·learn — project a per-project mem.json from the calcs' observed cgroup peaks.",
    toolchains = [_PY],
    attrs = {
        "calcs": attr.label_list(mandatory = True, doc = "every pk_calc in the project (its peak output group is aggregated)"),
        "_tool": attr.label(default = "//tools:mem_learn.py", allow_single_file = True),
    },
)

# Ζ·mutant (PREPARATION) — emit ONE mutated module as a Bazel artifact: `site`'s def-body → raise,
# the rest byte-identical (the pure paperkit/mutate.py transform).  Per (module, site) and
# CLAIM-INDEPENDENT, so Bazel generates it once and SHARES it across every claim whose check tests
# that mutation; an edit to one module invalidates only its own mutated modules.  pk_eval then runs
# a check with this module shadowing the real one on PYTHONPATH (the EVALUATION half).
def _mutate_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    o = ctx.actions.declare_file(ctx.label.name + ".mutated.py")
    ctx.actions.run_shell(
        outputs = [o],
        inputs = depset(ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + '"$(command -v python3)" paperkit/mutate.py ' +
                  ctx.attr.module + " '" + ctx.attr.site + "' > " + o.path,
        mnemonic = "PkMutate",
        progress_message = "Ζ·mutate " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([o]))]

pk_mutate = rule(
    implementation = _mutate_impl,
    doc = "Ζ·mutant preparation — emit one mutated module (site's body→raise) as a cached, claim-independent artifact.",
    toolchains = [_PY],
    attrs = {
        "module": attr.string(mandatory = True, doc = "path of the .py module to mutate, e.g. paperkit/grader.py"),
        "site": attr.string(mandatory = True, doc = "the def-site qualname whose body is replaced"),
        "data": attr.label_list(allow_files = True, doc = "the staged files (mutate.py + the module)"),
    },
)

# Ζ·mutant — ONE (claim, def-site) probe as a Bazel action: mutate exactly `site` and report
# whether it flips the check.  This LIFTS the def-sweep's in-process group-testing fanout into
# Bazel's graph (parallel + per-site cached); pk_sens aggregates the {flipped} records into the
# `sens` fingerprint pk_calc's def sweep computes in-process today.  One check-run, hermetic in its
# own sandbox copy (the per-mutant overhead the spike measures).
def _mutant_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    o = ctx.actions.declare_file(ctx.label.name + ".mutant.json")
    ctx.actions.run_shell(
        outputs = [o],
        inputs = depset(ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + 'export PAPERKIT_ROOT="$PWD"; ' +
                  '"$(command -v python3)" paperkit/discriminate.py --only ' + ctx.attr.claim +
                  " --mutant '" + ctx.attr.site + "' " + ctx.attr.project + " > " + o.path,
        mnemonic = "PkMutant",
        progress_message = "Ζ·mutant " + ctx.label.name,
        resource_set = _RS[512],
    )
    return [DefaultInfo(files = depset([o]))]

pk_mutant = rule(
    implementation = _mutant_impl,
    doc = "Ζ·mutant — one (claim, def-site) mutation probe → {claim, site, flipped}; the sweep's atom as a Bazel action.",
    toolchains = [_PY],
    attrs = {
        "claim": attr.string(mandatory = True),
        "project": attr.string(mandatory = True),
        "site": attr.string(mandatory = True, doc = "the mutation-site label (path or path::qualname)"),
        "data": attr.label_list(allow_files = True),
    },
)

def _cohere_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = ctx.actions.declare_file(ctx.label.name + ".cohere.json")
    calcs = " ".join([c.path for c in ctx.files.calcs])
    # Ζ·emerge·gate — cheap coherence: read the cached calc records (no re-sweep), assert grounding
    # soundness (0 genuine misses).  The ∂² faces gated as a READING over the calculation.
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset(ctx.files.calcs + ctx.files.data, transitive = [py.files]),
        command = _pypath(py) +
                  'if "$(command -v python3)" paperkit/coherence.py --from-calcs ' + ctx.attr.project +
                  " " + calcs + " >/dev/null 2>&1; then V=pass; else V=fail; fi; " +
                  "printf '{\"verb\":\"cohere\",\"verdict\":\"%s\"}\\n' \"$V\" > " + v.path,
        mnemonic = "PkCohere",
        progress_message = "Ζ·emerge·gate cohere " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([v]))]

pk_cohere = rule(
    implementation = _cohere_impl,
    doc = "Ζ·emerge·gate — coherence ∂² as a cheap READING over cached calcs; verdict pass iff grounding sound.",
    toolchains = [_PY],
    attrs = {
        "calcs": attr.label_list(allow_files = True, mandatory = True, doc = "the cached def-resolution calc records"),
        "project": attr.string(mandatory = True),
        "data": attr.label_list(allow_files = True),
    },
)

def _verdict_impl(ctx):
    v = ctx.actions.declare_file(ctx.label.name + ".verdict.json")
    calc = ctx.file.calc
    ctx.actions.run_shell(
        outputs = [v],
        inputs = [calc],
        command = "if grep -q '\"baseline\": true' " + calc.path + "; then V=pass; else V=fail; fi; " +
                  "printf '{\"verb\":\"verdict\",\"verdict\":\"%s\"}\\n' \"$V\" > " + v.path,
        mnemonic = "PkVerdict",
    )
    return [DefaultInfo(files = depset([v]))]

pk_verdict = rule(
    implementation = _verdict_impl,
    doc = "A cheap READING of a calc record: the verdict is the measured baseline.",
    attrs = {"calc": attr.label(allow_single_file = True, mandatory = True)},
)

def _grade_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    g = ctx.actions.declare_file(ctx.label.name + ".grade.json")
    calc = ctx.file.calc
    ctx.actions.run_shell(
        outputs = [g],
        inputs = depset([calc] + ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + '"$(command -v python3)" tools/read_grade.py ' + calc.path + " > " + g.path,
        mnemonic = "PkGradeRead",
        progress_message = "Ζ·calc grade " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([g]))]

pk_grade = rule(
    implementation = _grade_impl,
    doc = "A cheap READING of a calc record: the grade via grader._grade_from_sens (no re-sweep).",
    toolchains = [_PY],
    attrs = {
        "calc": attr.label(allow_single_file = True, mandatory = True),
        "data": attr.label_list(allow_files = True),
    },
)
