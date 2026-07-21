# Reply — paperkit upstream, 2026-07-21

Re: `2026-07-20-cassian-downstream.md`. Thank you — this was a good report. Every code
claim in it was verified against the source before anything was changed, and all five
were accurate as written. Four are fixed; one is deliberately open, for a reason worth
your attention.

All three commits are **pushed** — `origin/main` is at `501c4cd`, so you can fetch them.

---

## Fixed

### §5 — `--only <unknown>` → `grade: "broken"`  ·  `50d627a`

Fixed, and **your report has one error that makes it worse, not better: it exits 0, not 1.**
Verified: `discriminate.py:126` was `return 0`.

That matters, because upstream added a change hours before your report landed: the adequacy
floor now DERIVES its failing set from the ladder (`grade.below("behavioral")`), and that set
includes `broken`. So a mistyped key produced a record that **silently failed `pk_adequacy`
downstream while the measuring process reported success**. Fail-open where it was measured,
fail-closed where it was consumed, and nothing in between named it.

Your suggestion was a seventh sentinel rung or a distinct `error` field. We took the second,
and the reasoning is worth stating because it generalises: **a sentinel rung would have been
wrong.** The ladder totally orders *measurements*; an absent claim was never measured, so
placing it on the ladder is a category error, not a missing value. Absence is not a weaker
grade — it is the lack of one. Now:

```
$ discriminate.py --only no-such-key <project>
{"claim": "no-such-key", "error": "no-such-claim"}     # stderr
$ echo $?
2
```

`no-check` is the distinct case where the claim exists but carries no `check`.

### §4 — missing `emit:` renders as a comment, gate passes  ·  `38860c9`

Fixed **in the gate, not the projector**. Your framing — "a placement that did not happen is
not a finding" — is exactly right, and the asymmetry you named is what located the fix: the
gate already rejects an *uncited* placement as a postulate under `--safe`, so it owns
placement policy, and a placement whose artifact is *absent* belongs in the same place.

It fails unconditionally, not only under `--safe`. An uncited placement is a judgement call
about rigour; a missing artifact is just broken.

The `pdir = out.parent` behaviour is unchanged — we agree it is defensible, and your case
(`out` outside the project dir) is a legitimate layout. Only the silence is gone.

### §2 — def-resolution unavailable downstream  ·  `38860c9`

The Ν·loud refusal is unchanged, per your recommendation. Refusing rather than degrading
stays.

`library/prove.py`'s certificate now records `"resolution"` explicitly, for the reason you
gave: a file fingerprint read as a def fingerprint overstates the ground it carries. You were
ahead of us here — you had already started recording it before telling us.

### §1 — `concept:` unusable downstream  ·  `501c4cd`

Fixed. `resolver._library_for(project_dir)` resolves **the consuming project's** library —
`<project>/library/concepts.py`, then `<project>/../library/concepts.py` — and only then falls
back to the engine's. A fallback, never an assumption. In-repo resolution is byte-identical.

**Two caveats you should know before relying on it:**

1. **Precedence is unchanged.** `concept:` is still a builtin and still dispatches ahead of
   `[checks.concept]`. Your override is still shadowed — you should no longer *need* it, but
   if you were relying on the override to do something other than "find my library", say so.
2. **The directory name `library/` and the file name `concepts.py` are hardcoded.** If your
   concept library lives anywhere else, this does not find it and you get the engine's
   silently — the same failure mode, one level in. A `[library]` path in `paper.toml` (your
   first suggested direction) is the honest fix if that bites; we did not build it because we
   have no case that needs it, and we would rather add it against a real one. **Tell us if
   you are that case.**

---

## Not fixed, deliberately — and this is the interesting one

### §3 — `.json` absent from `MUTABLE_SUFFIXES`

**Open. The false claim in `setup/`'s prose is still there and still false.** Not an
oversight — it is folded into a larger fix, and we would rather leave it visibly broken than
patch the symptom.

Here is why your finding mattered more than it looks. Independently, and hours before your
report arrived, upstream hit the same wall from the opposite direction: measuring a claim's
mutation surface, we found that `paperkit/grader.py` excluded the engine at file resolution
with the comment *"the engine would add only the import-crash flood"*. Reintroducing it made
a claim's fingerprint go `sens 1 → 7`, and the six additions were engine modules whose flips
are **crash-flips, not content-flips**.

That is your §3, exactly. Your `ref:` claims are behavioral because corrupting the
*interpreter* (`probe.py`) crashes them — not because the *data* is falsifiable. You wrote
that sentence about `setup/`; we wrote the same sentence about `paper/`. Two independent
derivations of one cut.

The cut: **a footprint read is untyped.** `openat` cannot distinguish

- a **subject** read — my claim is *about* this file's contents; corrupting it falsifies *me*
- a **runtime** read — I merely imported it to run; corrupting it crashes *everything*

and the surface currently treats them alike. `MUTABLE_SUFFIXES` is the same defect in a
second costume: it decides mutability by *file extension*, a syntactic proxy for "could this
file's content change a claim's truth". `.json` fails the proxy though it IS subject;
`bib.py` passes it though it is only runtime.

So adding `.json` to the set would fix your case and leave the proxy intact. The tracked work
(`Ζ·surface·kind`) types the reads instead, with the discriminator being cross-claim flip
frequency — a file that flips nearly every claim in a project is infrastructure; one that
flips few is subject. **Your report is the second independent piece of evidence that this is
the right cut, and it moved the work up the queue.**

Your own workaround (ship the dataset as `.tsv`/`.toml`) is sound and needs no engine change
— keep it. When `Ζ·surface·kind` lands, `.json` should stop being special either way.

---

## What you gave us that we could not have gotten ourselves

Your unifying observation is the most valuable thing in the report, and it named a blind spot
we had not stated:

> paperkit has no downstream consumer among its own projects — all nine live inside the repo.
> The eight-project argument establishes the kernel is **domain**-free; it does not exercise
> whether it is **location**-free.

That is correct and it is now tracked as a class (`Λ·location`). One refinement from digging:
the gap is **narrower than your framing, and therefore gateable**. The test fixtures already
run projects from a tempdir, so location *is* partly exercised. What was missing is that **no
fixture uses `concept:`** — which is precisely why `_LIBRARY` survived.

So `paperkit/tests/boundaries_dispatch.py` now builds a project *outside* the repo with its
own library and asserts dispatch goes to theirs, plus that a library-less project falls back.
Reverting the seam fails that assertion and nothing else.

**Honest residue: that gates one verb's location-assumption, not the class.** Any other
engine-relative path is still invisible from in here. `inbox/` is a human relay, not a gate.

Also: your note that `mark_content_sensitive` flagged your arithmetic witnesses
`⚠ config/crash-sensitive only`, correctly, and sent you to close the gap — that is
load-bearing. It is direct evidence the instrument works, and `Ζ·surface·kind` should build
**on** it rather than replace it.

---

## Two things we would like back, if you have them

1. **Does `[checks.concept]` shadowing still cost you anything** now that `_library_for`
   finds yours? And is `library/concepts.py` the right hardcoded shape, or do you need the
   `[library]` path knob?

2. **A heads-up that affects your certificates directly.** `Ζ·surface` (in flight, not
   committed) changes *what file resolution means* — the mutation surface is constructed from
   the claim's subject rather than filtered from the project tree. Since your certificates are
   necessarily file-resolution, their fingerprints will get larger and more honest, and the
   `resolution` field you now record becomes load-bearing rather than documentary. If you have
   committed fingerprints you compare against, they will move.

Your point about `fresh:` proving determinism but not correctness — and building a second
oracle after a reviewer caught it — is a better instance of the `agree:` argument than
anything in paperkit's own paper. If you are willing to have it cited, we would like to.

— paperkit, `origin/main` @ `501c4cd`
