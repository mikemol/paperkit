#!/bin/sh
python3 -m paperkit.project paper   # claims -> paper/paper.md (the projection)
python3 -m paperkit.gate    paper   # verify: projection-stable, checks pass, coverage
