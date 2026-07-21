# Findings from a downstream consumer — cassian-observability, 2026-07-20

Reported by a session working in `~/github/cassian-observability`, which uses paperkit
as a **compiler**: engine invoked as a CLI from its checkout, not vendored, not
pinned, not modified, no Bazel. Two projects so far (`library/`, `practice/`), both
gating green against `paperkit/gate.py` at `b2d313c`.

**The unifying observation.** All five findings below are *downstream-consumer* issues,
and paperkit has no downstream consumer among its own projects — all nine live inside
the repo. The eight-project argument establishes the kernel is **domain**-free; it does
not exercise whether it is **location**-free. Every place the engine resolves a path
relative to its own tree rather than the project's is invisible from inside.

Nothing here is a complaint about the design. Three of the five are the engine
behaving *more* honestly than expected, and one is a documentation/mechanism mismatch
of exactly the class paperkit exists to catch.

---

## 1. `concept:` is unusable from a downstream project — no seam

**Where:** `paperkit/resolver.py:33`

```python
_LIBRARY = Path(__file__).resolve().parent.parent / "library"
```

`concept:` is a built-in verb, so it is dispatched (`resolver.py:19` in `resolves`)
*before* `[checks.<type>]` custom types are consulted. A downstream project that
declares `[checks.concept]` in its own `paper.toml` is silently shadowed, and
`concept:<key>` runs **paperkit's** `library/concepts.py`, which has no such key.

**Repro:** in any project outside this repo, `check = {concept:anything}` → the check
fails; `[checks.concept]` in that project's `paper.toml` has no effect.

**Why it matters.** The concept library is the answer to sweep cost — author and grade
once, import the certificate. A downstream repo with its own concept library cannot
use the verb built for exactly that, and must fall back to a custom type
(`witness:<key>`) that **re-runs** the witness rather than importing its certificate.
That reintroduces the per-citation sweep the library exists to remove.

**Note on severity:** this is the one finding where the workaround costs something
real. The others are cosmetic or informational.

**Possible directions** (not a prescription): a `[library]` path in `paper.toml`;
resolving `_LIBRARY` relative to the *project* with a fallback to the engine's; or
declaring `concept:` explicitly engine-local and documenting the downstream idiom.

---

## 2. Def-resolution is structurally unavailable downstream

**Where:** `paperkit/grader.py:~411`, `_sandbox_setup`

```
Ν·loud: def-resolution sweep cannot find the engine in the sandbox
(expected a directory at <tmp>/<project-root>/paperkit, under the copied root <root>);
refusing to silently degrade to file resolution and emit a vacuous fingerprint.
```

**This error is excellent and should not change.** Refusing rather than degrading is
exactly right, and the message named the cause precisely enough to act on in one read.

Reporting it only because of the **interaction with `library/prove.py`**, which runs
`discriminate --only <key> --calc --resolution def`. A downstream library copying that
pattern gets the refusal, since the engine is a compiler on the box and not a
directory in the consuming repo. Downstream certificates can therefore carry only a
**file**-resolution fingerprint.

That is a fine answer — ours now records `"resolution": "file"` explicitly, because a
file fingerprint read as a def fingerprint overstates the ground it carries. Worth a
line in whatever documents the certificate contract, so the next consumer records it
rather than discovering it.

---

## 3. `setup/`'s reference dataset is not on Δ's falsification surface

**This is the one that looks like a real defect**, and it is the documentation/mechanism
mismatch class rather than a bug in behaviour.

**Where:** `paperkit/layout.py:16`

```python
MUTABLE_SUFFIXES = {".bib", ".tsv", ".toml", ".md", ".sh", ".py", ".txt"}
```

`.json` is absent, so Δ never corrupts `setup/reference.json`. But `setup/paper.toml:11`
and `setup/warrants.bib:5` both state the opposite:

> *"Because the check reads a real file in the project, Δ can corrupt it and flip the
> verdict: the claims are NON-VACUOUS (behavioral), unlike a live `probe:` read of the
> kernel, which no file mutation can falsify."*

**Evidence:** every entry in `setup/.delta-cache.json` lists exactly one sensitive
input — `probe.py` for the 22 `ref:` + 1 `fresh:` checks, `experiment.py` for the 6
`load:` checks. Never `reference.json`, never `loadtest.json`.

So the claims **are** behavioral, but because corrupting the *interpreter* crashes
them — not because the *data* is falsifiable. The insight the comment states ("bring
the evidence inside the sandbox so Δ can reach it") is sound and is the reason the
pattern works; it just is not what is currently happening.

**Two ways out, and the second needs no engine change:** add `.json` to
`MUTABLE_SUFFIXES`, or ship the dataset in a suffix already there — `.tsv` or `.toml`.
We took the second for our own reference data.

**Why it is worth fixing rather than re-wording:** as written, a silent rewrite of
`reference.json` leaves every `ref:` claim green. The stated property is the one you
want; only the surface is missing.

---

## 4. A missing `emit:` asset renders as a comment and does not fail the gate

**Where:** `paperkit/project.py:143`

```python
return [f"<!-- emit: missing {f['emit']} -->"]
```

**Repro (ours, verbatim):** a project with `out = "../docs/practice.md"` and a warrant
carrying `emit = {assets/ledger.md}`. The asset is resolved against
`pdir = cfg["out"].parent` (`project.py:270`) — i.e. `docs/`, not the project dir — so
our generator wrote to a path the projector never read. Result: **`gate.py` reported
PASS while the projected document contained `<!-- emit: missing assets/ledger.md -->`.**

Green and visibly broken at the same time. Our own `fresh:` check also passed, because
it verified the copy the *generator* wrote — two paths for one asset, which we then
fixed on our side.

The `pdir = out.parent` behaviour is defensible (an emitted asset is referenced *from*
the document). The reportable part is that a **placement that did not happen** is not a
finding. `--safe` already rejects an uncited placement as a postulate; a *missing*
placement seems at least as strong a signal.

---

## 5. `discriminate --only <unknown>` reports `grade: "broken"`

**Where:** `paperkit/discriminate.py:122-126`

```python
f = F.get(only)
if not f or not f.get("check"):
    print(json.dumps({"claim": only, "grade": "broken"}))
```

`broken` is defined in `grade.py:41` as *"check does not pass in a pristine sandbox —
repo is not green"*. The condition here is different: **no such claim**. Two states
collapse to one grade, and the reported one is alarming rather than diagnostic.

**Repro:** `discriminate.py --only <a-witness-key-rather-than-a-claim-key> <project>`
→ `{"claim": "...", "grade": "broken"}`, exit 1.

Cost us one debugging cycle on a healthy project: we passed a witness key where a
claim key was wanted, and the honest reading of the output was "your repo is red".

Given `RANK_C` already distinguishes six rungs, a seventh sentinel — or a distinct
`error` field — would separate "measured and failing" from "not measured".

---

## Context, if useful

What we built on top, in case the downstream shape is interesting:

- `library/` — our own concept library, `[checks.witness]`, 9 claims / 8 checked, all
  `behavioral`. Certificates are ⟨verdict, file-resolution fingerprint⟩ per §2.
- `practice/` — a document whose ledger table is generated *and* cross-checked against
  an independent artifact, after a reviewer pointed out that `fresh:` proves only
  determinism, not correctness. (`fresh:` could not distinguish our generator's two
  real bugs from a correct one; a second oracle could.)
- One thing Δ told us that we would not have found: our arithmetic witnesses graded
  `⚠ config/crash-sensitive only`. Correct, and it sent us to close the gap. The
  `mark_content_sensitive` distinction is doing real work.

Happy to expand any of these or supply reduced repros.
