"""pk_dists -- the mtools dists paperkit pins, built to WHEELS at the pinned sha (paperkit:W315).

Bazel cells run the hermetic rules_python interpreter with no third-party site-packages, so a
module that imports `mikemol.*` cannot run there until the dists are DELIVERED.  This repository
rule is the delivery's source: it reads the pins from pyproject.toml (the one owner of the sha --
no copy lives in a .bzl), clones mtools at that sha, and builds every pinned dist with mtools' own
`mikemol-wheel` verb (mtools:W992), which is deterministic per sha.

The result is one filegroup of wheels (`@pk_dists//:wheels`) that `cell_venv(deps = ...)` installs.

HOST-DEPENDENT AT FETCH, ON PURPOSE AND SAID SO: the build runs the host's `mikemol-wheel` and
`uv`.  What makes the OUTPUT trustworthy is not the build's hermeticity but that the wheels are
content-stable per sha, so the fetched set can be compared with a recorded digest list.
"""

_PIN = "git+https://github.com/mikemol/mtools.git@"

def _pins(text):
    """(sha, [dist, ...]) from the mikemol-* lines of pyproject.toml; fail unless ONE sha."""
    shas = {}
    dists = []
    for line in text.splitlines():
        if _PIN not in line or "#subdirectory=" not in line:
            continue
        sha = line.split(_PIN, 1)[1].split("#", 1)[0]
        dist = line.split("#subdirectory=", 1)[1].split(";", 1)[0].split('"', 1)[0].strip()
        shas[sha] = True
        # a dist is named by the dev group AND by [project].dependencies (atomicwrite): once
        if dist not in ("hooks", "pathsforward") and dist not in dists:
            dists.append(dist)
    if len(shas) != 1:
        fail("pk_dists: pyproject pins mtools at %d different shas (%s); the mikemol namespace must resolve from ONE" % (len(shas), ", ".join(shas.keys())))
    return shas.keys()[0], dists

def _impl(ctx):
    sha, dists = _pins(ctx.read(ctx.attr.pyproject))
    ctx.report_progress("pk_dists: cloning mtools at " + sha[:7])
    # ⚑ GIT'S REPOSITORY-SELECTING ENVIRONMENT IS UNSET FOR THESE CALLS.  Measured 2026-10-11: run
    # from the pre-commit hook, GIT_DIR/GIT_INDEX_FILE/GIT_WORK_TREE name PAPERKIT's repository, so
    # `git -C mtools checkout` operated on paperkit itself (git refused only because the tree was
    # dirty: "local changes to .bazelrc, MODULE.bazel... would be overwritten").  A fetch rule that
    # inherits the caller's repository is aimed at the wrong tree; `env -u` makes it its own.
    unset = ["env", "-u", "GIT_DIR", "-u", "GIT_INDEX_FILE", "-u", "GIT_WORK_TREE", "-u", "GIT_OBJECT_DIRECTORY", "-u", "GIT_COMMON_DIR"]
    for argv in (
        unset + ["git", "init", "-q", "mtools"],
        unset + ["git", "-C", "mtools", "fetch", "-q", "--depth=1", "https://github.com/mikemol/mtools.git", sha],
        unset + ["git", "-C", "mtools", "checkout", "-q", "FETCH_HEAD"],
    ):
        r = ctx.execute(argv)
        if r.return_code != 0:
            fail("pk_dists: %s failed: %s" % (" ".join(argv), r.stderr))
    # The verb ships in mikemol-hooks, a dev dependency, so it lives in the workspace venv rather
    # than on the PATH a bazel client happens to carry (measured: a bare-PATH client failed here).
    tool = ctx.which("mikemol-wheel") or ctx.path(str(ctx.workspace_root) + "/.venv/bin/mikemol-wheel")
    if not tool.exists:
        fail("pk_dists: mikemol-wheel is on neither PATH nor .venv/bin (uv sync installs mikemol-hooks)")
    ctx.watch(tool)
    r = ctx.execute(unset + [tool] + dists +["--sha", sha, "--out", str(ctx.path("wheels")), "--mtools", str(ctx.path("mtools"))], timeout = 900)
    if r.return_code != 0:
        fail("pk_dists: mikemol-wheel failed: " + r.stderr)
    # ⚑ EXTRACTED INTO ONE TREE, NOT LEFT AS ZIPS ON PYTHONPATH.  Measured 2026-10-11: CPython 3.14
    # merges the `mikemol` namespace across zip entries, the cells' hermetic CPython 3.13 does NOT
    # (ModuleNotFoundError: mikemol with four wheels on PYTHONPATH).  A probe run on the host's
    # python proved the wrong thing; a directory merges its namespace on every version.
    for whl in ctx.path("wheels").readdir():
        if whl.basename.endswith(".whl"):
            # extract() decides the format from the SUFFIX and a wheel's is not one it knows, so the
            # wheel is read through a .zip name (it IS a zip) rather than shelling out to unzip.
            zipped = "zips/" + whl.basename[:-len(".whl")] + ".zip"
            ctx.symlink(whl, zipped)
            ctx.extract(archive = zipped, output = "site")
    ctx.file("site/PK_DISTS_SITE", "the directory holding this file is the merged site tree\n")
    ctx.file("BUILD.bazel", 'filegroup(name = "wheels", srcs = glob(["wheels/*.whl"]), visibility = ["//visibility:public"])\n' +
                            'filegroup(name = "site", srcs = glob(["site/**"]), visibility = ["//visibility:public"])\n')
    ctx.file("manifest.jsonl", r.stdout)

pk_dists = repository_rule(
    implementation = _impl,
    attrs = {"pyproject": attr.label(allow_single_file = True, mandatory = True)},
    environ = ["PATH"],
)
