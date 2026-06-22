#!/usr/bin/env python3
"""Render the claim DAG as adequacy-vs-dependency, with grade clamping.

Walk the DAG left to right — a claim's x is its dependency DEPTH (longest `from`
chain), premises left, terminal conclusions right.  Its y is its grade.  But a
claim is no better grounded than its weakest premise, so each node is drawn at its
EFFECTIVE (clamped) grade (filled), and where that is below its self-contained
grade a drop-line rises to a hollow ghost at the self grade — the delta is the gap.
Edges are the entailment links.  Pure-stdlib, deterministic SVG.
"""
GRADE_ORDER = ["behavioral", "existence", "indeterminate", "vacuous", "broken"]
# Okabe-Ito colour-blind-safe palette (per mat260's figure doctrine); grade is also
# encoded by vertical position, so colour is never the sole channel.
COLOR = {"behavioral": "#009E73", "existence": "#E69F00", "indeterminate": "#0072B2",
         "vacuous": "#D55E00", "broken": "#000000"}
INK = "#1a1a1a"   # all text is dark-on-light


def _depths(nodes):
    depth = {}

    def d(k):
        if k in depth:
            return depth[k]
        depth[k] = 0  # cycle guard
        deps = [x for x in nodes[k].get("rests-on", []) if x in nodes]
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

    def eff(r):
        return r.get("effective_grade", r["grade"])

    used = {g for r in records for g in (r["grade"], eff(r))}
    bands = [g for g in GRADE_ORDER if g in used]
    L, R, T, B, BH, plotW = 132, 30, 34, 48, 60, 560
    W, H = L + plotW + R, T + B + BH * len(bands)
    band_y = {g: T + i * BH + BH // 2 for i, g in enumerate(bands)}

    depended = {d for r in records for d in r.get("rests-on", [])}

    def x_of(k):                                      # terminal theses are right-aligned
        d = maxd if k not in depended else depth[k]
        return L + (round(plotW * d / maxd) if maxd else plotW // 2)

    # nodes sharing an (x-column, effective-grade) cell spread vertically within the band
    groups, pos = {}, {}
    for r in records:
        groups.setdefault((x_of(r["key"]), eff(r)), []).append(r["key"])
    for (xc, g), keys in groups.items():
        for i, k in enumerate(keys):
            pos[k] = (xc, round(band_y[g] + (i - (len(keys) - 1) / 2) * 13))

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'font-family="sans-serif" font-size="11">',
           f'<rect width="{W}" height="{H}" fill="white"/>']
    for g in bands:                                   # grade bands + y labels
        y = band_y[g]
        out.append(f'<line x1="{L}" y1="{y}" x2="{L + plotW}" y2="{y}" stroke="#eeeeee"/>')
        out.append(f'<circle cx="{L - 12}" cy="{y}" r="4" fill="{COLOR[g]}"/>')
        out.append(f'<text x="{L - 22}" y="{y + 3}" text-anchor="end" fill="{INK}">{g}</text>')
    for r in records:                                 # entailment edges (premise → claim)
        if r["key"] in pos:
            x2, y2 = pos[r["key"]]
            for dep in r.get("rests-on", []):
                if dep in pos:
                    x1, y1 = pos[dep]
                    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                               f'stroke="#cccccc" stroke-width="0.6"/>')
    for r in records:                                 # clamp drop-lines + self-grade ghost
        if r.get("clamp", 0) > 0 and r["key"] in pos:
            x, ye = pos[r["key"]]
            ys = band_y[r["grade"]]
            out.append(f'<line x1="{x}" y1="{ye}" x2="{x}" y2="{ys}" stroke="#999999" '
                       f'stroke-width="0.9" stroke-dasharray="2,2"/>')
            out.append(f'<circle cx="{x}" cy="{ys}" r="3.2" fill="white" '
                       f'stroke="{COLOR[r["grade"]]}" stroke-width="1.4"/>')
    for r in records:                                 # nodes, at effective grade (filled)
        x, y = pos[r["key"]]
        out.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{COLOR[eff(r)]}"/>')
        if r["key"] not in depended:                  # terminal thesis — nothing rests on it
            out.append(f'<circle cx="{x}" cy="{y}" r="7.5" fill="none" stroke="{INK}" stroke-width="1.3"/>')
    # legend + axis label
    lx = L + 4
    out.append(f'<circle cx="{lx}" cy="{T - 16}" r="4" fill="{INK}"/>'
               f'<text x="{lx + 8}" y="{T - 12}" fill="{INK}">effective</text>')
    out.append(f'<circle cx="{lx + 74}" cy="{T - 16}" r="3.2" fill="white" stroke="{INK}" stroke-width="1.4"/>'
               f'<text x="{lx + 83}" y="{T - 12}" fill="{INK}">self (if clamped)</text>')
    out.append(f'<circle cx="{lx + 196}" cy="{T - 16}" r="6.5" fill="none" stroke="{INK}" stroke-width="1.3"/>'
               f'<circle cx="{lx + 196}" cy="{T - 16}" r="3" fill="{INK}"/>'
               f'<text x="{lx + 207}" y="{T - 12}" fill="{INK}">terminal (nothing rests on it)</text>')
    out.append(f'<text x="{L + plotW // 2}" y="{H - 14}" text-anchor="middle" fill="{INK}">'
               f'grounding depth  (foundations → theses)</text>')
    out.append('</svg>')
    return "\n".join(out) + "\n"
