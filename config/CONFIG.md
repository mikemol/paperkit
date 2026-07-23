# paperkit Configurables

*Every knob resolves one way — arg over env over config over default — declared in the module that resolves it and projected here from the introspected union (Ω·config).*

## The Resolution Model

Every configurable resolves the one way — an explicit argument over an environment variable over the project's paper.toml config over a built-in default [@cfg-precedence]. The knob union is well-formed — each knob, declared in the module that resolves it and collected by introspection, carries a unique name and a unique PAPERKIT_ environment variable and a help line, and a flag declares no value choices [@cfg-wellformed]. Coverage is total — every knob is reachable by BOTH a command-line flag and an environment variable, so a container pipeline and an ad-hoc run reach the same controls [@cfg-covers].

## The Knobs

The knobs, each with its flag, environment variable, config key, and default — generated from the introspected union of the engine's knob declarations, so this table cannot drift from the code [@cfg-table].

| knob | flag | env var | config | default |
| --- | --- | --- | --- | --- |
| `all` (flag) | `--all` | `PAPERKIT_ALL` | — | `—` |
| `budget` (value) | `--budget` | `PAPERKIT_BUDGET` | — | `—` |
| `check` (flag) | `--check` | `PAPERKIT_CHECK` | — | `—` |
| `delta-pulse` (value) | `--delta-pulse` | `PAPERKIT_DELTA_PULSE` | — | `2` |
| `delta-repeat` (value) | `--delta-repeat` | `PAPERKIT_DELTA_REPEAT` | — | `1` |
| `footprint` (flag) | `--footprint` | `PAPERKIT_FOOTPRINT` | — | `—` |
| `invariants` (flag) | `--invariants` | `PAPERKIT_INVARIANTS` | — | `—` |
| `jobs` (value) | `--jobs` | `PAPERKIT_JOBS` | `jobs` | `—` |
| `json` (flag) | `--json` | `PAPERKIT_JSON` | — | `—` |
| `min-corroboration` (value) | `--min-corroboration` | `PAPERKIT_MIN_CORROBORATION` | `min_corroboration` | `—` |
| `min-strength` (value) | `--min-strength` | `PAPERKIT_MIN_STRENGTH` | `min_strength` | `—` |
| `mutant` (value) | `--mutant` | `PAPERKIT_MUTANT` | — | `—` |
| `no-cache` (flag) | `--no-cache` | `PAPERKIT_NO_CACHE` | — | `—` |
| `only` (value) | `--only` | `PAPERKIT_ONLY` | — | `—` |
| `path` (value) | `--path` | `PAPERKIT_PATH` | — | `—` |
| `resolution` (value) | `--resolution` | `PAPERKIT_RESOLUTION` | `resolution` | `file` |
| `root` (value) | `--root` | `PAPERKIT_ROOT` | `root` | `—` |
| `safe` (flag) | `--safe` | `PAPERKIT_SAFE` | `safe` | `—` |
| `state` (value) | `--state` | `PAPERKIT_STATE` | — | `—` |
| `target` (value) | `--target` | `PAPERKIT_TARGET` | `target` | `pandoc` |
| `without-K` (flag) | `--without-K` | `PAPERKIT_WITHOUT_K` | `without_k` | `—` |
