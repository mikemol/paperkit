#!/bin/sh
# Ρ·render·emit — render the paper to a valid .docx via pandoc, and confirm it is a well-
# formed OOXML package that pandoc can read back.  (cwd = render/; .. = repo root.)
set -eu
cd ..
d=$(mktemp -d)
trap 'rm -rf "$d"' EXIT
pandoc paper/paper.md -o "$d/paper.docx"
unzip -l "$d/paper.docx" | grep -q "word/document.xml"   # a real docx package
pandoc "$d/paper.docx" -t plain >/dev/null                # round-trips: pandoc can read it back
