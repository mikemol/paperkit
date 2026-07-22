# The Paperkit Guide

*Every sentence below is certified by a concept the library authored and GRADED once --- this view adds NO witness code; it imports certificates and runs the gate on its own starter.*

## The Model: Claims, Not Prose

A document is built from claims, not prose — each claim is a single bibliography entry: a statement, the section it belongs to, the claims it depends on, and its check [@g-model], and each claim carries a machine-checkable verifier the gate actually runs [@g-verifier].

## The Gate: Nothing Unverified Ships

An unverified sentence does not ship — a claim whose check fails blocks the gate, so the document cannot overclaim [@g-noship]. The gate enforces its invariants mechanically: the committed prose equals its projection, and every cited claim's check passes [@g-invariants].

## Extending: Your Domain, Your Verifiers

Cmd is the universal escape hatch every check reduces to, and a new domain adds named check types in its own config without touching the engine [@g-extend].

## Adequacy: How Hard Can a Check Fail

Beyond pass/fail, the mutation sweep grades how much each check can actually fail — a presupposed file grades vacuous, a content-sensitive command behavioral — so a green gate also says how hard its greens are to fake [@g-adequacy].

## A Copyable Starter

A complete project is a paper.toml, a warrants bibliography, and a rubric — the starter below is not pseudocode, it gates green exactly as shown (this claim's check RUNS paperkit's gate on it) [@g-starter]. Its paper.toml declares the document [@g-starter-toml].

```toml
[paper]
title = "A Note"
warrants = ["warrants.bib"]
rubric = "rubric.tsv"
out = "note.md"
```

Its warrants bibliography is the document's one claim [@g-starter-bib].

```bibtex
@misc{ships-verified,
  section = {note},
  claim   = {every sentence in this note is the projection of a claim a check verified},
  check   = {cmd:true}
}
```
