r"""Ζ·toolchain·declare — the executor IMAGE digests a verdict is keyed on.

Every remote verdict is a function of the paper AND of the image it ran in, so the image's
identity must be in the action key: a rebuilt image must re-run the check, an unchanged one must
hit.  There are TWO images, one per pool (tools/pool.bzl):

    default pool   `buildbuddy-executor`  — luthen's thin image (python + strace): the SWEEP's
                                            substrate; every sandbox cell (pk_calc) runs here
    paperkit pool  `paperkit-executor`    — the render toolchain (image/executor/Containerfile);
                                            every `toolchain`-tier check runs here

⚑ MEASURED 2026-09-21, the reason the default pool is keyed too: strace was added to the default
image and `boundaries//:gate --config=mutant --config=remote` returned `113 action cache hit` —
the four read-footprint calc baselines refuted against the strace-less image were served back as
hits, because a sandbox cell's key carried nothing about the image.  A cache hit is fine when the
key is sound (operator); this key was not.

Digests are not authored here — luthen-observability declares them (images.json) and answers by
NAME through its own query, so a field change on their side breaks their query, not a parser of
mine.  Same discipline as tools/project_endpoints.py.

    python3 tools/image_digest.py paperkit-executor    # prints `sha256:…`, or `absent`
    python3 tools/image_digest.py buildbuddy-executor

`absent` is a STABLE value, not an error: on a host without the pools nothing runs remotely, so no
verdict is ever produced under it to be mis-cached.  Read by tools/toolchain_status.sh.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

DIRECTORY = Path("/home/mikemol/github/luthen-observability")
QUERY = DIRECTORY / "checks" / "images_query.py"
PYTHON = DIRECTORY / ".venv" / "bin" / "python"
IMAGES = ("paperkit-executor", "buildbuddy-executor")


def digest(image: str) -> str:
    if image not in IMAGES:
        raise SystemExit(f"image_digest: unknown image {image!r}; known: {', '.join(IMAGES)}")
    if not QUERY.is_file() or not PYTHON.is_file():
        return "absent"
    r = subprocess.run([str(PYTHON), str(QUERY), image],  # noqa: S603
                       capture_output=True, text=True, check=False)
    if r.returncode != 0 or not r.stdout.strip():
        return "absent"
    rec = json.loads(r.stdout)
    return rec["digest"] if rec.get("state") == "answered" and rec.get("digest") else "absent"


if __name__ == "__main__":
    print(digest(sys.argv[1] if len(sys.argv) > 1 else "paperkit-executor"))
