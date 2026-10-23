# BagHunter — 100-Bagger DNA Lab

A local US-equities research laboratory with point-in-time feature cutoffs, failed-peer comparisons,
a deterministic screening demonstration, and a read-only research terminal. **Research and simulation
only. No orders or automated trading.**

The first release uses **entirely synthetic fixtures**: fictional securities, prices, filings and
outcomes. It proves software mechanics; it supplies no empirical alpha, investment probability,
real stock recommendation or verified thesis. No licensed historical market provider is connected.

## Start locally

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 24 and npm. From the repository root:

```powershell
uv sync --locked
npm --prefix apps/web ci
uv run baghunter demo
uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
npm --prefix apps/web run dev
```

Open **http://127.0.0.1:5173**. The UI proxies `/api` to port 8000. API documentation:
http://127.0.0.1:8000/docs. `Ctrl+C` stops each service. No public deployment is configured.

## Reproduce and inspect

```powershell
uv run baghunter study-demo --asof 2022-01-03T23:00:00+00:00 --seed 7 --output data/fixture/latest
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy packages apps/api
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web run build
cd apps/web
npx playwright install chromium
cd ../..
npm --prefix apps/web run test:e2e
```

`pwsh -NoProfile -File scripts/qa.ps1` runs the complete acceptance sequence and saves logs to
`artifacts/test_results/`. Browser tests launch their own backend and web server unless local
servers already occupy those addresses. For GNU Make users, equivalent `make` targets exist.

`ingest-demo`, `study-demo` and `backtest-demo` are aliases that rebuild the same complete slice.
There is no incremental refresh or configurable research universe yet. CLI `--help`
lists implemented arguments only. Outputs are published as immutable runs below
`data/fixture/latest/runs/<run-id>/`; `CURRENT` selects the active run atomically. Raw content is
SHA-256 addressed in `data/fixture/raw/`. Silver, gold and hindsight Parquet tables are separate.
CSV and Markdown exports live inside each run's `reports/` folder. These generated files are ignored.

## Research protocol and limitations

The fixture has three common shares and one fictional market baseline, from 2019-01-01 through
2023-03-30 (weekdays, not exchange sessions). The study anchor is 2020-01-01, with prospective
1/2/3/5-year horizons; unavailable horizons stay null. A synthetic failed peer includes zero-proceeds
delisting. Maximum-hit multiples and terminal holding returns are different outputs.

The toy evaluation freezes a 63-session momentum selector before sequential decisions. It selects
after the close, enters next weekday open, exits 21 sessions later, charges 40 bps round trip, and
compares with equal-weight eligible peers and the artificial market. It does not fit a model or
claim an untouched holdout. It has cash gaps and lacks production capacity/sector constraints.
Scores are explicitly unvalidated placeholder weights; missing components remain null and reduce
the attainable score. The current stage implementation covers WATCH, IGNITION and EXTENDED/AGING.

See [research method](docs/METHOD.md), [schemas](docs/SCHEMAS.md), [sources](docs/SOURCES.md),
[operations](docs/OPERATIONS.md), [release matrix](reports/RELEASE_READINESS.md), and
[current status](STATUS.md). The original numbered Markdown files remain the product contract.

## Optional real SEC raw download

Set `SEC_USER_AGENT` in your shell to your organization and real contact email, then:

```powershell
uv run baghunter sec-fetch --cik 320193 --output data/real/sec/raw
```

This makes a public SEC request and saves raw submissions plus a checksum manifest. It does not
parse historical financial facts or make the synthetic sample real. No contact identity is inferred.
The CLI does not auto-load `.env`; inject environment variables explicitly. No paid requests occur.

## Historical export staging

`uv run baghunter audit-history --bundle examples/history-fixture` audits the new fictional import
example. `uv run baghunter ingest-history --bundle examples/history-fixture --output data/imported`
preserves its source bytes and writes quarantined Parquet plus a coverage report. Normalized external
exports can use the same adapter, with explicit source authorization and checksums. They remain
EXTERNAL_UNVERIFIED and never become candidates automatically. See the
[historical import contract](docs/HISTORICAL_IMPORT.md) for formats, PIT rules and resource limits.

The owner has Finviz Elite. Its current-screener export handoff and remaining historical-data gaps
are documented in [Finviz setup](docs/FINVIZ.md). `ingest-finviz` imports the saved overview CSV into
an immutable, quarantined current snapshot. It does not activate candidates or the fixture dashboard.

## Development workflow

Read [AGENTS.md](AGENTS.md). Short branches, lockfile installs, exact-head CI and independent model
review; merge only through `scripts/merge-pr.ps1`. Deployment is manual, owner-confirmed and limited
to merged commits. Public repository visibility was explicitly authorized by the owner on 2026-10-23.
