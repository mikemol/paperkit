"""Ζ·compose — a witness is a build ARTIFACT, and rests-on is a build DEP (proof composition).

A claim's check emits its witness IFF the claim holds (else the action FAILS — no artifact); a claim
that rests-on others takes their witness artifacts as INPUTS.  So the bib's grounding DAG becomes the
build DAG: a dependent cannot build unless every premise's witness was produced (the premise was
proven).  build-success = proven — the Agda model, where a proof of B consumes the proof of A as a
term.  A premise is just a label — `//:local` (rests-on) or `@other-paper//:witness` (importing a
paper's results = treating it as a library); the package boundary is not semantic, so there is no
`result:` special case.  pk_proof builds the whole DAG (every witness); building it proves the paper.
"""

_PY = "@bazel_tools//tools/python:toolchain_type"

def _sq(s):
    return "'" + s.replace("'", "'\\''") + "'"

def _pypath(py):
    return 'export PATH="$(cd "$(dirname ' + py.interpreter.path + ')" && pwd):$PATH"; '

def _witness_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    w = ctx.actions.declare_file(ctx.label.name + ".witness.json")
    prem = " ".join([p.path for p in ctx.files.premises])
    # The premises are INPUTS, and this action CONSUMES them (reads each, like the linker reads
    # file.o — not just test -f).  A premise whose claim does not hold emits no artifact → this
    # dependent cannot build; and a premise whose artifact does not assert its fact is rejected.
    guard = ("for p in " + prem + "; do grep -qE '\"(witness|proof)\":\"(holds|complete)\"' \"$p\" || exit 1; done; ") if prem else ""
    inner = "sh -c " + _sq(ctx.attr.holds)
    if ctx.attr.project and ctx.attr.project != ".":
        inner = "cd " + _sq(ctx.attr.project) + " && " + inner
    ctx.actions.run_shell(
        outputs = [w],
        inputs = depset(ctx.files.premises + ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + guard + "if ( " + inner + " ) >/dev/null 2>&1; then " +
                  "echo '{\"claim\":\"" + ctx.label.name + "\",\"witness\":\"holds\"}' > " + w.path +
                  "; else echo 'witness " + ctx.label.name + " does not hold' >&2; exit 1; fi",
        mnemonic = "PkWitness",
        progress_message = "Ζ·compose witness " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([w]))]

pk_witness = rule(
    implementation = _witness_impl,
    doc = "A claim's witness as a build artifact: emitted iff `holds` (cwd=project, toolchain), consuming `premises`.",
    toolchains = [_PY],
    attrs = {
        "holds": attr.string(mandatory = True, doc = "the witness body — a shell cmd; exit 0 = the claim holds"),
        "project": attr.string(default = "."),
        "premises": attr.label_list(allow_files = True, doc = "rests-on ∪ imports: premise claims' witnesses (any package)"),
        "data": attr.label_list(allow_files = True),
    },
)

def _proof_impl(ctx):
    p = ctx.actions.declare_file(ctx.label.name + ".proof.json")
    ctx.actions.run_shell(
        outputs = [p],
        inputs = ctx.files.witnesses,
        command = "echo '{\"proof\":\"complete\",\"witnesses\":" + str(len(ctx.files.witnesses)) +
                  "}' > " + p.path,
        mnemonic = "PkProof",
        progress_message = "Ζ·compose proof " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([p]))]

pk_proof = rule(
    implementation = _proof_impl,
    doc = "The whole proof DAG: depends on every witness, so building it proves the project (build = proven).",
    attrs = {"witnesses": attr.label_list(allow_files = True, mandatory = True)},
)
