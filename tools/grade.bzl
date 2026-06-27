"""Ζ·pi — the Δ GRADE is a build graph, run under the HERMETIC python toolchain (Ζ·toolchain).

The Δ sweep is decomposed INTO Bazel: a grade is the SAME check re-run over the baseline and each
mutated input, aggregated — each rerun its own action, Bazel's sandbox the mutation sandbox.  The
reruns run under rules_python's HERMETIC interpreter (not host python3), so sys.executable is
DEFINED — the engine's subprocess-spawning (gate→check→…) works in a build action, where host
python left it empty.  No python-spawning-host-python; the toolchain is the interpreter.

Proof: baseline + ONE mutant (a sensitive engine file) for a real check.  The full per-footprint
fan-out + ladder + rests_on clamp is the scaled version.
"""

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
