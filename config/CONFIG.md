# paperkit Configurables

*Every knob resolves one way — arg over env over config over default — and is projected here from the one registry that defines it (Ω·config).*

## The Resolution Model

Every configurable resolves the one way — an explicit argument over an environment variable over the project's paper.toml config over a built-in default [@cfg-precedence]. The registry is well-formed — each knob carries a unique name and a unique PAPERKIT_ environment variable and a help line, and a flag declares no value choices [@cfg-wellformed]. Coverage is total — every knob is reachable by BOTH a command-line flag and an environment variable, so a container pipeline and an ad-hoc run reach the same controls [@cfg-covers].

## The Knobs

The knobs, each with its flag, environment variable, config key, and default — generated from the registry, so this table cannot drift from the code [@cfg-table].

| knob | flag | env var | config | default |
| --- | --- | --- | --- | --- |
| `root` (value) | `--root` | `PAPERKIT_ROOT` | `root` | `—` |
| `path` (value) | `--path` | `PAPERKIT_PATH` | — | `—` |
| `safe` (flag) | `--safe` | `PAPERKIT_SAFE` | `safe` | `—` |
| `without-K` (flag) | `--without-K` | `PAPERKIT_WITHOUT_K` | `without_k` | `—` |
| `jobs` (value) | `--jobs` | `PAPERKIT_JOBS` | `jobs` | `—` |
| `json` (flag) | `--json` | `PAPERKIT_JSON` | — | `—` |
| `min-strength` (value) | `--min-strength` | `PAPERKIT_MIN_STRENGTH` | `min_strength` | `—` |
| `min-corroboration` (value) | `--min-corroboration` | `PAPERKIT_MIN_CORROBORATION` | `min_corroboration` | `—` |
| `resolution` (value) | `--resolution` | `PAPERKIT_RESOLUTION` | `resolution` | `file` |
| `target` (value) | `--target` | `PAPERKIT_TARGET` | `target` | `pandoc` |
| `state` (value) | `--state` | `PAPERKIT_STATE` | — | `—` |
| `budget` (value) | `--budget` | `PAPERKIT_BUDGET` | — | `—` |
| `all` (flag) | `--all` | `PAPERKIT_ALL` | — | `—` |
| `footprint` (flag) | `--footprint` | `PAPERKIT_FOOTPRINT` | — | `—` |
| `no-cache` (flag) | `--no-cache` | `PAPERKIT_NO_CACHE` | — | `—` |
| `delta-repeat` (value) | `--delta-repeat` | `PAPERKIT_DELTA_REPEAT` | — | `1` |
| `delta-pulse` (value) | `--delta-pulse` | `PAPERKIT_DELTA_PULSE` | — | `2` |
| `check` (flag) | `--check` | `PAPERKIT_CHECK` | — | `—` |
| `only` (value) | `--only` | `PAPERKIT_ONLY` | — | `—` |
| `invariants` (flag) | `--invariants` | `PAPERKIT_INVARIANTS` | — | `—` |
