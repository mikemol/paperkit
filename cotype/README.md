# cotype — the cross-session shadow ledger

This is the shadow-engineer *cotype*: the durable, versioned record of labelled work
items (AIs) accumulated across sessions, so that reasoning state survives context loss
and compaction. It is the settled twin of the working plan (`~/.claude/plans/…`, which
is ephemeral scratch); an item earns a place here once it is a real commitment.

## The one rule: append-only, retirement-logged

The cotype grows monotonically. An entry is never silently overwritten or deleted.

- **Add** freely.
- **Change status** by editing the entry's status field in place (live → closed).
- **Retire** an entry only with a `RETIRED: <reason>` note; the entry stays, the reason
  is logged. Deletion without a logged retirement is forbidden — it breaks the
  cross-session persistence the cotype exists to provide.

This invariant is the cotype's own gate (see `cotype-monotone`, a planned check: every
line removed from `ledger.md` in a commit must be accompanied by a `RETIRED:` line in
the same commit). Until that gate lands, the rule is enforced by convention.

## The over-decode guard: entailed vs asserted

The shadow-engineer standing-line rule forbids forcing a line's third point to tidy
present ambiguity. In a cotype the failure is *delayed*: a later pass "discovers" a
unification an earlier pass planted to tidy the picture, and treats the forced
completion as real. A downstream consumer hit exactly this — 16 findings declared "one
invariant" where 9 actually were.

So an entry that UNIFIES multiple findings under a common structure (a "terminus", "one
law") must record which it is:

- **entailed** — two populated points forced the third (a real Fano-line completion);
  cite the two points.
- **asserted** — declared to tidy the picture; a *candidate*, not a closure, and must
  not be leaned on until a real second point populates it.

The predicate a future gate (or a reader) applies: *was this entry entailed by two
populated points, or asserted to tidy?* An asserted unification that a later pass
consumes as entailed is the over-decode this guards. Unlabelled unifications default to
**asserted**.

## Axis-signatures

Each entry may carry a shadow-engineer axis-signature `[abc]` over (goal, shadows,
artefact): `100` pure goal↔shadows, `010` pure shadows↔artefact, `001` guard event,
`110` mediated-composite, `111` triadic-full, etc. The signature is the read/write set
of the move, not a priority.
