#!/usr/bin/env python3
"""paperkit.bib — the ONE parser + data model for a warrants `.bib` (the claim-DAG).

A `.bib` entry is a claim: `@type{key, field = {value}, ...}`.  This module is the
single source of truth for that grammar and the small data-model over it (config
load, rubric, dependency order, placement).  It was previously three parsers —
the projector's field-whitelist `entries`, footdeps' line scanner for `reads`,
and coherence's line scanner for `rests-on` — each re-deriving the format and
disagreeing on which fields survive (the whitelist dropped `reads`).  Now there is
one: `parse()` returns the FULL record per claim and every consumer projects the
fields it wants.

Scalar fields are carried verbatim (LaTeX un-expanded — the projector cleans on
render); the edge/token fields (`from`, `rests-on`, `reads`) are lists.
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import re

# scalar fields carried verbatim (the projector + checks read these).  `tier` is a per-warrant
# enforcement-tier flag consumed by the GENERATOR (bibtex.bzl), not by any engine code here —
# tier ∈ {sandbox (hermetic, mutation-swept), local (host-coupled, uncached), toolchain (host
# toolchain, cached + stamped)}; a non-sandbox check runs on the host, gated but not swept.  paperkit
# parses and carries it so it is a quiet, owned field, not a loud-dropped unknown; the generator
# reads the same bib text (Ζ·tier).
_SCALAR = ("title", "author", "year", "note", "section", "claim",
           "check", "glue", "join", "move", "emit", "as", "mem", "link", "depth", "tier")
# list-valued fields.  `from` = prose-order edge (dep_order + glue); `rests-on` =
# grounding/entailment edge (adequacy clamping, NOT prose) — the two are often
# reversed (prose runs general→specific, grounding specific→general); `reads` =
# the declared cross-package footprint (the declare+audit source, Ζ·foot);
# `consumes` = sibling warrant keys whose verdict RECORD this check reads (records-as-deps).
_LIST = ("from", "rests-on", "reads", "consumes")
# Standard BibTeX reference metadata paperkit TOLERATES on a references.bib citation but does
# not consume (the projector reads only title/author/year).  Kept so the unknown-field warning
# below fires on a MEANINGFUL dropped field (a downstream author's `points`, a mistyped `check`)
# and stays quiet on ordinary bibliography metadata that is expected to be carried and ignored.
_BIBTEX = frozenset({
    "journal", "volume", "number", "pages", "booktitle", "doi", "url", "publisher", "editor",
    "address", "month", "isbn", "issn", "organization", "school", "institution", "series",
    "chapter", "edition", "howpublished", "eprint", "archiveprefix", "primaryclass", "keywords",
})
_WARNED: set = set()          # (file, key, field) already reported — a build parses each bib many times


def _unescaped_braces(s: str):
    """Yield (index, char) for every `{`/`}` in `s` that is NOT LaTeX-escaped (`\\{` `\\}`).
    Inline math in a claim carries literal braces — set notation `\\{ x : … \\}`, `\\mathrm{}` —
    that are CONTENT, not structure; counting them as structural braces miscounts the depth and
    truncates the field.  A brace is escaped iff preceded by an odd run of backslashes."""
    for i, ch in enumerate(s):
        if ch in "{}":
            bs = 0
            j = i - 1
            while j >= 0 and s[j] == "\\":
                bs += 1
                j -= 1
            if bs % 2 == 0:                      # even (incl. zero) backslashes → a real brace
                yield i, ch


def _scalar_value(body: str, name: str) -> str | None:
    """The value of scalar field `name` by TRUE brace-counting from its `name = {` — handles
    arbitrary nesting depth (`\\min\\{ \\mathrm{eff}(d) : … \\}`) and skips LaTeX-escaped braces,
    where the one-level regex it replaces would stop at the first inner `}`.  None if absent."""
    m = re.search(r"\b" + re.escape(name) + r"\s*=\s*\{", body)
    if not m:
        return None
    start = m.end()                              # first char inside the opening brace
    depth = 1
    for i, ch in _unescaped_braces(body[start:]):
        depth += 1 if ch == "{" else -1
        if depth == 0:
            return body[start:start + i]
    return None                                  # unbalanced — no closing brace (caller sees absent)


def _top_fields(body: str) -> list:
    """The TOP-LEVEL `name = {` field names in an entry body, tracking brace depth so an `=`
    inside a value (set notation `x = {1,2}` in a claim) is not mistaken for a field.  Used to
    catch a field the parser does not consume — which it would otherwise drop in silence.  Skips
    LaTeX-escaped braces (`\\{` `\\}`) so inline math does not throw off the depth (same fix as
    _scalar_value)."""
    names, depth = [], 0
    real = dict(_unescaped_braces(body))                 # index → real brace char (escaped skipped)
    for m in re.finditer(r"([A-Za-z][\w-]*)\s*=\s*\{|[{}]", body):
        tok = m.group(0)
        if tok in "{}":
            if m.start() in real:                        # count only UNescaped structural braces
                depth += 1 if tok == "{" else -1
                depth = max(0, depth)
        else:                                            # a `name = {` — a field only at top level
            if depth == 0:
                names.append(m.group(1))
            depth += 1                                   # entered the value's brace
    return names


def parse(path: Path, consumer_fields: tuple = ()) -> dict:
    """{key: {field: value, _src}} for one .bib (a missing file → {}).

    `consumer_fields` are extra scalar fields a PROJECT has DECLARED it tolerates (via its
    paper.toml `consumer_fields`, resolved in load_config) — carried verbatim like _SCALAR but
    consumed by NO paperkit invariant (the projector and gate ignore them); a downstream consumer
    reads them.  This is the mechanism/policy split: paperkit owns the mechanism (parse-and-carry a
    declared field), the vocabulary is the consumer's (declared per project, not baked into the
    engine — a domain-and-location-free engine must not learn one consumer's field names).  A
    DECLARED field is quiet in the loud-drop below; an UNdeclared unknown field is still named loud,
    so the declaration is what distinguishes a consumer's field from a typo."""
    out = {}
    path = Path(path)
    scalars = tuple(_SCALAR) + tuple(consumer_fields)
    if path.exists():
        for m in re.finditer(r"@\w+\{\s*([^,\s]+)\s*,(.*?)\n\}", path.read_text(), re.S):
            key, body = m.group(1), m.group(2)
            f = {"_src": path.name}
            for name in scalars:
                v = _scalar_value(body, name)            # true brace-counting, escaped-brace-safe
                if v is not None:
                    f[name] = v
            for name in _LIST:
                fr = re.search(r"\b" + name + r"\s*=\s*\{([^}]*)\}", body)
                f[name] = [a for a in re.split(r"[,\s]+", fr.group(1)) if a] if fr else []
            # Ζ·ladder·sentinel (the parser's face) — a field paperkit does not consume is DROPPED,
            # and a silent drop is a silent failure: a downstream author's `points` (a real grounding
            # relation) vanished on 14 entries with no signal.  Name it LOUD rather than drop it in
            # silence — but stay quiet on standard BibTeX metadata (_BIBTEX), which references carry
            # and paperkit is expected to ignore, and on this project's DECLARED consumer fields.  A
            # warning, not a refusal: the field may be deliberate human documentation, and breaking a
            # downstream's build is not the point — being SEEN is.  Deduped, since a build parses each
            # bib many times.
            unknown = [n for n in _top_fields(body)
                       if n not in scalars and n not in _LIST and n not in _BIBTEX]
            for n in unknown:
                if (path.name, key, n) not in _WARNED:
                    _WARNED.add((path.name, key, n))
                    print(f"paperkit-bib: {path.name} @{key}: field '{n}' is not a paperkit field "
                          f"and was DROPPED (not silently) — paperkit reads "
                          f"{', '.join(list(_SCALAR) + list(_LIST))}"
                          + (f" plus this project's declared {', '.join(consumer_fields)}"
                             if consumer_fields else "")
                          + "; use one, or remove it", file=sys.stderr)
            out[key] = f
    return out


def _bibpath(project: Path, b: str) -> Path:
    """Resolve a warrants token to a path.  A bare basename is relative to the project dir; a Bazel
    LABEL (//pkg:file, //:path/file, @repo//…) is a bib imported from the concept library, resolved
    repo-root-relative — correct when the importer IS the root project (project == repo root, the
    README-import case).  Mirrors the generator's label branch so ONE warrants list drives both."""
    if b.startswith("//") or ":" in b or b.startswith("@"):
        pkg, _, name = b.split("//", 1)[1].partition(":")
        return project / (f"{pkg}/{name}" if pkg else name)
    return project / b


def paper_keys() -> tuple:
    """The [paper] keys `load_config` actually reads — parsed from its OWN source.

    Λ·registry — the set has ONE owner: the `p.get("k", …)` calls in load_config.  A guard that
    kept its own copy would certify a tautology the moment the two drifted, and adding a key
    would then be a two-site edit with no signal when only one site was done.  checks/gen_fields.py
    derives the documented key table the same way, from the same source."""
    import inspect
    import re
    src = inspect.getsource(load_config)
    seen = []
    for k in re.findall(r'p\.get\(\s*"([^"]+)"', src):
        if k not in seen:
            seen.append(k)
    return tuple(seen)


def _param_config_keys() -> tuple:
    """The [paper] keys owned by Ω·config Params, read from the engine's own sources via AST.

    Λ·registry — a Param DECLARES its paper.toml key (`Param(..., config="root")`), so the
    declarations are the owner.  Parsed rather than imported: load_config runs on every gate
    invocation and importing every engine module here would be both slow and circular.  AST,
    never grep — a regex matches the name in prose and strings too (the lesson closure.py
    records); this reads the keyword argument of an actual Param(...) call.

    ⚑ THE [paper] KEY SET HAS TWO OWNERS.  load_config's `p.get` calls are one; these Params are
    the other, and they are what makes `root` a [paper] key even though load_config never reads
    it.  A guard over only the first would have missed the very instance that prompted it."""
    import ast as _ast
    out = []
    for f in sorted(Path(__file__).resolve().parent.glob("*.py")):
        try:
            tree = _ast.parse(f.read_text())
        except (OSError, SyntaxError):
            continue
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            fn = node.func
            if getattr(fn, "id", None) != "Param" and getattr(fn, "attr", None) != "Param":
                continue
            for kw in node.keywords:
                if kw.arg == "config" and isinstance(kw.value, _ast.Constant) \
                        and isinstance(kw.value.value, str) and kw.value.value not in out:
                    out.append(kw.value.value)
    return tuple(out)


def _misplaced_paper_key(cfg: Path) -> None:
    """Refuse LOUDLY if a [paper] key was declared in a table that is not [paper].

    Ζ·toml·scope — the general form of Ζ·consumer·scope, which guarded exactly one key.  TOML
    scoping is POSITIONAL and invisible: `root = "."` on line 8 with `[paper]` opening on line 10
    is inert, while the same three characters above line 1 of a `[paper]`-first file are correct.
    Same characters, opposite effect, indistinguishable by eye.

    Three faces are on record, and only the first was guarded:
      · `consumer_fields` under a [checks.X] header — a downstream consumer lost SIX fields, and
        the only signal was drop-warnings scrolling past a green exit.
      · the [checks.claim]-cmd shadowing trap — same class, one level down.
      · `root` declared ABOVE [paper] — reported by summit against memmesh.  layout.py reads
        `.get("paper", {})`, so a top-level key is outside that dict.  ⚑ An absent root is
        INFERRED SILENTLY, so the misplacement is unfalsifiable on every green board until the
        one run where Δ actually copies the parent — the most expensive possible moment.

    Two of the three were found by downstream consumers, and paperkit's own eleven paper.toml
    files are all correctly scoped: this is a trap that catches CONSUMERS and never us, which is
    why it survived two sightings.  So the check is TOTAL over the owner's key set rather than
    per-key, and it covers the TOP LEVEL as well as sibling tables — the top level is where the
    reported instance actually sat, and the per-key guard did not look there at all.

    REFUSES rather than warns: a warning is what the consumer already had, and it did not stop
    the build."""
    import tomllib as _t
    keys = set(paper_keys()) | set(_param_config_keys())
    raw = _t.loads(cfg.read_text())

    def _refuse(key, where):
        sys.exit(f"paperkit: `{key}` is declared {where}, but it belongs under [paper].  TOML "
                 f"scoped it out of the [paper] table, so the engine reads NONE of it and the "
                 f"build would still report success.  Move it below the [paper] header.")

    for k, v in raw.items():                       # the TOP level: a key above [paper]
        if k in keys and not isinstance(v, dict):
            _refuse(k, "at the top level of paper.toml (above any [paper] header)")
    for table, body in raw.items():                # any NON-[paper] table, and its subtables
        if table == "paper" or not isinstance(body, dict):
            continue
        for k, v in body.items():
            if k in keys and not isinstance(v, dict):
                _refuse(k, f"under [{table}]")
            if isinstance(v, dict):
                for k2 in v:
                    if k2 in keys:
                        _refuse(k2, f"under [{table}.{k}]")


def _misplaced_consumer_fields(cfg: Path) -> list:
    """[] — and a LOUD refusal first if `consumer_fields` was declared in the wrong TOML table.

    Called as load_config's DEFAULT for the key, so the `p.get("consumer_fields", ...)` read stays
    visible in load_config's own source: checks/gen_fields.py derives the documented [paper] key
    set by parsing that source, and a read hidden inside a helper silently drops the key from the
    generated field table (measured — it reddened rm-fields).

    Ζ·consumer·scope — `consumer_fields` belongs under [paper].  Put it after a [checks.X] header
    and TOML scopes it into THAT table, so `paper.get("consumer_fields")` is empty, every declared
    field loud-drops as unknown, and THE BUILD STILL REPORTS SUCCESS.  Reported by a downstream
    consumer who lost six fields that way; the only signal was drop-warnings scrolling past a
    green exit.  Same class as the [checks.claim]-cmd shadowing trap: a real misconfiguration
    that degrades the output while the gate stays quiet.

    A misplaced key is unambiguous — no other table has any use for it — so this REFUSES rather
    than warning.  A warning is what they already had, and it did not stop the build."""
    import tomllib as _t
    raw = _t.loads(cfg.read_text())
    for table, body in raw.items():
        if table != "paper" and isinstance(body, dict):
            for sub, inner in list(body.items()) + [(table, body)]:
                d = inner if isinstance(inner, dict) else body
                if isinstance(d, dict) and "consumer_fields" in d:
                    sys.exit(f"paperkit: `consumer_fields` is declared under [{table}"
                             f"{'.' + sub if isinstance(inner, dict) else ''}], but it belongs "
                             f"under [paper].  TOML scoped it into that table, so the engine sees "
                             f"NONE and every field you declared would drop silently.")
    return []


def load_config(project: Path) -> dict:
    cfg = project / "paper.toml"
    if not cfg.exists():
        sys.exit(f"paperkit: no paper.toml in {project}")
    _misplaced_paper_key(cfg)          # Ζ·toml·scope — refuse a [paper] key scoped out of [paper]
    p = tomllib.loads(cfg.read_text()).get("paper", {})
    return {
        "title": p.get("title", "Untitled"),
        "subtitle": p.get("subtitle", ""),
        # The project DIRECTORY — where warrants and rubric live, and the FIRST anchor emit: assets
        # resolve against (see emit_anchors): a project whose `out` points OUTSIDE itself keeps its
        # assets here.  out.parent (the OUTPUT location, which `out = "../../foo.md"` can push
        # outside the project) is the SECOND anchor, for a project whose assets sit beside `out`
        # (the mirror layout).  The two coincide for an in-repo project.
        "project_dir": project,
        "rubric": project / p.get("rubric", "rubric.tsv"),
        "bibs": [_bibpath(project, b) for b in p.get("warrants", ["warrants.bib"])],
        "out": project / p.get("out", "paper.md"),
        "numbered": p.get("numbered", True),
        # ISO 24495-1 one-topic-per-paragraph: "claim" gives each claim its
        # own paragraph; "woven" (default) joins a section into running prose.
        "paragraph": p.get("paragraph", "woven"),
        "references": p.get("references", True),
        "adequacy": p.get("adequacy", False),   # Ζ·project: emit a Δ-adequacy Bazel test for this project
        # Extra scalar fields THIS project declares it tolerates — a downstream consumer's vocabulary
        # (e.g. a summit report's reporter/genre/target), carried by the parser but consumed by no
        # paperkit invariant.  The policy (which fields) is the consumer's, declared here per project;
        # the mechanism is the engine's.  An UNdeclared unknown field is still named loud by parse.
        "consumer_fields": tuple(p.get("consumer_fields", _misplaced_consumer_fields(cfg))),
        # Ζ·talk·tier — the check TYPES this project declares NON-MECHANICAL: gated, never graded.
        # A `premise:` ("everyone here has shipped a doc that lies") or a `definition:` ("a passing
        # example is DOCUMENTATION") is not a claim a mutation can flip; its `cmd = "true"` is
        # unfalsifiable BY CONSTRUCTION, so the def-sweep correctly measures sens=∅ and the grade
        # lands `indeterminate` — below the adequacy floor.  That is a true measurement of a claim
        # that was never a sweep candidate, and failing adequacy on it would force the project to
        # either delete its honest premises or dress them in a fake mechanism, which is exactly the
        # dishonesty the premise: verb exists to prevent.
        #
        # DECLARED, never inferred: `cmd == "true"` would be a tempting tell and a hole — any
        # project could then silence adequacy by routing a real claim through a trivial command.
        # The declaration is the policy (the project's), the exclusion is the mechanism (the
        # engine's) — the same split as consumer_fields above.  Same shape as `tier`, which
        # already means "gated but not graded" for a host-run check the sandbox cannot grade.
        "nonmechanical": tuple(sorted(
            t for t, spec in tomllib.loads(cfg.read_text()).get("checks", {}).items()
            if isinstance(spec, dict) and spec.get("mechanical") is False)),
    }


def parse_project(project_dir: Path) -> dict:
    """Every entry across a project's warrant bibs, parsed with the project's DECLARED consumer
    fields resolved from its paper.toml — the ONE place that binds "which extra fields this project
    tolerates" to the parse, so no caller re-implements the load-config-then-parse-all loop (and
    none can forget to pass consumer_fields, silently strict-rejecting a declared field)."""
    cfg = load_config(project_dir)
    F = {}
    for b in cfg["bibs"]:
        F.update(parse(b, cfg["consumer_fields"]))
    return F


def load_bib(bib_path: Path, project_dir: Path) -> dict:
    """Parse ONE bib with the consumer_fields declared by project_dir's paper.toml — the single-bib
    analogue of parse_project, for a caller that reads a LONE bib by a narrower projection (footdeps: a
    MODULE.bazel row's bib; gen_formulas: one of paper/*.bib) rather than a project's full warrant list.
    It still binds the project's DECLARED consumer fields, so such a caller cannot loud-drop a field the
    project carries — the same "none can forget" owner as parse_project, one bib at a time.  load_config
    exits on a missing paper.toml, so a caller against an unconfigured tree must guard existence first."""
    return parse(bib_path, load_config(project_dir)["consumer_fields"])


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


def is_placed(f: dict) -> bool:
    """A warrant projected as a block (emit:) or a figure — placed verbatim, not
    woven into prose, and so covered by its placement rather than a citation."""
    return bool(f.get("emit")) or f.get("check", "").startswith("figure:")


def emit_anchors(cfg: dict, emit: str) -> list:
    """The DISTINCT directories that hold a placement asset, in RESOLUTION ORDER — beside the
    warrants (`project_dir`) FIRST, then beside the output (`out.parent`).  An index-extension,
    NOT a choice of anchors: a project whose `out` points OUTSIDE itself keeps its assets by the
    project dir, and a project whose assets sit BESIDE `out` (the mirror layout) keeps them there;
    the two coincide for an in-repo project, so this returns ONE entry there.

    `[]`      — the asset is at NEITHER anchor: genuinely ABSENT.
    `len 1`   — resolved unambiguously (the common case, always so in-repo).
    `len 2`   — it is at BOTH distinct anchors, which is a LAYOUT AMBIGUITY the caller must SURFACE
                (the gate does) rather than silently resolve — a silent patch is silent debt.

    (629af60 keyed emit: on `project_dir` UNCONDITIONALLY — `cfg.get("project_dir") or out.parent`,
    the `or` dead because load_config always sets project_dir — which fixed the out-outside case
    and broke the mirror layout it did not consider.  The real fallback its message promised is
    this ordered lookup over both.)"""
    seen, hits = set(), []
    for anchor in (cfg["project_dir"], cfg["out"].parent):
        d = Path(anchor).resolve()
        if d in seen:                            # in-repo: the two anchors are one dir
            continue
        seen.add(d)
        p = d / emit
        if p.exists():
            hits.append(p)
    return hits


def emit_path(cfg: dict, emit: str) -> "Path | None":
    """The path a placement asset RESOLVES to for READING — the first anchor that holds it
    (project_dir before out.parent, deterministic so the projection is stable), or None when
    neither does.  The projector reads this; the GATE surfaces the ambiguity when BOTH hold it
    (emit_anchors, len 2), so a coin-flip the author did not intend never resolves in silence."""
    hits = emit_anchors(cfg, emit)
    return hits[0] if hits else None


def rests_closure(seed: set, F: dict) -> tuple:
    """The transitive closure of `seed` under `rests-on` (grounding) edges.

    A cited/placed claim's grounding premises are part of the argument whether or
    not a marker for them survives in the rendered prose (plain/footnote render no
    [@key]; adjacent and cross-scope edges render nothing on ANY target) — so the
    verified set must include every claim REACHABLE from the seed along rests-on,
    recursively.  Cycles are handled (each key is visited once).  Returns
    (reachable, dangling): reachable ⊇ seed ∩ F; dangling is the set of
    (claim, target) edges whose target is defined in no bib — a broken grounding.
    """
    seen, dangling = set(), set()
    stack = [k for k in seed if k in F]
    while stack:
        k = stack.pop()
        if k in seen:
            continue
        seen.add(k)
        for y in F[k].get("rests-on", []):
            if y not in F:
                dangling.add((k, y))
            elif y not in seen:
                stack.append(y)
    return seen, dangling
