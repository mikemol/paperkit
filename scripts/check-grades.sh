#!/bin/sh
# The README's Δ grade table stays fresh-by-construction: every grade it lists
# must be a grade discriminate.py actually defines (and the table must list it),
# so renaming a grade in the tool fails this check until the table is regenerated.
set -eu
for g in vacuous existence behavioral indeterminate; do
  grep -q "$g" paperkit/discriminate.py || { echo "grade '$g' absent from discriminate.py" >&2; exit 1; }
  grep -q "$g" assets/grades.md         || { echo "grade '$g' absent from README table"   >&2; exit 1; }
done
echo "check-grades: OK — README grade table ≡ discriminate.py grades"
