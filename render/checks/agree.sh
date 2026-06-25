#!/bin/sh
# Ρ·render·agree — PRESENTATION AGREEMENT: the plain text extracted from the rendered .docx
# is byte-for-byte the plain text of paper.md, so the document presents the verified paper
# with nothing dropped or corrupted.  (cwd = render/; .. = repo root.)
set -eu
cd ..
d=$(mktemp -d)
trap 'rm -rf "$d"' EXIT
pandoc paper/paper.md -o "$d/paper.docx"
pandoc paper/paper.md    -t plain | sed 's/[[:space:]]*$//' > "$d/md.txt"
pandoc "$d/paper.docx"   -t plain | sed 's/[[:space:]]*$//' > "$d/docx.txt"
diff -q "$d/md.txt" "$d/docx.txt" >/dev/null   # exit 0 iff the docx says exactly what the paper says
