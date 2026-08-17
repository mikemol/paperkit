#!/bin/sh
# Ζ·tier·toolchain — the toolchain fingerprint, emitted as Bazel STABLE workspace-status keys.
#
# A `toolchain`-tier check (verb.bzl) runs on the host under a real toolchain (pandoc, veraPDF,
# lualatex, LibreOffice) rather than in the hermetic sandbox — deterministic GIVEN A PINNED
# toolchain, but not hermetic.  Its verdict is only trustworthy if the toolchain it ran under is
# pinned, and it should re-run exactly when that toolchain CHANGES and be cached otherwise.
#
# Bazel's stamping mechanism provides precisely that: a STABLE_ key whose value changes invalidates
# every stamped action that depends on it (`bazel-out/stable-status.txt`), while an unchanged value
# is a cache hit — measured, not assumed (the Ζ·tier·toolchain probe).  So this script emits each
# render-toolchain tool's version as a stable key.  A tool upgrade changes its key → the toolchain
# checks re-run; an unchanged toolchain → they stay cached.
#
# The SAME keys are the fingerprint a downstream consumer needs to trust "which environment proved
# this claim" (the VPAT's per-claim enforcement disclosure): the cache key IS the toolchain digest.
# An ABSENT tool emits `absent` (a stable value) rather than failing — so a box without the toolchain
# has a well-defined fingerprint (and its toolchain checks are honestly "not currently provable"),
# never a broken status command that would abort every build.
#
#   bazel build --stamp --workspace_status_command=tools/toolchain_status.sh …
# (wired in .bazelrc; the script emits `STABLE_TOOLCHAIN_<tool> <version>` lines to stdout).
set -u

# Emit `STABLE_TOOLCHAIN_<name> <version-or-absent>`.  `$2…` is the version command; its FIRST line
# is the fingerprint (version banners are multi-line; the first line carries the version).
emit() {
    name="$1"
    shift
    if command -v "$1" >/dev/null 2>&1; then
        v=$("$@" 2>/dev/null | head -1 | tr -s ' ' | tr -d '\r')
        [ -n "$v" ] || v="present-unversioned"
    else
        v="absent"
    fi
    echo "STABLE_TOOLCHAIN_${name} ${v}"
}

emit PANDOC   pandoc --version
emit VERAPDF  verapdf --version
emit LUALATEX lualatex --version
emit SOFFICE  soffice --version

# veraPDF's PDF/UA verdict is a pure function of its JAR, so its content sha256 is a finer key than
# the banner (a rebuilt-same-version JAR with a different ruleset would otherwise cache-collide).
jar=$(ls "$HOME"/.local/opt/verapdf/bin/cli-*.jar 2>/dev/null | head -1)
if [ -n "$jar" ] && command -v sha256sum >/dev/null 2>&1; then
    echo "STABLE_TOOLCHAIN_VERAPDF_JAR $(sha256sum "$jar" | cut -d' ' -f1)"
else
    echo "STABLE_TOOLCHAIN_VERAPDF_JAR absent"
fi
