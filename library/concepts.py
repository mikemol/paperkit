#!/usr/bin/env python3
"""library/concepts.py — the concept-witness LIBRARY (the owner of each concept's proof).

A concept is authored ONCE — its record in the library's concepts.bib, its witness here — and the
library GRADES each witness once (a def-sweep, engine fingerprint) and exports that as a certificate.
Every VIEW that cites the concept (paper, deep; README, pitch; later a guide) resolves its
`concept:<key>` check by IMPORTING the certificate (verdict + fingerprint), instead of re-authoring a
parallel — and often weaker — witness.  (The README's old rm_delta GREPPED engine source; this witness
RUNS the real grader, so importing the concept also upgrades the pitch's proof.)

The library runs the witness as a plain `cmd:python3 concepts.py <key>` (cwd = library/).  Paths derive
from __file__: ROOT = the repo root (parents[1]), ENGINE = ROOT/paperkit.  PAPERKIT_ENGINE (a paperkit
knob, survives clean_env) points the engine at a mutated variant during Δ's def-sweep, so mutating an
engine def-site flips the witness → the certificate's sensitivity fingerprint IS the engine.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = Path(os.environ.get("PAPERKIT_ENGINE") or ROOT / "paperkit")
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests"))
from _fixture_model import entry  # noqa: E402  (the validated fixture kernel; capability helpers
#   are imported FUNCTION-LOCALLY per witness — the minimal-capability discipline of Μ·kernel·fixture·split)
import project as P  # noqa: E402  — the bib parser (Μ·model), for the claim-is-record witness
import gate  # noqa: E402  — the resolver/gate, for the verifier concepts (parser+resolver are engine)
import resolver  # noqa: E402  — VERBS, the engine's OWN verb set (never re-listed here; Λ·registry)


def adequacy_pitch():
    from _fixture_delta import discriminate
    # the Δ grade ladder, the PITCH face — a passing check only proves a sentence named a verifier,
    # not that the verifier ENTAILS it, so Δ grades how much each check can actually fail.  Witnessed
    # the STRONG way (run the real grader over a fixture, not grep the engine source): a presupposed
    # file: grades vacuous, a content-sensitive cmd: grades behavioral.
    recs = json.loads(discriminate(
        [entry("vac", claim="v", check="file:w.bib"),
         entry("beh", claim="b", check="cmd:grep -q TOKEN a.txt", frm="vac")],
        "--all", "--json", assets={"a.txt": "TOKEN\n"})[1])
    g = {r["key"]: r["grade"] for r in recs}
    assert g["vac"] == "vacuous" and g["beh"] == "behavioral", f"grade ladder wrong: {g}"


def _parse(text):
    # the bib PARSER is engine code (project.entries), so mutating a parser def-site flips this
    # witness — the certificate's sensitivity fingerprint IS that parser, which is exactly what a
    # view citing "a claim is a record" should inherit rather than re-derive.
    d = tempfile.mkdtemp()
    try:
        p = Path(d) / "t.bib"
        p.write_text(text)
        return P.entries(p)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def claim_is_record():
    # a claim is one bibliography entry: a statement, its section, its dependencies, its check.
    # Authored once here; README (rm-model) and paper (claim-is-record) both import this certificate.
    rec = _parse("@misc{k,\n  section = {s},\n  from = {d},\n  claim = {a statement},\n  check = {file:x}\n}\n")["k"]
    for field in ("claim", "section", "from", "check"):
        assert rec.get(field), f"a claim record is missing its {field}"


def claim_bears_check():
    # each claim carries a machine-checkable verifier: the check field names a verb, and the gate
    # RESOLVES it (runs it).  Parser and resolver are engine, so the certificate's fingerprint IS them.
    rec = _parse("@misc{c,\n  section = {s},\n  claim = {x},\n  check = {cmd:true}\n}\n")["c"]
    assert rec.get("check") == "cmd:true", "the claim carries no check"
    assert gate.resolves("cmd:true", ENGINE, {}) is True and gate.resolves("cmd:false", ENGINE, {}) is False, \
        "the verifier is not machine-checkable"


def custom_type_resolves():
    # cmd is the escape hatch every check reduces to, and a new domain adds a verifier in config
    # without touching the engine: a config-supplied type resolves by running its cmd; an unregistered
    # one does not.  The resolver dispatch is engine, so mutating a dispatch def-site flips this.
    assert gate.resolves("demo:x", ENGINE, {"demo": {"cmd": "true"}}) is True, \
        "a config-supplied check type did not resolve to its cmd"
    assert gate.resolves("demo:x", ENGINE, {}) is False, \
        "an unregistered check type resolved with nothing behind it"


def failing_check_blocks():
    from _fixture_gate import gate
    from _fixture_project import project_text
    # an unverified sentence cannot ship: a claim whose check FAILS blocks the gate.  The gate is
    # engine, so mutating its resolution/projection def-sites flips this — the fingerprint is the gate.
    ok = [entry("x", claim="present", check="cmd:true")]
    bad = [entry("x", claim="present", check="cmd:false")]
    good = project_text(ok)
    assert gate(ok, out=good)[0] == 0, "a claim with a passing verifier did not ship"
    assert gate(bad, out=good)[0] != 0, "a claim with a FAILING verifier still shipped"


def gate_enforces_invariants():
    from _fixture_gate import gate
    from _fixture_project import project_text
    # the gate ENFORCES its invariants — the committed prose equals its projection, and every cited
    # claim's check passes — so violating each makes it RED.  The gate is the engine's, so its
    # def-sites (projection-equality, check-resolution) are the certificate's fingerprint.
    w = [entry("x", claim="content", check="cmd:true")]
    good = project_text(w)
    assert gate(w, out=good)[0] == 0, "a faithful, verified document should pass"
    assert gate(w, out=good + "\nDRIFT\n")[0] != 0, "projection-equality not enforced"
    bad = [entry("x", claim="content", check="cmd:false")]
    assert gate(bad, out=project_text(bad))[0] != 0, "check-resolution not enforced"


def resolver_dispatches():
    # the resolver COMPONENT's certificate (Μ·kernel): a verifier is NAMED type:target (the prefix
    # selects the verb), every DECLARED verb dispatches to a real branch — read from resolver.VERBS,
    # no count, no list, nothing to drift (Λ·registry) — the built-in set is CLOSED, and a custom
    # [checks.X] type dispatches through the registry.  The SUPERSET of the four view faces it
    # certifies; the fingerprint is the resolver's own def-sites.
    assert gate.resolves("cmd:true", ENGINE, {}) is True and gate.resolves("file:true", ENGINE, {}) is False, \
        "the type prefix does not select the verb (a verifier is named type:target)"
    assert gate.resolves("file:gate.py", ENGINE, {}) is True, "file: verb"
    assert gate.resolves("agree:printf 42 ||| printf 42", ENGINE, {}) is True, "agree: verb"
    for typ in resolver.VERBS:
        assert gate.resolves(f"{typ}:no-such-target-{typ}", ENGINE, {}) is False, \
            f"{typ}: is declared in VERBS but does not dispatch to a real branch"
    assert gate.resolves("nosuchverb:x", ENGINE, {}) is False, \
        "an unregistered type resolved — the built-in set is not closed"
    assert gate.resolves("demo:x", ENGINE, {"demo": {"cmd": "true"}}) is True, \
        "a custom [checks.X] type did not dispatch through the registry"


def document_is_projection():
    from _fixture_project import project_text
    # the PROJECTOR component's certificate: a document IS the projection of its claim-DAG — the
    # title, EVERY rubric section (populated or not), and every claim's prose appear in the emitted
    # document, which leads with a heading.  The superset of the three view faces (README pitch,
    # paper thesis, paper projector-emits).
    t = project_text([entry("a", claim="alpha thesis"),
                      entry("b", claim="beta point", frm="a")],
                     rubric=(("s", "Sec One"), ("t", "Sec Two")), title="Doc")
    low = t.lower()
    assert t.startswith("#"), "the projection does not lead with a document heading"
    for needle in ("# doc", "## sec one", "## sec two", "alpha thesis", "beta point"):
        assert needle in low, f"the projection is missing {needle!r}"


def project_then_gate():
    from _fixture_gate import gate
    from _fixture_project import project_text
    # two commands do the work — PROJECT makes the document, GATE verifies it: the exact projection
    # passes, and hand-edited drift is rejected.
    w = [entry("x", claim="content")]
    doc = project_text(w)
    assert doc.startswith("#"), "project did not make a document"
    assert gate(w, out=doc)[0] == 0, "gate rejected a faithful document"
    assert gate(w, out=doc + "\nDRIFT\n")[0] != 0, "gate did not verify (drift accepted)"


# ── delta component (Μ·kernel·certs·delta) — the Δ grader/coherence concepts, interned here as
# canonical nodes (library-is-hash-cons: authored ONCE, the paper CITES via concept:). ────────
def content_marks_relevance():
    from _fixture_delta import discriminate
    # Δ FLAGS the relevance gap without closing it: a check can grade behavioral yet be sensitive
    # only to inputs OTHER than the document's content (an asset, not its bib/rubric/out) —
    # content_sensitive marks that, so behavioral is necessary but not sufficient for relevance.
    recs = json.loads(discriminate(
        [entry("c", claim="c", check="cmd:grep -q TOKEN a.txt")],   # sensitive to an asset, not content
        "--all", "--json", assets={"a.txt": "TOKEN\n"})[1])
    r = recs[0]
    assert r["grade"] == "behavioral" and r.get("content_sensitive") is False, \
        f"a non-content-sensitive behavioral check should be flagged (content_sensitive={r.get('content_sensitive')})"


def delegated_grade():
    # a verdict-import sits OUTSIDE the falsifiability ladder: Δ grades result: "imported" —
    # adequacy delegated to a sibling the gate verifies on its own — run once, never swept.
    import grader
    d = Path(tempfile.mkdtemp())
    try:
        sib = d / "g"
        sib.mkdir()
        (sib / "paper.toml").write_text('[paper]\ntitle = "t"\nwarrants = ["w.bib"]\n'
                                        'rubric = "r.tsv"\nout = "out.md"\n')
        (sib / "r.tsv").write_text("s\tSec\n")
        (sib / "w.bib").write_text("@misc{c,\n  section = {s},\n  claim = {x},\n  check = {cmd:true}\n}\n")
        (sib / "out.md").write_text(P.project(P.load_config(sib)))
        rec = grader.grade_check("result:g", d, set(), {}, d)
        assert rec["grade"] == "imported", f"a green verdict-import should grade imported, got {rec['grade']}"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def sandbox_excludes_siblings():
    # grading runs in a sandbox copy whose mutation surface excludes SIBLING projects (a nested dir
    # with its own paper.toml), so a project grades independently of them.
    import grader
    import layout
    d = Path(tempfile.mkdtemp())
    try:
        (d / "paper.toml").write_text("[paper]\n")
        (d / "main.py").write_text("own\n")
        (d / "sub").mkdir()
        (d / "sub" / "paper.toml").write_text("[paper]\n")          # a nested sibling project
        (d / "sub" / "inner.py").write_text("theirs\n")
        assert (d / "sub") in layout._nested_roots(d), "nested project not detected"
        names = [f.name for f in grader.sandbox_files(d, set())]
        assert "main.py" in names and "inner.py" not in names, \
            f"surface should keep own files, drop the sibling's (got {names})"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def grounding_reflected():
    # ∂²'s grounding face — each DECLARED rests-on edge checked against MEASURED engine
    # sensitivity: overlap is reflected; a disjoint edge from a claim that tests engine capability
    # is a genuine miss (dischargeable by a `link`); one from a claim that tests nothing engine is
    # vacuously disjoint (rhetorical, auto-discharged); shared test scaffolding is not grounding.
    import coherence
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
    assert g["rhetorical"] == 1 and ["w", "y"] not in g["misses"], g    # w vacuously disjoint
    assert coherence.grounding_residual(recs, discharged={"z"})["undischarged"] == 0, \
        "a `link` did not discharge a genuine grounding miss"
    scaffold = [
        {"key": "y", "grade": "behavioral", "rests-on": [], "tests": ["checks/claims.py::y"]},
        {"key": "x", "grade": "behavioral", "rests-on": ["y"], "tests": ["checks/claims.py::x"]},
    ]
    assert coherence.grounding_residual(scaffold)["grounding_edges"] == 0, \
        "shared scaffolding counted as engine grounding — the engine restriction failed"


def emergence_collapse():
    # ∂²'s emergence face — the COVERAGE sibling of grounding: a claim whose engine fingerprint is
    # ⊆ its premises' COLLAPSES (its witness emerges by consuming them); a residual is an INCREMENT;
    # no grounding is a LEAF axiom.  STRICTER than grounding — an edge can OVERLAP yet the claim
    # still test more, which coverage (not overlap) catches.
    import coherence
    recs = [
        {"key": "ax", "rests-on": [], "tests": ["paperkit/gate.py::resolves"]},                # no grounding → leaf
        {"key": "col", "rests-on": ["ax"], "tests": ["paperkit/gate.py::resolves"]},           # ⊆ premise → collapse
        {"key": "inc", "rests-on": ["ax"],                                                      # extra site → increment
         "tests": ["paperkit/gate.py::resolves", "paperkit/project.py::weave"]},
    ]
    e = coherence.emergence_residual(recs)
    assert e["leaf"] == 1, e                                            # 'ax' has no grounding
    assert e["collapse"] == 1, e                                        # 'col' reduces to its premise
    assert e["increment"] == 1 and e["increments"][0][0] == "inc", e    # 'inc' tests beyond its premise
    assert coherence.grounding_residual(recs)["reflected"] >= 1 and e["collapse"] == 1, \
        "emergence is not strictly finer than grounding (overlap should pass where coverage can fail)"


def rests_on_clamps():
    # rests-on is a SEPARATE grounding edge: the EFFECTIVE grade clamps to the weakest premise
    # along it (a behavioral thesis resting on a vacuous atom clamps to vacuous), regardless of
    # prose order — the clamp (grade.clamp) over known premise grades.
    import grade
    recs = grade.clamp([
        {"key": "atom", "grade": "vacuous", "rests-on": []},
        {"key": "thesis", "grade": "behavioral", "rests-on": ["atom"]},
    ])
    th = next(r for r in recs if r["key"] == "thesis")
    assert th["grade"] == "behavioral" and th["effective_grade"] == "vacuous", \
        f"rests-on did not clamp the thesis (self={th['grade']}, eff={th['effective_grade']})"


CONCEPTS = {
    # delta component (Μ·kernel·certs·delta) — canonical Δ-grader/coherence nodes.
    "crash-sensitive-limit": content_marks_relevance,
    "imported-grade": delegated_grade,
    "sandbox-grade": sandbox_excludes_siblings,
    "grounding-reflected": grounding_reflected,
    "emergence-collapse": emergence_collapse,
    "edge-rests-grounds": rests_on_clamps,
    # one witness, two keys: the README's pitch face and paper's deep grade-ladder face resolve to the
    # SAME grader run — the adequacy concept is authored once here, each view imports the certificate.
    "adequacy-pitch": adequacy_pitch,
    "grade-ladder": adequacy_pitch,
    # a claim is a record: authored once, imported by README (rm-model) and paper (claim-is-record).
    "rm-model": claim_is_record,
    "claim-is-record": claim_is_record,
    # each claim carries a machine-checkable verifier: README pitch (rm-verifier), paper (claim-bears-check).
    "rm-verifier": claim_bears_check,
    "claim-bears-check": claim_bears_check,
    # cmd is the escape hatch / a new domain adds a type via config — one witness, THREE keys:
    # README (rm-resolver-cmd), paper (cmd-escape, new-domain-adds).
    "rm-resolver-cmd": custom_type_resolves,
    "cmd-escape": custom_type_resolves,
    "new-domain-adds": custom_type_resolves,
    # an unverified sentence cannot ship: README pitch (rm-noship), paper (fail-omits).
    "rm-noship": failing_check_blocks,
    "fail-omits": failing_check_blocks,
    # the gate enforces its invariants: README (rm-cmds-inv), paper self-host (gate-is-subject).
    "rm-cmds-inv": gate_enforces_invariants,
    "gate-is-subject": gate_enforces_invariants,
    # the resolver component (Μ·kernel) — one SUPERSET witness, FOUR keys: README (rm-resolver),
    # paper (verifier-named, gate-dispatches, two-builtins).  The reconcile: the paper's three
    # weaker faces now import the strong enumerative certificate.
    "rm-resolver": resolver_dispatches,
    "verifier-named": resolver_dispatches,
    "gate-dispatches": resolver_dispatches,
    "two-builtins": resolver_dispatches,
    # the projector component — one witness, THREE keys: README pitch (rm-pitch), the paper's
    # thesis (paper-is-projection), and its engine face (projector-emits).
    "rm-pitch": document_is_projection,
    "paper-is-projection": document_is_projection,
    "projector-emits": document_is_projection,
    # project then gate: README (rm-cmds), paper (gate-rejects-drift).
    "rm-cmds": project_then_gate,
    "gate-rejects-drift": project_then_gate,
}


def main(argv) -> int:
    prove_mode = "--prove" in argv
    argv = [a for a in argv if a != "--prove"]
    if not argv or argv[0] not in CONCEPTS:
        # Λ·doc·concept — name WHICH library answered.  `concept:` resolves to the consuming
        # project's library and falls back to the ENGINE's (resolver._library_for), and the
        # fallback is silent by design.  Without this path in the message, a downstream reader
        # whose library is missing or differently named sees "unknown concept key" listing keys
        # they never wrote, and reads it as a bug in their OWN bib rather than as resolution
        # having landed somewhere else.  The message borrowed the wrong denotation; now it says
        # where it stands.  (Asked for by a downstream consumer, who predicted this exact symptom.)
        print(f"usage: concepts.py <{'|'.join(CONCEPTS)}> [--prove]\n"
              f"  this library: {Path(__file__).resolve()}\n"
              f"  if that is not the library you meant, `concept:` fell back to the engine's — "
              f"a project's own library is <project>/library/concepts.py or <repo>/library/concepts.py",
              file=sys.stderr)
        return 2
    if prove_mode:
        # Λ·witness — the SELF-PROVING face: emit this witness's own certificate ⟨verdict, sensitivity
        # fingerprint⟩ instead of a bare pass/fail, so the proof travels with the witness to every view
        # that imports it.  The same measurement the build caches as <key>__dcalc (see prove.py).
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import prove
        print(json.dumps(prove.certificate(argv[0]), indent=2))
        return 0
    try:
        CONCEPTS[argv[0]]()
    except AssertionError as e:
        print(f"concept {argv[0]}: FAIL — {e}", file=sys.stderr)
        return 1
    print(f"concept {argv[0]}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
