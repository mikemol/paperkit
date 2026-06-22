#!/usr/bin/env python3
"""paperkit gate — verify the paper.

Three invariants, all from the warrant set:
  RESOLVE   every [@key] cited in the prose resolves — a claim whose `check`
            passes, or a reference (no `check`) that is at least defined.
  COVERAGE  every rubric section appears in the prose, and every claim tagged
            for a section is cited within it.  A PLACEMENT (emit:/figure) tagged
            to a section but cited by no prose is a postulate — advised against by
            default, and rejected under --safe (a zero-postulate document).
  PROJECT   the committed prose equals the projection (paperkit-project --check).

A claim's verifier is `<type>:<target>`.  Built-in types (no config needed):
  file:<path>   the artifact exists, relative to the project
  cmd:<script>  run `<target>` from the project dir; exit 0 = pass
Custom types come from paper.toml as `[checks.<type>] cmd = "... {target} ..."`,
run from the project dir, exit 0 = pass.  `cmd:` is the universal escape hatch
every check reduces to; the registry just gives recurring ones a name.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project as P  # noqa: E402


def run_ok(cmd: str, cwd: Path) -> bool:
    try:
        return subprocess.run(cmd, shell=True, cwd=cwd,
                              capture_output=True).returncode == 0
    except Exception:
        return False


def resolves(check: str, project_dir: Path, custom: dict) -> bool:
    typ, _, target = check.partition(":")
    if typ == "file":
        return (project_dir / target).exists()
    if typ == "cmd":
        return run_ok(target, project_dir)
    if typ in custom:
        return run_ok(custom[typ]["cmd"].replace("{target}", target), project_dir)
    return False


def cited_keys(prose: str) -> set:
    # Citations live in prose, not in emitted code blocks — strip fenced blocks so
    # an example containing `@misc{…}` is not misread as a citation [@misc].
    prose = re.sub(r"```.*?```", "", prose, flags=re.S)
    return set(re.findall(r"@([A-Za-z0-9][\w.:-]*)", prose))


def main(argv: list) -> int:
    args = [a for a in argv if not a.startswith("-")]
    safe = "--safe" in argv      # zero-postulate: uncited placements FAIL, not advise
    project_dir = Path(args[0]).resolve() if args else Path.cwd()
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
    if prose != P.project(cfg):
        print(f"paperkit-gate: {out.name} ≠ projection — regenerate (paperkit-project)", file=sys.stderr)
        rc = 1
    else:
        print(f"paperkit-gate: {out.name} ≡ projection")

    # RESOLVE — every cited claim's check passes; references at least defined.
    # Placed warrants (emit:/figure) carry no citation but ARE in the document by
    # construction, so their checks must pass too.
    warrants = {k for k, f in F.items() if f.get("check")}
    placed = {k for k, f in F.items() if P.is_placed(f)}
    to_verify = (cited | placed) & warrants
    undefined = sorted(cited - set(F))
    cache: dict = {}

    def ok(chk: str) -> bool:
        if chk not in cache:        # each distinct check runs once, not per-citation
            cache[chk] = resolves(chk, project_dir, custom)
        return cache[chk]

    bad = sorted(k for k in to_verify if not ok(F[k]["check"]))
    if undefined:
        print(f"paperkit-gate: undefined citations: {', '.join(undefined)}", file=sys.stderr)
        rc = 1
    if bad:
        for k in bad:
            print(f"paperkit-gate: check FAILED for [@{k}]: {F[k]['check']}", file=sys.stderr)
        rc = 1
    if not undefined and not bad:
        print(f"paperkit-gate: {len(to_verify)} cited/placed claim(s) all resolve to passing checks")

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
    if gaps:
        for g in gaps:
            print(f"paperkit-gate: coverage — {g}", file=sys.stderr)
        rc = 1
    else:
        secs = len(P.rubric(cfg["rubric"]))
        print(f"paperkit-gate: coverage complete — {secs} sections, all tagged claims cited")
    for a in advisories:
        print(f"paperkit-gate: advisory — {a}", file=sys.stderr)

    print("paperkit-gate: PASS" if rc == 0 else "paperkit-gate: FAIL", file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
