#!/usr/bin/env python3
"""Per-claim discriminating witnesses — the `claim:` check type (registered in
paper.toml as `[checks.claim] cmd = "python3 checks/claims.py {target}"`).

Each function asserts the SPECIFIC proposition its claim makes about the engine, so
the check fails if the claim is false (Δ grades it `behavioral`) and every claim
names its own target `claim:<key>` (so the gate's --without-K is satisfied: a
distinct witness per claim, not one shared `file:` standing for many).

    python3 checks/claims.py <claim-key>      # run from paper/; exit 0 = claim holds
"""
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

# Ζ·mutant — the engine LOCATION is overridable via PAPERKIT_ENGINE (a paperkit knob, so it survives
# resolver.clean_env): a pk_eval action points it at an engine-VARIANT (the real engine with one
# module swapped for a mutated one) to test whether mutating that def flips this check.  Unset →
# the engine beside the paper (the normal gate path).
ENGINE = Path(os.environ.get("PAPERKIT_ENGINE") or Path(__file__).resolve().parents[2] / "paperkit")
PAPER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests"))
from _fixture_model import entry  # noqa: E402  (the validated fixture kernel — counter-fixtures;
#   capability helpers are imported FUNCTION-LOCALLY per witness, so closure.py's BASE stays model-only)

def _src(name):
    """A module's SOURCE, read INSIDE the witness that inspects it (Μ·kernel·fixture·reads):
    the "x.py" string constant sits in the witness body, so only the source-inspecting
    witnesses stage that module (flat) and sweep its sites — a MODULE-level read would make
    it a staged input of EVERY row of the grid."""
    return (ENGINE / name).read_text()


def _parse(bib_text):
    import project as P
    """Parse one .bib through the real engine parser; return its record fields."""
    d = tempfile.mkdtemp()
    try:
        p = Path(d) / "t.bib"
        p.write_text(bib_text)
        return P.entries(p)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def agree_builtin():
    # agree CONCURS — ≥2 independent producers (split on |||) must all exit 0 and emit
    # IDENTICAL output; agreement across implementations rules out a shared bug.
    import gate
    assert gate.resolves("agree:printf 42 ||| printf 42", ENGINE, {}) is True, "agree: of two concurring producers failed"
    assert gate.resolves("agree:printf 42 ||| printf 43", ENGINE, {}) is False, "agree: of two disagreeing producers passed"
    assert gate.resolves("agree:printf 42", ENGINE, {}) is False, "agree: with a single producer (no independence) passed"
    assert gate.resolves("agree:printf 42 ||| false", ENGINE, {}) is False, "agree: tolerated a producer that failed"


def result_builtin():
    # result PARSES a sibling project's machine-readable gate verdict (gate --json): a
    # green sibling resolves True, a red one False — composition, not re-derivation.
    import gate
    import project as P
    d = Path(tempfile.mkdtemp())
    try:
        sib = d / "g"
        sib.mkdir()

        def write(check):
            import project as P
            (sib / "paper.toml").write_text('[paper]\ntitle = "t"\nwarrants = ["w.bib"]\n'
                                            'rubric = "r.tsv"\nout = "out.md"\n')
            (sib / "r.tsv").write_text("s\tSec\n")
            (sib / "w.bib").write_text("@misc{c,\n  section = {s},\n  claim = {x},\n  check = {%s}\n}\n" % check)
            (sib / "out.md").write_text(P.project(P.load_config(sib)))

        write("cmd:true")
        assert gate.resolves("result:g", d, {}) is True, "result: did not PARSE a green sibling's verdict as pass"
        write("cmd:false")
        assert gate.resolves("result:g", d, {}) is False, "result: did not PARSE a red sibling's verdict as fail"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def dataset_backed():
    # "a custom verifier may interpret a dataset the project SHIPS … a single edit can
    # falsify" — a check whose command reads a project file resolves true while the file
    # matches and flips false on a one-line edit to that shipped dataset.
    import gate
    d = Path(tempfile.mkdtemp())
    try:
        custom = {"data": {"cmd": "python3 -c \"import json,sys; "
                                  "sys.exit(0 if json.load(open('d.json'))['k']=='ok' else 1)\""}}
        (d / "d.json").write_text('{"k": "ok"}')
        assert gate.resolves("data:x", d, custom) is True, "a dataset-backed check over matching data must resolve"
        (d / "d.json").write_text('{"k": "drift"}')
        assert gate.resolves("data:x", d, custom) is False, "a single edit to the shipped dataset must flip the verdict"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def dataset_fresh():
    # "the verifier re-runs the producer … and fails on drift" — fresh-by-construction:
    # a check that regenerates via the producer and compares passes on a matching
    # committed asset and fails once that asset drifts from what the producer yields.
    import gate
    d = Path(tempfile.mkdtemp())
    try:
        # a fresh: check REGENERATES via its producer and compares to the committed asset — the
        # producer RUN is the essence (that is what "fresh" means), a single-level cmd spawn gate
        # runs like any cmd: check.  (The regenerator is a plain producer.sh, not a nested python
        # subprocess — one spawn, so the hermetic mutation sandbox runs it like grade-ladder's cmd.)
        (d / "producer.sh").write_text("echo CANON-V1\n")
        custom = {"fresh": {"cmd": 'test "$(cat asset.txt)" = "$(sh producer.sh)"'}}
        (d / "asset.txt").write_text("CANON-V1\n")
        assert gate.resolves("fresh:x", d, custom) is True, "a committed asset matching its producer must pass"
        (d / "asset.txt").write_text("STALE\n")
        assert gate.resolves("fresh:x", d, custom) is False, "an asset drifted from its producer must fail"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def file_builtin():
    # "file, that an artifact exists"
    import gate
    assert gate.resolves("file:gate.py", ENGINE, {}) is True, "file: of an existing path failed"
    assert gate.resolves("file:does-not-exist.xyz", ENGINE, {}) is False, "file: of a missing path passed"


def cmd_builtin():
    # "cmd, that a script exits zero"
    import gate
    assert gate.resolves("cmd:true", ENGINE, {}) is True, "cmd:true did not pass"
    assert gate.resolves("cmd:false", ENGINE, {}) is False, "cmd:false did not fail"


# ── engine section ───────────────────────────────────────────────────────────
def prose_is_artifact():
    # "the committed prose is a build artifact, not a source" — the projector has a
    # --check mode that compares the committed file against a fresh projection
    src = _src("project.py")
    assert "--check" in src and "read_text() != out" in src, \
        "projector can no longer detect a hand-edit against its projection"


def edit_cant_survive():
    from _fixture_gate import gate
    from _fixture_project import project_text
    # "a hand-edit cannot survive a build" — only the exact projection passes the gate
    w = [entry("x", claim="anchored")]
    canonical = project_text(w)
    assert gate(w, out=canonical)[0] == 0
    for edit in ("PREPENDED\n" + canonical, canonical + "\nAPPENDED\n", canonical + "x"):
        assert edit != canonical and gate(w, out=edit)[0] != 0, "a hand-edit survived the build"


def coverage_both_sides():
    # "coverage is enforced from both sides" — section-present AND claim-cited branches
    src = _src("gate.py")
    assert "absent" in src and "not cited" in src, "coverage no longer checks both directions"


def every_section_appears():
    # "every required section must appear"
    assert "not in headings" in _src("gate.py"), "gate no longer checks each section appears"


def every_claim_cited():
    # "every claim tagged for a section must be cited within it"
    assert "k not in cited" in _src("gate.py"), "gate no longer checks each tagged claim is cited"


# ── model section ────────────────────────────────────────────────────────────
def record_is_bibentry():
    # "which is exactly the shape of a bibliography entry" — a standard reference
    # entry parses through the very same record parser
    recs = _parse("@misc{ref,\n  author = {Knuth},\n  year = {1984},\n"
                  "  title = {Literate Programming}\n}\n")
    assert recs.get("ref", {}).get("title") and recs["ref"].get("author"), \
        "a standard bibliography entry no longer parses as a record"


def prose_projected():
    from _fixture_project import project_text
    # "the prose is projected, not authored" — the prose tracks the warrants
    a = project_text([entry("x", claim="zzfirst wording")]).lower()
    b = project_text([entry("x", claim="zzsecond wording")]).lower()
    assert "zzfirst" in a and "zzsecond" in b and a != b, \
        "prose does not track the warrants (it is authored, not projected)"


def ordered_by_deps():
    from _fixture_project import project_text
    # "within each section the claims are ordered by their dependency edges"
    t = project_text([entry("b", claim="zzbeta", frm="a"),
                      entry("a", claim="zzalpha")]).lower()
    assert t.index("zzalpha") < t.index("zzbeta"), "claims are not ordered by dependency edges"


def joined_by_glue():
    from _fixture_project import project_text
    # "joined by connective glue" — an explicit glue connector is woven between edges
    t = project_text([entry("a", claim="zzalpha"),
                      entry("b", claim="zzbeta", frm="a", glue="BECAUSE")]).lower()
    assert "because zzbeta" in t, "explicit glue is not woven between dependent claims"


def deterministic():
    from _fixture_project import project_text
    # "the same warrant set always giving the same document"
    w1 = [entry("a", claim="zzalpha")]
    w2 = [entry("a", claim="zzomega")]
    assert project_text(w1) == project_text(w1), "same warrants gave different documents"
    assert project_text(w1) != project_text(w2), "the document is independent of its warrants"
    assert "zzalpha" in project_text(w1).lower()


# ── Π·foundations: the vacuous atoms the grounding DAG rests on ───────────────
def node_is_claim():
    # each node of the claim-DAG is a single claim record
    recs = _parse("@misc{n,\n  section = {s},\n  claim = {a single statement},\n  check = {file:x}\n}\n")
    assert len(recs) == 1 and recs["n"].get("claim") == "a single statement", \
        "a warrant node is not a single claim"


def claims_are_warrants():
    # this paper's claims ARE its warrants: warrants.bib parses to the cited claim records
    import project as P
    recs = {}                                             # bib-list-aware: claims may be authored across modules
    for b in P.load_config(PAPER_DIR)["bibs"]:
        recs.update(P.entries(b))
    assert recs.get("paper-is-projection", {}).get("claim"), "the paper's claims are not its warrants"


# ── Π·selfhost: the drift-caught negative-assertions, as Φ counter-fixtures ───
def paperkit_on_paperkit():
    from _fixture_gate import gate
    from _fixture_project import project_text
    # run paperkit on paperkit: project a fixture, confirm the gate ACCEPTS the
    # faithful projection and REJECTS a drift of it
    w = [entry("x", claim="self applied")]
    good = project_text(w)
    assert gate(w, out=good)[0] == 0, "the gate rejected paperkit's own faithful projection"
    assert gate(w, out=good + "\nHAND-EDITED DRIFT\n")[0] != 0, "the gate accepted a drifted projection"


def one_green_check():
    from _fixture_gate import gate
    from _fixture_project import project_text
    # the document's correctness and the tool's are ONE green check: a single gate
    # invocation verifies the projection (document) AND runs the verifier (tool) —
    # breaking either side fails the same gate
    w = [entry("x", claim="one check", check="cmd:true")]
    good = project_text(w)
    assert gate(w, out=good)[0] == 0, "the single gate check did not pass"
    assert gate(w, out=good + "\nx\n")[0] != 0, "drift (document side) did not fail the gate"
    bad_check = [entry("x", claim="one check", check="cmd:false")]
    assert gate(bad_check, out=good)[0] != 0, "check failure (tool side) did not fail the gate"


# ── Π·distinct-witnesses: split the shared projection-stable group (--without-K) ──
def paper_is_paperkit():
    # this paper is itself a paperkit project: a well-formed config projecting to paper.md
    import project as P
    cfg = P.load_config(PAPER_DIR)
    assert (PAPER_DIR / "paper.toml").exists() and cfg["bibs"] and cfg["rubric"].exists(), \
        "the paper is not a well-formed paperkit project"
    assert cfg["out"].name == "paper.md", "the paper does not project to paper.md"


def prose_is_projection():
    # the paper's prose IS the projection of its warrants
    import project as P
    cfg = P.load_config(PAPER_DIR)
    assert P.project(cfg) == cfg["out"].read_text(), "paper.md is not the projection of its warrants"


def closes_gap():
    # closes the say/check gap: every claim in the ledger carries a verifier
    import project as P
    F = {}                                                # bib-list-aware: claims may be authored across modules
    for b in P.load_config(PAPER_DIR)["bibs"]:
        F.update(P.entries(b))
    # an entry with an `author` is an external reference (resolves by being defined), not an
    # assertion the paper makes — only the paper's OWN claims owe a verifier.
    missing = [k for k, f in F.items()
               if f.get("section") and f.get("claim") and not f.get("check") and not f.get("author")]
    assert not missing, f"claims without a verifier (the gap is open): {missing}"


def unverified_cant_ship():
    from _fixture_gate import gate
    from _fixture_project import project_text
    # an unverified sentence cannot ship: one failing verifier blocks the whole document
    w = [entry("a", claim="verified", check="cmd:true"),
         entry("b", claim="unverified", frm="a", check="cmd:false")]
    assert gate(w, out=project_text(w))[0] != 0, "a document with an unverified sentence shipped"


def not_project():
    from _fixture_gate import gate
    from _fixture_project import project_text
    # ...because it does not project: only the exact projection ships
    w = [entry("x", claim="canonical")]
    good = project_text(w)
    assert gate(w, out=good)[0] == 0, "the canonical projection was rejected"
    assert gate(w, out="not the projection\n")[0] != 0, "a non-projection shipped"


# ── edges: the three dependency graphs (from / rests-on / move) ───────────────
def edge_from_orders():
    from _fixture_project import project_text
    # `from` fixes prose order — a claim is projected only AFTER the claims it lists,
    # so document order is a topological sort of the from-graph (keys given scrambled)
    t = project_text([entry("c", claim="gamma", frm="b"),
                      entry("a", claim="alpha"),
                      entry("b", claim="beta", frm="a")]).lower()
    ia, ib, ic = (t.find(x) for x in ("alpha", "beta", "gamma"))
    assert -1 < ia < ib < ic, "from did not order the prose alpha→beta→gamma"


def edge_chiral():
    # grounding is independent of prose adjacency: rests-on clamps even when the premise is NOT a
    # from-neighbor (the two graphs diverge / reverse).  Π — tests the CLAMP (grade.clamp) over
    # known grades: the thesis grounds on `atom` but is a prose-neighbor of `mid`, yet clamps to atom.
    import grade
    recs = grade.clamp([
        {"key": "atom", "grade": "vacuous", "rests-on": []},
        {"key": "mid", "grade": "behavioral", "rests-on": []},               # the prose neighbor
        {"key": "thesis", "grade": "behavioral", "from": ["mid"], "rests-on": ["atom"]},
    ])
    th = next(r for r in recs if r["key"] == "thesis")
    assert "atom" in th.get("rests-on", []) and "atom" not in th.get("from", []), \
        "fixture should ground on a non-prose-neighbor"
    assert th["effective_grade"] == "vacuous", \
        "rests-on did not clamp despite atom not being a from-neighbor"


def edge_move_types():
    # the `move` field names a typed relation; its KIND decides its role, and a
    # section's scheme admits only certain kinds
    import rhetoric
    assert rhetoric.kind_of("consequence") == "entail", "consequence is not an entail move"
    assert rhetoric.kind_of("antithesis") == "turn", "antithesis is not a turn move"
    ok = rhetoric.check_scheme("ladder", ["a", "b"], ["consequence"])
    bad = rhetoric.check_scheme("ladder", ["a", "b"], ["antithesis"])
    assert ok == [] and bad, "a ladder must admit consequence (entail) and reject antithesis (turn)"


# ── projection: the projector's mechanics ────────────────────────────────────
def weave_sentence():
    from _fixture_project import project_text
    # a section's claims weave into ONE paragraph: first clause capitalized, each
    # carries its own citation tag, the rest attach inline (not one bullet per claim)
    t = project_text([entry("a", claim="alpha beat"),
                      entry("b", claim="beta beat", frm="a")])
    para = next(ln for ln in t.splitlines() if "@a]" in ln)
    assert "@b]" in para, "claims were not woven into one paragraph"
    assert para.lstrip()[:5] == "Alpha", "first clause was not capitalized"


def connector_resolution():
    from _fixture_project import project_text
    # the connector between adjacent clauses resolves by priority: an explicit `join`
    # overrides a `move`'s default connector
    won = project_text([entry("a", claim="alpha"),
                        entry("b", claim="beta", frm="a", join="; therefore, ", move="apposition")])
    assert "therefore" in won and "that is" not in won, "explicit join did not override the move connector"
    # a `move` with no `join` falls back to the move's typed connector (apposition → " — that is, ")
    fell = project_text([entry("a", claim="alpha"),
                         entry("b", claim="beta", frm="a", move="apposition")])
    assert "that is" in fell, "the move's connector was not used as the fallback"


def emit_placement():
    from _fixture_project import project_text
    # an `emit` warrant is placed VERBATIM (not woven), fenced by the asset's
    # extension; an image asset is placed as a markdown image instead
    code = project_text([entry("e", claim="example", emit="ex.sh")],
                        assets={"ex.sh": "echo hi\n"})
    assert "```sh" in code and "echo hi" in code, "shell asset not placed, fenced as sh"
    img = project_text([entry("g", claim="a figure", emit="fig.svg")],
                       assets={"fig.svg": "<svg></svg>\n"})
    assert "![a figure](fig.svg)" in img, "image asset not placed as a markdown image"


def config_flags():
    from _fixture_project import project_text
    # projection structure is configured, not hard-coded: `numbered` toggles section
    # numbers, `references` toggles the bibliography heading
    on = project_text([entry("a", claim="x")], numbered=True, references=True)
    off = project_text([entry("a", claim="x")], numbered=False, references=False)
    assert "## 1." in on and "## References" in on, "flags not honored when on"
    assert "## 1." not in off and "References" not in off, "flags not honored when off"


def latex_clean():
    from _fixture_project import project_text
    # claim text is normalized on the way out: --- → em-dash, an inter-word -- →
    # en-dash, LaTeX escapes resolved, braces stripped, trailing period dropped
    t = project_text([entry("a", claim=r"alpha --- beta, a\_b, and x--y")]).lower()
    assert "alpha — beta" in t, "--- not converted to an em-dash"
    assert "a_b" in t, "the \\_ escape was not resolved"
    assert "x–y" in t, "inter-word -- not converted to an en-dash"


# ── gate: resolution and the strict modes ────────────────────────────────────
def resolve_passes():
    from _fixture_gate import gate
    # RESOLVE: a cited claim whose check FAILS blocks the gate (the verdict is the
    # conjunction of every cited claim's check)
    assert gate([entry("c", claim="present", check="cmd:true")])[0] == 0, \
        "a passing cited check did not gate green"
    assert gate([entry("c", claim="present", check="cmd:false")])[0] != 0, \
        "a failing cited check did not block the gate"


def safe_rejects_postulates():
    from _fixture_gate import gate
    # --safe: an uncited placement (a block no prose cites) is a postulate — advised
    # against by default, REJECTED under --safe
    w = [entry("p", claim="cited prose", check="cmd:true"),
         entry("ph", emit="ph.txt", check="cmd:true")]            # placed, cited by nothing
    assert gate(w, assets={"ph.txt": "block\n"})[0] == 0, "an uncited placement was not tolerated by default"
    assert gate(w, "--safe", assets={"ph.txt": "block\n"})[0] != 0, "--safe did not reject the postulate"


def without_k_distinct():
    from _fixture_gate import gate
    # --without-K: two cited claims sharing ONE witness collapse (proof-irrelevance,
    # Axiom K); the flag forbids it, demanding a distinct witness per claim
    shared = [entry("a", claim="alpha", check="cmd:true"),
              entry("b", claim="beta", check="cmd:true", frm="a")]
    distinct = [entry("a", claim="alpha", check="cmd:true"),
                entry("b", claim="beta", check="file:w.bib", frm="a")]
    assert gate(shared)[0] == 0, "a shared witness is intolerable even without the flag"
    assert gate(shared, "--without-K")[0] != 0, "--without-K did not flag the collapse"
    assert gate(distinct, "--without-K")[0] == 0, "--without-K rejected distinct witnesses"


def jobs_parallel():
    from _fixture_gate import gate
    # --jobs: checks resolve concurrently (default all cores) and the verdict is
    # independent of the worker count — parallel ≡ serial
    ok = [entry("a", claim="alpha", check="cmd:true"),
          entry("b", claim="beta", check="cmd:true", frm="a")]
    bad = [entry("a", claim="alpha", check="cmd:true"),
           entry("b", claim="beta", check="cmd:false", frm="a")]
    assert gate(ok, "--jobs=1")[0] == 0 and gate(ok, "--jobs=8")[0] == 0, "parallel disagreed on a pass"
    assert gate(bad, "--jobs=1")[0] != 0 and gate(bad, "--jobs=8")[0] != 0, "parallel disagreed on a fail"


# ── adequacy: how Δ grades a check ───────────────────────────────────────────
# grade-ladder's witness is OWNED by the concept library (library/concepts.py) and imported here as
# `concept:grade-ladder` — the pitch face (README) imports the identical certificate.  It was
# byte-for-byte this module's old grade_ladder(), so the concept is now authored, graded, and proved
# ONCE, and this view inherits the owner's engine fingerprint rather than re-deriving it.
def mutation_probes():
    from _fixture_delta import discriminate
    # the grade is empirical: Δ corrupts each input and sees if the check flips from
    # pass to fail; the inputs whose corruption flips it are its sensitivity set
    recs = json.loads(discriminate(
        [entry("c", claim="c", check="cmd:grep -q TOKEN a.txt")],
        "--all", "--json", assets={"a.txt": "TOKEN\n"})[1])
    r = recs[0]
    assert r["grade"] == "behavioral" and "a.txt" in r.get("tests", []), \
        f"corrupting a.txt should flip the check (tests={r.get('tests')})"


def content_cache():
    # a Δ grade is cached PER CHECK on its READ footprint (the files it opens), over the
    # content key as the coarse soundness basis: a grade is a pure function of that content.
    import discriminate
    import resolver
    d = Path(tempfile.mkdtemp())
    try:
        (d / "paper.toml").write_text('[paper]\nwarrants = ["w.bib"]\nrubric = "r.tsv"\nout = "o.md"\n')
        (d / "w.bib").write_text("@misc{c,\n  section = {s},\n  claim = {x},\n  check = {cmd:grep -q ZZZ w.bib}\n}\n")
        (d / "r.tsv").write_text("s\tSec\n")
        # basis: content_key is stable, and moves when an input changes (a pure content hash — no strace)
        k1 = discriminate.content_key(d)
        assert k1 == discriminate.content_key(d), "content key not stable for unchanged inputs"
        # refinement: the per-check cache key is the check's READ footprint — a SUBSET of content, so an
        # unread file is not in it (the cache will not over-invalidate).  Φ·spawn·foot: test the footprint
        # PARSE over the check's trace (reads w.bib only) hermetically; the strace CAPTURE is
        # boundaries_footprint's (standard sandbox).  data.txt is written but never opened → not read.
        (d / "data.txt").write_text("unread by the check\n")
        trace = ('openat(AT_FDCWD, "/lib/libc.so.6", O_RDONLY|O_CLOEXEC) = 3\n'
                 'openat(AT_FDCWD, "w.bib", O_RDONLY) = 3\n')
        fp = resolver.parse_reads(trace, d, d)
        assert fp == ["w.bib"], f"footprint is not exactly the file the check reads: {fp}"
        assert "data.txt" not in fp, "an unread file entered the footprint — the cache would over-invalidate"
        (d / "w.bib").write_text((d / "w.bib").read_text() + "\n% changed\n")
        assert discriminate.content_key(d) != k1, "content key did not change when an input changed"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def footprint_scopes():
    # Δ traces each check's READ footprint (the files it opens), a SUPERSET of its
    # sensitivity set, so the footprint SCOPES the sweep — each check graded against what
    # it reads, not the whole repo.  An unread file is in neither the footprint nor the flip-set.
    import grader
    import resolver
    d = Path(tempfile.mkdtemp())
    try:
        (d / "a.txt").write_text("FOO\n")
        (d / "b.txt").write_text("unread\n")
        chk = "cmd:grep -q FOO a.txt"
        # Φ·spawn·foot — the footprint has a CAPTURE half (strace, a process op tested in the standard
        # sandbox by boundaries_footprint) and a PARSE half (which opens count as inputs — paperkit's
        # own logic).  A hermetic witness tests the PARSE over a representative trace: a real read
        # (a.txt), a FAILED open, a WRITE-ONLY output, a libc read outside the project — only a.txt is
        # an input.  (Running strace here would need the ptrace the hermetic mutation sandbox forbids.)
        trace = ('openat(AT_FDCWD, "/lib/libc.so.6", O_RDONLY|O_CLOEXEC) = 3\n'
                 'openat(AT_FDCWD, "a.txt", O_RDONLY) = 3\n'
                 'openat(AT_FDCWD, "nope.txt", O_RDONLY) = -1 ENOENT (No such file or directory)\n'
                 'openat(AT_FDCWD, "out.md", O_WRONLY|O_CREAT|O_TRUNC, 0644) = 4\n')
        fp = resolver.parse_reads(trace, d, d)
        assert fp == ["a.txt"], f"footprint should be the one read file: {fp}"
        baseline, sens = grader.sensitivity(chk, d, {}, None, footprint=fp)
        assert baseline and set(sens) <= set(fp), f"sensitivity is not within the read footprint: {sens}"
        assert "b.txt" not in sens, "an unread file flipped the check"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def module_split():
    # the engine is not a monolith but small single-responsibility modules — a resolver that
    # runs a check, a grader that sweeps it, a grade ladder that interprets the sweep, a cache,
    # a topology — each importable on its own; the leaf modules do not import the orchestrators,
    # so a change to one has a small blast radius.
    for mod in ("resolver", "grader", "grade", "cache", "layout"):
        assert (ENGINE / f"{mod}.py").exists(), f"engine module {mod}.py is missing"
    resolver_src = _src("resolver.py")
    assert "import gate" not in resolver_src and "concurrent.futures" not in resolver_src, \
        "the resolver imports the gate / its parallelism — not a small blast radius"
    grader_src = (ENGINE / "grader.py").read_text()
    assert "import gate" not in grader_src and "import project" not in grader_src, \
        "the grader imports gate/project — it would not be testable on its own"
    grade_src = (ENGINE / "grade.py").read_text()
    assert not any(f"import {m}" in grade_src for m in ("gate", "project", "grader", "resolver", "cache")), \
        "the grade ladder imports an orchestrator — it must be a pure leaf (Μ·grade: calc vs interp)"


def min_strength():
    from _fixture_delta import discriminate
    # --min-strength gates the grades: a project fails if any cited claim's check grades
    # BELOW the threshold — this is how the paper enforces its own proof-relevance
    strong = [entry("c", claim="c", check="cmd:grep -q TOKEN a.txt")]   # behavioral
    weak = [entry("c", claim="c", check="file:w.bib")]                  # vacuous
    rc_ok, _ = discriminate(strong, "--min-strength", "behavioral", assets={"a.txt": "TOKEN\n"})
    rc_bad, _ = discriminate(weak, "--min-strength", "behavioral")
    assert rc_ok == 0 and rc_bad != 0, f"--min-strength did not gate on grade (ok={rc_ok}, bad={rc_bad})"


# ── liveness: resumable pump/parse witnesses ─────────────────────────────────
def pump_parse_witness():
    # a slow check is structured as pump()/parse(): pump advances state one increment
    # (no verdict), parse reads done?/progress; the driver only loads → pump → serialize
    import driver
    class W:
        def initial(self): return {"c": 0}
        def pump(self, s): return {"c": s["c"] + 1}
        def parse(self, s): return {"done": s["c"] >= 3, "progress": f'{s["c"]}/3'}
        def serialize(self, s): return json.dumps(s)
        def deserialize(self, x): return json.loads(x)
    meaning, steps, done = driver.drive(W())
    assert done and steps == 3 and meaning["progress"] == "3/3", \
        f"the driver did not pump to completion (steps={steps}, {meaning})"


def resumable():
    # under a budget the driver stops short and persists its state (exit 2 = resume,
    # not failure); resuming from the token completes — a resumed run equals an
    # uninterrupted one
    import driver
    class W:
        def initial(self): return {"c": 0, "r": []}
        def pump(self, s): time.sleep(0.05); return {"c": s["c"] + 1, "r": s["r"] + [s["c"]]}
        def parse(self, s): return {"done": s["c"] >= 4, "results": s["r"]}
        def serialize(self, s): return json.dumps(s, sort_keys=True)
        def deserialize(self, x): return json.loads(x)
    sf = os.path.join(tempfile.mkdtemp(), "s.json")
    w = W()
    _, _, done1 = driver.drive(w, state_path=sf, budget=0.06)     # budget bites before 4 pumps
    assert not done1, "the budget did not stop the witness short"
    m2, _, done2 = driver.drive(w, state_path=sf, budget=0.0)     # resume; 0 = run to completion
    assert done2 and m2["results"] == [0, 1, 2, 3], f"resume did not complete faithfully ({m2})"


def roundtrip_obligation():
    # the one soundness obligation is deserialize(serialize(state)) == state; the driver
    # asserts it, so a witness whose serialization loses state is rejected
    import driver
    class Lossy:
        def initial(self): return {"c": 0, "keep": "x"}
        def pump(self, s): return {"c": s["c"] + 1, "keep": s["keep"]}
        def parse(self, s): return {"done": s["c"] >= 2}
        def serialize(self, s): return json.dumps({"c": s["c"]})   # DROPS "keep"
        def deserialize(self, x): return json.loads(x)
    try:
        driver.drive(Lossy())
    except AssertionError:
        return
    raise AssertionError("the driver did not enforce the round-trip obligation")


# ── rhetoric: typed moves and checkable schemes ──────────────────────────────
def prosody():
    # the clause-attachment layer is PROSODY, not glue: a typed move whose KIND and
    # default connector are a data-driven vocabulary (a new device is a new row)
    import rhetoric
    kinds = {rhetoric.kind_of(m) for m in rhetoric.MOVES}
    assert {"entail", "extend", "turn", "parallel", "restate"} <= kinds, f"missing move kinds ({kinds})"
    assert rhetoric.MOVES["consequence"][1] == "so ", "the consequence connector is not 'so '"
    assert rhetoric.kind_of("not-a-move") is None, "an unknown move was given a kind"


def scheme_count():
    # a section's scheme constrains its claim COUNT (a period is one beat, a tricolon three)
    import rhetoric
    assert rhetoric.check_scheme("period", ["a", "b"], ["addition"]), "period must reject two claims"
    assert rhetoric.check_scheme("tricolon", ["a", "b"], ["addition"]), "tricolon must reject two claims"
    assert rhetoric.check_scheme("tricolon", ["a", "b", "c"], ["addition", "addition"]) == [], \
        "tricolon must accept three parallel claims"


def scheme_opt_in():
    # schemes are OPT-IN: only a section that declares one in the rubric's 3rd column is
    # checked; a two-column row is unconstrained
    import rhetoric
    d = Path(tempfile.mkdtemp())
    try:
        (d / "r.tsv").write_text("a\tAlpha\nb\tBeta\tladder\n")     # only b declares a scheme
        sch = rhetoric.schemes_from_rubric(d / "r.tsv")
        assert sch == {"b": "ladder"}, f"only a declaring section should carry a scheme ({sch})"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def form_gate():
    # rhetoric makes FORM checkable like content: a section that declares a scheme is
    # gated — analyze flags a violation when its realized moves break it, none when they honor it
    import rhetoric
    d = Path(tempfile.mkdtemp())
    try:
        (d / "paper.toml").write_text('[paper]\nwarrants = ["w.bib"]\nrubric = "r.tsv"\nout = "o.md"\n')
        (d / "r.tsv").write_text("s\tSec\tladder\n")               # section s declares a ladder (entail-only)
        base = ("@misc{a,\n  section = {s},\n  claim = {alpha}\n}\n"
                "@misc{b,\n  section = {s}, from = {a}, move = {%s},\n  claim = {beta}\n}\n")
        (d / "w.bib").write_text(base % "antithesis")             # a turn beat breaks the ladder
        assert next(r[4] for r in rhetoric.analyze(d) if r[0] == "s"), "a turn beat should violate a ladder"
        (d / "w.bib").write_text(base % "consequence")            # an entail beat honors it
        assert next(r[4] for r in rhetoric.analyze(d) if r[0] == "s") == [], "an all-entail ladder should be clean"
    finally:
        shutil.rmtree(d, ignore_errors=True)
    # and THIS paper practices it: the rhetoric section declares a scheme (rubric 3rd column)
    # and its realized moves honor it, so the declaration is load-bearing, not decorative.
    rows = {r[0]: r for r in rhetoric.analyze(PAPER_DIR)}
    assert "rhetoric" in rows, "the rhetoric section should declare a scheme (rubric 3rd column)"
    assert rows["rhetoric"][4] == [], f"the paper's own rhetoric section violates its scheme: {rows['rhetoric'][4]}"


# ── projects: the repository as a family of verified documents ───────────────
def multi_project():
    # the repository is several paperkit projects — each a paper.toml directory that
    # projects a document — discovered by their paper.toml, not hard-coded
    import project as P
    root = Path(__file__).resolve().parents[2]
    tomls = [p for p in root.rglob("paper.toml") if ".git" not in p.parts]
    assert len(tomls) >= 4, f"expected several projects, found {len(tomls)}"
    for d in (root / "paper", root / "boundaries"):
        cfg = P.load_config(d)
        assert P.project(cfg) == cfg["out"].read_text(), f"{cfg['out'].name} is not its own projection"


def project_dag():
    # the projects form a DAG over the shared engine: the README IMPORTS the paper's
    # verdict (a result: edge — Ξ·seam), and the report ingests the paper's grades
    root = Path(__file__).resolve().parents[2]
    assert "result:paper" in (root / "warrants.bib").read_text(), \
        "the README's status claim does not import the paper's verdict (result:paper)"
    gen = (root / "report" / "gen.py").read_text()
    assert '_delta("paper")' in gen and "--json" in gen, \
        "the report does not ingest the paper's --json pipeline data"


def local_ci():
    # the local CI is ONE Bazel target: the pre-commit runs `bazel test //:hook`, which both gates
    # (per-claim checks + invariants) AND grades (Δ adequacy) every document — Ζ·foot folded
    # adequacy into the hook, so there is no separate --min-strength step in the pre-commit.
    # Ζ·hook·index — and the "never committed broken" clause is only sound if the hook also
    # verifies worktree≡index (else it gates bytes the commit does not land), so require BOTH
    # invocations.  Still names-not-entails (the standing warrant-adequacy-gap: a substring is
    # not the behaviour); the entailing witness is bnd-hook-index over the predicate's core.
    hook = (Path(__file__).resolve().parents[2] / ".githooks" / "pre-commit").read_text()
    assert "bazel test //:hook" in hook, "the pre-commit hook does not run `bazel test //:hook`"
    assert "tools/hook_index.py" in hook, "the pre-commit hook does not verify worktree≡index (Ζ·hook·index)"


def boundaries_project():
    # every engine tool ships a ⟨P, F, δ⟩ boundary suite, and those suites are gathered
    # as their own gated project (BOUNDARIES.md)
    import project as P
    root = Path(__file__).resolve().parents[2]
    suites = list((root / "paperkit" / "tests").glob("boundaries_*.py"))
    assert len(suites) >= 6, f"expected the tool boundary suites, found {len(suites)}"
    cfg = P.load_config(root / "boundaries")
    assert cfg["out"].name == "BOUNDARIES.md" and P.project(cfg) == cfg["out"].read_text(), \
        "the boundaries project does not project to BOUNDARIES.md"


def report_live():
    # the report's figures are live pipeline output — rendered from gate/Δ --json, not
    # scraped from human text — and the report projects to its own document
    import project as P
    root = Path(__file__).resolve().parents[2]
    gen = (root / "report" / "gen.py").read_text()
    assert "discriminate.py" in gen and "gate.py" in gen and "--json" in gen, \
        "the report does not render from machine-readable pipeline data"
    assert P.load_config(root / "report")["out"].name == "REPORT.md", "the report does not project to REPORT.md"


# ── implications: what follows, and the honest limits ────────────────────────
def fresh_by_construction():
    from _fixture_gate import gate
    from _fixture_project import project_text
    # because the document IS the projection, regeneration is idempotent and any
    # hand-edit is rejected — the prose cannot drift from its claims
    w = [entry("a", claim="alpha")]
    once, twice = project_text(w), project_text(w)
    assert once == twice, "projection is not idempotent"
    assert gate(w, out=once)[0] == 0 and gate(w, out=once + "\nedit\n")[0] != 0, \
        "a hand-edited (drifted) copy was not rejected"


def adequacy_gap():
    from _fixture_gate import gate
    # Π — ONE capability: the GATE is blind to relevance.  A passing check proves a sentence
    # NAMED a verifier, not that the verifier ENTAILS the claim, so a false sentence whose check
    # is behavioral-but-irrelevant still passes the gate.  That the GRADER even grades such a check
    # behavioral is a DISTINCT capability — the sibling claim crash-sensitive-limit owns it — so it
    # is not re-asserted here; re-asserting it dragged the whole grader into this claim's footprint
    # (Δ·scope then bounds adequacy-gap to the gate it actually exercises, not gate + grader).
    w = [entry("c", claim="the sky is green", check="cmd:grep -q TOKEN a.txt")]
    assert gate(w, assets={"a.txt": "TOKEN\n"})[0] == 0, "the gate cannot tell a check is irrelevant"


def trust_boundary():
    from _fixture_gate import gate
    # a check is arbitrary code (cmd: is the universal escape hatch), so gating a
    # document EXECUTES its checks — the warrant set is trusted code, like a Makefile.
    # Demonstrate: a cmd: check with a side effect runs when the document is gated.
    d = tempfile.mkdtemp()
    try:
        marker = os.path.join(d, "ran")
        gate([entry("c", claim="x", check=f"cmd:touch {marker}")])
        assert os.path.exists(marker), "gating did not execute the check — arbitrary code runs"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def env_sanitized():
    from _fixture_gate import gate
    # to bound that, a check runs in a controlled, default-deny environment: an ambient
    # variable that is not on the allow-list does NOT reach it, so a verdict cannot be
    # injected through the caller's environment (sshd's defence against env injection)
    os.environ["INJECTED_XYZ"] = "leaked"
    try:
        w = [entry("c", claim="x", check='cmd:test -z "$INJECTED_XYZ"')]
        assert gate(w)[0] == 0, "an un-allow-listed ambient var leaked into the check"
    finally:
        os.environ.pop("INJECTED_XYZ", None)


def path_surface():
    # Τ·path: clean_env DROPS PATH's relative/empty entries — the ones that resolve a tool to the cwd
    # (the project dir being gated) — so a document cannot shadow a tool by planting it beside itself.
    # The OWNED logic is clean_env's PATH filter, a PURE function of the input environment; testing it
    # over an explicit env needs no subprocess and no os.environ/cwd manipulation (the end-to-end
    # plant-a-tool-and-resolve DEMONSTRATION is a cwd/PATH process probe — boundaries_path, standard
    # sandbox; running it here would depend on the cwd/PATH the hermetic mutation sandbox controls).
    import resolver
    kept = resolver.clean_env(
        {"PATH": os.pathsep.join(["/usr/bin", ".", "", "reldir", "/bin"])})["PATH"].split(os.pathsep)
    assert "/usr/bin" in kept and "/bin" in kept, "clean_env dropped an ABSOLUTE PATH dir (the host's trust)"
    assert all(os.path.isabs(p) for p in kept if p), "clean_env kept a non-absolute PATH entry"
    assert not ({".", "", "reldir"} & set(kept)), \
        "clean_env kept a cwd-relative PATH entry — a document could shadow a tool beside itself"


def collapse_safe():
    # The proof that COLLAPSE is safe to delete, routed through the graph (not an ephemeral test):
    # replacing a collapsed claim's witness with consuming its premises preserves the proof's
    # discrimination — every input that flips it flips a premise (its fingerprint is covered), so the
    # premise's witness fails and blocks it; only an INCREMENT's residual escapes (no premise catches
    # it).  So emergence's collapse verdict is SOUND for deletion, its increment verdict a keep-warning.
    import coherence
    by = {r["key"]: r for r in [
        {"key": "ax", "rests-on": [], "tests": ["paperkit/gate.py::resolves"]},
        {"key": "col", "rests-on": ["ax"], "tests": ["paperkit/gate.py::resolves"]},
        {"key": "inc", "rests-on": ["ax"], "tests": ["paperkit/gate.py::resolves", "paperkit/project.py::weave"]},
    ]}
    e = coherence.emergence_residual(list(by.values()))
    # COLLAPSE ⇒ SAFE: nothing the collapsed claim discriminates escapes its premises.
    col_escapes = coherence._engine_cap(by["col"]["tests"]) - coherence._engine_cap(by["ax"]["tests"])
    assert e["collapse"] == 1 and not col_escapes, \
        "a collapsed claim discriminates an input no premise catches — deletion would lose it"
    # INCREMENT ⇒ KEEP: the residual is exactly the input no premise catches.
    assert ["inc", ["paperkit/project.py::weave"]] in e["increments"], \
        "the increment's escaping input was not surfaced as the keep-residual"


def forward_direction():
    import project as P
    # the structure residual is closed by PROJECTION: the grounding DAG renders as transitively-REDUCED
    # cross-references — a re-cited premise reachable by a LONGER rests-on path is redundant and dropped
    # (transitive_reduction, the `drop` rung of drop < cite < expound < figure).  Behavioral (Ε·behavioral).
    assert P.transitive_reduction({"c": ["a", "b"], "b": ["a"]}) == {"c": ["b"], "b": ["a"]}, \
        "did not drop the redundant c→a edge (a is already reachable from c via b)"
    assert P.transitive_reduction({"c": ["a"], "b": ["a"]}) == {"c": ["a"], "b": ["a"]}, \
        "dropped a direct grounding edge that has no longer path"


CLAIMS = {
    "collapse-safe": collapse_safe,
    "fresh-by-construction": fresh_by_construction,
    "adequacy-gap": adequacy_gap,
    "trust-boundary": trust_boundary,
    "env-sanitized": env_sanitized,
    "path-surface": path_surface,
    "forward-direction": forward_direction,
    "multi-project": multi_project,
    "project-dag": project_dag,
    "local-ci": local_ci,
    "boundaries-project": boundaries_project,
    "report-live": report_live,
    "prosody": prosody,
    "scheme-count": scheme_count,
    "scheme-opt-in": scheme_opt_in,
    "form-gate": form_gate,
    "pump-parse-witness": pump_parse_witness,
    "resumable": resumable,
    "roundtrip-obligation": roundtrip_obligation,
    "mutation-probes": mutation_probes,
    "content-cache": content_cache,
    "footprint-scopes": footprint_scopes,
    "module-split": module_split,
    "min-strength": min_strength,
    "resolve-passes": resolve_passes,
    "safe-rejects-postulates": safe_rejects_postulates,
    "without-k-distinct": without_k_distinct,
    "jobs-parallel": jobs_parallel,
    "weave-sentence": weave_sentence,
    "connector-resolution": connector_resolution,
    "emit-placement": emit_placement,
    "config-flags": config_flags,
    "latex-clean": latex_clean,
    "edge-from-orders": edge_from_orders,
    "edge-chiral": edge_chiral,
    "edge-move-types": edge_move_types,
    "paper-is-paperkit": paper_is_paperkit,
    "prose-is-projection": prose_is_projection,
    "closes-gap": closes_gap,
    "unverified-cant-ship": unverified_cant_ship,
    "not-project": not_project,
    "paperkit-on-paperkit": paperkit_on_paperkit,
    "one-green-check": one_green_check,
    "node-is-claim": node_is_claim,
    "claims-are-warrants": claims_are_warrants,
    "dataset-backed": dataset_backed,
    "dataset-fresh": dataset_fresh,
    "agree-builtin": agree_builtin,
    "result-builtin": result_builtin,
    "file-builtin": file_builtin,
    "cmd-builtin": cmd_builtin,
    "prose-is-artifact": prose_is_artifact,
    "edit-cant-survive": edit_cant_survive,
    "coverage-both-sides": coverage_both_sides,
    "every-section-appears": every_section_appears,
    "every-claim-cited": every_claim_cited,
    "record-is-bibentry": record_is_bibentry,
    "prose-projected": prose_projected,
    "ordered-by-deps": ordered_by_deps,
    "joined-by-glue": joined_by_glue,
    "deterministic": deterministic,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in CLAIMS:
        print(f"usage: claims.py <{'|'.join(CLAIMS)}>", file=sys.stderr)
        return 2
    key = argv[1]
    try:
        CLAIMS[key]()
    except AssertionError as e:
        print(f"claim {key}: FAIL — {e}", file=sys.stderr)
        return 1
    print(f"claim {key}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
