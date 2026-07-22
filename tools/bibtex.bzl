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
project's paper.toml [checks.X] cmd template; the two BOUNDARY-CROSSING verbs are real cross-repo
deps on the owner's record (records-as-deps): `result:<sibling>` on its gate_rec (Ξ·result-imported),
and `concept:<key>` on the library's per-concept verdict + `__dcalc` certificate (Λ·witness — it
reuses pk_result, since importing a certificate IS reading a sibling's record); a host-coupled project
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
    rests = []      # rests-on: the premise claims this one is grounded on (Ζ·compose deps)
    for raw in content.splitlines():
        s = raw.strip()
        if s.startswith("@") and "{" in s:
            if key != None:
                out.append((key, check, sib, reads, rests))
            key = s.split("{", 1)[1].split(",", 1)[0].strip()
            check = ""
            sib = ""
            reads = []
            rests = []
        elif key != None and "=" in s:
            name = s.split("=", 1)[0].strip()
            if name == "check":
                check = s.split("{", 1)[1].rsplit("}", 1)[0].strip()
                if check.startswith("result:"):
                    sib = check.split(":", 1)[1].strip()
            elif name == "reads":
                inner = s.split("{", 1)[1].rsplit("}", 1)[0]
                reads = [t.strip() for t in inner.split(",") if t.strip()]
            elif name == "rests-on" and "{" in s and "}" in s:
                inner = s.split("{", 1)[1].rsplit("}", 1)[0]
                rests = [t.strip() for t in inner.split(",") if t.strip()]
    if key != None:
        out.append((key, check, sib, reads, rests))
    return out

def _data(tokens, files, imports = [], engine = True):
    """own files + engine (always) + the IMPORTED concept-bib packages' files (a view composes bibs
    from other packages, and the runtime engine re-reads them when it gates/grades) + each DECLARED
    read token → its project's filegroup (`.` → the root project's files; a sibling → its files)."""
    out = {files: True}
    if engine:
        out["@@//paperkit:engine"] = True
    for i in imports:
        out[i] = True
    for t in tokens:
        if t == "paperkit":
            # Μ·kernel·fixture·unstage — a DECLARED engine read: a witness that runs a sibling
            # GATE (boundaries-project) genuinely reads the whole engine tree, and says so here;
            # with engine=False (the eval cells) this declaration is what stages it.
            out["@@//paperkit:engine"] = True
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

def _warrants(content):
    """The project's WARRANTS LIST from paper.toml ([paper] warrants = ["a.bib", "b.bib"]).  Starlark
    has no toml parser, so string ops on the single-line array shape (the same discipline as _custom).
    Empty ⇒ [] ⇒ caller falls back to the anchor bib's basename (a single-bib project is unchanged)."""
    for raw in content.splitlines():
        s = raw.strip()
        if s.startswith("warrants") and "=" in s and "[" in s and "]" in s:
            inner = s[s.find("[") + 1:s.rfind("]")]
            out = []
            for part in inner.split(","):
                p = part.strip()
                if len(p) >= 2 and p[0] == '"' and p[-1] == '"':
                    out.append(p[1:-1])
            return out
    return []

def _body(check, custom):
    """The witness BODY — the shell command behind a cmd:/custom check (exit 0 = the claim holds).
    Only cmd:/custom have one; the other resolver.VERBS entries (file:/result:/agree:/concept:) are
    handled by the verb gate, not the proof DAG yet — each resolves through machinery, not a shell line."""
    i = check.find(":")
    typ, target = check[:i], check[i + 1:]
    if typ == "cmd":
        return target
    if typ in custom:
        return custom[typ].replace("{target}", target)
    return None

def _verb_rule(name, check, proj, files, reads, custom, local, imports = []):
    """Dispatch ONE bib check to its specific typed rule (a record), not a general `gate.py --only`
    script.  The check's TYPE selects the rule; python is dropped-to only in pk_cmd (the exit-code
    oracle), under the toolchain.  A custom type expands its [checks.X] cmd template.  `local` marks
    a host-coupled project (setup): pk_cmd runs on the host, unsandboxed (Ζ·resist)."""
    i = check.find(":")
    typ = check[:i]
    target = check[i + 1:]
    dl = ", ".join([_lit(d) for d in _data(reads, files, imports)])
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

def _membucket(mem, claim, res):
    """Τ·mem ladder (= the Ω·config resolution ladder): a claim's reservation is the most-specific
    learned entry — per-claim override > per-resolution default > 0 (calc.bzl's cold-start floor)."""
    return mem.get("claims", {}).get(claim, mem.get(res, 0))

def _sitename(m, q):
    """A unique, valid target-name fragment for a perturbation site (module, spec): stem__spec with
    the mutate.py spec flattened to an identifier — a def-drop qualname's dots, and an import op's
    `+`/`-`/`:` (import+:gate → import_add__gate) — so every op has a distinct, valid target name."""
    spec = q.replace(".", "_").replace("+", "_add_").replace("-", "_drop_").replace(":", "_")
    return m[len("paperkit/"):-len(".py")].replace("/", "_") + "__" + spec

def _filesitename(spec):
    """A valid target-name fragment for a FILE toggle site (file+:/file-:<path>): the spec flattened
    to an identifier (file+:paperkit/cli.py → file_add_paperkit_cli_py).  No module stem — a file cell
    perturbs a path in the sandbox, not an engine module."""
    return spec.replace(".", "_").replace("+", "_add_").replace("-", "_drop_").replace(":", "_").replace("/", "_")

# ·gen·surface — the def-mutable SURFACE is a property of the ENGINE, not any project.  It is
# enumerated ONCE in the module extension (engine-side, below) and passed to each emerge bib_repo;
# NOT per-project (a check that non-emerge "skips it" would be the tell of a misplaced engine
# property).  The core modules are DERIVED from //paperkit:engine's declaration (ENGINE_SRCS — the
# single source, no glob), minus the boundary suites no check imports.
_BOUNDARY = "tests/boundaries_"

def _core_from_engine(components_text):
    # Μ·kernel·bounds — the engine file list's ONE owner is paperkit/components.bzl (BUILD.bazel
    # derives ENGINE_SRCS from the same literal).  Every quoted *.py token in it is a partition
    # member (component names carry no ".py"; comments are never a lone quoted filename), so the
    # core is the sorted union minus the boundary suites no check imports.
    srcs = [t for t in components_text.split('"') if t.endswith(".py") and "\n" not in t and " " not in t]
    return sorted(["paperkit/" + s for s in srcs if not s.startswith(_BOUNDARY)])

def _core(module_ctx):
    """The core engine module .py paths (the component partition minus boundary suites), watched so
    an add/remove re-generates.  The SHARED input of ·gen·surface (def-sites) and ·gen·closure
    (witness closures) — both project the same engine AST (def_sites.py / closure.py beside
    imports.py)."""
    module_ctx.watch(module_ctx.path(Label("@@//paperkit:components.bzl")))
    core = _core_from_engine(module_ctx.read(module_ctx.path(Label("@@//paperkit:components.bzl"))))
    for m in core:
        module_ctx.watch(module_ctx.path(Label("@@//paperkit:" + m[len("paperkit/"):])))
    return core

def _host_py(module_ctx, who):
    py = module_ctx.which("python3")
    if not py:
        fail(who + ": python3 not on PATH")
    return py

def _surface(module_ctx, core):
    """·gen·surface — enumerate the engine PERTURBATION surface ONCE via sites.py over the core modules
    (host-python AST — build-graph metadata like the bib parse, NOT check execution, so the
    hermetic-python principle holds).  Returns ["module\tspec", ...] where spec is a mutate.py mutation:
    a def-drop (bare qualname) or an import+ inject (Ζ·mutant·struct — toggle presence, both polarities)."""
    py = _host_py(module_ctx, "·gen·surface")
    ds = module_ctx.path(Label("@@//tools:sites.py"))
    # WATCH the generator + its imports, so editing the enumerator regenerates the surface (else the
    # extension serves a STALE result — the tool is an INPUT like the core modules, [[bazel-action-idempotency]]).
    for t in ("sites.py", "def_sites.py", "imports.py"):
        module_ctx.watch(module_ctx.path(Label("@@//tools:" + t)))
    root = str(module_ctx.path(Label("@@//:MODULE.bazel")).dirname)
    res = module_ctx.execute([str(py), str(ds)] + core, working_directory = root)
    if res.return_code != 0:
        fail("·gen·surface: sites.py failed (%d): %s" % (res.return_code, res.stderr))
    return [l for l in res.stdout.splitlines() if "\t" in l]

def _claim_script(module_ctx, project):
    """The claim-WITNESS module a project's `claim:` type runs — the .py in its paper.toml
    [checks.claim] cmd (paper → checks/claims.py, root → checks/readme.py; NOT hardcoded — the second
    consumer, root's readme.py, proved the assumption).  None if the project declares no claim: type."""
    lbl = "@@//:paper.toml" if project == "." else "@@//" + project + ":paper.toml"
    p = module_ctx.path(Label(lbl))
    if not p.exists:
        return None
    text = module_ctx.read(p)
    module_ctx.watch(p)
    i = text.find("[checks.claim]")
    if i < 0:
        return None
    j = text.find("cmd", i)                      # the cmd = "python3 <script> {target}" line
    line = text[j:text.find("\n", j)]
    for tok in line.split(" "):
        t = tok.strip('"').strip("'")
        if t.endswith(".py"):
            return t  # relative to the project dir, e.g. checks/claims.py
    return None

def _closures(module_ctx, project, core):
    """Ξ·dag·eval — per emerge project, each claim WITNESS's closure ROOTS via closure.py over the
    project's claim-witness module (paper.toml [checks.claim]) + the engine fixture + the core names.
    Returns ["claim\tmodule", ...]; [] if the project declares no claim: type.  Unlike the def-site
    SURFACE (engine-global), a witness's closure depends on the PROJECT's check module — so this runs
    per emerge project, watching that module so an edited witness re-generates its cells' closures."""
    script = _claim_script(module_ctx, project)
    if not script:
        return []
    lbl = "@@//:" + script if project == "." else "@@//" + project + ":" + script
    check = module_ctx.path(Label(lbl))
    if not check.exists:
        return []
    module_ctx.watch(check)
    fixture = module_ctx.path(Label("@@//paperkit:tests/_fixture.py"))
    py = _host_py(module_ctx, "·gen·closure")
    cl = module_ctx.path(Label("@@//tools:closure.py"))
    # WATCH the enumerator + the fixture it reads (the fx CLI map), so editing either regenerates the
    # closures (the tool is an INPUT, [[bazel-action-idempotency]] — else a stale closure output).
    module_ctx.watch(cl)
    module_ctx.watch(fixture)
    root = str(module_ctx.path(Label("@@//:MODULE.bazel")).dirname)
    # --relpath — the check's REPO-RELATIVE path (paper/checks/claims.py, checks/readme.py), so
    # closure.py resolves Path(__file__).parents[N] to the SANDBOX prefix a file toggle must hit.
    relpath = script if project == "." else project + "/" + script
    res = module_ctx.execute([str(py), str(cl), "--check", str(check), "--fixture", str(fixture), "--relpath", relpath] + core, working_directory = root)
    if res.return_code != 0:
        fail("·gen·closure: closure.py failed (%d): %s" % (res.return_code, res.stderr))
    return [l for l in res.stdout.splitlines() if "\t" in l]

def _bib_repo_impl(repository_ctx):
    bibp = repository_ctx.path(repository_ctx.attr.bib)
    proj = repository_ctx.attr.project
    files = "@@//:files" if proj == "." else "@@//%s:files" % proj
    local = repository_ctx.attr.local

    # Custom check types AND the project's WARRANTS LIST both come from paper.toml (watched, so an
    # edit re-fetches).  Multi-bib composition is the same thing project.py does over `warrants`
    # (bib.load_config), lifted to the generator so a project's claims may be authored across modules
    # (the concept-library reconstitution).  The `bib` attr is the ANCHOR that locates the project dir;
    # a single-bib project (empty/1-element list) is byte-for-byte unchanged.  Check-less claims (bib
    # references) contribute no target — every parsed loop below skips `if not check`.
    custom = {}
    warrants = []
    tomlp = bibp.dirname.get_child("paper.toml")
    if tomlp.exists:
        repository_ctx.watch(tomlp)
        toml = repository_ctx.read(tomlp)
        custom = _custom(toml)
        warrants = _warrants(toml)
    if not warrants:
        warrants = [bibp.basename]
    # Ζ·import·stage — the IMPORTED concept-bib packages (label tokens in warrants): their :files must
    # be staged in this project's runtime actions, because the engine RE-READS the composed bibs when
    # it gates/grades (the fetch-time compose in the loop below alone leaves them out of the sandbox).
    imports = {}
    for w in warrants:
        if w.startswith("//") and ":" in w:
            pkg = w[2:].split(":", 1)[0]
            imports["@@//:files" if pkg == "" else "@@//%s:files" % pkg] = True
    imports = [k for k in sorted(imports) if k != files]
    parsed = []
    for w in warrants:
        # A bare basename is a LOCAL sibling of the anchor (get_child, one segment).  A LABEL token
        # (//pkg:file, //:path/file, @repo//…) is a bib IMPORTED from another package — the composing
        # project (a VIEW) pulling a claim authored in the concept library.  get_child cannot express a
        # `..` or multi-segment path; path(Label(...)) can (already the idiom at the anchor read + the
        # module extension).  A POSIX basename never contains ':', so the discriminator is safe and
        # every existing basename token stays on the unchanged get_child branch.
        wp = repository_ctx.path(Label(w)) if (":" in w or w.startswith("@")) else bibp.dirname.get_child(w)
        repository_ctx.watch(wp)
        parsed = parsed + _entries(repository_ctx.read(wp))

    # Τ·mem·learn — the per-project learned reservation manifest (a projection of observed peaks,
    # mem.json beside the bib; regenerated on-demand by //:mem-learn).  Resolved per claim down the
    # (claim > resolution > cold-start) ladder when emitting each pk_calc.  Absent ⇒ {} ⇒ every
    # claim falls through to calc.bzl's cold-start floor (mem = 0).
    mem = {}
    memp = repository_ctx.path(repository_ctx.attr.bib).dirname.get_child("mem.json")
    if memp.exists:
        repository_ctx.watch(memp)
        mem = json.decode(repository_ctx.read(memp))

    out = ['load("@@//tools:verb.bzl", "pk_agree", "pk_cmd", "pk_file", "pk_gate", "pk_result")']
    syms = []
    if repository_ctx.attr.adequacy:
        syms += ["pk_adequacy", "pk_grade_claim"]
    if not local:                       # Ζ·foot·act — the footprint audit (skips host-coupled projects)
        syms += ["pk_footaudit", "pk_footprint"]
    if syms:
        out.append("load(\"@@//tools:grade.bzl\", " + ", ".join([_lit(s) for s in sorted(syms)]) + ")")
    if repository_ctx.attr.compose:
        out.append('load("@@//tools:witness.bzl", "pk_proof", "pk_witness")')
    calc = repository_ctx.attr.calc
    emerge = repository_ctx.attr.emerge
    # ·gen·surface — the def-mutable surface, enumerated ONCE engine-side and passed in (emerge repos
    # get it; non-emerge get [] because they build no grid — the surface is not conditional on them).
    sites = [l.split("\t") for l in repository_ctx.attr.sites]
    closures = {}  # ·gen·closure — claim key → its witness's closure ROOT modules (Ξ·dag·eval)
    fsites = {}    # Ζ·mutant·struct·node-kinds — claim key → its FILE toggle specs (file+:/file-:<path>)
    contents = {}  # Ζ·mutant·struct·node-kinds — claim key → [(op, path, substring)] CONTENT toggles
    for l in repository_ctx.attr.closures:
        parts = l.split("\t")
        k = parts[0]
        if len(parts) == 4 and parts[1] in ("content-", "content+"):
            contents.setdefault(k, []).append((parts[1], parts[2], parts[3]))
        elif parts[1].startswith("file+:") or parts[1].startswith("file-:"):
            fsites.setdefault(k, []).append(parts[1])
        else:
            closures.setdefault(k, []).append(parts[1])
    # the claim-WITNESS script each pk_eval runs, EXEC-relative — the .py in THIS project's
    # [checks.claim] cmd (paper → paper/checks/claims.py, root → checks/readme.py), project-prefixed.
    # NOT hardcoded: root's readme.py is a different module than paper's claims.py, so a hardcoded
    # paper/checks/claims.py ran the wrong script for every root cell → every root ∅ flipped (garbage).
    wscript = ""
    for tok in custom.get("claim", "").split(" "):
        if tok.endswith(".py"):
            wscript = tok if proj == "." else proj + "/" + tok
            break
    if emerge:
        out.append("# ·gen·surface: %d core engine def-sites (enumerated once, engine-side)" % len(sites))
    if calc:
        csyms = ["pk_calc", "pk_grade", "pk_mem_learn", "pk_verdict"]
        if emerge:
            csyms += ["pk_cohere", "pk_mutate", "pk_pyc", "pk_eval", "pk_sens"]
        out.append('load("@@//tools:calc.bzl", ' + ", ".join([_lit(s) for s in csyms]) + ")")
    out.append("")
    if emerge:
        # Ζ·mutant·wire·gen·emit — the def-sweep GRID's shared PREP (once, claim-independent): per
        # def-site D, pk_mutate(D)→pk_pyc(D) = D's mutated bytecode, reused by every claim's cell; plus
        # the ∅ identity mutant = the baseline point.  Compile-once (Ζ·pyc·engine); shared across claims.
        for m, q in sites:
            sn = _sitename(m, q)
            out.append('pk_mutate(name = "mut_%s", module = %s, site = %s, data = ["@@//paperkit:engine"])' % (sn, _lit(m), _lit(q)))
            out.append('pk_pyc(name = "pyc_%s", src = ":mut_%s")' % (sn, sn))
        out.append('pk_mutate(name = "mut_0", module = "paperkit/bib.py", site = "", data = ["@@//paperkit:engine"])')
        out.append('pk_pyc(name = "pyc_0", src = ":mut_0")')
    recs = []
    calc_claims = {}
    imported_cert = {}   # Λ·witness — k → the owner library's __dcalc cert label (a concept: import edge)
    owns = repository_ctx.attr.owns_concepts
    vis = ', visibility = ["//visibility:public"]'  # the owner EXPORTS per-concept records for views to import
    for k, check, sib, reads, rests in parsed:
        if not check:
            continue
        if check.startswith("concept:"):
            # Λ·witness — a concept: check IMPORTS a concept authored + GRADED once in the library.  The
            # VERDICT is the library's per-concept verdict record (pk_result, records-as-deps, like
            # result:); the GRADE + :cohere read the library's def-sweep certificate (__dcalc = verdict +
            # engine fingerprint), so the PROOF travels WITH the import — the view neither re-sweeps
            # (Λ·grid's cost) nor drops the fingerprint (naive-delegate's :cohere break).
            key = check[len("concept:"):]
            out.append("pk_result(name = " + _lit(k) + ', sibling_verdict = "@paperkit_library//:' + key + '")')
            imported_cert[k] = "@paperkit_library//:" + key + "__dcalc"
            recs.append('":%s"' % k)
            continue
        if calc and _body(check, custom) != None:
            # Ζ·calc·interp — ONE cached sweep (pk_calc) feeds the verdict reading here (and the grade
            # reading below); the redundant verdict run + the adequacy re-sweep collapse into it.
            dl = ", ".join([_lit(d) for d in _data(reads, files, imports)])
            out.append("pk_calc(name = " + _lit(k + "__calc") + ", claim = " + _lit(k) +
                       ", project = " + _lit(proj) + ", mem = " + str(_membucket(mem, k, "file")) +
                       ", data = [" + dl + "])")
            out.append("pk_verdict(name = " + _lit(k) + ", calc = " + _lit(":" + k + "__calc") + (vis if owns else "") + ")")
            calc_claims[k] = True
            if emerge and closures.get(k):
                # Ζ·mutant·wire·gen·emit — a WITNESS claim's ROW of the grid: one pk_eval CELL per
                # def-site (the check run off its CLOSURE with D's bytecode swapped — parallel + cached,
                # Ξ·dag·eval), the ∅-baseline cell, and pk_sens reading them → {claim, baseline, sens}
                # (a drop-in for the old pk_calc __dcalc pk_cohere consumes).  The fanout IS the build
                # graph — each cell a node — lifted from grader.sensitivity's in-process group-testing.
                # ·surface·scope — a claim's PERTURBATION SURFACE is the mutations over its CLOSURE, not
                # the engine globally: a site in a module the witness never touches (m ∉ closure) swaps a
                # .pyc the check never loads, so its cell is a NO-OP == baseline BY CONSTRUCTION — pure
                # grid waste.  Scoping the row to closure sites drops exactly those no-ops (sens is
                # UNCHANGED: every module whose mutation could flip the check is imported/read by it, so
                # it is in the closure).  This is the common structure of ·surface·scope AND file/bib node
                # kinds: the surface is per-claim-READS, so a claim reading a file / bib-edge perturbs
                # THAT artifact (a later rung, closure roots beyond .py) — through this same scoped row.
                cset = {m: True for m in closures[k]}
                csites = [s for s in sites if s[0] in cset]
                cl = ", ".join(['"@@//paperkit:%s"' % m[len("paperkit/"):-len(".py")] for m in closures[k]])
                # stage the claim's DECLARED reads (dl = _data(reads, files)), not just the project
                # files — a witness may read cross-project inputs (local-ci reads .githooks/pre-commit,
                # multi-project/report-live read siblings); the old pk_calc staged dl, so the grid ∅
                # must too, else the unmutated check errors and the baseline flips (garbage sens).
                # Μ·kernel·fixture·unstage — but NOT the flat engine: the cell's CLOSURE (PycInfo
                # cones, .py + .pyc) already stages every engine module the check can load, so
                # "@@//paperkit:engine" here made every engine edit invalidate every cell (the
                # measured 25.8k storm) while buying nothing.  Dropping it is what makes a module
                # edit invalidate only the cells whose closure contains it.  An under-staged dynamic
                # load fails LOUD: the unmutated check errors, the ∅-baseline flips, pk_sens refuses.
                # …except a result:-checked row, which runs a whole SIBLING GATE in the cell — the
                # sibling's checks (bnd-components' partition-totality among them) legitimately read
                # the full engine tree, so its row keeps the flat staging.
                edl = ", ".join([_lit(d) for d in _data(reads, files, imports, engine = False)])
                ev = ("check = " + _lit(wscript) + ", closure = [" + cl + "], project = [" +
                      (dl if check.startswith("result:") else edl) + "]")
                cellnames = []
                for m, q in csites:
                    sn = _sitename(m, q)
                    out.append('pk_eval(name = "%s__%s", claim = %s, site = %s, module = %s, mutated_py = ":mut_%s", mutated_pyc = ":pyc_%s", %s)' % (
                        k, sn, _lit(k), _lit(m + "::" + q), _lit(m), sn, sn, ev))
                    cellnames.append(sn)
                # Ζ·mutant·struct·node-kinds — the claim's FILE toggle cells (file+ inject / file- drop),
                # per its witness's .exists() edges.  A file cell mutates no module: it passes no
                # module/mutant (eval.py branches on the file+/file- site prefix), only the site + the
                # same check/closure/project (ev).  The file analog of the import+/- cells, so it folds
                # into the SAME pk_sens — sens now spans both artifact kinds (module defs/imports AND
                # file existence).  This makes rm-next (a "cli.py does not exist" negative) BEHAVIORALLY
                # falsifiable at the grid: file+ injects cli.py → the assertion flips.
                for spec in fsites.get(k, []):
                    fn = _filesitename(spec)
                    out.append('pk_eval(name = "%s__%s", claim = %s, site = %s, %s)' % (k, fn, _lit(k), _lit(spec), ev))
                    cellnames.append(fn)
                # CONTENT cells (Ζ·mutant·struct·node-kinds, BIB/content) — one per (op, path, substring)
                # DAG-edge toggle.  Indexed target name (the substring is not a valid identifier); the
                # readable site LABEL carries op:path:substring for the record.  The substring rides the
                # content_text attr (→ ctx.actions.write in pk_eval), never a shell arg.
                for i in range(len(contents.get(k, []))):
                    op, path, sub = contents[k][i]
                    cn = "content_%d" % i
                    out.append('pk_eval(name = "%s__%s", claim = %s, site = %s, content_path = %s, content_text = %s, %s)' % (
                        k, cn, _lit(k), _lit(op + ":" + path + ":" + sub), _lit(path), _lit(sub), ev))
                    cellnames.append(cn)
                out.append('pk_eval(name = "%s__0", claim = %s, site = "0", module = "paperkit/bib.py", mutated_py = ":mut_0", mutated_pyc = ":pyc_0", %s)' % (k, _lit(k), ev))
                out.append('pk_sens(name = "%s__dcalc", evals = [%s], baseline = ":%s__0")' % (k, ", ".join(['":%s__%s"' % (k, c) for c in cellnames]), k))
            elif emerge:
                # A calc claim with NO engine witness (a cmd:/result: check — e.g. a grep over a static
                # asset).  It has no closure (closure.py enumerates only the witness module's CLAIMS), so
                # no grid; its engine sensitivity is empty BY CONSTRUCTION.  The in-process def-sweep
                # (pk_calc resolution=def) computes exactly that {claim, baseline, sens:∅}, so pk_cohere
                # consumes a __dcalc for EVERY emerge calc claim uniformly (the grid just optimizes the
                # witness subset — a projection, not a special case).
                out.append("pk_calc(name = " + _lit(k + "__dcalc") + ", claim = " + _lit(k) +
                           ", project = " + _lit(proj) + ', resolution = "def", mem = ' +
                           str(_membucket(mem, k, "def")) + ", data = [" + dl + "]" + (vis if owns else "") + ")")
        else:
            out.append(_verb_rule(k, check, proj, files, reads, custom, local, imports))
        recs.append('":%s"' % k)

    if calc_claims:
        # Τ·mem·learn — the regen target: aggregate every calc's observed peak → mem.json (the
        # committed projection consumed by the ladder above).  On-demand: build under
        # --config=memobserve in a clean output base, then copy bazel-bin .../mem.json to the source
        # mem.json beside this bib (NOT hook-gated — the observe is too costly and a stale manifest
        # is a benign perf hint).  Aggregates the file-calcs' peaks; the def-sweep is now a grid of
        # pk_eval cells (Ζ·mutant·wire·gen), not a pk_calc with a peak output group, so it is not here.
        ml = [":" + k + "__calc" for k in calc_claims]
        out.append('pk_mem_learn(name = "mem_learn", calcs = [' +
                   ", ".join([_lit(t) for t in ml]) + '], visibility = ["//visibility:public"])')

    if emerge and (calc_claims or imported_cert):
        # Ζ·emerge·gate — the ∂² coherence faces (grounding/emergence) as a CHEAP READING over the
        # def-calcs (coherence --from-calcs): grounding soundness gated with no re-sweep.  The
        # def-sweep is the cost (in //:hook by the owner's call); the reading itself is ~0.1s.
        # Λ·witness — an imported concept: contributes the LIBRARY's def-cert (its real engine
        # fingerprint), so the view's ∂² reading sees the concept's grounding, not an empty node.
        cc = ", ".join([_lit(":" + k + "__dcalc") for k in calc_claims] +
                       [_lit(imported_cert[k]) for k in imported_cert])
        out.append('pk_cohere(name = "cohere_rec", project = ' + _lit(proj) + ", calcs = [" + cc +
                   '], data = ["@@//paperkit:engine", ' + _lit(files) + "".join([", " + _lit(i) for i in imports]) + "])")
        out.append('sh_test(name = "cohere", srcs = ["@@//tools:assert_pass.sh"], ' +
                   'args = ["$(rootpath :cohere_rec)"], data = [":cohere_rec"], size = "small", ' +
                   'visibility = ["//visibility:public"])')

    # invariants — a structural meta-check over the WHOLE bib (coverage, no-axiom-K); an irreducibly
    # GENERAL oracle, kept as a cmd: drop (Ζ·resist).
    lc = ", local = True" if local else ""
    inv = "\"$(command -v python3)\" paperkit/gate.py --invariants --safe --without-K " + proj
    out.append("pk_cmd(name = \"invariants\", cmd = " + _lit(inv) + lc + ", data = [" + _lit(files) + "".join([", " + _lit(i) for i in imports]) + ', "@@//paperkit:engine"])')
    recs.append('":invariants"')

    # pk_gate aggregates the records → the project verdict; the assert-test puts it in the live gate.
    out.append('pk_gate(name = "gate_rec", checks = [%s], visibility = ["//visibility:public"])' % ", ".join(recs))
    out.append('sh_test(name = "gate", srcs = ["@@//tools:assert_pass.sh"], ' +
               'args = ["$(rootpath :gate_rec)"], data = [":gate_rec"], size = "small", ' +
               'visibility = ["//visibility:public"])')
    if repository_ctx.attr.adequacy:
        # Ζ·nest — adequacy as a NESTING of per-claim grade records (pk_grade_claim) aggregated by
        # pk_adequacy; the assert-test puts it in //:hook.  (The old discriminate.py sweep sh_test
        # is retired; discriminate.py stays as the per-claim grade ORACLE behind pk_grade_claim.)
        grades = []
        for k, check, sib, reads, rests in parsed:
            if not check:
                continue
            if k in imported_cert:
                # Λ·witness — grade = the IMPORTED library certificate, read via read_grade → behavioral
                # WITH the owner's engine fingerprint (tests), so it passes adequacy (behavioral ≥ floor)
                # AND the same cert feeds the view's :cohere.  No local re-sweep, no dropped fingerprint.
                out.append("pk_grade(name = " + _lit(k + "__grade") + ", calc = " + _lit(imported_cert[k]) +
                           ', data = ["@@//paperkit:engine", "@@//tools:read_grade.py"])')
            elif k in calc_claims:
                # Ζ·pyc·run·collapse — the grade is a READING of the GRID (the __dcalc pk_sens record),
                # not the file-resolution k__calc crutch: for a WITNESS claim (closures.get(k)) the grid
                # IS the calculation — grade = _grade_from_sens over its measured sens.  This makes the
                # grid GATE-RELEVANT (adequacy reads it), so a surface bug that forces a false ∅ (the
                # ·surface·scope roots-vs-cone regression) now FAILS adequacy instead of hiding behind
                # file-res ([[witness-the-live-path]]).  A NON-witness calc claim (a cmd: grep, no engine
                # closure) has only the def-fallback __dcalc (sens ∅ by construction) — grading it off
                # that would demote it to indeterminate, so it stays on k__calc until its content surface
                # is wired (the last gap before k__calc fully retires).
                gcalc = ":" + k + ("__dcalc" if closures.get(k) else "__calc")
                out.append("pk_grade(name = " + _lit(k + "__grade") + ", calc = " + _lit(gcalc) +
                           ', data = ["@@//paperkit:engine", "@@//tools:read_grade.py"])')
            else:
                out.append("pk_grade_claim(name = " + _lit(k + "__grade") + ", claim = " + _lit(k) +
                           ", project = " + _lit(proj) + ", data = [" +
                           ", ".join([_lit(d) for d in _data(reads, files, imports)]) + "])")
            grades.append('":%s__grade"' % k)
        out.append('pk_adequacy(name = "adequacy_rec", grades = [%s], visibility = ["//visibility:public"])' % ", ".join(grades))
        out.append('sh_test(name = "adequacy", srcs = ["@@//tools:assert_pass.sh"], ' +
                   'args = ["$(rootpath :adequacy_rec)"], data = [":adequacy_rec"], size = "small", ' +
                   'visibility = ["//visibility:public"])')

    if not local:
        # Ζ·foot·act — the declare+audit cross-check as a NESTING of per-claim footprint records
        # (pk_footprint, footdeps --only) aggregated by pk_footaudit, dissolving footdeps' ThreadPool.
        # Data is GENEROUS (every project) so the strace sees reads BEYOND the declaration.  On-demand
        # (not in //:hook); host-coupled projects (local) skip it — their footprint needs the host.
        foots = []
        for k, check, sib, reads, rests in parsed:
            if not check or sib or check.startswith("concept:"):  # result:/concept: are import edges — no local footprint
                continue
            out.append("pk_footprint(name = " + _lit(k + "__foot") + ", claim = " + _lit(k) +
                       ", project = " + _lit(proj) + ", data = [" + _ALL_DATA + "])")
            foots.append('":%s__foot"' % k)
        if foots:
            out.append('pk_footaudit(name = "footaudit", foots = [%s], visibility = ["//visibility:public"])' % ", ".join(foots))

    if repository_ctx.attr.compose:
        # Ζ·compose — each claim's WITNESS as a build artifact; rests-on as build DEPS (the grounding
        # DAG IS the build DAG).  `bazel build //<proj>:proof` builds every witness — build-success =
        # proven, and an unproven premise blocks every claim resting on it.  On-demand (not //:hook yet).
        checked = {k: True for k, check, sib, reads, rests in parsed if check}
        wits = []
        pj = "" if proj == "." else ", project = " + _lit(proj)
        for k, check, sib, reads, rests in parsed:
            if not check:
                continue
            prem = ['":%s__witness"' % r for r in rests if r in checked]
            if sib:
                # result: — importing another paper's results is just depending on it as a LIBRARY:
                # a premise dep on the sibling's :proof (built iff the sibling is proven).  No pk_result.
                prem.append('"@paperkit_%s//:proof"' % sib)
                body = "true"
            else:
                body = _body(check, custom)
                if body == None:             # file:/agree: — not a single-command witness yet
                    continue
            out.append("pk_witness(name = " + _lit(k + "__witness") + ", holds = " + _lit(body) + pj +
                       ", premises = [" + ", ".join(prem) + "], data = [" +
                       ", ".join([_lit(d) for d in _data(reads, files, imports)]) + "])")
            wits.append('":%s__witness"' % k)
        out.append('pk_proof(name = "proof", witnesses = [%s], visibility = ["//visibility:public"])' % ", ".join(wits))
    repository_ctx.file("BUILD.bazel", "\n".join(out) + "\n")

bib_repo = repository_rule(
    implementation = _bib_repo_impl,
    attrs = {
        "bib": attr.label(mandatory = True, allow_single_file = True),
        "project": attr.string(mandatory = True),
        "adequacy": attr.bool(default = False),
        "local": attr.bool(default = False),  # Ζ·resist: host-coupled project (setup) — pk_cmd runs on the host
        "compose": attr.bool(default = False),  # Ζ·compose: project the witness DAG (rests-on as build deps) + :proof
        "calc": attr.bool(default = False),  # Ζ·calc·interp: one cached pk_calc per claim → verdict + grade readings
        "emerge": attr.bool(default = False),  # Ζ·emerge·gate: a def-calc per claim + pk_cohere (∂² faces in //:hook)
        "sites": attr.string_list(default = []),  # ·gen·surface: the engine def-sites (enumerated once by the extension)
        "closures": attr.string_list(default = []),  # ·gen·closure: per-claim witness closure roots (Ξ·dag·eval)
        "owns_concepts": attr.bool(default = False),  # Λ·witness: the concept LIBRARY — its per-concept verdict + def-cert are PUBLIC, imported by views' concept: checks
    },
)

def _bib_ext_impl(module_ctx):
    # ·gen·surface — the def-site surface is a property of the ENGINE (computed once here); ·gen·closure
    # — each claim's witness closure is a property of the PROJECT's check module (computed per emerge
    # project).  Both project the shared engine AST (core), beside the bib parse.
    core = _core(module_ctx)
    sites = _surface(module_ctx, core)
    for mod in module_ctx.modules:
        for tag in mod.tags.project:
            bib_repo(name = tag.name, bib = tag.bib, project = tag.project, adequacy = tag.adequacy, local = tag.local, compose = tag.compose, calc = tag.calc, emerge = tag.emerge, owns_concepts = tag.owns_concepts, sites = sites if tag.emerge else [], closures = _closures(module_ctx, tag.project, core) if tag.emerge else [])

bib = module_extension(
    implementation = _bib_ext_impl,
    tag_classes = {
        "project": tag_class(attrs = {
            "name": attr.string(mandatory = True),
            "bib": attr.label(mandatory = True),
            "project": attr.string(mandatory = True),
            "adequacy": attr.bool(default = False),
            "local": attr.bool(default = False),
            "compose": attr.bool(default = False),
            "calc": attr.bool(default = False),
            "emerge": attr.bool(default = False),
            "owns_concepts": attr.bool(default = False),
        }),
    },
)
