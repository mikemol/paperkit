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
    tier = ""       # Ζ·tier — per-warrant `tier = {sandbox|local|toolchain}` ("" = inherit the project default)
    consumes = []   # Ρ·wcag·oracle-edge — sibling warrant KEYS whose verdict RECORD this check reads
                    # (records-as-deps within a project: the sibling runs ONCE, memoized, and its
                    # verdict.json is a declared bazel input here — freshness by the action graph)
    for raw in content.splitlines():
        s = raw.strip()
        if s.startswith("@") and "{" in s:
            if key != None:
                out.append((key, check, sib, reads, rests, tier, consumes))
            key = s.split("{", 1)[1].split(",", 1)[0].strip()
            check = ""
            sib = ""
            reads = []
            rests = []
            tier = ""
            consumes = []
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
            elif name == "tier" and "{" in s and "}" in s:
                tier = s.split("{", 1)[1].rsplit("}", 1)[0].strip()
            elif name == "consumes" and "{" in s and "}" in s:
                inner = s.split("{", 1)[1].rsplit("}", 1)[0]
                consumes = [t.strip() for t in inner.split(",") if t.strip()]
    if key != None:
        out.append((key, check, sib, reads, rests, tier, consumes))
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

def _nonmechanical(content):
    """Ζ·talk·tier — the check TYPES a project declares NON-MECHANICAL (`[checks.X] mechanical =
    false`): GATED but never GRADED, the same disposition `tier` gives a host-run warrant.

    A `premise:` or `definition:` resolves by `cmd = "true"`, which is unfalsifiable BY
    CONSTRUCTION — no mutation of any input can flip it — so the def-sweep correctly measures
    sens=∅ and the grade lands `indeterminate`, below the adequacy floor.  Failing adequacy there
    would force a project to delete its honest premises or dress them in a fake mechanism, which
    is the dishonesty the verb exists to prevent.  Excluding them keeps adequacy ASSERTING over
    the claims that are actually sweep candidates.

    DECLARED, never inferred: `cmd == "true"` would be a tempting tell and a hole, since any
    project could then silence adequacy by routing a real claim through a trivial command."""
    out = []
    cur = None
    for raw in content.splitlines():
        s = raw.strip()
        if s.startswith("[checks."):
            cur = s[len("[checks."):].split("]")[0].strip()
        elif s.startswith("["):
            cur = None
        elif cur != None and s.startswith("mechanical") and "=" in s:
            if s.split("=", 1)[1].strip().lower() == "false":
                out.append(cur)
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

def _import_label(verb, name, key, owner, exports, wired, hint):
    """Ζ·grid·sibling — REFUSE a cross-project import label that nothing will emit.

    `result:` and `concept:` are the two BOUNDARY-CROSSING verbs: each writes a label into a
    SIBLING generated repo (`@paperkit_<owner>//:<key>`) that nothing on this side produces or
    validates.  Bazel discovers the lie only when the action runs — measured for `concept:` on
    2026-08-28: an entry written with the wrong verb resolved GREEN standalone, passed its
    project gate at 43/43, and died ~5,000 lines into a two-hour //:hook as `missing input file
    '@@+bib+paperkit_library//:degeneracy-has-kinds__dcalc'`.  That message names the SYMPTOM.
    The information needed to refuse — which projects are wired, which EXPORT, and what keys they
    export — is resolved in the module extension and handed here, so the refusal happens at
    generation with the one-word cause in it.

    Three ways the label can dangle, three distinct causes:
      * the owner project is not a `bib.project` at all      → NO SUCH PROJECT
      * it is wired but does not export (owns_* unset)       → NOT EXPORTED
      * it exports, but not this key (a rename, a typo)      → NO SUCH CLAIM

    ⚑ AN EMPTY POPULATION REFUSES, IT DOES NOT REJECT.  `wired` is the set of every bib.project
    tag, so it can only be empty if the extension did not hand one down — the instrument never saw
    the population.  Rejecting each citation against an empty set would fail-closed on EVERY
    cross-project import, including true ones, and a guard that reds a correct citation teaches
    the next reader to delete the guard rather than read it.  Measured here 2026-09-02: a sibling
    agent's query landed in the window between this attr being declared (default []) and the
    extension being taught to populate it, and saw exactly that — `rm-status`, a valid
    `result:paper`, refused with an empty `Wired:` list.  The transient cause is gone; the
    fail-closed shape it exposed is what this arm removes.  "I cannot tell" is a different verdict
    from "this dangles", and folding the first into the second is the defect.
    """
    if not wired:
        fail(("bibtex Ζ·grid·sibling: %s: cannot check `check = {%s}` — the WIRED PROJECT SET IS " +
              "EMPTY, so this guard never saw a population to check against.  That is an " +
              "uncalibrated instrument, not a dangling label: the citation may well be correct.  " +
              "The set is computed in _bib_ext_impl from the `bib.project` tags and passed on the " +
              "`wired` attr; an empty one means the extension did not hand it down (a stale " +
              "generated repo mid-edit, or a bib_repo instantiated outside the extension).  " +
              "Re-fetch; if it persists, the extension is the layer to fix — do NOT relax this " +
              "guard, which is measuring nothing, not measuring a failure.") % (name, verb))
    if owner not in wired:
        fail(("bibtex Ζ·grid·sibling: %s: `check = {%s}` names the project '%s', which is NOT A " +
              "WIRED PROJECT.  This emits `@paperkit_%s//:%s`, a label in a repo MODULE.bazel " +
              "never declares, so it would surface hours into the build as `missing input file` " +
              "rather than here.  Add a `bib.project(name = \"paperkit_%s\", …)` and list it in " +
              "`use_repo`, or fix the project name.  Wired: %s") %
             (name, verb, owner, owner, key, owner, ", ".join(wired)))
    have = {}
    for e in exports:
        p, _, k = e.partition("\t")
        if p == owner:
            have[k] = True
    if not have:
        fail(("bibtex Ζ·grid·sibling: %s: `check = {%s}` imports from '%s', which EXPORTS " +
              "NOTHING.  A project's per-claim records are public only when it opts in, so " +
              "`@paperkit_%s//:%s` is not emitted and the import would fail as `missing input " +
              "file` hours from now.  Set `%s` on '%s' in MODULE.bazel — the owner declares its " +
              "claims a public surface it intends views to cite (and accepts that renaming one " +
              "is a breaking change).") % (name, verb, owner, owner, key, hint, owner))
    if key not in have:
        fail(("bibtex Ζ·grid·sibling: %s: `check = {%s}` names '%s', which is NO SUCH CLAIM in " +
              "project '%s'.  `@paperkit_%s//:%s` is a label nothing emits — a RENAMED or " +
              "misspelled key, the exact shape that resolves green locally and dies hours into " +
              "the build as `missing input file`.  '%s' exports: %s") %
             (name, verb, key, owner, owner, key, owner, ", ".join(sorted(have))))
    return "@paperkit_" + owner + "//:" + key

def _verb_rule(name, check, proj, files, reads, custom, tier, consumes = [], imports = [], vis = "", exports = [], wired = []):
    """Dispatch ONE bib check to its specific typed rule (a record), not a general `gate.py --only`
    script.  The check's TYPE selects the rule; python is dropped-to only in pk_cmd (the exit-code
    oracle), under the toolchain.  A custom type expands its [checks.X] cmd template.  `tier` is the
    warrant's enforcement tier (Ζ·tier): sandbox (hermetic, swept) | local (host-coupled, uncached) |
    toolchain (host toolchain, cached + stamped with the toolchain fingerprint).  Only pk_cmd carries
    a tier (the others are always hermetic-sandbox records).  `consumes` (Ρ·wcag·oracle-edge) names
    sibling warrant keys whose verdict records this pk_cmd depends on (records-as-deps, memoized)."""
    i = check.find(":")
    typ = check[:i]
    target = check[i + 1:]
    dl = ", ".join([_lit(d) for d in _data(reads, files, imports)])
    pj = "" if proj == "." else ", project = " + _lit(proj)
    tc = "" if tier == "sandbox" else ", tier = " + _lit(tier)
    # Ρ·wcag·oracle-edge — each consumed sibling key → its verdict-record target label ":<key>" in the
    # same generated package (all warrants of a project are pk_* siblings here — no visibility barrier).
    cs = "" if not consumes else ", consumes = [" + ", ".join([_lit(":" + c) for c in consumes]) + "]"
    if typ == "cmd":
        return "pk_cmd(name = " + _lit(name) + ", cmd = " + _lit(target) + pj + tc + cs + ", data = [" + dl + "]" + vis + ")"
    elif typ == "file":
        return "pk_file(name = " + _lit(name) + ", path = " + _lit(target) + ", data = [" + dl + "]" + vis + ")"
    elif typ == "result":   # records-as-deps: depend on the sibling's verdict record
        # Λ·reduce — `<project>#<claim>` depends on the sibling's PER-CLAIM record instead of its
        # aggregate.  pk_result already reads "a verdict record from a label" and does not care
        # which, and the bib's claim-DAG already emits one target per claim (Ζ·starlark), so the
        # finer address is a LABEL change, not a new rule: the structure was there, only the
        # aggregate was ever addressed.  Bare `<project>` keeps the gate_rec dep unchanged.
        sproj, _, sclaim = target.partition("#")
        # Ζ·grid·sibling — REFUSE a dangling sibling label HERE (see _import_label).  `gate_rec` is
        # emitted PUBLIC by every generated project, so the bare `result:<proj>` form needs only the
        # WIRING check; the `#<claim>` form additionally needs the owner to export that key, which
        # is the live risk — render is owns_warrants and talk cites four of its claims BY NAME, so
        # a rename in render reproduces Ζ·grid·dangling exactly.
        if sclaim:
            lbl = _import_label("result:" + target, name, sclaim, sproj, exports, wired, "owns_warrants = True")
        elif sproj not in wired:
            fail(("bibtex Ζ·grid·sibling: %s: `check = {result:%s}` names the project '%s', which " +
                  "is NOT A WIRED PROJECT.  This emits `@paperkit_%s//:gate_rec`, a label in a " +
                  "repo MODULE.bazel never declares, so it would surface hours into the build as " +
                  "`missing input file` rather than here.  Add a `bib.project(name = " +
                  "\"paperkit_%s\", …)` and list it in `use_repo`, or fix the project name.  " +
                  "Wired: %s") % (name, target, sproj, sproj, sproj, ", ".join(wired)))
            lbl = ""
        else:
            lbl = "@paperkit_" + sproj + "//:gate_rec"
        return "pk_result(name = " + _lit(name) + ', sibling_verdict = "' + lbl + '"' + vis + ')'
    elif typ == "agree":
        prods = ", ".join([_lit(p.strip()) for p in target.split("|||") if p.strip()])
        return "pk_agree(name = " + _lit(name) + ", producers = [" + prods + "]" + pj + tc + vis + ")"
    elif typ in custom:     # a config-declared cmd template — {target} substituted, run as a cmd oracle
        cmd = custom[typ].replace("{target}", target)
        return "pk_cmd(name = " + _lit(name) + ", cmd = " + _lit(cmd) + pj + tc + ", data = [" + dl + "])"
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
    spec = q.replace(".", "_").replace("+", "_add_").replace("-", "_drop_").replace(":", "_").replace("#", "_arm_")
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
    # Μ·sweep·atom — sites.py imports the branch:/flip: enumerators from paperkit/mutate.py (the ONE
    # atom source), so an edit to it must regenerate the surface too, else the extension serves a stale
    # set ([[bazel-action-idempotency]]: the tool is an input like the core modules).
    module_ctx.watch(module_ctx.path(Label("@@//paperkit:mutate.py")))
    root = str(module_ctx.path(Label("@@//:MODULE.bazel")).dirname)
    res = module_ctx.execute([str(py), str(ds)] + core, working_directory = root)
    if res.return_code != 0:
        fail("·gen·surface: sites.py failed (%d): %s" % (res.return_code, res.stderr))
    return [l for l in res.stdout.splitlines() if "\t" in l]

def _claim_script(module_ctx, project):
    """The claim-WITNESS module a project's `claim:` type runs — DECLARED as [checks.claim] witness.

    ⚑ IT USED TO BE INFERRED FROM `cmd`, BY TAKING THE FIRST `.py` TOKEN ON THAT LINE.  That reads a
    MODULE out of a string whose only contract is to be a runnable COMMAND, and it made the two
    inseparable: the grid, bnd-toplevel and closure_census all need the module, the resolver needs
    the command, and one string served both only for as long as the command happened to name a
    python file.

    ⚑⚑ Ζ·entry·point BROKE THAT, WHICH IS HOW THE COUPLING SURFACED.  A witness whose environment is
    owned by an entry point declares `cmd = "./run-witness {target}"` — no `.py` anywhere — and the
    inference silently returned None, so the library's witness became underivable and bnd-toplevel
    reported 2 of 3 emerge projects.  Not a regression in the entry point: the inference was always
    reading a filename out of a command, and the entry point is simply the first command that does
    not contain one.

    The declaration is REQUIRED, not defaulted (operator's call, 2026-08-31: *"Require it; this is
    why I haven't published yet"*).  A fallback to the old scan would keep the inference alive in
    the one place it is hardest to see — a project that silently gets the historical behaviour —
    and there is no published consumer to protect.  A project declaring `claim:` and no `witness`
    FAILS the generation, naming the file and the key, rather than yielding an empty closure that
    degrades a cell grid into monolithic sweeps (the Ζ·library·grid failure: ~10 min per claim, a
    critical path nothing could parallelise, and no def memory measurement at all).
    """
    lbl = "@@//:paper.toml" if project == "." else "@@//" + project + ":paper.toml"
    p = module_ctx.path(Label(lbl))
    if not p.exists:
        return None
    text = module_ctx.read(p)
    module_ctx.watch(p)
    i = text.find("[checks.claim]")
    if i < 0:
        return None
    # ⚑ THE KEY IS MATCHED AT LINE START, NOT AS A SUBSTRING.  A bare `text.find("witness", i)`
    # matches the word inside `cmd = "./run-witness {target}"` — which comes FIRST — and then reads
    # `{target}"` as the value.  Measured: it failed exactly that way on library/paper.toml, the
    # one project whose command names an entry point.  The scan that this replaces had the same
    # class of defect one field over; repeating it here would have been the joke telling itself.
    for raw in text[i:].split("\n"):
        stripped = raw.strip()
        if stripped.startswith("[") and not stripped.startswith("[checks.claim]"):
            break                                    # left the table without finding the key
        if not stripped.startswith("witness"):
            continue
        rest = stripped[len("witness"):].strip()
        if not rest.startswith("="):
            continue                                 # `witness_something = ...`, not our key
        val = rest[1:].strip().strip('"').strip("'")
        if val.endswith(".py"):
            return val  # relative to the project dir, e.g. checks/claims.py
        fail("·gen·closure: %s [checks.claim] `witness` is not a .py path: %s" % (lbl, stripped))
    fail("·gen·closure: %s declares [checks.claim] but no `witness` key.  The witness MODULE " % lbl +
         "is no longer inferred from `cmd` (a command need not name a .py — see Ζ·entry·point); " +
         "declare it explicitly, e.g. `witness = \"checks/claims.py\"`.")
    return None

def _closures(module_ctx, project, core):
    """Ξ·dag·eval — per emerge project, each claim WITNESS's closure ROOTS via closure.py over the
    project's claim-witness module (paper.toml [checks.claim]) + the core names (which include the
    per-capability _fixture_* modules, Μ·kernel·fixture·split — a fixture import is an ordinary
    IMPORT root, no facade plumbing).  Returns ["claim\tmodule", ...] plus "claim\tread:module"
    for pure-READ roots (Μ·kernel·fixture·reads — staged flat, own sites only); [] if the project
    declares no claim: type.  Unlike the def-site SURFACE (engine-global), a witness's closure depends on the
    PROJECT's check module — so this runs per emerge project, watching that module so an edited
    witness re-generates its cells' closures."""
    script = _claim_script(module_ctx, project)
    if not script:
        return []
    lbl = "@@//:" + script if project == "." else "@@//" + project + ":" + script
    check = module_ctx.path(Label(lbl))
    if not check.exists:
        return []
    module_ctx.watch(check)
    py = _host_py(module_ctx, "·gen·closure")
    cl = module_ctx.path(Label("@@//tools:closure.py"))
    # WATCH the enumerator, so editing it regenerates the closures (the tool is an INPUT,
    # [[bazel-action-idempotency]] — else a stale closure output).  The _fixture_* capability
    # modules are core modules, already watched by _core.
    module_ctx.watch(cl)
    root = str(module_ctx.path(Label("@@//:MODULE.bazel")).dirname)
    # --relpath — the check's REPO-RELATIVE path (paper/checks/claims.py, checks/readme.py), so
    # closure.py resolves Path(__file__).parents[N] to the SANDBOX prefix a file toggle must hit.
    relpath = script if project == "." else project + "/" + script
    res = module_ctx.execute([str(py), str(cl), "--check", str(check), "--relpath", relpath] + core, working_directory = root)
    if res.return_code != 0:
        fail("·gen·closure: closure.py failed (%d): %s" % (res.return_code, res.stderr))
    return [l for l in res.stdout.splitlines() if "\t" in l]

def _exports(module_ctx, project, bib_label):
    """Ζ·grid·sibling — the claim keys a project EXPORTS, resolved in the EXTENSION.

    A cross-project check (`result:<proj>#<claim>`, `concept:<key>`) emits a label in ANOTHER
    generated repo, and a `repository_ctx` cannot see that repo: it holds only its own attrs.  So
    the importing side asserted the label and let Bazel discover the lie hours later as `missing
    input file` — the Ζ·grid·dangling shape, one seam over.  The module extension is the layer
    that OWNS cross-project resolution: it enumerates every `bib.project` tag, so it can read each
    exporting project's bibs here, once, and hand every repo the resolved key set.

    Returns the CHECKED claim keys (a check-less bib reference emits no target, so it is not
    importable).  The warrants list resolves exactly as _bib_repo_impl resolves it — paper.toml
    `warrants`, else the anchor bib's basename — because that is what decides which entries the
    generated package contains."""
    bp = module_ctx.path(bib_label)
    warrants = []
    tomlp = bp.dirname.get_child("paper.toml")
    if tomlp.exists:
        module_ctx.watch(tomlp)
        warrants = _warrants(module_ctx.read(tomlp))
    if not warrants:
        warrants = [bp.basename]
    keys = []
    for w in warrants:
        wp = module_ctx.path(Label(w)) if (":" in w or w.startswith("@")) else bp.dirname.get_child(w)
        module_ctx.watch(wp)
        for k, check, _s, _r, _rr, _t, _c in _entries(module_ctx.read(wp)):
            if check:
                keys.append(project + "\t" + k)
    return keys

def _bib_repo_impl(repository_ctx):
    bibp = repository_ctx.path(repository_ctx.attr.bib)
    proj = repository_ctx.attr.project
    files = "@@//:files" if proj == "." else "@@//%s:files" % proj
    # Ζ·tier — the project `tier` attr is the DEFAULT enforcement tier for a warrant that does not
    # declare its own `tier = {…}`.  A warrant's effective tier is `wt` = its own `tier` or this default:
    #   sandbox (hermetic, cached, mutation-SWEPT) | local (host-coupled, uncached — setup) |
    #   toolchain (host toolchain, cached + stamped).  Only `sandbox` is swept and footprint-audited.
    proj_tier = repository_ctx.attr.tier

    # Custom check types AND the project's WARRANTS LIST both come from paper.toml (watched, so an
    # edit re-fetches).  Multi-bib composition is the same thing project.py does over `warrants`
    # (bib.load_config), lifted to the generator so a project's claims may be authored across modules
    # (the concept-library reconstitution).  The `bib` attr is the ANCHOR that locates the project dir;
    # a single-bib project (empty/1-element list) is byte-for-byte unchanged.  Check-less claims (bib
    # references) contribute no target — every parsed loop below skips `if not check`.
    custom = {}
    warrants = []
    nonmech = []
    tomlp = bibp.dirname.get_child("paper.toml")
    if tomlp.exists:
        repository_ctx.watch(tomlp)
        toml = repository_ctx.read(tomlp)
        custom = _custom(toml)
        warrants = _warrants(toml)
        nonmech = _nonmechanical(toml)
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

    # Ζ·tier — a project is all-HOST iff EVERY checked warrant runs on the host (its effective tier is
    # local or toolchain, never sandbox).  The footprint audit (a per-sandbox-warrant declare-vs-strace
    # cross-check) is emitted iff SOME warrant is sandbox — so its symbols load iff `not all_host`.
    all_host = True
    for _pk, _pc, _ps, _pr, _prr, _pt, _pcons in parsed:
        if _pc and ((_pt if _pt else proj_tier) == "sandbox"):
            all_host = False
            break

    # Τ·mem·learn — the per-project learned reservation manifest (a projection of observed peaks,
    # mem.json beside the bib; regenerated on-demand by //:mem-learn).  Resolved per claim down the
    # (claim > resolution > cold-start) ladder when emitting each pk_calc.  Absent ⇒ {} ⇒ every
    # claim falls through to calc.bzl's cold-start floor (mem = 0).
    mem = {}
    # Ζ·mem·wire — the build input is the PROJECTION (mem.json), not the observation store
    # (mem.sqlite).  Measured before choosing: a new cell changes the DB's bytes but NOT the
    # manifest it projects to — one sweep deposits ~163 observations, so watching the DB would
    # re-fetch this repo rule 163 times to regenerate a BUILD file whose content never moved
    # (paper's is 52,584 pk_eval targets).  Watching the projection invalidates exactly when a
    # RESERVATION changes, which is the only thing this generator reads.
    #
    # The store is where provenance lives ("256 rests on 79 cells, 76-216MB, measured when"); the
    # projection is where the build reads a number.  Regenerate with tools/mem_project.py — the
    # generate-and-gate discipline (project-dont-author), not a hand-maintained copy.
    memp = repository_ctx.path(repository_ctx.attr.bib).dirname.get_child("mem.json")
    if memp.exists:
        repository_ctx.watch(memp)
        mem = json.decode(repository_ctx.read(memp))

    out = ['load("@@//tools:verb.bzl", "pk_agree", "pk_cmd", "pk_file", "pk_gate", "pk_result")']
    syms = []
    if repository_ctx.attr.adequacy:
        syms += ["pk_adequacy", "pk_grade_claim"]
    if not all_host:                    # Ζ·foot·act — the footprint audit (emitted iff some warrant is sandbox)
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
    rroots = {}    # Μ·kernel·fixture·reads — claim key → pure-READ modules (staged FLAT .py, no cone)
    fsites = {}    # Ζ·mutant·struct·node-kinds — claim key → its FILE toggle specs (file+:/file-:<path>)
    contents = {}  # Ζ·mutant·struct·node-kinds — claim key → [(op, path, substring)] CONTENT toggles
    for l in repository_ctx.attr.closures:
        parts = l.split("\t")
        k = parts[0]
        if len(parts) == 4 and parts[1] in ("content-", "content+"):
            contents.setdefault(k, []).append((parts[1], parts[2], parts[3]))
        elif parts[1].startswith("file+:") or parts[1].startswith("file-:"):
            fsites.setdefault(k, []).append(parts[1])
        elif parts[1].startswith("read:"):
            rroots.setdefault(k, []).append(parts[1][len("read:"):])
        else:
            closures.setdefault(k, []).append(parts[1])
    # the claim-WITNESS script each pk_eval runs, EXEC-relative — the .py in THIS project's
    # [checks.claim] cmd (paper → paper/checks/claims.py, root → checks/readme.py), project-prefixed.
    # NOT hardcoded: root's readme.py is a different module than paper's claims.py, so a hardcoded
    # paper/checks/claims.py ran the wrong script for every root cell → every root ∅ flipped (garbage).
    # Ζ·entry·point — DECLARED, not inferred.  This scanned `custom["claim"]` (the `cmd` string)
    # for a `.py` token, which reads a filename out of a string whose only contract is to be
    # RUNNABLE.  `cmd = "./run-witness {target}"` names no .py, so wscript was "" and every
    # library cell ran `eval.py --check` with no argument.  The declaration is resolved once by
    # _claim_script (the owner, in the extension) and arrives on the `witness` attr.
    wscript = repository_ctx.attr.witness
    if wscript and proj != ".":
        wscript = proj + "/" + wscript
    if emerge:
        out.append("# ·gen·surface: %d core engine def-sites (enumerated once, engine-side)" % len(sites))
    if calc:
        csyms = ["pk_calc", "pk_grade", "pk_mem_learn", "pk_verdict"]
        if emerge:
            csyms += ["pk_cohere", "pk_mutate", "pk_pyc", "pk_eval", "pk_sens", "pk_decisions", "pk_decisions_summary"]
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
    dcns = []            # Μ·sweep·atom — the per-claim __decisions targets, folded into one summary (else inert)
    calc_claims = {}
    # Ζ·mem·def·blind — every pk_eval label emitted, so mem_learn can aggregate the DEF resolution
    # too.  Without it the expensive resolution was the unmeasured one: the def-sweep is a grid of
    # pk_eval cells (not a pk_calc), so `def` could only ever be the cold-start floor.
    eval_cells = []
    imported_cert = {}   # Λ·witness — k → the owner library's __dcalc cert label (a concept: import edge)
    owns = repository_ctx.attr.owns_concepts
    # Λ·delegate — a project that EXPORTS its warrants lets a sibling `result:<proj>#<claim>`
    # depend on ONE of its per-claim verdict records.  OPT-IN, exactly like owns_concepts:
    # making every claim public by default would silently widen every project's boundary to
    # its entire claim set, so a project declares that its warrants are a public surface it
    # intends downstream views to cite, and accepts that renaming one is a breaking change.
    wvis = ', visibility = ["//visibility:public"]' if repository_ctx.attr.owns_warrants else ""
    vis = ', visibility = ["//visibility:public"]'  # the owner EXPORTS per-concept records for views to import
    for k, check, sib, reads, rests, tier, consumes in parsed:
        if not check:
            continue
        # Ζ·tier — the warrant's effective tier: its own `tier = {…}`, else the project default.  A
        # NON-sandbox warrant (local or toolchain) runs on the host and takes the `else` verb-rule
        # branch (so it is gated, in gate_rec) and never the hermetic sweep branch below — the sweep
        # mutates engine bytecode in the sandbox, which a host-run check cannot use.
        wt = tier if tier else proj_tier
        if check.startswith("concept:"):
            # Λ·witness — a concept: check IMPORTS a concept authored + GRADED once in the library.  The
            # VERDICT is the library's per-concept verdict record (pk_result, records-as-deps, like
            # result:); the GRADE + :cohere read the library's def-sweep certificate (__dcalc = verdict +
            # engine fingerprint), so the PROOF travels WITH the import — the view neither re-sweeps
            # (Λ·grid's cost) nor drops the fingerprint (naive-delegate's :cohere break).
            # Λ·key·graded — the key may be PARAMETERISED (`family/subfamily/argument`), so it
            # carries `/`, and it is used here UNFLATTENED on purpose.  Two reasons, both load-bearing:
            #   (1) `/` is legal in a Bazel target NAME (it is a package-relative path fragment) —
            #       verified: `//:shadow/110/cotype-unify` analyses and builds.
            #   (2) BOTH SIDES derive from the same bib key.  @paperkit_library is a GENERATED repo
            #       (MODULE.bazel bib.project(owns_concepts = True)) whose per-concept targets are
            #       named `_lit(k)` from the library's own keys.  Flattening `/`→`_` HERE (as
            #       _sitename/_filesitename do for perturbation sites) would desynchronise this
            #       consumer's label from the emitter's target name and break the import — the
            #       flatteners exist for mutation SITES, which have no such counterpart to match.
            key = check[len("concept:"):]
            # Ζ·grid·dangling — A LIBRARY MAY NOT `concept:` ITS OWN KEY.  `concept:` is the IMPORT
            # verb: it names a certificate the CONCEPT LIBRARY authors, and the two labels below are
            # asserted to exist in another repo without anything here checking that they do.  From
            # inside the library that assertion is self-referential and always false — the library
            # AUTHORS its concepts (every one of its own entries is `claim:`, resolved by its
            # declared witness), so it emits no `@paperkit_library//:<key>__dcalc` for a key it is
            # currently defining, and the `__grade` rule below then consumes a label NOTHING
            # produces.
            #
            # ⚑ MEASURED 2026-08-28, and the cost is the point: an entry added to concepts.bib with
            # `check = {concept:...}` instead of `{claim:...}` resolved GREEN standalone (the CLI
            # runs the witness directly and never reads this bib's check field), passed the
            # project gate at 43/43, and died ~5,000 lines into a two-hour //:hook as `missing
            # input file '@@+bib+paperkit_library//:degeneracy-has-kinds__dcalc'` — a name that
            # points at the symptom and not at the one-word cause.  The information needed to
            # refuse was present HERE, at generation, before any action ran.
            #
            # This is the same fold paperkit's tristate exists to refuse, in the generator: an
            # unsatisfiable REQUEST recorded as if it were a satisfiable one.  Fail at the layer
            # that knows, naming the verb to use instead.
            if repository_ctx.attr.owns_concepts:
                fail(("bibtex: %s: `check = {concept:%s}` in the CONCEPT LIBRARY itself.  " +
                      "`concept:` IMPORTS a certificate this library authors, so from inside it " +
                      "the import is self-referential: no `@paperkit_library//:%s__dcalc` is " +
                      "emitted for a key defined here, and the generated grade rule would consume " +
                      "a label nothing produces (surfacing hours later as `missing input file`).  " +
                      "Use `check = {claim:%s}` — the library's own witness verb, declared in its " +
                      "paper.toml `[checks.claim]`.") % (k, key, key, key))
            # Ζ·grid·sibling — the MIRROR of the guard above.  That one refuses the library citing
            # a key it AUTHORS; this one refuses a VIEW citing a key the library does NOT author.
            # Same dangling label, same `missing input file` hours later — only the direction of
            # the mistake differs, and a key rename in concepts.bib produces exactly this one.
            lbl = _import_label("concept:" + key, k, key, "library", repository_ctx.attr.exports,
                                repository_ctx.attr.wired, "owns_concepts = True")
            out.append("pk_result(name = " + _lit(k) + ', sibling_verdict = "' + lbl + '")')
            imported_cert[k] = lbl + "__dcalc"
            recs.append('":%s"' % k)
            continue
        if calc and wt == "sandbox" and _body(check, custom) != None:
            # Ζ·calc·interp — ONE cached sweep (pk_calc) feeds the verdict reading here (and the grade
            # reading below); the redundant verdict run + the adequacy re-sweep collapse into it.
            # Ζ·tier — only a SANDBOX warrant is swept (the `wt == "sandbox"`): the sweep is hermetic
            # (calc.bzl has no host-escape), so a host-coupled check cannot be mutation-swept; it falls
            # to the `else` verb-rule branch and is GATED but not graded.
            dl = ", ".join([_lit(d) for d in _data(reads, files, imports)])
            out.append("pk_calc(name = " + _lit(k + "__calc") + ", claim = " + _lit(k) +
                       ", project = " + _lit(proj) + ", mem = " + str(_membucket(mem, k, "file")) +
                       ", data = [" + dl + "])")
            out.append("pk_verdict(name = " + _lit(k) + ", calc = " + _lit(":" + k + "__calc") + (vis if owns else "") + ")")
            calc_claims[k] = True
            if emerge and (closures.get(k) or rroots.get(k)):
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
                # Μ·kernel·fixture·reads — a pure-READ root joins the SITE set (mutating its
                # SOURCE can flip a source-inspection assert) but NOT the pyc-cone closure (a
                # read_text never loads imports, so its cone cannot flip the check); it is staged
                # as the plain //paperkit:<m>.py file label in the project list below.
                cset = {m: True for m in closures.get(k, []) + rroots.get(k, [])}
                csites = [s for s in sites if s[0] in cset]
                cl = ", ".join(['"@@//paperkit:%s"' % m[len("paperkit/"):-len(".py")] for m in closures.get(k, [])])
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
                rdl = ['"@@//paperkit:%s"' % m[len("paperkit/"):] for m in rroots.get(k, [])]
                edl = ", ".join([_lit(d) for d in _data(reads, files, imports, engine = False)] + rdl)
                # Τ·mem·learn·eval — a GRID cell is sized from the manifest exactly as a calc is.
                # pk_eval used to take calc.bzl's cold-start floor unconditionally, so the learned
                # `def` reservation reached the monolithic pk_calc and never the cells that replaced
                # it: measured, compose-chains needs 61MB and started every run at 4, climbing
                # 4→8→16→32→64 to re-derive a number already sitting in mem.json.  The ladder in
                # _membucket (per-claim > per-resolution > floor) is shared, so a claim measured
                # once is sized everywhere it runs.
                ev = ("check = " + _lit(wscript) + ", closure = [" + cl + "], project = [" +
                      (dl if check.startswith("result:") else edl) + "]" +
                      ", mem = " + str(_membucket(mem, k, "def")))
                # Μ·sweep·atom — PARTITION the closure sites by kind.  Raise-kind (def:/branch:/import+:)
                # cells are MONOTONE (an uncatchable raise / a presence toggle) → they feed the
                # sensitivity sweep (pk_sens).  flip: cells are NON-monotone (a condition inversion) →
                # they are BARRED from pk_sens and routed to pk_decisions (the orthogonal coverage axis)
                # — the grid-level bar mirroring the in-process FlipSite type; sens.py additionally
                # FAILS LOUD if a flip: record ever reaches it (belt-and-suspenders, since Starlark
                # cannot make a type error).
                cellnames = []
                flipcells = []
                for m, q in csites:
                    sn = _sitename(m, q)
                    out.append('pk_eval(name = "%s__%s", claim = %s, site = %s, module = %s, mutated_py = ":mut_%s", mutated_pyc = ":pyc_%s", %s)' % (
                        k, sn, _lit(k), _lit(m + "::" + q), _lit(m), sn, sn, ev))
                    # Μ·sweep·atom — the NON-monotone cells (flip: condition inversion, dflip: data-value
                    # perturb) route to pk_decisions; the raise-kind cells (def:/branch:/data-:/import+:)
                    # feed the sensitivity sweep.  A dflip: is the DATA analog of flip: — same partition.
                    (flipcells if (q.startswith("flip:") or q.startswith("dflip:")) else cellnames).append(sn)
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
                eval_cells += [":%s__%s" % (k, c) for c in cellnames] + [":%s__0" % k]
                # Ζ·library·grid — the GRID's __dcalc must carry the same visibility the
                # MONOLITHIC pk_calc below does.  A library with owns_concepts exports each
                # certificate so an importing view's pk_grade can read it (Λ·witness), and
                # converting library to a cell grid moved the certificate from pk_calc (which
                # applied `vis if owns`) to pk_sens (which did not) — so every downstream
                # `concept:` import failed ANALYSIS with "not visible from", before any action ran.
                out.append('pk_sens(name = "%s__dcalc", evals = [%s], baseline = ":%s__0"%s)' % (
                    k, ", ".join(['":%s__%s"' % (k, c) for c in cellnames]), k, vis if owns else ""))
                # Μ·sweep·atom — the DECISION-COVERAGE grid twin: pk_decisions reads the flip: cells
                # (did inverting each condition flip the check) AND the raise-kind cells (which branch:
                # arms are reached — each cell is single-site, so its flipped bit IS a per-arm reach
                # probe, sibling-independent by construction, exactly the in-process flip_one gate).  A
                # decision is unasserted iff BOTH its sibling branch: arms are reached and its inversion
                # does NOT flip.  Emitted only when the row has flip: cells (a condition to cover).
                if flipcells:
                    out.append('pk_decisions(name = "%s__decisions", flips = [%s], reach = [%s])' % (
                        k,
                        ", ".join(['":%s__%s"' % (k, c) for c in flipcells]),
                        ", ".join(['":%s__%s"' % (k, c) for c in cellnames])))
                    dcns.append('":%s__decisions"' % k)     # collect for the project summary (else inert)
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
            out.append(_verb_rule(k, check, proj, files, reads, custom, wt, consumes, imports, wvis,
                                  repository_ctx.attr.exports, repository_ctx.attr.wired))
        recs.append('":%s"' % k)

    if calc_claims:
        # Τ·mem·learn — the regen target: aggregate every calc's observed peak → mem.json (the
        # committed projection consumed by the ladder above).  On-demand: build under
        # --config=memobserve in a clean output base, then copy bazel-bin .../mem.json to the source
        # mem.json beside this bib (NOT hook-gated — the observe is too costly and a stale manifest
        # is a benign perf hint).  Aggregates the file-calcs' peaks; the def-sweep is now a grid of
        # pk_eval cells (Ζ·mutant·wire·gen), not a pk_calc with a peak output group, so it is not here.
        # Ζ·mem·def·blind — file-calcs only as DEPENDENCIES.  The def-sweep's eval cells carry a
        # peak too (pk_eval's `peak` output group), but making mem_learn DEPEND on them inverts
        # the economics: paper's grid is 52,584 cells, so the manifest that exists to make the
        # sweep affordable would first require running the sweep unsized (measured: 41,468 deps
        # on one action).  The measurement must not cost what it is meant to save.
        #
        # The cells write their peaks as a SIDE EFFECT of work that runs anyway, and the manifest
        # is a READING over whatever peaks exist — mem_learn already tolerates a partial corpus
        # (it skips what it cannot read and NAMES why, rather than folding it to 0).  So the
        # measurement warms up: the first sweep runs on the cold-start floor and deposits peaks,
        # //:mem-observe harvests them, and the next sweep is sized.  A first pass may be
        # mis-sized; it fails fast and retries fast, which is cheaper than a barrier that can
        # never be crossed the first time.
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

    # Μ·sweep·atom — fold the per-claim __decisions records into ONE project summary, so the
    # decision-coverage grid twin is CONSUMED (the enforcement adversary's emitted-but-inert finding).
    # A PUBLIC target //<proj>:decisions built every commit (added to //:hook by the owner), reachable +
    # non-inert; the summary reads each __decisions record (a malformed one reds — a partition/
    # aggregation regression), reporting the reached-but-unasserted decisions.  It does NOT gate a floor:
    # decision-coverage is an orthogonal axis, so a high unasserted count is surfaced, never failed.
    if emerge and dcns:
        out.append('pk_decisions_summary(name = "decisions_rec", decisions = [%s], visibility = ["//visibility:public"])'
                   % ", ".join(dcns))
        out.append('sh_test(name = "decisions", srcs = ["@@//tools:assert_pass.sh"], ' +
                   'args = ["$(rootpath :decisions_rec)"], data = [":decisions_rec"], size = "small", ' +
                   'visibility = ["//visibility:public"])')

    # invariants — a structural meta-check over the WHOLE bib (coverage, no-axiom-K); an irreducibly
    # GENERAL oracle, kept as a cmd: drop (Ζ·resist).  It runs at the PROJECT default tier (a whole-bib
    # oracle has no single warrant's tier); it is pure engine, so sandbox for most projects.
    lc = "" if proj_tier == "sandbox" else ", tier = " + _lit(proj_tier)
    inv = "\"$(command -v python3)\" paperkit/gate.py --invariants --safe --without-K " + proj
    out.append("pk_cmd(name = \"invariants\", cmd = " + _lit(inv) + lc + ", data = [" + _lit(files) + "".join([", " + _lit(i) for i in imports]) + ', "@@//paperkit:engine"])')
    recs.append('":invariants"')

    # pk_gate aggregates the records → the project verdict; the assert-test puts it in the live gate.
    out.append('pk_gate(name = "gate_rec", checks = [%s], visibility = ["//visibility:public"])' % ", ".join(recs))
    # Ζ·gate·detail — stage the PER-CLAIM records beside the aggregate, so a red names the claims
    # that failed instead of only that something did.  Without them the assert sees one file
    # saying {"verdict":"fail"} and the diagnosis is a hand reconstruction from sibling artifacts.
    out.append('sh_test(name = "gate", srcs = ["@@//tools:assert_pass.sh"], ' +
               'args = ["$(rootpath :gate_rec)"], data = [":gate_rec", %s], size = "small", ' % ", ".join(recs) +
               'visibility = ["//visibility:public"])')
    if repository_ctx.attr.adequacy:
        # Ζ·nest — adequacy as a NESTING of per-claim grade records (pk_grade_claim) aggregated by
        # pk_adequacy; the assert-test puts it in //:hook.  (The old discriminate.py sweep sh_test
        # is retired; discriminate.py stays as the per-claim grade ORACLE behind pk_grade_claim.)
        grades = []
        for k, check, sib, reads, rests, tier, _consumes in parsed:
            if not check:
                continue
            # Ζ·tier — a NON-sandbox warrant (local or toolchain) is GATED but not GRADED: the adequacy
            # sweep (a hermetic mutation grade) cannot soundly grade a host-run check, so it is excluded
            # from the adequacy record entirely (it is not in calc_claims, and file-resolution grading
            # its source under the sandbox would be the same unsoundness).  Its verdict still gates via
            # gate_rec above; adequacy asserts falsifiability only over the sandbox subset.
            if (tier if tier else proj_tier) != "sandbox":
                continue
            # Ζ·talk·tier — a NON-MECHANICAL check type is gated but not graded, exactly as a
            # non-sandbox tier is: its cmd is unfalsifiable by construction, so a sweep measures
            # sens=∅ and adequacy would red on an honest premise.  Declared in paper.toml.
            if check.split(":")[0] in nonmech:
                continue
            if k in imported_cert:
                # Λ·witness — grade = the IMPORTED library certificate, read via read_grade → behavioral
                # WITH the owner's engine fingerprint (tests), so it passes adequacy (behavioral ≥ floor)
                # AND the same cert feeds the view's :cohere.  No local re-sweep, no dropped fingerprint.
                out.append("pk_grade(name = " + _lit(k + "__grade") + ", calc = " + _lit(imported_cert[k]) +
                           ', data = ["@@//paperkit:grade.py", "@@//tools:read_grade.py"])')
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
                gcalc = ":" + k + ("__dcalc" if closures.get(k) or rroots.get(k) else "__calc")
                # Μ·kernel — the grade is a READING via the ladder LEAF alone (read_grade imports
                # paperkit/grade.py, nothing else); the flat engine here re-keyed every grade
                # reading on ANY engine edit while buying nothing.
                out.append("pk_grade(name = " + _lit(k + "__grade") + ", calc = " + _lit(gcalc) +
                           ', data = ["@@//paperkit:grade.py", "@@//tools:read_grade.py"])')
            else:
                out.append("pk_grade_claim(name = " + _lit(k + "__grade") + ", claim = " + _lit(k) +
                           ", project = " + _lit(proj) + ", data = [" +
                           ", ".join([_lit(d) for d in _data(reads, files, imports)]) + "])")
            grades.append('":%s__grade"' % k)
        out.append('pk_adequacy(name = "adequacy_rec", grades = [%s], visibility = ["//visibility:public"])' % ", ".join(grades))
        # Ζ·gate·detail — the per-claim GRADE records staged too, so a red adequacy names the
        # claims that fell below the floor (and their grade) instead of only that some did.
        out.append('sh_test(name = "adequacy", srcs = ["@@//tools:assert_pass.sh"], ' +
                   'args = ["$(rootpath :adequacy_rec)"], data = [":adequacy_rec", %s], size = "small", ' % ", ".join(grades) +
                   'visibility = ["//visibility:public"])')

    # Ζ·foot·act — the declare+audit cross-check as a NESTING of per-claim footprint records
    # (pk_footprint, footdeps --only) aggregated by pk_footaudit, dissolving footdeps' ThreadPool.
    # Data is GENEROUS (every project) so the strace sees reads BEYOND the declaration.  On-demand
    # (not in //:hook).  Ζ·tier — a `local` (host-coupled) WARRANT's footprint needs the host, so it
    # is skipped per-warrant; the audit is still emitted for a project with ANY sandbox warrant.
    foots = []
    for k, check, sib, reads, rests, tier, _consumes in parsed:
        if not check or sib or check.startswith("concept:"):  # result:/concept: are import edges — no local footprint
            continue
        if (tier if tier else proj_tier) != "sandbox":   # a host-run warrant's footprint needs the host
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
        checked = {k: True for k, check, sib, reads, rests, tier, _consumes in parsed if check}
        wits = []
        pj = "" if proj == "." else ", project = " + _lit(proj)
        for k, check, sib, reads, rests, tier, _consumes in parsed:
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
        "tier": attr.string(default = "sandbox", values = ["sandbox", "local", "toolchain"]),  # Ζ·tier: the PROJECT-default enforcement tier for warrants that don't override
        "compose": attr.bool(default = False),  # Ζ·compose: project the witness DAG (rests-on as build deps) + :proof
        "calc": attr.bool(default = False),  # Ζ·calc·interp: one cached pk_calc per claim → verdict + grade readings
        "emerge": attr.bool(default = False),  # Ζ·emerge·gate: a def-calc per claim + pk_cohere (∂² faces in //:hook)
        "sites": attr.string_list(default = []),  # ·gen·surface: the engine def-sites (enumerated once by the extension)
        "closures": attr.string_list(default = []),  # ·gen·closure: per-claim witness closure roots (Ξ·dag·eval)
        # Ζ·entry·point — the claim-witness MODULE, project-relative, resolved by _claim_script in
        # the EXTENSION (which can read paper.toml) and passed in.  A repository_ctx cannot call
        # _claim_script — it holds no module_ctx — so re-deriving it here is the only alternative,
        # and re-deriving is what broke: this value used to be inferred by scanning the `cmd`
        # string for a `.py` token, which returned "" for `cmd = "./run-witness {target}"` and
        # emitted every library cell with an EMPTY `--check` (measured: `eval.py: error: argument
        # --check: expected one argument`, three cells, //:hook red).  ONE owner, two readers.
        "witness": attr.string(default = ""),
        "owns_concepts": attr.bool(default = False),  # Λ·witness: the concept LIBRARY — its per-concept verdict + def-cert are PUBLIC, imported by views' concept: checks
        "owns_warrants": attr.bool(default = False),  # Λ·delegate: this project EXPORTS its per-claim verdict records, so a sibling result:<proj>#<claim> can import ONE warrant instead of the whole gate
        # Ζ·grid·sibling — the cross-project IMPORT SURFACE, resolved once in the extension (the
        # only layer that can see sibling projects) and handed to every repo: "<proj>\t<key>" for
        # each claim an owns_warrants/owns_concepts project exports, plus the WIRED project names
        # (every bib.project tag).  Without them a dangling import label is merely ASSERTED here
        # and diagnosed hours later by Bazel as `missing input file` — Ζ·grid·dangling's shape.
        "exports": attr.string_list(default = []),
        "wired": attr.string_list(default = []),
    },
)

def _bib_ext_impl(module_ctx):
    # ·gen·surface — the def-site surface is a property of the ENGINE (computed once here); ·gen·closure
    # — each claim's witness closure is a property of the PROJECT's check module (computed per emerge
    # project).  Both project the shared engine AST (core), beside the bib parse.
    core = _core(module_ctx)
    sites = _surface(module_ctx, core)
    # Ζ·grid·sibling — the cross-project IMPORT SURFACE, resolved ONCE here.  A `result:` or
    # `concept:` check emits a label into a SIBLING generated repo, and only this loop can see
    # which siblings exist, which ones EXPORT (owns_warrants / owns_concepts), and what keys they
    # export.  Resolved here, the two import verbs are checkable at generation instead of hours
    # later; see the guards at the emit sites in _bib_repo_impl.
    wired = []
    exports = []
    for mod in module_ctx.modules:
        for tag in mod.tags.project:
            wired.append(tag.project)
            if tag.owns_warrants or tag.owns_concepts:
                exports += _exports(module_ctx, tag.project, tag.bib)
    wired = sorted(wired)
    for mod in module_ctx.modules:
        for tag in mod.tags.project:
            # Ζ·entry·point — `witness` is resolved HERE (only a module_ctx can read paper.toml)
            # and passed down; the repository rule reads the declaration instead of re-deriving it
            # from `cmd`.  Unconditional, not gated on emerge: _claim_script returns None for a
            # project declaring no `[checks.claim]`, and a project that HAS one owes the key
            # whether or not it builds a grid.
            bib_repo(name = tag.name, bib = tag.bib, project = tag.project, adequacy = tag.adequacy, tier = tag.tier, compose = tag.compose, calc = tag.calc, emerge = tag.emerge, owns_concepts = tag.owns_concepts, owns_warrants = tag.owns_warrants, sites = sites if tag.emerge else [], closures = _closures(module_ctx, tag.project, core) if tag.emerge else [], witness = _claim_script(module_ctx, tag.project) or "", exports = exports, wired = wired)

bib = module_extension(
    implementation = _bib_ext_impl,
    tag_classes = {
        "project": tag_class(attrs = {
            "name": attr.string(mandatory = True),
            "bib": attr.label(mandatory = True),
            "project": attr.string(mandatory = True),
            "adequacy": attr.bool(default = False),
            "tier": attr.string(default = "sandbox", values = ["sandbox", "local", "toolchain"]),
            "compose": attr.bool(default = False),
            "calc": attr.bool(default = False),
            "emerge": attr.bool(default = False),
            "owns_concepts": attr.bool(default = False),
            "owns_warrants": attr.bool(default = False),
        }),
    },
)
