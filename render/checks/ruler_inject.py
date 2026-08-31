#!/usr/bin/env python3
r"""Ρ·render·ruler-inject — apply ruler-sequence rules to every LaTeX table BY CONSTRUCTION.

The a11y default (owner: "passing-by-construction-except-where-explicitly-excepted"): every table the
latex node renders carries ruler-sequence rules (rulerseq.py) between its data rows, encoding the
table's binary row structure in the rule PATTERN (WCAG 1.4.1, a non-colour cue) — UNLESS a table is
EXPLICITLY excepted, and an exception is a NAMED marker, never a silent absence.

Pandoc renders a markdown table as a `longtable` whose DATA rows sit between `\endlastfoot` and
`\end{longtable}`, each terminated by `\\`.  The injector walks that region and inserts
`\Rule<cycle_order(i)>` after the i-th data row (the boundary between rows i and i+1), and adds the
nicematrix custom-line definitions to the preamble.  The seam is well-delimited (the longtable
markers), so no cell parsing is needed — the boundaries are exactly the `\\`-terminated data rows.

The typed EXCEPTION: a table preceded by the marker comment `%ruler:off` (which a source author can
place, and which survives pandoc as a raw-latex comment) is left with pandoc's plain rules and
RECORDED as excepted — the deliverable says which tables opted out, it does not drop the cue
silently.  One deliberately-excepted table demonstrates the exception is real and legible.

    inject(latex_body) -> (body_with_rules, report)   # report: per-table (rows, excepted?)
    preamble_defs(max_order) -> str                    # the nicematrix \Rule<k> + \usepackage lines
    python3 checks/ruler_inject.py                     # ⟨P,F,δ⟩ over a synthetic longtable
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rulerseq

_OFF = "%ruler:off"                       # the typed exception marker (a raw-latex comment)
# A table, optionally preceded by the %ruler:off marker on its own line — the marker travels WITH the
# table so the injector sees the exception (it is placed just before \begin{longtable} in the source).
_TABLE = re.compile(r"(?:" + re.escape(_OFF) + r"[^\n]*\n\s*)?\\begin\{longtable\}.*?\\end\{longtable\}", re.S)


def _inject_one(table: str) -> tuple[str, int, bool]:
    """Rule one longtable.  Returns (rendered, n_data_rows, excepted).  Excepted iff the table
    carries the %ruler:off marker — then it is returned unchanged (pandoc's plain rules).
    """
    excepted = _OFF in table
    # the DATA region is after \endlastfoot (or \midrule…\endhead if no foot) up to \end{longtable}.
    m = re.search(r"(\\endlastfoot|\\endhead)(.*?)(\\end\{longtable\})", table, re.S)
    if not m:
        return table, 0, excepted
    head, data, tail = m.group(1), m.group(2), m.group(3)
    # data rows are the `\\`-terminated lines in the region (ignore blank/rule-only lines).
    rows = [ln for ln in data.split("\\\\") if ln.strip() and "&" in ln]
    n = len(rows)
    if excepted or n < 2:
        return table, n, excepted     # nothing to rule (0/1 rows) or opted out
    # rebuild the data region inserting \Rule<cycle_order(i)> after the i-th row (boundary i).
    out = []
    for i, row in enumerate(rows, start=0):
        out.append(row + r"\\")
        if i + 1 < n:                 # a rule at boundary i+1 (between row i and row i+1)
            out.append("\n" + rulerseq.rule(i + 1, "tex") + "\n")
    ruled = table.replace(m.group(0), head + "".join(out) + "\n" + tail)
    return ruled, n, False


def inject(latex_body: str) -> tuple[str, list[dict]]:
    """Rule every longtable in `latex_body` by construction.  Returns the body and a per-table
    report [{rows, excepted}], so a witness can gate that every table is ruled or named-excepted.
    """
    report = []

    def _sub(mt):
        ruled, n, excepted = _inject_one(mt.group(0))
        report.append({"rows": n, "excepted": excepted})
        return ruled

    return _TABLE.sub(_sub, latex_body), report


def preamble_defs(max_order: int) -> str:
    """The nicematrix package + one `\\Rule<k>` custom-line per cycle order the document's tables use.
    max_order is the largest cycle order any table reaches (derived from the widest table's row
    count), so the definitions are exactly what the document needs, uncapped.
    """
    return "\n".join([r"\usepackage{nicematrix}", rulerseq.nicematrix_defs(max_order + 1)])


def max_order_of(report: list[dict]) -> int:
    """The largest cycle order the report's ruled tables reach (for preamble_defs).  A table of n
    rows has boundaries up to order floor(log2(n-1)).
    """
    orders = [rulerseq.cycle_order(i)
              for t in report if not t["excepted"] and t["rows"] >= 2
              for i in range(1, t["rows"])]
    return max(orders) if orders else 0


def _selftest() -> int:
    ok = 0
    tbl = (r"\begin{longtable}[]{@{}cc@{}}" "\n\\toprule\\noalign{}\n"
           r"a & b \\" "\n\\midrule\\noalign{}\n\\endhead\n\\bottomrule\\noalign{}\n\\endlastfoot\n"
           r"1 & 2 \\" "\n" r"3 & 4 \\" "\n" r"5 & 6 \\" "\n" r"7 & 8 \\" "\n\\end{longtable}")
    # P: a 4-data-row table gets a rule at each of its 3 interior boundaries, orders [0,1,0].
    ruled, report = inject(tbl)
    if report != [{"rows": 4, "excepted": False}]:
        ok = 1
    got = re.findall(r"\\(Rule\w+)", ruled)                       # findall the name after the backslash
    want = [rulerseq.rule(i, "tex")[1:] for i in (1, 2, 3)]       # rule() → "\RuleXXX"; drop the backslash
    if got != want:
        ok = 1
    # F: a %ruler:off table is left unruled and RECORDED excepted (no silent drop).
    off_ruled, off_report = inject(tbl.replace(r"\begin{longtable}", _OFF + "\n" + r"\begin{longtable}"))
    if not off_report[0]["excepted"] or re.search(r"\\Rule\w+", off_ruled):
        ok = 1
    # δ: the ONE difference between ruled and excepted is the marker; same table, marker flips it.
    if "\\Rule" not in ruled or "\\Rule" in off_ruled:
        ok = 1
    # a table with <2 rows has no interior boundary → no rule, not an error.
    tiny = tbl.replace("3 & 4 \\\\\n5 & 6 \\\\\n7 & 8 \\\\\n", "")
    if re.search(r"\\Rule\w+", inject(tiny)[0]):
        ok = 1
    if ok == 0:
        print("ruler-inject: ok — every LaTeX table ruled by construction, exceptions named")
        print(f"  P: a 4-row table gets rules at boundaries 1,2,3 (orders {[rulerseq.cycle_order(i) for i in (1,2,3)]})")
        print("  F: a %ruler:off table is left unruled and RECORDED excepted (no silent drop)")
        print("  δ: the %ruler:off marker — same table, its presence flips ruled → excepted")
        return 0
    print("ruler-inject: FAIL — the by-construction injection or the exception is wrong", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
