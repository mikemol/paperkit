"""Ζ·verb — each check KIND is a SPECIFIC TYPED Starlark action emitting a RECORD, not a free-form
script.  The resolver's verbs (declared as data in resolver.VERBS) become typed rules, and the
gate an aggregate over their records.  No count is named here — the set grows, this file cannot
see it, and `concept:` is deliberately absent below: it wires through pk_result (bibtex.bzl),
because importing a certificate IS reading a sibling's record.

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

def _basekey(f):
    # a consumed record file is "<key>.verdict.json" → recover <key> (the sibling warrant's name)
    return f.basename[:-len(".verdict.json")] if f.basename.endswith(".verdict.json") else f.basename

def _pypath(py):
    # prepend the hermetic interpreter's dir so `command -v python3` resolves to it (absolute path ⇒
    # sys.executable is populated for any subprocess the tool spawns — see tools/eval.py).
    return 'export PATH="$(cd "$(dirname ' + py.interpreter.path + ')" && pwd):$PATH"; '

def _verdict_tool(py, tool):
    return _pypath(py) + '"$(command -v python3)" ' + tool.path + " "

def _tier_exec(ctx, py, tier):
    """Ζ·tier — resolve a warrant's enforcement tier to the action's (execution_requirements,
    use_default_shell_env, python-PATH-prefix, stamp inputs).  A `toolchain` check must run under the
    HOST toolchain IN FULL — host binaries (pandoc/veraPDF/soffice/lualatex) AND the host python + its
    site-packages (pikepdf, …) — so it inherits the client env (use_default_shell_env) and drops the
    hermetic `_pypath` prepend so `python3` resolves to the host interpreter.  Sound: the check is
    deterministic given a PINNED toolchain, and ctx.info_file (STABLE_TOOLCHAIN_*) keys the cache on
    the toolchain identity — the same argument covers host binaries and host python packages alike."""
    er = {}
    stamp_inputs = []
    host_env = False
    pyprefix = _pypath(py)
    if tier == "local":
        er = {"local": "1", "no-sandbox": "1", "no-cache": "1", "no-remote": "1"}
    elif tier == "toolchain":
        er = {"local": "1", "no-sandbox": "1", "no-remote": "1"}   # cacheable (no no-cache)
        stamp_inputs = [ctx.info_file]   # depend on the stable toolchain fingerprint → precise invalidation
        host_env = True
        pyprefix = ""
    return er, host_env, pyprefix, stamp_inputs

def _cmd_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = _v(ctx)
    inner = "sh -c " + _sq(ctx.attr.cmd)
    # Ρ·wcag·oracle-edge — records-as-deps: `consumes` names sibling warrants' verdict records.  Bazel
    # runs each sibling ONCE (memoized) and stages its verdict.json as an input here; the check reads the
    # cached verdict instead of re-running the sibling's expensive validator (veraPDF 37s).  The records
    # are staged at execroot-relative paths, but the check runs with cwd=project (after the cd below), so
    # export their ABSOLUTE paths — anchored to $PWD captured BEFORE the cd (the pk_agree idiom) — in
    # PAPERKIT_CONSUMED_RECORDS as `key=abspath` pairs, so the check finds each record regardless of cwd.
    consume_prefix = ""
    if ctx.files.consumes:
        pairs = " ".join([_basekey(f) + "=$PWD/" + f.path for f in ctx.files.consumes])
        consume_prefix = 'export PAPERKIT_CONSUMED_RECORDS="' + pairs + '"; '
    if ctx.attr.project and ctx.attr.project != ".":
        inner = "cd " + _sq(ctx.attr.project) + " && " + inner  # cwd = the project dir (relative paths)
    # Ζ·tier — the check's enforcement tier decides how it runs and whether it is cached/swept:
    #   sandbox (default): hermetic linux-sandbox, cached, mutation-swept — a pure check.
    #   local: a HOST-COUPLED check (setup probes the live /proc,/sys, runs a cgroup experiment) — NOT
    #     hermetic AND NOT a function of declared inputs (the machine is unpinned), so run on the host
    #     unsandboxed AND UNCACHED (a cached verdict would bank a host-dependent die-roll).
    #   toolchain: a TOOLCHAIN-COUPLED check (render's veraPDF/lualatex/soffice/pandoc) — needs a real
    #     toolchain the sandbox lacks, so run on the host unsandboxed, BUT it is DETERMINISTIC given a
    #     PINNED toolchain, so it is CACHED and STAMPED with the toolchain fingerprint (ctx.info_file,
    #     the STABLE_TOOLCHAIN_* keys): a toolchain change invalidates it precisely, an unchanged
    #     toolchain is a cache hit — enforceable every commit AND fast.  Cacheable = omit no-cache.
    er, host_env, pyprefix, stamp_inputs = _tier_exec(ctx, py, ctx.attr.tier)
    # The ONE irreducibly-shell oracle: run the arbitrary `cmd` and read its exit code → $V; the
    # record itself is emitted by verdict.py (no JSON built in shell).
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset([ctx.file._tool] + ctx.files.data + ctx.files.consumes + stamp_inputs, transitive = [py.files]),
        use_default_shell_env = host_env,
        # Ζ·sched-batch·phase2 — the check `inner` is an arbitrary compound shell command, not a
        # single exec, so we tune the ACTION SHELL ($$, single-threaded) and inner + the emit inherit
        # (SCHED_BATCH + nice 19 + 100ms slice), matching the per-cell tuning of the grid rules.
        # Ζ·tier·exit — TYPE the exit, engine-aligned with gate.py/discriminate (_REFUSE = 3): a check
        # that CANNOT RUN (its host toolchain is absent — the render checks return 3) is `cannot-run`,
        # NOT `fail`.  rc 0 → pass · rc 3 → cannot-run (not verified here, but not a failure — the gate's
        # bad-set is {fail}, so it does not red the commit) · any other nonzero → fail (ran-and-failed).
        # Closes the false-red: on a toolchain-less box an honest "cannot verify" no longer blocks commits.
        command = pyprefix + consume_prefix + '' +
                  "( " + inner + " ) >/dev/null 2>&1; rc=$?; " +
                  'if [ "$rc" = 0 ]; then V=pass; elif [ "$rc" = 3 ]; then V=cannot-run; else V=fail; fi; ' +
                  '"$(command -v python3)" ' + ctx.file._tool.path + ' emit cmd "$V" ' + v.path,
        # Ρ·check·resource·set — a check action declares NO resource_set, so per-claim checks are
        # scheduled by job count alone while the sweep grid (pk_calc) is memory-bounded per cell.
        # MEASURED before concluding this is a defect: a live check peaks at 16-68MB (discriminate
        # 68, concepts 25, eval 16), against grid cells at 2GB — so 23 concurrent checks cost well
        # under one cell, and bounding them would buy nothing while adding a reservation to every
        # generated target.  The asymmetry is CORRECT: reserve where the cost is, not everywhere.
        # Recorded because the raw sandbox count (23, with the budget flag set) reads like an
        # escape and is not one; the number to look at is RSS, not process count.
        mnemonic = "PkCmd",
        execution_requirements = er,
    )
    return [DefaultInfo(files = depset([v]))]

pk_cmd = rule(
    implementation = _cmd_impl,
    doc = "EXECS — verdict pass iff `cmd` exits 0 (cwd=project) under the toolchain.  Ζ·tier: tier = " +
          "sandbox (hermetic, swept) | local (host-coupled, uncached — Ζ·resist) | toolchain (host " +
          "toolchain, cached + stamped with the toolchain fingerprint).",
    toolchains = [_PY],
    attrs = {
        "cmd": attr.string(mandatory = True),
        "project": attr.string(default = "."),
        "data": attr.label_list(allow_files = True),
        # Ρ·wcag·oracle-edge — sibling warrants whose verdict records this check consumes (records-as-deps:
        # they run once, memoized; their verdict.json is staged + their paths exported in
        # PAPERKIT_CONSUMED_RECORDS as key=abspath, so the check reads the cached verdict, never re-runs it).
        "consumes": attr.label_list(allow_files = True),
        "tier": attr.string(default = "sandbox", values = ["sandbox", "local", "toolchain"]),
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
    # Ζ·tier — the PRODUCERS are the toolchain-coupled work (render's pandoc twice, etc.), so they carry
    # the tier's exec regime exactly like a pk_cmd; the final equality action is a pure verdict.py parse.
    er, host_env, pyprefix, stamp_inputs = _tier_exec(ctx, py, ctx.attr.tier)
    if len(ctx.attr.producers) < 2:
        ctx.actions.run_shell(  # agreement needs >=2 independent producers
            outputs = [v],
            inputs = depset([tool], transitive = [py.files]),
            command = _verdict_tool(py, tool) + "emit agree fail " + v.path,
            mnemonic = "PkAgree",
        )
        return [DefaultInfo(files = depset([v]))]
    # A producer's `cmd` uses paths relative to the PROJECT dir (cwd), exactly like pk_cmd — so `cd`
    # into it before running.  The output must be written to an ABSOLUTE path (o.path is execroot-
    # relative), so anchor it to $PWD captured before the cd.
    prefix = ""
    if ctx.attr.project and ctx.attr.project != ".":
        prefix = "cd " + _sq(ctx.attr.project) + " && "
    inters = []
    for i in range(len(ctx.attr.producers)):
        prod = ctx.attr.producers[i]
        o = ctx.actions.declare_file(ctx.label.name + ".prod" + str(i) + ".out")
        ctx.actions.run_shell(  # each producer's output is an agglomerated INTERMEDIATE artifact
            outputs = [o],
            inputs = depset(stamp_inputs, transitive = [py.files]),
            use_default_shell_env = host_env,
            command = pyprefix + 'O="$PWD/' + o.path + '"; if ( ' + prefix + "sh -c " + _sq(prod) +
                      ' ) > "$O" 2>/dev/null; then :; else echo __FAIL__ > "$O"; fi',
            mnemonic = "PkProducer",
            execution_requirements = er,
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
        "project": attr.string(default = "."),
        "tier": attr.string(default = "sandbox", values = ["sandbox", "local", "toolchain"]),
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
