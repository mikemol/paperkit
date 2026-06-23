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
import re
import shutil
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "paperkit"
PAPER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests"))
import gate  # noqa: E402
import project as P  # noqa: E402
import rhetoric  # noqa: E402  (the move/scheme vocabulary)
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


CLAIMS = {
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
