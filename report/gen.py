#!/usr/bin/env python3
"""Generate the paperkit verification REPORT — capture the live pipeline outputs as
assets, then project REPORT.md from them.

The report is a paperkit project like any other: its claims describe the
verification state, and its figures are emitted assets.  Those assets are the
*actual* output of running the tools, so the report is fresh-by-construction —
`--check` regenerates and diffs, and a stale report fails its gate (the same
manifest≡generator discipline the paper uses for its figures).

    python3 report/gen.py                 # refresh assets + project REPORT.md
    python3 report/gen.py --check         # exit 1 if any committed asset is stale
    python3 report/gen.py --check delta.txt
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = HERE / "assets"


def _run(*args):
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


def gate_text():
    paper = _run("paperkit/gate.py", "--safe", "paper")
    readme = _run("paperkit/gate.py", "--safe", ".")
    return (f"$ paperkit-gate --safe paper\n{paper}\n\n"
            f"$ paperkit-gate --safe .   (the README project)\n{readme}\n")


def delta_text():
    out = _run("paperkit/discriminate.py", "paper")
    keep = [ln for ln in out.splitlines()
            if "distinct check" in ln or "summary:" in ln or "PROVABLY" in ln]
    return "$ paperkit-discriminate paper\n" + "\n".join(keep) + "\n"


def without_k_text():
    return "$ paperkit-gate --without-K paper\n" + _run("paperkit/gate.py", "--without-K", "paper") + "\n"


GENERATORS = {"gate.txt": gate_text, "delta.txt": delta_text, "without-k.txt": without_k_text}


def main(argv):
    if "--check" in argv:
        names = [a for a in argv if a in GENERATORS] or list(GENERATORS)
        stale = [n for n in names
                 if not (ASSETS / n).exists() or (ASSETS / n).read_text() != GENERATORS[n]()]
        if stale:
            print(f"report stale: {', '.join(stale)} — run python3 report/gen.py", file=sys.stderr)
            return 1
        print(f"report fresh ({', '.join(names)})")
        return 0
    ASSETS.mkdir(exist_ok=True)
    for name, gen in GENERATORS.items():
        (ASSETS / name).write_text(gen())
    subprocess.run([sys.executable, "paperkit/project.py", "report"], cwd=ROOT)
    print("report generated", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
