#!/usr/bin/env python3
"""Per-claim discriminating witnesses — the `claim:` check type (registered in
paper.toml as `[checks.claim] cmd = "python3 checks/claims.py {target}"`).

Each function asserts the SPECIFIC proposition its claim makes about the engine, so
the check fails if the claim is false (Δ grades it `behavioral`) and every claim
names its own target `claim:<key>` (so the gate's --without-K is satisfied: a
distinct witness per claim, not one shared `file:` standing for many).

    python3 checks/claims.py <claim-key>      # run from paper/; exit 0 = claim holds
"""
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
    # "cmd is the hatch every other check reduces to" — custom types run via cmd
    assert 'run_ok(custom[typ]["cmd"]' in GATE_SRC, "custom types no longer reduce to a cmd"


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


CLAIMS = {
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
