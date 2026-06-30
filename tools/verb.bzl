"""Ζ·verb — each check KIND is a SPECIFIC TYPED Starlark action emitting a RECORD, not a free-form
script.  The resolver's four verbs (resolver.py resolves()) become four rules, and the gate an
aggregate over their records:

    pk_file   EXISTS  — a path is present in the staged inputs
    pk_cmd    EXECS   — a command exits 0 (the one irreducibly-shell oracle: run arbitrary `cmd`)
    pk_result PARSES  — a sibling's verdict RECORD (a dep — records-as-artifacts) reads pass
    pk_agree  CONCURS — N producers' outputs (agglomerated intermediates) are all-equal & all-ok
    pk_gate           — aggregates verdict records to ONE verdict (pass iff none reads fail)

Each emits the {verb, verdict} record through tools/verdict.py — the ONE authority for that record's
format and oracles.  The verdict is COMPUTED and the record is PARSED in python (json), never built
or grepped in a shell string: a verb's only inline shell is the irreducible oracle that runs an
ARBITRARY command (pk_cmd's `sh -c cmd`, pk_agree's producers).  bazel = the proof structure, the
record = the artifact downstream proofs depend on.
"""

_PY = "@bazel_tools//tools/python:toolchain_type"
_VERDICT = "//tools:verdict.py"

def _sq(s):
    return "'" + s.replace("'", "'\\''") + "'"  # shell single-quote a literal

def _v(ctx):
    return ctx.actions.declare_file(ctx.label.name + ".verdict.json")

def _pypath(py):
    # prepend the hermetic interpreter's dir so `command -v python3` resolves to it (absolute path ⇒
    # sys.executable is populated for any subprocess the tool spawns — see tools/eval.py).
    return 'export PATH="$(cd "$(dirname ' + py.interpreter.path + ')" && pwd):$PATH"; '

def _verdict_tool(py, tool):
    return _pypath(py) + '"$(command -v python3)" ' + tool.path + " "

def _cmd_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = _v(ctx)
    inner = "sh -c " + _sq(ctx.attr.cmd)
    if ctx.attr.project and ctx.attr.project != ".":
        inner = "cd " + _sq(ctx.attr.project) + " && " + inner  # cwd = the project dir (relative paths)
    er = {}
    if ctx.attr.local:
        # Ζ·resist — a HOST-COUPLED check (setup probes the live /proc,/sys and runs a cgroup
        # experiment): NOT hermetic, so run on the host, unsandboxed, and uncached (the machine
        # is not a declared input, so a cached verdict would be unsound).  The sanctioned escape.
        er = {"local": "1", "no-sandbox": "1", "no-cache": "1", "no-remote": "1"}
    # The ONE irreducibly-shell oracle: run the arbitrary `cmd` and read its exit code → $V; the
    # record itself is emitted by verdict.py (no JSON built in shell).
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset([ctx.file._tool] + ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + "if ( " + inner + " ) >/dev/null 2>&1; then V=pass; else V=fail; fi; " +
                  '"$(command -v python3)" ' + ctx.file._tool.path + ' emit cmd "$V" ' + v.path,
        mnemonic = "PkCmd",
        execution_requirements = er,
    )
    return [DefaultInfo(files = depset([v]))]

pk_cmd = rule(
    implementation = _cmd_impl,
    doc = "EXECS — verdict pass iff `cmd` exits 0 (cwd=project) under the toolchain; local=host escape (Ζ·resist).",
    toolchains = [_PY],
    attrs = {
        "cmd": attr.string(mandatory = True),
        "project": attr.string(default = "."),
        "data": attr.label_list(allow_files = True),
        "local": attr.bool(default = False),
        "_tool": attr.label(default = _VERDICT, allow_single_file = True),
    },
)

def _file_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = _v(ctx)
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset([ctx.file._tool] + ctx.files.data, transitive = [py.files]),
        command = _verdict_tool(py, ctx.file._tool) + "exists file " + _sq(ctx.attr.path) + " " + v.path,
        mnemonic = "PkFile",
    )
    return [DefaultInfo(files = depset([v]))]

pk_file = rule(
    implementation = _file_impl,
    doc = "EXISTS — verdict pass iff `path` is present in the staged `data`.",
    toolchains = [_PY],
    attrs = {
        "path": attr.string(mandatory = True),
        "data": attr.label_list(allow_files = True),
        "_tool": attr.label(default = _VERDICT, allow_single_file = True),
    },
)

def _result_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = _v(ctx)
    sib = ctx.file.sibling_verdict
    # PARSES the sibling record (verdict.py agg) — pass iff it does not read fail; never greps it.
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset([ctx.file._tool, sib], transitive = [py.files]),
        command = _verdict_tool(py, ctx.file._tool) + "agg result " + v.path + " verdict fail " + sib.path,
        mnemonic = "PkResult",
    )
    return [DefaultInfo(files = depset([v]))]

pk_result = rule(
    implementation = _result_impl,
    doc = "PARSES — verdict pass iff the sibling's verdict RECORD (a dep) reads pass. Records-as-deps.",
    toolchains = [_PY],
    attrs = {
        "sibling_verdict": attr.label(allow_single_file = True, mandatory = True),
        "_tool": attr.label(default = _VERDICT, allow_single_file = True),
    },
)

def _agree_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = _v(ctx)
    tool = ctx.file._tool
    if len(ctx.attr.producers) < 2:
        ctx.actions.run_shell(  # agreement needs >=2 independent producers
            outputs = [v],
            inputs = depset([tool], transitive = [py.files]),
            command = _verdict_tool(py, tool) + "emit agree fail " + v.path,
            mnemonic = "PkAgree",
        )
        return [DefaultInfo(files = depset([v]))]
    inters = []
    for i in range(len(ctx.attr.producers)):
        prod = ctx.attr.producers[i]
        o = ctx.actions.declare_file(ctx.label.name + ".prod" + str(i) + ".out")
        ctx.actions.run_shell(  # each producer's output is an agglomerated INTERMEDIATE artifact
            outputs = [o],
            inputs = depset(transitive = [py.files]),
            command = _pypath(py) + "if sh -c " + _sq(prod) + " > " + o.path +
                      " 2>/dev/null; then :; else echo __FAIL__ > " + o.path + "; fi",
            mnemonic = "PkProducer",
        )
        inters.append(o)
    # PARSES the producer outputs (verdict.py agree) — pass iff all byte-equal and none failed.
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset([tool] + inters, transitive = [py.files]),
        command = _verdict_tool(py, tool) + "agree agree " + v.path + " " + " ".join([o.path for o in inters]),
        mnemonic = "PkAgree",
    )
    return [DefaultInfo(files = depset([v]))]

pk_agree = rule(
    implementation = _agree_impl,
    doc = "CONCURS — >=2 producers' outputs, agglomerated, all-equal & all-ok. Batched equality.",
    toolchains = [_PY],
    attrs = {
        "producers": attr.string_list(mandatory = True),
        "_tool": attr.label(default = _VERDICT, allow_single_file = True),
    },
)

def _gate_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = _v(ctx)
    # PARSES every child verdict record (verdict.py agg) — pass iff none reads fail.
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset([ctx.file._tool] + ctx.files.checks, transitive = [py.files]),
        command = _verdict_tool(py, ctx.file._tool) + "agg gate " + v.path + " verdict fail " +
                  " ".join([r.path for r in ctx.files.checks]),
        mnemonic = "PkGate",
    )
    return [DefaultInfo(files = depset([v]))]

pk_gate = rule(
    implementation = _gate_impl,
    doc = "Aggregate verdict RECORDS to one verdict — pass iff none reads fail. The gate IS a check.",
    toolchains = [_PY],
    attrs = {
        "checks": attr.label_list(allow_files = True, mandatory = True),
        "_tool": attr.label(default = _VERDICT, allow_single_file = True),
    },
)
