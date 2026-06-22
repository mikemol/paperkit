#!/usr/bin/env python3
"""Render the claim DAG as adequacy-vs-dependency.

Walk the DAG left to right — a claim's x is its dependency DEPTH (the longest chain
of `from` edges reaching it), so premises with things depending on them sit left and
terminal conclusions sit right.  Its y is its Δ grade.  Edges are the entailment
links.  Pure-stdlib, deterministic SVG (integer coordinates, stable ordering).
"""
GRADE_ORDER = ["behavioral", "indeterminate", "existence", "vacuous", "broken"]
# Okabe-Ito colour-blind-safe palette (per mat260's figure doctrine); grade is also
# encoded by vertical position, so colour is never the sole channel.
COLOR = {"behavioral": "#009E73", "indeterminate": "#0072B2", "existence": "#E69F00",
         "vacuous": "#D55E00", "broken": "#000000"}
INK = "#1a1a1a"   # all text is dark-on-light


def _depths(nodes):
    depth = {}

    def d(k):
        if k in depth:
            return depth[k]
        depth[k] = 0  # cycle guard
        deps = [x for x in nodes[k].get("from", []) if x in nodes]
        depth[k] = 1 + max((d(x) for x in deps), default=-1) if deps else 0
        return depth[k]

    for k in nodes:
        d(k)
    return depth


def svg(records):
    nodes = {r["key"]: r for r in records}
    if not nodes:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>\n'
    depth = _depths(nodes)
    maxd = max(depth.values())
    bands = [g for g in GRADE_ORDER if any(r["grade"] == g for r in records)]
    L, R, T, B, BH, plotW = 132, 30, 22, 48, 60, 560
    W, H = L + plotW + R, T + B + BH * len(bands)
    band_y = {g: T + i * BH + BH // 2 for i, g in enumerate(bands)}

    def x_of(k):
        return L + (round(plotW * depth[k] / maxd) if maxd else plotW // 2)

    # nodes sharing a (depth, grade) cell are spread vertically within the band
    groups, pos = {}, {}
    for r in records:
        groups.setdefault((depth[r["key"]], r["grade"]), []).append(r["key"])
    for (_dep, g), keys in groups.items():
        for i, k in enumerate(keys):
            pos[k] = (x_of(k), round(band_y[g] + (i - (len(keys) - 1) / 2) * 13))

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'font-family="sans-serif" font-size="11">',
           f'<rect width="{W}" height="{H}" fill="white"/>']
    for g in bands:
        y = band_y[g]
        out.append(f'<line x1="{L}" y1="{y}" x2="{L + plotW}" y2="{y}" stroke="#eeeeee"/>')
        out.append(f'<circle cx="{L - 12}" cy="{y}" r="4" fill="{COLOR[g]}"/>')   # colour swatch
        out.append(f'<text x="{L - 22}" y="{y + 3}" text-anchor="end" fill="{INK}">{g}</text>')
    for r in records:                       # entailment edges (premise → claim)
        if r["key"] in pos:
            x2, y2 = pos[r["key"]]
            for dep in r.get("from", []):
                if dep in pos:
                    x1, y1 = pos[dep]
                    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                               f'stroke="#cccccc" stroke-width="0.6"/>')
    for r in records:                       # nodes
        if r["key"] in pos:
            x, y = pos[r["key"]]
            out.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{COLOR[r["grade"]]}"/>')
    out.append(f'<text x="{L + plotW // 2}" y="{H - 14}" text-anchor="middle" fill="#333">'
               f'dependency depth  (premises → conclusions)</text>')
    out.append('</svg>')
    return "\n".join(out) + "\n"
