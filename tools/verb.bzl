"""Ζ·verb — each check KIND is a SPECIFIC TYPED Starlark action emitting a RECORD, not a general
script that may drop to python.  The resolver's four verbs (resolver.py resolves()) become four
rules, and the gate an aggregate over their records:

    pk_file   EXISTS  — a path is present in the staged inputs (no oracle beyond a test)
    pk_cmd    EXECS   — a command exits 0 (oracle: the exit code, under the hermetic toolchain)
    pk_result PARSES  — a sibling's verdict RECORD (a dep — records-as-artifacts) reads pass
    pk_agree  CONCURS — N producers' outputs (agglomerated intermediates) are all-equal & all-ok
    pk_gate           — aggregates verdict records to ONE verdict (the batched equality, as a whole)

Each emits a verdict record (a build artifact); python is dropped-to ONLY for the irreducible
per-verb oracle, under the toolchain — never a free-form script.  bazel = the proof structure,
the verdict = the equality oracle, the record = the artifact downstream proofs depend on.
"""

_PY = "@bazel_tools//tools/python:toolchain_type"

def _sq(s):
    return "'" + s.replace("'", "'\\''") + "'"  # shell single-quote a literal

def _v(ctx):
    return ctx.actions.declare_file(ctx.label.name + ".verdict.json")

def _rec(v, verb):
    # the trailing snippet: write the verdict record given shell $V = pass|fail
    return " printf '{\"verb\":\"" + verb + "\",\"verdict\":\"%s\"}\\n' \"$V\" > " + v.path

def _pypath(py):
    # prepend the hermetic interpreter's dir so a check's bare `python3` resolves to it
    return 'export PATH="$(cd "$(dirname ' + py.interpreter.path + ')" && pwd):$PATH"; '

def _cmd_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = _v(ctx)
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset(ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + "if sh -c " + _sq(ctx.attr.cmd) +
                  " >/dev/null 2>&1; then V=pass; else V=fail; fi;" + _rec(v, "cmd"),
        mnemonic = "PkCmd",
    )
    return [DefaultInfo(files = depset([v]))]

pk_cmd = rule(
    implementation = _cmd_impl,
    doc = "EXECS — verdict pass iff `cmd` exits 0, under the hermetic toolchain.",
    toolchains = [_PY],
    attrs = {"cmd": attr.string(mandatory = True), "data": attr.label_list(allow_files = True)},
)

def _file_impl(ctx):
    v = _v(ctx)
    ctx.actions.run_shell(
        outputs = [v],
        inputs = ctx.files.data,
        command = "if [ -f " + _sq(ctx.attr.path) + " ]; then V=pass; else V=fail; fi;" + _rec(v, "file"),
        mnemonic = "PkFile",
    )
    return [DefaultInfo(files = depset([v]))]

pk_file = rule(
    implementation = _file_impl,
    doc = "EXISTS — verdict pass iff `path` is present in the staged `data`.",
    attrs = {"path": attr.string(mandatory = True), "data": attr.label_list(allow_files = True)},
)

def _result_impl(ctx):
    v = _v(ctx)
    sib = ctx.file.sibling_verdict
    ctx.actions.run_shell(
        outputs = [v],
        inputs = [sib],
        command = "if grep -q '\"verdict\":\"pass\"' " + sib.path +
                  "; then V=pass; else V=fail; fi;" + _rec(v, "result"),
        mnemonic = "PkResult",
    )
    return [DefaultInfo(files = depset([v]))]

pk_result = rule(
    implementation = _result_impl,
    doc = "PARSES — verdict pass iff the sibling's verdict RECORD (a dep) reads pass. Records-as-deps.",
    attrs = {"sibling_verdict": attr.label(allow_single_file = True, mandatory = True)},
)

def _agree_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = _v(ctx)
    if len(ctx.attr.producers) < 2:
        ctx.actions.run_shell(  # agreement needs >=2 independent producers
            outputs = [v], command = "V=fail;" + _rec(v, "agree"), mnemonic = "PkAgree",
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
    paths = " ".join([o.path for o in inters])
    ctx.actions.run_shell(  # batched equality over the whole set of intermediates
        outputs = [v],
        inputs = inters,
        command = 'if [ "$(sort -u ' + paths + ' | wc -l)" = 1 ] && ! grep -q __FAIL__ ' + paths +
                  "; then V=pass; else V=fail; fi;" + _rec(v, "agree"),
        mnemonic = "PkAgree",
    )
    return [DefaultInfo(files = depset([v]))]

pk_agree = rule(
    implementation = _agree_impl,
    doc = "CONCURS — >=2 producers' outputs, agglomerated, all-equal & all-ok. Batched equality.",
    toolchains = [_PY],
    attrs = {"producers": attr.string_list(mandatory = True)},
)

def _gate_impl(ctx):
    v = _v(ctx)
    paths = " ".join([r.path for r in ctx.files.checks])
    ctx.actions.run_shell(
        outputs = [v],
        inputs = ctx.files.checks,
        command = "if grep -h -q '\"verdict\":\"fail\"' " + paths +
                  "; then V=fail; else V=pass; fi;" + _rec(v, "gate"),
        mnemonic = "PkGate",
    )
    return [DefaultInfo(files = depset([v]))]

pk_gate = rule(
    implementation = _gate_impl,
    doc = "Aggregate verdict RECORDS to one verdict — pass iff none reads fail. The gate IS a check.",
    attrs = {"checks": attr.label_list(allow_files = True, mandatory = True)},
)
