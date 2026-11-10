# Explicit fixture replay inputs

All four fixture commands (`demo`, `ingest-demo`, `study-demo`, `backtest-demo`)
accept `--asof`, `--universe`, `--source-manifest`, `--seed`, `--config` and `--output`.
The only implemented research universe is `fixture-common-v1`, the closed fictional
common-share universe with a separate benchmark. Other names fail argument validation.
Current Finviz observations and historical exports have separate commands and namespaces;
selecting a universe cannot promote them into historical research.

`--config` accepts at most 64 KiB of JSON with optional `discovery`, `portfolio`
and `event` policy objects. Unknown keys, duplicate keys, nonfinite constants and invalid
policy values fail before publication. It is exclusive with the existing `--policy`,
`--portfolio-policy` and `--event-policy` files, avoiding silent precedence rules.
Omitted policy blocks retain ordinary defaults, including the CLI seed for portfolio
and event policies. A supplied block uses that policy's defaults unless explicitly set.
The resulting complete policies and their hashes are saved in the research run.

```powershell
uv run baghunter demo --universe fixture-common-v1 --config examples/replay-config.json --asof 2022-01-03T23:00:00+00:00 --seed 7 --output data/fixture/replay
```

To assert the source on replay, use the original saved run's `source_manifest.json`:

```powershell
uv run baghunter demo --universe fixture-common-v1 --source-manifest data/fixture/replay/runs/<run-id>/source_manifest.json --config examples/replay-config.json --asof 2022-01-03T23:00:00+00:00 --seed 7 --output data/fixture/replay
```

The manifest must exactly match the generated source metadata, including its raw SHA-256.
Verification runs before any cached-run activation or write. It does not import observations,
change source attribution, backdate current data or bypass integrity checks. An older fixture
manifest that differs after a generator/schema change fails explicitly; retain its original
source revision for exact replay. Formatting differences alone do not change its meaning.
The default invocation remains compatible when the optional controls are omitted.
