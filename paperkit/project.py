#!/usr/bin/env python3
"""paperkit project — emit a paper's prose by PROJECTING it from the warrant set.

A paper is the projection of a claim-DAG.  Each entry in a `.bib` is a claim:
a statement (`claim`/`title`), a rubric `section`, its dependencies (`from`),
and a verifier (`check`).  This command reads those records and emits the prose —
every section's claims ordered by their `from` edges and joined with connective
`glue` across genuine entailment edges, and each claim's NON-ADJACENT grounding
(`rests-on`) edges projected as trailing cross-references (the long edges the
connective cannot carry by adjacency).  The output passes the gate (every
citation resolves, every required claim present, in order) BY CONSTRUCTION.

    paperkit-project [DIR]            # write the projection to the configured `out`
    paperkit-project --check [DIR]    # exit 1 if the committed file != the projection
    paperkit-project -o - [DIR]       # write to stdout

DIR defaults to the current directory and must contain `paper.toml`.
"""
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402  (Ω·config — the one configurable-resolution pipeline)
import bib  # noqa: E402  (paperkit.bib — the one .bib parser + data model)
# the projector parses then renders, so it uses the bib data model internally (short names).
from bib import dep_order, is_placed, load_config, rubric  # noqa: E402,F401
from bib import parse as entries  # noqa: E402,F401
# top-level now: after Μ·cycle rhetoric imports bib (a leaf), NOT project, so project→rhetoric is
# one-way — the project↔rhetoric cycle is gone and this need no longer be a function-local import.
from rhetoric import MOVES  # noqa: E402

# Minimal, domain-agnostic LaTeX -> Unicode for claim text (em/en dashes, a few
# escapes, inline math).  A paper that needs more declares its own; this is the
# common floor.
_LATEX = [
    (r"\\textsuperscript\{(\d)\}", lambda m: "⁰¹²³⁴⁵⁶⁷⁸⁹"[int(m.group(1))]),
    (r"\\texttt\{([^{}]*)\}", r"\1"), (r"\\textbackslash", ""),
    (r"\\&", "&"), (r"\\\$", "$"), (r"\\_", "_"),
    (r"\\'e", "é"), (r'\\"o', "ö"), (r"\\'E", "É"),
    (r"---", "—"), (r"(?<=\S)--(?=\S)", "–"), (r"\\equiv", "≡"),
    (r"\$([^$]*)\$", r"\1"),
]


def clean(s: str) -> str:
    # Inline math $…$ is renderable CONTENT for the downstream engine (pandoc/MathJax), not
    # LaTeX-prose to flatten — shield each span verbatim (its delimiters, macros, AND grouping
    # braces) so neither the floor-flattening below nor the grouping-brace strip touches it. This
    # is the same shield discipline as \{ \}, one level up: the whole math span is literal.
    math: list = []
    s = re.sub(r"(?<!\\)\$[^$]*\$",
               lambda m: math.append(m.group(0)) or f"\x02{len(math) - 1}\x03", s)
    for pat, rep in _LATEX:
        s = re.sub(pat, rep, s)
    # Escaped braces \{ \} are LITERAL (e.g. set notation {1,2,3}); shield them
    # from the grouping-brace strip below, then restore as real braces.
    s = s.replace(r"\{", "\x00").replace(r"\}", "\x01")
    s = re.sub(r"[{}]", "", s)
    s = s.replace("\x00", "{").replace("\x01", "}")
    s = re.sub(r"\x02(\d+)\x03", lambda m: math[int(m.group(1))], s)
    return s.strip().rstrip(".")


def short_author(a: str) -> str:
    a = clean(a)
    names = re.split(r"\s+and\s+", a)
    if len(names) > 2:
        return names[0].split()[-1] + " et al."
    return " & ".join(n.split()[-1] if " " in n else n for n in names)


def _anchor(key: str, body: str, target: str) -> str:
    """A claim's own citation point: a pandoc [@key] tag (for citeproc), a web ANCHOR that other
    claims link to, or NOTHING for the footnote target (where the marker + its verification note
    are attached by the weaver instead).  The grounding edges are the same `rests-on` DATA either
    way — only how a citation MATERIALIZES differs by target (the projector's one job)."""
    if target == "web":
        return f'<a id="{key}"></a>{body}'
    if target == "footnote":
        return body
    return f"{body} [@{key}]"


def _verify_note(check: str) -> str:
    """The footnote target's provenance line: HOW this clause's claim is machine-verified, read
    off its `check`.  A cmd: names the verifier to re-run; a claim:/file: names what is imported/
    present.  This is the whole point of the footnote target — every clause cites its own proof."""
    kind, _, tgt = check.partition(":")
    if not check:
        return "Asserted without a machine check"
    if kind == "cmd":
        return f"Machine-verified — `{tgt}`"
    if kind == "agda":
        return f"Agda-proved — `{tgt}`"
    if kind == "premise":
        return f"Classical premise (not machine-checked) — `{tgt}`"
    if kind == "claim":
        return f"Verified claim `{tgt}`"
    if kind == "file":
        return f"Artifact present — `{tgt}`"
    return f"Machine-verified — `{tgt}`" if tgt else "Machine-verified"


def sentence(key: str, f: dict, primary: str, target: str = "pandoc") -> str:
    """A claim sentence carrying its own citation/anchor for `target`.  Prefer an explicit
    `claim`; else a warrant's `title` (the title IS the claim); else a terse cite."""
    if f.get("claim"):
        return _anchor(key, clean(f["claim"]), target)
    title = clean(f.get("title", key))
    if f["_src"] == primary:
        return _anchor(key, title, target)
    yr = f.get("year", "")
    who = short_author(f.get("author", "")) if "author" in f else ""
    paren = ", ".join(x for x in (who, yr) if x)
    return _anchor(key, title + (f" ({paren})" if paren else ""), target)


GLUE = ["and from that, ", "so "]

# A placed (not woven) warrant emits a verbatim asset instead of a sentence; the
# fence language is inferred from the asset's extension (empty = raw include, for
# markdown tables and prose snippets).
FENCE = {".sh": "sh", ".bash": "sh", ".py": "python", ".toml": "toml",
         ".bib": "bibtex", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
         ".txt": "text", ".tsv": "text", ".md": ""}   # .md = raw include (tables)


IMAGE_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".emf"}


def emit_block(pdir: Path, f: dict) -> list:
    """The lines for an `emit:` warrant.  An image asset is placed as a markdown
    image (the claim is its caption/alt); any other asset is included verbatim,
    fenced by the language its extension implies (raw if none)."""
    p = pdir / f["emit"]
    if p.suffix.lower() in IMAGE_EXTS:
        return [f"![{clean(f.get('claim', 'figure'))}]({f['emit']})"]
    if not p.exists():
        return [f"<!-- emit: missing {f['emit']} -->"]
    content = p.read_text().rstrip("\n")
    lang = FENCE.get(p.suffix, "")
    return [f"```{lang}", content, "```"] if lang else [content]


def transitive_reduction(rests: dict) -> dict:
    """Drop a grounding edge X→Y when Y is already reachable from X by a LONGER `rests-on`
    path (the reader reaches Y through the intermediate, so re-citing Y is redundant
    clutter, not new grounding).  The `drop` rung — the zero of the reference's
    materialization ladder (drop < cite < expound < figure), need-proportioned."""
    def reaches(a, b):
        seen, stk = set(), [x for x in rests.get(a, ()) if x != b]
        while stk:
            n = stk.pop()
            if n == b:
                return True
            if n not in seen:
                seen.add(n)
                stk += list(rests.get(n, ()))
        return False
    return {k: [y for y in ys if not reaches(k, y)] for k, ys in rests.items()}


def references(k: str, targets: list, pos: dict, target: str = "pandoc") -> str:
    """Project a claim's NON-ADJACENT grounding edges (after transitive reduction) as
    cross-references — the long edges the prose connective cannot carry by adjacency.  A
    connective IS a reference at distance 0; this is the same edge-projection at distance
    > 0, the direction read off the sign of the prose-distance (a back-reference to ground
    already laid, a forward-reference to ground laid below).  Citation is the floor
    materialization; richer forms (expound, figure) are opt-in.  Returns the parenthetical.
    For `target` web a cross-reference is an intra-page hyperlink to the grounded claim's
    anchor; for pandoc it is a [@key] citation — the SAME edge, materialized per target."""
    if not pos or k not in pos:
        return ""

    def tok(y: str) -> str:
        human = y.replace('-', ' ').replace('_', ' ')
        if target == "web":
            return f"[{human}](#{y})"
        if target == "footnote":
            return human            # a footnote body cannot host a [@key]/anchor — name the claim in prose
        return f"[@{y}]"
    back, fwd = [], []
    for y in targets:
        yp = pos.get(y)
        if yp is None or yp == pos[k] - 1:        # cross-scope, or carried by the connective
            continue
        (back if yp < pos[k] else fwd).append(tok(y))
    parts = []
    if back:
        parts.append("grounded above in " + ", ".join(back))
    if fwd:
        parts.append("developed below at " + ", ".join(fwd))
    return f" ({'; '.join(parts)})" if parts else ""


def weave(text: list, F: dict, primary: str, pos: dict | None = None,
          reduced: dict | None = None, footnotes: dict | None = None,
          target: str = "pandoc") -> str:
    """Weave a run of prose-claim keys into one sentence-diagrammed paragraph.  A
    claim carrying a `link` is materialized at the EXPOUND rung of the reference
    ladder (drop < cite < expound < figure): a footnote marker on the sentence, the
    link explanation + its grounding citations collected into `footnotes` for the
    document end.  Without a link (or no footnotes sink) the grounding is the CITE
    floor — the inline parenthetical.  `target` selects how citations materialize."""
    def clause(k: str) -> str:
        s = sentence(k, F[k], primary, target)
        ref = references(k, (reduced or {}).get(k, F[k].get("rests-on", [])), pos or {}, target)
        link = F[k].get("link")
        if link and footnotes is not None:           # expound: link + citations → footnote
            footnotes[k] = clean(link) + ref
            return s + f"[^{k}]"
        if target == "footnote" and footnotes is not None:   # CITE floor as a provenance footnote
            footnotes[k] = _verify_note(F[k].get("check", "")) + ref
            return s + f"[^{k}]"
        return s + ref                               # cite floor: inline parenthetical
    clauses = [clause(k) for k in text]
    clauses[0] = clauses[0][:1].upper() + clauses[0][1:]
    clauses[1:] = [re.sub(r"^(The|A|An) ", lambda m: m.group(1).lower() + " ", c)
                   for c in clauses[1:]]
    parts, woven = [clauses[0]], 0
    for i in range(1, len(text)):
        f = F[text[i]]
        clause = clauses[i]
        # `join` is the FULL connector to the previous clause — the grammatical
        # attachment of a sentence-diagram constituent: "— " apposition, ", and "
        # conjunction, ", which " relative, ": " list-intro, ". " new sentence.
        # Default is the legacy "; " + `glue` weave.
        if f.get("join") is not None:
            j = f["join"] if f["join"].endswith(" ") else f["join"] + " "
            if j.strip().endswith((".", "!", "?")):   # sentence boundary → capitalize
                clause = clause[:1].upper() + clause[1:]
            parts.append(j + clause)
            continue
        mv = f.get("move")
        if mv:                                    # a typed `move` with no explicit `join`:
            if mv in MOVES:                       # realize its default connector (MOVES imported up top)
                conn = MOVES[mv][1]
                if conn.strip().endswith((".", "!", "?")):
                    parts.append(conn + clause[:1].upper() + clause[1:])
                else:
                    parts.append("; " + conn + clause)
                continue
        edge = text[i - 1] in f.get("from", [])
        if edge and f.get("glue"):
            g = f["glue"]
            conn = g if g.endswith(" ") else g + " "
        elif edge and f["_src"] == primary and F[text[i - 1]]["_src"] == primary:
            conn = GLUE[woven % len(GLUE)]
            woven += 1
        else:
            conn = ""
        parts.append("; " + conn + clause)
    return "".join(parts) + "."


def project(cfg: dict, target: str = "pandoc") -> str:
    F, primary = {}, cfg["bibs"][0].name
    for b in cfg["bibs"]:
        F.update(entries(b))
    pdir = cfg["out"].parent
    by_sec = {}
    for k, f in F.items():
        if f.get("section"):
            by_sec.setdefault(f["section"], []).append(k)
    # global prose linearization (rubric order × dep_order) — positions used to project
    # a claim's long (non-adjacent) grounding edges as cross-references.
    pos, _i = {}, 0
    for sk, _t in rubric(cfg["rubric"]):
        for k in dep_order(by_sec.get(sk, []), F):
            pos[k] = _i
            _i += 1
    # transitive reduction of the grounding DAG — project only references the reader
    # cannot already reach through a shorter rests-on path (drop redundant clutter).
    reduced = transitive_reduction({k: f.get("rests-on", []) for k, f in F.items()})
    footnotes: dict = {}                              # expound-rung materializations, in document order

    lines = [f"# {cfg['title']}", ""]
    if cfg["subtitle"]:
        lines += [f"*{cfg['subtitle']}*", ""]
    for n, (sk, title) in enumerate(rubric(cfg["rubric"]), 1):
        lines += [f"## {n}. {title}" if cfg["numbered"] else f"## {title}", ""]
        keys = dep_order(by_sec.get(sk, []), F)
        if not keys:
            lines += ["<!-- structural section: connective prose, no required claim atom -->", ""]
            continue
        # Walk the section in dependency order, interleaving woven-prose runs with placed asset blocks and
        # NESTED PROOF STEPS: a run of (depthless) claims weaves into one paragraph; an emit: warrant flushes
        # it then drops its block; a claim carrying `depth = N` is a proof step, rendered as a Markdown list
        # item indented by N (so a decomposed proof reads as an outline, not interleaved flat prose).
        run: list = []
        in_list = [False]

        def _blank():
            if lines and lines[-1] != "":
                lines.append("")

        def _flush():
            if run:
                lines.append(weave(run, F, primary, pos, reduced, footnotes, target))
                run.clear()

        def _close_list():
            if in_list[0]:
                _blank()
                in_list[0] = False

        for k in keys:
            f = F[k]
            if f.get("depth"):                       # a nested proof step → indented list item (tight)
                if not in_list[0]:
                    _flush()
                    _blank()
                    in_list[0] = True
                item = weave([k], F, primary, pos, reduced, footnotes, target)
                lines.append("  " * (int(f["depth"]) - 1) + "- " + item)
            elif f.get("emit"):
                _close_list()
                if f.get("claim") or f.get("title"):
                    run.append(k)
                _flush()
                _blank()
                lines += emit_block(pdir, f)
                _blank()
            elif f.get("check", "").startswith("figure:"):
                continue
            else:
                _close_list()
                run.append(k)
        _close_list()
        _flush()
        _blank()
    # the expound rung: a claim's `link` materialized as a document-end footnote
    # (the marker rode the sentence; the explanation + its citations land here).
    if footnotes:
        lines += [f"[^{k}]: {v[:1].upper() + v[1:]}" for k, v in footnotes.items()] + [""]
    if cfg["references"]:
        lines += ["## References", ""]
    return "\n".join(lines).rstrip("\n") + "\n"          # exactly one trailing newline (MD012-clean)


def main(argv: list) -> int:
    config.apply_args(argv)
    pos = config.positionals(argv)
    project_dir = Path(pos[0]).resolve() if pos else Path.cwd()
    cfg = load_config(project_dir)
    pol = tomllib.loads((project_dir / "paper.toml").read_text()).get("paper", {})

    out = project(cfg, config.resolve(config.TARGET, pol))   # Ω·config: pandoc (default) | web

    if config.resolve(config.CHECK):
        tgt = cfg["out"]
        if not tgt.exists() or tgt.read_text() != out:
            print(f"paperkit-project: {tgt.name} ≠ projection — regenerate "
                  f"(paperkit-project)", file=sys.stderr)
            return 1
        print(f"paperkit-project: {tgt.name} ≡ projection ({len(out.split())} words)")
        return 0
    if "-o" in argv and argv[argv.index("-o") + 1] == "-":
        sys.stdout.write(out)
        return 0
    cfg["out"].write_text(out)
    print(f"paperkit-project: wrote {cfg['out'].name} ({len(out.split())} words)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
