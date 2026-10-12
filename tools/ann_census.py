"""Census the untyped function arguments (ruff ANN001) by what could infer their type (W337).

Nothing is changed.  Each parameter that carries no annotation is classified by the one thing a
codemod could read locally -- its default value -- so the card can say how many of the debt are
inferable at all before anyone designs a rewriter:

    scalar     the default is an int/float/str/bytes/bool literal, which fixes the type
    none       the default is None (the type is "something or None": not inferable here)
    expr       the default is some other expression
    nodefault  nothing local to read: only call sites or runtime tracing could say

The count is a REFERENCE-ARM instrument, so it must reproduce a known value: the total of the
first four classes equals ruff's ANN001 count over the same files (self/cls are excluded, as ruff
excludes them; *args and **kwargs are ANN002/ANN003 and are reported apart as `variadic`).

    python3 tools/ann_census.py FILE...      census these files
    python3 tools/ann_census.py --selftest   prove the classifier on a fixed sample
"""

from __future__ import annotations

import ast
import re
import sys
from collections import Counter
from pathlib import Path

_SCALAR = re.compile(r"""^(?:-?\d+(?:\.\d+)?|True|False|b?(?:'[^']*'|"[^"]*"))$""")
_SKIPPED = frozenset({"self", "cls"})
_KINDS = ("scalar", "none", "expr", "nodefault")
_SAMPLE = (
    'def f(a, b=1, c="x", d=None, e=g(), *rest, **extra): ...\n'
    "class K:\n"
    "    def m(self, x, y=True): ...\n"
)
_EXPECTED = {"nodefault": 2, "scalar": 3, "none": 1, "expr": 1, "variadic": 2}


def _kind(default: ast.expr | None) -> str:
    """Return the class of one untyped parameter from its default expression."""
    if default is None:
        return "nodefault"
    text = ast.unparse(default)
    if text == "None":
        return "none"
    return "scalar" if _SCALAR.match(text) else "expr"


def _untyped(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Counter[str]:
    """Count one function's untyped parameters by class."""
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    pairs = list(zip(positional, defaults, strict=True))
    pairs += list(zip(args.kwonlyargs, args.kw_defaults, strict=True))
    found: Counter[str] = Counter()
    for arg, default in pairs:
        if arg.annotation is None and arg.arg not in _SKIPPED:
            found[_kind(default)] += 1
    for variadic in (args.vararg, args.kwarg):
        if variadic is not None and variadic.annotation is None:
            found["variadic"] += 1
    return found


def census(text: str) -> Counter[str]:
    """Return the untyped-parameter classes over every function in `text`."""
    found: Counter[str] = Counter()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            found += _untyped(node)
    return found


def selftest() -> bool:
    """Prove the classifier reads a fixed sample exactly (pass) and sees a typed edit (flag)."""
    got = census(_SAMPLE)
    typed = census(_SAMPLE.replace("b=1", "b: int = 1"))
    return dict(got) == _EXPECTED and typed["scalar"] == _EXPECTED["scalar"] - 1


def main(argv: list[str] | None = None) -> int:
    """Run the census: FILE... or --selftest; anything else is a usage error (rc 2)."""
    args = sys.argv[1:] if argv is None else argv
    if args == ["--selftest"]:
        ok = selftest()
        sys.stdout.write(f"ann_census selftest: {'PASS' if ok else 'FAIL'}\n")
        return 0 if ok else 1
    if not args or any(a.startswith("-") for a in args):
        sys.stderr.write("usage: ann_census.py (--selftest | FILE...)\n")
        return 2
    total: Counter[str] = Counter()
    for name in args:
        total += census(Path(name).read_text(encoding="utf-8"))
    ann001 = sum(total[kind] for kind in _KINDS)
    for kind in (*_KINDS, "variadic"):
        sys.stdout.write(f"{kind:10} {total[kind]}\n")
    sys.stdout.write(f"ANN001 (scalar+none+expr+nodefault) {ann001} over {len(args)} file(s)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
