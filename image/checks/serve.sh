#!/bin/sh
# Κ·image·serve — the proof image PRESENTS the paper over HTTP: run it in serve mode and
# fetch the paper, asserting the served bytes ARE the committed paper.  The proof object
# serves itself.  (cwd = the image/ project; .. = repo root.)
set -eu
cd ..
podman build -q --timestamp 0 -t paperkit-proof-serve -f Containerfile . >/dev/null
port=$((8000 + $$ % 1000))
cid=$(podman run -d --rm -p "127.0.0.1:${port}:8000" paperkit-proof-serve serve)
trap 'podman rm -f "$cid" >/dev/null 2>&1 || true; podman rmi -f paperkit-proof-serve >/dev/null 2>&1 || true' EXIT
url="http://127.0.0.1:${port}/paper/paper.md"
i=0; while [ "$i" -lt 40 ]; do
  python3 -c "import urllib.request;urllib.request.urlopen('$url',timeout=1)" 2>/dev/null && break
  i=$((i+1)); sleep 0.5
done
served=$(python3 -c "import urllib.request;print(urllib.request.urlopen('$url',timeout=5).read().decode(),end='')")
[ "$served" = "$(cat paper/paper.md)" ]   # exit 0 iff the image served the actual paper
