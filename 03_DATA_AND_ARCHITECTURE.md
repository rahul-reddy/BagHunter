# 03 — Data, provenance and software architecture

## Provider strategy
- SEC official data.sec.gov: company submissions and extracted XBRL/Companyfacts where available; obey fair-access guidance and include appropriate user agent, caching and backoff. Filings may require parsing specific forms for nuanced facts.
- Licensed market data provider: historical daily bars, active and delisted security reference, share history, splits/dividends, and ideally official delisting returns/proceeds. Massive/Polygon is a candidate; *verify entitlement, coverage, as-of historical reference semantics, splits, corporate actions, limits and license before selecting*.
- Optional institutional-grade PIT fundamentals/universe/returns provider if accessible. Do not present today's Yahoo/Finviz universe as a valid historical universe.
- Optional independent catalyst/news primary-source timeline, each item timestamped.

## Required tables (Parquet/DuckDB; identifiers and timestamps are mandatory)
`instrument`: permanent_security_id, cik, exchange, first_seen, last_seen, security_type, identifiers_version.
`symbol_history`: security_id, ticker, valid_from, valid_to, source.
`universe_membership`: security_id, asof_date, eligible, rejection_reason, marketcap_asof, dollar_volume, source_snapshot_id.
`daily_bar`: security_id, session_date, raw_ohlcv, adjustment_policy, vendor_recorded_at, source_id.
`corporate_action`: security_id, effective_date, event_type, factor, proceeds, source_id.
`fundamental_fact`: security_id, period_end, filing_accepted_at, published_at, metric, value, unit, accession, amended_flag, source_url, ingestion_at.
`event_evidence`: security_id, event_at, first_public_at, evidence_type, source_url, raw_digest, summary, classification_confidence.
`feature_snapshot`: security_id, asof_time, feature_version, source_snapshot_ids, numeric_columns, completeness_flags.
`label`: security_id, anchor_at, horizon, outcome_method, max_multiple, terminal_total_return, delisted_status, coverage_flag.
`cohort_pair`: anchor_at, case_security_id, control_security_id, strata, matching_seed, weighting.
`signal`: security_id, asof_time, stage, score_components, model_version, limitations.
`backtest_execution`: run_id, timestamp, security_id, order_intent, assumed_fill, costs, rejected_reason.
`thesis`: security_id, asof_time, scenario_assumptions, citations, adversarial_review, version.
`source_manifest`: source_id, URL/provider, license_note, retrieval_at, asof_coverage, checksum, status.

## PIT barriers
- Every derived feature must expose `asof_time` and the latest included publication timestamp.
- Data extracted today from an amended filing cannot be substituted silently for the originally knowable historical fact.
- New shares/shares outstanding must be time-stamped; use point-in-time market cap rather than modern shares times historic price.
- Create read-time checks that reject a feature if its `published_at > asof_time`.
- Label tables MUST be physically/logically isolated from live candidate features and model-fitting features.
- Maintain independent raw immutable landing tables, transformed silver and feature gold.

## Architecture
`apps/api` FastAPI (read-only screening, profiles, study, run metadata).
`apps/web` React TypeScript dashboard.
`packages/data` provider clients, ingestion, validated records, parquet.
`packages/research` outcomes, cohorts, features, event studies, stage classification.
`packages/backtest` universe, execution assumptions, portfolio simulation, statistics.
`packages/thesis` citations, deterministic numerical models, AI narrative adapter.
`packages/shared` schemas/config.
`tests` unit, integration, PIT leakage, regression, browser.
`jobs` backfill/incremental discovery/reports.
`docs` sources, method, licenses, runbooks.

## API draft
GET /health, /sources/status, /universes?asof=, /signals?asof=&stage=, /stocks/{id}/profile?asof=, /studies/{run_id}, /backtests/{run_id}, /theses/{id}, /runs, /metrics. POST /research/runs only with explicit authorization and local rate constraints. No execution/trading endpoint.

## Data-provider adapter interface
`list_instruments(asof)`, `get_bars(security_ids,start,end,adjustment)`, `get_actions(...)`, `get_fundamentals(security_ids,asof)`, `get_filings(cik,start,end)`, `get_coverage_report()`. All return provider name, as-of, ingestion time, provenance, errors and coverage metadata. Handle pagination, rate limiting, retries, caching and credentials. No fake success response.

## Local developer UX
`make bootstrap`, `make ingest-demo`, `make study-demo`, `make backtest-demo`, `make api`, `make web`, `make test`, `make lint`, `make build`, `make qa`. `demo` commands use unmistakably synthetic FIXTURE labels if live sources are unavailable; real-data commands require valid sources and separate output folders.

## External sources to consult
- SEC data APIs: https://www.sec.gov/edgar/sec-api-documentation
- SEC fair access: https://www.sec.gov/developer
- Massive stocks offerings: https://massive.com/stocks
- Massive grouped daily guidance: https://polygon.io/knowledge-base/article/how-can-i-get-the-daily-prices-for-all-stocks-using-polygons-market-data
Check updated provider documentation during build; don't assume any specific subscription supports PIT delistings and full corporate action history.
