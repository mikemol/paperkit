#!/usr/bin/env python3
"""paperkit project — emit a paper's prose by PROJECTING it from the warrant set.

A paper is the projection of a claim-DAG.  Each entry in a `.bib` is a claim:
a statement (`claim`/`title`), a rubric `section`, its dependencies (`from`),
and a verifier (`check`).  This command reads those records and emits the prose —
every section's claims ordered by their `from` edges and joined with connective
`glue` across genuine entailment edges.  The output passes the gate (every
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
    for pat, rep in _LATEX:
        s = re.sub(pat, rep, s)
    return re.sub(r"[{}]", "", s).strip().rstrip(".")


def load_config(project: Path) -> dict:
    cfg = project / "paper.toml"
    if not cfg.exists():
        sys.exit(f"paperkit: no paper.toml in {project}")
    p = tomllib.loads(cfg.read_text()).get("paper", {})
    return {
        "title": p.get("title", "Untitled"),
        "subtitle": p.get("subtitle", ""),
        "rubric": project / p.get("rubric", "rubric.tsv"),
        "bibs": [project / b for b in p.get("warrants", ["warrants.bib"])],
        "out": project / p.get("out", "paper.md"),
        "numbered": p.get("numbered", True),
        "references": p.get("references", True),
    }


def entries(path: Path) -> dict:
    """{key: {field: cleaned-value, _src}} for one .bib."""
    out = {}
    if path.exists():
        for m in re.finditer(r"@\w+\{\s*([^,\s]+)\s*,(.*?)\n\}", path.read_text(), re.S):
            key, body = m.group(1), m.group(2)
            f = {"_src": path.name}
            for name in ("title", "author", "year", "note", "section", "claim", "check", "glue", "join", "move", "emit", "mem"):
                fm = re.search(r"\b" + name + r"\s*=\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", body)
                if fm:
                    f[name] = fm.group(1)
            # `from` = prose-order edge (sets dep_order + glue).  `rests-on` =
            # grounding/entailment edge (what the claim's credibility rests on);
            # used for adequacy clamping, NOT for prose.  They are often reversed:
            # prose runs general→specific, grounding runs specific→general.
            for field in ("from", "rests-on"):
                fr = re.search(r"\b" + field + r"\s*=\s*\{([^}]*)\}", body)
                f[field] = [a for a in re.split(r"[,\s]+", fr.group(1)) if a] if fr else []
            out[key] = f
    return out


def rubric(path: Path) -> list:
    out = []
    for ln in path.read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "\t" in ln:
            # key <TAB> title [<TAB> scheme …]; the title is the 2nd column only.
            # A 3rd column (rhetorical scheme) is read by rhetoric.py, not here.
            parts = ln.split("\t")
            out.append((parts[0].strip(), parts[1].strip()))
    return out


def dep_order(keys: list, F: dict) -> list:
    seen, out = set(), []

    def visit(k):
        if k in seen or k not in keys:
            return
        seen.add(k)
        for a in F.get(k, {}).get("from", []):
            visit(a)
        out.append(k)

    for k in keys:
        visit(k)
    return out


def short_author(a: str) -> str:
    a = clean(a)
    names = re.split(r"\s+and\s+", a)
    if len(names) > 2:
        return names[0].split()[-1] + " et al."
    return " & ".join(n.split()[-1] if " " in n else n for n in names)


def sentence(key: str, f: dict, primary: str) -> str:
    """A claim sentence ending with its [@key] tag.  Prefer an explicit `claim`;
    else a warrant's `title` (the title IS the claim); else a terse cite."""
    if f.get("claim"):
        return f"{clean(f['claim'])} [@{key}]"
    title = clean(f.get("title", key))
    if f["_src"] == primary:
        return f"{title} [@{key}]"
    yr = f.get("year", "")
    who = short_author(f.get("author", "")) if "author" in f else ""
    paren = ", ".join(x for x in (who, yr) if x)
    return f"{title}" + (f" ({paren})" if paren else "") + f" [@{key}]"


GLUE = ["and from that, ", "so "]

# A placed (not woven) warrant emits a verbatim asset instead of a sentence; the
# fence language is inferred from the asset's extension (empty = raw include, for
# markdown tables and prose snippets).
FENCE = {".sh": "sh", ".bash": "sh", ".py": "python", ".toml": "toml",
         ".bib": "bibtex", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
         ".txt": "text", ".tsv": "text", ".md": ""}   # .md = raw include (tables)


def is_placed(f: dict) -> bool:
    """A warrant projected as a block (emit:) or a figure — placed verbatim, not
    woven into prose, and so covered by its placement rather than a citation."""
    return bool(f.get("emit")) or f.get("check", "").startswith("figure:")


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


def weave(text: list, F: dict, primary: str) -> str:
    """Weave a run of prose-claim keys into one sentence-diagrammed paragraph."""
    clauses = [sentence(k, F[k], primary) for k in text]
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
            from rhetoric import MOVES            # realize its default connector (lazy: cycle)
            if mv in MOVES:
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


def project(cfg: dict) -> str:
    F, primary = {}, cfg["bibs"][0].name
    for b in cfg["bibs"]:
        F.update(entries(b))
    pdir = cfg["out"].parent
    by_sec = {}
    for k, f in F.items():
        if f.get("section"):
            by_sec.setdefault(f["section"], []).append(k)

    lines = [f"# {cfg['title']}", ""]
    if cfg["subtitle"]:
        lines += [f"*{cfg['subtitle']}*", ""]
    for n, (sk, title) in enumerate(rubric(cfg["rubric"]), 1):
        lines += [f"## {n}. {title}" if cfg["numbered"] else f"## {title}", ""]
        keys = dep_order(by_sec.get(sk, []), F)
        if not keys:
            lines += ["<!-- structural section: connective prose, no required claim atom -->", ""]
            continue
        # Walk the section in dependency order, interleaving woven-prose runs with
        # placed asset blocks: a run of claims weaves into one paragraph; an emit:
        # warrant flushes that paragraph then drops its verbatim block in place.
        run: list = []
        for k in keys:
            f = F[k]
            if f.get("emit"):
                # A healthy example is CITED: if the warrant also carries a claim,
                # its sentence (with its [@key]) closes the current paragraph and
                # introduces the block, so the placement is referenced, not orphaned.
                if f.get("claim") or f.get("title"):
                    run.append(k)
                if run:
                    lines += [weave(run, F, primary), ""]
                    run = []
                lines += emit_block(pdir, f) + [""]
            elif f.get("check", "").startswith("figure:"):
                continue
            else:
                run.append(k)
        if run:
            lines += [weave(run, F, primary), ""]
    if cfg["references"]:
        lines += ["## References", ""]
    return "\n".join(lines) + "\n"


def main(argv: list) -> int:
    args = [a for a in argv if not a.startswith("-")]
    project_dir = Path(args[0]).resolve() if args else Path.cwd()
    cfg = load_config(project_dir)
    out = project(cfg)

    if "--check" in argv:
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
