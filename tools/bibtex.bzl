"""Ζ·starlark — the bib IS the build graph (no projected, checked-in BUILD).

A repository rule reads a paperkit project's warrants.bib during the FETCH phase — the one place
Starlark may read a file — and projects each CHECKED claim (@misc entry with a `check` field) into
its SPECIFIC TYPED rule (Ζ·verb): the check's type selects a pk_* rule (tools/verb.bzl) that emits
a verdict RECORD (a build artifact).  pk_gate aggregates the records into the project's verdict
(`gate_rec`), and a thin assert-test (`gate`, Ζ·hook·assert) puts that record into the live gate.
This SUPERSEDES the checked-in BUILD projector AND the old sh_test(gate.py --only) projection:
Bazel reads the bib DIRECTLY (re-fetch on change), and the resolver's per-check dispatch lives in
Starlark, not a general python script.

Each target's `data` is its own project's files + the engine, plus the claim's DECLARED `reads`
(Ζ·foot, declare+audit): a bib field naming the cross-package projects the check touches
(`.` = root files like .githooks, or a sibling project).  A custom check type resolves from the
project's paper.toml [checks.X] cmd template; a `result:<sibling>` check is a real cross-repo dep
on the sibling's gate_rec record (records-as-deps, Ξ·result-imported); a host-coupled project
(setup, `local`) runs its pk_cmd on the host, unsandboxed (Ζ·resist).  adequacy (the Δ sweep) is
still an engine sh_test (discriminate.py) until Ζ·nest.

Starlark has no regex, so the parse is string ops on the regular `@type{key, field = {val}, ...}`
shape: an entry begins only at a LINE-START `@type{key,`; a claim is checkable iff a later field
line's name is `check`.
"""

def _entries(content):
    out = []
    key = None
    check = ""      # the full check value `type:target` ("" = uncheckable claim)
    sib = ""        # for a result:<sibling> check — the sibling it definitionally reads
    reads = []
    for raw in content.splitlines():
        s = raw.strip()
        if s.startswith("@") and "{" in s:
            if key != None:
                out.append((key, check, sib, reads))
            key = s.split("{", 1)[1].split(",", 1)[0].strip()
            check = ""
            sib = ""
            reads = []
        elif key != None and "=" in s:
            name = s.split("=", 1)[0].strip()
            if name == "check":
                check = s.split("{", 1)[1].rsplit("}", 1)[0].strip()
                if check.startswith("result:"):
                    sib = check.split(":", 1)[1].strip()
            elif name == "reads":
                inner = s.split("{", 1)[1].rsplit("}", 1)[0]
                reads = [t.strip() for t in inner.split(",") if t.strip()]
    if key != None:
        out.append((key, check, sib, reads))
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

# Ζ·foot·act — the GENEROUS universe (engine + every project) for a footprint audit: the strace
# must see reads BEYOND a claim's declaration, else an under-declared read is just an absent file.
_ALL_DATA = ('"@@//paperkit:engine", "@@//:files", "@@//boundaries:files", ' +
             '"@@//config:files", "@@//paper:files", "@@//setup:files"')

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

def _verb_rule(name, check, proj, files, reads, custom, local):
    """Dispatch ONE bib check to its specific typed rule (a record), not a general `gate.py --only`
    script.  The check's TYPE selects the rule; python is dropped-to only in pk_cmd (the exit-code
    oracle), under the toolchain.  A custom type expands its [checks.X] cmd template.  `local` marks
    a host-coupled project (setup): pk_cmd runs on the host, unsandboxed (Ζ·resist)."""
    i = check.find(":")
    typ = check[:i]
    target = check[i + 1:]
    dl = ", ".join([_lit(d) for d in _data(reads, files)])
    pj = "" if proj == "." else ", project = " + _lit(proj)
    lc = ", local = True" if local else ""
    if typ == "cmd":
        return "pk_cmd(name = " + _lit(name) + ", cmd = " + _lit(target) + pj + lc + ", data = [" + dl + "])"
    elif typ == "file":
        return "pk_file(name = " + _lit(name) + ", path = " + _lit(target) + ", data = [" + dl + "])"
    elif typ == "result":   # records-as-deps: depend on the sibling's aggregate verdict record
        return "pk_result(name = " + _lit(name) + ', sibling_verdict = "@paperkit_' + target + '//:gate_rec")'
    elif typ == "agree":
        prods = ", ".join([_lit(p.strip()) for p in target.split("|||") if p.strip()])
        return "pk_agree(name = " + _lit(name) + ", producers = [" + prods + "])"
    elif typ in custom:     # a config-declared cmd template — {target} substituted, run as a cmd oracle
        cmd = custom[typ].replace("{target}", target)
        return "pk_cmd(name = " + _lit(name) + ", cmd = " + _lit(cmd) + pj + lc + ", data = [" + dl + "])"
    else:
        fail("Ζ·verb·wire: check type '" + typ + ":' is neither builtin nor a [checks." + typ +
             "] template — claim '" + name + "'")

def _bib_repo_impl(repository_ctx):
    content = repository_ctx.read(repository_ctx.path(repository_ctx.attr.bib))
    proj = repository_ctx.attr.project
    files = "@@//:files" if proj == "." else "@@//%s:files" % proj
    parsed = _entries(content)
    local = repository_ctx.attr.local

    # Custom check types resolve from the project's paper.toml [checks.X] templates (watched, so a
    # template edit re-fetches).
    custom = {}
    tomlp = repository_ctx.path(repository_ctx.attr.bib).dirname.get_child("paper.toml")
    if tomlp.exists:
        repository_ctx.watch(tomlp)
        custom = _custom(repository_ctx.read(tomlp))

    out = ['load("@@//tools:verb.bzl", "pk_agree", "pk_cmd", "pk_file", "pk_gate", "pk_result")']
    syms = []
    if repository_ctx.attr.adequacy:
        syms += ["pk_adequacy", "pk_grade_claim"]
    if not local:                       # Ζ·foot·act — the footprint audit (skips host-coupled projects)
        syms += ["pk_footaudit", "pk_footprint"]
    if syms:
        out.append("load(\"@@//tools:grade.bzl\", " + ", ".join([_lit(s) for s in sorted(syms)]) + ")")
    out.append("")
    recs = []
    for k, check, sib, reads in parsed:
        if not check:
            continue
        out.append(_verb_rule(k, check, proj, files, reads, custom, local))
        recs.append('":%s"' % k)

    # invariants — a structural meta-check over the WHOLE bib (coverage, no-axiom-K); an irreducibly
    # GENERAL oracle, kept as a cmd: drop (Ζ·resist).
    lc = ", local = True" if local else ""
    inv = "python3 paperkit/gate.py --invariants --safe --without-K " + proj
    out.append("pk_cmd(name = \"invariants\", cmd = " + _lit(inv) + lc + ", data = [" + _lit(files) + ', "@@//paperkit:engine"])')
    recs.append('":invariants"')

    # pk_gate aggregates the records → the project verdict; the assert-test puts it in the live gate.
    out.append('pk_gate(name = "gate_rec", checks = [%s], visibility = ["//visibility:public"])' % ", ".join(recs))
    out.append('sh_test(name = "gate", srcs = ["@@//tools:assert_pass.sh"], ' +
               'args = ["$(rootpath :gate_rec)"], data = [":gate_rec"], visibility = ["//visibility:public"])')
    if repository_ctx.attr.adequacy:
        # Ζ·nest — adequacy as a NESTING of per-claim grade records (pk_grade_claim) aggregated by
        # pk_adequacy; the assert-test puts it in //:hook.  (The old discriminate.py sweep sh_test
        # is retired; discriminate.py stays as the per-claim grade ORACLE behind pk_grade_claim.)
        grades = []
        for k, check, sib, reads in parsed:
            if not check:
                continue
            out.append("pk_grade_claim(name = " + _lit(k + "__grade") + ", claim = " + _lit(k) +
                       ", project = " + _lit(proj) + ", data = [" +
                       ", ".join([_lit(d) for d in _data(reads, files)]) + "])")
            grades.append('":%s__grade"' % k)
        out.append('pk_adequacy(name = "adequacy_rec", grades = [%s], visibility = ["//visibility:public"])' % ", ".join(grades))
        out.append('sh_test(name = "adequacy", srcs = ["@@//tools:assert_pass.sh"], ' +
                   'args = ["$(rootpath :adequacy_rec)"], data = [":adequacy_rec"], visibility = ["//visibility:public"])')

    if not local:
        # Ζ·foot·act — the declare+audit cross-check as a NESTING of per-claim footprint records
        # (pk_footprint, footdeps --only) aggregated by pk_footaudit, dissolving footdeps' ThreadPool.
        # Data is GENEROUS (every project) so the strace sees reads BEYOND the declaration.  On-demand
        # (not in //:hook); host-coupled projects (local) skip it — their footprint needs the host.
        foots = []
        for k, check, sib, reads in parsed:
            if not check or sib:        # result: is an edge — no footprint
                continue
            out.append("pk_footprint(name = " + _lit(k + "__foot") + ", claim = " + _lit(k) +
                       ", project = " + _lit(proj) + ", data = [" + _ALL_DATA + "])")
            foots.append('":%s__foot"' % k)
        if foots:
            out.append('pk_footaudit(name = "footaudit", foots = [%s], visibility = ["//visibility:public"])' % ", ".join(foots))
    repository_ctx.file("BUILD.bazel", "\n".join(out) + "\n")

bib_repo = repository_rule(
    implementation = _bib_repo_impl,
    attrs = {
        "bib": attr.label(mandatory = True, allow_single_file = True),
        "project": attr.string(mandatory = True),
        "adequacy": attr.bool(default = False),
        "local": attr.bool(default = False),  # Ζ·resist: host-coupled project (setup) — pk_cmd runs on the host
    },
)

def _bib_ext_impl(module_ctx):
    for mod in module_ctx.modules:
        for tag in mod.tags.project:
            bib_repo(name = tag.name, bib = tag.bib, project = tag.project, adequacy = tag.adequacy, local = tag.local)

bib = module_extension(
    implementation = _bib_ext_impl,
    tag_classes = {
        "project": tag_class(attrs = {
            "name": attr.string(mandatory = True),
            "bib": attr.label(mandatory = True),
            "project": attr.string(mandatory = True),
            "adequacy": attr.bool(default = False),
            "local": attr.bool(default = False),
        }),
    },
)
