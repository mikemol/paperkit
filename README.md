# paperkit

**A paper is a projection of a verified claim-DAG.** Write claims, not prose. Each
claim carries a machine-checkable *verifier*; paperkit projects the claims into a
document and refuses to ship a sentence whose verifier fails. The paper cannot
overclaim, because an unverified sentence does not project.

This repository is **self-hosting**: the paper that explains paperkit
([`paper/`](paper/)) is itself a paperkit project, and every claim it makes about
the tool is checked *by the tool*.

## The model

A claim is one bibliography entry:

```bibtex
@misc{drift,
  section = {engine}, from = {projector},
  claim   = {the gate rejects any prose that has drifted from its projection},
  check   = {cmd:sh checks/drift-caught.sh}
}
```

- **`claim`** — the sentence.
- **`section`** — which rubric section it belongs to.
- **`from`** — the claims it depends on (sets prose order + connective glue).
- **`check`** — its verifier, `type:target`.

## The two commands

```sh
python3 paperkit/project.py paper      # claims -> paper/paper.md (the projection)
python3 paperkit/gate.py    paper      # verify: projection-stable, every check passes, coverage
```

The gate enforces three invariants: the committed prose **equals** its projection;
every cited claim's **check passes**; and every section is **covered** both ways.

## The check-resolver (the one extensible seam)

A verifier is `type:target`. Two types ship built in:

| type | passes when |
| --- | --- |
| `file:<path>` | the artifact exists |
| `cmd:<script>` | the script exits `0` |

`cmd:` is the universal escape hatch every check reduces to. New domains add named
types in `paper.toml` without touching the engine:

```toml
[checks.agda]
cmd = "agda --safe {target}"
[checks.pytest]
cmd = "pytest -k {target}"
```

## Layout

```text
paperkit/        the engine — project.py, gate.py (domain-free)
paper/           the self-hosting paper (the first, dogfooding instance)
  warrants.bib   its claims          rubric.tsv   its sections
  paper.toml     its config          checks/      its verifiers (paperkit on paperkit)
  paper.md       the projection (a build artifact, gated to equal the claims)
```

## Status

A working spike: the engine projects + gates, and the self-hosting paper is green.
Render-to-PDF (pandoc/docx) and a packaged CLI (`paperkit init/project/gate/build`)
are the next steps; see the paper for the design.
