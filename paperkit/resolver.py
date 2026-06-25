#!/usr/bin/env python3
"""The check RESOLVER — paperkit's check-resolution core, factored out of the gate so it
can be imported and tested with a SMALL blast radius (no projector, no parallel gate loop,
no config/CLI).  A verifier is named `type:target`; this module is the registry that
dispatches it, one branch per VERB:

    file:<path>       EXISTS  — the artifact is present (no subprocess)
    cmd:<script>      EXECS   — the script exits 0 (the universal escape hatch)
    result:<project>  PARSES  — a sibling project's machine-readable gate verdict parses green
    agree:<p>|||<q>   CONCURS — N independent producers all exit 0 and emit identical output
    <custom>:<target> EXECS   — a config-declared cmd template (domain types add here)

It also sanitizes the environment a check runs in (clean_env, sshd-style default-deny) and
traces a check's READ footprint (footprint, Φ — the files it opens, the sound key to cache a
grade on).  Deps: only the stdlib + the membudget script + gate.py-as-a-subprocess (for
result:), never the rest of the engine.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import config

_MB_SCRIPT = Path(__file__).resolve().parent / "membudget"
_GATE = Path(__file__).resolve().parent / "gate.py"   # invoked as a subprocess for result:
_MB_OK = None


def membudget_ok() -> bool:
    """Is the memory-budget semaphore usable here?  Cached.  Inside an existing
    membudget scope (MEMBUDGET_PARENT set) it is by construction — that is the
    recursion point: a nested gate re-invokes membudget so its checks SUBALLOCATE
    from the parent's lease rather than the global pool.  At top level, probe that
    a user systemd scope opens; set PAPERKIT_NO_MEMBUDGET to force the plain path."""
    global _MB_OK
    if _MB_OK is not None:
        return _MB_OK
    if config.resolve(config.NO_MEMBUDGET) or not os.access(_MB_SCRIPT, os.X_OK):
        _MB_OK = False
    elif os.environ.get("MEMBUDGET_PARENT"):
        _MB_OK = True
    else:
        try:
            _MB_OK = subprocess.run(["systemd-run", "--user", "--scope", "--quiet", "true"],
                                    capture_output=True, timeout=15).returncode == 0
        except Exception:
            _MB_OK = False
    return _MB_OK


# A check is arbitrary code (cmd: is the universal escape hatch), so it must not run in
# whatever ambient environment the gate happened to inherit — that is both an injection
# surface (LD_PRELOAD, IFS, BASH_ENV, PYTHONPATH, …) and a reproducibility leak (the
# verdict would depend on the caller's shell).  Like sshd, we DON'T inherit: we build a
# controlled environment, default-deny, keeping only what a check (and the membudget
# semaphore + a nested gate) legitimately need.  PATH is kept so tools resolve, but its
# RELATIVE entries are dropped (Τ·path): a check runs with cwd = the project dir, so an
# empty/"." PATH component would resolve a tool to the project being gated — letting a
# document plant a tool beside itself.  Which ABSOLUTE dir resolves a tool stays the
# host's trust (the reproducibility leak above); pinning per-tool (GNU vs uutils) is further.
_ENV_KEEP = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "TERM", "TZ", "TMPDIR",
             "LANG", "LANGUAGE",
             "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"}  # membudget's systemd --user
_ENV_KEEP_PREFIX = ("LC_", "MEMBUDGET_", "PAPERKIT_")        # locale + paperkit's own knobs


def clean_env(env: dict | None = None) -> dict:
    """A sanitized environment for running a check: the controlled allow-list only, so
    no LD_PRELOAD/IFS/BASH_ENV/PYTHONPATH and the like reach the command.  PATH's relative
    and empty entries are dropped (Τ·path) — they would resolve a tool to the cwd (the
    project dir being gated), so a document could shadow a tool by planting it beside itself."""
    src = os.environ if env is None else env
    out = {k: v for k, v in src.items()
           if k in _ENV_KEEP or k.startswith(_ENV_KEEP_PREFIX)}
    if "PATH" in out:
        out["PATH"] = os.pathsep.join(p for p in out["PATH"].split(os.pathsep)
                                      if p and os.path.isabs(p))
    return out


def run_ok(cmd: str, cwd: Path, lease: int | None = None, label: str = "check") -> bool:
    try:
        e = clean_env()
        if lease:   # run under a memory lease; membudget admits it when RAM fits
            argv = [str(_MB_SCRIPT), "run", str(lease), label, "--", "sh", "-c", cmd]
            return subprocess.run(argv, cwd=cwd, env=e, capture_output=True).returncode == 0
        return subprocess.run(cmd, shell=True, cwd=cwd, env=e,
                              capture_output=True).returncode == 0
    except Exception:
        return False


def resolves(check: str, project_dir: Path, custom: dict, lease: int | None = None) -> bool:
    typ, _, target = check.partition(":")
    if typ == "file":
        return (project_dir / target).exists()        # EXISTS — no subprocess → no lease
    if typ == "result":
        # Ξ·seam — the third resolver verb: file EXISTS, cmd EXECS, result PARSES.  It
        # imports a sibling project's machine-readable gate VERDICT (gate --json) and
        # PARSES it — green iff the parsed verdict reports pass — rather than re-deriving
        # what the sibling owns and separately gates.  cwd = this project's dir, so the
        # target is the sibling's path relative to it.  Δ grades it "imported" (run once),
        # never mutation-sweeping a whole sub-gate.
        try:
            argv = [sys.executable, str(_GATE), "--json", "--safe", "--without-K", target]
            if lease:
                argv = [str(_MB_SCRIPT), "run", str(lease), check, "--", *argv]
            r = subprocess.run(argv, cwd=project_dir, env=clean_env(),
                               capture_output=True, text=True)
            return bool(json.loads(r.stdout or "{}").get("pass"))
        except Exception:
            return False
    if typ == "agree":
        # Δ·agree (Ε·agree) — the fourth verb: file EXISTS, cmd EXECS, result PARSES, agree
        # CONCURS.  The SAME fact established by N INDEPENDENT producers (split on |||) that
        # must AGREE — every one exits 0 AND emits identical output.  Where cmd: trusts one
        # implementation, agreement across independent producers rules out a shared bug a
        # single check cannot catch: stronger evidence, a distinct KIND.
        producers = [p.strip() for p in target.split("|||") if p.strip()]
        if len(producers) < 2:
            return False                              # agreement needs ≥2 independent producers
        outs = set()
        for prod in producers:
            try:
                if lease:
                    argv = [str(_MB_SCRIPT), "run", str(lease), check, "--", "sh", "-c", prod]
                    r = subprocess.run(argv, cwd=project_dir, env=clean_env(),
                                       capture_output=True, text=True)
                else:
                    r = subprocess.run(prod, shell=True, cwd=project_dir, env=clean_env(),
                                       capture_output=True, text=True)
            except Exception:
                return False
            if r.returncode != 0:
                return False                          # a producer that fails cannot concur
            outs.add(r.stdout.rstrip())
        return len(outs) == 1                         # green iff every producer agreed
    if typ == "cmd":
        cmd = target
    elif typ in custom:
        cmd = custom[typ]["cmd"].replace("{target}", target)
    else:
        return False
    return run_ok(cmd, project_dir, lease=lease, label=check)


def _check_cmd(check: str, custom: dict) -> str | None:
    """The shell command a check RUNS — or None for file:, which opens only its target.
    The single source of the command behind cmd:/custom/result:, so footprint() traces
    exactly what resolves() runs."""
    typ, _, target = check.partition(":")
    if typ == "file":
        return None
    if typ == "result":
        return f"{sys.executable} {_GATE} --json --safe --without-K {target}"
    if typ == "agree":   # trace every producer's reads — the footprint is their union
        return "; ".join(p.strip() for p in target.split("|||") if p.strip())
    if typ == "cmd":
        return target
    if typ in custom:
        return custom[typ]["cmd"].replace("{target}", target)
    return None


# strace open/openat line: open[at](… "PATH", FLAGS[, MODE]) = RC   (RC<0 ⇒ failed open)
_OPEN_RE = re.compile(
    r'open(?:at)?\((?:AT_FDCWD, )?"(?P<path>(?:[^"\\]|\\.)*)", (?P<flags>[^),]*)[^)]*\)'
    r'\s*=\s*(?P<rc>-?\d+)')


def footprint(check: str, project_dir: Path, custom: dict) -> list:
    """Φ·footprint — the READ footprint: the project-relative files this check OPENS for
    reading when it runs (traced with strace).  A SOUND basis for caching: a check is a
    pure function of its inputs, so if a diff touches none of these the verdict cannot
    change.  Distinct from the SENSITIVITY footprint (Δ's `tests` = files a single
    mutation flips) — a negative-assertion check reads inputs no corruption flips, so
    reads ⊇ sensitivity, and only reads is safe to cache on.  Best-effort: needs strace,
    and resolves openat with AT_FDCWD or absolute paths."""
    project_dir = Path(project_dir).resolve()
    typ, _, target = check.partition(":")
    if typ == "file":
        return [target] if (project_dir / target).exists() else []   # opens only its target
    cmd = _check_cmd(check, custom)
    if cmd is None:
        return []
    with tempfile.NamedTemporaryFile("w+", suffix=".strace", delete=False) as tf:
        trace = Path(tf.name)
    try:
        subprocess.run(["strace", "-f", "-qq", "-e", "trace=openat,open", "-o", str(trace),
                        "sh", "-c", cmd], cwd=project_dir, env=clean_env(), capture_output=True)
        reads = set()
        for line in trace.read_text(errors="replace").splitlines():
            m = _OPEN_RE.search(line)
            if not m or m.group("rc").startswith("-"):
                continue                                  # unparsed line or failed open
            if "O_WRONLY" in m.group("flags"):
                continue                                  # write-only = output, not an input
            raw = m.group("path")
            p = (Path(raw) if raw.startswith("/") else project_dir / raw).resolve()
            if not p.is_file():
                continue                                  # directories (O_DIRECTORY), /dev nodes, gone — not a hashable input
            try:
                reads.add(str(p.relative_to(project_dir)))
            except ValueError:
                continue                                  # outside the project — not a cacheable input
        return sorted(reads)
    finally:
        trace.unlink(missing_ok=True)
