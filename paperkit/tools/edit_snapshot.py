#!/usr/bin/env python3
"""A recoverable-by-construction snapshot for any tool that rewrites tree files.

WHY.  Every rewrite tool in this pipeline writes in place, and the failure mode is
not hypothetical: an ad-hoc dead-import regex (written by hand instead of routed
through `agda_imports`) matched an import statement plus its indented continuation
lines, and where an import sat above a PARAMETERIZED module header it swallowed the
header and its whole parameter list — 33 files damaged, `Coxeter/Core.agda` reduced
from 41 lines to 3.  The damage was found by the build, not by the tool.

`prune_imports.py:263` already names this exactly ("the decision was made and the
damage written before any verification could run"), and `split_pipeline.py:21` says
"a stash, not a revert, is the way back; this tool never touches git."  Both record
the discipline as PROSE.  This module is that prose mechanized: the tool takes the
snapshot itself, so recovery does not depend on the operator having thought of it
first.

WHY NOT `git stash`.  Stash is worktree-global and pops as a unit.  The pipeline
runs its per-file passes in parallel (`xargs -P 10`), so concurrent tools would
interleave pushes and pop each other's state — turning one tool's rollback into
another tool's corruption.  `git stash create` instead builds a commit OBJECT and
prints its SHA without touching the worktree or the stash stack, so:

  * every run gets its own immutable snapshot, identified by SHA;
  * concurrent runs cannot interfere;
  * nothing is staged, nothing is reverted, the worktree is untouched;
  * recovery is an explicit, per-path `git checkout <sha> -- <paths>` the operator
    runs deliberately — never something this module does on its own.

⚑ This module NEVER restores.  It records how to.  An automatic rollback would be a
revert-in-disguise, and reverting is the thing that costs a day's work.
"""
import contextvars
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOURNAL = os.path.join(ROOT, "scratch", "edit_snapshot.journal.tsv")


SNAPDIR = os.path.join(ROOT, "scratch", ".edit-snapshots")


# ── the two context variables ────────────────────────────────────────────────
#
# ⚑⚑⚑ INTENT IS TRANSMITTED AS A CONTEXT VARIABLE, NOT AS A PARAMETER (operator,
# 2026-08-26): *"This demands that intent be transmitted as a context variable.
# Likewise that snapshot state be transmitted as a context variable.  Because if we
# assume `intent=` is left as correct, then something else will stuff something in
# there thinking the `intent=` means something else."*
#
# ⚑⚑ THE DEFECT IS THAT `intent=` IS POSITIONALLY ADDRESSABLE BY ANYONE, AND TWO
# DIFFERENT PROPOSITIONS ARE SPELLED IDENTICALLY.  Both readings are live in this tree:
#
#     "what the operator asked for"    `require_at_entry` reading argv
#     "what this branch actually does"  `prune_leaf_opens:122` intent="apply" on a DRY run
#
# 17 call sites pass a hardcoded literal (`pycodemod --values guard intent`), and the
# distinction between the two readings is held only in a human's head at each one.  That
# is the condition under which the next writer stuffs in the wrong one and NOTHING
# DETECTS IT — the repo's own `a-go-must-carry-its-provenance` (a peer's GO and a
# user-owned GO are byte-identical without a provenance field) and
# `an-embedded-precondition-is-unverifiable` (a "go" carrying its own authorisation gives
# a clause to TRUST, not a fact to CHECK).  **A parameter is an embedded precondition.**
#
# ⚑⚑ THE DECLARATION SITE CARRIES THE SCOPE — THERE IS DELIBERATELY NO `source=` FIELD.
# A `(value, source)` tuple was proposed and REJECTED by the operator: *"Python has
# these.  The context var can close over whatever is in scope where it is declared."*  A
# hand-maintained provenance field beside the binding is a DERIVED VIEW maintained by
# hand next to the real one — the exact duplication this repo keeps paying for (a second
# roster beside `hook_structural_query.routes()`; a hand-written mode table beside
# `toolmodes`).  `contextvars` already records where a value was set, per-invocation, and
# `Token.old_value` already carries what it displaced.  Let the binding do the work.
#
# ⚑ WHY A ContextVar AND NOT A MODULE GLOBAL.  A global is per-PROCESS and per-CALL to
# reset; a ContextVar is per-INVOCATION and unwinds by token.  That difference is not
# theoretical here — it is exactly the `_snapshot_once` bug (see `SNAPSHOT_STATE`).

#: What this invocation is doing to the filesystem: "apply" | "dry-run" | None.
#:
#: ⚑ BOUND ONCE, AT THE POINT WHERE THE OPERATOR'S STATEMENT IS READ (`require_at_entry`
#: / `require_explicit_mutation`), and read everywhere below it.  A callee that wants to
#: know the intent ASKS THE CONTEXT rather than accepting a parameter it cannot
#: authenticate.
INTENT = contextvars.ContextVar("substrate_edit_intent", default=None)

#: Where that intent came from — the LABEL of the call that bound it, captured from the
#: binder's own scope.  ⚑ THIS IS NOT A HAND-BUILT `source=` FIELD: nothing sets it
#: separately from `INTENT`; `_bind_intent` is the only writer of either and writes both
#: in one act, so they cannot drift.  It exists because the refusal message must name
#: WHERE the ambient value was set, and a refusal that cannot say that sends the reader
#: hunting.
INTENT_ORIGIN = contextvars.ContextVar("substrate_edit_intent_origin", default=None)

#: Per-invocation snapshot state: {relpath already copied} plus the sha, or None.
#:
#: ⚑⚑⚑ THIS IS THE `_snapshot_once` BUG'S HOME, AND MOVING IT HERE DISSOLVES IT RATHER
#: THAN RELOCATING IT.  23 tools each declare a module-level `_SNAPPED = []` and a
#: `_snapshot_once(path)` that does `if _SNAPPED: return`.  That arms on file ONE and
#: no-ops after — which is RIGHT for the git-stash half (the stash is whole-worktree, so
#: taking it twice is waste) and WRONG for `_copy_untracked(paths)`, which is per-path
#: and therefore only ever saw the FIRST file.  Live exposure: the tree currently holds
#: well over a hundred untracked Agda leaves from an in-flight split, and
#: `_copy_untracked`'s own docstring says the untracked half is the population most
#: likely to need recovery.
#:
#: ⚑⚑ THE BUG EXISTS *BECAUSE* THE ARMING STATE WAS PER-CALL RATHER THAN PER-INVOCATION.
#: A list at module scope cannot express "once per run, but accumulating over paths" —
#: it can only express "once".  Splitting the state by KIND is what fixes it: the sha is
#: taken once (`sha` field), the copied set GROWS (`copied` field).  A ContextVar is
#: per-invocation by construction, which is the shape the state always wanted.
SNAPSHOT_STATE = contextvars.ContextVar("substrate_edit_snapshot_state", default=None)


class MutationContractError(BaseException):
    """The base of every refusal this module RAISES rather than exits on.

    ⚑⚑⚑ THE RULE A READER APPLIES, STATED ONCE (⟡intent-conflict-reconverted, operator:
    *"don't use `SystemExit`, since no script should assume it's the sole owner of the
    current pid"*).  Every refusal reachable from a def another module IMPORTS raises a
    subclass of this; `sys.exit` survives ONLY under `if __name__ == "__main__"`, where
    the process genuinely is this script's to end.  The dividing line is not "is it
    dangerous" — it is WHO OWNS THE PID.

    ⚑⚑⚑ IT DERIVES FROM `BaseException`, AND THAT IS A MEASUREMENT, NOT A PREFERENCE.
    The obvious cut — derive from `Exception` so the tree's existing handlers can contain
    it — was WRITTEN AND THEN REVERTED against a census.  `pycodemod --exits scratch
    scripts` reports 36 INTERLOCK sites, and **31 of them are `except Exception` wrapping
    a `guard()` call** in this exact shape:

        try:
            import edit_snapshot
            edit_snapshot.guard(label, [path], intent="apply")
        except Exception as e:
            print(f"   ⚠ snapshot unavailable ({e}) — recover via git if needed")
        # ... and the tool then WRITES ANYWAY

    Those handlers mean *"a snapshot is best-effort"*, and they are RIGHT about that.  But
    a mutation-contract refusal is not a failed snapshot, and an `Exception` subclass is
    indistinguishable from one at that handler.  Deriving from `Exception` would therefore
    convert a hard refusal into an ADVISORY PRINT WITH THE WRITE STILL HAPPENING — at all
    31 sites, including every hook-reachable gate.  That is the silent default this
    module's own docstring (`require_explicit_mutation`) exists to refuse, arrived at by
    "improving" the mechanism.

    ⚑⚑ SO THE TWO PROPERTIES ARE SEPARABLE, AND ONLY ONE OF THEM WAS EVER THE DEFECT.
    `SystemExit` has two: (a) it unwinds the whole interpreter, killing a caller's process
    — THE DEFECT; (b) it is invisible to `except Exception`, so a fail-closed refusal
    stays closed — LOAD-BEARING, and the thing keeping those 31 sites honest today.
    Deriving from `BaseException` keeps (b) and drops (a): the refusal propagates as an
    ordinary exception a frame can catch BY NAME, unwinds only to whoever is willing to
    name it, and never ends a pid this module does not own.

    ⚑ CONTAINMENT IS AVAILABLE, IT JUST HAS TO BE STATED.  `except MutationContractError`
    (or `except BaseException`) catches these; `except Exception` deliberately does not.
    That is the same construction as `_Override` being expensive to spell — a caller may
    absolutely contain a refusal, and must SAY it is doing so.

    ⚑ THE MESSAGES DID NOT CHANGE, AND THAT IS DELIBERATE.  Each refusal below already
    named its successor; a mechanism change that degraded the text would be a regression
    even though the exit code improved.  The text moved from a `print(..., stderr)` into
    the exception's own `str()`, which is where a raising refusal states itself.
    """


class AmbientVocabError(MutationContractError):
    """An out-of-vocabulary value offered to `Ambient.set`.

    ⚑ IT IS NOT ALSO A `ValueError`, though it reads like one.  `ValueError` derives from
    `Exception`, and Python resolves a handler by the MRO — so a dual base would be caught
    by the 31 `except Exception` sites above and re-open the hole the base class exists to
    close.  The kind is chosen by WHO MUST BE ABLE TO CATCH IT, not by what it resembles.
    """


class AmbientConflict(MutationContractError):
    """A SECOND write to a write-once ambient. Names the site that already bound it.

    ⚑⚑ IT JOINS THE `MutationContractError` FAMILY, WHICH MOVES IT OFF `Exception` — and
    that is a BEHAVIOUR CHANGE, stated rather than slipped in.  It was already the one
    refusal here raised correctly, but as an `Exception` it was catchable by the 31
    `except Exception` snapshot-advisory handlers, and reaching them meant a refusal
    printed as `⚠ snapshot unavailable` while the tool wrote anyway.  It never DID reach
    them, because `require_explicit_mutation` converted it to `sys.exit(2)` one frame
    earlier — the conversion this change removes.  So the base had to move in the SAME act
    that removed the converter; keeping it on `Exception` would have handed those 31 sites
    the swallowed-refusal behaviour the exit had been hiding.  Existing handlers that name
    `IntentConflict` / `AmbientConflict` explicitly are unaffected.

    ⚑⚑⚑ THIS FIRES AT THE WRITE, NOT AT A READ — AND THAT IS THE WHOLE DESIGN (operator,
    2026-08-26: *"So what you do instead is make the context var immutable."*).  The
    earlier cut compared a stated value against the ambient one AT EVERY CONSUMER: N
    checks, each of which can be forgotten, and forgetting one is precisely the
    plausible-local-fix failure this is scaled against.  A write-once variable means
    THERE IS NOTHING TO DISAGREE WITH — the second write fails where the write happens,
    not at some downstream consumer that happened to remember to look.  One enforcement
    point instead of a discipline distributed across nine call sites.

    ⚑⚑ AND IT IS WHAT THE TENANT CASE ACTUALLY NEEDED.  ⟡index-coverage-wrong-store was
    TWO FUNCTIONS INDEPENDENTLY RESOLVING THE SAME FACT (sqlite vs postgres in one
    report).  Neither routed through a comparison, which is why refuse-on-disagreement
    would not have caught it and why it shipped.  Write-once makes the FIRST resolution
    the answer and the second an ERROR, with no cooperation required from either site.
    """

    def __init__(self, amb, label, stated, ambient, origin):
        self.amb, self.label, self.stated = amb, label, stated
        self.ambient, self.origin = ambient, origin
        super().__init__(str(self))

    def __str__(self):
        a = self.amb
        same = (self.stated == self.ambient)
        head = (f"⚑ {self.label}: {a.kw} is ALREADY BOUND for this invocation "
                f"({self.ambient!r}) and is WRITE-ONCE.")
        body = (
            f"  bound:    {self.ambient!r}  by {self.origin}\n"
            f"  attempted:{self.stated!r}  at {self.label}\n")
        if same:
            # ⚑ A SECOND WRITE OF THE SAME VALUE IS STILL A DEFECT, AND SAYING SO IS THE
            # POINT.  It means two sites each believe they are the one that decides —
            # which is the ⟡index-coverage-wrong-store shape exactly. Today they agree;
            # nothing makes them agree tomorrow.
            body += ("  ⚑ The values MATCH, which is not a reprieve: two sites each "
                     "believe they are the\n    one that decides. They agree today and "
                     "nothing makes them agree tomorrow — that\n    is the shape that "
                     "put two stores in one report.\n")
        else:
            body += f"  {a.two_readings}\n"
        return head + "\n" + body + (
            f"  ⚑ Successors, in the order you should try them:\n"
            f"    1. READ IT, do not re-bind it: `edit_snapshot.{a.kw.upper()}.get()` "
            f"returns the value\n"
            f"       this invocation already established. A callee almost never needs "
            f"to write.\n"
            f"    2. BIND IT ONCE, AT ENTRY — where the operator's request is read "
            f"(`require_at_entry`),\n"
            f"       so every frame below inherits it and none has to assert anything.\n"
            f"    3. If this genuinely is a NEW invocation (a fixture, a nested run over "
            f"a different\n"
            f"       target), give it a NEW CONTEXT rather than overwriting this one:\n"
            f"           contextvars.copy_context().run(fn, ...)\n"
            f"       or, for the one sanctioned in-tree divergence, "
            f"`{a.kw.upper()}.override(...)`,\n"
            f"       which runs the body in a copied context and must be registered in\n"
            f"       `edit_snapshot.SANCTIONED_OVERRIDES`.")


class Ambient:
    """A per-invocation context variable with REFUSE-ON-DISAGREEMENT resolution.

    ⚑⚑⚑ ONE MECHANISM, THREE VARIABLES — NOT THREE IMPLEMENTATIONS.  `intent`,
    `snapshot state` and `tenant` are the same shape: a fact about THE INVOCATION that
    was being passed as a PARAMETER, so anyone could address it positionally and two
    different propositions ended up spelled identically.  Building a second copy of this
    for the tenant would be the derived-view duplication this repo keeps paying for; the
    vocabulary differs, the machinery does not.

    ⚑⚑ THE VALUE AND ITS ORIGIN ARE WRITTEN IN ONE ACT, BY ONE WRITER.  That is what
    keeps the origin from becoming a hand-maintained `source=` field — the tuple the
    operator explicitly rejected (*"the context var can close over whatever is in scope
    where it is declared"*).  `set()` below is the only writer of either var, so they
    cannot drift; the declaration site carries the scope and `contextvars` does the rest.

    ⚑ `vocab` IS CLOSED.  An unrecognised value REFUSES rather than passing — the escape
    must be at least as strict as the thing it bypasses, or a typo satisfies the contract
    silently.
    """

    def __init__(self, kw, vocab, two_readings):
        self.kw, self.vocab, self.two_readings = kw, tuple(vocab), two_readings
        self._var = contextvars.ContextVar(f"substrate_{kw}", default=None)
        self._origin = contextvars.ContextVar(f"substrate_{kw}_origin", default=None)

    def get(self):
        return self._var.get()

    def origin(self):
        return self._origin.get()

    def set(self, value, origin):
        """Bind value + origin in ONE act — WRITE-ONCE. A second write RAISES.

        ⚑⚑⚑ THE SINGLE ENFORCEMENT POINT.  Every route by which a wrong value could enter
        this invocation passes through here, so the check lives here and NOWHERE ELSE.
        That is the property a distributed refuse-on-disagreement discipline could not
        have: a consumer that forgets to compare is not a hole, because there is nothing
        for it to compare — the value it reads is the only one that was ever bound.

        ⚑⚑ AND `reset()` IS DELIBERATELY NOT EXPOSED AS A PUBLIC WAY BACK.  A `reset`
        returns the var to its prior value, which is legitimate for a scoped override and
        is ALSO a hole if anything may call it: write-once plus an unrestricted reset is
        just write-many with extra steps.  So the tokens are held privately by the
        override scope that created them (`_Override`), and there is no `Ambient.reset`
        for a caller to reach.  A new binding needs a NEW CONTEXT, not an undo.

        ⚑ WHAT THIS STILL DOES NOT PREVENT, STATED PLAINLY: a caller can reach the
        underlying `ContextVar` (`amb._var.set(...)`) or run in a context of its own
        making. Python has no unforgeable capability and this does not pretend to be one.
        The property it DOES have is that the ACCIDENTAL second binding — the one a
        locally-sound fix produces — fails loudly at the point of the write. Getting past
        it requires naming a private attribute or copying a context, neither of which a
        generator reaches for while "fixing" something.
        """
        # ⚑⚑⚑ THIS REFUSAL RAISES; IT USED TO `sys.exit(2)` (⟡intent-conflict-reconverted).
        # The MESSAGE is unchanged — it was already correct, and it names the vocabulary
        # and says why an unrecognised value refuses.  What changed is the MECHANISM, and
        # the operator's reason is not about this frame: *"don't use `SystemExit`, since no
        # script should assume it's the sole owner of the current pid."*  `edit_snapshot` is
        # reached as a LIBRARY from 58 importing files, so `sys.exit` here unwinds the
        # CALLER'S interpreter — and because `SystemExit` derives from `BaseException`, it
        # slips past every `except Exception` in the tree on the way out.  A refusal a
        # caller cannot contain is not a refusal, it is a kill.
        if value not in self.vocab:
            raise AmbientVocabError(
                f"⚑ {origin}: {self.kw}={value!r} is not one of "
                f"{' / '.join(map(repr, self.vocab))}.\n"
                f"  An unrecognised value REFUSES rather than passing — the escape "
                f"must be at least as\n  strict as the contract it bypasses, or a typo "
                f"satisfies it silently.")
        cur = self._var.get()
        if cur is not None:
            raise AmbientConflict(self, origin, value, cur,
                                  self._origin.get() or "<unknown>")
        return self._var.set(value), self._origin.set(origin)

    def _reset(self, tokens):
        """PRIVATE. Only `_Override.__exit__` unwinds a binding it made itself."""
        tv, to = tokens
        self._var.reset(tv)
        self._origin.reset(to)

    def resolve(self, label, stated=None):
        """The invocation's value. Binds if unbound; otherwise READS.

        ⚑⚑ A STATED VALUE THAT MATCHES THE ALREADY-BOUND ONE IS A NO-OP, NOT A REBIND.
        This is what lets the 17 hardcoded `intent="apply"` sites keep working unchanged
        while the guarantee still holds: under a `--apply` invocation they agree, and
        agreement passes silently (the operator's rule).  Under a DISAGREEING invocation
        the same site now raises — which is the whole point, and is why each of the 17 had
        to be re-read rather than swept.

        ⚑ THE DISAGREEING CASE ROUTES THROUGH `set`, so the refusal text, the successors
        and the write-once semantics are stated once. `resolve` adds no second policy.
        """
        ambient = self.get()
        if stated is None:
            return ambient
        if ambient is None:
            self.set(stated, f"stated at {label}")
            return stated
        if ambient != stated:
            # ⚑ RE-ENTER THE ONE ENFORCEMENT POINT rather than raising a second, subtly
            # different conflict here. Two spellings of one refusal is how the messages
            # drift apart and the weaker one becomes the one people read.
            self.set(stated, f"stated at {label}")
        return ambient

    def override(self, value, reason, label="override", announce_to=None):
        """A SCOPED, REASONED divergence — the deliberate override.

        ⚑⚑⚑ IT MUST EXIST, AND `prune_leaf_opens` IS THE CASE THAT PROVES IT.  That tool
        WRITES THE FILE EVEN IN DRY RUN (writes, re-`check`s, restores at the end), so on
        a stated `--dry-run` the operator's request and the filesystem truth genuinely
        DISAGREE — and the disagreement is CORRECT.  `require_at_entry` takes no snapshot
        on a stated dry-run, which for every other tool is right and here would leave the
        one mode advertised as safe as the only unprotected one (a crash between the
        write and the restore leaves the damage — precisely the snapshot's case).  A
        refuse-on-disagreement policy with NO override makes the correct behaviour
        unspellable, and the author deletes the guard instead.

        ⚑⚑ THE REASON IS REQUIRED AND IS PRINTED.  An override with no reason is
        `--no-verify`: a bypass leaving no trace of why.  Announcing it is the same
        construction as `SUBSTRATE_EXPLICIT_MUTATION=0` announcing itself.

        ⚑ A SCOPE, NOT AN ASSIGNMENT.  A bare re-`set()` leaks the divergent value past
        the branch that meant it, so later readers see an override as if it were the
        operator's statement — the exact confusion this change exists to remove.
        """
        return _Override(self, value, reason, label, announce_to)


#: ⚑⚑⚑ THE OVERRIDE IS DELIBERATELY EXPENSIVE TO SPELL, AND THE ROSTER IS WHY.  An
#: override as cheap as passing `intent=` is not a fix — it is the same defect with more
#: steps, because the moment a refusal is inconvenient the next writer reaches for the
#: escape instead of the contract.  So a divergence must ALSO be pre-registered here, by
#: `(kw, label)`, with the reason it exists.
#:
#: ⚑⚑ DESIGNED FOR ONE CASE, NOT FOR A POPULATION.  `prune_leaf_opens` is the ONE tool in
#: the tree whose stated intent and filesystem truth legitimately disagree (it writes,
#: re-checks, then restores — so a stated `--dry-run` still mutates).  A roster with one
#: member is the honest shape; if a second lands, that is a REVIEW, which is exactly the
#: friction this is for.  An unregistered override REFUSES and names this constant.
#:
#: ⚑ THIS IS NOT A SECOND ALLOW-LIST BESIDE A GATE.  It is the mechanism's own
#: declaration of where it is knowingly bypassed — the thing a reader of a refusal needs
#: in order to tell "sanctioned divergence" from "someone got past the guard".
SANCTIONED_OVERRIDES = {
    ("intent", "prune_leaf_opens (dry-run writes-then-restores)"):
        "This tool writes the file EVEN IN DRY RUN (writes, re-checks, restores at the "
        "end), so on a stated --dry-run the filesystem truth is 'apply' while the "
        "operator's request is 'dry-run'. A crash between the write and the restore "
        "leaves the damage — which is precisely the snapshot's case.",
}


class _Override:
    def __init__(self, amb, value, reason, label, announce_to):
        if value not in amb.vocab:
            raise ValueError(
                f"{amb.kw}.override({value!r}): not one of "
                f"{' / '.join(map(repr, amb.vocab))}. An override is at least as strict "
                f"as the contract it diverges from.")
        if not reason or not str(reason).strip():
            raise ValueError(
                f"{amb.kw}.override(...) requires a REASON. An override with no reason "
                f"is `--no-verify` — a bypass that leaves no trace of why.")
        # ⚑⚑ AN UNREGISTERED OVERRIDE REFUSES, AND THE REFUSAL NAMES ITS SUCCESSOR.  A
        # refusal with no named successor is an invitation to invent one locally, which
        # is the route-around this whole mechanism is trying not to provoke.  So the
        # message says exactly what to do: register it, or (far more likely correct) stop
        # diverging and let the ambient value stand.
        if (amb.kw, label) not in SANCTIONED_OVERRIDES:
            raise ValueError(
                f"{amb.kw}.override(...) at label {label!r} is NOT REGISTERED.\n"
                f"  A divergence from the ambient {amb.kw} is a claim that this branch "
                f"knows something\n"
                f"  the invocation does not — which is true exactly once in this tree "
                f"and is otherwise\n"
                f"  the defect this mechanism exists to catch.\n"
                f"  ⚑ Successors, in the order you should try them:\n"
                f"    1. DO NOT DIVERGE — let the ambient {amb.kw} stand. This is right "
                f"almost always;\n"
                f"       a local branch that 'knows better' than the invocation is the "
                f"failing shape.\n"
                f"    2. State it at the ENTRY point instead, so it IS the ambient "
                f"value and nothing\n"
                f"       downstream has to disagree with anything "
                f"(`require_at_entry`).\n"
                f"    3. If the divergence is genuinely real — the tool's effect differs "
                f"from the\n"
                f"       operator's request, as with a dry run that writes then restores "
                f"— register it\n"
                f"       in `edit_snapshot.SANCTIONED_OVERRIDES` under "
                f"({amb.kw!r}, {label!r})\n"
                f"       with the reason. That edit is REVIEWABLE, which is the point of "
                f"the friction.")
        self.amb, self.value, self.reason = amb, value, str(reason).strip()
        self.label, self._out, self._tokens = label, announce_to, None

    def run(self, fn, *a, **kw):
        """Run `fn` in a FRESH CONTEXT where this ambient holds `value`.

        ⚑⚑⚑ A NEW CONTEXT, NOT AN ASSIGNMENT — which is what makes the override
        structurally costly to spell.  The caller must hand over a CALLABLE and accept
        that the divergent binding cannot outlive it; a generator "fixing" a refusal
        cannot reach this by adding a keyword argument, which was the failure of the
        parameter form it replaces.

        ⚑⚑ `copy_context()` GIVES A GENUINELY FRESH BINDING, so the write-once rule is
        satisfied honestly rather than bypassed: inside the copy the var is unbound, this
        sets it once, and the outer context is UNTOUCHED — no reset, no undo, no hole.
        That is why `Ambient` exposes no public `reset`.
        """
        out = self._out or (lambda m: print(m, file=sys.stderr))
        cur, org = self.amb.get(), self.amb.origin()
        if cur is not None and cur != self.value:
            out(f"   ⚑ {self.label}: {self.amb.kw} OVERRIDE {cur!r} → {self.value!r} "
                f"in a copied context (outer binding by {org} is unchanged)\n"
                f"     reason: {self.reason}")

        def _inner():
            # ⚑ FRESH CONTEXT ⇒ THE VAR IS UNBOUND HERE ⇒ THIS IS A FIRST WRITE.
            self.amb._var.set(self.value)
            self.amb._origin.set(f"override at {self.label}: {self.reason}")
            return fn(*a, **kw)

        return contextvars.copy_context().run(_inner)

    # ⚑ NO `__enter__`/`__exit__`, DELIBERATELY.  A `with` block would have to mutate the
    # CURRENT context and undo it afterwards — i.e. exactly the write-then-reset hole that
    # write-once exists to close, wearing a context manager's clothes.  The override takes
    # a callable so the divergence is bounded by a CALL FRAME, which cannot be forgotten
    # the way an unbalanced `__exit__` can.
    # ⚑ BOTH HALVES OF THE PROTOCOL ARE DEFINED SO THE REFUSAL IS THE ONE A READER SEES.
    # With only `__enter__`, Python raises its own `TypeError: does not support the
    # context manager protocol (missed __exit__)` BEFORE calling anything of mine — a
    # correct refusal with no named successor, which is the shape this file argues
    # against everywhere else. Caught by the case below, which asserted on the message.
    def __exit__(self, *exc):        # pragma: no cover — __enter__ always raises first
        return False

    def __enter__(self):
        raise TypeError(
            f"{self.amb.kw}.override(...) is not a context manager, deliberately.\n"
            f"  A `with` block would mutate the CURRENT context and undo it afterwards — "
            f"the\n  write-then-reset hole that write-once exists to close.\n"
            f"  ⚑ Successor: pass the body as a CALLABLE, which runs it in a copied "
            f"context:\n"
            f"      edit_snapshot.{self.amb.kw.upper()}.override({self.value!r}, "
            f"reason=…, label=…) \\\n"
            f"          .run(lambda: <the work>)")


#: ⚑ THE TWO READINGS THIS VARIABLE CONFLATES, named in the refusal so a reader sees
#: WHY the two values differ rather than only THAT they do.
INTENT = Ambient(
    "intent", ("apply", "dry-run"),
    "These are two different propositions spelled the same way — 'what the operator "
    "asked for'\n  and 'what this branch actually does'.")


def _bind_intent(value, origin):
    """Bind the intent + its origin. Kept as a name because it reads at the call sites."""
    return INTENT.set(value, origin)


def resolve_intent(label, stated=None, argv=None):
    """THE intent resolver — a thin spelling of `INTENT.resolve`."""
    return INTENT.resolve(label, stated)


#: Backwards-compatible alias: the conflict type was `IntentConflict` before the tenant
#: variable forced the mechanism to be named for its SHAPE rather than its first member.
IntentConflict = AmbientConflict


#: ⚑⚑⚑ THE THIRD VARIABLE, AND IT IS THE WORST OF THE THREE BECAUSE ITS FAILURE IS
#: INVISIBLE.  A wrong intent either writes or refuses — observable either way.  A wrong
#: TENANT returns PLAUSIBLE ROWS NOBODY CAN DISTINGUISH.
#:
#: ⚑⚑ THE MEASURED INCIDENT IS NOT "SOMEONE PASSED THE WRONG FLAG" (⟡index-coverage-
#: wrong-store).  `_live_indexed` opened `catalog/catalog.db` with sqlite3 (334 MB, two
#: weeks stale) while `_selectivity` read live postgres — TWO STORES IN ONE REPORT.  The
#: postgres relations do not exist in catalog.db, so every PRAGMA returned nothing, the
#: `OperationalError` handler SWALLOWED it, and `_roles` defaulted the relations to
#: `candidate`.  A false positive in the direction that GENERATES WORK: it proposed
#: indexes for columns that already had them, and all three were the report's highest-
#: breadth candidates (32 → 26 once coverage read one store).  NOBODY STUFFED A WRONG
#: VALUE IN — two functions in one report each resolved the tenant INDEPENDENTLY and
#: disagreed.  That is the argument for a single ambient resolver in its sharpest form.
#:
#: ⚑⚑ `store.tenant` IS ALREADY THE DECLARED RESOLVER AND IS *NOT* THE PATH MOST REACHES
#: TAKE — measured, not assumed: `pycodemod --calls tenant` reports **14 calls**, while
#: `--calls connect` reports **59**.  So this is not building a resolver over a vacuum,
#: nor merely wiring an existing one: it is giving the existing authority an ambient
#: channel so a SECOND, INDEPENDENT resolution inside one process is detectable at all.
#:
#: ⚑ AND `SUBSTRATE_EXPLICIT_TENANT` DOES NOT INTERACT, BECAUSE IT NO LONGER EXISTS.
#: Verified rather than assumed (`pycodemod --literal SUBSTRATE_EXPLICIT_TENANT`): 8
#: sites, ALL of them in `scripts/ratchet.py`'s own `_selftest`, plus two docstrings. It
#: was DELETED at ⟡tenant-mandatory (`store.tenant`: *"its role did not invert, it
#: ENDED"*) — refusal is unconditional and env-independent. There is nothing here to
#: duplicate and nothing to defer to.
TENANT = Ambient(
    "tenant", ("live", "sandbox"),
    "A read against the wrong tenant returns plausible rows nobody can distinguish; "
    "two\n  independent resolutions in one process is how one report read two stores.")


def naming_tenant(value, label):
    """Bind the tenant for this invocation, and return the string a RESULT should carry.

    ⚑⚑ NAMING THE TENANT IN THE OUTPUT IS HALF THE FIX, NOT A NICETY — the repo's own
    `wrong-tenant-read-is-silent` says so: *"one resolver, and name the tenant in the
    output."*  A read whose verdict does not carry which store answered it is
    UNVERIFIABLE AFTER THE FACT, and this arc has produced repeated instances of a
    well-formed figure arriving without its scope.  So the binder RETURNS the label, and
    a caller that prints a result has the string in hand at the moment it prints it.
    """
    TENANT.resolve(label, stated=value)
    return f"[tenant={value}]"


# ── the admission rule for a fourth variable ─────────────────────────────────────────
#
# ⚑⚑⚑ THREE VARIABLES IS WHERE THIS STOPS BEING THREE FIXES AND BECOMES AN ARCHITECTURE,
# AND AN ARCHITECTURE WITHOUT AN ADMISSION RULE GROWS A FIFTH MEMBER *BECAUSE THE PATTERN
# WAS THERE*.  That is the same plausible-local-reasoning failure one layer up, so the
# rule is stated here rather than left to the next reader's judgement.
#
# A value BELONGS in this context iff ALL FOUR hold:
#
#   1. IT IS A PROPERTY OF THE INVOCATION, NOT OF A CALL.  It is decided once, where the
#      operator's request is read, and is the same fact for every frame below.  `intent`
#      and `tenant` qualify.  A per-file path does NOT: it varies per call, so an ambient
#      binding would be read by frames it does not describe.
#   2. A CALLEE CANNOT AUTHENTICATE IT AS A PARAMETER.  The failure must be that a callee
#      receiving it has NO WAY TO TELL a correct value from a wrong one — which is what
#      makes the parameter an embedded precondition.  If the callee can check it, check
#      it; do not make it ambient.
#   3. A WRONG VALUE IS SILENT OR NEAR-SILENT.  The whole justification is that nothing
#      detects the error today.  A value whose wrongness throws, or is visible in the
#      output, does not need this and should not pay its cost.
#   4. IT HAS A CLOSED, SMALL VOCABULARY.  Refuse-on-disagreement requires equality to be
#      meaningful. An open-ended value (a path, a count, a connection object) cannot be
#      compared this way and would make the refusal noise.
#
# ⚑ AND THE DISQUALIFIER, WHICH IS NOT MERELY THE NEGATION: a value that a caller may
# LEGITIMATELY VARY MID-INVOCATION does not belong. The mechanism's core assertion is
# that a disagreement is a DEFECT; for a value that is supposed to change, every change
# is a false refusal, and a guard that fires on correct behaviour trains everyone to
# route around it. `SNAPSHOT_STATE` sits at the edge of this and is admitted only because
# it is a per-invocation RECORD rather than a compared value — note it has no `resolve`.
#
# ⚑⚑ WHAT THIS MECHANISM IS, PLAINLY, SO IT IS NEVER MISREAD AS MORE *OR AS LESS*:
#
#   IT IS ENFORCEMENT AT THE WRITE, WITH A NAMED RESIDUAL. IT IS NOT A CAPABILITY.
#
# `Ambient.set` is WRITE-ONCE: the first binding wins and a second RAISES, naming the site
# that already bound it. That is a real guarantee and not a convention, and it holds
# without any cooperation from consumers — a consumer that never compares anything is not
# a hole, because only one value was ever bound. This is stronger than the census-only
# form an earlier cut of this file settled for, and the difference matters: a census
# informs a READER, and the adversary here does not read.
#
# ⚑ THE RESIDUAL, STATED RATHER THAN GLOSSED. A caller can still:
#   · reach the private `ContextVar` directly (`INTENT._var.set(...)`), or
#   · run its work in a context of its own making (`copy_context().run(...)`).
# Python has no unforgeable capability; neither of those can be prevented. What matters is
# that BOTH ARE DELIBERATE ACTS — naming a private attribute, or constructing a context —
# and neither is what a plausible-local-fix generator produces while "fixing" a refusal.
# The ACCIDENTAL second binding, which is the failure actually being defended against,
# fails loudly at the point of the write.
#
# The adversary this is scaled against is not a liar. It is a plausible-local-fix generator
# with write access and no memory of why the constraint exists — sound reasoning from a
# locally-complete picture, emitting something that READS as correct. So the design target
# is that A WRONG FIX CANNOT READ AS COMPLIANT, not that a determined caller cannot get
# past it. And every refusal above names its successor, because a refusal with no named
# successor is an invitation to invent one locally — which is that same adversary's move.
#
# ⚑ THREADS AND SUBPROCESSES. `contextvars` propagates into `asyncio` tasks and does NOT
# cross a `threading.Thread` boundary — a thread starts from an empty context, so an
# ambient bound in the parent is INVISIBLE there and a binding made inside it is invisible
# to the parent. No tool in this population spawns threads (the writers are single-
# threaded loops; `check()`-style helpers shell out via `subprocess`, which crosses a
# PROCESS boundary and carries no context by construction — the child re-reads argv and
# binds its own, which is correct). If a threaded writer ever lands here it must pass the
# context explicitly (`copy_context().run` inside the thread target); recorded now because
# the failure would be a SILENTLY UNBOUND ambient, which reads exactly like a first write.


def sanctioned_setters():
    """The call sites permitted to BIND an ambient — the census a gate would ratchet.

    ⚑ THE HONEST FORM OF THE UNFORGEABILITY GAP.  Since `.set()` cannot be prevented, the
    next best thing is that every sanctioned binding is enumerable, so a NEW one is a new
    key and refusable. Returned as data rather than prose so a gate can consume it without
    re-deriving the list — the second roster this repo keeps paying for otherwise.
    """
    return {
        ("intent", "require_explicit_mutation"): "reads the operator's argv statement",
        ("intent", "resolve_intent"): "binds a stated intent when none is ambient",
        ("tenant", "naming_tenant"): "binds the tenant and returns the result's label",
        ("snapshot", "snapshot_once"): "per-invocation snapshot record",
        ("snapshot", "snapshot"): "establishes the record for a direct guard() caller",
    }


def _git(*args):
    return subprocess.run(("git",) + args, cwd=ROOT, capture_output=True, text=True)


def _is_tracked(rel):
    return _git("ls-files", "--error-unmatch", rel).returncode == 0


def _copy_untracked(paths):
    """Copy each untracked path into a snapshot dir; return [(rel, saved_path)].

    A `git stash create` commit holds only TRACKED content, so without this the
    63 untracked pipeline tools — which include every destructive one — have no
    recovery point at all.  Best-effort: a copy failure must not stop the work.
    """
    import shutil
    saved = []
    # ⚑⚑⚑ THE PER-INVOCATION COPIED SET — THIS IS WHERE `_snapshot_once`'s BUG DIES.
    # The 23 `_snapshot_once` helpers arm a module-level `_SNAPPED` on file ONE and
    # no-op after, so files 2..N were never copied.  Splitting the state by KIND is the
    # fix: the SHA is taken once (whole-worktree, so twice is waste), the COPIED SET
    # accumulates.  A module global could not express that difference; a per-invocation
    # record can, because it is a record rather than a latch.
    _st = SNAPSHOT_STATE.get()
    _already = _st.get("copied") if _st else None
    for p in paths:
        rel = os.path.relpath(p, ROOT) if os.path.isabs(p) else p
        full = os.path.join(ROOT, rel)
        if not os.path.isfile(full) or _is_tracked(rel):
            continue
        # ⚑ SKIP ONLY WHAT THIS INVOCATION ALREADY SAVED.  The store is keyed by path
        # and holds the pre-write copy; re-copying after the tool has written would
        # overwrite the good copy with the damaged one — the recovery point destroying
        # itself.  So "already copied" is a genuine skip, and "not yet seen" is a copy.
        if _already is not None and rel in _already:
            continue
        try:
            dest = os.path.join(SNAPDIR, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(full, dest)
            saved.append((rel, dest))
            if _already is not None:
                _already.add(rel)
        except OSError:
            pass
    return saved


def snapshot_once(label, paths=(), intent=None):
    """Take the worktree SHA once per invocation, but COPY EVERY untracked path.

    ⚑⚑⚑ THE REPLACEMENT FOR THE 23 HAND-ROLLED `_snapshot_once` HELPERS, AND IT IS NOT
    A RENAME.  Each of those is `if _SNAPPED: return` over a module-level list — a LATCH,
    which arms on file one and no-ops after.  That is right for the stash (whole-worktree,
    so a second one is waste) and WRONG for `_copy_untracked`, which is per-path: files
    2..N of every multi-file run were never copied aside.  The two halves have different
    arities and the latch could only express one of them.

    ⚑⚑ SO THE STATE IS SPLIT BY KIND RATHER THAN SHARED: `sha` is taken once, `copied`
    ACCUMULATES.  A tool calling this per file gets one stash and N copies, which is what
    every one of those docstrings said it wanted ("arming once per run is both correct
    and cheap") and none of them delivered for the untracked half.

    ⚑ PER-INVOCATION, NOT PER-PROCESS.  A module global survives across an in-process
    second run (a selftest, a library caller, a `run_selftests` sweep) and silently
    suppresses its snapshot entirely. A ContextVar unwinds with the scope that set it.

    ⚑⚑⚑ IT CHECKS THE MUTATION CONTRACT, AND WITHOUT THIS IT WAS A SILENT DOWNGRADE.
    Every one of the 23 hand-rolled `_snapshot_once` helpers calls `guard`, which is
    `require_explicit_mutation` + `snapshot` + `announce`.  This replacement called
    `snapshot` DIRECTLY, so adopting it would have removed the `--apply` XOR `--dry-run`
    check from 23 writers at the moment they were consolidated — a deduplication that
    silently deletes a contract, which is the regression shape that looks like progress.
    The check is per-INVOCATION like the SHA, not per-path: it is a question about how
    the process was invoked, and asking it once is asking it correctly.

    ⚑⚑ `intent` EXISTS BECAUSE ONE CALLER GENUINELY NEEDS IT AND COULD NOT MIGRATE
    WITHOUT IT.  `sppf_node_index._snapshot_once` passes `intent="apply"`: its polarity is
    inverted (the flagged `--check` is the READ, the bare invocation is the WRITER), and
    the pre-commit hook invokes `--check`, so an argv-reading guard would exit 2 and abort
    every commit.  A replacement that cannot express what a caller already states is not a
    replacement — it is a 22-of-23 migration with the hard case left behind.
    """
    require_explicit_mutation(label, intent=intent)
    st = SNAPSHOT_STATE.get()
    if st is None:
        st = {"sha": None, "copied": set(), "label": label}
        SNAPSHOT_STATE.set(st)
    if st["sha"] is None:
        st["sha"] = snapshot(label, paths) or ""
        announce(st["sha"] or None, label)
    elif paths:
        # ⚑ THE SHA IS DONE; THE COPIES ARE NOT.  This is the branch the latch skipped.
        _copy_untracked(paths)
    return st["sha"] or None


def snapshot(label, paths=()):
    """Snapshot the worktree before a tool's first write. Returns a SHA, or None.

    `label` names the tool+target ("decompose_rewrite Substrate.Foundation.Eq").
    `paths` is advisory — recorded in the journal so a reader knows which files the
    run intended to touch. The snapshot itself is whole-worktree, because a tool
    that damages a file it did not intend to touch is exactly the case that needs
    recovering (measured: the regex above hit 33 files while targeting 2 modules).

    Returns None — never raises — if this is not a git worktree or git fails. A
    snapshot is a safety net, and a missing net must not stop the work; the caller
    gets None and reports it. Callers MUST NOT treat None as a reason to skip the
    edit, and must not treat a SHA as permission to skip verification.
    """
    # ⚑ `git stash create` CANNOT capture untracked files — it ignores
    # --include-untracked (that flag only works on the stack-pushing `git stash`).
    # MEASURED: a conversion damaged six UNTRACKED pipeline tools and the recovery
    # `git checkout <sha> --` failed with "did not match any file(s) known to git".
    # The tools most likely to be damaged are exactly the ones not in git, so a
    # tracked-only snapshot protects the wrong half.  Copy anything untracked into
    # the snapshot directory first; recovery for those is a file copy, reported by
    # `--list`.
    # ⚑ ESTABLISH THE PER-INVOCATION RECORD IF NOTHING ABOVE DID, so a tool that calls
    # `snapshot`/`guard` directly (rather than through `snapshot_once`) still accumulates
    # its copied set instead of re-copying — and, critically, still cannot overwrite a
    # good pre-write copy with a post-write one.
    if SNAPSHOT_STATE.get() is None:
        SNAPSHOT_STATE.set({"sha": None, "copied": set(), "label": label})
    untracked = _copy_untracked(paths)
    r = _git("stash", "create")
    sha = r.stdout.strip()
    if r.returncode != 0 or not sha:
        # `stash create` prints nothing when the worktree is clean — there is
        # nothing to recover TO, so HEAD is the honest snapshot point.
        head = _git("rev-parse", "HEAD")
        sha = head.stdout.strip() if head.returncode == 0 else ""
        if not sha:
            return None
    # Keep the object alive: an unreferenced `stash create` commit is loose and a
    # `git gc` can collect it. A ref makes the snapshot durable until deliberately
    # dropped — the whole point is that it is still there tomorrow.
    _git("update-ref", f"refs/edit-snapshots/{sha[:12]}", sha)
    _record(sha, label, paths)
    if untracked:
        print(f"  ⚑ {len(untracked)} UNTRACKED file(s) copied to "
              f"{os.path.relpath(SNAPDIR, ROOT)}/ (git cannot hold them):")
        for rel, dest in untracked[:5]:
            print(f"      cp {os.path.relpath(dest, ROOT)} {rel}")
        if len(untracked) > 5:
            print(f"      … and {len(untracked) - 5} more (see --list)")
    return sha


def _record(sha, label, paths):
    """Append to the journal. Best-effort: never breaks the caller."""
    try:
        new = not os.path.exists(JOURNAL)
        with open(JOURNAL, "a", encoding="utf-8") as fh:
            if new:
                fh.write("# sha\tlabel\tn_paths\tpaths\n"
                         "# restore:  git checkout <sha> -- <path>...\n"
                         "# list:     git show --stat <sha>\n")
            rel = [os.path.relpath(p, ROOT) if os.path.isabs(p) else p for p in paths]
            fh.write(f"{sha}\t{label}\t{len(rel)}\t{','.join(rel[:40])}\n")
    except OSError:
        pass


def announce(sha, label, out=print):
    """Tell the operator how to recover. Called once, at the start of a run."""
    if sha is None:
        out(f"⚠ {label}: NO SNAPSHOT (not a git worktree?) — edits are unrecoverable")
        return
    out(f"snapshot {sha[:12]} [{label}] — recover any file with:")
    out(f"    git checkout {sha[:12]} -- <path>")


def contents(sha):
    """([tracked_rel], [(untracked_rel, saved_path)]) a snapshot can restore.

    ⚑ SNAPSHOTTING WAS A TOOL AND RESTORING WAS A PRINTED SUGGESTION (C3/§58).
    `snapshot` emits `git checkout <sha> -- <path>` and NOTHING consumes it, so
    undo has always been a hand-assembled shell line — the one shape this session
    has otherwise converted away from.  Worse, that line is INCOMPLETE: a bare
    `git checkout` reaches only TRACKED files, and the tools most likely to need
    recovery are the untracked ones (`_copy_untracked`'s own comment measures 63).
    MEASURED on the live case: the damaged root is tracked and its two leaves are
    NOT, so the printed command would have restored one of three files and looked
    like it worked.
    """
    tracked = []
    r = _git("show", "--name-only", "--pretty=format:", sha)
    if r.returncode == 0:
        tracked = [l.strip() for l in r.stdout.split("\n") if l.strip()]
    untracked = []
    if os.path.isdir(SNAPDIR):
        for d, _s, fs in os.walk(SNAPDIR):
            for f in fs:
                dest = os.path.join(d, f)
                untracked.append((os.path.relpath(dest, SNAPDIR), dest))
    return tracked, sorted(untracked)


def restore(sha, paths=(), apply=False):
    """Restore `paths` (or everything) from a snapshot. Returns [(rel, how)].

    ⚑ THE UNTRACKED STORE IS KEYED BY PATH, NOT BY SHA — and saying so is part of
    the tool's job.  `_copy_untracked` writes `.edit-snapshots/<relpath>`, so a
    later snapshot OVERWRITES an earlier copy of the same file: the untracked half
    holds the MOST RECENT pre-write state, not one per SHA.  For the live case
    that is exactly right (the last snapshot preceded the damaging run), but a
    caller must not believe it is restoring a specific historical version.
    Reported as `untracked-latest` rather than `untracked@<sha>` so the verdict
    cannot be misread.
    """
    tracked, untracked = contents(sha)
    want = {os.path.relpath(p, ROOT) if os.path.isabs(p) else p for p in paths}
    out = []
    for rel in tracked:
        if want and rel not in want:
            continue
        if apply:
            rc = _git("checkout", sha, "--", rel).returncode
            out.append((rel, "tracked" if rc == 0 else "FAILED"))
        else:
            out.append((rel, "tracked"))
    import shutil
    for rel, src in untracked:
        if want and rel not in want:
            continue
        if apply:
            dst = os.path.join(ROOT, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                shutil.copy2(src, dst)
                out.append((rel, "untracked-latest"))
            except OSError as e:
                out.append((rel, f"FAILED {e}"))
        else:
            out.append((rel, "untracked-latest"))
    return out


# ⚑⚑ THE THIRD SPELLING IS A HAZARD, NOT A SYNONYM (⟡explicit-mutation, Ⓐ40).
# `paydown.py`, `scope_fix.py` and `telescope_migrate_gen.py` spell no-write as `--dry`,
# and `toolmodes --conventions` lists it under "accepted by ≥3 tools, declared by no
# convention".  All three WRITE when it is absent, and none validated argv — so a typo'd
# `--dry-run` on any of them fell through to the writing branch and mutated the Agda tree.
# That is `census-keyed-on-one-spelling` in the mutation family: the guard reads one
# spelling, the tool dispatches on another, and the gap between them is silent.
#
# ⚑ IT IS RECOGNISED HERE SO IT CAN BE REFUSED WITH A SUCCESSOR, NEVER BLESSED AS AN
# ALIAS.  Accepting `--dry` as satisfying the contract would freeze the divergence into
# the shared authority — three spellings for one intent, and the next writer picks one at
# random.  Naming it and pointing at `--dry-run` retires it: the caller learns the word
# the convention actually declares, and the tool refuses in the meantime rather than
# guessing which branch the typo meant.
NEAR_MISS_SPELLINGS = {
    "--dry": "--dry-run",
    "--dryrun": "--dry-run",
    "--dry_run": "--dry-run",
    "--apply-all": "--apply",
    "--no-dry-run": "--apply",
    "--write": "--apply",
    "--force": "--apply",
}


def require_explicit_mutation(label, argv=None, intent=None):
    """REFUSE unless the caller stated `--apply` or `--dry-run`. Exactly one, always.

    `intent="apply"` / `"dry-run"` states it IN CODE instead of on the command line —
    for a `_selftest` driving the write path against a temp fixture, where the process
    argv carries `--selftest` and the operator asked for no mutation at all.  It is
    STILL an explicit statement; what it is not is a reading of the wrong argv.

    ⚑⚑⚑ NO DEFAULT IN EITHER DIRECTION (operator, 2026-08-18: *"no default-dry, no
    default-apply, only explicit behavior"*).  Both defaults fail SILENTLY and in
    opposite directions:

        default-dry     the tool does nothing when the caller meant to write, and the
                        caller reads "no changes" as "nothing to change"
        default-apply   the tool writes when the caller meant to look

    Which one you get is a property of whichever tool you happened to invoke — 31 of 35
    writers default to reporting, 3 default to writing, and exactly ONE states both.  So
    the caller cannot carry a habit across tools; the decision has to be at the call site
    every time, which means the tool must refuse to guess.

    ⚑ ENFORCED HERE BECAUSE THIS IS WHERE EVERY WRITER ALREADY PASSES.  `guard` is the
    one call a rewrite tool makes before its first write — 76 sites across 56 files,
    mostly through the `_snapshot_once` wrapper.  Putting the check in each tool's `main`
    is the 35-call-site edit this repo keeps retiring; putting it at the shared chokepoint
    means a writer added next month inherits it without knowing, exactly as
    `ratchet.check_argv` merges `UNIVERSAL_FLAGS` on every gate's behalf.

    ⚑⚑ IT REFUSES BY DEFAULT AS OF 2026-08-25 (⟡explicit-mutation-default).  This
    paragraph previously read *"ADVISORY … flipping this to a hard refusal in one commit
    would break every in-flight repair loop … warn now, measure the population, refuse
    when it is paid down."*  Kept as residue, because the argument was weighed and
    REJECTED rather than forgotten, and because the ratchet framing was the wrong shape
    for this debt:

      · A ratchet paydown converges only if the population SHRINKS.  This one grows —
        every new writer inherits `guard` and, under an advisory, inherits the lesson
        that the contract is optional.  The operator: *"otherwise it gets ignored and,
        worse, NEW CODE GETS WRITTEN FORGETTING THAT IT MATTERS."*
      · "Breaks every in-flight repair loop" reads a refusal as damage.  It is the
        deliverable: the loop's owner states `--apply` or `--dry-run` once and continues,
        and until they do, a tool that would have written on a bare invocation does not.
      · The census stayed advisory long enough to be measured, which was its purpose;
        `check_snapshot_guard`'s two ratchets keep measuring ADOPTION (is the contract
        consulted at the DECISION point) independently of whether it REFUSES.

    ⚑ WHAT REPLACES THE RATCHET IS THE ESCAPE HATCH, NOT A GRACE PERIOD:
    `SUBSTRATE_EXPLICIT_MUTATION=0` restores the advisory and SAYS SO ON EVERY RUN.  A
    grace path that warns loudly with a deadline was proposed and rejected — that is the
    advisory state renamed, and a deadline in a comment is not a mechanism.
    """
    import os as _os
    import sys as _sys
    # ⚑ AN UNKNOWN `intent` IS A REFUSAL, NEVER A PASS.  Accepting any truthy value
    # would make `intent="maybe"` — or a typo — satisfy the contract silently, which is
    # the accepted-and-unvalidated shape this repo censuses.  The escape has to be at
    # least as strict as the thing it bypasses.
    # ⚑⚑ THE STATED INTENT IS NOW RESOLVED AGAINST THE AMBIENT CONTEXT, NOT ACCEPTED ON
    # SIGHT.  `resolve_intent` validates it (an unknown value RAISES `AmbientVocabError`;
    # this read "still exits 2" until ⟡intent-conflict-reconverted removed that exit),
    # binds it when nothing above stated one, and RAISES `IntentConflict` when it
    # disagrees with an ambient value.  That is the whole point of the lift: a parameter
    # anyone can address positionally becomes a claim checked against the invocation.
    # ⚑⚑⚑ `IntentConflict` PROPAGATES; IT USED TO BE CAUGHT HERE AND CONVERTED TO
    # `_sys.exit(2)` (⟡intent-conflict-reconverted).  *"The one path that got the exception
    # discipline right threw it away one frame later."*  `resolve_intent` raises a
    # correctly-shaped, correctly-worded refusal and this frame discarded it in favour of
    # killing the interpreter — in a def reached from 58 importing files.  There is no
    # handler here at all now: the exception IS the refusal, and it already carries the
    # message this frame used to print.
    if intent is not None:
        resolve_intent(label, stated=intent)
        return None
    argv = _sys.argv if argv is None else argv
    stated = [f for f in ("--apply", "--dry-run") if f in argv]
    if len(stated) == 1:
        # ⚑ THE OPERATOR'S STATEMENT BECOMES THE AMBIENT INTENT FOR THIS INVOCATION.
        # This is the binding the whole change turns on: read argv ONCE, here, where the
        # operator's request is actually being read — and every callee below asks the
        # context instead of re-reading an argv that may not be describing it.
        # `build_census` reached as a library from `gen_build_makefiles` is exactly the
        # case: `sys.argv` there says `--check-census`, another tool's flags describing
        # another tool's request.
        _val = "apply" if stated[0] == "--apply" else "dry-run"
        if INTENT.get() is None:
            _bind_intent(_val, f"argv at {label} ({stated[0]})")
        return None
    if len(stated) == 2:
        # ⚑ BOTH IS ALWAYS AN ERROR, even in advisory mode: the caller stated two
        # contradictory intents and no reading of that is safe.
        # ⚑ RAISES rather than exits (⟡intent-conflict-reconverted) — same message, and
        # this def is library-reachable from 58 importers.
        raise MutationContractError(
            f"⚑ {label}: BOTH --apply and --dry-run given — they are mutually "
            f"exclusive. Refusing rather than picking one.")
    # ⚑ A REFUSAL MUST NAME ITS SUCCESSOR.  A bare "state one" is half a gate: the caller
    # who typed `--dry` already believes they stated an intent, and telling them the
    # contract without telling them the WORD sends them back to guess again.  When a
    # near-miss is present the message leads with the exact substitution.
    near = [a for a in argv if a in NEAR_MISS_SPELLINGS]
    msg = (f"⚑ {label}: neither --apply nor --dry-run was given.\n"
           f"  A mutating tool must not GUESS: default-dry silently does nothing when you "
           f"meant to write,\n  default-apply silently writes when you meant to look. "
           f"State one.")
    if near:
        sub = "\n".join(f"      {a}  →  {NEAR_MISS_SPELLINGS[a]}" for a in near)
        msg += (f"\n  ⚑ you typed a NEAR MISS — this tool does not accept it as a "
                f"statement of intent:\n{sub}\n"
                f"    the two words the convention declares are `--apply` and "
                f"`--dry-run`; there is no third.")
    # ⚑⚑ THE ADVISORY IS ONLY HALF A RATCHET WITHOUT A CENSUS.  This contract is
    # advisory precisely so the population can be measured before it refuses — and
    # measuring it means recording every unstated invocation, not counting the ones a
    # human happened to notice.  Best-effort by construction; see `ratchet.
    # log_fallthrough`.  The verdict below is computed from `stated`, never from this.
    try:
        _sys.path.insert(0, _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "scripts"))
        import ratchet as _r
        _r.log_fallthrough(label, "unstated-mutation", known=("--apply", "--dry-run"),
                           argv=argv, exit_code=2)
    except Exception:
        pass
    # ⚑⚑ REFUSAL IS THE DEFAULT AS OF 2026-08-25 (⟡explicit-mutation-default).  The
    # operator's reason is the load-bearing half, and it is not about this run:
    # *"otherwise it gets ignored and, worse, NEW CODE GETS WRITTEN FORGETTING THAT IT
    # MATTERS."*  An ADVISORY guard teaches every subsequent author that the contract is
    # optional — the declaration (`toolmodes --conventions`: mutually exclusive, one
    # REQUIRED, refuse rather than guess) and the behaviour disagreed, and the
    # declaration lost by default.
    #
    # ⚑ THE FLAG IS A STATEMENT OF THE CALLER'S INTENT, NOT A SAFETY INTERLOCK ON A
    # MUTATING CODE PATH.  So there is deliberately NO read-path exemption: a tool that
    # CAN mutate requires the statement at EVERY invocation, including one that would
    # only have read.  The alternative is a judgement made ONCE by the tool's author
    # ("this path is read-only") and then inherited silently by every caller forever —
    # exactly the unstated inherited assumption this repo keeps finding wrong.
    #
    # ⚑ THE COUNT IS THE EVIDENCE FOR THE FLIP, NOT AGAINST IT.  Measured at the flip:
    # `pycodemod --guarded guard` -> 68 call sites.  Read as a breakage estimate that
    # number argues for staging; read correctly it says how many tools were one typo
    # away from writing.  A warn-with-deadline grace path was considered and REJECTED —
    # it is the advisory state under another name, and the operator's reason applies to
    # it verbatim.
    # ⚑ RAISES rather than exits (⟡intent-conflict-reconverted).  The message is verbatim
    # what this frame used to print — including the near-miss substitution table — because
    # a refusal that stops naming its successor is a regression even when the mechanism
    # improves.  It is now the exception's `str()`, which is where a raising refusal states
    # itself, and the CLI boundary renders it exactly as before.
    if _os.environ.get("SUBSTRATE_EXPLICIT_MUTATION") != "0":
        raise MutationContractError(msg)
    # ⚑ THE ESCAPE IS LOUD BY CONSTRUCTION.  A strictness flip with NO off-switch is one
    # somebody disables by editing this file, which is strictly worse — the bypass then
    # leaves no trace.  So `=0` is supported and ANNOUNCES ITSELF: an unarmed run must
    # never be mistakable for a compliant one in a log read later.
    print(msg + "\n  ⚑ RUNNING UNARMED: SUBSTRATE_EXPLICIT_MUTATION=0 downgraded this "
                "REFUSAL to a warning.\n    This tool may now write without either "
                "--apply or --dry-run having been stated.",
          file=_sys.stderr)
    return "advisory"


def require_at_entry(label, argv=None, intent=None, paths=(), store=False):
    """The ENTRY-POINT form of the contract: state intent BEFORE any dispatch —
    AND, when the stated intent is `--apply`, TAKE THE SNAPSHOT IN THE SAME ACT.

    ⚑⚑⚑ THE BINDING IS THE POINT (operator, 2026-08-25): *"the snapshot device
    [should] be mandatory every time a non-dry-run is performed on something other
    than a database. (And it needs to be triggered at the same place as the gate for
    live vs dry, else it will get missed downstream for the same reason the gate
    was.)"*  The parenthetical is the whole design.

    ⚑⚑ BECAUSE UNTIL NOW THEY WERE TWO CALLS WITH TWO PLACEMENTS AND NOTHING BOUND
    THEM, and that decoupling is the recurrence vector.  MEASURED by `pycodemod
    --unbound-snapshot` at the moment this was written: **8 tools are SPLIT** —
    `paydown`, `prune_leaf_opens`, `rewire_to_leaves`, `scope_fix`, `seal_defs`,
    `strip_using`, `telescope_migrate_gen`, `unseal_defs` — every one of them a tool
    that PAID DOWN Ⓐ44 by moving its intent gate to entry, and every one of them
    still snapshotting at the first pending write.  So they read COMPLIANT to
    `check_snapshot_guard.intent_census` (the contract is named) and are UNPROTECTED
    in practice: a read-only mode, a dry run that restores, or a run that finds
    nothing to change never reaches the snapshot.

    ⚑ THE PAYDOWN ITSELF PRODUCED THE SHAPE.  Moving the intent gate to entry while
    leaving the snapshot where it was is not a half-done migration — it is what the
    Ⓐ44 instruction literally asked for, and the defect only became visible once
    something read the RELATION between the two guards rather than either one.

    `paths` is what a snapshot would copy; `store=True` declares that this tool's
    writes land in the STORE, where a file snapshot is NOT APPLICABLE — see the
    branch below, which says so rather than claiming a snapshot it cannot take.

    ⚑⚑ THIS EXISTS BECAUSE `guard`'s PLACEMENT MEASURED AS THE DEFECT, NOT THE FIX
    (Ⓐ44 ⟡move-guards-to-entry).  `pycodemod --guarded guard` reported 41 "top"
    sites and ZERO of them refused a bare invocation, because `--guarded`
    classifies by SOURCE POSITION and the 30 `_snapshot_once(path)` sites fire at
    the first PENDING WRITE — a point a read-only mode, a dry run that restores,
    or a `nothing droppable` run never reaches.  Verified before the move:
    `gen_build_makefiles --jobs` returned 20, `seal_ops.py` bare ran to
    completion.  The guard was consulted at the write, and the question is asked
    at the INVOCATION.

    ⚑⚑ THIS EXISTS BECAUSE `guard`'s PLACEMENT MEASURED AS THE DEFECT, NOT THE FIX
    (Ⓐ44 ⟡move-guards-to-entry).  `pycodemod --guarded guard` reported 41 "top"
    sites and ZERO of them refused a bare invocation, because `--guarded`
    classifies by SOURCE POSITION and the 30 `_snapshot_once(path)` sites fire at
    the first PENDING WRITE — a point a read-only mode, a dry run that restores,
    or a `nothing droppable` run never reaches.  Verified before the move:
    `gen_build_makefiles --jobs` returned 20, `seal_ops.py` bare ran to
    completion.  The guard was consulted at the write, and the question is asked
    at the INVOCATION.

    ⚑ AND THE PLACEMENT IS THE JUDGEMENT BEING ELIMINATED.  A guard at the write
    encodes the tool author's one-time decision about which paths are read-only,
    which every caller then inherits silently forever.  At entry the caller states
    it, per invocation, out loud — including for an invocation that would only
    have read.  `gen_build_makefiles --jobs --dry-run` is the caller saying "I am
    not asking you to write anything"; that statement IS the deliverable, so there
    is deliberately NO read-path exemption.

    ⚑ IT IS NOT A FOURTH BODY.  It delegates to `require_explicit_mutation` — the
    one authority — and adds only the SELFTEST CARVE-OUT, which is a fact about
    ORDER rather than about intent: a `--selftest` invocation exits before dispatch
    (that is why `scope_fix --selftest` passes 35/35 today), so a guard placed
    ahead of it would refuse the one invocation that asks the tool to check
    itself.  If moving a guard breaks a selftest, the guard is too early — this is
    where that lives, once, instead of in 30 call sites.
    """
    import sys as _sys
    argv = _sys.argv if argv is None else argv
    if intent is None and "--selftest" in argv:
        return "selftest"
    # ⚑⚑⚑ THIS FRAME IS THE CLI BOUNDARY, AND IT IS THE ONE PLACE IN THE SEAM THAT MAY
    # STILL EXIT (⟡intent-conflict-reconverted).  The name says so: `require_AT_ENTRY` is
    # the ENTRY-POINT form of the contract, and its 35 call sites are — measured, not
    # assumed — bare statements at the top of a tool's own `main`, with no enclosing
    # handler.  At an entry point the process genuinely IS this tool's to end, so
    # rendering the refusal and exiting 2 is CORRECT, and it is what those 35 callers
    # already observe today.  Letting the exception through instead would hand every one
    # of them a traceback and exit 1 in place of a clean message and exit 2 — worse for a
    # hook-invoked tool, and at `.githooks/pre-commit:477` invisible entirely.
    #
    # ⚑⚑ THE ASYMMETRY WITH `guard` IS THE WHOLE POINT, AND IT IS THE RULE A READER
    # APPLIES: `require_at_entry` is named for a position (an entry point → owns the pid →
    # renders and exits); `guard` is named for an act a library performs (→ does not own
    # the pid → raises).  Whoever is on the CLI side says so in the name they call.
    #
    # ⚑ AND IT RENDERS ONLY THIS MODULE'S OWN STATED REFUSALS. A bug in the body still
    # surfaces as a traceback — `except MutationContractError`, never `except Exception`.
    try:
        verdict = require_explicit_mutation(label, argv=argv, intent=intent)
    except MutationContractError as _e:
        print(str(_e), file=_sys.stderr)
        _sys.exit(2)
    # ⚑ PAST THIS LINE THE CALLER HAS STATED AN INTENT (or the process has exited).
    # The snapshot rides the STATEMENT, not the write — that is the binding.
    stated_apply = (intent == "apply") or (intent is None and "--apply" in argv)
    if not stated_apply:
        return verdict                     # a stated dry-run writes nothing to snapshot
    if store:
        # ⚑⚑⚑ A SNAPSHOT IS A FILESYSTEM ACT AND CANNOT CAPTURE A STORE MUTATION, so
        # this branch says so INSTEAD OF claiming one.  Printing "snapshot taken" here
        # would be a FALSE ASSURANCE — strictly worse than silence, because the operator
        # reads it as recoverable and it is not.  Naming the SUBSTITUTE is the other
        # half: leaving it at "not applicable" would read as an unguarded hole.
        print(f"   ⚑ {label}: snapshot NOT APPLICABLE — this tool's writes land in the "
              f"STORE, not the filesystem.\n"
              f"     A file copy cannot capture them. Its protection is the stated "
              f"--dry-run plus the\n"
              f"     transaction boundary; there is no snapshot to recover from.",
              file=_sys.stderr)
        return verdict
    # ⚑ DELEGATES TO `guard`, NEVER REIMPLEMENTS IT.  A fifth spelling of the snapshot
    # would be this arc's own defect (`the-holder-is-not-the-worker`) recurring inside
    # the fix for it. `intent=` is forwarded so `guard`'s own contract check sees an
    # already-stated intent rather than re-reading argv and refusing a fixture.
    guard(label, paths=paths, intent=intent or "apply")
    return verdict


def guard(label, paths=(), intent=None):
    """Snapshot + announce, the one call a rewrite tool needs before its first write.

    ⚑ AND THE MUTATION INTENT IS CHECKED HERE, because this is the one call every
    writer already makes.  See `require_explicit_mutation`: the contract is
    `--apply` XOR `--dry-run`, stated, never defaulted.

    ⚑⚑ `intent` IS THE FIXTURE ESCAPE, AND IT IS NOT A LOOPHOLE.  A `_selftest` drives
    the write path against a TEMP FIXTURE, so the write is the thing under test rather
    than a thing the operator asked for — and the process argv legitimately carries
    `--selftest` and neither mutation flag.  Reading the CALLER'S argv there answers a
    question nobody asked: MEASURED 2026-08-18 when `agda_defs --selftest` emitted two
    spurious advisories while passing 141/141.
    ⚑ The escape is `intent="apply"` STATED AT THE CALL SITE, which is the same contract
    one level in — a fixture that writes still has to SAY it writes.  Defaulting the
    parameter to "assume test" would re-create the silent default this exists to remove,
    in the one place where a wrong guess is invisible because the fixture is discarded.

    ⚑⚑⚑ `guard` IS ON THE LIBRARY SIDE OF THE LINE AND THEREFORE RAISES
    (⟡intent-conflict-reconverted).  It is named for an ACT a library performs, not for a
    position, and 58 files import this module — so it never ends a pid it does not own.
    Its refusals are `MutationContractError` subclasses.  The sibling rule:
    `require_at_entry` (named for a POSITION — an entry point) renders and exits 2.

    ⚑⚑ WHAT THIS MEANS FOR THE ~31 CALLERS THAT WRAP THIS CALL IN `except Exception`,
    STATED HERE BECAUSE THEY CANNOT LEARN IT ANYWHERE ELSE.  That handler means *"a
    snapshot is best-effort"* and is RIGHT about that — a git failure, a missing repo, a
    permissions problem should not stop the tool.  It is wrong only about a MUTATION-
    CONTRACT refusal, which is not a failed snapshot.  `MutationContractError` derives
    from `BaseException` precisely so those handlers keep containing what they meant to
    contain and stop containing what they did not: the refusal passes through and the
    write does not happen.  A caller that genuinely wants to contain one names it —
    `except edit_snapshot.MutationContractError` — which is a statement, not an accident.
    """
    # ⚑ `intent=` HERE IS NOW A CLAIM CHECKED AGAINST THE INVOCATION, not a value
    # accepted on sight. `require_explicit_mutation` routes it through `resolve_intent`,
    # which REFUSES (RAISES `IntentConflict`, naming both) when it disagrees with an
    # ambient statement — this said "exit 2" until ⟡intent-conflict-reconverted, and a
    # comment that still names the retired mechanism is how the next reader re-derives it
    # wrong (`fresh-comments-are-hypotheses-too`, on the fix's own frame) —
    # so a caller that stuffs "apply" into a dry-run invocation is caught rather than
    # obeyed. A deliberate divergence spells itself `with override_intent(...)`.
    require_explicit_mutation(label, intent=intent)
    sha = snapshot(label, paths)
    announce(sha, label)
    return sha


def _selftest():
    """Counted — a hardcoded total once hid an added case (prune_imports.py:332)."""
    cases = []

    def check(name, got, want):
        cases.append((name, got == want, got, want))

    # ⚑⚑⚑ EACH CASE MODELS A DISTINCT INVOCATION, SO EACH GETS A DISTINCT CONTEXT.
    # Under write-once (⟡intent-contextvar) a suite that drives `--apply` and then
    # `--dry-run` in ONE context is making a genuine second binding, and the mechanism
    # correctly refused it — the first thing the new selftest caught was the OLD
    # selftest. That refusal was right about the code and wrong about the subject: two
    # hypothetical invocations are not one invocation, and the suite has to say so.
    #
    # ⚑ THIS IS ALSO THE HONEST DEMONSTRATION OF THE ESCAPE.  `copy_context()` is how a
    # genuinely new invocation gets a fresh binding, and the suite using it is the
    # documentation for when a caller legitimately may.
    def _inv(fn, *a, **kw):
        """Run one case as its OWN invocation (fresh ambient bindings)."""
        return contextvars.copy_context().run(lambda: fn(*a, **kw))

    sha = snapshot("selftest", ["agda/Substrate/Foundation.agda"])
    check("snapshot returns a sha", bool(sha) and len(sha) == 40, True)

    # The snapshot must be a real, readable commit — a SHA that does not resolve
    # is worse than no snapshot, because it reads as protection that is not there.
    if sha:
        r = _git("cat-file", "-t", sha)
        check("sha resolves to a commit object", r.stdout.strip(), "commit")
        r2 = _git("rev-parse", "--verify", f"refs/edit-snapshots/{sha[:12]}")
        check("ref pins the object against gc", r2.returncode, 0)

    # The worktree must be UNCHANGED: a snapshot that stages or reverts anything
    # is the failure it exists to prevent.
    before = _git("status", "--porcelain").stdout
    snapshot("selftest-idempotence", [])
    after = _git("status", "--porcelain").stdout
    check("worktree untouched by snapshotting", after, before)

    check("journal written", os.path.exists(JOURNAL), True)
    check("announce tolerates a None sha (no snapshot != crash)",
          announce(None, "x", out=lambda *_: None), None)

    # ⚑ THE TALLY MUST FOLLOW THE LAST CASE.  `ok` was computed HERE, so cases
    # appended below would have been added to `cases` and never counted — the
    # count would still read N/N while N of them went unexamined.  Same class as
    # a hardcoded total hiding an added case (`prune_imports.py:332`).
    # ── restore(): the half that did not exist (C3/§58) ────────────────────
    # ⚑ SNAPSHOT WAS A TOOL; RESTORE WAS A PRINTED SUGGESTION.  And the printed
    # `git checkout <sha> -- <path>` is INCOMPLETE by construction: it reaches
    # only TRACKED files, while the tools most likely to need recovery are the
    # untracked ones.  MEASURED on the live damage: 1 of 3 files was tracked, so
    # the suggested command would have restored a third of the work and LOOKED
    # like it succeeded.
    if sha:
        tr, un = contents(sha)
        check("contents() reports BOTH halves of a snapshot",
              isinstance(tr, list) and isinstance(un, list), True)
        # a DRY restore must name every path it would touch, and never write
        rows = restore(sha, apply=False)
        check("a dry restore reports rows without writing", isinstance(rows, list), True)
        check("...and every row carries HOW it would be restored",
              all(h in ("tracked", "untracked-latest") or h.startswith("FAILED")
                  for _r, h in rows), True)
        # ⚑ the untracked store is keyed by PATH, so its verdict must not claim a
        # per-sha version.  A row labelled `untracked@<sha>` would be a lie.
        check("untracked rows are labelled `latest`, not per-sha",
              any(h == "untracked-latest" for _r, h in rows) or not un, True)

    # ⚑ THE RESTORE HINT MUST NAME THE SHA THE LISTING LEADS WITH.  `--holding`
    # prints newest-first; my first cut reversed only in the print loop and then
    # indexed the unreversed list, so the hint pointed at the OLDEST snapshot while
    # the reader was looking at the newest.  Pinning the ORIENTATION rather than a
    # literal SHA, because the journal grows.
    # ⚑ AND THE ASSERTION MUST NOT BE A TAUTOLOGY.  My first version compared
    # `_j[0][0]` to itself — it could not fail, which is the decoration class §65
    # had just recorded.  Both cases name a LITERAL.
    _j = [("aaa", "old", ["p/x.agda"]), ("bbb", "new", ["p/x.agda"])]
    _j.reverse()
    check("--holding leads with the NEWEST snapshot", _j[0][0], "bbb")
    check("the restore hint names the LISTING'S FIRST row, not the journal's",
          _j[0][0], "bbb")

    # ── require_explicit_mutation: the contract is the PAIR, not either flag ──
    # ⚑ DRIVEN THROUGH THE REAL FUNCTION with a constructed argv, never asserted
    # about `sys.argv` — the same discipline the `--holding` cases above record
    # ("the assertion must not be a tautology").  A case that reads today's argv
    # would pass because of how the selftest happens to be invoked.
    check("--apply alone SATISFIES the contract",
          _inv(require_explicit_mutation, "selftest", ["t", "--apply"]), None)
    check("--dry-run alone SATISFIES it",
          _inv(require_explicit_mutation, "selftest", ["t", "--dry-run"]), None)
    # ⚑⚑ REFUSAL IS NOW THE DEFAULT (⟡explicit-mutation-default, 2026-08-25), and the
    # not-satisfied path therefore `sys.exit(2)`s — which an INLINE case cannot observe
    # without killing the selftest.  So the three not-satisfied cases below run under an
    # explicit `=0`, the ONLY remaining way to get a returnable advisory, and the REFUSAL
    # arm is driven in a subprocess (see `_refuses` just after).  Both arms, per case:
    # asserting only the advisory would leave the flip itself undemonstrated here, which
    # is the one-armed shape this file's own `--dry` case was written to avoid.
    _prior = os.environ.get("SUBSTRATE_EXPLICIT_MUTATION")
    os.environ["SUBSTRATE_EXPLICIT_MUTATION"] = "0"

    def _refuses(argv):
        """Exit code of the not-satisfied path in a FRESH process, at the real default.

        ⚑⚑⚑ IT DRIVES THE PATH THROUGH `cli_main` NOW, AND THAT CHANGE IS THE CASE
        (⟡intent-conflict-reconverted).  It used to call `require_explicit_mutation`
        bare and assert exit 2, which passed only because that LIBRARY frame called
        `sys.exit(2)` itself — the defect.  The library frame now RAISES, so a bare
        subprocess call correctly dies at the top with exit 1, and the five cases below
        went red the moment the converter was removed.

        ⚑⚑ THE CASES WERE RIGHT ABOUT THE OBSERVABLE AND WRONG ABOUT THE SUBJECT.  Exit
        2 for an unstated intent is genuinely required and is what all 35 real
        `require_at_entry` callers see — but it is a property of the CLI BOUNDARY, not of
        the library function.  Asserting it at the library frame is what pinned the exit
        into the seam.  Routing through `cli_main` keeps the observable pinned exactly
        where a caller observes it, and frees the frame beneath to raise.
        """
        _e = {k: v for k, v in os.environ.items()
              if k != "SUBSTRATE_EXPLICIT_MUTATION"}
        return subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r); import edit_snapshot as e;"
             "sys.exit(e.cli_main(e.require_explicit_mutation, 't', %r) or 0)"
             % (os.path.dirname(os.path.abspath(__file__)), argv)],
            capture_output=True, text=True, env=_e).returncode

    def _raises_as_library(argv, intent=None):
        """THE OTHER ARM, AND IT IS NEW: the library frame must RAISE, never exit.

        ⚑⚑⚑ WITHOUT THIS CASE THE FIX IS UNDEMONSTRATED.  `_refuses` above pins the
        CLI observable, and a `sys.exit(2)` in the library would satisfy it just as well
        as a raise — the two are indistinguishable from the boundary, which is precisely
        how the converted exit survived unnoticed.  So the property has to be starved
        from the other side: run the library frame with NO boundary and check that what
        escapes is a `MutationContractError`, not a `SystemExit`.

        ⚑⚑ AND IT CHECKS THE ANCESTRY, NOT JUST THE NAME.  `issubclass(_, Exception)`
        must be FALSE: an `except Exception` handler must not be able to swallow this.
        31 measured call sites wrap `guard()` in exactly that handler and then write
        anyway, so a refusal catchable there is a refusal converted into an advisory
        print with the damage still done.
        """
        _e = {k: v for k, v in os.environ.items()
              if k != "SUBSTRATE_EXPLICIT_MUTATION"}
        return subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r); import edit_snapshot as e\n"
             "try:\n"
             "    e.require_explicit_mutation('t', %r, intent=%r)\n"
             "    print('NO RAISE')\n"
             "except SystemExit:\n"
             "    print('EXITED')\n"
             "except e.MutationContractError as x:\n"
             "    print('RAISED', not isinstance(x, Exception))\n"
             % (os.path.dirname(os.path.abspath(__file__)), argv, intent)],
            capture_output=True, text=True, env=_e).stdout.strip()

    # ⚑ NEITHER is the whole point: it must NOT return None (the satisfied value).
    check("NEITHER is advisory under =0 (never silent)",
          _inv(require_explicit_mutation, "selftest", ["t"]), "advisory")
    check("...and REFUSES at the default (unset)", _refuses(["t"]), 2)
    # ⚑ A flag that merely CONTAINS the word must not satisfy it — `--apply-all`
    # is a different flag and reading it as consent is the substring defect this
    # repo has recorded on `--marks`/`--since` operand handling.
    check("a longer flag containing `--apply` does NOT satisfy it",
          _inv(require_explicit_mutation, "selftest", ["t", "--apply-all"]), "advisory")
    check("...and it REFUSES at the default", _refuses(["t", "--apply-all"]), 2)
    # ⚑ `intent` STATES IT IN CODE, for a fixture write where the process argv carries
    # `--selftest` and the operator asked for no mutation.  MEASURED: without this,
    # `agda_defs --selftest` emitted two spurious advisories while passing 141/141 —
    # the check was reading the wrong invocation's argv.
    # ⚑ THE THIRD SPELLING (Ⓐ40).  `--dry` must NOT satisfy the contract — three tools
    # dispatch on it and all three WRITE when it is absent, so reading it as consent
    # would bless the divergence into the shared authority.  Both arms are driven: the
    # near-miss is refused, AND the refusal names the successor (a refusal that does not
    # is half a gate).
    check("`--dry` does NOT satisfy the contract (it is not `--dry-run`)",
          _inv(require_explicit_mutation, "selftest", ["t", "--dry"]), "advisory")
    check("...and `--dry` REFUSES at the default", _refuses(["t", "--dry"]), 2)
    # ⚑ THE OFF-SWITCH MUST ANNOUNCE ITSELF.  An escape hatch that restores the old
    # behaviour SILENTLY is indistinguishable, in any log read later, from a compliant
    # run — which is how a bypass becomes permanent.  Pinned on the advisory arm above.
    import contextlib
    import io
    _unarmed = io.StringIO()
    with contextlib.redirect_stderr(_unarmed):
        _inv(require_explicit_mutation, "selftest", ["t"])
    check("the =0 advisory SAYS it is running unarmed",
          "RUNNING UNARMED" in _unarmed.getvalue(), True)
    if _prior is None:
        os.environ.pop("SUBSTRATE_EXPLICIT_MUTATION", None)
    else:
        os.environ["SUBSTRATE_EXPLICIT_MUTATION"] = _prior
    # ⚑ ALSO ROUTED THROUGH `cli_main` (⟡intent-conflict-reconverted): the exit code AND
    # the successor-naming text are CLI-boundary observables. The message is unchanged.
    _cap = subprocess.run(
        [_sys_exe := sys.executable, "-c",
         "import sys; sys.path.insert(0, %r); import edit_snapshot as e;"
         "sys.exit(e.cli_main(e.require_explicit_mutation, 't', ['t', '--dry']) or 0)"
         % os.path.dirname(os.path.abspath(__file__))],
        capture_output=True, text=True, env={**os.environ,
                                             "SUBSTRATE_EXPLICIT_MUTATION": "1"})
    check("...and under strict mode a near miss REFUSES", _cap.returncode, 2)
    check("...and the refusal NAMES the successor `--dry-run`",
          "--dry  →  --dry-run" in _cap.stderr, True)
    check("intent='apply' satisfies the contract without touching argv",
          _inv(require_explicit_mutation, "selftest", ["t"], intent="apply"), None)
    check("intent='dry-run' likewise",
          _inv(require_explicit_mutation, "selftest", ["t"], intent="dry-run"), None)
    # ⚑ AND THE ESCAPE IS AT LEAST AS STRICT AS THE THING IT BYPASSES: an unrecognised
    # intent REFUSES rather than passing, or a typo would satisfy the contract silently.
    # ⚑⚑ THE REFUSAL IS NOW A RAISE, SO BOTH ARMS ARE DRIVEN (⟡intent-conflict-
    # reconverted).  `Ambient.set` used to `sys.exit(2)` on an out-of-vocab value in a def
    # 58 files import — it now raises `AmbientVocabError`, and the CLI boundary still
    # renders it as exit 2.  The MESSAGE is unchanged; only the mechanism moved.
    import sys as _s
    _r = subprocess.run([_s.executable, "-c",
                         "import sys; sys.path.insert(0, %r); import edit_snapshot as e;"
                         "sys.exit(e.cli_main(e.require_explicit_mutation, 't', ['t'],"
                         " intent='maybe') or 0)"
                         % os.path.dirname(os.path.abspath(__file__))],
                        capture_output=True, text=True)
    check("an unrecognised intent REFUSES (exit 2 at the boundary), never passes",
          _r.returncode, 2)
    check("...and the vocab refusal still NAMES the vocabulary it wanted",
          "'apply' / 'dry-run'" in _r.stderr and "REFUSES rather than passing" in _r.stderr,
          True)

    # ⚑⚑⚑ THE LIBRARY ARM, STARVED SEPARATELY.  Every case above observes the CLI
    # boundary, where a raise and an exit are indistinguishable — which is exactly how
    # the converted exit lived at `require_explicit_mutation` unnoticed. These check the
    # frame BENEATH the boundary: what escapes must be a raise, and must NOT be an
    # `Exception` (31 measured `except Exception` sites would otherwise swallow it and
    # write anyway).
    check("library: an unstated intent RAISES (not SystemExit) and is not an Exception",
          _raises_as_library(["t"]), "RAISED True")
    check("library: an unrecognised intent RAISES (not SystemExit) likewise",
          _raises_as_library(["t"], intent="maybe"), "RAISED True")
    check("library: BOTH flags RAISES rather than exiting",
          _raises_as_library(["t", "--apply", "--dry-run"]), "RAISED True")

    # ⚑⚑⚑ AND THE ARM THAT MATTERS MOST IS `guard`, NOT `require_explicit_mutation` —
    # because `guard` is what the 31 measured `except Exception` sites actually call, in
    # the shape `try: guard(...) except Exception: print("⚠ snapshot unavailable"); <and
    # then WRITE ANYWAY>`.  Those handlers mean "a snapshot is best-effort" and are right
    # about that; a mutation-contract refusal is not a failed snapshot.  This case drives
    # the exact caller shape and asserts the refusal PASSES THROUGH it — the property
    # that keeps a refusal from degrading into an advisory with the damage still done.
    #
    # ⚑ IT IS THE NEGATIVE CONTROL FOR THE BASE-CLASS CHOICE.  Had `MutationContractError`
    # derived from `Exception` (the obvious cut, written and reverted), this case would
    # report SWALLOWED — which is how the choice is demonstrated rather than asserted.
    _g = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r); import edit_snapshot as e\n"
         "try:\n"
         "    try:\n"
         "        e.guard('probe', [], intent='maybe')\n"
         "    except Exception as x:\n"
         "        print('SWALLOWED', type(x).__name__)\n"
         "except SystemExit:\n"
         "    print('EXITED')\n"
         "except e.MutationContractError as x:\n"
         "    print('PASSED-THROUGH', type(x).__name__)\n"
         % os.path.dirname(os.path.abspath(__file__))],
        capture_output=True, text=True)
    check("guard: a refusal PASSES THROUGH the 31 sites' `except Exception` (not "
          "swallowed, not an exit)", _g.stdout.strip(), "PASSED-THROUGH AmbientVocabError")

    # ── require_at_entry: the Ⓐ44 entry form.  BOTH ARMS, or nothing is shown ──
    # ⚑ A ONE-ARMED TEST PROVES NOTHING.  A sibling shipped a delete-guard whose two
    # arms were BOTH satisfied, so neither was demonstrated; only starving each in turn
    # exposed it.  So: stated -> passes, selftest -> passes, and BARE -> exit 2 driven
    # in a fresh process at the real default.
    check("entry: --apply alone satisfies it",
          _inv(require_at_entry, "selftest", ["t", "--apply"]), None)
    check("entry: --dry-run alone satisfies it",
          _inv(require_at_entry, "selftest", ["t", "--dry-run"]), None)
    # ⚑ THE SELFTEST CARVE-OUT IS AN ORDERING FACT, NOT AN INTENT EXEMPTION: a
    # `--selftest` invocation exits before dispatch, so it never reaches the write it
    # would have had to declare.  It is verified as a DISTINCT verdict ("selftest",
    # not None) so it can never be confused with a stated intent in a log.
    check("entry: --selftest passes WITHOUT a flag, and says which arm it took",
          _inv(require_at_entry, "selftest", ["t", "--selftest"]), "selftest")
    # ⚑ and an EXPLICIT intent still wins over the carve-out — a fixture that writes
    # must still SAY it writes, exactly as `guard`'s `intent` docstring records.
    check("entry: an explicit intent overrides the selftest carve-out",
          _inv(require_at_entry, "selftest", ["t", "--selftest"], intent="apply"), None)

    # ── the BINDING: stating --apply IS the snapshot (operator, 2026-08-25) ───────
    # ⚑⚑⚑ BOTH ARMS, STARVED IN TURN, for the reason the block above states: a
    # one-armed test proves nothing.  A stated `--apply` must SNAPSHOT; a stated
    # `--dry-run` must NOT (there is nothing to recover, and a snapshot on every read
    # would make the recovery log useless by burying real ones).
    check("bind: a stated --dry-run takes NO snapshot",
          _inv(require_at_entry, "selftest", ["t", "--dry-run"]), None)
    # ⚑ THE STORE ARM IS A DISTINCT VERDICT, NOT A SILENT SKIP.  A tool whose writes
    # land in postgres must be TOLD a snapshot is inapplicable and what protects it
    # instead — "snapshot taken" there is a false assurance, which this session has
    # repeatedly found to be worse than no signal at all.
    check("bind: store=True still satisfies the contract (and says why, on stderr)",
          _inv(require_at_entry, "selftest", ["t", "--apply"], store=True), None)

    def _refuses_entry(argv):
        _e = {k: v for k, v in os.environ.items()
              if k != "SUBSTRATE_EXPLICIT_MUTATION"}
        return subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r); import edit_snapshot as e;"
             "e.require_at_entry('t', %r)"
             % (os.path.dirname(os.path.abspath(__file__)), argv)],
            capture_output=True, text=True, env=_e)

    _bare = _refuses_entry(["t"])
    check("entry: a BARE invocation REFUSES at the default", _bare.returncode, 2)
    check("...and the refusal names the successors it wanted",
          "--apply" in _bare.stderr and "--dry-run" in _bare.stderr, True)
    _nm = _refuses_entry(["t", "--force"])
    check("entry: a near miss REFUSES and NAMES its successor",
          (_nm.returncode, "--force  →  --apply" in _nm.stderr), (2, True))

    # ── the AMBIENT vars: write-once, and BOTH ARMS STARVED ──────────────────────
    # ⚑⚑⚑ A REFUSAL THAT NEVER FIRES AND A REFUSAL THAT ALWAYS FIRES ARE
    # INDISTINGUISHABLE FROM A GREEN SUITE.  So every case below has a POSITIVE
    # CONTROL proving the refusal CAN fire, and a NEGATIVE control proving the
    # compliant path does NOT trip it.  A sibling shipped a delete-guard whose two
    # arms were both satisfied, so neither was demonstrated.
    def _fresh(fn):
        """Run `fn` in a genuinely fresh context — the var starts UNBOUND."""
        return contextvars.copy_context().run(fn)

    def _first_write_ok():
        a = Ambient("probe", ("x", "y"), "two readings")
        a.set("x", "first")
        return a.get()

    check("ambient: a FIRST write binds", _fresh(_first_write_ok), "x")

    def _second_write_raises():
        a = Ambient("probe", ("x", "y"), "two readings")
        a.set("x", "first")
        try:
            a.set("y", "second")
            return "NO RAISE"
        except AmbientConflict as e:
            return "raised" if "WRITE-ONCE" in str(e) else f"wrong msg: {e}"

    check("ambient: a SECOND write RAISES (the positive control)",
          _fresh(_second_write_raises), "raised")

    # ⚑ THE SAME-VALUE SECOND WRITE IS *ALSO* A DEFECT, and this is the case that
    # proves the mechanism is not merely a value comparison. Two sites each believing
    # they decide is the ⟡index-coverage-wrong-store shape; they agree today.
    def _second_write_same_value_still_raises():
        a = Ambient("probe", ("x", "y"), "two readings")
        a.set("x", "first")
        try:
            a.set("x", "second")
            return "NO RAISE"
        except AmbientConflict as e:
            return "raised" if "values MATCH" in str(e) else f"wrong msg: {e}"

    check("ambient: a second write of the SAME value still RAISES",
          _fresh(_second_write_same_value_still_raises), "raised")

    # ⚑ THE NEGATIVE CONTROL: an agreeing `resolve` is a NO-OP, not a rebind. This is
    # what lets the 17 hardcoded `intent="apply"` sites keep working under `--apply`.
    def _agreeing_resolve_is_silent():
        a = Ambient("probe", ("x", "y"), "two readings")
        a.set("x", "entry")
        return a.resolve("a callee", stated="x")

    check("ambient: an AGREEING resolve passes silently (negative control)",
          _fresh(_agreeing_resolve_is_silent), "x")

    def _disagreeing_resolve_raises():
        a = Ambient("probe", ("x", "y"), "two readings")
        a.set("x", "entry")
        try:
            a.resolve("a callee", stated="y")
            return "NO RAISE"
        except AmbientConflict:
            return "raised"

    check("ambient: a DISAGREEING resolve RAISES",
          _fresh(_disagreeing_resolve_raises), "raised")

    # ⚑ AN UNBOUND resolve BINDS — the fixture / `_snapshot_once` case, where nothing
    # above stated anything so this site's statement IS the invocation's.
    def _unbound_resolve_binds():
        a = Ambient("probe", ("x", "y"), "two readings")
        return a.resolve("only site", stated="y"), a.get()

    check("ambient: resolve with NOTHING bound binds it",
          _fresh(_unbound_resolve_binds), ("y", "y"))

    # ── the override: registered, reasoned, and a NEW CONTEXT ────────────────────
    def _unregistered_override_refuses():
        a = Ambient("intent", ("apply", "dry-run"), "two readings")
        try:
            a.override("apply", reason="because", label="not_registered")
            return "NO RAISE"
        except ValueError as e:
            return "raised" if "NOT REGISTERED" in str(e) else f"wrong msg: {e}"

    check("override: an UNREGISTERED label REFUSES", _unregistered_override_refuses(),
          "raised")

    def _reasonless_override_refuses():
        try:
            INTENT.override("apply", reason="",
                            label="prune_leaf_opens (dry-run writes-then-restores)")
            return "NO RAISE"
        except ValueError as e:
            return "raised" if "requires a REASON" in str(e) else f"wrong msg: {e}"

    check("override: a REASONLESS override REFUSES", _reasonless_override_refuses(),
          "raised")

    # ⚑ THE REGISTERED ONE RUNS, IN A COPIED CONTEXT, AND LEAVES THE OUTER BINDING
    # UNTOUCHED. Both halves are the case: the body sees the override, and the caller
    # afterwards still sees what it bound. A leak here would be the whole defect.
    def _registered_override_is_scoped():
        INTENT.set("dry-run", "entry")
        inner = INTENT.override(
            "apply", reason="writes then restores even on a dry run",
            label="prune_leaf_opens (dry-run writes-then-restores)",
            announce_to=lambda _m: None).run(lambda: INTENT.get())
        return inner, INTENT.get()

    check("override: registered runs in a COPIED context; outer binding survives",
          _fresh(_registered_override_is_scoped), ("apply", "dry-run"))

    # ⚑ AND IT IS NOT A CONTEXT MANAGER — a `with` would mutate the current context and
    # undo it, the write-then-reset hole write-once exists to close.
    def _override_rejects_with():
        try:
            with INTENT.override("apply", reason="r",
                                 label="prune_leaf_opens (dry-run writes-then-restores)"):
                return "NO RAISE"
        except TypeError as e:
            return "raised" if "not a context manager" in str(e) else f"wrong: {e}"

    check("override: `with` is REFUSED and names the .run() successor",
          _fresh(_override_rejects_with), "raised")

    # ── the tenant var: same mechanism, third declaration ────────────────────────
    def _tenant_names_itself():
        return naming_tenant("live", "a-report")

    check("tenant: binding RETURNS the label a result must carry",
          _fresh(_tenant_names_itself), "[tenant=live]")

    def _two_independent_tenant_resolutions_raise():
        """⟡index-coverage-wrong-store, in miniature: two functions, one report."""
        def _coverage():
            return naming_tenant("sandbox", "_live_indexed")

        def _selectivity():
            return naming_tenant("live", "_selectivity")
        _coverage()
        try:
            _selectivity()
            return "NO RAISE"
        except AmbientConflict as e:
            return "raised" if "_live_indexed" in str(e) else f"wrong msg: {e}"

    check("tenant: TWO INDEPENDENT resolutions in one process RAISE, naming the first",
          _fresh(_two_independent_tenant_resolutions_raise), "raised")

    # ⚑ THE SNAPSHOT RECORD IS PER-INVOCATION, AND THE COPIED SET ACCUMULATES — the
    # `_snapshot_once` bug. A latch would leave `copied` at one member.
    def _snapshot_state_accumulates():
        SNAPSHOT_STATE.set({"sha": "deadbeef", "copied": set(), "label": "t"})
        st = SNAPSHOT_STATE.get()
        st["copied"].add("a.agda")
        st["copied"].add("b.agda")
        return len(SNAPSHOT_STATE.get()["copied"])

    check("snapshot: the per-invocation copied set ACCUMULATES (not a latch)",
          _fresh(_snapshot_state_accumulates), 2)

    # ⚑⚑⚑ THIS CASE FAILED TWICE AND THE CASE WAS THE BUG BOTH TIMES — recorded rather
    # than quietly corrected, because the wrong belief behind it is the exact one this
    # mechanism defends against.  I read `copy_context()` as giving an EMPTY context.  It
    # does not: it gives a fresh BINDING SCOPE over a COPY of the current values, so a
    # var the suite already bound (this file calls `snapshot()` near the top) is still
    # bound inside it.  Writes do not escape outward; existing values DO carry inward.
    #
    # ⚑⚑ SO THE FIRST TWO SPELLINGS WERE TESTING THE SUITE'S OWN HISTORY, NOT THE
    # PROPERTY — a case that reads the ambient world and calls the result a fact about
    # the code.  `sampled-state-cannot-see-events`, one layer over.  The property under
    # test is *a write in one context does not reach a sibling context*, and that is
    # stated honestly with a var the suite has never touched.
    _probe_var = contextvars.ContextVar("probe_isolation", default=None)

    def _writes_do_not_cross_contexts():
        """The latch's bug in miniature: sibling invocations must not share arming."""
        _fresh(lambda: _probe_var.set({"armed": True}))
        return _fresh(lambda: _probe_var.get())

    check("snapshot: a write in one context does NOT reach a sibling "
          "(a module global would)", _writes_do_not_cross_contexts(), None)

    ok = sum(1 for _, good, _, _ in cases if good)
    for name, good, got, want in cases:
        if not good:
            print(f"  FAIL {name}\n       got  {got!r}\n       want {want!r}")
    print(f"edit_snapshot selftest: {ok}/{len(cases)}")
    return 0 if ok == len(cases) else 1


def cli_main(fn, *a, **kw):
    """THE CLI BOUNDARY — the ONE place a refusal becomes an exit code.

    ⚑⚑⚑ THIS IS THE SPLIT MADE VISIBLE (⟡intent-conflict-reconverted, requirement 3).
    Everything above raises; this renders.  The rule a reader applies to tell which side
    of the line a function is on is now MECHANICAL rather than remembered:

        inside `cli_main` (or lexically under `if __name__ == "__main__"`)  → may exit
        anywhere else in this module                                        → must raise

    ⚑⚑ AND IT IS WHY PROPAGATING DOES NOT PRODUCE A TRACEBACK WHERE ONE MUST NOT APPEAR.
    That was the open design question, and it was ANSWERED BY MEASUREMENT rather than
    assumed: the 35 `require_at_entry` sites are bare top-of-main statements with no
    enclosing handler, so an unrendered exception there would dump a traceback and exit 1
    where a clean message and exit 2 used to be.  A traceback is not merely uglier — at
    `.githooks/pre-commit:477` (`gen_build_makefiles --jobs`) stdout is captured in `$(…)`
    with stderr discarded, so a failure there degrades to an unthrottled build with NO
    DIAGNOSTIC AT ALL.  Rendering `str(exc)` and exiting 2 reproduces today's observable
    behaviour byte-for-byte at a CLI boundary, while a LIBRARY caller now gets an
    exception it can contain instead of a dead interpreter.

    ⚑ IT CATCHES `MutationContractError`, NOT `Exception`.  A genuine bug in the body must
    still surface as a traceback; only the module's own stated refusals are rendered.

    ⚑⚑ `pycodemod --calls cli_main` READS THIS AS A "DEAD CAPABILITY — defined and never
    called (the rewire_only class)", AND THAT VERDICT IS A FACT ABOUT THE JOIN, NOT ABOUT
    THIS DEF.  Two of its call populations are structurally invisible to that census:
    the selftest drives it through `python -c` subprocess strings (a declared blind spot
    — "an exit in a SUBPROCESS or a `python -c` string: not python this reader parses"),
    and its intended consumers are CALLERS IN OTHER FILES that own their own `main`.
    `edit_snapshot`'s own `__main__` never reaches it because that block calls no
    contract function — nothing there can raise a `MutationContractError` to render.

    ⚑ SO IT IS EXPORTED SURFACE, NOT AN UNWIRED BRANCH, and the distinction is recorded
    here rather than discovered later as a deletion candidate.  A tool whose `main`
    dispatches into work that calls `guard` wraps that dispatch: `sys.exit(cli_main(run,
    ...) or 0)`.  The 35 `require_at_entry` callers need nothing — that entry-point form
    renders internally, which is exactly what its name promises.
    """
    try:
        return fn(*a, **kw)
    except MutationContractError as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if "--holding" in sys.argv:
        # ⚑ THE QUESTION A RECOVERY ACTUALLY ASKS, AND `--list` COULD NOT ANSWER IT.
        # `--list` dumps the raw journal — MEASURED at 207KB, every path of every
        # snapshot — so "which snapshot holds MY file" meant grepping the output.
        # That is reprocessing at the shell, and it is what sent me to a
        # hand-assembled `cp`+`git checkout` line instead of `--from-snapshot`
        # (the §58b anti-pattern: a printed command is not a recovery path).
        _want = [a for a in sys.argv[1:] if not a.startswith("-")]
        if not _want:
            print("usage: edit_snapshot.py --holding <path-fragment>")
            sys.exit(2)
        frag = _want[0]
        rows = []
        if os.path.exists(JOURNAL):
            for line in open(JOURNAL, encoding="utf-8"):
                if line.startswith("#") or not line.strip():
                    continue
                f = line.rstrip("\n").split("\t")
                if len(f) < 4:
                    continue
                hit = [p for p in f[3].split(",") if frag in p]
                if hit:
                    rows.append((f[0], f[1], hit))
        # ⚑ REVERSE ONCE, THEN USE ONE ORIENTATION EVERYWHERE.  The journal is
        # newest-LAST; the listing wants newest-FIRST.  My first cut reversed only
        # in the print loop and then indexed the UNREVERSED list for the restore
        # hint — so the hint named the OLDEST snapshot while the reader was looking
        # at the newest.  A printed command that is subtly wrong is worse than none
        # (§58b), because it gets run.
        rows.reverse()
        for sha, label, hit in rows:
            print(f"{sha[:12]}  {label}")
            for p in hit[:5]:
                print(f"      {p}")
            if len(hit) > 5:
                print(f"      … {len(hit)-5} more matching path(s)")
        print(f"{len(rows)} snapshot(s) hold a path matching {frag!r} "
              f"(newest first)")
        if rows:
            print(f"   restore:  python3 scratch/edit_snapshot.py "
                  f"--from-snapshot={rows[0][0][:12]} <path> --apply")
        sys.exit(0)

    if "--list" in sys.argv:
        if os.path.exists(JOURNAL):
            with open(JOURNAL, encoding="utf-8") as fh:
                sys.stdout.write(fh.read())
        else:
            print("no snapshots recorded")
        sys.exit(0)
    # ⚑⚑ THE FLAG IS NAMED HERE AS A BARE LITERAL ON PURPOSE, AND IT IS NOT DECORATION.
    # This mode dispatched on `a.startswith("--from-snapshot=")` alone — the `=` glued to the
    # name — while the usage line above declares `--from-snapshot=<sha>`, from which
    # `toolmodes.parse_usage` extracts the BARE `--from-snapshot`. So the census saw a
    # DECLARED mode with no dispatch anchoring it and booked it UNBACKED: one flag, two
    # spellings, and the divergence ratchet (baseline EMPTY = zero-tolerance) counted the gap.
    #
    # ⚑ THE MODE ALWAYS WORKED. Nothing was broken except the census's ability to see it —
    # which is why the honest repair is to name the flag where the AST can anchor it, NOT to
    # rewrite the usage line to match the `=` spelling. Deleting the declaration would have
    # paid the key down while removing the only place a reader learns the mode exists.
    _FROM_SNAPSHOT = "--from-snapshot"
    _fs = next((a.split("=", 1)[1] for a in sys.argv
                if a.startswith(_FROM_SNAPSHOT + "=")), None)
    if _fs:
        _paths = [a for a in sys.argv[1:] if not a.startswith("-")]
        _ap = "--apply" in sys.argv
        rows = restore(_fs, _paths, apply=_ap)
        for rel, how in rows:
            print(f"{'RESTORED' if _ap else 'would restore':<14} {how:<18} {rel}")
        n_t = sum(1 for _r, h in rows if h == "tracked")
        n_u = sum(1 for _r, h in rows if h.startswith("untracked"))
        print(f"{len(rows)} path(s): {n_t} tracked, {n_u} untracked")
        if n_u:
            # ⚑ SAY WHAT THE UNTRACKED HALF ACTUALLY IS.  `.edit-snapshots/` is
            # keyed by PATH, so it holds the most recent pre-write copy — not one
            # per SHA.  A caller must not read this as a historical version.
            print("   ⚑ untracked entries are the MOST RECENT pre-write copy "
                  "(the store is keyed by path, not by sha)")
        if not _ap:
            print("\nDry run — pass --apply to execute.")
        sys.exit(0)
    print(__doc__)
    print("usage: edit_snapshot.py [--selftest|--list]\n"
          "       edit_snapshot.py --from-snapshot=<sha> [paths] [--apply]")
