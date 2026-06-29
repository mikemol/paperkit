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
    ctx.actions.run_shell(
        outputs = [c, p],
        inputs = depset(ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + 'export PAPERKIT_ROOT="$PWD"; ' +
                  '"$(command -v python3)" paperkit/discriminate.py --only ' + ctx.attr.claim +
                  " --calc" + res + " " + ctx.attr.project + " > " + c.path +
                  # Τ·mem·observe — this action's cgroup memory.peak (tree-accurate; the ONLY observe
                  # channel — Bazel's log has no peak).  Meaningful under --config=memobserve (each
                  # action in its own cgroup); best-effort — degrades to 0 where cgroups are absent.
                  " ; cat /sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup)/memory.peak > " + p.path +
                  " 2>/dev/null || echo 0 > " + p.path,
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
