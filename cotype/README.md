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

## Axis-signatures

Each entry may carry a shadow-engineer axis-signature `[abc]` over (goal, shadows,
artefact): `100` pure goal↔shadows, `010` pure shadows↔artefact, `001` guard event,
`110` mediated-composite, `111` triadic-full, etc. The signature is the read/write set
of the move, not a priority.
