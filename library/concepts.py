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
sys.path.insert(0, str(Path(__file__).resolve().parent))   # this library — for its own domain walk)
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests"))
from _fixture_model import entry  # noqa: E402  (the validated fixture kernel; capability helpers
#   are imported FUNCTION-LOCALLY per witness — the minimal-capability discipline of Μ·kernel·fixture·split)
import project as P  # noqa: E402  — the bib parser (Μ·model), for the claim-is-record witness
import gate  # noqa: E402  — the resolver/gate, for the verifier concepts (parser+resolver are engine)
import resolver  # noqa: E402  — VERBS, the engine's OWN verb set (never re-listed here; Λ·registry)
import routes  # noqa: E402  — Λ·key·graded, the shared graded-key walk (this library is grade 0)


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
    assert gate.resolves("cmd:true", ENGINE, {}).passed and not gate.resolves("cmd:false", ENGINE, {}).passed, \
        "the verifier is not machine-checkable"


def custom_type_resolves():
    # cmd is the escape hatch every check reduces to, and a new domain adds a verifier in config
    # without touching the engine: a config-supplied type resolves by running its cmd; an unregistered
    # one does not.  The resolver dispatch is engine, so mutating a dispatch def-site flips this.
    assert gate.resolves("demo:x", ENGINE, {"demo": {"cmd": "true"}}).passed, \
        "a config-supplied check type did not resolve to its cmd"
    assert not gate.resolves("demo:x", ENGINE, {}).passed, \
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


def adequacy_gap():
    from _fixture_gate import gate
    # the GATE is blind to RELEVANCE: a passing check proves a sentence NAMED a verifier, not that
    # the verifier ENTAILS the claim, so a false sentence with a behavioral-but-irrelevant check
    # still passes — verification here is adequacy, not proof of meaning.  (Δ·scope bounds this to
    # the GATE it exercises, not gate + grader; crash-sensitive-limit owns the grader's half.)
    w = [entry("c", claim="the sky is green", check="cmd:grep -q TOKEN a.txt")]
    assert gate(w, assets={"a.txt": "TOKEN\n"})[0] == 0, "the gate cannot tell a check is irrelevant"


def resolver_dispatches():
    # the resolver COMPONENT's certificate (Μ·kernel): a verifier is NAMED type:target (the prefix
    # selects the verb), every DECLARED verb dispatches to a real branch — read from resolver.VERBS,
    # no count, no list, nothing to drift (Λ·registry) — the built-in set is CLOSED, and a custom
    # [checks.X] type dispatches through the registry.  The SUPERSET of the four view faces it
    # certifies; the fingerprint is the resolver's own def-sites.
    assert gate.resolves("cmd:true", ENGINE, {}).passed and not gate.resolves("file:true", ENGINE, {}).passed, \
        "the type prefix does not select the verb (a verifier is named type:target)"
    assert gate.resolves("file:gate.py", ENGINE, {}).passed, "file: verb"
    assert gate.resolves("agree:printf 42 ||| printf 42", ENGINE, {}).passed, "agree: verb"
    for typ in resolver.VERBS:
        assert not gate.resolves(f"{typ}:no-such-target-{typ}", ENGINE, {}).passed, \
            f"{typ}: is declared in VERBS but does not dispatch to a real branch"
    assert gate.resolves("nosuchverb:x", ENGINE, {}).is_unavailable(), \
        "an unregistered type resolved — the built-in set is not closed"
    assert gate.resolves("demo:x", ENGINE, {"demo": {"cmd": "true"}}).passed, \
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


def graded_key_resolves():
    # Λ·key·graded — a concept key is GRADED: `family[/subfamily]/argument`, resolved by consuming
    # `/`-separated segments to a `(fn, arg)` leaf.  Two properties make the grading worth having,
    # and this asserts both against the REAL walk (routes.py), so mutating a walk def-site flips it.
    #
    # (1) DEPTH-AGNOSTIC.  One loop serves every grade, so grade 0 — a flat key, THIS library's own
    #     shape — is the degenerate case rather than a separate mechanism.  A depth-bounded walk is
    #     the defect this pins: a deeper family would resolve under one implementation and vanish
    #     under another.
    # (2) DISTINCT KEYS, SHARED IMPLEMENTATION.  `f/A` and `f/B` route to ONE function with
    #     different arguments, which is what makes reuse and proof-relevance compatible: the gate
    #     compares check STRINGS (--without-K), so the two are distinct witnesses to it.
    seen = []
    shared = seen.append          # ONE implementation, reached under two keys — the point of (2)
    grid = {"flat": (lambda: seen.append("flat"), None),                       # grade 0 (nullary)
            "f": {"A": (shared, "A"), "B": (shared, "B")},                     # grade 1
            "d": {"s": {"deep": (shared, "deep")}}}                            # grade 2
    for key in ("flat", "f/A", "f/B", "d/s/deep"):
        assert routes.dispatch(grid, key, "t", report=False) == 0, f"a grade-valid key did not certify: {key}"
    assert seen == ["flat", "A", "B", "deep"], f"the walk ran the wrong witnesses: {seen}"
    # the two grade-1 keys share ONE implementation but arrive with DIFFERENT arguments
    fa, fb = routes.walk(grid, "f/A"), routes.walk(grid, "f/B")
    assert fa[0] is fb[0] and fa[1] != fb[1], "parameterised keys did not share one implementation"
    # THE EXIT-CODE PROTOCOL: 2 is "not mine" (so a resolver can fall through), 1 is FAILED.  A
    # leaf's KeyError must read as 2, NOT 1 — "this argument is not one I serve" is indistinguishable
    # from an unresolved route, and reading it as failure would break the fallthrough resolver.py
    # depends on (Λ·library·fallthrough).
    def boom(a):
        raise {"miss": KeyError, "bad": AssertionError}[a](a)
    arm = {"x": {"miss": (boom, "miss"), "bad": (boom, "bad")}}
    assert routes.dispatch(arm, "x/miss", "t", report=False) == 2, "a leaf's KeyError did not read as not-mine"
    assert routes.dispatch(arm, "x/bad", "t", report=False) == 1, "a failing witness did not read as FAILED"
    for absent in ("nope", "f/Z", "f", "flat/extra"):
        assert routes.dispatch(grid, absent, "t", report=False) == 2, f"{absent!r} should be not-mine"
    # THIS library is grade 0, and its table is DERIVED from CONCEPTS — so the two cannot drift.
    assert set(ROUTES) == set(CONCEPTS), "the grade-0 route table drifted from CONCEPTS"
    assert all(routes.walk(ROUTES, k)[1] is None for k in CONCEPTS), "grade 0 is not nullary"


def slice_cache_sound():
    # Λ·cache·slice — a check's verdict is reusable exactly when NOTHING IT CAN REACH has changed,
    # so the cache key is the check's SLICE: its witness function, the transitive closure of the
    # module-level names that function references, and the CONTENT of every module the slice reaches.
    #
    # TWO DIMENSIONS make it sound, and each closes a measured stale-PASS.
    #
    # THE FILE DIMENSION.  A name-only slice sees `ast.Name` nodes in one file, so a witness
    # reaching code through a FUNCTION-LOCAL import (the minimal-capability discipline this library
    # itself follows — `from _fixture_delta import discriminate` inside the witness) binds a local
    # alias that is NOT a module-level name: edits to that module then do not invalidate.
    #
    # THE CONSTANT DIMENSION.  A slice that indexes only FUNCTION bodies stops at a constant's own
    # name, so anything reachable only THROUGH a literal — a dispatch table, an operator registry —
    # is invisible.  Measured downstream: a lifted library's NAND/IMP/CON/XNOR were named only by a
    # `BINARY` dict, so editing an operator did not invalidate the witnesses that use it.
    #
    # Both are asserted against the real slicer, on a fixture carrying both shapes.
    import checkcache as CC
    src = ("import sys\n"
           "TOP = 1\n"
           "def leaf(x):\n"
           "    return x\n"
           "TABLE = {'k': leaf}\n"          # leaf is reachable ONLY through this literal
           "def reaches_via_constant(w):\n"
           "    assert TABLE['k'](1)\n"
           "def reaches_local_import(w):\n"
           "    import helper as H\n"
           "    assert H.VALUE\n"
           "def reaches_nothing(w):\n"
           "    assert TOP == 1\n")
    d = tempfile.mkdtemp()
    try:
        base = Path(d)
        (base / "concepts.py").write_text(src)
        (base / "helper.py").write_text("VALUE = 'a'\n")
        _t, fns, names, segs, imports = CC.module_index(src)
        search = [base]

        def key(fn, route):
            return CC.slice_key(fn, route, fns, names, segs, imports, search)

        # the local-import edge is SEEN: helper is in the reached-module set, and not in the other's
        reach_local = CC.slice_of("reaches_local_import", fns, names, imports)
        reach_none = CC.slice_of("reaches_nothing", fns, names, imports)
        assert "helper" in reach_local[1], "a function-local import is invisible to the slice"
        assert "helper" not in reach_none[1], "an unrelated witness picked up a module it cannot reach"
        # and the edge is LOAD-BEARING: editing that module changes the dependent key, ONLY.
        before_l, before_n = key("reaches_local_import", "r/local"), key("reaches_nothing", "r/none")
        (base / "helper.py").write_text("VALUE = 'b'\n")
        after_l, after_n = key("reaches_local_import", "r/local"), key("reaches_nothing", "r/none")
        assert before_l != after_l, \
            "STALE-PASS: editing a function-locally imported module did not invalidate its check"
        assert before_n == after_n, "over-invalidation: an unreachable edit invalidated a check"
        # THE CONSTANT DIMENSION: the walk goes THROUGH a literal, not up to it.  `leaf` is named
        # only by TABLE, so a function-only index reaches TABLE and stops — and an edit to `leaf`
        # would leave the key untouched, which is the stale PASS.
        reach_const = CC.slice_of("reaches_via_constant", fns, names, imports)
        assert "TABLE" in reach_const[0], "the slice missed a constant the witness names"
        assert "leaf" in reach_const[0], \
            "STALE-PASS: a definition reachable only THROUGH a constant is invisible to the slice"
        assert "leaf" not in reach_none[0], "an unrelated witness picked up a name it cannot reach"
        # and it is LOAD-BEARING: editing the transitively-reached definition moves the key.
        before_c = key("reaches_via_constant", "r/const")
        mutated = src.replace("    return x\n", "    return x + 0\n")
        _t2, fns2, names2, segs2, imports2 = CC.module_index(mutated)
        after_c = CC.slice_key("reaches_via_constant", "r/const", fns2, names2, segs2, imports2, search)
        assert before_c != after_c, \
            "STALE-PASS: editing a definition reached through a constant did not invalidate"
        # the ROUTE is part of the key — one witness serving two claims is two checks, one slice.
        assert key("reaches_nothing", "r/one") != key("reaches_nothing", "r/two"), \
            "two routes into one witness collapsed onto a single cache entry"
        # FAIL-CLOSED: a slice that cannot be computed yields NO key, so the check runs every time.
        assert key("not_a_module_level_function", "r/x") is None, \
            "an uncomputable slice produced a key instead of forcing the check to run"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def conclusion_needs_backing():
    # Λ·conclusion·backed — the check apparatus covers LANDED CLAIMS: each carries a command that
    # must pass.  PRINTED REASONING carries nothing, so an analysis script can print a conclusion
    # beside output from the same run that refutes it and no gate notices.  This is the gate for
    # that: a printed conclusion must be backed by an assertion that would fail if it were false.
    #
    # The asymmetry is the design, and it is what makes the gate honest: it CANNOT tell whether an
    # assertion is the RIGHT one, only that a conclusion was staked with NOTHING behind it.  A gate
    # that judged relevance would have to be right about meaning, and would fail OPEN when it was
    # not — so the weak direction (pure prose naming no computed value) is passed deliberately.
    # conclusiongate lives in THIS library (staged by its BUILD manifest), not in cotype/ —
    # a witness may only import what the hermetic sandbox stages.
    import conclusiongate as CG
    staked = "x = 1 + 1\nprint(f'x is {x}')\nprint('=> therefore x is even')\n"
    backed = staked.replace("print('=>", "assert x % 2 == 0, 'x is odd'\nprint('=>")
    prose = "print('=> therefore the argument holds')\n"
    assert CG.findings(staked)["ungated"], "a conclusion with no assertion anywhere was not flagged"
    assert not CG.findings(backed)["unbacked"], "an assertion naming the same value did not count as backing"
    assert not CG.findings(prose)["unbacked"], \
        "a conclusion naming no computed value was flagged — the weak direction must stay weak"
    # UNBACKED is distinct from UNGATED: assertions exist, but none touches the conclusion's subject.
    other = "y = 5\nz = 2 + 2\nassert y == 5, 'y'\nprint(f'z is {z}')\nprint('=> so the z value is even')\n"
    u = CG.findings(other)["unbacked"]
    assert u and "z" in u[0][2], f"an assertion about an unrelated name was accepted as backing: {u}"


def label_records_carrier():
    # Λ·label·carrier — a LABEL is a point in an orbit: it names a concept FROM THE CARRIER one was
    # standing in.  So a concept has ONE identity and MANY labels, and the map is
    # `concept -> {carrier: label}` rather than `label -> concept`.  What it BUYS is ingestion:
    # a foreign corpus splits into REUSE (an existing witness family already covers this, so the
    # term becomes another ARGUMENT to it — the graded key) and WEDGE (transverse, needs new work).
    import labelmap as LM
    m = LM.LabelMap({"share": {"circuit": "current divider", "optimisation": "argmin"},
                     "reuse": {"functional": "hash-consing"}},
                    {"share": "operator/means/share"})          # PARTIAL — reuse has no route
    assert m.lookup("Current-Divider")[:2] == ("share", "circuit"), "normalisation failed"
    assert m.lookup("the argmin of it")[:2] == ("share", "optimisation"), "whole-word match failed"
    # THE RESOLUTION LIMIT: matching is on WHOLE WORDS.  A substring rule matched `ratio` inside
    # `bifibrational` and produced a hundred false hits — the instrument's own measured limit.
    assert m.lookup("bifibrational") is None, "a substring matched — the false-hit rule is back"
    reuse, wedge = m.contrast(["current divider", "hash-consing", "sheaf"])
    assert set(reuse) == {"share", "reuse"} and wedge == ["sheaf"], \
        f"contrast did not split the corpus into reuse and wedge: {reuse}, {wedge}"
    # a concept with no route is UNRESOLVED — the third verdict, never a merge.
    assert m.discriminate("argmin", "hash-consing", lambda r: 1)[0] == "unresolved", \
        "a routeless concept was merged instead of reported unresolved"
    # the index GROWS, and a collision is the DATUM (synonyms, or an under-parameterised concept) —
    # which of the two is DERIVED by running the witnesses, never declared as a annotation.
    m.add("potential divider", "share", "circuit")
    assert sorted(m.collisions()[("share", "circuit")]) == ["current divider", "potential divider"], \
        "the index did not grow, or the collision went undetected"


def boundary_is_a_triple():
    """<P, F, delta>: a pass arm, a flag arm, and the minimum delta between them.

    Interned as the SHAPE, proven on a constructed check — not by counting the boundary suites in
    this repository.  Two reasons.  The library stages only its own files, so reaching into a
    sibling project would pass in-process and fail in the sandbox (the trap concept_carries_several
    _views already documents).  And a COUNT is the wrong referent anyway: "more than twenty suites
    exist" is a fact about this corpus at one moment, while the claim is about what a boundary IS.

    The property that makes the triple a measurement: the delta must be MINIMAL and SUFFICIENT --
    changing it flips the verdict, and changing nothing does not.  A pair of arms without that is
    two anecdotes, and a check that cannot fail is indistinguishable from one that discriminates.
    """
    def check(text):                      # a toy tool: passes iff its input carries the token
        return "TOKEN" in text

    P, F = "a TOKEN here", "a  here"      # the minimal pass / minimal flag pair
    assert check(P), "the P arm does not pass — it is not a pass arm"
    assert not check(F), "the F arm does not flag — a check that cannot fail proves nothing"

    # delta: the ONE difference between the arms, and it is what flips the verdict.
    assert P.replace("TOKEN", "") == F.replace("TOKEN", ""), \
        "P and F differ in more than the delta — the pair does not isolate a cause"
    assert check(F.replace(" ", "TOKEN", 1)) is not check(F), \
        "applying the delta to F does not flip it — the delta is not sufficient"

    # a happy-path-only tool has an UNDEFINED boundary: no F arm distinguishes these two.
    def always(text):
        return True
    assert always(P) and always(F), "the degenerate tool should accept both"
    assert check(P) != check(F), "the real tool discriminates where the degenerate one cannot"


def capability_owned_as_data():
    """A capability matrix is DATA with a named exception, not prose with silent gaps.

    Proven against a CONSTRUCTED matrix, never by importing a project's own grid: the library
    stages only its own files (the hermetic sandbox honours that), and a witness that reached into
    a sibling would pass in-process and fail in the sandbox — the exact failure the talk's
    hand-rolled version had.  What is interned here is the SHAPE: cells are declared, an
    unaffordable cell is EXCEPTED rather than absent, and absence is therefore detectable.
    """
    grid = {"alt-text": {"docx": "native", "latex": "post", "pdf": "excepted"},
            "math":     {"docx": "native", "latex": "native", "pdf": "post"}}
    fmts = {f for cells in grid.values() for f in cells}
    for cap, cells in grid.items():
        assert set(cells) == fmts, f"{cap} leaves a format undeclared — a silent gap"
    assert "excepted" in {st for c in grid.values() for st in c.values()}, \
        "no cell is EXCEPTED — an honest matrix names what it cannot afford"
    # the property that makes it data: DELETING a cell is detectable, which prose cannot offer.
    holed = {c: dict(v) for c, v in grid.items()}
    holed["math"].pop("pdf")
    assert any(set(v) != fmts for v in holed.values()), \
        "a removed cell is undetectable — the matrix is not owned as data"


def pipeline_is_a_coalgebra():
    """Targets are OBJECTS, conversions are MORPHISMS, a route is a WALK over declared edges.

    Constructed, for the same staging reason as capability_owned_as_data.  The interned property is
    that a route is CHECKED against the adjacency: an edge the graph does not declare is refused,
    which is what separates a tracked pipeline from a shell script that happens to work today.
    """
    objects = {"md", "docx", "pdf"}
    morphisms = {("md", "docx"), ("docx", "pdf")}

    def walks(route):
        return all(e in morphisms for e in zip(route, route[1:])) and set(route) <= objects

    assert walks(["md", "docx", "pdf"]), "a route over declared edges does not compose"
    assert not walks(["md", "pdf"]), "an UNDECLARED edge composes — the adjacency is decorative"
    assert not walks(["md", "epub"]), "a route reaches an object the graph does not declare"


def derived_is_regenerated_not_trusted():
    """Every derived artifact is regenerated and compared — the drift face, generalised.

    project_then_gate interns this for PROSE (project -> gate on a document).  This node is the
    same discipline over any derivative a project commits: a table, a manifest, a figure.  It is a
    DISTINCT concept rather than a second key on that witness, because the property is about the
    committed derivative's relation to its generator, not about the projector.
    """
    d = Path(tempfile.mkdtemp())
    try:
        def generate(src):
            return "\n".join(f"| {k} | {v} |" for k, v in sorted(src.items()))

        src = {"a": 1, "b": 2}
        committed = d / "table.md"
        committed.write_text(generate(src))
        assert committed.read_text() == generate(src), "a fresh derivative does not match"
        src["c"] = 3                                   # the source moves, the derivative does not
        assert committed.read_text() != generate(src), \
            "the committed derivative still matches a CHANGED source — nothing is being compared"
        committed.write_text(generate(src))            # regenerate closes it
        assert committed.read_text() == generate(src), "regeneration does not restore agreement"
    finally:
        shutil.rmtree(d, ignore_errors=True)


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


def concept_imports_a_certificate():
    # `concept:` IMPORTS rather than runs: the verb resolves a key against a library and yields
    # its certificate.  Δ therefore grades it `imported` — outside the falsifiability ladder,
    # delegated to the owner that graded it — exactly as a verdict-import is.
    import grader
    import resolver
    assert resolver.VERBS["concept"]["verb"] == "imports", \
        "the concept verb no longer IMPORTS — the engine's own registry disagrees with the claim"
    assert resolver.VERBS["concept"]["crosses"], \
        "concept: must be a BOUNDARY-CROSSING verb — its proof lives in another project"
    rec = grader.grade_check("concept:adequacy-pitch", ROOT / "paper", set(), {}, ROOT / "paper")
    assert rec["grade"] == "imported", \
        f"a concept citation should grade imported (delegated to its library), got {rec['grade']}"


def concept_interns_to_one_node():
    # A library is a HASH-CONS table: two keys naming the same concept resolve to the SAME
    # canonical witness object, not to two copies that could drift.  The engine's own library
    # exhibits it — adequacy-pitch and grade-ladder are one node under two citations.
    assert CONCEPTS["adequacy-pitch"] is CONCEPTS["grade-ladder"], \
        ("two keys for one concept resolve to DIFFERENT witnesses — the library is a cache of "
         "repeats, not a hash-cons table, and the two can drift apart")
    # and interning is not deduplication-after-the-fact: a key present ONCE is still canonical.
    assert CONCEPTS["crash-sensitive-limit"] is CONCEPTS["crash-sensitive-limit"], \
        "a singly-cited concept must still be one canonical node"


def concept_carries_several_views():
    # ONE truth, SEVERAL prose faces: distinct views cite the same concept and get the IDENTICAL
    # certificate, so their sentences cannot drift apart.
    #
    # Asserted against CONSTRUCTED views, not by scanning the repository: a witness that globbed
    # the tree passed in-process and failed in the hermetic sandbox, which stages only declared
    # inputs — and it was measuring "does this corpus happen to share a key" rather than "does one
    # concept serve several views", which is the property the claim actually makes.
    import resolver
    d = Path(tempfile.mkdtemp())
    try:
        def view(name, key):
            p = d / name
            p.mkdir()
            (p / "paper.toml").write_text('[paper]\ntitle = "t"\nwarrants = ["w.bib"]\n'
                                          'rubric = "r.tsv"\nout = "out.md"\n')
            (p / "r.tsv").write_text("s\tSec\n")
            (p / "w.bib").write_text("@misc{c,\n  section = {s},\n  claim = {a face},\n"
                                     "  check = {concept:%s}\n}\n" % key)
            return p
        a, b = view("pitch", "adequacy-pitch"), view("deep", "adequacy-pitch")
        ra = resolver.resolves("concept:adequacy-pitch", a, {})
        rb = resolver.resolves("concept:adequacy-pitch", b, {})
        assert ra.passed and rb.passed, \
            "two distinct views citing one concept did not both resolve against the library"
        # and the SAME key under a different citation is one node: adequacy-pitch and grade-ladder
        # are two keys the library maps to one witness, so a view may cite either face and import
        # the identical proof.
        assert CONCEPTS["adequacy-pitch"] is CONCEPTS["grade-ladder"], \
            "two keys for one concept are not one node — the faces can drift apart"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def concept_resolves_consumer_first():
    # Λ·library·seam — a project's OWN library answers first; the engine's is the FALLBACK, and
    # the fallthrough is decided PER KEY so a downstream library cannot eclipse engine concepts.
    #
    # Ρ·concept·shareable·cost — the seam is witnessed with the CHEAPEST key that exercises it.
    # An earlier version probed the fallthrough with `adequacy-pitch`, whose own witness runs the
    # real Δ grader over a fixture: correct, and 20x the cost of every sibling concept (measured
    # ~1.6s of nested-spawn overhead against a 0.10s baseline), repeated per engine def-site under
    # a def-sweep.  What the fallthrough claim needs is that a key the consumer DISCLAIMS reaches
    # the engine's library and gets ITS verdict — the identity of that key is irrelevant, so it
    # should be the cheapest concept in the library, not the most expensive.
    import resolver
    d = Path(tempfile.mkdtemp())
    try:
        # a consumer with its own library, owning one key and disclaiming the rest (exit 2).
        #
        # ⚑ Ζ·lib·contract — THE FIXTURE DECLARES ITSELF A PROJECT.  It used to write only
        # `concepts.py`, which passed the old directory test (`concepts.py`.is_file()) — a
        # predicate WEAKER than the contract, and the ecosystem populated the gap: two repos ship
        # a concepts.py-only `library/` that satisfies the test and cannot answer, and one ships a
        # `library/` with no concepts.py at all that silently fell through to THIS engine's
        # library.  A library is a PROJECT now, so the fixture carries the paper.toml that says
        # so — and the `[checks.claim] cmd` below is READ by _library_cmd rather than reconstructed,
        # which is why the witness module may be named anything (it is `witness.py` here on
        # purpose: a fixture named concepts.py could pass against a resolver that still hardcoded
        # the name, and would prove nothing about the declaration being read).
        (d / "library").mkdir()
        (d / "library" / "paper.toml").write_text(
            '[paper]\ntitle="c"\nrubric="r.tsv"\nwarrants=["concepts.bib"]\nout="l.md"\n'
            '\n[checks.claim]\ncmd = "python3 witness.py {target}"\n')
        (d / "library" / "witness.py").write_text(
            "import sys\n"
            "sys.exit(0 if sys.argv[1:2] == ['mine'] else 2)\n")
        # SELECTION is pure — no spawn needed to witness that the consumer's library is chosen.
        assert resolver._library_for(d) == (d / "library"), \
            "a project with its own library did not resolve to it — the seam is engine-relative"
        assert resolver._library_for(ROOT / "paper") == resolver._LIBRARY, \
            "a project WITHOUT its own library did not fall back to the engine's"
        # its own key resolves against ITS library (one spawn, of a two-line stub)...
        assert resolver.resolves("concept:mine", d, {}).passed, \
            "a consumer's own concept key did not resolve against its own library"
        # ...and a key it disclaims FALLS THROUGH to the engine's, rather than being eclipsed.
        # `label-carrier` is the cheapest engine concept (measured 0.07s); any engine key proves
        # the fallthrough, so the probe pays the minimum.
        assert resolver.resolves("concept:label-carrier", d, {}).passed, \
            ("a key the consumer's library disclaims did not fall through to the engine's — "
             "directory-level selection alone makes every engine concept unreachable")
        # and an UNOWNED key is UNAVAILABLE from both, never a silent pass.
        assert not resolver.resolves("concept:no-such-concept-anywhere", d, {}).passed, \
            "a key no library owns resolved as passing — an absent concept must not certify"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def degeneracy_has_kinds():
    """Δ·degeneracy·kinds — a degenerate report distinguishes WHY it is degenerate.

    A document with no grounding graph is degenerate for two different reasons, and one verdict
    for both hides the actionable case: UNDECLARED (no record carries `rests-on` — the document
    may have an argument and simply has not declared it, which an author can fix) versus
    UNGROUNDED (the field is declared but names nothing reachable — there is no argument here to
    ground, so the section cut is the honest answer and nothing is owed).
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "paperkit"))
    import genre

    undeclared = [{"key": "a", "section": "S"}, {"key": "b", "section": "S"}]
    declared_empty = [{"key": "a", "section": "S", "rests-on": []},
                      {"key": "b", "section": "S", "rests-on": []}]

    u, d = genre.partition(undeclared), genre.partition(declared_empty)
    assert u["degenerate"] and d["degenerate"], "both fixtures must still report degenerate"
    assert u["edges"] == 0 and d["edges"] == 0, "neither fixture has a grounding edge"
    # The load-bearing arm: the two must be DISTINGUISHABLE in the record alone.
    assert u.get("kind") != d.get("kind"), (
        "a degenerate report must say WHICH degeneracy — never-declared and declared-but-empty "
        f"are different actionable states (both reported {u.get('kind')!r})")
    assert u.get("kind") == "undeclared", f"no rests-on anywhere is `undeclared` (got {u.get('kind')!r})"
    assert d.get("kind") == "ungrounded", f"declared-but-empty is `ungrounded` (got {d.get('kind')!r})"
    # A grounded document is not degenerate at all, and carries no kind.
    grounded = [{"key": "a", "section": "S", "rests-on": ["b"]},
                {"key": "b", "section": "S", "rests-on": ["a"]}]
    assert not genre.partition(grounded)["degenerate"], "a grounded document must not be degenerate"


CONCEPTS = {
    # resolver component — the concept verb and the library seam (Ρ·paper·concept).
    # project component — what a derived grouping may honestly claim (Δ·degeneracy·kinds).
    "degeneracy-has-kinds": degeneracy_has_kinds,
    "concept-builtin": concept_imports_a_certificate,
    "concept-interned": concept_interns_to_one_node,
    "concept-views": concept_carries_several_views,
    "concept-shareable": concept_resolves_consumer_first,
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
    # the gate is blind to RELEVANCE (adequacy, not proof of meaning): paper (adequacy-gap).  The
    # grader's half — that Δ even grades such a check behavioral — is crash-sensitive-limit (delta).
    "adequacy-gap": adequacy_gap,
    # the resolver component (Μ·kernel) — one SUPERSET witness, FOUR keys: README (rm-resolver),
    # paper (verifier-named, gate-dispatches, two-builtins).  The reconcile: the paper's three
    # weaker faces now import the strong enumerative certificate.
    "rm-resolver": resolver_dispatches,
    "verifier-named": resolver_dispatches,
    "gate-dispatches": resolver_dispatches,
    "two-builtins": resolver_dispatches,
    # the GRADED key (Λ·key·graded) — resolution of a key to its witness is itself a resolver
    # capability, so it is interned beside the verb dispatch it parallels.
    "graded-key": graded_key_resolves,
    # the SLICE cache (Λ·cache·slice) — when a verdict may be REUSED is an adequacy question, so it
    # is interned in delta beside the grading concepts.
    "slice-cache": slice_cache_sound,
    # the cotype layer (Λ·conclusion·backed, Λ·label·carrier) — gating REASONING, not claims.
    "conclusion-backed": conclusion_needs_backing,
    "conclusion-weak-direction": conclusion_needs_backing,
    "label-carrier": label_records_carrier,
    # the projector component — one witness, THREE keys: README pitch (rm-pitch), the paper's
    # thesis (paper-is-projection), and its engine face (projector-emits).
    "rm-pitch": document_is_projection,
    "paper-is-projection": document_is_projection,
    "projector-emits": document_is_projection,
    # project then gate: README (rm-cmds), paper (gate-rejects-drift).
    "rm-cmds": project_then_gate,
    "gate-rejects-drift": project_then_gate,
    "boundary-is-a-triple": boundary_is_a_triple,
    "capability-owned-as-data": capability_owned_as_data,
    "pipeline-is-a-coalgebra": pipeline_is_a_coalgebra,
    "derived-is-regenerated-not-trusted": derived_is_regenerated_not_trusted,
}

# Λ·key·graded — this library is a GRADE-0 route table, the degenerate case of the graded walk in
# routes.py (`family[/subfamily]/argument`, resolved by consuming `/`-separated segments to a
# `(fn, arg)` leaf).  Grade 0 is a flat key -> leaf map with no parameter axis, so adopting the
# shared walk is a NO-OP here: the ~20 keys and every bib record are untouched, and each leaf holds
# `arg = None` because these witnesses are nullary.
#
# DERIVED, never re-authored.  CONCEPTS above stays the authored form — its comments record which
# VIEW cites each key, which is the reason several keys share one witness — and ROUTES is computed
# from it, so the two cannot drift.  A library with a real parameter axis (mdt: `orbit/OR` vs
# `orbit/XOR`) writes a nested table directly instead.
ROUTES = {key: (fn, None) for key, fn in CONCEPTS.items()}


def main(argv) -> int:
    prove_mode = "--prove" in argv
    argv = [a for a in argv if a != "--prove"]
    if not argv or routes.walk(ROUTES, argv[0]) is None:
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
    # The shared walk owns RESOLUTION and the exit-code protocol (0 certified / 1 FAILED /
    # 2 not-mine, with a leaf's KeyError reading as 2 — see routes.py).  The verdict LINES stay
    # in this format: `concept <key>: OK` is what this library has always emitted, and the
    # message is a documented surface, so the port must not silently re-word it.
    fn, arg = routes.walk(ROUTES, argv[0])
    try:
        fn(arg) if arg is not None else fn()
    except KeyError:
        return 2                        # "not an argument I serve" — falls through, like no route
    except AssertionError as e:
        print(f"concept {argv[0]}: FAIL — {e}", file=sys.stderr)
        return 1
    print(f"concept {argv[0]}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
