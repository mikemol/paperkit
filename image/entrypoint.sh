#!/bin/sh
# The proof image's two modes from one immutable artifact:
#   (default) gate  — PROVE the paper: run the gate, exit 0 iff it verifies hermetically.
#   serve [port]    — PRESENT the paper: serve the repository over HTTP (default :8000), so
#                     the paper hosts itself — the same image that proves it also presents it.
# cwd is /work (WORKDIR); the paper's checks resolve their siblings from there.
case "${1:-gate}" in
  serve) exec python3 -m http.server "${2:-8000}" --directory /work --bind 0.0.0.0 ;;
  gate)  exec python3 paperkit/gate.py --safe --without-K paper ;;
  *)     exec "$@" ;;   # passthrough, for debugging
esac
