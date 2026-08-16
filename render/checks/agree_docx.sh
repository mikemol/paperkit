#!/bin/sh
# Ρ·render·agree — producer 2 of 2 (the DELIVERED document): the plain text extracted
# from the rendered .docx.  Builds the .docx from paper.md, then reads it back out; emits
# the normalized plain text to stdout.  The agree: verb concurs this with producer 1
# (paper.md's own plain text) — presentation agreement extends prose≡projection down the
# render stack.  Math spans are replaced with a stable placeholder first (checks/prose.py),
# identically to producer 1: agree DELEGATES the equations' fidelity to the OMML check
# (rnd-omml) and concurs only the prose.  (cwd = render/; .. = repo root.)
set -eu
d=$(mktemp -d)
trap 'rm -rf "$d"' EXIT
python3 checks/prose.py < ../paper/paper.md > "$d/paper.md"
pandoc "$d/paper.md" -o "$d/paper.docx"
pandoc "$d/paper.docx" -t plain | sed 's/[[:space:]]*$//'
