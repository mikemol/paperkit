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
    line with the body, so a line-span replacement can't isolate the body — it is skipped."""
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
    must widen (the branch: canary + the ∅-baseline/pk_canary guards catch a live regression loudly)."""
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
    isolate the body span), mirroring _def_sites."""
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
    bar lives at the consumer, not here)."""
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
    primitive as def:, so branch: IS a raise-kind site)."""
    for qn, i, (b0, blast) in _branch_sites(text):
        if qn == qualname and i == n:
            lines = text.splitlines(keepends=True)
            col = b0.col_offset
            lines[b0.lineno - 1:blast.end_lineno] = [" " * col + "raise BaseException('PAPERKIT_MUT')\n"]
            return "".join(lines)
    raise KeyError(f"Ζ·mutant: 'branch:{qualname}#{n}' is not a branch-arm site in the module")


def _flip_condition(text: str, qualname: str, n: int) -> str:
    """INVERT one condition — `if C:` → `if not (C):` — via a span rewrite of the test source.  Never
    routed through _mutate_lines (a value-swap is not a raise; it is NON-monotone by design)."""
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


def _mutate_lines(text: str, nodes: list) -> str:
    """Replace each given def's body line-span with an UNCATCHABLE raise, leaving the rest of the file
    byte-identical (so a source-grep witness flips only when ITS grepped text lived in a mutated body,
    not because the file was reformatted).  BaseException — not Exception — so a witness's own
    `except Exception` cannot swallow the mutation (MONOTONE BY CONSTRUCTION).  Takes a LIST of nodes:
    grader.py's in-process group-testing mutates several def-sites at once."""
    lines = text.splitlines(keepends=True)
    for node in sorted(nodes, key=lambda n: n.body[0].lineno, reverse=True):
        s, e, col = node.body[0].lineno, node.end_lineno, node.body[0].col_offset
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
        if isinstance(node, ast.Import) and any(a.name == name for a in node.names):
            drop.update(range(node.lineno, node.end_lineno + 1))
        elif isinstance(node, ast.ImportFrom) and node.module == name:
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
    docstring / any `from __future__` imports (which must stay first)."""
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
    A bare qualname (no ':') is a def-drop, for backward compatibility with def_sites.py."""
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
    if op == "import-":
        return _drop_import(text, arg)
    if op == "import+":
        return _inject_import(text, arg)
    raise KeyError(f"Ζ·mutant: unknown mutation op in spec '{spec}'")


if __name__ == "__main__":
    module, spec = sys.argv[1], sys.argv[2]
    sys.stdout.write(emit_mutant(open(module).read(), spec))
