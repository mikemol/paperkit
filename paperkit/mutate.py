#!/usr/bin/env python3
"""Ζ·mutant — the PURE perturbation leaf: given a .py module and a mutation SPEC, emit the perturbed
module.  A perturbation TOGGLES an element's PRESENCE between the actual source and a nearby
counterfactual (Ζ·mutant·struct — drop the present, inject the absent):

    ""                the IDENTITY (∅): byte-identical, the baseline point of the mutation set — an
                      eval against it measures the UNMUTATED check in the same sandbox (sens.py's
                      validity witness).
    <qualname>        DROP a def's BEHAVIOUR — its body → an uncatchable raise (present → absent),
    or  def:<qualname>    the rest byte-identical, so a witness flips only if it EXERCISES that def.
    branch:<qn>#<n>   DROP one BRANCH ARM's behaviour — the arm's body → the SAME uncatchable raise, the
                      rest byte-identical (Μ·sweep·atom — a FINER, still-MONOTONE atom than def:).  It
                      grades whether a witness REACHES that arm; it is ADDITIVE to def: (both cells exist),
                      never a replacement.  An arm enclosed by a `except BaseException` / bare `except:`
                      handler is REFUSED (the raise would be swallowed → non-monotone) — see _branch_sites.
    flip:<qn>#<n>     INVERT one CONDITION (`if C` → `if not (C)`) — NON-monotone (a wrong-but-non-crashing
                      value flips only if the witness ASSERTS on it), so it is BARRED from the sensitivity
                      sweep and feeds the ORTHOGONAL `decisions_unasserted` axis, never the grade ladder.
    data-:<qn>#<n>    DROP one KEY/ELEMENT of a module-level dict/list/set/tuple LITERAL (Μ·sweep·atom, the
                      DATA cell of the Klein four-group: axis code↔data × drop↔perturb).  Present → absent,
                      MONOTONE like def:/branch: — a witness reading that key flips (membership False, or a
                      KeyError on bare subscript) — so it feeds the SENSITIVITY sweep.  A key whose dict is
                      read ONLY via `.get(k, DEFAULT)` / `except KeyError` is REFUSED (the default swallows
                      the drop → non-monotone, the DATA analog of branch:'s BaseException-enclosure).
    dflip:<qn>#<n>    PERTURB one VALUE of a dict-value / list-element to a counterfactual (a VALID-ENUM
                      sibling where the literal has a finite value domain, else a distinct marker) —
                      NON-monotone (a wrong value flips only if the witness ASSERTS on it), so it is BARRED
                      from the sweep and feeds `decisions_unasserted`, exactly like flip:.  The (data,perturb)
                      cell.  Never applies to bare set membership (a set element has no value to perturb).
    import-:<name>    DROP `import <name>` / `from <name> import …` (a present import → absent) — a
                      POSITIVE import-dependence flips.
    import+:<name>    INJECT `import <name>` (an absent import → present) — the NEGATIVE polarity that
                      falsifies a "module does NOT import X" assertion (the Π counter-fixture, as a
                      grid mutation rather than a hand-written one).

The mechanical AST surgery ONLY — not the sensitivity interpretation (what a flip MEANS, the
group-testing, the fingerprint), which stays in grader.py.  A pure function, so the Bazel mutant
graph (pk_mutate prepares one perturbed module per site, pk_eval runs a check against it) builds on
it without importing the sweep.  Ν·loud (KeyError) on a spec that names no such element — a real miss
is never a silent no-op.  CLI: `mutate.py <module.py> <spec>` prints the perturbed module to stdout.
"""
from __future__ import annotations

import ast
import sys


def _def_sites(text: str) -> list:
    """Every def/method in a .py source as (qualname, node).  Mutation resolution for CODE is the
    DEFINITION, not the file: corrupting a whole file breaks its import and flips every witness
    identically; replacing one function's BODY leaves the module importable, so a witness flips only
    if it actually exercises that function.  A one-liner (`def f(): return 1`) shares its signature
    line with the body, so a line-span replacement can't isolate the body — it is skipped.
    """
    out: list = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out

    def rec(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.body[0].lineno > child.lineno:
                    out.append((prefix + child.name, child))
                rec(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                rec(child, prefix + child.name + ".")
            else:
                rec(child, prefix)

    rec(tree, "")
    return out


def _base_catching_regions(tree) -> set:
    """The set of AST nodes that live in a `try` BODY whose handlers catch BaseException / bare `except:`.
    A `raise BaseException('PAPERKIT_MUT')` planted anywhere in such a region would be SWALLOWED — so a
    branch: mutation there is NON-monotone and MUST be refused (Μ·sweep·atom precondition, revision a).
    Intra-def only: a DYNAMIC catcher (contextlib.suppress(BaseException), or a caller-frame handler
    outside the def) is invisible here — currently no swept module uses either, but if one appears this
    must widen (the branch: canary + the ∅-baseline/pk_canary guards catch a live regression loudly).
    """
    unsafe: set = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Try) and any(
                h.type is None or (isinstance(h.type, ast.Name) and h.type.id == "BaseException")
                for h in n.handlers):
            for stmt in n.body:                          # the protected region (NOT the handler bodies)
                for d in ast.walk(stmt):
                    unsafe.add(d)
    return unsafe


def _branch_sites(text: str) -> list:
    """Every mutable BRANCH ARM as (qualname, n, node): the arms of `if/elif/else`, `for`/`while` bodies,
    `try` bodies, and `with` bodies, WITHIN each def, numbered `#n` in stable source order (dependents key
    on the order).  Each arm's body → the same uncatchable raise as def:, so a witness flips only if it
    REACHES that arm — a finer, still-MONOTONE reach probe.  REFUSES an arm inside a BaseException-catching
    region (the raise would be swallowed) and a one-liner arm whose body shares its header line (can't
    isolate the body span), mirroring _def_sites.
    """
    out: list = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    unsafe = _base_catching_regions(tree)

    def arms(stmt):                                      # the mutable sub-bodies of a compound statement
        if isinstance(stmt, ast.If):
            return [stmt.body, stmt.orelse]
        if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)):
            return [stmt.body]
        if isinstance(stmt, ast.Try):
            return [stmt.body, *[h.body for h in stmt.handlers], stmt.orelse, stmt.finalbody]
        return []

    def rec(node, prefix, counter):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                rec(child, prefix + child.name + ".", [0])
            elif isinstance(child, ast.ClassDef):
                rec(child, prefix + child.name + ".", counter)
            else:
                if prefix:                               # only arms INSIDE a def are sites
                    for body in arms(child):
                        # REFUSE (revision a): an arm whose body sits in a BaseException-catching region
                        # (its first statement is `unsafe`) — a planted raise there would be swallowed.
                        if body and body[0] not in unsafe:
                            b0 = body[0]
                            out.append((prefix.rstrip("."), counter[0], (b0, body[-1])))
                            counter[0] += 1
                rec(child, prefix, counter)

    rec(tree, "", [0])
    return out


def _flip_sites(text: str) -> list:
    """Every mutable CONDITION as (qualname, n, test_node): the `test` of each `if`/`while` within a def,
    numbered `#n` in stable source order.  A flip: mutation INVERTS the condition — NON-monotone, so this
    is a SEPARATE generator from _branch_sites; the sensitivity sweep never consumes it (the structural
    bar lives at the consumer, not here).
    """
    out: list = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out

    def rec(node, prefix, counter):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                rec(child, prefix + child.name + ".", [0])
            elif isinstance(child, ast.ClassDef):
                rec(child, prefix + child.name + ".", counter)
            else:
                if prefix and isinstance(child, (ast.If, ast.While)):
                    out.append((prefix.rstrip("."), counter[0], child.test))
                    counter[0] += 1
                rec(child, prefix, counter)

    rec(tree, "", [0])
    return out


def _split_qn_n(arg: str):
    """`<qualname>#<n>` → (qualname, int n).  The finer atoms address an arm/condition WITHIN a def."""
    qn, _, n = arg.rpartition("#")
    return qn, int(n)


def _mutate_branch(text: str, qualname: str, n: int) -> str:
    """DROP one branch arm's behaviour — its body → the uncatchable raise (the same _mutate_lines
    primitive as def:, so branch: IS a raise-kind site).
    """
    for qn, i, (b0, blast) in _branch_sites(text):
        if qn == qualname and i == n:
            lines = text.splitlines(keepends=True)
            col = b0.col_offset
            lines[b0.lineno - 1:blast.end_lineno] = [" " * col + "raise BaseException('PAPERKIT_MUT')\n"]
            return "".join(lines)
    raise KeyError(f"Ζ·mutant: 'branch:{qualname}#{n}' is not a branch-arm site in the module")


def _flip_condition(text: str, qualname: str, n: int) -> str:
    """INVERT one condition — `if C:` → `if not (C):` — via a span rewrite of the test source.  Never
    routed through _mutate_lines (a value-swap is not a raise; it is NON-monotone by design).
    """
    for qn, i, test in _flip_sites(text):
        if qn == qualname and i == n:
            src = ast.get_source_segment(text, test)
            if src is None:
                raise KeyError(f"Ζ·mutant: 'flip:{qualname}#{n}' has no recoverable source span")
            lines = text.splitlines(keepends=True)
            s, sc, e, ec = test.lineno, test.col_offset, test.end_lineno, test.end_col_offset
            if s == e:
                ln = lines[s - 1]
                lines[s - 1] = ln[:sc] + "not (" + src + ")" + ln[ec:]
            else:                                        # multi-line test: rewrite the whole span
                head = lines[s - 1][:sc]
                tail = lines[e - 1][ec:]
                lines[s - 1:e] = [head + "not (" + src + ")" + tail]
            return "".join(lines)
    raise KeyError(f"Ζ·mutant: 'flip:{qualname}#{n}' is not a condition site in the module")


def _swallowing_dicts(tree) -> set:
    """The names of module-level dicts read in a way that would SWALLOW a dropped key: any access
    `<name>.get(k, DEFAULT)` with a real default, or a `try: <name>[k] except KeyError`.  A data-: DROP
    of such a dict is NON-monotone (the default hides the drop, the DATA analog of a branch raise
    swallowed by `except BaseException`), so its sites are REFUSED.  Static + conservative: a dynamic
    access (`**merge`, `dict(d)` copy, a computed default) is invisible here and must widen if a swept
    module grows one — the ∅-baseline + the canary catch a live regression loudly.
    """
    unsafe: set = set()
    for n in ast.walk(tree):
        # <name>.get(key, DEFAULT) — two args ⇒ a default that swallows a missing key
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "get" and isinstance(n.func.value, ast.Name)
                and len(n.args) >= 2):
            unsafe.add(n.func.value.id)
        # try: … except KeyError — a handler that recovers from a dropped key
        if isinstance(n, ast.Try):
            for h in n.handlers:
                names = ([h.type] if isinstance(h.type, ast.Name)
                         else h.type.elts if isinstance(h.type, ast.Tuple) else [])
                if any(isinstance(t, ast.Name) and t.id == "KeyError" for t in names):
                    for stmt in n.body:
                        for d in ast.walk(stmt):
                            if (isinstance(d, ast.Subscript) and isinstance(d.value, ast.Name)):
                                unsafe.add(d.value.id)
    return unsafe


def _data_assigns(tree):
    """Every module-level `<NAME> = <dict/list/set/tuple literal>` as (name, literal_node).  Only a
    single Name target (a tuple-unpack / attribute / subscript target has no stable scalar qualname).
    """
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            name, v = stmt.targets[0].id, stmt.value
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value is not None:
            name, v = stmt.target.id, stmt.value
        else:
            continue
        if isinstance(v, (ast.Dict, ast.List, ast.Set, ast.Tuple)):
            yield name, v


def _data_sites(text: str) -> list:
    """Every mutable DATA site as (qualname, n, kind, key_node|None, value_node): each top-level
    key/element of a module-level dict/list/set/tuple literal, numbered #n in stable source order.  A
    dict whose EVERY read swallows a dropped key (`.get(k, DEFAULT)` / `except KeyError`, see
    _swallowing_dicts) is REFUSED — the precondition that keeps data-: MONOTONE.
    """
    out: list = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    unsafe = _swallowing_dicts(tree)
    for name, v in _data_assigns(tree):
        if name in unsafe:
            continue                                     # REFUSED — a dropped key would be swallowed
        if isinstance(v, ast.Dict):
            for i, (k, val) in enumerate(zip(v.keys, v.values)):
                if k is not None:                        # skip **spread entries (no single key)
                    out.append((name, i, "dict", k, val))
        else:                                            # List / Set / Tuple
            for i, el in enumerate(v.elts):
                out.append((name, i, type(v).__name__, None, el))
    return out


def _seg(text: str, node) -> str:
    """The exact source substring of an AST node (its lineno/col span) — used for byte-MINIMAL data
    edits: unlike ast.unparse (which reformats the WHOLE literal and would spuriously flip a
    source-grep witness), a segment splice touches only the dropped/perturbed span.
    """
    lines = text.splitlines(keepends=True)
    if node.lineno == node.end_lineno:
        return lines[node.lineno - 1][node.col_offset:node.end_col_offset]
    seg = lines[node.lineno - 1][node.col_offset:]
    seg += "".join(lines[node.lineno:node.end_lineno - 1])
    seg += lines[node.end_lineno - 1][:node.end_col_offset]
    return seg


def _splice(text: str, start_node, end_node, replacement: str) -> str:
    """Replace the source span from start_node's start to end_node's end with `replacement`."""
    lines = text.splitlines(keepends=True)
    prefix = "".join(lines[:start_node.lineno - 1]) + lines[start_node.lineno - 1][:start_node.col_offset]
    suffix = lines[end_node.end_lineno - 1][end_node.end_col_offset:] + "".join(lines[end_node.end_lineno:])
    return prefix + replacement + suffix


def _drop_data(text: str, qualname: str, n: int) -> str:
    """DROP one key/element of a module-level literal, keeping it PARSEABLE and its TYPE intact.  The
    edit is the SMALLEST that stays syntactically valid: it rebuilds ONLY the affected literal (not
    the whole module) from the surviving entries — so a source-grep witness over an UNRELATED literal
    never flips, while the guaranteed-parseable rebuild handles every comma / trailing-comma / tuple
    case (a 1-element tuple keeps its `(x,)`, an empty container is `{}`/`[]`/`set()`/`()`).  A byte-
    minimal comma-splice cannot: dropping a 2-tuple to `("x")` silently loses tuple-ness (Python reads
    a parenthesised value), which broke the sweep on resolver._ENV_KEEP_PREFIX.
    """
    for name, i, kind, k, val in _data_sites(text):
        if name == qualname and i == n:
            tree = ast.parse(text)
            lit = next(v for nm, v in _data_assigns(tree) if nm == qualname)
            if isinstance(lit, ast.Dict):
                keep = ast.Dict(keys=[kk for j, kk in enumerate(lit.keys) if j != i],
                                values=[vv for j, vv in enumerate(lit.values) if j != i])
            else:
                keep = type(lit)(elts=[e for j, e in enumerate(lit.elts) if j != i])
                if isinstance(lit, ast.Set) and not keep.elts:
                    return _splice(text, lit, lit, "set()")   # ast.unparse gives {} (a dict) — fix
            shortened = ast.unparse(ast.fix_missing_locations(keep))
            dropped = _splice(text, lit, lit, shortened)      # rebuild ONLY this literal's span
            ast.parse(dropped)                                # Ν·loud: a malformed drop raises
            return dropped
    raise KeyError(f"Ζ·mutant: 'data-:{qualname}#{n}' is not a data site in the module")


def _drop_data_multi(text: str, specs: list) -> str:
    """DROP several keys/elements at once — COMPOSITION-SAFE.  A sequential spec-by-spec drop renumbers
    a literal as it goes (dropping #2 makes #3 become #2), so a group-testing group that lists several
    indices of ONE literal would lose the later ones.  This resolves every (qualname, index) against
    the ORIGINAL text once and rebuilds each affected literal from the surviving entries in a single
    pass — the data analog of _mutate_lines taking a LIST of nodes.  A spec naming no current site is
    Ν·loud (a genuine miss), but a spec whose index is valid in the original text always applies.
    """
    by_qn: dict = {}
    for spec in specs:
        arg = spec.removeprefix("data-:")
        qn, _, n = arg.rpartition("#")
        by_qn.setdefault(qn, set()).add(int(n))
    tree = ast.parse(text)
    assigns = {nm: v for nm, v in _data_assigns(tree)}
    # rebuild in REVERSE source order so earlier splices don't invalidate later nodes' spans.
    edits = []
    for qn, drop_idx in by_qn.items():
        lit = assigns.get(qn)
        if lit is None:
            raise KeyError(f"Ζ·mutant: 'data-:{qn}' is not a data literal in the module")
        count = len(lit.keys) if isinstance(lit, ast.Dict) else len(lit.elts)
        if any(i >= count for i in drop_idx):
            raise KeyError(f"Ζ·mutant: 'data-:{qn}#{max(drop_idx)}' index out of range")
        if isinstance(lit, ast.Dict):
            keep = ast.Dict(keys=[k for j, k in enumerate(lit.keys) if j not in drop_idx],
                            values=[v for j, v in enumerate(lit.values) if j not in drop_idx])
        else:
            keep = type(lit)(elts=[e for j, e in enumerate(lit.elts) if j not in drop_idx])
        if isinstance(lit, ast.Set) and not keep.elts:
            rendered = "set()"
        else:
            rendered = ast.unparse(ast.fix_missing_locations(keep))
        edits.append((lit, rendered))
    for lit, rendered in sorted(edits, key=lambda e: e[0].lineno, reverse=True):
        text = _splice(text, lit, lit, rendered)
    ast.parse(text)                                       # Ν·loud on a malformed rebuild
    return text


def _leaf_path(entry_value, leaf) -> tuple | None:
    """The structural INDEX-PATH from an entry's value node down to `leaf` (e.g. () = the value IS the
    leaf; (0,) = first element of a tuple/list value; (0, 1) = nested).  None if leaf is not reachable
    by positional descent (a dict-valued position has no positional index — handled as no-domain).
    """
    if entry_value is leaf:
        return ()
    if isinstance(entry_value, (ast.Tuple, ast.List)):
        for i, el in enumerate(entry_value.elts):
            sub = _leaf_path(el, leaf)
            if sub is not None:
                return (i,) + sub
    return None


def _at_path(entry_value, path):
    """Follow an index-path into an entry value; None if the shape does not match (a sibling entry with
    a different structure has no value at this path).
    """
    node = entry_value
    for i in path:
        if isinstance(node, (ast.Tuple, ast.List)) and i < len(node.elts):
            node = node.elts[i]
        else:
            return None
    return node


def _domain_of(text: str, qualname: str, value_node, leaf) -> list:
    """The finite VALUE DOMAIN of a leaf's POSITION — the string values that appear at the SAME
    structural position across the literal's sibling entries.  Position-aware (not "every string in
    the literal"): for a dict of `(scope, remark)` tuples the domain of the SCOPE leaf (path (0,)) is
    the set of first-tuple-elements {full, fragment, …}, never the keys or remarks.  Empty ⇒ no finite
    same-position domain ⇒ the caller falls back to a distinct marker (grades presence, not correctness).
    """
    if not (isinstance(leaf, ast.Constant) and isinstance(leaf.value, str)):
        return []
    path = _leaf_path(value_node, leaf)
    if path is None:
        return []
    tree = ast.parse(text)
    lit = next((v for nm, v in _data_assigns(tree) if nm == qualname), None)
    if not isinstance(lit, (ast.Dict, ast.List, ast.Set, ast.Tuple)):
        return []
    values = lit.values if isinstance(lit, ast.Dict) else lit.elts
    vals = set()
    for ev in values:
        node = _at_path(ev, path)                        # the same-position leaf of each sibling entry
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            vals.add(node.value)
    return sorted(vals - {leaf.value})


def _counterfactual(text: str, qualname: str, entry_value, leaf) -> str:
    """A source-literal DIFFERENT from `leaf`: a valid-enum SAME-POSITION sibling (grades correctness)
    if the leaf's position has a finite domain, else a type-directed distinct marker (grades presence).
    `entry_value` is the whole entry value (the top of the position path); `leaf` the scalar to swap.
    """
    v = leaf.value
    if isinstance(v, str):
        dom = _domain_of(text, qualname, entry_value, leaf)
        return repr(dom[0]) if dom else repr(v + "·PAPERKIT_PERTURB")
    if isinstance(v, bool):
        return repr(not v)
    if isinstance(v, (int, float)):
        return repr(v + 1)
    if v is None:
        return repr("PAPERKIT_PERTURB")
    return '"PAPERKIT_PERTURB"'                           # bytes / other constant → a distinct marker


def _perturb_data(text: str, qualname: str, n: int) -> str:
    """PERTURB one value to a counterfactual (non-monotone — a value swap, never a drop).  Recurses
    into a nested value to the FIRST scalar leaf (so a `({route:scope}, remark)` value perturbs the
    scope), keeping the module parseable.  The swap is located via ast.get_source_segment — NOT raw
    col_offset slicing: an entry on a line with escaped/raw strings (e.g. a regex `(r"\\\\'E", "É")`)
    desyncs naive column arithmetic from the true span, so the segment API (which Python guarantees
    correct) locates the leaf's source, and the replacement is scoped to the ENTRY's segment so a
    same-text leaf elsewhere in the module is untouched (byte-minimal, like _drop_data's rebuild).
    """
    assign = _assign_of(ast.parse(text), qualname)      # the whole `<qualname> = <literal>` statement
    for name, i, kind, k, val in _data_sites(text):
        if name == qualname and i == n:
            # descend to the first scalar leaf of the value (the perturbable decision).
            leaf = val if isinstance(val, ast.Constant) else next(
                (node for node in ast.walk(val) if isinstance(node, ast.Constant)), None)
            asrc = ast.get_source_segment(text, assign) if assign is not None else None
            entry_src = ast.get_source_segment(text, val)
            leaf_src = None if leaf is None else ast.get_source_segment(text, leaf)
            # OFFSET-FREE: locate + rewrite via ast.get_source_segment (Python-correct on escaped/raw-
            # string lines where col_offset slicing desyncs), scoped ENTRY→ASSIGNMENT→module so a
            # same-text leaf/entry elsewhere is untouched (byte-minimal, like _drop_data's rebuild).
            if asrc is None or entry_src is None:
                return _splice(text, val, val, '"PAPERKIT_PERTURB"')  # unlocatable → col_offset marker
            if leaf is None or leaf_src is None:
                # a value with NO scalar leaf (e.g. a Param(...) call) — no value to swap; mark its
                # PRESENCE (a distinct whole-value marker), offset-free via the entry segment.
                new_asrc = asrc.replace(entry_src, '"PAPERKIT_PERTURB"', 1)
            else:
                cf = _counterfactual(text, qualname, val, leaf)
                new_entry = entry_src.replace(leaf_src, cf, 1)
                new_asrc = asrc.replace(entry_src, new_entry, 1)
            out = text.replace(asrc, new_asrc, 1)
            ast.parse(out)                               # Ν·loud on a malformed perturb
            return out
    raise KeyError(f"Ζ·mutant: 'dflip:{qualname}#{n}' is not a data site in the module")


def _assign_of(tree, qualname):
    """The module-level `Assign` node whose target is `qualname` (the statement a data literal lives in)."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == qualname for t in node.targets):
            return node
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == qualname:
            return node
    return None


def _mutate_lines(text: str, nodes: list) -> str:
    """Replace each given def's body line-span with an UNCATCHABLE raise, leaving the rest of the file
    byte-identical (so a source-grep witness flips only when ITS grepped text lived in a mutated body,
    not because the file was reformatted).  BaseException — not Exception — so a witness's own
    `except Exception` cannot swallow the mutation (MONOTONE BY CONSTRUCTION).  Takes a LIST of nodes:
    grader.py's in-process group-testing mutates several def-sites at once.

    NESTED nodes are collapsed: when an OUTER def/arm span CONTAINS an inner one (a def and its own
    closure/branch, both in the group), replacing the outer body already removes the inner, and
    replacing BOTH would slice a line list a prior replacement already shortened — corrupting content
    below (the data atom exposed this: it silently overwrote a module-level literal far downstream).
    So drop any node whose span is contained in another's, then replace the survivors bottom-up.
    """
    spans = [(n.body[0].lineno, n.end_lineno, n.body[0].col_offset) for n in nodes]
    outer = [(s, e, c) for i, (s, e, c) in enumerate(spans)
             if not any(j != i and os <= s and e <= oe and (os, oe) != (s, e)
                        for j, (os, oe, _oc) in enumerate(spans))]
    lines = text.splitlines(keepends=True)
    for s, e, col in sorted(outer, key=lambda x: x[0], reverse=True):
        lines[s - 1:e] = [" " * col + "raise BaseException('PAPERKIT_MUT')\n"]
    return "".join(lines)


def _drop_def(text: str, qualname: str) -> str:
    """DROP one def-site's BEHAVIOUR — its body → the uncatchable raise (present → absent)."""
    for qn, node in _def_sites(text):
        if qn == qualname:
            return _mutate_lines(text, [node])
    raise KeyError(f"Ζ·mutant: '{qualname}' is not a def-site in the module")


def _drop_import(text: str, name: str) -> str:
    """Remove the top-level `import <name>` / `from <name> import …` (a PRESENT import → absent)."""
    drop = set()
    for node in ast.parse(text).body:
        if (isinstance(node, ast.Import) and any(a.name == name for a in node.names)) or (isinstance(node, ast.ImportFrom) and node.module == name):
            drop.update(range(node.lineno, node.end_lineno + 1))
    if not drop:
        raise KeyError(f"Ζ·mutant: '{name}' is not a top-level import in the module")
    return "".join(l for i, l in enumerate(text.splitlines(keepends=True), 1) if i not in drop)


def _inject_import(text: str, name: str) -> str:
    """INJECT `import <name>` GUARDED under `if False:` (an ABSENT import → present in the SOURCE).  A
    "module does NOT import X" assertion — whether it greps the source or walks the AST — now flips,
    because the import statement IS there.  But it is DEAD code: the peephole optimiser drops the
    `if False:` block from the .pyc, so it NEVER EXECUTES — no circular-import breakage flips OTHER
    claims spuriously (a top-level `import gate` into resolver would break resolver, an imprecise
    whole-module flip).  A PRECISE toggle of the import's TEXTUAL presence.  Placed after the module
    docstring / any `from __future__` imports (which must stay first).
    """
    after = 0                                            # line to insert after (0 = top of file)
    for node in ast.parse(text).body:
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            after = node.end_lineno                      # module docstring
        elif isinstance(node, ast.ImportFrom) and node.module == "__future__":
            after = node.end_lineno                      # __future__ imports must remain first
        else:
            break
    lines = text.splitlines(keepends=True)
    lines.insert(after, f"if False:  # PAPERKIT_MUT\n    import {name}\n")
    return "".join(lines)


def emit_mutant(text: str, spec: str) -> str:
    """The module perturbed by `spec` (see the module docstring).  The EMPTY spec is the IDENTITY (∅).
    A bare qualname (no ':') is a def-drop, for backward compatibility with def_sites.py.
    """
    if spec == "":
        return text                                      # ∅ — the identity element of the mutation set
    op, sep, arg = spec.partition(":")
    if not sep:                                          # bare qualname ⇒ def-drop (def_sites.py output)
        return _drop_def(text, spec)
    if op == "def":
        return _drop_def(text, arg)
    if op == "branch":
        return _mutate_branch(text, *_split_qn_n(arg))
    if op == "flip":
        return _flip_condition(text, *_split_qn_n(arg))
    if op == "data-":
        return _drop_data(text, *_split_qn_n(arg))
    if op == "dflip":
        return _perturb_data(text, *_split_qn_n(arg))
    if op == "import-":
        return _drop_import(text, arg)
    if op == "import+":
        return _inject_import(text, arg)
    raise KeyError(f"Ζ·mutant: unknown mutation op in spec '{spec}'")


if __name__ == "__main__":
    module, spec = sys.argv[1], sys.argv[2]
    sys.stdout.write(emit_mutant(open(module).read(), spec))
