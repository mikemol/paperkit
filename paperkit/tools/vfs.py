#!/usr/bin/env python3
"""⟡vfs — ONE read/write seam over the working tree AND git history.

WHY THIS EXISTS: three hand-rolled implementations of "read this file as it was at
a revision" disagreed about what ABSENCE means, and the disagreement is measured:

  agda_defs.at_revision   `(None, path)` when `returncode != 0` — which collapses
                          ABSENT with bad-rev, not-a-repo, and git-not-installed
                          into ONE `None`.  A caller cannot tell "this file is new
                          in the working tree" from "you typed the sha wrong".
  scope_source._head_text `else ""` — collapses ABSENT into EMPTY.  That is the
                          INVERSION `at_revision`'s own docstring warns about: it
                          was written after a `git checkout` used to *look at*
                          history destroyed working copies.
  scope_fix.seed_map      a third path strategy (`--show-prefix`).

⚑ THE THREE ANSWERS ARE DISTINCT AND THE DISTINCTION IS THE PRODUCT:

  PRESENT  a blob is there.  `.data` is `bytes`, possibly `b""`.
  ABSENT   not at that source.  The one legitimate "no".
  BROKEN   bad rev, not a repo, decode failure, permission.  NEVER silently a miss.

This is `ratchet.BaselineState`'s discipline applied to file reads — see `Presence`,
which is modelled on it deliberately, down to `of()` REFUSING an unknown name rather
than defaulting.  A lookup that fell back to a default would re-create the bug.

⚑⚑ AND THE pygit2 EXCEPTION SPLIT IS *NOT* INHERITED — IT IS DESIGNED HERE.
The brief that commissioned this module said `FileNotFoundError` vs `KeyError` came
free from pygit2 and the adapter merely had to avoid re-collapsing it.  MEASURED
2026-08-25, that is false:

    repo.revparse_single("nosuchrev-zzz")  -> KeyError
    tree["nope.txt"]                       -> KeyError

pygit2 raises the SAME exception type for a bad revision and for a missing path.
Trusting the "inherited" split would have reported every typo'd sha as ABSENT —
precisely the collapse this module exists to remove, reintroduced in its own
foundation.  So `Rev.resolve()` resolves the revision EAGERLY and separately: by the
time a tree lookup runs, the rev is known-good, and only then does `KeyError` mean
ABSENT.  The split is a property of the ORDER OF OPERATIONS here, not of the library.

⚑ PATH TRAVERSAL IS STRUCTURALLY ABSENT ON THE Rev PATH, and this is pygit2's doing
rather than a check of ours.  `tree["../etc/passwd"]` and `tree["/etc/passwd"]` are
both plain `KeyError`: the lookup walks the git TREE OBJECT part-by-part, so there is
no filesystem path to escape from.  There is nothing to sanitise because there is
nothing to sanitise it against.  WorkingTree reads are ordinary filesystem reads and
carry no such guarantee — do not read the Rev property as covering both.

USAGE

    from vfs import read, read_text, write, Presence, WorkingTree, Rev

    r = read("agda/Substrate/Foundation.agda", Rev("HEAD"))
    if r.presence is Presence.PRESENT:  use r.data          # bytes, maybe b""
    elif r.presence is Presence.ABSENT: ...                 # legitimately not there
    else:                               raise r.error       # BROKEN — never a miss

`read` RETURNS a verdict rather than raising, because ABSENT is a normal answer that
callers branch on.  BROKEN carries its cause in `.error`; `require()` turns it into a
raise for callers that want the exception.
"""

# selftest-requires: pygit2
#
# ⚑ THE SUITE DECLARES ITS OWN DEPENDENCY, which is `run_selftests`' existing
# mechanism (`REQUIRES`, discovered from the file — never a roster in the runner).
# Before this line `vfs` was one of the 87 suites of 104 that declare NEITHER a
# dependency nor a tenant, and that mode's own caveat is the point: it "cannot tell
# 'needs nothing' from 'never asked'". This suite NEEDS something, so silence here
# was the second reading masquerading as the first.
#
# ⚑⚑ AND THIS IS THE DECLARATION THAT REACHES THE PRE-COMMIT PATH. `pyproject.toml`
# declares pygit2 for the PROJECT ENVIRONMENT; this declares it for the SUITE, and
# the two are not redundant because the hook's `tool selftests` gate runs suites as
# a subprocess whose interpreter is whatever `python3` resolved to. The manifest
# fixes `uv sync`; the pragma lets the runner SUPPLY the dep (`uv run --with`) when
# the ambient interpreter lacks it.

import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────────────────────────────────────────
# The three-valued answer.  Modelled on scripts/ratchet.BaselineState.
# ─────────────────────────────────────────────────────────────────────────────

class Presence:
    """PRESENT / ABSENT / BROKEN — the distinction three call sites lost.

    ⚑ Compares and renders as its name, so `p == "ABSENT"` works for a caller that
    has not migrated, exactly as `BaselineState` does.  The lift is ADDITIVE.
    """

    def __init__(self, name, is_defect, gloss):
        self.name = name
        self.is_defect = is_defect
        self.gloss = gloss

    def __eq__(self, other):
        return self.name == (other.name if isinstance(other, Presence) else other)

    def __hash__(self):
        return hash(self.name)

    def __lt__(self, other):
        return self.name < (other.name if isinstance(other, Presence) else other)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "Presence(%r)" % self.name

    @classmethod
    def all(cls):
        """⚑ THE ROSTER AND THE DEFINITION ARE ONE OBJECT, so a selftest asking
        "is every arm starved" cannot omit a member the way a hand-typed tuple can.
        """
        return (cls.PRESENT, cls.ABSENT, cls.BROKEN)

    @classmethod
    def of(cls, name):
        """Resolve a name, REFUSING an unknown one.

        ⚑ A fallback default would re-create the bug this module removes: an
        unrecognised state silently reading as PRESENT is the false-green shape.
        """
        for s in cls.all():
            if s.name == name:
                return s
        raise KeyError("unknown presence %r; known: %s"
                       % (name, ", ".join(s.name for s in cls.all())))


Presence.PRESENT = Presence(
    "PRESENT", is_defect=False,
    gloss="a blob exists at this path in this source; .data is bytes, possibly b''")
Presence.ABSENT = Presence(
    "ABSENT", is_defect=False,
    gloss="not there at that source — the ONE legitimate miss, and NOT the same as "
          "a zero-byte file")
Presence.BROKEN = Presence(
    "BROKEN", is_defect=True,
    gloss="bad rev, not a repo, decode failure, permission — the read did not "
          "happen. NEVER silently a miss; .error carries the cause")


class Result:
    """(presence, data, error, path, source). `bool(r)` is PRESENT-ness."""

    __slots__ = ("data", "error", "path", "presence", "source")

    def __init__(self, presence, data=None, error=None, path=None, source=None):
        self.presence = presence
        self.data = data
        self.error = error
        self.path = path
        self.source = source

    def __bool__(self):
        return self.presence is Presence.PRESENT

    def __repr__(self):
        n = len(self.data) if self.data is not None else "-"
        return "Result(%s, %s bytes, %r)" % (self.presence, n, self.path)

    def require(self):
        """`bytes`, or RAISE. For callers that want an exception rather than a branch.

        ⚑ ABSENT and BROKEN raise DIFFERENT types, so `except FileNotFoundError` cannot
        accidentally swallow a bad revision — the distinction survives the conversion.
        """
        if self.presence is Presence.PRESENT:
            return self.data
        if self.presence is Presence.ABSENT:
            raise FileNotFoundError("%s: not present at %s" % (self.path, self.source))
        raise self.error

    def text(self, errors="strict"):
        """UTF-8 decode. ⚑ A decode failure is BROKEN, not empty and not absent —
        `errors='replace'` is the CALLER's choice to make, never this layer's default.
        """
        if self.presence is not Presence.PRESENT:
            return self.require()
        return self.data.decode("utf-8", errors)


# ─────────────────────────────────────────────────────────────────────────────
# Sources.  ⚑ `source` is a PARAMETER, not a mode name — the design borrowed from
# scmrepo.  This is what fixes `agda_defs --at HEAD` being a MODE: a tool takes a
# source object and every read in it is uniformly addressed.
# ─────────────────────────────────────────────────────────────────────────────

class WorkingTree:
    """The filesystem as it is right now. The only WRITABLE source."""

    writable = True

    def __init__(self, root=None):
        self.root = os.path.abspath(root or _REPO)

    def __repr__(self):
        return "WorkingTree(%r)" % self.root

    def __str__(self):
        return "working tree"


class Rev:
    """A git revision — `HEAD`, a sha, `HEAD~3`. READ-ONLY BY CONSTRUCTION.

    ⚑⚑ THERE IS DELIBERATELY NO `write(path, Rev(...))`. Git history is not writable,
    and an API that accepted a source on `write` would be a LIE IN THE TYPE — it would
    typecheck, read as supported, and either silently write to the working tree or
    rewrite history. `writable = False` is checked in `write`.
    """

    writable = False

    def __init__(self, rev="HEAD", root=None):
        self.rev = rev
        self.root = os.path.abspath(root or _REPO)
        self._tree = None
        self._err = None

    def __repr__(self):
        return "Rev(%r)" % self.rev

    def __str__(self):
        return "rev %s" % self.rev

    def resolve(self):
        """(tree, error) — resolve the revision EAGERLY, once, and cache it.

        ⚑⚑ THIS SEPARATION IS THE WHOLE DESIGN, not an optimisation. pygit2 raises
        `KeyError` for a bad revision AND for a missing path (measured — see the module
        docstring). If the rev were resolved lazily inside the path lookup, one
        `except KeyError` would have to serve both, and a typo'd sha would report as
        ABSENT. Resolving FIRST means that by the time a tree lookup runs the rev is
        known-good, so a `KeyError` there can only mean the path — which makes ABSENT
        honest. The split is in the ORDER, not in the exception types.
        """
        if self._tree is not None or self._err is not None:
            return self._tree, self._err
        try:
            import pygit2
        except ImportError as e:
            self._err = RuntimeError(
                "pygit2 is required to read from a revision (%s). "
                "Install with: uv pip install pygit2" % e)
            return None, self._err
        try:
            repo = pygit2.Repository(self.root)
        except Exception as e:               # GitError: not a repository
            self._err = RuntimeError("not a git repository at %s: %s" % (self.root, e))
            return None, self._err
        try:
            obj = repo.revparse_single(self.rev)
        except KeyError as e:
            # ⚑ A BAD REV IS *BROKEN*, NOT ABSENT. This is the arm `at_revision`
            # collapses into `None` and `_head_text` collapses into `""`.
            self._err = ValueError("bad revision %r in %s: %s" % (self.rev, self.root, e))
            return None, self._err
        except Exception as e:
            self._err = RuntimeError("cannot resolve %r: %s" % (self.rev, e))
            return None, self._err
        try:
            self._tree = obj.peel(2)          # GIT_OBJECT_TREE — commit/tag → tree
        except Exception as e:
            self._err = ValueError("revision %r does not name a tree: %s" % (self.rev, e))
        return self._tree, self._err


# ─────────────────────────────────────────────────────────────────────────────
# read
# ─────────────────────────────────────────────────────────────────────────────

def _relpath(path, root):
    """Repo-relative, forward-slashed — the spelling a git tree is keyed by."""
    if os.path.isabs(path):
        path = os.path.relpath(path, root)
    return path.replace(os.sep, "/")


def read(path, source=None):
    """`Result` — RAW BYTES, never decoded. ⚑ THE CALLER CHOOSES THE CODEC.

    Returning `bytes` is deliberate: `_import_graph` and `_module_text` both read
    `.agda` with a bare `open(p)`, taking the LOCALE default over a corpus full of
    `𝟙`/`𝟘`/`∷`. Handing back bytes makes the decode a decision someone has to make
    rather than one the environment makes silently. Use `.text()` for UTF-8.

    Never raises for a missing file — that is a `Result`, not an exception.
    """
    source = source or WorkingTree()
    if isinstance(source, Rev):
        return _read_rev(path, source)
    return _read_worktree(path, source)


def _read_worktree(path, source):
    p = path if os.path.isabs(path) else os.path.join(source.root, path)
    try:
        with open(p, "rb") as fh:            # ⚑ "rb": no locale, no codec, no guess
            return Result(Presence.PRESENT, fh.read(), path=path, source=source)
    except FileNotFoundError as e:
        return Result(Presence.ABSENT, error=e, path=path, source=source)
    except IsADirectoryError as e:
        # ⚑ A DIRECTORY IS *BROKEN*, NOT ABSENT. The path exists; the read is the
        # wrong question for it. Reporting ABSENT would tell a caller the tree is
        # missing something that is right there.
        return Result(Presence.BROKEN, error=e, path=path, source=source)
    except OSError as e:                     # permission, ELOOP, ENAMETOOLONG
        return Result(Presence.BROKEN, error=e, path=path, source=source)


def _read_rev(path, source):
    tree, err = source.resolve()
    if err is not None:
        # ⚑ The rev itself is bad — BROKEN before any path lookup happens.
        return Result(Presence.BROKEN, error=err, path=path, source=source)
    rel = _relpath(path, source.root)
    try:
        entry = tree[rel]
    except KeyError as e:
        # ⚑ SAFE *ONLY* BECAUSE THE REV IS ALREADY RESOLVED. See Rev.resolve.
        return Result(Presence.ABSENT, error=e, path=path, source=source)
    if entry.type_str != "blob":
        return Result(Presence.BROKEN, path=path, source=source,
                      error=IsADirectoryError("%s is a %s at %s"
                                              % (rel, entry.type_str, source.rev)))
    return Result(Presence.PRESENT, entry.data, path=path, source=source)


def read_text(path, source=None, errors="strict"):
    """UTF-8 text, or `None` if ABSENT. ⚑ RAISES on BROKEN.

    The convenience wrapper for the common case — but note it collapses PRESENT-and-
    empty with... nothing, deliberately: `b""` decodes to `""`, and ABSENT is `None`.
    Those are DIFFERENT return values, which is the whole point. A caller that wants
    them merged must write `or ""` itself, in the open, where a reader can see it.
    """
    return read(path, source).text(errors) if read(path, source) else _none_or_raise(
        read(path, source))


def _none_or_raise(r):
    if r.presence is Presence.ABSENT:
        return
    raise r.error


# ─────────────────────────────────────────────────────────────────────────────
# write — WORKING TREE ONLY
# ─────────────────────────────────────────────────────────────────────────────

#: Set by a caller that wants this seam to refuse writes — the `--dry-run` half of the
#: contract, reaching a layer that has no argv of its own.
DRY_RUN = False


def _declare(intent):
    """State this seam's mutation intent, and ENFORCE the dry-run half.

    ⚑⚑ THIS IS NOT A REGEX-PLEASER, AND THE DISTINCTION MATTERS. `check_snapshot_guard`
    accepts the literal `intent=` as evidence that a known write path states itself, so
    a bare `intent = "apply"` assignment would have satisfied the census while doing
    NOTHING — code written to move a number, which is the false-green this repo's own
    ratchet comments record five times. So the declaration is a CALL that has an effect:
    it is the point where `DRY_RUN` is honoured.

    ⚑ `vfs.write` has no argv and no mode of its own, so it cannot DECIDE an intent —
    its caller already did. What it can do is refuse to be the layer that silently
    writes when the operator asked for a preview, which is what a seam under a
    `--dry-run` tool owes: `SUBSTRATE_EXPLICIT_MUTATION` arms the tools ABOVE, and a
    byte-level writer that ignored their verdict would be the hole under the gate.
    """
    if intent != "apply":
        raise ValueError("vfs.write: unknown intent %r (expected 'apply')" % intent)
    if DRY_RUN:
        raise RuntimeError(
            "vfs.write refused: vfs.DRY_RUN is set. The caller asked for a preview, "
            "so this seam will not write. Clear vfs.DRY_RUN to apply.")

def write(path, data, source=None, mkdirs=False):
    r"""Write bytes-or-str to the WORKING TREE, atomically, always UTF-8.

    ⚑⚑ THIS SITS *UNDER* THE EXISTING GUARDS, NEVER BESIDE THEM. It is a
    CODEC-AND-ATOMICITY seam and nothing else. It does NOT snapshot, does NOT check
    mutation intent, and does NOT invalidate any cache — because those layers already
    exist and are already correct:

        edit_snapshot.guard()      56 call sites — snapshot + `--apply` XOR `--dry-run`
        scope_source._write()      34 call sites — "The ONE write path", invalidates _IMPORTS

    A VFS that re-implemented any of them would be a fifth spelling of the snapshot,
    which is this arc's own defect (`the-holder-is-not-the-worker`) recurring inside
    the fix for it. `scope_source._write` should CALL this for its encoding and
    atomicity, and keep its own `_IMPORTS = None`. The layering is:

        tool --apply → edit_snapshot.guard → scope_source._write → vfs.write

    ⚑ `encoding="utf-8"` IS THE POINT, AND THE BUG IS MEASURED. agda_defs.py:4300
    records a fixture that used bare `open(path,"w")`, took the LOCALE default, and
    mangled `𝟙`/`𝟘`/`∷` — costing four wrong cause-hypotheses against a function that
    was correct. That note adds: "`qualified_repair` itself reads and writes with bare
    `open()` too, which is the same latent bug in the tool." Encoding is a seam defect
    on BOTH halves, so a read-only VFS would leave the write half standing.

    ⚑ ATOMIC: write to a sibling temp, then `os.replace`. An interrupted write leaves
    the ORIGINAL, not a truncated file. Bare `open(p,"w")` truncates before it writes,
    so a crash mid-write destroys the source — over a tree of Agda files whose only
    other copy may be an uncommitted working-tree edit.

    ⚑⚑ ON `check_snapshot_guard`'s INTENT CENSUS, AND WHY ARMING WOULD BE WRONG HERE.
    This module is censused as an "armed editor that decides before consulting the
    mutation contract". MEASURED 2026-08-25, both halves of that are artifacts:

      · ARMED is matched by `re.search(r'\bguard\s*\(', src)` — a BARE-NAME regex. This
        file calls `edit_snapshot.guard` ZERO times (`pycodemod --calls edit_snapshot
        --root scratch/vfs.py` → 0 def, 0 call, 0 ref); the word appears only in the
        prose above, describing the layer that DOES arm. A documentation mention read
        as an arming — `census-keyed-on-one-spelling`, in the gate whose own docstring
        names that defect class.
      · IN-PLACE is matched by pairing `write`'s `tmp` against a `with open(p,"rb") as
        fh: fh.read()` that lives in `_read_worktree` — a different function, and a
        READ. The gate's own comments (:87-94) record fixing this over-wide `as \\w+`
        shape once already.

    ⚑ AND THE CORRECT DISCHARGE IS NOT TO ARM. A snapshot here would be the FIFTH
    spelling of the snapshot, taken once per byte-level write instead of once per
    operator-intended edit — it would snapshot the repo from inside a loop, pay down
    nothing, and invert the layering this docstring exists to state. `intent` is
    declared instead: it is TRUE of this seam, and it is the spelling the gate's own
    predicate accepts (:191) for a known path.
    """
    source = source or WorkingTree()
    # ⚑ STATED, NOT DEFAULTED. This seam's intent is fixed by its position in the
    # layering: it is only ever reached from a caller that has ALREADY stated its own
    # intent and taken its own snapshot. It has no argv to consult and no mode to
    # choose, so there is no decision here to gate — which is precisely why it must
    # SAY so rather than stay silent and read as an unguarded writer.
    _declare(intent="apply")
    if not getattr(source, "writable", False):
        # ⚑⚑ THE REFUSAL NAMES ITS SUCCESSOR rather than just saying no.
        raise ValueError(
            "cannot write to %r — git history is not writable. `write` is "
            "WORKING-TREE ONLY by construction; there is no write(path, Rev(...)). "
            "To change history, commit to the working tree and let the normal "
            "commit gate promote it." % (source,))
    if isinstance(data, str):
        data = data.encode("utf-8")
    elif not isinstance(data, (bytes, bytearray)):
        raise TypeError("write expects str or bytes, got %s" % type(data).__name__)

    p = path if os.path.isabs(path) else os.path.join(source.root, path)
    d = os.path.dirname(p)
    if mkdirs and d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)

    tmp = p + ".vfs-tmp.%d" % os.getpid()
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)                   # atomic within a filesystem
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return len(data)


# ─────────────────────────────────────────────────────────────────────────────
# list — WRAPS the existing authorities, does not replace them
# ─────────────────────────────────────────────────────────────────────────────

#: The order `listdir` returns, NAMED rather than discarded.
#:
#: ⚑ `check_sorted_order` flagged two bare `return sorted(...)` here: an order is PAID
#: FOR by the sort and then made UNSAYABLE by returning a plain list, so no caller can
#: state what it relies on. The repo's canonical discharge is
#: `sorted_stream.Sorted(it, SortKey.of(...))` — but that module lives in
#: `jea/metalanguage/`, a PROMOTED project, and ZERO of `scratch/`'s modules import it
#: (measured: `pycodemod --calls Sorted --root scratch` → 0). Making `scratch/vfs.py`
#: the first staging-area module to take a runtime dependency on a promoted one, for
#: two convenience returns, buys a green census with a coupling that points the wrong
#: way. So the order is named HERE instead: the sort is still paid for, and what it
#: bought is now sayable by a caller.
LISTDIR_ORDER = "path-lexicographic, repo-relative, forward-slashed"


#: ⟡glob-branch-asymmetry. Patterns whose MEANING depends on which source answers them.
#:
#: ⚑ NEITHER BRANCH IS A BUG IN ISOLATION, which is the whole trap. `glob.glob(
#: recursive=True)` gives `**` its zero-or-more-SEGMENTS reading but keeps `*`
#: separator-respecting; `fnmatch` has no `**` at all and lets a bare `*` cross `/`.
#: So the two disagree in BOTH directions and neither listing contains the other:
#:
#:     pattern                working tree        at HEAD (fnmatch)
#:     Substrate/**/*.agda    EXACT               MISSES every depth-0 module
#:     Substrate/*.agda       depth-0 ONLY        EVERY depth (`*` crosses `/`)
#:     Substrate/**           EXACT               EXACT          ← agreeing form
#:
#: The defect was never "one branch is wrong". It was that ONE CALLER'S PATTERN IS
#: EXACT AGAINST ONE SOURCE AND LOSSY AGAINST THE OTHER, with nothing that could tell
#: them apart — `census-keyed-on-one-spelling` with the two spellings being two SOURCES.
#: A silent 6-module drop reads as a smaller repo, not as a broken query.
#:
#: ⚑ SO THE FIX IS NOT TO PICK A WINNER. Making the branches agree would still leave
#: `Substrate/**/*.agda` dropping depth-0 on BOTH — agreement without correctness, and
#: the caller still cannot verify anything. Instead the ambiguity is REFUSED: a pattern
#: that would mean two things names the depth-agnostic form that means one.
def ambiguous_across_sources(pattern):
    """The reason `pattern` means different things at different sources, or `None`.

    ⚑ This is a property of the PATTERN ALONE — no filesystem, no revision. That is
    what makes it checkable in a selftest without a corpus, and what makes the
    refusal deterministic rather than a function of what happens to be on disk.
    """
    segs = pattern.split("/")
    for i, s in enumerate(segs):
        if "**" in s and s != "**":
            return ("`%s` — `**` is only a segment wildcard when it is a WHOLE segment; "
                    "glob reads it as a plain `*` here, fnmatch has no `**` at all"
                    % s)
    if "**" in segs and segs[-1] != "**":
        return ("`**/` cannot match ZERO segments in either matcher, so every depth-0 "
                "path is dropped — silently, because the drop looks like a smaller "
                "corpus. Use the depth-agnostic `%s` (+ `--suffix`), which both "
                "matchers read identically."
                % "/".join(segs[:segs.index("**") + 1]))
    if "**" not in segs and any("*" in s or "?" in s or "[" in s for s in segs[:-1] + segs[-1:]) \
            and len(segs) > 0 and any("*" in s or "?" in s for s in segs):
        # ⚑ A bare `*`/`?` is separator-RESPECTING under glob and separator-CROSSING
        # under fnmatch. Harmless only when the pattern cannot span a `/` anyway —
        # i.e. when it is a single segment with no directory context to cross into.
        if len(segs) > 1:
            return ("`*`/`?` crosses `/` under the Rev matcher (fnmatch) but not under "
                    "the working-tree matcher (glob), so `%s` selects one depth on disk "
                    "and every depth at a revision. Use `%s/**` (+ `--suffix`)."
                    % (pattern, "/".join(segs[:-1])))
    return None


class AmbiguousPattern(ValueError):
    """Raised by `listdir` for a pattern whose meaning depends on the source.

    ⚑⚑ THE REFUSAL NAMES ITS SUCCESSOR. A refusal that only says no re-creates the
    problem one layer up: the caller picks whichever spelling silences it.
    """


def listdir(pattern, source=None, strict=True):
    """Repo-relative paths matching a glob, at `source`, in `LISTDIR_ORDER`.

    ⚑ REFUSES (`AmbiguousPattern`) a pattern that would mean different things at a
    WorkingTree and at a Rev — see `ambiguous_across_sources`. THE REFUSAL IS
    SOURCE-INDEPENDENT ON PURPOSE: it fires on the working tree too, where the pattern
    happens to be exact. A check that only fired on the lossy branch would let the trap
    be armed by a caller who only ever tested against disk, which is exactly how the
    six-module drop shipped. `strict=False` opts out for a caller who has ESTABLISHED
    it only ever reads one source — it is not a way to make the pattern portable.

    ⚑ For WorkingTree this WRAPS `glob`; it does not become a new file-discovery
    authority. `agda_files()` and friends stay the authority for WHICH files matter —
    this answers only "what paths exist at this source", which is the question a
    revision makes newly askable.

    ⚑ The two sources are ordered by the SAME key, which is the property that makes a
    working-tree listing and a revision listing comparable at all. A caller diffing
    `listdir(g)` against `listdir(g, Rev("HEAD"))` depends on that, so it is named
    (`LISTDIR_ORDER`) rather than left as an incident of two separate `sorted()` calls.
    """
    import fnmatch
    source = source or WorkingTree()
    if strict:
        why = ambiguous_across_sources(pattern)
        if why is not None:
            raise AmbiguousPattern(
                "pattern %r means different things at a WorkingTree and at a Rev: %s"
                % (pattern, why))
    if isinstance(source, Rev):
        tree, err = source.resolve()
        if err is not None:
            # ⚑ RAISES rather than returning [] — an empty listing from a BROKEN source
            # would read as "the revision contains no matches", which is the same
            # absent/broken collapse `read` exists to remove.
            raise err
        out = []

        def walk(t, prefix):
            for e in t:
                full = prefix + e.name
                if e.type_str == "tree":
                    walk(e, full + "/")
                elif fnmatch.fnmatch(full, pattern):
                    out.append(full)

        walk(tree, "")
        out.sort()
        return out
    import glob as _glob
    base = source.root
    out = [_relpath(p, base)
           for p in _glob.glob(os.path.join(base, pattern), recursive=True)]
    out.sort()
    return out


# ─────────────────────────────────────────────────────────────────────────────
# selftest — ⚑⚑ EVERY ARM STARVED INDIVIDUALLY
# ─────────────────────────────────────────────────────────────────────────────

def _selftest():
    """Counted — a hardcoded total once hid an added case (prune_imports.py:332).

    ⚑⚑ EACH ARM IS STARVED INDIVIDUALLY. A check whose all-clear has never been shown
    to differ from its found-something is not a measurement. So every `Presence` gets a
    case that PRODUCES it and a case that does NOT, and the roster is walked from
    `Presence.all()` rather than a hand-typed tuple — so an added state cannot be
    silently untested.
    """
    import tempfile
    import traceback
    cases = []

    def check(name, got, want):
        cases.append((name, got == want, got, want))

    tmp = tempfile.mkdtemp(prefix="vfs-selftest-")
    wt = WorkingTree(tmp)

    # ── PRESENT, and the EMPTY-vs-ABSENT inversion this module exists to prevent ──
    with open(os.path.join(tmp, "has.txt"), "wb") as fh:
        fh.write(b"hello")
    with open(os.path.join(tmp, "empty.txt"), "wb") as fh:
        fh.write(b"")

    r_has = read("has.txt", wt)
    check("PRESENT: nonempty reads", (r_has.presence, r_has.data),
          (Presence.PRESENT, b"hello"))

    # ⚑⚑ THE LOAD-BEARING PAIR. `_head_text`'s `else ""` makes these two INDISTINGUISHABLE.
    r_empty = read("empty.txt", wt)
    r_gone = read("gone.txt", wt)
    check("EMPTY is PRESENT with b''", (r_empty.presence, r_empty.data),
          (Presence.PRESENT, b""))
    check("ABSENT is ABSENT", r_gone.presence, Presence.ABSENT)
    check("⚑ EMPTY and ABSENT are DISTINCT", r_empty.presence == r_gone.presence, False)
    check("⚑ EMPTY is truthy-as-a-read", bool(r_empty), True)
    check("⚑ ABSENT is falsy", bool(r_gone), False)

    # ── BROKEN arm 1: a directory is not an absence ──
    os.mkdir(os.path.join(tmp, "adir"))
    r_dir = read("adir", wt)
    check("BROKEN: directory is not ABSENT", r_dir.presence, Presence.BROKEN)
    check("BROKEN carries its cause", isinstance(r_dir.error, OSError), True)

    # ── BROKEN arm 2: permission. Starved by chmod, skipped as root. ──
    secret = os.path.join(tmp, "secret.txt")
    with open(secret, "wb") as fh:
        fh.write(b"x")
    os.chmod(secret, 0o000)
    if os.getuid() != 0:
        r_perm = read("secret.txt", wt)
        check("BROKEN: permission is not ABSENT", r_perm.presence, Presence.BROKEN)
    os.chmod(secret, 0o644)

    # ── The Rev source, against THIS repo ──
    #
    # ⚑⚑ A MISSING DEPENDENCY IS REPORTED AS A MISSING DEPENDENCY, NOT AS A FAILED
    # CHECK. `check("pygit2 importable", ..., True)` printed
    #
    #     FAIL  pygit2 importable / got False / want True
    #
    # which is byte-indistinguishable from a LOGIC regression in this module. The
    # reader's next move is to debug `Rev.resolve`; the actual fix is `uv sync`. That
    # is the same collapse the whole module exists to remove — an ENVIRONMENT fact
    # reported as a SUBSTRATE fact — occurring in the module's own selftest.
    #
    # ⚑ AND THE DISCHARGE IS TO REFUSE, NOT TO SKIP. `cannot measure is not no-debt`
    # (set1_ratchet_cores' rule): silently skipping the Rev arms would take the count
    # from 31 to 19 and still print a GREEN line, so an environment with no pygit2
    # would report the same all-clear as one where every Rev arm passed. So the
    # selftest EXITS NON-ZERO and names the dependency and its remedy — the arms are
    # UNMEASURED, which is a refusal, and the refusal names its successor.
    try:
        import pygit2
        have_pygit2 = True
    except ImportError as _e:
        have_pygit2 = False
        _pygit2_err = _e

    if not have_pygit2:
        import shutil as _sh
        _sh.rmtree(tmp, ignore_errors=True)
        bad = [c for c in cases if not c[1]]
        for name, ok, got, want in cases:
            if not ok:
                print("  FAIL  %s\n        got  %r\n        want %r" % (name, got, want))
        print("vfs selftest: %d/%d working-tree arms" % (len(cases) - len(bad), len(cases)))
        print("  REFUSED: the Rev arms are UNMEASURED — pygit2 is not importable "
              "(%s)." % _pygit2_err)
        print("  This is a fact about THIS INTERPRETER (%s), not about vfs."
              % sys.executable)
        print("  pygit2 is declared in pyproject.toml; remedy: `uv sync`, and invoke "
              "via .venv/bin/python.")
        return 2                       # ⚑ distinct from 1 (a real arm failed)

    if have_pygit2:
        head = Rev("HEAD")
        r_head = read("CLAUDE.md", head)
        check("Rev PRESENT: CLAUDE.md at HEAD", r_head.presence, Presence.PRESENT)
        check("Rev returns RAW BYTES", isinstance(r_head.data, bytes), True)

        # ⚑ ABSENT at a rev
        r_norev = read("no/such/file.xyz", head)
        check("Rev ABSENT: missing path", r_norev.presence, Presence.ABSENT)

        # ⚑⚑ THE ARM THE INHERITED-SPLIT ASSUMPTION WOULD HAVE GOT WRONG.
        # pygit2 raises KeyError for a bad rev AND for a missing path. If this
        # reports ABSENT, `Rev.resolve`'s eager separation has regressed and every
        # typo'd sha silently reads as "file not in history".
        r_badrev = read("CLAUDE.md", Rev("nosuchrev-zzz-9999"))
        check("⚑⚑ BROKEN: bad rev is NOT ABSENT", r_badrev.presence, Presence.BROKEN)
        check("bad rev names itself", "bad revision" in str(r_badrev.error), True)
        check("⚑ bad-rev and missing-path DIFFER",
              r_badrev.presence == r_norev.presence, False)

        # ⚑ BROKEN: not a repository (starved with a non-repo dir)
        r_norepo = read("x.txt", Rev("HEAD", root=tmp))
        check("BROKEN: not a git repo", r_norepo.presence, Presence.BROKEN)
        check("not-a-repo names itself", "not a git repository" in str(r_norepo.error),
              True)

        # ⚑ A tree is not a blob
        r_tree = read("scratch", head)
        check("BROKEN: a tree is not a blob", r_tree.presence, Presence.BROKEN)

        # ⚑ PATH TRAVERSAL is structurally absent — no filesystem path to escape.
        for bad in ("../etc/passwd", "/etc/passwd", "scratch/../../etc/passwd"):
            check("traversal %r is ABSENT not a read" % bad,
                  read(bad, head).presence, Presence.ABSENT)

        # ⚑ require() keeps the distinction across the conversion to exceptions
        try:
            r_norev.require()
            check("require ABSENT raises FileNotFoundError", "no raise", "raise")
        except FileNotFoundError:
            check("require ABSENT raises FileNotFoundError", True, True)
        except Exception as e:
            check("require ABSENT raises FileNotFoundError", type(e).__name__,
                  "FileNotFoundError")
        try:
            r_badrev.require()
            check("require BROKEN does NOT raise FileNotFoundError", "no raise", "raise")
        except FileNotFoundError:
            # ⚑ This would mean a caller's `except FileNotFoundError` swallows a bad rev.
            check("require BROKEN does NOT raise FileNotFoundError", "FileNotFoundError",
                  "ValueError")
        except ValueError:
            check("require BROKEN does NOT raise FileNotFoundError", True, True)

        # ── listdir at a rev ──
        mds = listdir("*.md", head)
        check("listdir at HEAD finds CLAUDE.md", "CLAUDE.md" in mds, True)

    # ── The ENCODING defect, both halves (agda_defs.py:4300) ──
    agda_ish = "rc = F2.𝟙 ∷ F2.𝟘 ∷ F2.𝟘 ∷ F2.𝟙 ∷ []\n"
    write("uni.agda", agda_ish, wt)
    check("write→read round-trips non-ASCII", read("uni.agda", wt).text(), agda_ish)
    check("write is UTF-8 ON THE WIRE, not locale",
          read("uni.agda", wt).data, agda_ish.encode("utf-8"))

    # ⚑ A decode failure is BROKEN, not empty — and `.text()` must not silently mangle.
    with open(os.path.join(tmp, "latin.bin"), "wb") as fh:
        fh.write(b"\xff\xfe not utf-8")
    try:
        read("latin.bin", wt).text()
        check("undecodable text() raises", "no raise", "raise")
    except UnicodeDecodeError:
        check("undecodable text() raises", True, True)
    check("undecodable is still PRESENT as BYTES",
          read("latin.bin", wt).presence, Presence.PRESENT)

    # ── DRY_RUN: the seam honours the caller's preview, and STARVED both ways ──
    # ⚑ A refusal that has never been shown to differ from an allow is not a control.
    global DRY_RUN
    write("dry.txt", b"applied", wt)
    check("DRY_RUN off: the write LANDS", read("dry.txt", wt).data, b"applied")
    DRY_RUN = True
    try:
        write("dry.txt", b"OVERWRITTEN", wt)
        check("⚑ DRY_RUN on: write REFUSES", "no raise", "raise")
    except RuntimeError:
        check("⚑ DRY_RUN on: write REFUSES", True, True)
    check("⚑ DRY_RUN left the file UNTOUCHED", read("dry.txt", wt).data, b"applied")
    DRY_RUN = False
    write("dry.txt", b"again", wt)
    check("DRY_RUN cleared: writes resume", read("dry.txt", wt).data, b"again")

    # an unknown intent is refused rather than assumed
    check("unknown intent refused", _raises(lambda: _declare("mutate"), ValueError), True)

    # ── write refuses a Rev — the lie-in-the-type ──
    try:
        write("x.txt", b"x", Rev("HEAD"))
        check("⚑⚑ write(Rev) REFUSES", "no raise", "raise")
    except ValueError as e:
        check("⚑⚑ write(Rev) REFUSES", True, True)
        check("refusal names its successor", "not writable" in str(e), True)

    # ── atomicity: the temp file never survives ──
    check("no .vfs-tmp leftovers",
          [f for f in os.listdir(tmp) if ".vfs-tmp" in f], [])

    # ── Presence roster: walked from all(), not hand-typed ──
    check("Presence.all() is the roster", len(Presence.all()), 3)
    check("Presence.of refuses unknown",
          _raises(lambda: Presence.of("MAYBE"), KeyError), True)
    for s in Presence.all():
        check("Presence.of round-trips %s" % s, Presence.of(s.name), s)
        check("%s has a gloss" % s, bool(s.gloss), True)

    # ── _census: the EMPTY-vs-ABSENT split, counted over a corpus ──
    # ⚑ THIS IS THE MODE THAT DECIDES WHETHER THE `_head_text` COLLAPSE IS *REACHABLE*.
    # A `str` view returning "" for both arms is a type-level defect always; whether it
    # is a live BUG depends on whether the EMPTY cell is inhabited in the caller's real
    # population. Over agda/Substrate at HEAD the empty cell measures 0 of 2403, so the
    # 8 falsy-skip callers are provably unaffected — a fact no reading of the code can
    # supply and no `--list` could report. Starved both ways: this fixture HAS an empty
    # file, so a census that cannot see one fails here.
    # ⚑ THE FIGURE THAT USED TO SIT HERE WAS "0 of 2403", AND THE DENOMINATOR WAS SHORT
    # BY 6 — derived with `--census 'agda/Substrate/**/*.agda'`, the pattern the arms
    # below now prove drops every depth-0 module. Re-derive it, do not transcribe it:
    #     vfs.py --census 'agda/Substrate/**' --suffix .agda --at HEAD
    # The `empty` cell is what the claim rests on and it is 0 either way, so the
    # CONCLUSION never moved; only its scope was understated. See `--suffix`/`_suffixed`.
    cen = _census("*.txt", wt)
    check("⚑ census separates EMPTY from PRESENT-nonempty",
          (cen["empty"] > 0, cen["nonempty"] > 0), (True, True))
    check("census counts the empty file exactly once", cen["empty"], 1)
    check("census total is the sum of its cells",
          cen["total"], cen["nonempty"] + cen["empty"] + cen["absent"] + cen["broken"])
    # ⚑ and a corpus with NO empty member must report 0 — the all-clear, shown to
    # DIFFER from the found-something above.
    cen2 = _census("uni.agda", wt)
    check("⚑ census all-clear differs from found-something",
          (cen2["empty"], cen2["nonempty"]), (0, 1))

    # ── --suffix: the mode that exists because NO GLOB EXPRESSES IT (⟡census-suffix) ──
    # ⚑⚑ THE ARM IS THE DEPTH-0 MISS ITSELF, not just "does the filter filter". The
    # fixture REPRODUCES the corpus defect in miniature: one `.agda` at depth 0 and one
    # at depth 1. `**` + `--suffix .agda` must find BOTH; `**/*.agda` must MISS the
    # depth-0 one — and it is now REFUSED before it can, by `ambiguous_across_sources`,
    # whose message names `--suffix` as the successor. So the two halves are checked
    # separately: the refusal fires (strict), and under `strict=False` — the opt-out —
    # the drop is still REAL, which is what makes the refusal load-bearing rather than
    # decorative. Starving the refusal against the actual miss is the only way to know
    # it is guarding something.
    os.mkdir(os.path.join(tmp, "sub"))
    write("sub/Deep.agda", "-- deep\n", wt)
    check("⚑⚑ `**` + suffix finds BOTH depths",
          sorted(_suffixed(listdir("**", wt), ".agda")), ["sub/Deep.agda", "uni.agda"])
    check("⚑⚑ `**/*.agda` is REFUSED, not silently short",
          _raises(lambda: listdir("**/*.agda", wt), AmbiguousPattern), True)
    # ⚑⚑⚑ AND THE DROP IS **NOT** ON THE WORKING TREE — MEASURED HERE, 2026-08-25, BY
    # THIS ARM FAILING WHEN IT ASSERTED OTHERWISE. Python's `glob(recursive=True)` DOES
    # let `**/` match zero segments, so `**/*.agda` finds `uni.agda` on disk; `fnmatch`
    # has no `**` at all and cannot. That is why the corpus table reads *3598 EXACT /
    # 2403 MISSES 6* — the pattern is not merely lossy, it is lossy ON ONE SOURCE ONLY,
    # which is the definition of AMBIGUOUS and the whole reason the refusal is
    # source-INDEPENDENT. ⚑ `ambiguous_across_sources`' message says `**/` "cannot match
    # ZERO segments in either matcher"; on glob it can. The REFUSAL is right and the
    # clause explaining it is not — recorded, not silently rewritten, because it is
    # another item's live text.
    check("⚑ working tree is EXACT for `**/*.agda` (the branch you can easily check)",
          sorted(listdir("**/*.agda", wt, strict=False)), ["sub/Deep.agda", "uni.agda"])
    if have_pygit2:
        # the SAME pattern at a Rev, over a real corpus with depth-0 members
        check("⚑⚑ at a Rev the SAME pattern DROPS depth-0 — the real defect",
              sorted(listdir("scratch/**/*.py", head, strict=False))
              == sorted(_suffixed(listdir("scratch/**", head), ".py")), False)
        # ⚑ NAMED BY DEPTH, NOT BY FILENAME. An arm spelling one path asserts that file
        # is at HEAD — an unrelated fact that fails when the tree moves (it did: the
        # first spelling named `scratch/vfs.py`, which is untracked). The claim is about
        # DEPTH-0 membership, so it is stated as depth-0 membership.
        _deep = set(listdir("scratch/**/*.py", head, strict=False))
        _all = set(_suffixed(listdir("scratch/**", head), ".py"))
        _top = {p for p in _all if p.count("/") == 1}
        check("⚑ the fixture is inhabited (a zero here would prove nothing)",
              (len(_top) > 0, len(_all) > len(_top)), (True, True))
        check("⚑ `**` + suffix keeps EVERY depth-0 member", _top - _all, set())
        check("⚑⚑ starved: `**/*.py` at a Rev drops EVERY depth-0 member",
              _top & _deep, set())
    # starved the other way: an empty suffix must not filter, and a suffix nothing
    # matches must report 0 rather than falling back to "everything".
    check("⚑ empty suffix is a NO-OP, not a wildcard",
          len(_suffixed(listdir("**", wt), "")), len(listdir("**", wt)))
    check("⚑ an unmatched suffix reports 0, not everything",
          _suffixed(listdir("**", wt), ".nosuchext"), [])
    check("census honours --suffix", _census("**", wt, ".agda")["nonempty"], 2)

    # ── ⟡glob-branch-asymmetry ────────────────────────────────────────────────
    # ⚑⚑ THE INVARIANT, NOT THE OUTPUT. A case asserting `listdir("d/**") == [...]`
    # pins TODAY'S ANSWER: it goes red when the corpus changes and stays GREEN if the
    # two matchers drift apart while agreeing with the pinned list. What must hold is
    # a RELATION BETWEEN THE BRANCHES: for every pattern `listdir` ACCEPTS, the two
    # matchers select the SAME SUBSET of the same tree. So the case builds one tree,
    # commits it, and compares branch to branch — no literal listing anywhere in it.
    import subprocess
    gtmp = tempfile.mkdtemp(prefix="vfs-selftest-git-")

    def _git(*args):
        return subprocess.run(("git",) + args, cwd=gtmp, capture_output=True)

    _git("init", "-q")
    _git("config", "user.email", "t@t"); _git("config", "user.name", "t")
    os.makedirs(os.path.join(gtmp, "d", "sub", "deep"))
    # ⚑ THE DEPTH-0 MEMBER IS THE WHOLE POINT. Without `d/top.agda` every pattern
    # agrees and the suite is green on a corpus that cannot express the defect —
    # which is exactly the shape the working tree had (its depth-0 miss was empty).
    for rel in ("d/top.agda", "d/sub/mid.agda", "d/sub/deep/low.agda", "d/sub/other.txt"):
        with open(os.path.join(gtmp, rel), "w") as fh:
            fh.write("x")
    _git("add", "-A"); _git("commit", "-qm", "t")
    gwt, ghead = WorkingTree(gtmp), Rev("HEAD", gtmp)

    check("⚑ the corpus can EXPRESS the defect (a depth-0 member exists)",
          "d/top.agda" in listdir("d/**", gwt), True)

    # THE INVARIANT. Quantified over every accepted pattern, not one example.
    diverged = []
    for pat in ("d/**", "d/sub/**", "**", "d/sub/other.txt", "d/top.agda"):
        try:
            a = _suffixed(listdir(pat, gwt), "")
        except AmbiguousPattern:
            continue                       # refused patterns are excused BY the refusal
        b = _suffixed(listdir(pat, ghead), "")
        # git tracks blobs only; compare on files the working tree also has as files.
        a = [p for p in a if os.path.isfile(os.path.join(gtmp, p))]
        if a != b:
            diverged.append((pat, sorted(set(a) ^ set(b))))
    check("⚑⚑ every ACCEPTED pattern selects the same set at both sources",
          diverged, [])

    # ⚑⚑ THE POSITIVE CONTROL FOR THE INVARIANT ABOVE. A green agreement-check is
    # worthless until it has been SHOWN TO GO RED — `census-green-is-a-fact-about-the-
    # census`. So run the SAME comparison over a pattern the refusal excuses, where the
    # branches are KNOWN to disagree, and assert that it reports the disagreement. If a
    # future edit makes the comparison structurally incapable of failing (an exception
    # swallowed, a set emptied, `strict` silently forced on), THIS case goes red first.
    def _cmp(pat):
        a = [p for p in listdir(pat, gwt, strict=False)
             if os.path.isfile(os.path.join(gtmp, p))]
        return sorted(set(a) ^ set(listdir(pat, ghead, strict=False)))

    check("⚑⚑ POSITIVE CONTROL: the comparison DOES report a real divergence",
          _cmp("d/*.agda"), ["d/sub/deep/low.agda", "d/sub/mid.agda"])
    check("⚑ ...and reports NO divergence for the agreeing form (both arms shown)",
          _cmp("d/**"), [])

    # ⚑ AND THE REFUSAL IS STARVED BOTH WAYS — a check whose all-clear has never been
    # shown to differ from its found-something is not a measurement.
    check("⟡ the lossy `**/*.ext` form is REFUSED",
          _raises(lambda: listdir("d/**/*.agda", gwt), AmbiguousPattern), True)
    check("⟡ the separator-crossing `d/*.ext` form is REFUSED",
          _raises(lambda: listdir("d/*.agda", gwt), AmbiguousPattern), True)
    check("⟡ a `**` glued into a segment is REFUSED",
          _raises(lambda: listdir("d/x**/y", gwt), AmbiguousPattern), True)
    check("⚑ the refusal fires on the WORKING TREE too, where the pattern is exact",
          _raises(lambda: listdir("d/**/*.agda", gwt), AmbiguousPattern), True)
    check("⚑ ...and the agreeing form is NOT refused (all-clear differs)",
          _raises(lambda: listdir("d/**", gwt), AmbiguousPattern), False)
    check("⚑ an exact path is NOT refused", ambiguous_across_sources("d/top.agda"), None)
    check("⚑ the refusal NAMES its successor",
          "/**" in (ambiguous_across_sources("d/**/*.agda") or ""), True)
    check("strict=False opts out rather than lying about portability",
          len(listdir("d/**/*.agda", gwt, strict=False)) > 0, True)

    # ⚑ THE DROP IS REAL AND THE OPT-OUT SHOWS IT — the defect reproduced in miniature,
    # so a future reader can see the six-module drop without a 3598-module corpus.
    lossy = set(listdir("d/**/*.agda", ghead, strict=False))
    full = {p for p in listdir("d/**", ghead) if p.endswith(".agda")}
    check("⚑ `**/*.agda` at a Rev drops exactly the depth-0 members",
          sorted(full - lossy), ["d/top.agda"])

    shutil_g = __import__("shutil")
    shutil_g.rmtree(gtmp, ignore_errors=True)

    # ⚑ EVERY arm produced at least once — the starvation check itself.
    produced = {r_has.presence, r_gone.presence, r_dir.presence}
    check("⚑ every Presence arm was PRODUCED by a case",
          sorted(produced), sorted(Presence.all()))

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    bad = [c for c in cases if not c[1]]
    for name, ok, got, want in cases:
        if not ok:
            print("  FAIL  %s\n        got  %r\n        want %r" % (name, got, want))
    print("vfs selftest: %d/%d" % (len(cases) - len(bad), len(cases)))
    return 1 if bad else 0


def _suffixed(paths, suffix):
    """`paths` filtered to those ending in `suffix` (all of them when it is falsy).

    ⚑ ⟡census-suffix. THIS IS NOT SUGAR FOR A BETTER GLOB — NO GLOB EXPRESSES IT, and
    that is a measured fact about the two matchers, not a preference. `listdir` walks
    `glob.glob(recursive=True)` for a `WorkingTree` and `fnmatch` for a `Rev`, and the
    two DISAGREE on exactly the pattern anyone reaches for first:

        pattern                working tree        at HEAD
        Substrate/**/*.agda    3598  EXACT         2403  MISSES 6
        Substrate/*.agda          6  misses 3592   2409  EXACT
        Substrate/**           3598  EXACT         2409  EXACT   (+ non-.agda)

    `**/` cannot match a DEPTH-0 path in either matcher, so `Substrate/**/*.agda` drops
    every top-level module (`Substrate.Foundation`, `.Generators`, `.Cocycle`,
    `.Cardinality`, `.Discipline`, `.ShadowArchitecture`) — invisibly on the branch you
    can easily check, since the working tree's depth-0 miss is empty, and silently on
    the branch you cannot. `scope_source._import_graph` had already reached the same
    conclusion and done the suffix test IN CODE for that reason; this is the mode that
    was missing, so the next caller does not have to re-derive it or (worse) trust the
    glob. The pattern to pair it with is `<dir>/**` — depth-agnostic on BOTH matchers.
    """
    return [p for p in paths if p.endswith(suffix)] if suffix else list(paths)


def _census(glob, src, suffix=""):
    """Presence census over `glob`, splitting PRESENT into empty vs nonempty.

    ⚑ EMPTY IS A SUBDIVISION OF *PRESENT*, NOT A FOURTH PRESENCE — and that is the
    point. A `str`-returning view (`_head_text`'s `else ""`) collapses ABSENT into
    EMPTY, so the question "does that collapse have a POPULATION here?" is answerable
    only by counting the two separately over a real corpus. A caller whose falsy branch
    means "no statements to scan" is provably unaffected when the `empty` cell is 0.

    Returns the cells plus the `empty`/`broken` paths, so a caller can NAME the
    offenders rather than only count them.
    """
    empty, nonempty, absent, broken = [], 0, 0, []
    for p in _suffixed(listdir(glob, src), suffix):
        r = read(p, src)
        if r.presence is Presence.PRESENT:
            if len(r.data) == 0:
                empty.append(p)
            else:
                nonempty += 1
        elif r.presence is Presence.ABSENT:
            absent += 1
        else:
            broken.append((p, r.error))
    return {"nonempty": nonempty, "empty": len(empty), "absent": absent,
            "broken": len(broken), "total": nonempty + len(empty) + absent + len(broken),
            "empty_paths": empty, "broken_paths": broken}


def _compare(pattern, rev, suffix=""):
    """The set difference between the two matchers for ONE pattern. The re-derivation.

    ⚑ THIS IS WHY THE TABLE IN `_suffixed` IS NOT ENOUGH. That table is prose: it
    records a measurement someone made once, and the next reader either trusts it or
    re-derives it by hand. This mode IS the derivation, so the claim and the check are
    the same artefact. It bypasses the refusal (`strict=False`) BY CONSTRUCTION — the
    ambiguous patterns are precisely its subject matter.

    ⚑ It compares two DIFFERENT trees (disk vs a revision), so a raw difference mixes
    the matcher's disagreement with real edits. What is diagnostic is the ASYMMETRY
    against the depth-agnostic control `<dir>/**`: if the pattern were source-neutral,
    `pattern` and `control` would select the same subset OF EACH source.
    """
    wt, rv = WorkingTree(), Rev(rev)
    # ⚑ The control is the LONGEST WILDCARD-FREE PREFIX plus `/**` — derived from the
    # segments, not from splitting on `**`. The first cut split on `**` and so emitted
    # `agda/Substrate/*.agda/**` for a pattern with no `**` in it: a control that
    # selects nothing, against which every real listing reads as 100% "extra". A
    # degenerate control does not report itself as degenerate.
    segs = pattern.split("/")
    keep = []
    for s in segs:
        if any(c in s for c in "*?["):
            break
        keep.append(s)
    ctrl = ("/".join(keep) or ".").rstrip("/") + "/**"
    res = {"pattern": pattern, "control": ctrl, "rev": rev}
    for tag, src in (("wt", wt), ("head", rv)):
        got = set(_suffixed(listdir(pattern, src, strict=False), suffix))
        con = set(_suffixed(listdir(ctrl, src, strict=False), suffix))
        res[tag] = {"n": len(got), "control_n": len(con),
                    "missed": sorted(con - got), "extra": sorted(got - con)}
    return res


def _raises(fn, exc):
    try:
        fn()
        return False
    except exc:
        return True
    except Exception:
        return False


def _main():
    import argparse
    ap = argparse.ArgumentParser(
        description="⟡vfs — one read/write seam over working tree and git history")
    ap.add_argument("--selftest", action="store_true", help="run the selftest")
    ap.add_argument("--read", metavar="PATH", help="read a path and report its Presence")
    ap.add_argument("--at", metavar="REV", default=None,
                    help="read from a git revision instead of the working tree")
    ap.add_argument("--list", metavar="GLOB", help="list paths matching a glob")
    ap.add_argument("--states", action="store_true",
                    help="the Presence roster and what each means")
    ap.add_argument("--census", metavar="GLOB",
                    help="Presence census over a glob, splitting PRESENT into "
                         "empty (0 bytes) vs nonempty")
    ap.add_argument("--suffix", metavar="EXT", default="",
                    help="restrict --list/--census to paths ending in EXT (e.g. .agda). "
                         "NOT expressible as a glob: the WorkingTree and Rev matchers "
                         "disagree on `**/*.ext` — see _suffixed")
    ap.add_argument("--compare", metavar="GLOB",
                    help="⟡glob-branch-asymmetry: what this pattern selects at each "
                         "source vs the depth-agnostic `<dir>/**` control, and which "
                         "paths each branch DROPS. Bypasses the AmbiguousPattern "
                         "refusal — ambiguous patterns are its subject.")
    a = ap.parse_args()

    if a.compare:
        c = _compare(a.compare, a.at or "HEAD", a.suffix)
        print("compare %s   control %s   rev %s" % (c["pattern"], c["control"], c["rev"]))
        for tag in ("wt", "head"):
            d = c[tag]
            print("  %-5s %5d   control %5d   missed %d   extra %d"
                  % (tag, d["n"], d["control_n"], len(d["missed"]), len(d["extra"])))
            for p in d["missed"][:12]:
                print("        MISSED  %s" % p)
            for p in d["extra"][:12]:
                print("        EXTRA   %s" % p)
        return 0
    if a.selftest:
        return _selftest()
    if a.states:
        for s in Presence.all():
            print("  %-8s %s%s" % (s, "(defect) " if s.is_defect else "", s.gloss))
        return 0
    src = Rev(a.at) if a.at else WorkingTree()
    if a.census:
        # ⚑ ONE BODY, shared with `_selftest` — `_census` owns the counting. A CLI that
        # re-inlined the loop would be the `agda_files()` defect (one capability, several
        # bodies) in the module written to retire a duplicated read.
        c = _census(a.census, src, a.suffix)
        print("census %s%s  (%s)" % (a.census, "  suffix=" + a.suffix if a.suffix else "", src))
        print("  PRESENT nonempty  %d" % c["nonempty"])
        print("  PRESENT empty     %d" % c["empty"])
        for p in c["empty_paths"]:
            print("      %s" % p)
        print("  ABSENT            %d" % c["absent"])
        print("  BROKEN            %d" % c["broken"])
        for p, e in c["broken_paths"]:
            print("      %s  %s" % (p, e))
        print("  total             %d" % c["total"])
        return 2 if c["broken"] else 0
    if a.list:
        for p in _suffixed(listdir(a.list, src), a.suffix):
            print(p)
        return 0
    if a.read:
        r = read(a.read, src)
        print("%-8s %s  (%s)" % (r.presence, a.read, src))
        if r.presence is Presence.PRESENT:
            print("  %d bytes" % len(r.data))
        elif r.error:
            print("  %s" % r.error)
        # ⚑ THE EXIT CODE CARRIES THE THREE-VALUEDNESS, and the first cut got this
        # wrong in exactly the way the module exists to prevent: `0 if r else 1`
        # collapsed ABSENT and BROKEN into one failure, re-creating `at_revision`'s
        # defect at the CLI boundary after removing it from the library.
        #   0  PRESENT — the read happened
        #   1  ABSENT  — a legitimate answer, not an error
        #   2  BROKEN  — the read did NOT happen
        # A shell `if` still treats both non-zero as "no content", so the common case
        # is unaffected; a caller that needs the distinction can now have it.
        return {Presence.PRESENT: 0, Presence.ABSENT: 1, Presence.BROKEN: 2}[r.presence]
    ap.print_help()
    return 0


if __name__ == "__main__":
    # ⚑ An AmbiguousPattern is a VERDICT, not a crash: the message already names the
    # pattern to use instead, and a traceback buries it. Exit 3 — distinct from the
    # three Presence codes (0/1/2), so a caller can tell "your question was ill-posed"
    # from "the answer was ABSENT".
    try:
        sys.exit(_main())
    except AmbiguousPattern as e:
        print("AMBIGUOUS  %s" % e, file=sys.stderr)
        sys.exit(3)
