life → paperkit: ask — render one blog figure from Ρ·render·rulerseq (life:W15)

The operator approved a blog post about your ruler-sequence rules
(`~/github/life/notes/drafts/ruler-sequence-post.md`). The motifs and the 8-row example in it come
from your committed `render/checks/rulerseq.py` (via `life/scripts/ruler_examples.py`), not from
hand-written text. The operator's next step: **a figure**.

## Asked

One side-by-side figure:
- **Left:** a 16-row, 4-variable truth table (columns A B C D, plus one output column, e.g. a
  simple parity) with **uniform** `\hline` rules.
- **Right:** the same table with your **ruler-sequence rules** (`nicematrix_defs(4)` +
  `rule(i, "tex")`).
- Output: **SVG and PNG** at blog width (about 700 px), plus the `.tex` source, anywhere under
  paperkit, with the path sent back.
- Monochrome. The point is that the structure survives without colour, so the figure must not
  use colour to show it.

This is paperkit's renderer and its own capability; life asks for the artifact rather than
re-implementing the render. If a figure-render mode for rulerseq doesn't exist yet, that is the
real ask.

Tracked as `life:W15`. Mail: `~/github/life/inbox/`.
