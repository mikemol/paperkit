#!/usr/bin/env python3
"""paperkit gate — verify the paper.

Three invariants, all from the warrant set:
  RESOLVE   every [@key] cited in the prose resolves — a claim whose `check`
            passes, or a reference (no `check`) that is at least defined.
  COVERAGE  every rubric section appears in the prose, and every claim tagged
            for a section is cited within it.  A PLACEMENT (emit:/figure) tagged
            to a section but cited by no prose is a postulate — advised against by
            default, and rejected under --safe (a zero-postulate document).
  --without-K  opt-in proof-relevance: every cited claim must carry a DISTINCT
            witness.  The gate's check→bool is proof-irrelevant (Axiom K / UIP), so
            it would otherwise identify distinct claims that share one check.
  PROJECT   the committed prose equals the projection (paperkit-project --check).

A claim's verifier is `<type>:<target>`.  Built-in types (no config needed):
  file:<path>   the artifact exists, relative to the project
  cmd:<script>  run `<target>` from the project dir; exit 0 = pass
Custom types come from paper.toml as `[checks.<type>] cmd = "... {target} ..."`,
run from the project dir, exit 0 = pass.  `cmd:` is the universal escape hatch
every check reduces to; the registry just gives recurring ones a name.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project as P  # noqa: E402


_MB_SCRIPT = Path(__file__).resolve().parent / "membudget"
_MB_OK = None


def membudget_ok() -> bool:
    """Is the memory-budget semaphore usable here?  Cached.  Inside an existing
    membudget scope (MEMBUDGET_PARENT set) it is by construction — that is the
    recursion point: a nested gate re-invokes membudget so its checks SUBALLOCATE
    from the parent's lease rather than the global pool.  At top level, probe that
    a user systemd scope opens; set PAPERKIT_NO_MEMBUDGET to force the plain path."""
    global _MB_OK
    if _MB_OK is not None:
        return _MB_OK
    if os.environ.get("PAPERKIT_NO_MEMBUDGET") or not os.access(_MB_SCRIPT, os.X_OK):
        _MB_OK = False
    elif os.environ.get("MEMBUDGET_PARENT"):
        _MB_OK = True
    else:
        try:
            _MB_OK = subprocess.run(["systemd-run", "--user", "--scope", "--quiet", "true"],
                                    capture_output=True, timeout=15).returncode == 0
        except Exception:
            _MB_OK = False
    return _MB_OK


# A check is arbitrary code (cmd: is the universal escape hatch), so it must not run in
# whatever ambient environment the gate happened to inherit — that is both an injection
# surface (LD_PRELOAD, IFS, BASH_ENV, PYTHONPATH, …) and a reproducibility leak (the
# verdict would depend on the caller's shell).  Like sshd, we DON'T inherit: we build a
# controlled environment, default-deny, keeping only what a check (and the membudget
# semaphore + a nested gate) legitimately need.  PATH is kept so tools resolve; pinning
# WHICH tools (e.g. GNU vs uutils coreutils) is a further step.
_ENV_KEEP = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "TERM", "TZ", "TMPDIR",
             "LANG", "LANGUAGE",
             "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"}  # membudget's systemd --user
_ENV_KEEP_PREFIX = ("LC_", "MEMBUDGET_", "PAPERKIT_")        # locale + paperkit's own knobs


def clean_env(env: dict | None = None) -> dict:
    """A sanitized environment for running a check: the controlled allow-list only, so
    no LD_PRELOAD/IFS/BASH_ENV/PYTHONPATH and the like reach the command."""
    src = os.environ if env is None else env
    return {k: v for k, v in src.items()
            if k in _ENV_KEEP or k.startswith(_ENV_KEEP_PREFIX)}


def run_ok(cmd: str, cwd: Path, lease: int | None = None, label: str = "check") -> bool:
    try:
        e = clean_env()
        if lease:   # run under a memory lease; membudget admits it when RAM fits
            argv = [str(_MB_SCRIPT), "run", str(lease), label, "--", "sh", "-c", cmd]
            return subprocess.run(argv, cwd=cwd, env=e, capture_output=True).returncode == 0
        return subprocess.run(cmd, shell=True, cwd=cwd, env=e,
                              capture_output=True).returncode == 0
    except Exception:
        return False


def resolves(check: str, project_dir: Path, custom: dict, lease: int | None = None) -> bool:
    typ, _, target = check.partition(":")
    if typ == "file":
        return (project_dir / target).exists()        # no subprocess → no lease
    if typ == "cmd":
        cmd = target
    elif typ in custom:
        cmd = custom[typ]["cmd"].replace("{target}", target)
    else:
        return False
    return run_ok(cmd, project_dir, lease=lease, label=check)


def cited_keys(prose: str) -> set:
    # Citations live in prose, not in emitted code blocks — strip fenced blocks so
    # an example containing `@misc{…}` is not misread as a citation [@misc].
    prose = re.sub(r"```.*?```", "", prose, flags=re.S)
    return set(re.findall(r"@([A-Za-z0-9][\w.:-]*)", prose))


def main(argv: list) -> int:
    args = [a for a in argv if not a.startswith("-")]
    safe = "--safe" in argv      # zero-postulate: uncited placements FAIL, not advise
    without_k = "--without-K" in argv or "--without-k" in argv   # forbid shared witnesses
    as_json = "--json" in argv   # emit structured results to stdout (human lines suppressed)
    # The bib IS the makefile: a project's distinct checks are independent targets,
    # so the gate runs them concurrently (default = all cores; --jobs=1 forces serial).
    jobs = next((int(a.split("=", 1)[1]) for a in argv if a.startswith("--jobs=")),
                os.cpu_count() or 4)
    project_dir = Path(args[0]).resolve() if args else Path.cwd()

    def info(msg):              # human success lines — suppressed under --json
        if not as_json:
            print(msg)
    cfg = P.load_config(project_dir)
    custom = tomllib.loads((project_dir / "paper.toml").read_text()).get("checks", {})

    F, primary = {}, cfg["bibs"][0].name
    for b in cfg["bibs"]:
        F.update(P.entries(b))

    out = cfg["out"]
    if not out.exists():
        print(f"paperkit-gate: {out.name} not built — run paperkit-project", file=sys.stderr)
        return 1
    prose = out.read_text()
    cited = cited_keys(prose)
    rc = 0

    # PROJECT — committed prose is the projection
    proj_ok = prose == P.project(cfg)
    if not proj_ok:
        print(f"paperkit-gate: {out.name} ≠ projection — regenerate (paperkit-project)", file=sys.stderr)
        rc = 1
    else:
        info(f"paperkit-gate: {out.name} ≡ projection")

    # RESOLVE — every cited claim's check passes; references at least defined.
    # Placed warrants (emit:/figure) carry no citation but ARE in the document by
    # construction, so their checks must pass too.
    warrants = {k for k, f in F.items() if f.get("check")}
    placed = {k for k, f in F.items() if P.is_placed(f)}
    to_verify = (cited | placed) & warrants
    undefined = sorted(cited - set(F))
    # Resolve each DISTINCT check exactly once (shared witnesses run one time).  Two
    # kinds of target.  A check whose warrant DECLARES a lease (`mem`) is memory-bound:
    # run it under the membudget semaphore, fanned out UNBOUNDED and admitted as RAM
    # frees — and recursion-aware, since a check that runs a nested gate suballocates
    # from its own lease.  A light check (no `mem`) is CPU-bound, not memory-bound: run
    # it in a plain pool capped at `jobs` (wrapping every tiny check in a systemd scope
    # only adds latency and, at scale, thrashes).  So the bib is also the makefile's
    # resource manifest: heavy targets say how much RAM they hold.
    distinct = sorted({F[k]["check"] for k in to_verify})
    mem_of: dict = {}
    for k in to_verify:
        if F[k].get("mem"):
            c = F[k]["check"]
            mem_of[c] = max(mem_of.get(c, 0), int(F[k]["mem"]))
    mb = membudget_ok() and jobs != 1 and bool(mem_of)
    if mb:
        subprocess.run([str(_MB_SCRIPT), "status"], capture_output=True)   # init ledger once

    def resolve1(c: str) -> bool:
        return resolves(c, project_dir, custom, lease=mem_of.get(c) if mb else None)

    heavy = [c for c in distinct if mb and c in mem_of]
    light = [c for c in distinct if c not in heavy]
    results: dict = {}
    if len(distinct) > 1 and (jobs > 1 or heavy):
        with ThreadPoolExecutor(max_workers=max(1, jobs)) as lex, \
             ThreadPoolExecutor(max_workers=max(1, len(heavy))) as hex:
            fut = {lex.submit(resolve1, c): c for c in light}
            fut.update({hex.submit(resolve1, c): c for c in heavy})
            for f in fut:
                results[fut[f]] = f.result()
    else:
        results = {c: resolve1(c) for c in distinct}
    cache = {c: results[c] for c in distinct}

    bad = sorted(k for k in to_verify if not cache[F[k]["check"]])
    if undefined:
        print(f"paperkit-gate: undefined citations: {', '.join(undefined)}", file=sys.stderr)
        rc = 1
    if bad:
        for k in bad:
            print(f"paperkit-gate: check FAILED for [@{k}]: {F[k]['check']}", file=sys.stderr)
        rc = 1
    if not undefined and not bad:
        info(f"paperkit-gate: {len(to_verify)} cited/placed claim(s) all resolve to passing checks")

    # WITHOUT-K — proof-relevance.  The gate reduces each check to a boolean, so it
    # silently identifies distinct cited claims that share one witness (Axiom K /
    # UIP).  --without-K drops that: every cited claim must carry a DISTINCT witness.
    # (collapses are computed always, for --json; they only FAIL the gate under --without-K.)
    by_check: dict = {}
    for k in sorted(cited & warrants):
        by_check.setdefault(F[k]["check"], []).append(k)
    collapses = {c: ks for c, ks in by_check.items() if len(ks) > 1}
    if without_k:
        if collapses:
            for c, ks in sorted(collapses.items()):
                print(f"paperkit-gate: --without-K — {len(ks)} cited claims collapse onto "
                      f"one witness {c}: {', '.join(ks)}", file=sys.stderr)
            rc = 1
        else:
            info(f"paperkit-gate: --without-K — {len(cited & warrants)} cited claim(s) "
                 f"each carry a distinct witness")

    # COVERAGE — sections present, section-tagged claims cited
    headings = "\n".join(ln for ln in prose.splitlines() if ln.startswith("## "))
    gaps = []
    for sk, title in P.rubric(cfg["rubric"]):
        if title.lower() not in headings.lower():
            gaps.append(f"section '{title}' absent")
    advisories = []
    for k, f in F.items():
        if f.get("section") and k not in cited:
            if P.is_placed(f):
                # An uncited placement is a POSTULATE: a block in the document with
                # no claim citing it — present and load-bearing, but outside the
                # checked claim-DAG.  Tolerated by default (advisory); under --safe
                # it fails, exactly as `agda --safe` rejects postulates.
                msg = (f"uncited placement [@{k}] (section={f['section']}) — a postulate: "
                       f"a block no claim cites; prefer an example the prose cites")
                (gaps if safe else advisories).append(msg)
            else:
                gaps.append(f"claim [@{k}] tagged section={f['section']} but not cited")
    secs = len(P.rubric(cfg["rubric"]))
    if gaps:
        for g in gaps:
            print(f"paperkit-gate: coverage — {g}", file=sys.stderr)
        rc = 1
    else:
        info(f"paperkit-gate: coverage complete — {secs} sections, all tagged claims cited")
    for a in advisories:
        print(f"paperkit-gate: advisory — {a}", file=sys.stderr)

    if as_json:
        print(json.dumps({
            "document": out.name, "pass": rc == 0, "project_ok": proj_ok,
            "verified": len(to_verify), "undefined": undefined, "bad": bad,
            "sections": secs, "gaps": gaps,
            "postulates": sorted(k for k, f in F.items()
                                 if f.get("section") and k not in cited and P.is_placed(f)),
            "collapses": collapses,
        }, indent=2))
    print("paperkit-gate: PASS" if rc == 0 else "paperkit-gate: FAIL", file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
