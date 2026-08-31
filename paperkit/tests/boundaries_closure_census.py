"""Behavioral-boundary examples for Ξ·dag·script — the closure census and the edge it audits.

⟨P, F, δ⟩.  A witness that shells out to a sibling generator does not IMPORT what that generator
imports; `closure.py` must contribute the script's own engine cone, or the build stages too few
modules and the claim's BASELINE dies with ModuleNotFoundError.

⚑ THE SUITE EXISTS BECAUSE THE CENSUS WENT GREEN AND THAT PROVED NOTHING.  `closure_census.py`
flagged `edge-formulas` before the fix and does not now, which is a real before/after — but a
single one, on the instance that motivated the work.  An alarm whose red path is exercised once,
by the bug that prompted it, is an instrument trusted per-use, not a control
(Λ·instrument-vs-gate).  Every arm below CONSTRUCTS the failure on a synthetic project and asserts
the census names it, so the green is earned rather than assumed.

⚑⚑ AND THE CENSUS UNDER-REPORTED THREE TIMES BEFORE IT WAS RIGHT — a name list missed config/
(witness `registry.py`), bib-scraping missed paper/ (the `claim:KEY` verb never names its script),
and a `*/checks` glob missed the ROOT project (`checks/gen_fields.py`).  Each was a filter
reported as a population (Λ·declared-partial), and each read as a clean `0 under-declared`.  So
the coverage arms here assert what the census EXAMINED, not only what it found.

    python3 paperkit/tests/boundaries_closure_census.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
ROOT = ENGINE.parent
sys.path.insert(0, str(ROOT))

# ⚑ NAMED IN FULL, NOT FLAT (Ζ·engine·flat).  `from _boundary import Suite` behind a
# `sys.path.insert(ENGINE)` is unresolvable to mypy, so `Suite` types as Any and every call site
# poisons — 17 findings in a file whose own subject is an under-declared dependency.  Both
# `paperkit.tests` and `tools` are packages; the full name costs nothing and is checkable.
from paperkit.tests._boundary import Suite  # noqa: E402
from tools import closure_census as cc  # noqa: E402

PY = sys.executable or "python3"
MIN_WITNESSES = 30

# A witness module that reaches the engine ONLY through a subprocess: it names the generator as a
# path constant and runs it.  Nothing here imports bib.
WITNESS = '''\
"""synthetic witness."""
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def formulas():
    r = subprocess.run([sys.executable, str(HERE / "gen_thing.py"), "--check"], check=False)
    return r.returncode == 0


CLAIMS = {"synth-formulas": formulas}
'''

# The generator the witness shells out to — flat `import bib`, the shape that broke edge-formulas.
GEN = '''\
"""synthetic generator."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "paperkit"))
import bib
'''

# The same generator with NO engine import — the control: nothing to under-declare.
GEN_INERT = '''\
"""synthetic generator that touches no engine module."""
import sys
'''

TOML = ('[paper]\ntitle = "synth"\nout = "SYNTH.md"\n\n'
        '[checks.claim]\ncmd = "python3 checks/w.py {target}"\n')
BIB = ("@misc{synth-formulas,\n  section = {s},\n"
       "  claim   = {a synthetic claim},\n  check   = {claim:synth-formulas}\n}\n")


def _project(tmp: Path, gen: str) -> Path:
    """Build a synthetic project whose witness reaches the engine only via a subprocess."""
    proj = tmp / "synth"
    (proj / "checks").mkdir(parents=True)
    (proj / "paper.toml").write_text(TOML)
    (proj / "warrants.bib").write_text(BIB)
    (proj / "checks" / "w.py").write_text(WITNESS)
    (proj / "checks" / "gen_thing.py").write_text(gen)
    return proj


def _roots(check: Path, closure: Path) -> set[str]:
    """Derive the IMPORT roots `closure` gives the one claim in a synthetic witness."""
    mods = cc.engine_modules()
    r = subprocess.run(  # noqa: S603
        [PY, str(closure), "--check", str(check), "--relpath", "synth/checks/w.py", *mods],
        cwd=ROOT, capture_output=True, text=True, check=False,
        env={"PYTHONPATH": str(ROOT / "tools"), "PATH": "/usr/bin:/bin"},
    )
    return {Path(p).stem for ln in r.stdout.splitlines()
            for c, p in [ln.split("\t")[:2]] if c == "synth-formulas" and ":" not in p}


def _without_edge(tmp: Path) -> Path:
    """Write a copy of closure.py with the Ξ·dag·script edge REMOVED — the F arm's mechanism.

    ⚑ THE FIRST CUT OF THIS SUITE COULD NOT FAIL, AND THAT IS THE FINDING IT TAUGHT.  It built a
    synthetic under-declared project and asserted `closure_census` flagged it — but the census
    ASKS closure.py for the declared roots, so once the edge exists the roots already cover the
    generator and there is nothing to flag.  Perturbing the INPUT cannot exercise a detector whose
    subject is the tool it consumes; every arm went green by construction and four went red only
    because the fixture no longer reproduced the pre-fix state.

    So the F arm perturbs the MECHANISM instead — exactly the mutation the Δ sweep performs.  With
    the edge deleted, the same synthetic project must lose the generator's cone; with it present,
    that cone must be there.  That pair is falsifiable in both directions (Λ·audit·provenance:
    mutate the mechanism out, do not source-scan).
    """
    src = (ROOT / "tools" / "closure.py").read_text()
    marker = "        wi |= _script_roots(fn)"
    if marker not in src:
        msg = "closure.py no longer wires _script_roots where this suite expects it"
        raise AssertionError(msg)
    out = tmp / "closure_noedge.py"
    out.write_text(src.replace(marker, "        pass  # edge removed"))
    return out


def _synthetic(s: Suite) -> None:
    """Prove the Ξ·dag·script edge is what stages a subprocess generator's cone."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        check = _project(tmp / "a", GEN) / "checks" / "w.py"
        live = ROOT / "tools" / "closure.py"

        with_edge = _roots(check, live)
        s.check("the generator's engine import is staged (bib)", "bib" in with_edge)
        s.check("its TRANSITIVE cone is staged too (bibparse)", "bibparse" in with_edge)

        without = _roots(check, _without_edge(tmp))
        s.check("with the edge REMOVED, the generator's cone is gone", "bib" not in without)

        # a generator importing no engine module needs no cone either way — the edge is not
        # staging the whole engine indiscriminately
        inert = _roots(_project(tmp / "b", GEN_INERT) / "checks" / "w.py", live)
        s.check("a generator importing NO engine module stages no engine cone",
                "bib" not in inert)

        s.section("P, F, delta minimum-delta pairs")
        s.delta("the Xi-dag-script edge is what carries a subprocess generator's cone",
                "bib" in with_edge, "bib" not in without,
                p="P: with the edge, the witness stages bib + bibparse",
                f="F: with the edge removed, the identical witness stages neither",
                d="one line — `wi |= _script_roots(fn)` in closure.py's per-claim loop")
        s.delta("and it stages a cone only where the generator asks for one",
                "bib" in with_edge, "bib" not in inert,
                p="P: generator does `import bib` -> bib staged",
                f="F: generator imports only sys -> nothing staged",
                d="one import line in the generator")


def _coverage(s: Suite) -> None:
    """Assert the census reports its POPULATION, not only its findings — on synthetic projects.

    ⚑ THE FIRST CUT ASSERTED THIS AGAINST THE LIVE TREE, AND A BOUNDARY SUITE CANNOT.  It ran the
    census over the repo and required >=30 witness modules including `paper/checks/claims.py` —
    true on the host, false inside the hermetic cell the gate runs it in, where only the declared
    `reads` are staged.  A suite that asserts host-shaped facts is not hermetic; it passed for me
    and reddened the gate, which is the same host-vs-sandbox split that has bitten this arc three
    times.  Whether the LIVE tree is clean is the footprint audit's job (Ξ·dag·reads, run at the
    hook layer outside Bazel precisely because it needs the real tree).

    What IS hermetic, and what actually failed three times, is the discovery RULE: a witness named
    by a bib `cmd:`, and one named only by a `[checks.claim]` template in paper.toml.  Both are
    constructed here.
    """
    s.section("witness discovery — the rule that under-reported three times")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # a project whose witness is named ONLY by the paper.toml verb template (the paper/ and
        # root/ shape) — a bib-scraping census skipped these and reported them clean
        by_toml = _project(tmp / "t", GEN)
        found = {p.name for p in cc.witness_modules(by_toml)}
        s.check("a witness named only by the paper.toml verb template is found", "w.py" in found)
        s.check("the generator beside it is not mistaken for a witness",
                "gen_thing.py" not in found)

        # a project with NO witness at all must come back empty, not raise and not guess
        bare = tmp / "bare"
        (bare / "checks").mkdir(parents=True)
        s.check("a project with no bib and no toml yields no witness",
                cc.witness_modules(bare) == [])

        # and a directory that is not a project at all
        s.check("a directory with no checks/ yields no witness", cc.witness_modules(tmp) == [])


def main() -> int:
    """Exercise the census and the Ξ·dag·script edge on synthetic and live inputs."""
    s = Suite("BOUNDARIES", "Xi-dag-script — a subprocess-reached generator's cone is staged")
    _synthetic(s)
    _coverage(s)
    return s.finish()


if __name__ == "__main__":
    raise SystemExit(main())
