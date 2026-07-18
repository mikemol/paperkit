#!/bin/sh
# Ρ·render·agree — producer 1 of 2 (the SOURCE): the plain text of paper.md itself.
# Emits the normalized plain text to stdout; the agree: verb concurs it byte-for-byte
# with producer 2 (the round-tripped .docx), so agreement across two INDEPENDENT render
# paths rules out a shared bug either path alone could hide.  (cwd = render/; .. = repo root.)
set -eu
cd ..
pandoc paper/paper.md -t plain | sed 's/[[:space:]]*$//'
