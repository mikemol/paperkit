#!/usr/bin/env python3
r"""Ρ·talk·adequacy — per-claim witnesses for the talk's MECHANISM claims.

The talk makes two kinds of claim and must not conflate them.  A RHETORIC claim ("everyone here
has shipped a doc that lies") carries `premise:` and says out loud that no machine checked it.  A
MECHANISM claim states a fact about paperkit, and most of those import a certificate the library
already graded — zero new witness code, which is the concept-library story the talk itself makes.

The few here are mechanism claims with no matching library concept yet.  Each asserts its specific
proposition against the ENGINE, so it fails if the claim is false, rather than standing on cmd:true.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paperkit"))
sys.path.insert(0, str(ROOT / "render" / "checks"))


def t_chain():
    # imports CHAIN: a project resting on a sibling that rests on a third, and the chain is
    # LOAD-BEARING — break the innermost and the outermost goes red.
    import shutil, tempfile
    import gate, project as P
    d = Path(tempfile.mkdtemp())
    try:
        def mk(name, check):
            p = d / name; p.mkdir(exist_ok=True)
            (p / "paper.toml").write_text('[paper]\ntitle = "t"\nwarrants = ["w.bib"]\n'
                                          'rubric = "r.tsv"\nout = "out.md"\n')
            (p / "r.tsv").write_text("s\tSec\n")
            (p / "w.bib").write_text("@misc{c,\n  section = {s},\n  claim = {x},\n"
                                     "  check = {%s}\n}\n" % check)
            (p / "out.md").write_text(P.project(P.load_config(p)))
        mk("inner", "cmd:true"); mk("middle", "result:../inner")
        assert gate.resolves("result:middle", d, {}).passed, "a two-link chain did not resolve"
        mk("inner", "cmd:false")
        assert not gate.resolves("result:middle", d, {}).passed, \
            "breaking the innermost left the outermost green — the chain is decorative"
    finally:
        shutil.rmtree(d, ignore_errors=True)




def t_fmt_deck():
    # a deck is a SEGMENTATION, not a linearization: project() returns one string, observe()
    # returns units — a different observation of the same carrier.
    import project as P
    assert callable(P.observe) and callable(P.project), "the two observation shapes are not both present"
    cfg = P.load_config(ROOT / "talk")
    assert isinstance(P.project(cfg), str), "project() must return one flat stream"
    u = P.observe(cfg, "staged", ROOT / "talk")
    assert isinstance(u, list) and u and isinstance(u[0], dict), \
        "observe() must return UNITS — a segmentation, not a rendered string"


def t_fmt_genre():
    # grouping and pagination are INDEPENDENT axes, and the pagination objective is REGISTERED
    # like a check type — a consumer adds its own without touching the engine.
    import genre
    import project as P
    cfg = P.load_config(ROOT / "talk")
    a = P.observe(cfg, "staged", ROOT / "talk")
    b = P.observe(cfg, "atomic", ROOT / "talk")
    assert len(a) != len(b), "two genres gave the same cut — the axes are not independent"
    try:
        genre.resolve("no-such-genre")
        raise AssertionError("an unregistered genre resolved — the registry falls back silently")
    except genre.Unregistered:
        pass



def t_graphs_fig():
    # a FIGURE is alt-texted BY CONSTRUCTION: the projector renders an `as = image` placement as
    # ![claim](path), so the claim's own sentence IS the alternative text — a figure cannot ship
    # without a description unless the claim itself is empty.
    import project as P
    cfg = P.load_config(ROOT / "talk")
    F = {}
    for b in cfg["bibs"]:
        F.update(P.entries(b, cfg["consumer_fields"]))
    f = F["t-graphs-fig"]
    assert f.get("emit") and (f.get("as") == "image"), "the figure claim no longer places an image"
    line = P.emit_block(cfg, f)[0]
    assert line.startswith("!["), f"an image placement did not render as markdown image: {line!r}"
    alt = line[2:line.index("](")]
    assert len(alt.split()) > 5, f"the figure's alt text is too thin to describe it: {alt!r}"
    assert (ROOT / "talk" / f["emit"]).is_file(), "the figure asset is missing from the project"


def _figure(key):
    """Shared witness for a placed FIGURE: it is alt-texted by construction (the projector renders
    `as = image` as ![claim](path), so the claim IS the description), its asset exists, and its
    description reads as prose rather than a filename."""
    import project as P
    cfg = P.load_config(ROOT / "talk")
    F = {}
    for b in cfg["bibs"]:
        F.update(P.entries(b, cfg["consumer_fields"]))
    f = F[key]
    assert f.get("emit") and f.get("as") == "image", f"{key} no longer places an image"
    line = P.emit_block(cfg, f)[0]
    assert line.startswith("!["), f"{key} did not render as a markdown image: {line!r}"
    alt = line[2:line.index("](")]
    assert len(alt.split()) > 5, f"{key} alt text too thin: {alt!r}"
    assert not alt.endswith(".svg"), f"{key} alt text is a filename, not a description"
    assert (ROOT / "talk" / f["emit"]).is_file(), f"{key} asset missing"
    return (ROOT / "talk" / f["emit"]).read_text()


def _colour_safe(svg, key):
    """Ρ·talk·colour — WCAG 1.4.1 generalized from the LaTeX auditor to a drawing: colour must
    never be the SOLE carrier of a distinction.  The LaTeX rule demands a redundant WEIGHT cue
    beside a meaning colour; a drawing's redundant cues are shape, dash pattern, stroke weight and
    words.  Enforced negatively — the figure must not introduce meaning HUES at all — which is the
    strongest form of the rule and the one a reproduction in greyscale also satisfies."""
    import re as _re
    hues = {h.lower() for h in _re.findall(r'(?:fill|stroke)="(#[0-9a-fA-F]{3,6}|[a-z]+)"', svg)}
    allowed = {"#fff", "#ffffff", "#111", "#111111", "#333", "#333333", "none", "white", "black",
               "currentcolor"}
    meaning = hues - allowed
    assert not meaning, f"{key} uses meaning colour(s) {sorted(meaning)} — colour must not be the sole cue"
    redundant = ("stroke-dasharray" in svg or "font-weight" in svg or "stroke-width" in svg)
    assert redundant, f"{key} carries no non-colour cue (dash, weight or shape) to distinguish anything"
    assert 'role="img"' in svg and "aria-label" in svg, f"{key} SVG lacks role/aria-label"


def _figure_domain():
    """The DOMAIN of the figure family, DERIVED rather than listed.

    Ρ·witness·family — `_figure` and `_colour_safe` were already a Π-typed witness family (they
    take the key as a parameter), but their domain was three hand-written call sites.  A hardcoded
    domain is the guard-must-not-copy defect wearing a new hat: two mutation kinds exist for a
    family, "break the predicate for one x" and "REMOVE an x from the domain", and only a derived
    domain can notice the second.  Measured: t-graphs-fig — the FIRST figure, with a bespoke
    witness predating the family — was in the derived domain and absent from the hardcoded list,
    so the domain had already silently shrunk before anyone looked.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("_eb", ROOT / "paperkit" / "bib.py")
    eb = importlib.util.module_from_spec(spec); spec.loader.exec_module(eb)
    F = eb.parse_project(ROOT / "talk")
    return sorted(k for k, v in F.items() if v.get("emit") and v.get("as") == "image")


# The figure family's domain FLOOR — every asset the project ships as a figure.  Derived from the
# filesystem, which is a DIFFERENT owner than the bib the domain is computed from, so the two
# cannot drift together.  Without this, "check every element of the derived domain" is vacuously
# satisfied by a SMALLER domain: measured, dropping `as = {image}` from one warrant shrank the
# domain 4 -> 3 and the witness still passed.  A family that ranges over a derived set needs a
# floor from an independent owner, or the second mutation kind (remove an x) has no witness.
def _figure_assets():
    return sorted(p.name for p in (ROOT / "talk" / "assets").glob("*.svg"))


def _every_figure():
    """Instantiate the family at EVERY element of its derived domain, and assert the domain has
    not SHRUNK below the figures the project actually ships."""
    dom = _figure_domain()
    assert dom, "the figure family's domain is empty — nothing places an image"
    shipped = _figure_assets()
    assert len(dom) >= len(shipped), (
        f"the figure domain SHRANK: {len(dom)} claim(s) place an image but the project ships "
        f"{len(shipped)} figure asset(s) {shipped} — an asset with no image-placing claim is "
        f"outside the family and unchecked")
    for key in dom:
        _colour_safe(_figure(key), key)
    return dom


def t_verbs_fig():
    _every_figure()


def t_library_fig():
    _every_figure()


def t_routes_fig():
    _every_figure()



WITNESSES = {
    "t-graphs-fig": t_graphs_fig,
    "t-verbs-fig": t_verbs_fig,
    "t-library-fig": t_library_fig,
    "t-routes-fig": t_routes_fig,
    "t-chain": t_chain, "t-fmt-deck": t_fmt_deck, "t-fmt-genre": t_fmt_genre,
}

def _dispatch_total():
    """The dispatch table is itself a hand-kept domain, and the LAST unfloored one here.

    `WITNESSES` and the bib's `claim:` keys agree today, but nothing asserted it -- a new claim
    reaches the runner and dies on `no witness for ...`, which reads as a typo rather than as an
    unwitnessed claim, and a stale entry never fires at all.  Both owners are named, so this is
    the strong form of the floor: neither side is computed from the other.

    Checked in BOTH directions, because a floor that only catches shrinkage is half an instrument
    (the growth arm is the one that catches the derivation standing still while its owner grows).
    """
    import importlib.util, re
    spec = importlib.util.spec_from_file_location("_eb", ROOT / "paperkit" / "bib.py")
    eb = importlib.util.module_from_spec(spec); spec.loader.exec_module(eb)
    F = eb.parse_project(ROOT / "talk")
    want = {k for k, v in F.items() if (v.get("check") or "").startswith("claim:")}
    have = set(WITNESSES)
    assert not (want - have), (
        f"claims with no witness: {sorted(want - have)} -- the bib routes these to claim: but the "
        f"dispatch table has no entry, so the runner reports a missing key, not a missing witness")
    assert not (have - want), (
        f"witnesses with no claim: {sorted(have - want)} -- these never fire; either the claim was "
        f"dropped from the bib or the key drifted, and a dead witness proves nothing")


if __name__ == "__main__":
    key = sys.argv[1]
    if key == "--total":
        try:
            _dispatch_total()
        except AssertionError as e:
            print(f"talk --total: FAIL -- {e}", file=sys.stderr); raise SystemExit(1)
        print(f"talk --total: OK ({len(WITNESSES)} claims, each witnessed, none orphaned)")
        raise SystemExit(0)
    fn = WITNESSES.get(key)
    if fn is None:
        print(f"talk: no witness for {key!r}", file=sys.stderr); raise SystemExit(2)
    try:
        fn()
    except AssertionError as e:
        print(f"claim {key}: FAIL — {e}", file=sys.stderr); raise SystemExit(1)
    print(f"claim {key}: OK")
