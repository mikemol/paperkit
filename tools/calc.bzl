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
# ⚑ START TINY.  The ladder used to bottom at 128MB and the def floor was 2048 — a number chosen
# high "to be safe", which nothing ever pushed back on.  Measured: a def-sweep CELL peaked at
# 2,981,888 bytes (2.8MB), a ~700x over-reservation, because the floor was sized as if a cell were
# the whole sweep.  An over-reservation is invisible: it never fails, it just idles cores (this box
# ran 3 concurrent def cells where the budget allowed ~48).  An UNDER-reservation is loud — the cap
# kills the cell, the failure names the cell, and the next pass raises it.  So the ladder starts
# where measurements actually live and grows on evidence, rather than starting where nothing can
# fail and never learning anything.
def _rs_4(_os, _inputs):
    return {"memory": 4}

def _rs_8(_os, _inputs):
    return {"memory": 8}

def _rs_16(_os, _inputs):
    return {"memory": 16}

def _rs_32(_os, _inputs):
    return {"memory": 32}

def _rs_64(_os, _inputs):
    return {"memory": 64}

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
_RS = {4: _rs_4, 8: _rs_8, 16: _rs_16, 32: _rs_32, 64: _rs_64, 128: _rs_128, 256: _rs_256, 512: _rs_512, 1024: _rs_1024, 2048: _rs_2048, 4096: _rs_4096, 768: _rs_768}

def _cap_prefix(cap_path, bucket):
    """Ζ·cell·cap — an OPT-IN per-cell memory ceiling, or "" where none is configured.

    resource_set is a SCHEDULING HINT: it tells Bazel how many cells may run at once and bounds
    none of them.  Measured: paperkit's cells share ONE cgroup with memory.max=max, so a runaway
    cell has no boundary and the only backstop is the host OOM killer, which picks by heuristic
    rather than by culprit.  A real ceiling makes the kill attributable — and turns an over-run
    into a DATUM at a rung (the event Ζ·mem·climb needs) instead of a box-wide degradation.

    VENDORED, so the cap is paperkit's own and needs no opt-in.  tools/cgroup-scope is a copy of
    substrate's (251 lines, no substrate-internal references), taken because these cells run on
    arbitrary machines and depending on a sibling repo by absolute path would trade the PORTABLE
    memory-bounding Τ·mem exists to provide for a build that only works beside substrate.

    It DEGRADES rather than failing: `cgroup-scope` refuses loudly where the memory controller is
    not delegated (its own `probe` answers that with no side effects), so a machine without cgroup
    v2 delegation must still run the cell.  Hence `|| exec "$@"` — the cap is a safety property,
    never a precondition for grading a document.

    Ζ·cell·cap·swap — the capper must also zero swap.  Measured on this box: a 64MB alloc under an
    8MB memory.max gave `max 678, oom_kill 0` and SUCCEEDED, because the kernel compressed into
    zram instead of killing.  memory.max alone is a RECLAIM threshold; only memory.swap.max=0
    makes it a boundary.  cgroup-scope sets both (verified: 200MB under 64MB → exit 137)."""
    # ⚑ THE DEGRADATION IS A `probe` GUARD, not `|| exec`.  An earlier version of this docstring
    # claimed the cell degrades via `|| exec "$@"` and the prefix implemented no fallback at all:
    # `cgroup-scope` _die()s where no ancestor delegates `memory`, so on such a machine EVERY cell
    # failed and no document could be graded.  Measured — a sweep under a konsole scope (which
    # holds processes, so cannot delegate) died with "no usable memory controller" and produced no
    # output.  A cap is a SAFETY property; it must never become a precondition for grading.
    #
    # `|| exec` cannot work here: cgroup-scope may die AFTER partially setting up, and re-exec'ing
    # the payload would run it twice.  So ask FIRST — `probe` answers "will this work here" with
    # no side effects and exit 0/non-0, which is exactly the precondition test it was built for.
    #
    # PAPERKIT_CELL_CAP=0 disables the cap outright (a bisect, or a machine that wants the old
    # behaviour); the `:-` default names the vendored tool.
    # Resolved at EXEC time into a shell VARIABLE, then used as a prefix.  `probe` decides once
    # per cell whether the capper is usable; where it is not, PK_CAP is empty and the command
    # runs bare — the same command either way, so the action key does not change with the box.
    return ('PK_CAP=""; [ "${PAPERKIT_CELL_CAP:-x}" != 0 ] && %s probe >/dev/null 2>&1 && ' +
            'PK_CAP="%s %d --cpu-weight ${PAPERKIT_CELL_WEIGHT:-100} --"; $PK_CAP ') % (
                cap_path, cap_path, bucket)


def _peak_snippet(observing, path):
    """Ζ·mem·def·blind — the cgroup-peak read, as ONE owner with two callers (pk_calc and pk_eval).

    Τ·mem·observe·honest — an UNREADABLE peak must not become a ZERO.  `2>/dev/null || echo 0`
    collapsed three distinct causes onto one value: observe-off (a deliberate clean 0), a real
    cgroup that never charged a page, and a read that FAILED.  A consumer cannot tell them apart,
    so a check that never measured anything looks identical to one that measured zero.  (Cost,
    measured: 170 cells read 0 and the diagnosis was a kernel capability gap; the real cause was a
    cached non-observe write.)  So: the read's own failure is NAMED.

    Lifted here because the def-sweep needed the same read.  The def resolution is the EXPENSIVE
    one — 18-25 minute cells — and it was the one resolution with no measurement channel at all:
    pk_eval returned DefaultInfo only, so `mem_learn` aggregated file-calcs and the `def` bucket
    could only ever be a cold-start floor.  A second copy of this snippet would put the
    `unavailable:` vocabulary in two places, drifting from the single reader that parses it."""
    if observing:
        return (" ; { P=$(cut -d: -f3 /proc/self/cgroup); F=/sys/fs/cgroup$P/memory.peak; " +
                "if [ ! -e \"$F\" ]; then echo unavailable:absent; " +
                "elif ! cat \"$F\" 2>/dev/null; then echo unavailable:unreadable; fi; } > " + path)
    return " ; echo 0 > " + path


def _calc_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    c = ctx.actions.declare_file(ctx.label.name + ".calc.json")
    p = ctx.actions.declare_file(ctx.label.name + ".peak")
    res = (" --resolution " + ctx.attr.resolution) if ctx.attr.resolution else ""
    # Τ·mem — the learned bucket (via the bib generator's ladder), or the cold-start floor by
    # resolution when unmeasured (mem == 0).
    # Ζ·mem·climb — the cold-start floor is the ladder's BOTTOM, not a guess sized to never fail.
    # An over-reservation is silent (it idles cores; this box ran 3 def cells where the budget
    # allowed ~48) while an under-reservation is LOUD: the cap kills the cell, the failure names
    # it, and cgroup-scope's retry doubles until it fits.  Measured: a def cell peaks at 2.8MB
    # against the old 2048 floor — a ~700x guess nothing could ever falsify.
    bucket = ctx.attr.mem if ctx.attr.mem else 4
    # Τ·mem·observe·clean — read the cgroup peak ONLY when observing (per-action cgroup ⇒ tree-accurate);
    # otherwise write a clean 0.  The branch makes the flag part of the action key (see ObserveInfo).
    peak = _peak_snippet(ctx.attr._observe[ObserveInfo].enabled, p.path)
    ctx.actions.run_shell(
        outputs = [c, p],
        inputs = depset(ctx.files.data + [ctx.file._cap], transitive = [py.files]),
        command = _pypath(py) + 'export PAPERKIT_ROOT="$PWD"; ' + _cap_prefix(ctx.file._cap.path, bucket) +
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
        # Ζ·cell·cap — the vendored capper, staged so the cell can exec it in the sandbox.
        "_cap": attr.label(default = "//tools:cgroup-scope", allow_single_file = True, cfg = "exec"),
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
    # Ζ·mem·def·blind — the def-sweep's cells now carry a peak, like pk_calc's.  Without it the
    # EXPENSIVE resolution was the one with no measurement channel: mem_learn aggregates
    # file-calcs, so `def` could only ever be the cold-start floor (2048MB against a measured
    # ~179MB file cell), and no amount of cold observing could correct it.
    pk = ctx.actions.declare_file(ctx.label.name + ".peak")
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
    mut = ([mpy, mpyc] if mpy else [])
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
        outputs = [o, pk],
        inputs = depset(mut + [ctx.file._cap] + ctx.files.project,
                        transitive = [closure_pyc, closure_py]),
        # ⚑ Ζ·cell·wire — `tools`, NOT `inputs`, AND THE DIFFERENCE IS THE RUNFILES TREE.
        # A first cut staged the launcher and its runfiles FILES through `inputs` and the cell
        # died with `AssertionError: Cannot find .runfiles directory` — a py_binary launcher does
        # not want its dependencies as loose files, it wants the `.runfiles` SYMLINK TREE beside
        # it, which is what makes `from tools import cellargs` resolve by layout.  `tools =`
        # declares an executable dependency and Bazel materialises that tree; `inputs =` declares
        # data and does not.  The same distinction the operator named one layer up: staging is a
        # property the ACTION declares, and declaring it in the wrong field is still not
        # declaring it.
        tools = [ctx.attr._tool[DefaultInfo].files_to_run],
        # Ζ·sched-batch·phase2 — each grid cell self-tunes at exec (SCHED_BATCH + nice 19 + 100ms
        # slice), so concurrent cells run long uninterrupted stretches instead of preempting each
        # other every ~2.8ms (kills ctx-switch AND, under zswap, the refault codec-CPU thrash).
        # Per-cell = thread-independent (the durable fix Phase 1's server-tune could not reach).
        # Ζ·cell·wire — the LAUNCHER is invoked directly.  It was
        # `"$(command -v python3)" tools/eval.py`, which found an interpreter by hand precisely
        # because a bare script has no launcher; a py_binary ships one that sets the interpreter
        # AND the import layout together.  The `sys.executable` requirement the old comment
        # records (the check re-spawns the projector as [sys.executable, …], and bare `python3`
        # left it '' — a spurious flip) is satisfied more strongly: the launcher execs a real
        # absolute interpreter, so there is no `command -v` to resolve differently under OCI.
        command = _cap_prefix(ctx.file._cap.path, ctx.attr.mem if ctx.attr.mem else 4) +
                  ctx.executable._tool.path +
                  " --engine-dir paperkit" + marg + carg +
                  " --check " + ctx.attr.check + " --claim " + ctx.attr.claim +
                  " --site '" + ctx.attr.site + "' --out " + o.path +
                  # Τ·mem·observe·inside — the peak is read BY eval.py, from inside the
                  # cgroup-scope cell, not by a trailing shell statement outside it.  The
                  # `; read-the-peak` form ran AFTER the scope exited and sampled bazel's
                  # sandbox cgroup instead: 4.7MB reported for a cell whose in-scope peak is
                  # 35MB and which OOMs under a 32MB cap.  A sensor outside the actuator it
                  # measures cannot close the loop — it under-reports, the manifest sizes the
                  # cell too small, and the same OOM is re-derived every run.
                  (" --peak " + pk.path if ctx.attr._observe[ObserveInfo].enabled else "") +
                  ("" if ctx.attr._observe[ObserveInfo].enabled else " ; echo 0 > " + pk.path),
        mnemonic = "PkEval",
        progress_message = "Ζ·eval " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([o])), OutputGroupInfo(peak = depset([pk]))]

pk_eval = rule(
    implementation = _eval_impl,
    doc = "Ζ·mutant evaluation — a claim's check run off the engine .pyc with one module mutated on BOTH paths → {claim, site, flipped}.",
    attrs = {
        "claim": attr.string(mandatory = True, doc = "the claim key (the check's {target})"),
        "check": attr.string(mandatory = True, doc = "the claim-witness script, exec-relative (paper/checks/claims.py, checks/readme.py) — the project's [checks.claim] cmd, NOT hardcoded"),
        "site": attr.string(mandatory = True, doc = "the site label: a def-site/import spec for a .py cell, or file+:/file-:<path> for a file cell"),
        # Ζ·mem·def·blind — the observe flag is part of the ACTION KEY (as in pk_calc), so an
        # observe-vs-default cell caches as a distinct action and no stale 0 crosses configs.
        "_observe": attr.label(default = "//tools:observe"),
        # Ζ·cell·cap — the learned reservation, which is also the CEILING the cell runs under.
        "mem": attr.int(default = 0, doc = "Τ·mem learned reservation (MB); 0 = def cold-start floor"),
        "_cap": attr.label(default = "//tools:cgroup-scope", allow_single_file = True, cfg = "exec"),
        "module": attr.string(default = "", doc = "the engine module path mutated, e.g. paperkit/bib.py (empty for a file cell)"),
        "mutated_py": attr.label(allow_single_file = [".py"], doc = "the mutated module SOURCE (pk_mutate; identity for ∅) — the script-run path; absent for a file cell"),
        "mutated_pyc": attr.label(allow_single_file = [".pyc"], doc = "the mutated module BYTECODE (pk_pyc of it) — the import path; absent for a file cell"),
        "closure": attr.label_list(providers = [PycInfo], mandatory = True, doc = "Ξ·dag·eval — the check's closure ROOTS (pk_pyc targets, closure.py); PycInfo expands the transitive .py/.pyc cone"),
        "project": attr.label_list(allow_files = True, doc = "the paper project files"),
        "content_path": attr.string(default = "", doc = "a content cell's target file (its substring toggled in the sandbox); empty for a .py/file cell"),
        "content_text": attr.string(default = "", doc = "the substring a content cell drops/injects — delivered via ctx.actions.write, so any chars are safe"),
        # ⚑ Ζ·cell·wire — THE TOOL IS A py_binary, NOT A FILE, BECAUSE A FILE HAS NO SIBLINGS.
        #
        # This was `//tools:eval.py` with allow_single_file, and MEASURED that is exactly one file:
        #
        #     bazel query 'kind("source file", deps(//tools:eval.py))'   ->   //tools:eval.py
        #
        # So when Ζ·eval·split cut eval.py into cellargs/cellstage/cellcgroup, the sandbox had
        # nothing to import from and every cell would have died at `ModuleNotFoundError: No module
        # named 'tools'`.  The operator named the layer: *the code isn't getting properly staged
        # into the per-cell/action venv* — WHAT A CELL CAN IMPORT IS THE ACTION'S PROPERTY,
        # declared here, not something the script arranges for itself with sys.path at runtime.
        #
        # `py_binary` builds a runfiles tree carrying srcs at their real package paths, so
        # `from tools import cellargs` resolves BY LAYOUT.  `cfg = "exec"` because this runs as a
        # build tool; `executable = True` so ctx.executable._tool is the launcher, which sets up
        # the interpreter and PYTHONPATH itself — which is why the command below no longer needs
        # `"$(command -v python3)"` to find an interpreter by hand.
        "_tool": attr.label(default = "//tools:eval", executable = True, cfg = "exec"),
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

# Μ·sweep·atom — the DECISION-COVERAGE aggregator, the grid twin of grader.decisions_unasserted.
# Reads the flip: cells (condition inversions) and the raise-kind cells (per-arm reach), and reports
# which reached decisions the check never asserts.  A sibling of pk_sens (a cheap LOCAL reading over
# already-built cells), but a SEPARATE rule and tool: a flip: cell can never reach pk_sens (the grid
# partition + sens.py's fail-loud assert), and a raise-kind cell's sens is never confused with
# decision coverage.
def _decisions_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    o = ctx.actions.declare_file(ctx.label.name + ".decisions.json")
    flips = " ".join([e.path for e in ctx.files.flips])
    reach = " ".join([e.path for e in ctx.files.reach])
    ctx.actions.run_shell(
        outputs = [o],
        inputs = depset([ctx.file._tool] + ctx.files.flips + ctx.files.reach, transitive = [py.files]),
        command = _pypath(py) + '"$(command -v python3)" ' + ctx.file._tool.path +
                  " --flips " + flips + " --reach " + reach + " > " + o.path,
        mnemonic = "PkDecisions",
        progress_message = "Μ·decisions " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([o]))]

pk_decisions = rule(
    implementation = _decisions_impl,
    doc = "Μ·sweep·atom — aggregate a claim's flip:/branch: cells → its reached-but-unasserted decisions.",
    toolchains = [_PY],
    attrs = {
        "flips": attr.label_list(allow_files = True, mandatory = True, doc = "the flip: pk_eval records (condition inversions)"),
        "reach": attr.label_list(allow_files = True, mandatory = True, doc = "the raise-kind pk_eval records (per-arm reach)"),
        "_tool": attr.label(default = "//tools:decisions.py", allow_single_file = True),
    },
)

# Μ·sweep·atom — the PROJECT decision-coverage SUMMARY: fold every claim's __decisions record into one
# artifact, so the grid twin is CONSUMED (not emitted-but-inert — the enforcement adversary's finding).
# decision-coverage is an ORTHOGONAL axis, never a grade rung, so this does NOT gate a floor; it makes
# the aggregate REACHABLE + built every commit (a //:hook member), surfacing which reached decisions no
# witness asserts.  A red only on a MALFORMED record (a partition/aggregation regression), never on a
# high unasserted count — the axis reports coverage, it does not fail a build for having a gap.
def _decisions_summary_impl(ctx):
    py = ctx.toolchains[_PY].py3_runtime
    o = ctx.actions.declare_file(ctx.label.name + ".decisions_summary.json")
    recs = " ".join([e.path for e in ctx.files.decisions])
    ctx.actions.run_shell(
        outputs = [o],
        inputs = depset([ctx.file._tool] + ctx.files.decisions, transitive = [py.files]),
        command = _pypath(py) + '"$(command -v python3)" ' + ctx.file._tool.path +
                  " --summary " + recs + " > " + o.path,
        mnemonic = "PkDecisionsSummary",
        progress_message = "Μ·decisions·summary " + ctx.label.name,
    )
    return [DefaultInfo(files = depset([o]))]

pk_decisions_summary = rule(
    implementation = _decisions_summary_impl,
    doc = "Μ·sweep·atom — fold a project's per-claim __decisions records into one reachable coverage summary.",
    toolchains = [_PY],
    attrs = {
        "decisions": attr.label_list(allow_files = True, mandatory = True, doc = "the per-claim __decisions records"),
        "_tool": attr.label(default = "//tools:decisions.py", allow_single_file = True),
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
