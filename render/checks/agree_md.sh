#!/bin/sh
# Ρ·render·agree — producer 1 of 2 (the SOURCE): the plain text of paper.md itself.
# Emits the normalized plain text to stdout; the agree: verb concurs it byte-for-byte
# with producer 2 (the round-tripped .docx), so agreement across two INDEPENDENT render
# paths rules out a shared bug either path alone could hide.  Math spans are replaced with
# a stable placeholder first (checks/prose.py): agree owns PROSE fidelity and DELEGATES the
# equations' fidelity to the OMML check (rnd-omml), rather than compare two math flatteners.
# (cwd = render/; .. = repo root.)
set -eu
python3 checks/prose.py < ../paper/paper.md | pandoc -f markdown -t plain | sed 's/[[:space:]]*$//'
