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

ENGINE = Path(__file__).resolve().parents[2] / "paperkit"
PAPER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests"))
import gate  # noqa: E402
import project as P  # noqa: E402
import discriminate  # noqa: E402  (Δ: the adequacy grader)
import driver  # noqa: E402  (the pump/parse liveness driver)
import rhetoric  # noqa: E402  (the move/scheme vocabulary)
import coherence  # noqa: E402  (∂²: declared grounding vs measured sensitivity)
import _fixture as fx  # noqa: E402  (the validated fixture builder — counter-fixtures)

GATE_SRC = (ENGINE / "gate.py").read_text()
PROJECT_SRC = (ENGINE / "project.py").read_text()


def _parse(bib_text):
    """Parse one .bib through the real engine parser; return its record fields."""
    d = tempfile.mkdtemp()
    try:
        p = Path(d) / "t.bib"
        p.write_text(bib_text)
        return P.entries(p)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def verifier_named():
    # "a claim's verifier is named type:target" — the resolver splits on the ':'
    assert 'partition(":")' in GATE_SRC, "resolver no longer splits type:target"


def gate_dispatches():
    # "dispatches through a small registry" — built-in file/cmd branches + custom
    for needle in ('typ == "file"', 'typ == "cmd"', "typ in custom"):
        assert needle in GATE_SRC, f"resolver missing dispatch branch: {needle}"


def new_domain_adds():
    # "a new domain adds verifiers, not editing the engine" — a type supplied only
    # in the custom registry resolves; an unregistered one does not
    assert gate.resolves("demo:x", ENGINE, {"demo": {"cmd": "true"}}) is True, \
        "a registry-supplied check type does not resolve"
    assert gate.resolves("demo:x", ENGINE, {}) is False, \
        "an unregistered check type must not resolve"


def two_builtins():
    # "two verifiers ship built in" — exactly file and cmd (others come from config)
    builtins = set(re.findall(r'typ == "(\w+)"', GATE_SRC))
    assert builtins == {"file", "cmd"}, f"built-in types are {builtins}, expected file & cmd"


def dataset_backed():
    # "a custom verifier may interpret a dataset the project SHIPS … a single edit can
    # falsify" — a check whose command reads a project file resolves true while the file
    # matches and flips false on a one-line edit to that shipped dataset.
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
    d = Path(tempfile.mkdtemp())
    try:
        (d / "producer.py").write_text("print('CANON-V1')")
        custom = {"fresh": {"cmd": "python3 -c \"import subprocess,sys; "
                                   "canon=subprocess.run([sys.executable,'producer.py'],capture_output=True,text=True).stdout.strip(); "
                                   "sys.exit(0 if open('asset.txt').read().strip()==canon else 1)\""}}
        (d / "asset.txt").write_text("CANON-V1\n")
        assert gate.resolves("fresh:x", d, custom) is True, "a committed asset matching its producer must pass"
        (d / "asset.txt").write_text("STALE\n")
        assert gate.resolves("fresh:x", d, custom) is False, "an asset drifted from its producer must fail"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def file_builtin():
    # "file, that an artifact exists"
    assert gate.resolves("file:gate.py", ENGINE, {}) is True, "file: of an existing path failed"
    assert gate.resolves("file:does-not-exist.xyz", ENGINE, {}) is False, "file: of a missing path passed"


def cmd_builtin():
    # "cmd, that a script exits zero"
    assert gate.resolves("cmd:true", ENGINE, {}) is True, "cmd:true did not pass"
    assert gate.resolves("cmd:false", ENGINE, {}) is False, "cmd:false did not fail"


def cmd_escape():
    # "cmd is the hatch every other check reduces to" — a custom type resolves by
    # running its cmd template; a type with no cmd behind it does not resolve
    assert gate.resolves("demo:x", ENGINE, {"demo": {"cmd": "true"}}) is True, \
        "a custom type did not reduce to its cmd"
    assert gate.resolves("demo:x", ENGINE, {}) is False, \
        "an unregistered type resolved with nothing behind it"


# ── engine section ───────────────────────────────────────────────────────────
def projector_emits():
    # "the projector emits the whole document from the warrant set" — project a
    # two-section fixture; the whole document (title + every section + the claim) appears
    text = fx.project_text([fx.entry("x", claim="anchor phrase")],
                           rubric=(("s", "Sec One"), ("t", "Sec Two")), title="Doc")
    for needle in ("# Doc", "## Sec One", "## Sec Two", "anchor phrase"):
        assert needle.lower() in text.lower(), f"projection is missing {needle!r}"


def prose_is_artifact():
    # "the committed prose is a build artifact, not a source" — the projector has a
    # --check mode that compares the committed file against a fresh projection
    assert "--check" in PROJECT_SRC and "read_text() != out" in PROJECT_SRC, \
        "projector can no longer detect a hand-edit against its projection"


def gate_rejects_drift():
    # "the gate rejects prose that has drifted" — counter-fixture: canonical passes, drift fails
    w = [fx.entry("x", claim="anchored")]
    canonical = fx.project_text(w)
    assert fx.gate(w, out=canonical)[0] == 0, "gate rejected the exact projection"
    assert fx.gate(w, out=canonical + "\nHAND-EDITED DRIFT\n")[0] != 0, "gate accepted drifted prose"


def edit_cant_survive():
    # "a hand-edit cannot survive a build" — only the exact projection passes the gate
    w = [fx.entry("x", claim="anchored")]
    canonical = fx.project_text(w)
    assert fx.gate(w, out=canonical)[0] == 0
    for edit in ("PREPENDED\n" + canonical, canonical + "\nAPPENDED\n", canonical + "x"):
        assert edit != canonical and fx.gate(w, out=edit)[0] != 0, "a hand-edit survived the build"


def coverage_both_sides():
    # "coverage is enforced from both sides" — section-present AND claim-cited branches
    assert "absent" in GATE_SRC and "not cited" in GATE_SRC, "coverage no longer checks both directions"


def every_section_appears():
    # "every required section must appear"
    assert "not in headings" in GATE_SRC, "gate no longer checks each section appears"


def every_claim_cited():
    # "every claim tagged for a section must be cited within it"
    assert "k not in cited" in GATE_SRC, "gate no longer checks each tagged claim is cited"


# ── model section ────────────────────────────────────────────────────────────
def claim_is_record():
    # "a claim is a single record — a statement, its section, its dependencies, its verifier"
    rec = _parse("@misc{k,\n  section = {s},\n  from = {d},\n"
                 "  claim = {a statement},\n  check = {file:x}\n}\n")["k"]
    for field in ("claim", "section", "from", "check"):
        assert rec.get(field), f"a claim record is missing its {field}"


def record_is_bibentry():
    # "which is exactly the shape of a bibliography entry" — a standard reference
    # entry parses through the very same record parser
    recs = _parse("@misc{ref,\n  author = {Knuth},\n  year = {1984},\n"
                  "  title = {Literate Programming}\n}\n")
    assert recs.get("ref", {}).get("title") and recs["ref"].get("author"), \
        "a standard bibliography entry no longer parses as a record"


def prose_projected():
    # "the prose is projected, not authored" — the prose tracks the warrants
    a = fx.project_text([fx.entry("x", claim="zzfirst wording")]).lower()
    b = fx.project_text([fx.entry("x", claim="zzsecond wording")]).lower()
    assert "zzfirst" in a and "zzsecond" in b and a != b, \
        "prose does not track the warrants (it is authored, not projected)"


def ordered_by_deps():
    # "within each section the claims are ordered by their dependency edges"
    t = fx.project_text([fx.entry("b", claim="zzbeta", frm="a"),
                         fx.entry("a", claim="zzalpha")]).lower()
    assert t.index("zzalpha") < t.index("zzbeta"), "claims are not ordered by dependency edges"


def joined_by_glue():
    # "joined by connective glue" — an explicit glue connector is woven between edges
    t = fx.project_text([fx.entry("a", claim="zzalpha"),
                         fx.entry("b", claim="zzbeta", frm="a", glue="BECAUSE")]).lower()
    assert "because zzbeta" in t, "explicit glue is not woven between dependent claims"


def deterministic():
    # "the same warrant set always giving the same document"
    w1 = [fx.entry("a", claim="zzalpha")]
    w2 = [fx.entry("a", claim="zzomega")]
    assert fx.project_text(w1) == fx.project_text(w1), "same warrants gave different documents"
    assert fx.project_text(w1) != fx.project_text(w2), "the document is independent of its warrants"
    assert "zzalpha" in fx.project_text(w1).lower()


# ── Π·foundations: the vacuous atoms the grounding DAG rests on ───────────────
def node_is_claim():
    # each node of the claim-DAG is a single claim record
    recs = _parse("@misc{n,\n  section = {s},\n  claim = {a single statement},\n  check = {file:x}\n}\n")
    assert len(recs) == 1 and recs["n"].get("claim") == "a single statement", \
        "a warrant node is not a single claim"


def claim_bears_check():
    # each claim carries a verifier, and the verifier is machine-checkable (the gate runs it)
    rec = _parse("@misc{c,\n  section = {s},\n  claim = {x},\n  check = {cmd:true}\n}\n")["c"]
    assert rec.get("check") == "cmd:true", "the claim carries no check"
    assert gate.resolves("cmd:true", ENGINE, {}) is True and gate.resolves("cmd:false", ENGINE, {}) is False, \
        "the verifier is not machine-checkable"


def paper_is_projection():
    # a paper IS the projection of its claim-DAG: project emits the claims as the document
    t = fx.project_text([fx.entry("a", claim="alpha thesis"),
                         fx.entry("b", claim="beta point", frm="a")], title="Doc").lower()
    for needle in ("# doc", "alpha thesis", "beta point"):
        assert needle in t, f"the paper is not the projection of its claim-DAG ({needle!r} missing)"


def claims_are_warrants():
    # this paper's claims ARE its warrants: warrants.bib parses to the cited claim records
    recs = P.entries(PAPER_DIR / "warrants.bib")
    assert recs.get("paper-is-projection", {}).get("claim"), "the paper's claims are not its warrants"


def gate_is_subject():
    # the gate that accepts this paper is its subject: gate.py implements the very invariants
    # the paper describes (projection-equality, check-resolution, coverage)
    for inv in ("PROJECT", "RESOLVE", "COVERAGE"):
        assert inv in GATE_SRC, f"gate.py does not implement the {inv} invariant the paper describes"


# ── Π·selfhost: the drift-caught negative-assertions, as Φ counter-fixtures ───
def paperkit_on_paperkit():
    # run paperkit on paperkit: project a fixture, confirm the gate ACCEPTS the
    # faithful projection and REJECTS a drift of it
    w = [fx.entry("x", claim="self applied")]
    good = fx.project_text(w)
    assert fx.gate(w, out=good)[0] == 0, "the gate rejected paperkit's own faithful projection"
    assert fx.gate(w, out=good + "\nHAND-EDITED DRIFT\n")[0] != 0, "the gate accepted a drifted projection"


def one_green_check():
    # the document's correctness and the tool's are ONE green check: a single gate
    # invocation verifies the projection (document) AND runs the verifier (tool) —
    # breaking either side fails the same gate
    w = [fx.entry("x", claim="one check", check="cmd:true")]
    good = fx.project_text(w)
    assert fx.gate(w, out=good)[0] == 0, "the single gate check did not pass"
    assert fx.gate(w, out=good + "\nx\n")[0] != 0, "drift (document side) did not fail the gate"
    bad_check = [fx.entry("x", claim="one check", check="cmd:false")]
    assert fx.gate(bad_check, out=good)[0] != 0, "check failure (tool side) did not fail the gate"


# ── Π·distinct-witnesses: split the shared projection-stable group (--without-K) ──
def fail_omits():
    # a claim whose verifier FAILS cannot ship: the gate refuses the document
    ok = [fx.entry("x", claim="present", check="cmd:true")]
    bad = [fx.entry("x", claim="present", check="cmd:false")]
    good = fx.project_text(ok)
    assert fx.gate(ok, out=good)[0] == 0, "a claim with a passing verifier did not ship"
    assert fx.gate(bad, out=good)[0] != 0, "a claim with a FAILING verifier still shipped"


def paper_is_paperkit():
    # this paper is itself a paperkit project: a well-formed config projecting to paper.md
    cfg = P.load_config(PAPER_DIR)
    assert (PAPER_DIR / "paper.toml").exists() and cfg["bibs"] and cfg["rubric"].exists(), \
        "the paper is not a well-formed paperkit project"
    assert cfg["out"].name == "paper.md", "the paper does not project to paper.md"


def prose_is_projection():
    # the paper's prose IS the projection of its warrants
    cfg = P.load_config(PAPER_DIR)
    assert P.project(cfg) == cfg["out"].read_text(), "paper.md is not the projection of its warrants"


def closes_gap():
    # closes the say/check gap: every claim in the ledger carries a verifier
    F = P.entries(PAPER_DIR / "warrants.bib")
    missing = [k for k, f in F.items() if f.get("section") and f.get("claim") and not f.get("check")]
    assert not missing, f"claims without a verifier (the gap is open): {missing}"


def unverified_cant_ship():
    # an unverified sentence cannot ship: one failing verifier blocks the whole document
    w = [fx.entry("a", claim="verified", check="cmd:true"),
         fx.entry("b", claim="unverified", frm="a", check="cmd:false")]
    assert fx.gate(w, out=fx.project_text(w))[0] != 0, "a document with an unverified sentence shipped"


def not_project():
    # ...because it does not project: only the exact projection ships
    w = [fx.entry("x", claim="canonical")]
    good = fx.project_text(w)
    assert fx.gate(w, out=good)[0] == 0, "the canonical projection was rejected"
    assert fx.gate(w, out="not the projection\n")[0] != 0, "a non-projection shipped"


# ── edges: the three dependency graphs (from / rests-on / move) ───────────────
def edge_from_orders():
    # `from` fixes prose order — a claim is projected only AFTER the claims it lists,
    # so document order is a topological sort of the from-graph (keys given scrambled)
    t = fx.project_text([fx.entry("c", claim="gamma", frm="b"),
                         fx.entry("a", claim="alpha"),
                         fx.entry("b", claim="beta", frm="a")]).lower()
    ia, ib, ic = (t.find(x) for x in ("alpha", "beta", "gamma"))
    assert -1 < ia < ib < ic, "from did not order the prose alpha→beta→gamma"


def edge_rests_grounds():
    # rests-on is a SEPARATE grounding edge: effective grade clamps to the weakest
    # premise along it.  A behavioral thesis resting on a vacuous atom clamps to vacuous.
    recs = json.loads(fx.discriminate(
        [fx.entry("atom", claim="atom", check="file:w.bib"),                  # vacuous (presupposed)
         fx.entry("thesis", claim="thesis", check="cmd:grep -q TOKEN a.txt",  # behavioral
                  frm="atom", rests="atom")],
        "--all", "--json", assets={"a.txt": "TOKEN\n"})[1])
    th = next(r for r in recs if r["key"] == "thesis")
    assert th["grade"] == "behavioral" and th["effective_grade"] == "vacuous", \
        f"rests-on did not clamp the thesis (self={th['grade']}, eff={th['effective_grade']})"


def edge_chiral():
    # grounding is independent of prose adjacency: rests-on clamps even when the
    # premise is NOT a from-neighbor (the two graphs diverge / reverse)
    recs = json.loads(fx.discriminate(
        [fx.entry("atom", claim="atom", check="file:w.bib"),                  # vacuous
         fx.entry("mid", claim="mid", check="cmd:grep -q TOKEN a.txt"),       # the prose neighbor
         fx.entry("thesis", claim="thesis", check="cmd:grep -q TOKEN a.txt",
                  frm="mid", rests="atom")],                                  # prose←mid, grounding←atom
        "--all", "--json", assets={"a.txt": "TOKEN\n"})[1])
    th = next(r for r in recs if r["key"] == "thesis")
    assert "atom" in th.get("rests-on", []) and "atom" not in th.get("from", []), \
        "fixture should ground on a non-prose-neighbor"
    assert th["effective_grade"] == "vacuous", \
        "rests-on did not clamp despite atom not being a from-neighbor"


def edge_move_types():
    # the `move` field names a typed relation; its KIND decides its role, and a
    # section's scheme admits only certain kinds
    assert rhetoric.kind_of("consequence") == "entail", "consequence is not an entail move"
    assert rhetoric.kind_of("antithesis") == "turn", "antithesis is not a turn move"
    ok = rhetoric.check_scheme("ladder", ["a", "b"], ["consequence"])
    bad = rhetoric.check_scheme("ladder", ["a", "b"], ["antithesis"])
    assert ok == [] and bad, "a ladder must admit consequence (entail) and reject antithesis (turn)"


# ── projection: the projector's mechanics ────────────────────────────────────
def weave_sentence():
    # a section's claims weave into ONE paragraph: first clause capitalized, each
    # carries its own citation tag, the rest attach inline (not one bullet per claim)
    t = fx.project_text([fx.entry("a", claim="alpha beat"),
                         fx.entry("b", claim="beta beat", frm="a")])
    para = next(ln for ln in t.splitlines() if "@a]" in ln)
    assert "@b]" in para, "claims were not woven into one paragraph"
    assert para.lstrip()[:5] == "Alpha", "first clause was not capitalized"


def connector_resolution():
    # the connector between adjacent clauses resolves by priority: an explicit `join`
    # overrides a `move`'s default connector
    won = fx.project_text([fx.entry("a", claim="alpha"),
                           fx.entry("b", claim="beta", frm="a", join="; therefore, ", move="apposition")])
    assert "therefore" in won and "that is" not in won, "explicit join did not override the move connector"
    # a `move` with no `join` falls back to the move's typed connector (apposition → " — that is, ")
    fell = fx.project_text([fx.entry("a", claim="alpha"),
                            fx.entry("b", claim="beta", frm="a", move="apposition")])
    assert "that is" in fell, "the move's connector was not used as the fallback"


def emit_placement():
    # an `emit` warrant is placed VERBATIM (not woven), fenced by the asset's
    # extension; an image asset is placed as a markdown image instead
    code = fx.project_text([fx.entry("e", claim="example", emit="ex.sh")],
                           assets={"ex.sh": "echo hi\n"})
    assert "```sh" in code and "echo hi" in code, "shell asset not placed, fenced as sh"
    img = fx.project_text([fx.entry("g", claim="a figure", emit="fig.svg")],
                          assets={"fig.svg": "<svg></svg>\n"})
    assert "![a figure](fig.svg)" in img, "image asset not placed as a markdown image"


def config_flags():
    # projection structure is configured, not hard-coded: `numbered` toggles section
    # numbers, `references` toggles the bibliography heading
    on = fx.project_text([fx.entry("a", claim="x")], numbered=True, references=True)
    off = fx.project_text([fx.entry("a", claim="x")], numbered=False, references=False)
    assert "## 1." in on and "## References" in on, "flags not honored when on"
    assert "## 1." not in off and "References" not in off, "flags not honored when off"


def latex_clean():
    # claim text is normalized on the way out: --- → em-dash, an inter-word -- →
    # en-dash, LaTeX escapes resolved, braces stripped, trailing period dropped
    t = fx.project_text([fx.entry("a", claim=r"alpha --- beta, a\_b, and x--y")]).lower()
    assert "alpha — beta" in t, "--- not converted to an em-dash"
    assert "a_b" in t, "the \\_ escape was not resolved"
    assert "x–y" in t, "inter-word -- not converted to an en-dash"


# ── gate: resolution and the strict modes ────────────────────────────────────
def resolve_passes():
    # RESOLVE: a cited claim whose check FAILS blocks the gate (the verdict is the
    # conjunction of every cited claim's check)
    assert fx.gate([fx.entry("c", claim="present", check="cmd:true")])[0] == 0, \
        "a passing cited check did not gate green"
    assert fx.gate([fx.entry("c", claim="present", check="cmd:false")])[0] != 0, \
        "a failing cited check did not block the gate"


def safe_rejects_postulates():
    # --safe: an uncited placement (a block no prose cites) is a postulate — advised
    # against by default, REJECTED under --safe
    w = [fx.entry("p", claim="cited prose", check="cmd:true"),
         fx.entry("ph", emit="ph.txt", check="cmd:true")]            # placed, cited by nothing
    assert fx.gate(w, assets={"ph.txt": "block\n"})[0] == 0, "an uncited placement was not tolerated by default"
    assert fx.gate(w, "--safe", assets={"ph.txt": "block\n"})[0] != 0, "--safe did not reject the postulate"


def without_k_distinct():
    # --without-K: two cited claims sharing ONE witness collapse (proof-irrelevance,
    # Axiom K); the flag forbids it, demanding a distinct witness per claim
    shared = [fx.entry("a", claim="alpha", check="cmd:true"),
              fx.entry("b", claim="beta", check="cmd:true", frm="a")]
    distinct = [fx.entry("a", claim="alpha", check="cmd:true"),
                fx.entry("b", claim="beta", check="file:w.bib", frm="a")]
    assert fx.gate(shared)[0] == 0, "a shared witness is intolerable even without the flag"
    assert fx.gate(shared, "--without-K")[0] != 0, "--without-K did not flag the collapse"
    assert fx.gate(distinct, "--without-K")[0] == 0, "--without-K rejected distinct witnesses"


def jobs_parallel():
    # --jobs: checks resolve concurrently (default all cores) and the verdict is
    # independent of the worker count — parallel ≡ serial
    ok = [fx.entry("a", claim="alpha", check="cmd:true"),
          fx.entry("b", claim="beta", check="cmd:true", frm="a")]
    bad = [fx.entry("a", claim="alpha", check="cmd:true"),
           fx.entry("b", claim="beta", check="cmd:false", frm="a")]
    assert fx.gate(ok, "--jobs=1")[0] == 0 and fx.gate(ok, "--jobs=8")[0] == 0, "parallel disagreed on a pass"
    assert fx.gate(bad, "--jobs=1")[0] != 0 and fx.gate(bad, "--jobs=8")[0] != 0, "parallel disagreed on a fail"


def mem_lease():
    # mem: a check may declare a memory lease, routed through the vendored membudget
    # semaphore when a user scope is available — the lease never changes the verdict
    assert gate._MB_SCRIPT.exists(), "membudget is not vendored beside the engine"
    leased = [fx.entry("a", claim="alpha", check="cmd:true", mem="256"),
              fx.entry("b", claim="beta", check="cmd:false", frm="a", mem="256")]
    plain = [fx.entry("a", claim="alpha", check="cmd:true"),
             fx.entry("b", claim="beta", check="cmd:false", frm="a")]
    assert fx.gate(leased)[0] == fx.gate(plain)[0] != 0, "a mem lease changed the verdict"


# ── adequacy: how Δ grades a check ───────────────────────────────────────────
def grade_ladder():
    # Δ grades each check on a ladder by how much it can fail: a presupposed file: is
    # vacuous (no change removes it), a content-sensitive cmd: is behavioral
    recs = json.loads(fx.discriminate(
        [fx.entry("vac", claim="v", check="file:w.bib"),
         fx.entry("beh", claim="b", check="cmd:grep -q TOKEN a.txt", frm="vac")],
        "--all", "--json", assets={"a.txt": "TOKEN\n"})[1])
    g = {r["key"]: r["grade"] for r in recs}
    assert g["vac"] == "vacuous" and g["beh"] == "behavioral", f"grade ladder wrong: {g}"


def mutation_probes():
    # the grade is empirical: Δ corrupts each input and sees if the check flips from
    # pass to fail; the inputs whose corruption flips it are its sensitivity set
    recs = json.loads(fx.discriminate(
        [fx.entry("c", claim="c", check="cmd:grep -q TOKEN a.txt")],
        "--all", "--json", assets={"a.txt": "TOKEN\n"})[1])
    r = recs[0]
    assert r["grade"] == "behavioral" and "a.txt" in r.get("tests", []), \
        f"corrupting a.txt should flip the check (tests={r.get('tests')})"


def content_cache():
    # a Δ grade is a pure function of a CONTENT KEY (the project + engine files a check
    # could read), so it can be cached and recomputed only when that key changes
    d = Path(tempfile.mkdtemp())
    try:
        (d / "paper.toml").write_text('[paper]\nwarrants = ["w.bib"]\nrubric = "r.tsv"\nout = "o.md"\n')
        (d / "w.bib").write_text("@misc{c,\n  section = {s},\n  claim = {x},\n  check = {cmd:true}\n}\n")
        (d / "r.tsv").write_text("s\tSec\n")
        k1 = discriminate.content_key(d)
        assert k1 == discriminate.content_key(d), "content key not stable for unchanged inputs"
        (d / "w.bib").write_text((d / "w.bib").read_text() + "\n% changed\n")
        assert discriminate.content_key(d) != k1, "content key did not change when an input changed"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def sandbox_grade():
    # grading runs in a sandbox copy whose mutation surface excludes SIBLING projects
    # (a nested dir with its own paper.toml), so a project grades independently of them
    d = Path(tempfile.mkdtemp())
    try:
        (d / "paper.toml").write_text("[paper]\n")
        (d / "main.py").write_text("own\n")
        (d / "sub").mkdir()
        (d / "sub" / "paper.toml").write_text("[paper]\n")          # a nested sibling project
        (d / "sub" / "inner.py").write_text("theirs\n")
        assert (d / "sub") in discriminate._nested_roots(d), "nested project not detected"
        names = [f.name for f in discriminate.sandbox_files(d, set())]
        assert "main.py" in names and "inner.py" not in names, \
            f"surface should keep own files, drop the sibling's (got {names})"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def min_strength():
    # --min-strength gates the grades: a project fails if any cited claim's check grades
    # BELOW the threshold — this is how the paper enforces its own proof-relevance
    strong = [fx.entry("c", claim="c", check="cmd:grep -q TOKEN a.txt")]   # behavioral
    weak = [fx.entry("c", claim="c", check="file:w.bib")]                  # vacuous
    rc_ok, _ = fx.discriminate(strong, "--min-strength", "behavioral", assets={"a.txt": "TOKEN\n"})
    rc_bad, _ = fx.discriminate(weak, "--min-strength", "behavioral")
    assert rc_ok == 0 and rc_bad != 0, f"--min-strength did not gate on grade (ok={rc_ok}, bad={rc_bad})"


# ── liveness: resumable pump/parse witnesses ─────────────────────────────────
def pump_parse_witness():
    # a slow check is structured as pump()/parse(): pump advances state one increment
    # (no verdict), parse reads done?/progress; the driver only loads → pump → serialize
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
    kinds = {rhetoric.kind_of(m) for m in rhetoric.MOVES}
    assert {"entail", "extend", "turn", "parallel", "restate"} <= kinds, f"missing move kinds ({kinds})"
    assert rhetoric.MOVES["consequence"][1] == "so ", "the consequence connector is not 'so '"
    assert rhetoric.kind_of("not-a-move") is None, "an unknown move was given a kind"


def scheme_count():
    # a section's scheme constrains its claim COUNT (a period is one beat, a tricolon three)
    assert rhetoric.check_scheme("period", ["a", "b"], ["addition"]), "period must reject two claims"
    assert rhetoric.check_scheme("tricolon", ["a", "b"], ["addition"]), "tricolon must reject two claims"
    assert rhetoric.check_scheme("tricolon", ["a", "b", "c"], ["addition", "addition"]) == [], \
        "tricolon must accept three parallel claims"


def scheme_opt_in():
    # schemes are OPT-IN: only a section that declares one in the rubric's 3rd column is
    # checked; a two-column row is unconstrained
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


# ── projects: the repository as a family of verified documents ───────────────
def multi_project():
    # the repository is several paperkit projects — each a paper.toml directory that
    # projects a document — discovered by their paper.toml, not hard-coded
    root = Path(__file__).resolve().parents[2]
    tomls = [p for p in root.rglob("paper.toml") if ".git" not in p.parts]
    assert len(tomls) >= 4, f"expected several projects, found {len(tomls)}"
    for d in (root / "paper", root / "boundaries"):
        cfg = P.load_config(d)
        assert P.project(cfg) == cfg["out"].read_text(), f"{cfg['out'].name} is not its own projection"


def project_dag():
    # the projects form a DAG over the shared engine: the README's gate runs the paper's
    # gate, and the report ingests the paper's machine-readable grades
    root = Path(__file__).resolve().parents[2]
    assert "gate.py paper" in (root / "warrants.bib").read_text(), \
        "the README's status check does not gate the paper"
    gen = (root / "report" / "gen.py").read_text()
    assert '_delta("paper")' in gen and "--json" in gen, \
        "the report does not ingest the paper's --json pipeline data"


def local_ci():
    # a pre-commit githook is the local CI: every commit must leave each document green
    # (--safe --without-K) and the paper behaviorally adequate (--min-strength behavioral)
    hook = (Path(__file__).resolve().parents[2] / ".githooks" / "pre-commit").read_text()
    for needle in ("--safe --without-K", "--min-strength behavioral", "gate.py"):
        assert needle in hook, f"the pre-commit hook does not run {needle!r}"


def boundaries_project():
    # every engine tool ships a ⟨P, F, δ⟩ boundary suite, and those suites are gathered
    # as their own gated project (BOUNDARIES.md)
    root = Path(__file__).resolve().parents[2]
    suites = list((root / "paperkit" / "tests").glob("boundaries_*.py"))
    assert len(suites) >= 6, f"expected the tool boundary suites, found {len(suites)}"
    cfg = P.load_config(root / "boundaries")
    assert cfg["out"].name == "BOUNDARIES.md" and P.project(cfg) == cfg["out"].read_text(), \
        "the boundaries project does not project to BOUNDARIES.md"


def report_live():
    # the report's figures are live pipeline output — rendered from gate/Δ --json, not
    # scraped from human text — and the report projects to its own document
    root = Path(__file__).resolve().parents[2]
    gen = (root / "report" / "gen.py").read_text()
    assert "discriminate.py" in gen and "gate.py" in gen and "--json" in gen, \
        "the report does not render from machine-readable pipeline data"
    assert P.load_config(root / "report")["out"].name == "REPORT.md", "the report does not project to REPORT.md"


# ── implications: what follows, and the honest limits ────────────────────────
def fresh_by_construction():
    # because the document IS the projection, regeneration is idempotent and any
    # hand-edit is rejected — the prose cannot drift from its claims
    w = [fx.entry("a", claim="alpha")]
    once, twice = fx.project_text(w), fx.project_text(w)
    assert once == twice, "projection is not idempotent"
    assert fx.gate(w, out=once)[0] == 0 and fx.gate(w, out=once + "\nedit\n")[0] != 0, \
        "a hand-edited (drifted) copy was not rejected"


def adequacy_gap():
    # the honest limit: a passing check proves a sentence NAMED a verifier, not that the
    # verifier ENTAILS the claim — a false claim with a behavioral-but-irrelevant check
    # still passes the gate and even grades behavioral
    w = [fx.entry("c", claim="the sky is green", check="cmd:grep -q TOKEN a.txt")]
    assert fx.gate(w, assets={"a.txt": "TOKEN\n"})[0] == 0, "the gate cannot tell a check is irrelevant"
    recs = json.loads(fx.discriminate(w, "--all", "--json", assets={"a.txt": "TOKEN\n"})[1])
    assert recs[0]["grade"] == "behavioral", "the irrelevant check even grades behavioral"


def crash_sensitive_limit():
    # Δ FLAGS but does not forbid the gap: a check can be behavioral yet sensitive only
    # to inputs OTHER than the document's content (its bib/rubric/out) — content_sensitive
    # marks that, so "behavioral" is necessary but not sufficient for relevance
    recs = json.loads(fx.discriminate(
        [fx.entry("c", claim="c", check="cmd:grep -q TOKEN a.txt")],   # sensitive to an asset, not content
        "--all", "--json", assets={"a.txt": "TOKEN\n"})[1])
    r = recs[0]
    assert r["grade"] == "behavioral" and r.get("content_sensitive") is False, \
        f"a non-content-sensitive behavioral check should be flagged (content_sensitive={r.get('content_sensitive')})"


def trust_boundary():
    # a check is arbitrary code (cmd: is the universal escape hatch), so gating a
    # document EXECUTES its checks — the warrant set is trusted code, like a Makefile.
    # Demonstrate: a cmd: check with a side effect runs when the document is gated.
    d = tempfile.mkdtemp()
    try:
        marker = os.path.join(d, "ran")
        fx.gate([fx.entry("c", claim="x", check=f"cmd:touch {marker}")])
        assert os.path.exists(marker), "gating did not execute the check — arbitrary code runs"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def env_sanitized():
    # to bound that, a check runs in a controlled, default-deny environment: an ambient
    # variable that is not on the allow-list does NOT reach it, so a verdict cannot be
    # injected through the caller's environment (sshd's defence against env injection)
    os.environ["INJECTED_XYZ"] = "leaked"
    try:
        w = [fx.entry("c", claim="x", check='cmd:test -z "$INJECTED_XYZ"')]
        assert fx.gate(w)[0] == 0, "an un-allow-listed ambient var leaked into the check"
    finally:
        os.environ.pop("INJECTED_XYZ", None)


def path_surface():
    # the residual env-sanitizing leaves is a TRUST surface, not only reproducibility:
    # clean_env KEEPS PATH and run_ok runs the command through a shell, so a directory
    # earlier in PATH SHADOWS a check's tool — whatever it resolves to runs.  (Pinning
    # absolute tool paths would close it; paperkit does not yet do that.)  Demonstrate:
    # a bare tool name resolves to our planted binary iff its dir is on PATH.
    d = Path(tempfile.mkdtemp())
    saved = os.environ.get("PATH", "")
    try:
        shadow = d / "shadow"
        shadow.mkdir()
        (shadow / "pkdemotool").write_text("#!/bin/sh\nexit 0\n")
        os.chmod(shadow / "pkdemotool", 0o755)
        assert "PATH" in gate.clean_env(), "clean_env drops PATH — the name-resolution surface would not exist"
        os.environ["PATH"] = str(shadow) + os.pathsep + saved
        assert gate.resolves("cmd:pkdemotool", d, {}) is True, "a tool earlier on PATH did not resolve inside the gate"
        os.environ["PATH"] = saved
        assert gate.resolves("cmd:pkdemotool", d, {}) is False, "the bare tool resolved without the shadow dir — not PATH-shadowed"
    finally:
        os.environ["PATH"] = saved
        shutil.rmtree(d, ignore_errors=True)


def grounding_reflected():
    # ∂²'s grounding face — the comparison definition-resolution made possible: each
    # DECLARED rests-on edge is checked against MEASURED engine sensitivity.  Overlap is
    # reflected; a disjoint edge from a claim that tests NO engine capability is vacuously
    # disjoint (rhetorical, auto-discharged); a disjoint edge from a claim that DOES test
    # engine capability is a genuine miss, dischargeable by a `link`.  Shared test
    # scaffolding (claims.py / _fixture) does NOT count as engine grounding.
    recs = [
        {"key": "y", "grade": "behavioral", "rests-on": [],
         "tests": ["paperkit/gate.py::resolves"]},
        {"key": "x", "grade": "behavioral", "rests-on": ["y"],          # overlaps y
         "tests": ["paperkit/gate.py::resolves", "paperkit/project.py::weave"]},
        {"key": "z", "grade": "behavioral", "rests-on": ["y"],          # tests engine, disjoint → genuine
         "tests": ["paperkit/rhetoric.py::kind_of"]},
        {"key": "w", "grade": "behavioral", "rests-on": ["y"],          # tests nothing engine → rhetorical
         "tests": ["checks/claims.py::w"]},
    ]
    g = coherence.grounding_residual(recs)
    assert g["grounding_edges"] == 3, g                                 # x→y, z→y, w→y
    assert g["reflected"] == 1 and ["x", "y"] not in g["misses"], g     # x overlaps y
    assert g["undischarged"] == 1 and ["z", "y"] in g["misses"], g      # z genuine miss
    assert g["rhetorical"] == 1 and ["w", "y"] not in g["misses"], g    # w vacuously disjoint, auto-discharged
    assert coherence.grounding_residual(recs, discharged={"z"})["undischarged"] == 0, \
        "a `link` did not discharge a genuine grounding miss"
    scaffold = [
        {"key": "y", "grade": "behavioral", "rests-on": [], "tests": ["checks/claims.py::y"]},
        {"key": "x", "grade": "behavioral", "rests-on": ["y"], "tests": ["checks/claims.py::x"]},
    ]
    assert coherence.grounding_residual(scaffold)["grounding_edges"] == 0, \
        "shared scaffolding counted as engine grounding — the engine restriction failed"


def forward_direction():
    # the structure residual closed by PROJECTION (the grounding DAG renders as
    # transitively-reduced cross-references), not the retired "subsume into one chiral
    # edge" flattening.  The open work is the richer materialization rungs (an expounding
    # clause / a figure beyond the bare citation) — trips when one lands.
    src = (ENGINE / "project.py").read_text()
    assert "def transitive_reduction" in src and "def references" in src, \
        "the reference projection/reduction was removed — update the roadmap"
    assert "def expound" not in src, \
        "a richer reference materialization (expound) may have landed — update the roadmap"


CLAIMS = {
    "grounding-reflected": grounding_reflected,
    "fresh-by-construction": fresh_by_construction,
    "adequacy-gap": adequacy_gap,
    "crash-sensitive-limit": crash_sensitive_limit,
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
    "grade-ladder": grade_ladder,
    "mutation-probes": mutation_probes,
    "content-cache": content_cache,
    "sandbox-grade": sandbox_grade,
    "min-strength": min_strength,
    "resolve-passes": resolve_passes,
    "safe-rejects-postulates": safe_rejects_postulates,
    "without-k-distinct": without_k_distinct,
    "jobs-parallel": jobs_parallel,
    "mem-lease": mem_lease,
    "weave-sentence": weave_sentence,
    "connector-resolution": connector_resolution,
    "emit-placement": emit_placement,
    "config-flags": config_flags,
    "latex-clean": latex_clean,
    "edge-from-orders": edge_from_orders,
    "edge-rests-grounds": edge_rests_grounds,
    "edge-chiral": edge_chiral,
    "edge-move-types": edge_move_types,
    "fail-omits": fail_omits,
    "paper-is-paperkit": paper_is_paperkit,
    "prose-is-projection": prose_is_projection,
    "closes-gap": closes_gap,
    "unverified-cant-ship": unverified_cant_ship,
    "not-project": not_project,
    "paperkit-on-paperkit": paperkit_on_paperkit,
    "one-green-check": one_green_check,
    "node-is-claim": node_is_claim,
    "claim-bears-check": claim_bears_check,
    "paper-is-projection": paper_is_projection,
    "claims-are-warrants": claims_are_warrants,
    "gate-is-subject": gate_is_subject,
    "verifier-named": verifier_named,
    "gate-dispatches": gate_dispatches,
    "dataset-backed": dataset_backed,
    "dataset-fresh": dataset_fresh,
    "new-domain-adds": new_domain_adds,
    "two-builtins": two_builtins,
    "file-builtin": file_builtin,
    "cmd-builtin": cmd_builtin,
    "cmd-escape": cmd_escape,
    "projector-emits": projector_emits,
    "prose-is-artifact": prose_is_artifact,
    "gate-rejects-drift": gate_rejects_drift,
    "edit-cant-survive": edit_cant_survive,
    "coverage-both-sides": coverage_both_sides,
    "every-section-appears": every_section_appears,
    "every-claim-cited": every_claim_cited,
    "claim-is-record": claim_is_record,
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
