"""Ζ·compose — a witness is a build ARTIFACT, and rests-on is a build DEP (proof composition).

A claim's check emits its witness IFF the claim holds (else the action FAILS — no artifact); a claim
that rests-on others takes their witness artifacts as INPUTS.  So the bib's grounding DAG becomes the
build DAG: a dependent cannot build unless every premise's witness was produced (the premise was
proven).  build-success = proven — the Agda model, where a proof of B consumes the proof of A as a
term.  This generalizes Ξ·result-imported (a sibling's verdict as a dep) to intra-project rests-on,
and dissolves claims.py: each witness is a node in a composing graph, not a function in a dispatch
script.  (Synthetic proof; the real witness body is the claim's assertion under the toolchain.)
"""

def _witness_impl(ctx):
    w = ctx.actions.declare_file(ctx.label.name + ".witness.json")
    prem = " ".join([p.path for p in ctx.files.premises])
    # The premises are INPUTS: Bazel runs this action only if every premise witness was produced.
    # A premise whose claim does NOT hold emits no artifact → this dependent cannot build (composition).
    guard = ("for p in " + prem + "; do test -f \"$p\" || exit 1; done; ") if prem else ""
    ctx.actions.run_shell(
        outputs = [w],
        inputs = ctx.files.premises + ctx.files.data,
        command = guard + "if " + ctx.attr.holds +
                  "; then echo '{\"claim\":\"" + ctx.label.name + "\",\"witness\":\"holds\"}' > " + w.path +
                  "; else echo 'witness " + ctx.label.name + " does not hold' >&2; exit 1; fi",
        mnemonic = "PkWitness",
        progress_message = "Ζ·compose witness " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([w]))]

pk_witness = rule(
    implementation = _witness_impl,
    doc = "A claim's witness as a build artifact: emitted iff `holds`, consuming `premises`' witnesses (rests-on).",
    attrs = {
        "holds": attr.string(mandatory = True, doc = "the witness body — a shell cmd; exit 0 = the claim holds"),
        "premises": attr.label_list(allow_files = True, doc = "rests-on: the premise claims' witness artifacts"),
        "data": attr.label_list(allow_files = True),
    },
)
