| type | verb | passes when |
| --- | --- | --- |
| `file:<path>` | exists | the artifact exists |
| `cmd:<script>` | execs | the script exits `0` |
| `result:<project>` | parses | the sibling project's gate verdict parses green |
| `agree:<p>\|\|\|<q>` | concurs | the independent producers all exit `0` and emit identical output |
| `concept:<key>` | imports | the project's concept library --- else the engine's --- certifies that key |

**When the mutation grade adds nothing.** If an `agree:` check's second producer is a *reference computation* --- a theorem or closed form the result must match --- rather than a *file read*, the agreement is already the whole falsification surface: a wrong result disagrees with the reference directly, so there is no separate "could this claim's data be corrupted" question for the mutation sweep to answer. paperkit's grade earns its keep when the oracle is a file whose *mutability* is the question, not when it is another computation.
