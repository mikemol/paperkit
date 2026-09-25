r"""Ζ·luthen·remote — project the remote endpoints INTO .bazelrc from the host's directory.

.bazelrc carries four flag lines whose VALUE is a network address the host owns, not paperkit:
`--remote_cache`, `--bes_backend`, `--remote_executor` (one gRPC endpoint) and
`--bes_results_url` (the web UI).  A copied address rots — the loopback NodePort they carried
died BY DESIGN on 2026-09-20 and every `--config=remote` run on luthen then failed to reach the
executor that grants the run its integrity.  So the addresses are not AUTHORED here; they are
QUERIED from luthen-observability's endpoint directory at the moment of use and written IN PLACE:

    python3 tools/project_endpoints.py            # rewrite the four values
    python3 tools/project_endpoints.py --check    # exit 3 if .bazelrc disagrees with the directory

REPLACE, NEVER ADD.  A flag line that is missing, or present more than once, is a refusal — this
tool edits values it can NAME, it does not grow the file (the `[cas] expanded more than once`
warning is what a duplicated line looks like from bazel's side).  The directory query is by
service NAME, resolved through the host's dns-delegate; the result carries `as_of`, which is the
only timestamp that means anything about an address.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAZELRC = ROOT / ".bazelrc"
DIRECTORY = Path("/home/mikemol/github/luthen-observability/checks/endpoints_query.py")

# flag → (directory port name, scheme, path suffix).  The shape of each value is paperkit's; the
# host:port inside it is the directory's.
FLAGS = {
    "--remote_cache": ("grpc-bes", "grpc://", ""),
    "--bes_backend": ("grpc-bes", "grpc://", ""),
    "--remote_executor": ("grpc-bes", "grpc://", ""),
    "--bes_results_url": ("http-web", "http://", "/invocation/"),
}


def query(name: str) -> str:
    """Ask the directory for `name` on the host side; refuse anything but an answer."""
    r = subprocess.run([sys.executable, str(DIRECTORY), name, "--side", "host"],  # noqa: S603
                       capture_output=True, text=True, check=False)
    rec = json.loads(r.stdout) if r.stdout.strip() else {"state": "no-output"}
    if rec.get("state") != "answered":
        raise SystemExit(f"endpoint directory did not answer for {name}: {rec} {r.stderr.strip()}")
    return rec["address"]


def project(text: str) -> tuple[str, list[str]]:
    """Return (new text, list of changed flags).  Refuse on a missing or duplicated flag line."""
    out = text
    changed: list[str] = []
    for flag, (name, scheme, suffix) in FLAGS.items():
        pat = re.compile(rf"^(build:\w+ {re.escape(flag)}=){scheme}[^\s#]+", re.M)
        hits = pat.findall(out)
        if len(hits) != 1:
            raise SystemExit(f"{flag}: expected exactly one line in .bazelrc, found {len(hits)} — refusing")
        want = f"\\g<1>{scheme}{query(name)}{suffix}"
        new = pat.sub(want, out)
        if new != out:
            changed.append(flag)
        out = new
    return out, changed


def main(argv: list[str]) -> int:
    text = BAZELRC.read_text()
    new, changed = project(text)
    if "--check" in argv:
        for f in changed:
            print(f"stale: {f}")
        return 3 if changed else 0
    if changed:
        BAZELRC.write_text(new)
    print(f"projected {len(changed)} of {len(FLAGS)}: {', '.join(changed) or 'already current'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
