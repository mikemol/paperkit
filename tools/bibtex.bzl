"""Ζ·starlark — the bib IS the build graph (no projected, checked-in BUILD).

A repository rule reads a paperkit project's warrants.bib during the FETCH phase — the one place
Starlark may read a file — and projects each CHECKED claim (@misc entry with a `check` field) into
the ONE recursive check target: an sh_test whose command resolves that claim's check (the leaf),
aggregated by a `gate` test_suite (the node), with an optional Δ `adequacy` target.  This
SUPERSEDES the checked-in BUILD projector: Bazel reads the bib DIRECTLY, so a target cannot drift
from its claim — Bazel re-fetches whenever warrants.bib changes.

Each target's `data` is its own project's files + the engine, plus the claim's DECLARED `reads`
(Ζ·foot, declare+audit): a bib field naming the cross-package projects the check touches
(`.` = root files like .githooks, or a sibling project).  Declaration is the cheap, portable
SOURCE; the repo-scoped Φ·footprint AUDITS it on demand (footdeps --audit: footprint ⊆ declared),
so the build graph needs no strace and a check cannot silently under-declare.  The node and the Δ
adequacy target use the UNION of the project's declared reads (the sweep reruns every check).

Starlark has no regex, so the parse is string ops on the regular `@type{key, field = {val}, ...}`
shape: an entry begins only at a LINE-START `@type{key,`; a claim is checkable iff a later field
line's name is `check`; a `result:<sibling>` check is an EDGE (wired by Ζ·hook in //:hook).
"""

def _entries(content):
    out = []
    key = None
    check = ""      # the full check value `type:target` ("" = uncheckable claim)
    sib = ""        # for a result:<sibling> check — the sibling it definitionally reads
    reads = []
    mem = ""        # declared memory (MB) → a Bazel resource reservation (Ζ·membudget)
    for raw in content.splitlines():
        s = raw.strip()
        if s.startswith("@") and "{" in s:
            if key != None:
                out.append((key, check, sib, reads, mem))
            key = s.split("{", 1)[1].split(",", 1)[0].strip()
            check = ""
            sib = ""
            reads = []
            mem = ""
        elif key != None and "=" in s:
            name = s.split("=", 1)[0].strip()
            if name == "check":
                check = s.split("{", 1)[1].rsplit("}", 1)[0].strip()
                if check.startswith("result:"):
                    sib = check.split(":", 1)[1].strip()
            elif name == "reads":
                inner = s.split("{", 1)[1].rsplit("}", 1)[0]
                reads = [t.strip() for t in inner.split(",") if t.strip()]
            elif name == "mem":
                mem = s.split("{", 1)[1].rsplit("}", 1)[0].strip()
    if key != None:
        out.append((key, check, sib, reads, mem))
    return out

def _data(tokens, files):
    """own files + engine (always) + each DECLARED read token → its project's filegroup
    (`.` → the root project's files; a sibling name → that project's files)."""
    out = {files: True, "@@//paperkit:engine": True}
    for t in tokens:
        if t == "paperkit":
            continue
        out["@@//:files" if t == "." else "@@//%s:files" % t] = True
    return sorted(out.keys())

def _lit(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'  # a Starlark string literal

def _custom(content):
    """Parse a project's paper.toml [checks.X] cmd TEMPLATES (a custom verifier type X resolves by
    running its cmd with {target} substituted).  Starlark has no toml parser, so string ops on the
    `[checks.X]` / `cmd = "..."` shape — the same discipline as _entries on the bib."""
    out = {}
    cur = None
    for raw in content.splitlines():
        s = raw.strip()
        if s.startswith("[checks."):
            cur = s[len("[checks."):].split("]")[0].strip()
        elif s.startswith("["):
            cur = None
        elif cur != None and s.startswith("cmd") and "=" in s:
            val = s.split("=", 1)[1].strip()
            if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
                val = val[1:-1]
            out[cur] = val
    return out

def _verb_rule(name, check, proj, files, reads, custom):
    """Ζ·verb·wire — dispatch ONE bib check to its specific typed rule (a record), not a general
    `gate.py --only` script.  The check's TYPE selects the rule; python is dropped-to only in pk_cmd
    (the exit-code oracle), under the toolchain.  A custom type expands its [checks.X] cmd template."""
    i = check.find(":")
    typ = check[:i]
    target = check[i + 1:]
    dl = ", ".join([_lit(d) for d in _data(reads, files)])
    pj = "" if proj == "." else ", project = " + _lit(proj)
    if typ == "cmd":
        return "pk_cmd(name = " + _lit(name) + ", cmd = " + _lit(target) + pj + ", data = [" + dl + "])"
    elif typ == "file":
        return "pk_file(name = " + _lit(name) + ", path = " + _lit(target) + ", data = [" + dl + "])"
    elif typ == "result":   # records-as-deps: depend on the sibling's aggregate verdict record
        return "pk_result(name = " + _lit(name) + ', sibling_verdict = "@paperkit_' + target + '//:gate_rec")'
    elif typ == "agree":
        prods = ", ".join([_lit(p.strip()) for p in target.split("|||") if p.strip()])
        return "pk_agree(name = " + _lit(name) + ", producers = [" + prods + "])"
    elif typ in custom:     # a config-declared cmd template — {target} substituted, run as a cmd oracle
        cmd = custom[typ].replace("{target}", target)
        return "pk_cmd(name = " + _lit(name) + ", cmd = " + _lit(cmd) + pj + ", data = [" + dl + "])"
    else:
        fail("Ζ·verb·wire: check type '" + typ + ":' is neither builtin nor a [checks." + typ +
             "] template — claim '" + name + "'")

def _verb_build(adequacy, proj, files, parsed, custom):
    """The generated BUILD for a verb-wired project: a record per check + pk_gate over the records
    + the Ζ·hook·assert test that puts the aggregate record into the live gate (+ the old adequacy
    sh_test, kept on the engine path until Ζ·nest)."""
    out = ['load("@@//tools:verb.bzl", "pk_agree", "pk_cmd", "pk_file", "pk_gate", "pk_result")', ""]
    recs = []
    for k, check, sib, reads, mem in parsed:
        if not check:
            continue
        out.append(_verb_rule(k, check, proj, files, reads, custom))
        recs.append('":%s"' % k)
    # invariants — a structural meta-check over the WHOLE bib (coverage, no-axiom-K); an
    # irreducibly GENERAL oracle, kept as a cmd: drop for now (Ζ·resist).
    inv = "python3 paperkit/gate.py --invariants --safe --without-K " + proj
    out.append("pk_cmd(name = \"invariants\", cmd = " + _lit(inv) + ", data = [" + _lit(files) + ', "@@//paperkit:engine"])')
    recs.append('":invariants"')
    out.append('pk_gate(name = "gate_rec", checks = [%s], visibility = ["//visibility:public"])' % ", ".join(recs))
    out.append('sh_test(name = "gate", srcs = ["@@//tools:assert_pass.sh"], ' +
               'args = ["$(rootpath :gate_rec)"], data = [":gate_rec"], visibility = ["//visibility:public"])')
    if adequacy:   # Δ sweep — still the engine path (discriminate.py); union of the leaves' reads
        union = {}
        for k, check, sib, reads, mem in parsed:
            if check and not sib:
                for t in reads:
                    union[t] = True
        out.append(_sh_test("adequacy", ["adequacy", proj], _data(union.keys(), files)))
    return "\n".join(out) + "\n"

def _sh_test(name, args, data, mem = ""):
    lines = [
        'sh_test(',
        '    name = "%s",' % name,
        '    srcs = ["@@//tools:run.sh"],',
        '    args = [%s],' % ", ".join(['"%s"' % a for a in args]),
        '    data = [%s],' % ", ".join(['"%s"' % d for d in data]),
        '    size = "large",',
    ]
    if mem:
        # Ζ·membudget: the bib's `mem` (MB) → a Bazel resource reservation; the scheduler bounds
        # concurrent memory to the --local_extra_resources=mem_mb pool (.bazelrc).  No semaphore.
        lines.append('    tags = ["resources:mem_mb:%s"],' % mem)
    lines.append('    visibility = ["//visibility:public"],')
    lines.append(")")
    return "\n".join(lines)

def _bib_repo_impl(repository_ctx):
    content = repository_ctx.read(repository_ctx.path(repository_ctx.attr.bib))
    proj = repository_ctx.attr.project
    files = "@@//:files" if proj == "." else "@@//%s:files" % proj
    parsed = _entries(content)
    if repository_ctx.attr.verb:
        # Ζ·verb·wire — project per-verb RECORD rules + pk_gate over the records (the gate IS a
        # check), instead of one sh_test(gate.py --only) per claim.  resolver.resolves()'s dispatch
        # moves into Starlark; the leaf is typed, not a general script.  Custom check types resolve
        # from the project's paper.toml [checks.X] templates (watched, so a template edit re-fetches).
        custom = {}
        tomlp = repository_ctx.path(repository_ctx.attr.bib).dirname.get_child("paper.toml")
        if tomlp.exists:
            repository_ctx.watch(tomlp)
            custom = _custom(repository_ctx.read(tomlp))
        repository_ctx.file("BUILD.bazel", _verb_build(repository_ctx.attr.adequacy, proj, files, parsed, custom))
        return
    checked = [(k, reads, mem) for k, c, sib, reads, mem in parsed if c and not sib]   # LEAVES
    edges = [k for k, c, sib, reads, mem in parsed if c and sib]                       # result: EDGES
    out = ["# Generated by Ζ·starlark from %s — recursive check; data = own + engine + declared reads.\n" %
           str(repository_ctx.attr.bib)]
    if edges:
        out.append("# result: edges (claim → sibling gate), wired in //:hook by Ζ·hook: %s\n" % ", ".join(edges))
    # adequacy grades every checked claim; result: claims grade "imported" by DELEGATION
    # (Ξ·result-imported) without running the sibling, so they pull in NO deps — the union is just
    # the declared reads across the leaves.
    union = {}
    for k, reads, mem in checked:
        for t in reads:
            union[t] = True
    for k, reads, mem in checked:
        out.append(_sh_test(k, ["check", proj, k], _data(reads, files), mem))
    out.append(_sh_test("invariants", ["invariants", proj], [files, "@@//paperkit:engine"]))   # NODE
    tests = ['":%s"' % k for k, _, _ in checked] + ['":invariants"']
    out.append('test_suite(name = "gate", tests = [%s], visibility = ["//visibility:public"])' % ", ".join(tests))
    if repository_ctx.attr.adequacy:                              # Δ sweep reruns every check → UNION of reads
        out.append(_sh_test("adequacy", ["adequacy", proj], _data(union.keys(), files)))
    repository_ctx.file("BUILD.bazel", "\n".join(out) + "\n")

bib_repo = repository_rule(
    implementation = _bib_repo_impl,
    attrs = {
        "bib": attr.label(mandatory = True, allow_single_file = True),
        "project": attr.string(mandatory = True),
        "adequacy": attr.bool(default = False),
        "verb": attr.bool(default = False),   # Ζ·verb·wire: per-verb record rules (migrating project-by-project)
    },
)

def _bib_ext_impl(module_ctx):
    for mod in module_ctx.modules:
        for tag in mod.tags.project:
            bib_repo(name = tag.name, bib = tag.bib, project = tag.project, adequacy = tag.adequacy, verb = tag.verb)

bib = module_extension(
    implementation = _bib_ext_impl,
    tag_classes = {
        "project": tag_class(attrs = {
            "name": attr.string(mandatory = True),
            "bib": attr.label(mandatory = True),
            "project": attr.string(mandatory = True),
            "adequacy": attr.bool(default = False),
            "verb": attr.bool(default = False),
        }),
    },
)
