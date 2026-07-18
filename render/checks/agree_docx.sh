#!/bin/sh
# Ρ·render·agree — producer 2 of 2 (the DELIVERED document): the plain text extracted
# from the rendered .docx.  Builds the .docx from paper.md, then reads it back out; emits
# the normalized plain text to stdout.  The agree: verb concurs this with producer 1
# (paper.md's own plain text) — presentation agreement extends prose≡projection down the
# render stack.  (cwd = render/; .. = repo root.)
set -eu
cd ..
d=$(mktemp -d)
trap 'rm -rf "$d"' EXIT
pandoc paper/paper.md -o "$d/paper.docx"
pandoc "$d/paper.docx" -t plain | sed 's/[[:space:]]*$//'
