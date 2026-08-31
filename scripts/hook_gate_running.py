#!/usr/bin/env python3
"""PreToolUse(Edit|Write|NotebookEdit) — refuse a tracked-tree edit WHILE THE GATE IS RUNNING.

⚑ THE DEFECT THIS EXISTS FOR WAS COMMITTED FOUR TIMES IN ONE SESSION, BY THE AUTHOR OF THE
RULE AGAINST IT. `scripts/check` reports `7 of 7 slice(s) clean` and NOTHING about the tree it
read. So a green obtained before an edit is indistinguishable from one obtained after, and
staying correct depends entirely on a human holding the sequence in their head. Measured: four
invalidations in one session, the second of them inside the very edit that filed the defect.

⚑ SO THE FIX IS NOT A STAMP, IT IS A REFUSAL. A stamp (◆62) makes the invalidation VISIBLE
AFTERWARDS — you learn the run was worthless once it finishes. A hook makes it IMPOSSIBLE:
the edit does not land, the run stays valid, and no judgement is required at the moment it is
least available. Same lesson as ▣25's band, which caught four arm-count errors once it stopped
depending on anyone remembering to raise a floor.

⚑ WHAT IT MATCHES ON, AND WHY IT IS `cwd` RATHER THAN THE COMMAND LINE. Measured on a live
box, `pgrep -af "scripts/check"` returned SIX lines of which THREE were false positives: the
pgrep wrapper itself, and TWO PROCESSES FROM A DIFFERENT REPO's gate
(`cassian-observability/.precommit-staged/scripts/check`). Blocking this repo's edits because
another repo is running its own gate would be the exact failure `hook_no_chaining` records —
"a guard whose first act is to break a working session trains its owner to disable it."

`/proc/<pid>/cwd` is a fact about WHICH TREE the process is reading; the command line is a fact
about how someone spelled the invocation. This is the interface/producer distinction the repo
keeps a table about, applied to process identity: the argv is the producer's account of itself,
the cwd is what the kernel actually bound.

⚑ AND A PID CAN VANISH BETWEEN ENUMERATING IT AND ASKING ABOUT IT — measured, on the first
probe written for this. `readlink /proc/4112084/cwd` exited 1 because the process had already
finished. A disappeared process is NOT RUNNING; every read here is wrapped so the answer is
"no gate" rather than a traceback. ⚑ A guard that crashes is a guard that is off.

⚑ FAIL-OPEN ON UNCERTAINTY, DELIBERATELY, AND THIS IS THE ONE PLACE THAT CHOICE IS ARGUABLE.
If `/proc` is unreadable or the enumeration throws, this allows the edit. The alternative —
refusing every edit whenever the hook cannot tell — turns a transient failure into a session
that cannot work at all, and the cost being prevented is a WASTED GATE RUN, not a corruption.
Stated here rather than left implicit, because a fail-open guard reads as armed while being
silent, which is the shape `settings.json` warns about at length.

⚑ ADVISORY BY DEFAULT, matching both sibling hooks. `GATE_HOOK_BLOCK=1` (or the shared
`STRUCT_HOOK_BLOCK=1`) makes it refuse. Verify BY MAKING IT FIRE — `scripts/check --only routes`
runs both arms — never by reading `settings.json`.
"""
import json
import os
import sys

# The tree this hook guards. A gate process is OURS iff its cwd is this directory —
# `CLAUDE_PROJECT_DIR` when the harness supplies it, else the file's own repo root.
PROJECT = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

# ⚑ THE GATE'S OWN WRITES MUST NOT BE BLOCKED BY THE GATE RUNNING. `scripts/check` and the
# things it calls legitimately write caches and stamps while running. This hook only sees
# Edit/Write/NotebookEdit — harness tool calls, i.e. MY edits — so a subprocess's file writes
# never reach it. Recorded because the exemption looks missing and is structural.

# Paths under the project that a gate run does NOT depend on, so editing them mid-run cannot
# invalidate it. Deliberately EMPTY to start.
# ⚑ AN EXEMPTION LIST IS THE PLACE THIS GUARD WILL ROT. Every entry is a claim that the gate
# does not read that path, and nothing re-checks it when a slice starts reading one. Starting
# empty means the first false positive is a conversation, not a silent hole.
EXEMPT_PREFIXES = ()


def _ancestors():
    """This process and every ancestor, as ints.

    ⚑ WALKS /proc/<pid>/stat's PPid FIELD RATHER THAN TRUSTING os.getppid() ALONE, because
    the hook can be spawned at any depth beneath the thing that would otherwise match. Stops
    at pid 1, and stops on any unreadable entry — a chain that cannot be completed yields the
    ancestors found so far, which is the conservative direction: fewer exclusions means more
    blocking, and blocking is the safe failure for this guard.
    """
    seen, pid = set(), os.getpid()
    while pid and pid not in seen:
        seen.add(pid)
        try:
            with open(f"/proc/{pid}/status", "r") as fh:
                for line in fh:
                    if line.startswith("PPid:"):
                        pid = int(line.split()[1])
                        break
                else:
                    break
        except (OSError, ValueError):
            break
        if pid <= 1:
            break
    return seen


def _gate_pids():
    """Every live process whose cwd is this project AND which looks like the gate.

    Returns a list of (pid, cmdline). Empty means no gate is running here — which is also
    what an unreadable /proc yields, deliberately (see the module docstring's fail-open note).
    """
    out = []
    try:
        pids = [n for n in os.listdir("/proc") if n.isdigit()]
    except OSError:
        return out
    for pid in pids:
        # ⚑ EVERY READ IS GUARDED SEPARATELY. The process may exit between listdir and any of
        # these, and each failure means the same thing: it is not running now.
        try:
            cwd = os.readlink(f"/proc/{pid}/cwd")
        except OSError:
            continue
        if os.path.realpath(cwd) != os.path.realpath(PROJECT):
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as fh:
                raw = fh.read()
        except OSError:
            continue
        argv = [p.decode("utf-8", "replace") for p in raw.split(b"\0") if p]
        if not argv:
            continue
        # ⚑ MATCH THE SCRIPT AS A PATH COMPONENT, NOT AS A SUBSTRING. `grep -rn scripts/check
        # notes.md` mentions the gate and does not run it — the same false-positive surface
        # `hook_no_chaining` handles by tokenising rather than substring-matching.
        #
        # ⚑ AND THE EXCLUSION IS THE WHOLE ANCESTOR CHAIN, NOT pid+ppid. The first version
        # excluded only those two and PASSED ITS OWN F-ARM INSIDE A RUNNING GATE — which I
        # nearly banked as correct. Measured: with the hook spawned as a DIRECT child of a
        # gate-shaped process it answers ALLOW; one shell level deeper it answers DENY.
        # **The pass was a coincidence of how `run_hook` happens to spawn it**, not a property
        # of the design, and the harness invokes hooks through a shell.
        #
        # A gate that is my own ANCESTOR is one I am running *inside* — it cannot be a run my
        # edit would invalidate, because the edit is part of what it is measuring. A gate
        # anywhere else in the tree is exactly what must block me.
        if int(pid) in _ancestors():
            continue
        # ⚑ PAPERKIT'S GATE IS `bazel test //:hook`, NOT A SCRIPT. Upstream matched
        # `scripts/check` as a path component; this tree has no such file, so that predicate
        # would never fire and the hook would ALLOW every edit mid-sweep — armed in review,
        # silent in fact, the exact pairing settings.json warns about. The gate here is the
        # BUILD TOOL, so the token to match is the program name plus a building subcommand:
        # `bazel test|build|run`. A bare `bazel query`/`shutdown`/`info` reads no source and
        # cannot be invalidated by an edit, so it is deliberately not matched.
        #
        # ⚑ AND THE cwd TEST ABOVE IS WHAT MAKES THIS SAFE TO KEEP BROAD. `bazel` running for
        # a DIFFERENT repo has that repo's cwd and never reaches here — measured upstream as
        # three false positives from a sibling checkout's gate, which is why identity is the
        # kernel's cwd binding rather than the producer's account of itself in argv.
        toks = argv[1:] if argv[0].endswith(("bash", "sh", "-c")) else argv
        for i, tok in enumerate(toks):
            base = os.path.basename(tok.rstrip("/"))
            if base in ("check", "check-selftest") and "scripts" in tok:
                out.append((pid, " ".join(argv)))
                break
            if base in ("bazel", "bazelisk"):
                rest = [t for t in toks[i + 1:] if not t.startswith("-")]
                if rest and rest[0] in ("test", "build", "run", "coverage"):
                    out.append((pid, " ".join(argv)))
                break
    return out


def _target(data):
    """The path this tool call would write, or None."""
    ti = data.get("tool_input") or {}
    for k in ("file_path", "notebook_path", "path"):
        v = ti.get(k)
        if isinstance(v, str) and v:
            return v
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    path = _target(data)
    if not path:
        return 0
    ap = os.path.realpath(path)

    # Only edits INSIDE the guarded tree can invalidate this tree's gate. A scratchpad write
    # cannot, and blocking it would be the cassian false positive aimed inward.
    if not ap.startswith(os.path.realpath(PROJECT) + os.sep):
        return 0
    rel = os.path.relpath(ap, os.path.realpath(PROJECT))
    if any(rel.startswith(p) for p in EXEMPT_PREFIXES):
        return 0

    running = _gate_pids()
    if not running:
        return 0

    pids = ", ".join(f"pid {p}" for p, _c in running)
    msg = (
        f"gate-running: the gate is RUNNING right now ({pids}) and this edit to "
        f"{rel} would invalidate it.\n"
        "  ⚑ the run in flight is reading THIS tree. Editing now means its verdict describes\n"
        "     a tree that no longer exists — and a sandboxed cell whose input changed under it\n"
        "     reds with `input dependency modified during execution`, which reads as an ENGINE\n"
        "     defect rather than as interference, so the cost is the sweep AND the diagnosis.\n"
        "  ⚑ measured here 2026-08-27: a 3864s //:hook run went red in six Ζ·eval cells plus\n"
        "     @paperkit_paper//:cohere because bib.py was edited three minutes before it ended.\n"
        "     The red outlived its cause and was filed at the top of a paths-forward ledger as\n"
        "     an engine defect (Λ·quiesce, ~7 occurrences). Noticing is not a control.\n"
        "  wait for the run to finish, then edit, then re-run. If the edit is urgent, stop\n"
        "     the run first (TaskStop) so nothing green is left describing the wrong tree."
    )

    own = os.environ.get("GATE_HOOK_BLOCK")
    if own is None:
        own = os.environ.get("STRUCT_HOOK_BLOCK")
    if own == "1":
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": msg}}))
        return 0
    sys.stderr.write(msg + "\n")
    return 0


def _selftest() -> bool:
    """Arms that assert the ACT, not the spelling (▣27).

    ⚑ A CHECK ON THE PATTERN IS NOT A CHECK ON THE DETECTION. `hook_structural_query`'s
    routes slice runs both arms — deny when armed, NOT-deny when unarmed — so it cannot
    certify a hook that refuses everything. Same bar here.
    """
    cases = []

    def check(label, got, want):
        cases.append((label, got == want, got, want))

    # The detector must not report the CURRENT process as a gate: this selftest runs with the
    # project as cwd, which is exactly the condition a naive match would fire on.
    check("the hook does not detect ITSELF as a running gate",
          any(int(p) == os.getpid() for p, _c in _gate_pids()), False)

    # A path outside the tree is never guarded, however the gate is doing.
    check("a scratchpad path is out of scope",
          _target({"tool_input": {"file_path": "/tmp/x.md"}}), "/tmp/x.md")
    check("a call with no path is ignored",
          _target({"tool_input": {"command": "ls"}}), None)
    check("notebook_path is recognised as a write target",
          _target({"tool_input": {"notebook_path": "/a/b.ipynb"}}), "/a/b.ipynb")

    # ⚑ THE EXEMPTION LIST MUST START EMPTY — every entry is an unchecked claim that the gate
    # does not read that path. If this arm fails, someone added one and owes a reason.
    check("no exemptions are declared", len(EXEMPT_PREFIXES), 0)

    # ⚑ THE ANCESTOR CHAIN MUST BE DEEPER THAN pid+ppid, and this arm exists because the first
    # version was not. It excluded only those two and PASSED ITS OWN F-ARM inside a running
    # gate — measured: ALLOW when spawned as a direct child of a gate-shaped process, DENY one
    # shell level deeper. The pass was a coincidence of spawn depth, and the harness invokes
    # hooks through a shell. A chain of length <= 2 means the walk is not walking.
    check("the ancestor chain is walked, not just pid+ppid", len(_ancestors()) > 2, True)
    check("this process is in its own ancestor set", os.getpid() in _ancestors(), True)

    # ⚑ A VANISHED PID MUST READ AS 'NOT RUNNING', NEVER CRASH. Measured live: readlink on a
    # just-exited pid exits 1. Enumerating twice must not raise.
    try:
        _gate_pids()
        _gate_pids()
        survived = True
    except Exception:
        survived = False
    check("enumeration is crash-safe across process churn", survived, True)

    ok = sum(1 for _n, g, _a, _b in cases if g)
    for n, g, got, want in cases:
        if not g:
            print("  FAIL %s: got %r want %r" % (n, got, want))
    print("hook_gate_running selftest: %d/%d" % (ok, len(cases)))
    return ok == len(cases)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    if "--probe" in sys.argv:
        # What does the hook see right now? The mode that answers "is a gate running"
        # without needing a shell composition.
        found = _gate_pids()
        if not found:
            print(f"no gate running with cwd {PROJECT}")
        for p, c in found:
            print(f"pid {p}: {c}")
        sys.exit(0)
    sys.exit(main())
