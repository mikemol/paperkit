"""Ζ·calc·interp — separate the CALCULATION (the expensive measurement, computed once) from the
INTERPRETATIONS (cheap readings over it).  pk_calc runs the mutation sweep ONCE → a calc record
{baseline, sens}; pk_verdict and pk_grade are cheap READINGS of that record — the verdict is the
baseline, the grade is grader._grade_from_sens(baseline, sens).  Where the old families each
re-measured (pk_cmd runs the check, pk_grade_claim re-sweeps), here one sweep feeds both, and a
change re-runs only pk_calc; the readings are instant.  footaudit/emergence are the same shape.
"""

_PY = "@bazel_tools//tools/python:toolchain_type"

def _pypath(py):
    return 'export PATH="$(cd "$(dirname ' + py.interpreter.path + ')" && pwd):$PATH"; '

# Τ·mem·observe·clean — a native bool build setting (no skylib) gating the cgroup peak read.  Only
# under --config=memobserve (which sets --//tools:observe=True) is each action in its own cgroup, so
# memory.peak is tree-accurate; OFF, /proc/self/cgroup points at the SHARED bazel cgroup and the read
# is whole-build garbage.  So OFF the peak action writes a clean 0 (honest "not measured") instead.
# Because the flag value is spliced into the command string, it is part of the action KEY: observe
# and default builds cache as DISTINCT actions — a default build can never serve a stale measured
# peak, and an observe build re-measures rather than reusing a default 0.
ObserveInfo = provider(doc = "Τ·mem·observe·clean flag state", fields = ["enabled"])

def _observe_impl(ctx):
    return [ObserveInfo(enabled = ctx.build_setting_value)]

observe_setting = rule(implementation = _observe_impl, build_setting = config.bool(flag = True))

# Τ·mem (RESERVE+LEARN) — declare each sweep's memory so Bazel's local scheduler bounds CONCURRENT
# sweeps against --local_ram_resources (default HOST_RAM*.67) — PORTABLE memory-bounding for
# constrained / non-zswap machines, the substrate-membudget pool gone Bazel-native (NOT for this dev
# box, which zswap handles; for the general case).  resource_set MUST be a top-level def (Bazel
# forbids a closure), so the reservation is one top-level fn PER POW2 BUCKET; the bib generator
# resolves a claim's bucket down a (project,resolution,claim) specificity ladder (= the Ω·config
# ladder) and passes it as the `mem` attr.  mem=0 means "unmeasured" → the cold-start floor by
# resolution (a def sweep, project+engine mutation, is far heavier than a file sweep).  The learned
# layer (Τ·mem·observe → mem.json) overrides these floors per (project,resolution).
def _rs_128(_os, _inputs):
    return {"memory": 128}

def _rs_256(_os, _inputs):
    return {"memory": 256}

def _rs_512(_os, _inputs):
    return {"memory": 512}

def _rs_1024(_os, _inputs):
    return {"memory": 1024}

def _rs_2048(_os, _inputs):
    return {"memory": 2048}

def _rs_4096(_os, _inputs):
    return {"memory": 4096}

def _rs_768(_os, _inputs):
    return {"memory": 768}

# bucket (MB) → its top-level reservation fn.  Learned buckets are pure pow2 (mem_learn clamps to
# [128,4096]); 768 is the file cold-start floor only.  Add a level here if the distribution grows one.
_RS = {128: _rs_128, 256: _rs_256, 512: _rs_512, 1024: _rs_1024, 2048: _rs_2048, 4096: _rs_4096, 768: _rs_768}

def _calc_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    c = ctx.actions.declare_file(ctx.label.name + ".calc.json")
    p = ctx.actions.declare_file(ctx.label.name + ".peak")
    res = (" --resolution " + ctx.attr.resolution) if ctx.attr.resolution else ""
    # Τ·mem — the learned bucket (via the bib generator's ladder), or the cold-start floor by
    # resolution when unmeasured (mem == 0).
    bucket = ctx.attr.mem if ctx.attr.mem else (2048 if ctx.attr.resolution == "def" else 768)
    # Τ·mem·observe·clean — read the cgroup peak ONLY when observing (per-action cgroup ⇒ tree-accurate);
    # otherwise write a clean 0.  The branch makes the flag part of the action key (see ObserveInfo).
    if ctx.attr._observe[ObserveInfo].enabled:
        peak = " ; cat /sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup)/memory.peak > " + p.path + \
               " 2>/dev/null || echo 0 > " + p.path
    else:
        peak = " ; echo 0 > " + p.path
    ctx.actions.run_shell(
        outputs = [c, p],
        inputs = depset(ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + 'export PAPERKIT_ROOT="$PWD"; ' +
                  '"$(command -v python3)" paperkit/discriminate.py --only ' + ctx.attr.claim +
                  " --calc" + res + " " + ctx.attr.project + " > " + c.path + peak,
        mnemonic = "PkCalc",
        progress_message = "Ζ·calc " + ctx.label.name,
        # Τ·mem — bound concurrent sweeps against --local_ram_resources (Bazel-native, portable);
        # the reservation is the learned/floor bucket resolved above.
        resource_set = _RS[bucket],
    )
    # peak in a SEPARATE output group so consumers (verdict/grade/cohere) still see only the calc
    # record; the learned-mem manifest (Τ·mem·learn) reads the "peak" group.
    return [DefaultInfo(files = depset([c])), OutputGroupInfo(peak = depset([p]))]

pk_calc = rule(
    implementation = _calc_impl,
    doc = "The per-claim CALCULATION (one mutation sweep) → {claim, baseline, sens}; the cached measurement.",
    toolchains = [_PY],
    attrs = {
        "claim": attr.string(mandatory = True),
        "project": attr.string(mandatory = True),
        "resolution": attr.string(default = "", doc = "def = per-definition fingerprint (for emergence); else file"),
        "mem": attr.int(default = 0, doc = "Τ·mem learned reservation (MB, a pow2 bucket in _RS); 0 = unmeasured → cold-start floor by resolution"),
        "data": attr.label_list(allow_files = True),
        "_observe": attr.label(default = "@@//tools:observe"),
    },
)

# Τ·mem·learn — the manifest as a Bazel ACTION (orchestration → Bazel, not a hand-run): aggregate
# the `peak` output group of every calc in this project → mem.json, the projection consumed by the
# bib generator's reservation ladder.  Built under --config=memobserve in a clean output base
# (cold ⇒ real, cgroup-isolated peaks); mem_learn.py drops un-isolated reads, so a misrun yields an
# empty manifest, never a wrong one.  An ON-DEMAND projection (like report/, setup/) — the 44-min
# observe is too costly to hook-gate, and a stale mem.json is benign (a floor-bounded perf hint).
def _mem_learn_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    out = ctx.actions.declare_file("mem.json")
    peaks = []
    for t in ctx.attr.calcs:
        peaks += t[OutputGroupInfo].peak.to_list()
    ctx.actions.run_shell(
        outputs = [out],
        inputs = depset([ctx.file._tool] + peaks, transitive = [py.files]),
        command = _pypath(py) + '"$(command -v python3)" ' + ctx.file._tool.path + " " +
                  " ".join([p.path for p in peaks]) + " > " + out.path,
        mnemonic = "PkMemLearn",
        progress_message = "Τ·mem·learn " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([out]))]

pk_mem_learn = rule(
    implementation = _mem_learn_impl,
    doc = "Τ·mem·learn — project a per-project mem.json from the calcs' observed cgroup peaks.",
    toolchains = [_PY],
    attrs = {
        "calcs": attr.label_list(mandatory = True, doc = "every pk_calc in the project (its peak output group is aggregated)"),
        "_tool": attr.label(default = "//tools:mem_learn.py", allow_single_file = True),
    },
)

# Ζ·mutant (PREPARATION) — emit ONE mutated module as a Bazel artifact: `site`'s def-body → raise,
# the rest byte-identical (the pure paperkit/mutate.py transform).  Per (module, site) and
# CLAIM-INDEPENDENT, so Bazel generates it once and SHARES it across every claim whose check tests
# that mutation; an edit to one module invalidates only its own mutated modules.  pk_eval then runs
# a check with this module shadowing the real one on PYTHONPATH (the EVALUATION half).
def _mutate_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    o = ctx.actions.declare_file(ctx.label.name + ".mutated.py")
    ctx.actions.run_shell(
        outputs = [o],
        inputs = depset(ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + '"$(command -v python3)" paperkit/mutate.py ' +
                  ctx.attr.module + " '" + ctx.attr.site + "' > " + o.path,
        mnemonic = "PkMutate",
        progress_message = "Ζ·mutate " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([o]))]

pk_mutate = rule(
    implementation = _mutate_impl,
    doc = "Ζ·mutant preparation — emit one mutated module (site's body→raise) as a cached, claim-independent artifact.",
    toolchains = [_PY],
    attrs = {
        "module": attr.string(mandatory = True, doc = "path of the .py module to mutate, e.g. paperkit/grader.py"),
        "site": attr.string(mandatory = True, doc = "the def-site qualname whose body is replaced"),
        "data": attr.label_list(allow_files = True, doc = "the staged files (mutate.py + the module)"),
    },
)

# Ζ·pyc — compile one .py to its .pyc BUILD ARTIFACT (the .o-analog), via tools/pyc.py.  PEP 552
# UNCHECKED_HASH ⇒ content-addressed (no mtime → byte-reproducible, cacheable) + authoritative (the
# runtime never rechecks the source, so a mutated .pyc over an unchanged .py runs the mutation).  The
# compile is a BUILD step here, not an import-time side effect; pk_eval runs off these .pyc, swapping
# the one mutated module's .pyc rather than recompiling the engine on every counterfactual.
# Ξ·dag — a module's TRANSITIVE .pyc closure: itself ∪ the closures of the modules it imports.  The
# build DAG is a projection of the engine import DAG (paperkit/dag.bzl, AST-derived): a consumer that
# stages a module's `closure` gets exactly that module's dependency cone, not the flat engine.
PycInfo = provider(
    doc = "Ξ·dag — the transitive closure of a compiled module (itself ∪ its imports' closures), on " +
          "BOTH paths: .pyc (the import path) and .py (findability / read_text / CLI subprocess entry).",
    fields = {
        "pyc": "depset of .pyc File — this module plus every module it transitively imports",
        "py": "depset of .py File — the same module set as source (read_text, main-script spawn, unlink target)",
    },
)

def _pyc_impl(ctx):
    o = ctx.actions.declare_file(ctx.label.name + ".pyc")
    # Compile with the SANDBOX python (`command -v`, NOT the staged toolchain) — it MUST be the same
    # interpreter pk_eval runs, or the .pyc magic/cache-tag won't match and Python silently recompiles
    # from source (every counterfactual then reads baseline → no flip).  So //paperkit:pyc is built
    # under the eval's config (--config=mutant ⇒ host python; OCI ⇒ image python) and matches it.
    ctx.actions.run_shell(
        outputs = [o],
        inputs = depset([ctx.file._tool, ctx.file.src]),
        command = '"$(command -v python3)" ' + ctx.file._tool.path + " " + ctx.file.src.path + " " + o.path,
        mnemonic = "PkPyc",
        progress_message = "Ζ·pyc " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([o])), PycInfo(
        pyc = depset([o], transitive = [d[PycInfo].pyc for d in ctx.attr.deps]),
        py = depset([ctx.file.src], transitive = [d[PycInfo].py for d in ctx.attr.deps]),
    )]

pk_pyc = rule(
    implementation = _pyc_impl,
    doc = "Ζ·pyc — compile one .py to its content-addressed .pyc build artifact (UNCHECKED_HASH).",
    attrs = {
        "src": attr.label(allow_single_file = [".py"], mandatory = True, doc = "the .py module to compile"),
        "deps": attr.label_list(providers = [PycInfo], doc = "Ξ·dag — the modules this one imports (paperkit/dag.bzl)"),
        "_tool": attr.label(default = "//tools:pyc.py", allow_single_file = True),
    },
)

# Ζ·mutant·eval — run a claim's check against the engine with ONE module mutated, as a NORMAL action
# under --experimental_use_hermetic_linux_sandbox (hardlinks + chroot, so claims.py's resolve() can't
# escape the sandbox to source — the standard sandbox symlinks, which let it escape).  Overwrite the
# mutated module in place: `rm` removes the sandbox's hardlink (never the source inode), `cp` writes
# the mutant.  flipped = the check exits non-zero (the mutation broke the claim's assertion).
def _eval_impl(ctx):
    o = ctx.actions.declare_file(ctx.label.name + ".eval.json")
    mpy = ctx.file.mutated_py
    mpyc = ctx.file.mutated_pyc
    # The eval logic lives in tools/eval.py (a real script, not a shell blob in a string); here we
    # only stage its inputs and pass args.  Ξ·dag·eval — stage the CELL's transitive CLOSURE (this
    # check's PycInfo cone: the modules it imports, per closure.py — fixture capability imports are
    # ordinary IMPORT roots since Μ·kernel·fixture·split), NOT
    # the flat engine — so editing a module invalidates only the cells whose closure contains it.  The
    # engine RUNS OFF its .pyc (Ζ·pyc); the .py side is for findability / read_text / main-script spawn.
    # `"$(command -v python3)"` invokes the interpreter by ABSOLUTE path so eval.py's sys.executable
    # is populated — the check re-spawns the projector as [sys.executable, …], which execs '' (a
    # spurious flip) under bare `python3`.  No toolchain ⇒ command -v resolves the sandbox/OCI python.
    closure_pyc = depset(transitive = [t[PycInfo].pyc for t in ctx.attr.closure])
    closure_py = depset(transitive = [t[PycInfo].py for t in ctx.attr.closure])
    # Ζ·mutant·struct·node-kinds — a FILE cell (site = file+:/file-:) mutates no module: it toggles a
    # path in the sandbox, so it stages no mutant .py/.pyc and passes no --module/--mutant (eval.py
    # branches on the site prefix).  A .py cell passes them as before.
    mut = [ctx.file._tool] + ([mpy, mpyc] if mpy else [])
    marg = (" --module " + ctx.attr.module + " --mutant-py " + mpy.path +
            " --mutant-pyc " + mpyc.path) if mpy else ""
    # A CONTENT cell (site = content-:/content+:) toggles a substring in the staged file at
    # `content_path`.  Deliver the substring as a build artifact (ctx.actions.write) rather than a
    # shell arg — arbitrary quotes/parens/colons, never escaped through the command string.
    carg = ""
    if ctx.attr.content_path:
        cf = ctx.actions.declare_file(ctx.label.name + ".content.txt")
        ctx.actions.write(cf, ctx.attr.content_text)
        mut = mut + [cf]
        carg = " --content-path " + ctx.attr.content_path + " --content-textfile " + cf.path
    ctx.actions.run_shell(
        outputs = [o],
        inputs = depset(mut + ctx.files.project + [ctx.file._sched], transitive = [closure_pyc, closure_py]),
        # Ζ·sched-batch·phase2 — each grid cell self-tunes at exec (SCHED_BATCH + nice 19 + 100ms
        # slice), so concurrent cells run long uninterrupted stretches instead of preempting each
        # other every ~2.8ms (kills ctx-switch AND, under zswap, the refault codec-CPU thrash).
        # Per-cell = thread-independent (the durable fix Phase 1's server-tune could not reach).
        command = '"' + ctx.file._sched.path + '" -- "$(command -v python3)" ' + ctx.file._tool.path +
                  " --engine-dir paperkit" + marg + carg +
                  " --check " + ctx.attr.check + " --claim " + ctx.attr.claim +
                  " --site '" + ctx.attr.site + "' --out " + o.path,
        mnemonic = "PkEval",
        progress_message = "Ζ·eval " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([o]))]

pk_eval = rule(
    implementation = _eval_impl,
    doc = "Ζ·mutant evaluation — a claim's check run off the engine .pyc with one module mutated on BOTH paths → {claim, site, flipped}.",
    attrs = {
        "claim": attr.string(mandatory = True, doc = "the claim key (the check's {target})"),
        "check": attr.string(mandatory = True, doc = "the claim-witness script, exec-relative (paper/checks/claims.py, checks/readme.py) — the project's [checks.claim] cmd, NOT hardcoded"),
        "site": attr.string(mandatory = True, doc = "the site label: a def-site/import spec for a .py cell, or file+:/file-:<path> for a file cell"),
        "module": attr.string(default = "", doc = "the engine module path mutated, e.g. paperkit/bib.py (empty for a file cell)"),
        "mutated_py": attr.label(allow_single_file = [".py"], doc = "the mutated module SOURCE (pk_mutate; identity for ∅) — the script-run path; absent for a file cell"),
        "mutated_pyc": attr.label(allow_single_file = [".pyc"], doc = "the mutated module BYTECODE (pk_pyc of it) — the import path; absent for a file cell"),
        "closure": attr.label_list(providers = [PycInfo], mandatory = True, doc = "Ξ·dag·eval — the check's closure ROOTS (pk_pyc targets, closure.py); PycInfo expands the transitive .py/.pyc cone"),
        "project": attr.label_list(allow_files = True, doc = "the paper project files"),
        "content_path": attr.string(default = "", doc = "a content cell's target file (its substring toggled in the sandbox); empty for a .py/file cell"),
        "content_text": attr.string(default = "", doc = "the substring a content cell drops/injects — delivered via ctx.actions.write, so any chars are safe"),
        "_tool": attr.label(default = "//tools:eval.py", allow_single_file = True),
        "_sched": attr.label(default = "//tools:sched-batch-bin", allow_single_file = True, cfg = "exec"),
    },
)

# Ζ·mutant·sens — aggregate a claim's per-site pk_eval {flipped} records → its SENSITIVITY set (the
# sites whose mutation flips the check).  The Bazel-graph counterpart of grader.sensitivity: the
# fanout (one pk_eval per site) IS the graph; this reads the results.  A cheap LOCAL action.  The
# `baseline` is the ∅-mutation eval (the identity point of the same sweep) — its flipped=false is the
# harness's validity witness; sens.py FAILS this action if it flipped (a degenerate all-flip ⇒ broken
# harness, not a real sens set).
def _sens_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    o = ctx.actions.declare_file(ctx.label.name + ".sens.json")
    evals = " ".join([e.path for e in ctx.files.evals])
    ctx.actions.run_shell(
        outputs = [o],
        inputs = depset([ctx.file._tool, ctx.file.baseline] + ctx.files.evals, transitive = [py.files]),
        command = _pypath(py) + '"$(command -v python3)" ' + ctx.file._tool.path +
                  " --baseline " + ctx.file.baseline.path + " " + evals + " > " + o.path,
        mnemonic = "PkSens",
        progress_message = "Ζ·sens " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([o]))]

pk_sens = rule(
    implementation = _sens_impl,
    doc = "Ζ·mutant — aggregate per-(claim, site) {flipped} eval records → the claim's sensitivity set.",
    toolchains = [_PY],
    attrs = {
        "evals": attr.label_list(allow_files = True, mandatory = True, doc = "the pk_eval records for one claim"),
        "baseline": attr.label(allow_single_file = True, mandatory = True, doc = "the ∅-mutation eval — must be flipped=false"),
        "_tool": attr.label(default = "//tools:sens.py", allow_single_file = True),
    },
)

# Ζ·mutant — ONE (claim, def-site) probe as a Bazel action: mutate exactly `site` and report
# whether it flips the check.  This LIFTS the def-sweep's in-process group-testing fanout into
# Bazel's graph (parallel + per-site cached); pk_sens aggregates the {flipped} records into the
# `sens` fingerprint pk_calc's def sweep computes in-process today.  One check-run, hermetic in its
# own sandbox copy (the per-mutant overhead the spike measures).
def _mutant_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    o = ctx.actions.declare_file(ctx.label.name + ".mutant.json")
    ctx.actions.run_shell(
        outputs = [o],
        inputs = depset(ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + 'export PAPERKIT_ROOT="$PWD"; ' +
                  '"$(command -v python3)" paperkit/discriminate.py --only ' + ctx.attr.claim +
                  " --mutant '" + ctx.attr.site + "' " + ctx.attr.project + " > " + o.path,
        mnemonic = "PkMutant",
        progress_message = "Ζ·mutant " + ctx.label.name,
        resource_set = _RS[512],
    )
    return [DefaultInfo(files = depset([o]))]

pk_mutant = rule(
    implementation = _mutant_impl,
    doc = "Ζ·mutant — one (claim, def-site) mutation probe → {claim, site, flipped}; the sweep's atom as a Bazel action.",
    toolchains = [_PY],
    attrs = {
        "claim": attr.string(mandatory = True),
        "project": attr.string(mandatory = True),
        "site": attr.string(mandatory = True, doc = "the mutation-site label (path or path::qualname)"),
        "data": attr.label_list(allow_files = True),
    },
)

# Ζ·emerge·gate — cheap coherence READING (verdict.py cohere): run coherence.py over the cached calc
# records (no re-sweep), assert grounding soundness (0 genuine misses), emit the verdict.  The ∂²
# faces gated as a reading over the calculation.
def _cohere_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = ctx.actions.declare_file(ctx.label.name + ".cohere.json")
    calcs = " ".join([c.path for c in ctx.files.calcs])
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset([ctx.file._tool] + ctx.files.calcs + ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + '"$(command -v python3)" ' + ctx.file._tool.path +
                  " cohere cohere " + ctx.attr.project + " " + v.path + " " + calcs,
        mnemonic = "PkCohere",
        progress_message = "Ζ·emerge·gate cohere " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([v]))]

pk_cohere = rule(
    implementation = _cohere_impl,
    doc = "Ζ·emerge·gate — coherence ∂² as a cheap READING over cached calcs; verdict pass iff grounding sound.",
    toolchains = [_PY],
    attrs = {
        "calcs": attr.label_list(allow_files = True, mandatory = True, doc = "the cached def-resolution calc records"),
        "project": attr.string(mandatory = True),
        "data": attr.label_list(allow_files = True),
        "_tool": attr.label(default = "//tools:verdict.py", allow_single_file = True),
    },
)

# A cheap READING of a calc record (tools/verdict.py): the verdict is the measured baseline.
def _verdict_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = ctx.actions.declare_file(ctx.label.name + ".verdict.json")
    calc = ctx.file.calc
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset([ctx.file._tool, calc], transitive = [py.files]),
        command = _pypath(py) + '"$(command -v python3)" ' + ctx.file._tool.path +
                  " calc verdict " + calc.path + " " + v.path,
        mnemonic = "PkVerdict",
        progress_message = "Ζ·calc verdict " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([v]))]

pk_verdict = rule(
    implementation = _verdict_impl,
    doc = "A cheap READING of a calc record: the verdict is the measured baseline.",
    toolchains = [_PY],
    attrs = {
        "calc": attr.label(allow_single_file = True, mandatory = True),
        "_tool": attr.label(default = "//tools:verdict.py", allow_single_file = True),
    },
)

# Ζ·canary — the harness's POSITIVE CONTROL verdict: the guaranteed-flip pk_eval MUST have
# flipped, the ∅ identity MUST NOT.  The dual of pk_sens's ∅-baseline guard (that catches a
# harness flipping EVERYTHING; this catches one flipping NOTHING — the silently-degraded-sandbox
# class, twice demonstrated by the processwrapper false-indeterminate incidents).  verdict.py
# owns the record; failure is a NAMED harness error, never a silent green.
def _canary_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    v = ctx.actions.declare_file(ctx.label.name + ".verdict.json")
    ctx.actions.run_shell(
        outputs = [v],
        inputs = depset([ctx.file._tool, ctx.file.pos, ctx.file.nul], transitive = [py.files]),
        command = _pypath(py) + '"$(command -v python3)" ' + ctx.file._tool.path +
                  " canary " + ctx.file.pos.path + " " + ctx.file.nul.path + " " + v.path,
        mnemonic = "PkCanary",
        progress_message = "Ζ·canary " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([v]))]

pk_canary = rule(
    implementation = _canary_impl,
    doc = "Ζ·canary — the harness positive control: guaranteed-flip eval flipped AND ∅ identity did not, else a LOUD named failure.",
    toolchains = [_PY],
    attrs = {
        "pos": attr.label(allow_single_file = True, mandatory = True, doc = "the guaranteed-flip pk_eval record (MUST be flipped)"),
        "nul": attr.label(allow_single_file = True, mandatory = True, doc = "the ∅ identity pk_eval record (MUST NOT be flipped)"),
        "_tool": attr.label(default = "//tools:verdict.py", allow_single_file = True),
    },
)

def _grade_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    g = ctx.actions.declare_file(ctx.label.name + ".grade.json")
    calc = ctx.file.calc
    ctx.actions.run_shell(
        outputs = [g],
        inputs = depset([calc] + ctx.files.data, transitive = [py.files]),
        command = _pypath(py) + '"$(command -v python3)" tools/read_grade.py ' + calc.path + " > " + g.path,
        mnemonic = "PkGradeRead",
        progress_message = "Ζ·calc grade " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([g]))]

pk_grade = rule(
    implementation = _grade_impl,
    doc = "A cheap READING of a calc record: the grade via grader._grade_from_sens (no re-sweep).",
    toolchains = [_PY],
    attrs = {
        "calc": attr.label(allow_single_file = True, mandatory = True),
        "data": attr.label_list(allow_files = True),
    },
)
