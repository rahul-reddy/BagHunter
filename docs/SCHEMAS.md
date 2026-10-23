# Implemented data contracts

Validated models are in `packages/shared/models.py`; JSON raw snapshots retain all original fields.
Times require UTC offsets; nonfinite numbers and inconsistent OHLC fail validation.

| Layer / table | Identity and time | Coverage |
| --- | --- | --- |
| raw / checksum.json | SHA-256 of serialized Dataset | immutable synthetic source |
| silver / instruments | security_id, first_seen, last_seen | common / benchmark, fixture matching strata |
| silver / symbols | security_id, ticker, valid_from/to | dated mappings; half-open intervals |
| silver / bars | security_id, session, available_at | raw OHLCV, source_id, adjustment_policy |
| silver / facts | security_id, period_end, accepted_at, published_at | accession, metric, unit, amended, source URL |
| silver / actions | security_id, effective_date | split ratio / cash dividend / delist proceeds |
| gold / features | security_id, asof_time, feature_version | source IDs, cutoff, null factors, score, evidence |
| hindsight / labels | security_id, anchor, horizon_years | max multiple, terminal return, drawdown, coverage |
| hindsight / cohort_pairs | anchor, case/control IDs, matching_seed | strata and sampling weights |
| run.json | run_id, source checksum, seed, model_version, asof | signals, study and toy evaluation for read-only UI |
| source_manifest.json | source_id, checksum, latest source timestamp | fixture license, coverage, blocked real provider |

Full target tables in `03_DATA_AND_ARCHITECTURE.md` are not all implemented. There is no real historical
market-cap table, thesis table, instrument event ledger or production portfolio ledger yet. The toy
execution audit is explicit JSON rather than a production execution schema.

Historical normalized exports have a separate [import contract](HISTORICAL_IMPORT.md), implemented
in packages/data/history.py. Instruments have no synthetic bucket defaults; symbols have publication
times; universe rows include known publication, expiry, explicit null capitalization and exclusion
reasons. SHA-256 manifests cover every input table and a declared calendar supports missing-session
audits. Imported history is quarantined separately and cannot be consumed as a demo or live run.
