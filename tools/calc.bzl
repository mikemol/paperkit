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

# Τ·mem (RESERVE) — declare each sweep's memory so Bazel's local scheduler bounds CONCURRENT sweeps
# against --local_ram_resources (default HOST_RAM*.67) — PORTABLE memory-bounding for constrained /
# non-zswap machines, the substrate-membudget pool gone Bazel-native (NOT for this dev box, which
# zswap handles; for the general case).  resource_set MUST be a top-level def (Bazel forbids a
# closure), so per-resolution caps are distinct top-level fns; the learned per-claim value
# (Τ·mem·observe → pow2 buckets) will refine these cold-start defaults.  A def sweep (project+engine
# mutation) is far heavier than a file sweep.
def _rs_calc_def(_os, _inputs):
    return {"memory": 2048}

def _rs_calc_file(_os, _inputs):
    return {"memory": 768}

def _calc_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    c = ctx.actions.declare_file(ctx.label.name + ".calc.json")
    p = ctx.actions.declare_file(ctx.label.name + ".peak")
    res = (" --resolution " + ctx.attr.resolution) if ctx.attr.resolution else ""
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
        # Τ·mem (RESERVE) — bound concurrent sweeps against --local_ram_resources (Bazel-native, portable).
        resource_set = _rs_calc_def if ctx.attr.resolution == "def" else _rs_calc_file,
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
