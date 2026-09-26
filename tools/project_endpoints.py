r"""Ζ·luthen·remote — project the remote endpoints INTO .bazelrc from the host's directory.

.bazelrc carries four flag lines whose VALUE is a network address the host owns, not paperkit:
`--remote_cache`, `--bes_backend`, `--remote_executor` (one gRPC endpoint) and
`--bes_results_url` (the web UI).  A copied address rots — the loopback NodePort they carried
died BY DESIGN on 2026-09-20 and every `--config=remote` run on luthen then failed to reach the
executor that grants the run its integrity.  So the addresses are not AUTHORED here; they are
QUERIED from luthen-observability's endpoint directory at the moment of use and written IN PLACE:

    python3 tools/project_endpoints.py            # rewrite the four values
    python3 tools/project_endpoints.py --check    # exit 3 if .bazelrc disagrees with the directory
    python3 tools/project_endpoints.py --get <name> [<path suffix>]   # print one address (W44)

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
from typing import cast

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
USAGE = "usage: project_endpoints.py [--check] | --get <name> [<path suffix>]\n"
GET_ARGS = (2, 3)            # `--get <name>` and `--get <name> <suffix>`
GET_WITH_SUFFIX = 3


def query(name: str) -> str:
    """Ask the directory for `name` on the host side; refuse anything but an answer."""
    r = subprocess.run([sys.executable, str(DIRECTORY), name, "--side", "host"],  # noqa: S603
                       capture_output=True, text=True, check=False)
    # ⚑ NARROWED AT THE EDGE: json.loads is Any, so it lands DIRECTLY in an annotated `object` —
    # the one form mypy's disallow_any_expr permits (inside a conditional expression it is still
    # flagged) — and is checked before anything reads it.
    raw: object = json.loads(r.stdout.strip() or '{"state": "no-output"}')
    rec = cast("dict[str, object]", raw) if isinstance(raw, dict) else {"state": "not-a-record"}
    address = rec.get("address")
    if rec.get("state") != "answered" or not isinstance(address, str):
        msg = f"endpoint directory did not answer for {name}: {rec} {r.stderr.strip()}"
        raise SystemExit(msg)
    return address


def project(text: str) -> tuple[str, list[str]]:
    """Return (new text, list of changed flags).  Refuse on a missing or duplicated flag line."""
    out = text
    changed: list[str] = []
    for flag, (name, scheme, suffix) in FLAGS.items():
        pat = re.compile(rf"^(build:\w+ {re.escape(flag)}=){scheme}[^\s#]+", re.MULTILINE)
        hits = sum(1 for _ in pat.finditer(out))
        if hits != 1:
            msg = f"{flag}: expected exactly one line in .bazelrc, found {hits} — refusing"
            raise SystemExit(msg)
        want = f"\\g<1>{scheme}{query(name)}{suffix}"
        new = pat.sub(want, out)
        if new != out:
            changed.append(flag)
        out = new
    return out, changed


def main(argv: list[str]) -> int:
    """Project the endpoints into .bazelrc, check them, or print one address by service name.

    ⚑ W44 — AN UNKNOWN FLAG IS A REFUSAL, NOT A WRITE.  Every argument this did not recognise fell
    through to the projection, so `--help` REWROTE .bazelrc (it changed nothing only because the
    file happened to be current) — the help-flag-wrote-a-file class this repo already records.

    `--get <name> [<suffix>]` is the READ-ONLY face the pre-commit hook uses to find its telemetry
    sinks by service NAME (vmagent-http, victorialogs-http) instead of reading addresses copied into
    a per-clone file, where they went dead with the host move.
    """
    if argv and argv[0] == "--get":
        if len(argv) not in GET_ARGS:
            sys.stderr.write(USAGE)
            return 2
        suffix = argv[2] if len(argv) == GET_WITH_SUFFIX else ""
        sys.stdout.write(f"http://{query(argv[1])}{suffix}\n")
        return 0
    unknown = [a for a in argv if a != "--check"]
    if unknown:
        sys.stderr.write(f"project_endpoints.py: unknown argument(s) {unknown} — refusing rather "
                         "than rewriting .bazelrc.\n" + USAGE)
        return 2
    text = BAZELRC.read_text()
    new, changed = project(text)
    if "--check" in argv:
        for f in changed:
            sys.stdout.write(f"stale: {f}\n")
        return 3 if changed else 0
    if changed:
        BAZELRC.write_text(new)
    sys.stdout.write(f"projected {len(changed)} of {len(FLAGS)}: "
                     f"{', '.join(changed) or 'already current'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
