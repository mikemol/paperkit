| grade | meaning |
| --- | --- |
| `vacuous` | provably can't fail — `file:` of an input the build already requires |
| `existence` | `file:` of a contingent artifact — presence, not content |
| `behavioral` | proven falsifiable — a single-file mutation flips it red |
| `indeterminate` | no generic mutation flips it — vacuous, or a negative-assertion check |
