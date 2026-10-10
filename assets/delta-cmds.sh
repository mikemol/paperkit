#!/bin/sh
python3 -m paperkit.discriminate paper                            # report grades
python3 -m paperkit.discriminate --min-strength behavioral paper  # gate on weak checks
