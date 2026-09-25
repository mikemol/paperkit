#!/usr/bin/env python3
"""Μ·bnd-genre-emit — the GENERATOR emits `:genres` exactly where a project DECLARES one.

⚑ WHY THIS IS A BOUNDARY AND NOT A UNIT TEST.  `tools/bibtex.bzl` IS the build graph — 1,109
lines of it — and audit finding 1 measured its only claim as `bnd-lint`: three regexes
(`bare-python3`, `printf-json`, `grep-json`) over the TEXT, asserting nothing about what the
generator EMITS.  The generated things are gated ~182 ways; the generator was gated by a grep for
`printf {`.  This is the first claim about its OUTPUT.

WHAT IS ASSERTED, and why each half matters:
  · a project that DECLARES `[genres.X]` gets a `:genres` target       — else the seam is ungated
    again (Ν-F7: `genre.py --check` existed, invoked every declared cmd, and was wired to NOTHING)
  · a project that declares NONE does not                              — else eleven of twelve
    projects carry a check over an empty registry, green by vacuity.  A target that cannot fail is
    the `--without-K` collapse in target form, and this repo refuses that shape everywhere else.

⚑ THE IFF IS THE POINT.  Either half alone is satisfiable by a constant: "always emit" passes the
first, "never emit" passes the second.  Only the biconditional pins the generator's actual rule.

⚑ IT READS THE SOURCES, NOT THE BAZEL CACHE.  `hook_grid.py` is the precedent — it derives what
the generator WOULD emit from `MODULE.bazel`'s tags and compares against `BUILD.bazel`, invoking
no `bazel` and reading no `_bazel_<user>` path.  A witness keyed on an output-base hash is keyed
on one machine's cache layout, and would report a fact about this laptop as a fact about the
generator.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BZL = ROOT / "tools" / "bibtex.bzl"


def wired_projects(module: str) -> dict:
    """{repo_name: project_dir} for every bib.project tag — the projects the generator runs over."""
    out = {}
    for line in module.splitlines():
        if "bib.project(" not in line:
            continue
        name = re.search(r'name\s*=\s*"([^"]+)"', line)
        proj = re.search(r'project\s*=\s*"([^"]+)"', line)
        if name and proj:
            out[name.group(1)] = proj.group(1)
    return out


def declares_genre(project_dir: str) -> bool:
    """Does this project's paper.toml carry a `[genres.<name>]` table?

    Matched at LINE START, the way `_declared_genres` and `_claim_script` both match — a bare
    substring search finds the word inside a `cmd = "…"` string, which is the defect
    `bibtex.bzl:419` records having been measured on library/paper.toml.
    """
    p = (ROOT if project_dir == "." else ROOT / project_dir) / "paper.toml"
    # ⚑ Ζ·genre·stage — AN UNREADABLE TOML IS A CANNOT-RUN, NOT A "DECLARES NONE".
    #
    # This returned False when the file was absent, folding "this project declares no genre" onto
    # "I could not read this project's declaration" — the exact collapse the engine refuses in its
    # own verdicts (resolver.Verdict's UNAVAILABLE) and the reason this suite failed SILENTLY in a
    # cell while passing on the host.  MEASURED 2026-09-13: the claim declared only MODULE.bazel
    # and tools/bibtex.bzl in `builds`, so NO paper.toml was staged; every project then read as
    # "declares NONE" and the cell's record said `(13)` where the host says `(1)` declaring and
    # `(12)` not.  A partition that is unanimous because its input vanished is not a measurement.
    #
    # The 13 tomls are now declared in the bib (the same enumeration arch-roster-wired carries),
    # so an absent one means the DECLARATION is wrong, not that the project is quiet — and this
    # says so loudly rather than returning a plausible False.
    if not p.exists():
        raise SystemExit(
            f"bnd-genre-emit: CANNOT RUN — {p} is not staged, so whether {project_dir!r} declares "
            f"a genre is unmeasurable here (declare it in the warrant's `builds`)")
    return any(ln.strip().startswith("[genres.") for ln in p.read_text().splitlines())


def emission_state(bzl: str) -> str:
    """"guarded" | "unconditional" | "absent" — the generator's `:genres` emission rule.

    ⚑ THREE STATES, NOT TWO, AND THE THIRD IS WHY.  A first version returned a bool and reported
    a DELETED emission as "unconditional" — red for the right reason, naming the wrong cause.
    That is the misdiagnosis shape this repo refuses everywhere else (`Ζ·rests·unresolved`: "no
    record" and "no constraint" render identically once collapsed), so absence gets its own name.
    """
    i = bzl.find('name = \\"genres\\"')
    if i < 0:
        i = bzl.find('name = "genres"')
    if i < 0:
        return "absent"
    head = "\n".join(bzl[:i].splitlines()[-12:])
    return "guarded" if "repository_ctx.attr.genres" in head else "unconditional"


def main() -> int:
    module = (ROOT / "MODULE.bazel").read_text()
    bzl = BZL.read_text()
    projects = wired_projects(module)
    if not projects:
        print("bnd-genre-emit: no bib.project tags found in MODULE.bazel", file=sys.stderr)
        return 1

    print("Μ·bnd-genre-emit — the generator emits :genres iff a project declares a genre\n")
    print("⟨the guard exists⟩\n")

    state = emission_state(bzl)
    print(f"  {'ok' if state == 'guarded' else 'FAIL'} the `:genres` emission is "
          f"{'guarded by `repository_ctx.attr.genres`' if state == 'guarded' else state.upper()}")
    if state == "absent":
        print("bnd-genre-emit: there is NO `:genres` emission in the generator — a declared genre "
              "is invoked by nothing, which is Ν-F7 restored (`genre.py --check` wired to nothing)",
              file=sys.stderr)
        return 1
    if state == "unconditional":
        print("bnd-genre-emit: the emission is UNCONDITIONAL — every project would carry a check "
              "over an empty registry, green by vacuity", file=sys.stderr)
        return 1

    print("\n⟨the attribute has ONE owner⟩\n")
    # The extension must fill it; a repository_ctx cannot read paper.toml (bibtex.bzl:1046), so a
    # re-derivation inside the repo rule is the Ζ·entry·point defect verbatim.
    filled = "genres = _declared_genres(module_ctx, tag.project)" in bzl
    print(f"  {'ok' if filled else 'FAIL'} the extension fills it from `_declared_genres`")
    if not filled:
        print("bnd-genre-emit: nothing fills the `genres` attribute — the target would never be "
              "emitted, and the guard would be vacuously false", file=sys.stderr)
        return 1

    print("\n⟨P, F, δ⟩ the population, per project\n")
    declaring = sorted(p for p, d in projects.items() if declares_genre(d))
    silent = sorted(p for p, d in projects.items() if not declares_genre(d))
    print(f"  ok DECLARES a genre → gets :genres  ({len(declaring)}): "
          f"{', '.join(declaring) or 'none'}")
    print(f"  ok declares NONE   → no :genres     ({len(silent)}): "
          f"{', '.join(silent)}")

    if not declaring:
        # Not a pass: with no declaring project the biconditional is vacuously satisfiable by a
        # generator that never emits.  Absence here is a reading about the CORPUS, and it makes
        # this witness unable to discriminate — which is a refusal, not a green.
        print("\nbnd-genre-emit: NO project declares a genre, so the positive half of the "
              "biconditional has no witness.  This check cannot discriminate on this corpus.",
              file=sys.stderr)
        return 1

    print(f"\n      P (pass side): a [genres.*] table → the guard is true → :genres emitted")
    print(f"      F (flag side): no [genres.*] table → the guard is false → no target")
    print(f"      δ (min delta): one `[genres.<name>]` header in a project's paper.toml")
    print(f"\nBOUNDARIES: PASS (2 structural behaviors, {len(projects)} projects partitioned, "
          f"1 delta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
