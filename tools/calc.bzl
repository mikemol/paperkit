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

def _calc_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    c = ctx.actions.declare_file(ctx.label.name + ".calc.json")
    ctx.actions.run_shell(
        outputs = [c],
        inputs = depset(ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + 'export PAPERKIT_ROOT="$PWD"; ' +
                  '"$(command -v python3)" paperkit/discriminate.py --only ' + ctx.attr.claim +
                  " --calc " + ctx.attr.project + " > " + c.path,
        mnemonic = "PkCalc",
        progress_message = "Ζ·calc " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([c]))]

pk_calc = rule(
    implementation = _calc_impl,
    doc = "The per-claim CALCULATION (one mutation sweep) → {claim, baseline, sens}; the cached measurement.",
    toolchains = [_PY],
    attrs = {
        "claim": attr.string(mandatory = True),
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
