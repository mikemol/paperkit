_33 cited claims: 26 behavioral, 2 indeterminate, 5 vacuous._

| claim | section | Δ grade | witness |
| --- | --- | --- | --- |
| `paper-is-projection` | intro | vacuous | `file:../paperkit/project.py` |
| `node-is-claim` | intro | vacuous | `file:warrants.bib` |
| `claim-bears-check` | intro | vacuous | `file:warrants.bib` |
| `fail-omits` | intro | behavioral | `cmd:sh checks/projection-stable.sh` |
| `claim-is-record` | model | behavioral | `claim:claim-is-record` |
| `record-is-bibentry` | model | behavioral | `claim:record-is-bibentry` |
| `prose-projected` | model | behavioral | `claim:prose-projected` |
| `ordered-by-deps` | model | behavioral | `claim:ordered-by-deps` |
| `joined-by-glue` | model | behavioral | `claim:joined-by-glue` |
| `deterministic` | model | behavioral | `claim:deterministic` |
| `projector-emits` | engine | behavioral | `claim:projector-emits` |
| `prose-is-artifact` | engine | behavioral | `claim:prose-is-artifact` |
| `gate-rejects-drift` | engine | behavioral | `claim:gate-rejects-drift` |
| `edit-cant-survive` | engine | behavioral | `claim:edit-cant-survive` |
| `coverage-both-sides` | engine | behavioral | `claim:coverage-both-sides` |
| `every-section-appears` | engine | behavioral | `claim:every-section-appears` |
| `every-claim-cited` | engine | behavioral | `claim:every-claim-cited` |
| `verifier-named` | resolver | behavioral | `claim:verifier-named` |
| `gate-dispatches` | resolver | behavioral | `claim:gate-dispatches` |
| `new-domain-adds` | resolver | behavioral | `claim:new-domain-adds` |
| `two-builtins` | resolver | behavioral | `claim:two-builtins` |
| `file-builtin` | resolver | behavioral | `claim:file-builtin` |
| `cmd-builtin` | resolver | behavioral | `claim:cmd-builtin` |
| `cmd-escape` | resolver | behavioral | `claim:cmd-escape` |
| `paper-is-paperkit` | selfhost | behavioral | `cmd:sh checks/projection-stable.sh` |
| `claims-are-warrants` | selfhost | vacuous | `file:warrants.bib` |
| `prose-is-projection` | selfhost | behavioral | `cmd:sh checks/projection-stable.sh` |
| `gate-is-subject` | selfhost | vacuous | `file:../paperkit/gate.py` |
| `paperkit-on-paperkit` | selfhost | indeterminate | `cmd:sh checks/drift-caught.sh` |
| `one-green-check` | selfhost | indeterminate | `cmd:sh checks/drift-caught.sh` |
| `closes-gap` | conclusion | behavioral | `cmd:sh checks/projection-stable.sh` |
| `unverified-cant-ship` | conclusion | behavioral | `cmd:sh checks/projection-stable.sh` |
| `not-project` | conclusion | behavioral | `cmd:sh checks/projection-stable.sh` |
