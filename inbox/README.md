This directory has two roles, deliberately kept separate.

**The drop-zone (`inbox/`, ignored).** A place for other sessions — or other people —
to drop findings and bug reports without interfering with the ongoing session's live
git state. Everything dropped here is `.gitignore`d, so an incoming file never dirties
the working tree. This is the default; nothing here is tracked except this README and
the archive below.

**The archive (`inbox/archive/`, tracked).** Settled correspondence, promoted here by a
deliberate human act once an exchange is finished and worth keeping. Promotion is the
gate: a person judging the exchange settled and load-bearing. These files are primary
sources — they "resolve by being defined," the same standing as a `references.bib`
entry with no `check`. A finding worth citing in a projected document is distilled into
a bib reference and the prose (see `@cassian-fresh` in `paper/references.bib`); the raw
letters remain here as the evidence behind that distillation.
