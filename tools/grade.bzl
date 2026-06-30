"""Ζ·pi — the Δ GRADE is a build graph, run under the HERMETIC python toolchain (Ζ·toolchain).

The Δ sweep is decomposed INTO Bazel: a grade is the SAME check re-run over the baseline and each
mutated input, aggregated — each rerun its own action, Bazel's sandbox the mutation sandbox.  The
reruns run under rules_python's HERMETIC interpreter (not host python3), so sys.executable is
DEFINED — the engine's subprocess-spawning (gate→check→…) works in a build action, where host
python left it empty.  No python-spawning-host-python; the toolchain is the interpreter.

Proof: baseline + ONE mutant (a sensitive engine file) for a real check.  The full per-footprint
fan-out + ladder + rests_on clamp is the scaled version.
"""

_PY = "@bazel_tools//tools/python:toolchain_type"

def _pypath(py):
    return 'export PATH="$(cd "$(dirname ' + py.interpreter.path + ')" && pwd):$PATH"; '

def _verdict_tool(py, tool):
    return _pypath(py) + '"$(command -v python3)" ' + tool.path + " "

def _rerun(ctx, tag, mutate):
    """A Bazel action: stage the inputs, optionally corrupt `mutate`, run `gate.py --only` under
    the HERMETIC python (so the check + its subprocesses have a real sys.executable)."""
    py3 = ctx.toolchains["@bazel_tools//tools/python:toolchain_type"].py3_runtime
    interp = py3.interpreter.path
    v = ctx.actions.declare_file("%s.%s.verdict" % (ctx.label.name, tag))
    files = " ".join([f.path for f in ctx.files.data])
    corrupt = ('printf "\\nZ_PI_MUTATION = (\\n" >> "$D/%s"; ' % mutate) if mutate else ""
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset(ctx.files.data, transitive = [py3.files]),
        command = ('set -e; D=$(mktemp -d); cp --parents %s "$D/"; %s' +
                   'PY=$(cd "$(dirname %s)" && pwd)/$(basename %s); export PATH="$(dirname "$PY"):$PATH"; ' +
                   'if (cd "$D" && "$PY" paperkit/gate.py --only %s %s) >"$D/o" 2>&1; ' +
                   'then echo pass > %s; else { echo fail; tail -8 "$D/o"; } > %s; fi; rm -rf "$D"') % (
            files, corrupt, interp, interp, ctx.attr.claim, ctx.attr.project, v.path, v.path),
        mnemonic = "PkRerun",
        progress_message = "Ζ·pi rerun %s (%s)" % (ctx.label.name, tag),
    )
    return v

def _impl(ctx):
    name = ctx.label.name
    baseline = _rerun(ctx, "baseline", "")               # the check on the pristine staged tree
    mutant = _rerun(ctx, "mutant", ctx.attr.mutate)      # the check with one input corrupted
    grade = ctx.actions.declare_file(name + ".grade.json")
    ctx.actions.run_shell(
        outputs = [grade],
        inputs = [baseline, mutant],
        command = ('b=$(head -1 %s); m=$(head -1 %s); ' +
                   'if [ "$b" != pass ]; then g=broken; ' +
                   'elif [ "$m" = fail ]; then g=behavioral; else g=indeterminate; fi; ' +
                   'printf \'{"claim":"%s","grade":"%%s","baseline":"%%s","mutant":"%%s","mutated":"%s"}\\n\' ' +
                   '"$g" "$b" "$m" > %s') % (
            baseline.path, mutant.path, ctx.attr.claim, ctx.attr.mutate, grade.path),
        mnemonic = "PkGrade",
        progress_message = "Ζ·pi grade %s" % name,
    )
    return [DefaultInfo(files = depset([grade]))]

pk_grade = rule(
    implementation = _impl,
    doc = "A claim's Δ grade by Bazel actions (baseline + mutant reruns under the hermetic python + aggregate).",
    toolchains = ["@bazel_tools//tools/python:toolchain_type"],
    attrs = {
        "claim": attr.string(mandatory = True),
        "project": attr.string(mandatory = True),
        "data": attr.label_list(allow_files = True, doc = "engine + project files, staged into the rerun tree"),
        "mutate": attr.string(mandatory = True, doc = "a repo-relative input file to corrupt for the mutant"),
    },
)

# Ζ·nest — the per-claim grade as a Bazel action (the grade record family, sibling of pk_cmd's
# verdict).  discriminate --only is the grade ORACLE (the full sensitivity sweep + ladder stays in
# the engine grader, which Bazel can't statically fan out); Bazel NESTS one per claim and pk_adequacy
# aggregates them — so the whole-project SWEEP is the build graph, not discriminate's loop.
# PAPERKIT_ROOT pins the grader's sandbox universe to the execroot (the staged project + engine).
def _grade_claim_impl(ctx):
    py = ctx.toolchains["@bazel_tools//tools/python:toolchain_type"].py3_runtime
    interp = py.interpreter.path
    v = ctx.actions.declare_file(ctx.label.name + ".grade.json")
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset(ctx.files.data, transitive = [py.files]),
        command = ('PY=$(cd "$(dirname ' + interp + ')" && pwd)/$(basename ' + interp + '); ' +
                   'export PATH="$(dirname "$PY"):$PATH"; export PAPERKIT_ROOT="$PWD"; ' +
                   '"$PY" paperkit/discriminate.py --only ' + ctx.attr.claim + " " + ctx.attr.project +
                   " > " + v.path),
        mnemonic = "PkGradeClaim",
        progress_message = "Ζ·nest grade " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([v]))]

pk_grade_claim = rule(
    implementation = _grade_claim_impl,
    doc = "Grade ONE claim (discriminate --only, the per-claim grade oracle) → a grade record.",
    toolchains = ["@bazel_tools//tools/python:toolchain_type"],
    attrs = {
        "claim": attr.string(mandatory = True),
        "project": attr.string(mandatory = True),
        "data": attr.label_list(allow_files = True),
    },
)

# Ζ·nest — pk_adequacy aggregates per-claim grade RECORDS into the project's adequacy verdict (the
# batched equality, sibling of pk_gate over verdicts): pass iff every claim grades at the behavioral
# floor or above (the old `discriminate --min-strength behavioral` gate, which reads the RAW grade).
def _adequacy_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = ctx.actions.declare_file(ctx.label.name + ".verdict.json")
    paths = " ".join([g.path for g in ctx.files.grades])
    # PARSES each grade record (verdict.py agg) — fail iff any grade is below the behavioral floor.
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset([ctx.file._tool] + ctx.files.grades, transitive = [py.files]),
        command = _verdict_tool(py, ctx.file._tool) +
                  "agg adequacy " + v.path + " grade vacuous,existence,indeterminate,broken " + paths,
        mnemonic = "PkAdequacy",
    )
    return [DefaultInfo(files = depset([v]))]

pk_adequacy = rule(
    implementation = _adequacy_impl,
    doc = "Aggregate per-claim grade records → adequacy verdict: pass iff all grades >= behavioral.",
    toolchains = [_PY],
    attrs = {
        "grades": attr.label_list(allow_files = True, mandatory = True),
        "_tool": attr.label(default = "//tools:verdict.py", allow_single_file = True),
    },
)

# Ζ·foot·act — the per-claim FOOTPRINT-AUDIT as a Bazel action (the footprint record family, sibling
# of verdict/grade).  footdeps --only is the oracle (strace the check, compare its dep tokens to the
# claim's declared reads); Bazel nests one per claim and pk_footaudit aggregates — dissolving
# footdeps' ThreadPool.  Data is GENEROUS (all projects) so the strace sees reads BEYOND the
# declaration (else an under-declared read is just an absent file, not a detected miss).
def _footprint_impl(ctx):
    py = ctx.toolchains["@bazel_tools//tools/python:toolchain_type"].py3_runtime
    interp = py.interpreter.path
    v = ctx.actions.declare_file(ctx.label.name + ".foot.json")
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset(ctx.files.data, transitive = [py.files]),
        command = ('PY=$(cd "$(dirname ' + interp + ')" && pwd)/$(basename ' + interp + '); ' +
                   'export PATH="$(dirname "$PY"):$PATH"; ' +
                   '"$PY" paperkit/footdeps.py --only ' + ctx.attr.claim + " " + ctx.attr.project +
                   " > " + v.path),
        mnemonic = "PkFootprint",
        progress_message = "Ζ·foot·act " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([v]))]

pk_footprint = rule(
    implementation = _footprint_impl,
    doc = "Audit ONE claim's footprint vs its declared reads (footdeps --only) → a foot record.",
    toolchains = ["@bazel_tools//tools/python:toolchain_type"],
    attrs = {
        "claim": attr.string(mandatory = True),
        "project": attr.string(mandatory = True),
        "data": attr.label_list(allow_files = True),
    },
)

# Ζ·foot·act — pk_footaudit aggregates per-claim foot RECORDS into the project's audit verdict
# (sibling of pk_gate/pk_adequacy): pass iff every claim's footprint is covered by its declared
# reads (no record reads "ok": false).  On-demand (declare+audit), not in //:hook.
def _footaudit_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = ctx.actions.declare_file(ctx.label.name + ".verdict.json")
    paths = " ".join([f.path for f in ctx.files.foots])
    # PARSES each foot record (verdict.py agg) — fail iff any footprint is not ⊆ declared reads.
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset([ctx.file._tool] + ctx.files.foots, transitive = [py.files]),
        command = _verdict_tool(py, ctx.file._tool) + "agg footaudit " + v.path + " ok false " + paths,
        mnemonic = "PkFootAudit",
    )
    return [DefaultInfo(files = depset([v]))]

pk_footaudit = rule(
    implementation = _footaudit_impl,
    doc = "Aggregate per-claim foot records → audit verdict: pass iff every footprint ⊆ declared reads.",
    toolchains = [_PY],
    attrs = {
        "foots": attr.label_list(allow_files = True, mandatory = True),
        "_tool": attr.label(default = "//tools:verdict.py", allow_single_file = True),
    },
)
