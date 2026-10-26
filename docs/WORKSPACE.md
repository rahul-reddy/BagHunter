# Local research workspace

All nine views are implemented: Command Center, BagHunter Radar, 100-Bagger Museum, Candidate DNA,
Thesis Studio, Validation Lab, Data Quality, Settings and Finviz Observations. The research feed
remains synthetic. Current Finviz observations are separate, unverified saved sources. Software
acceptance does not establish empirical research success. Full-goal tracking: COMPLETION.md.

## Start

```powershell
uv sync --locked
npm --prefix apps/web ci
uv run baghunter demo
uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

In another terminal: `npm --prefix apps/web run dev`. Open http://127.0.0.1:5173/.
Services bind to loopback. No broker connection, spending, scheduler or deployment is enabled.

## Use the application

- Command Center shows stage distribution, descriptive fixture regime/breadth, saved-run inspection,
  comparisons, digest and watchlist downloads. Inspecting an archive never changes CURRENT.
- Radar searches ticker/permanent ID; filters stage, sector, cap stratum, minimum 3M return,
  relative volume, consolidation, saved watchlist, liquidity and coverage; sorts score, momentum,
  relative volume, liquidity or coverage. Watchlist/preferences persist in this browser. Cap strata
  are fictional matching buckets, not real market capitalizations.
- Candidate DNA shows raw price/volume, a labeled current base reference, dated stage markers/history,
  relative strength, peer breadth, moving averages, ATR, volatility, available annual financial ratios,
  score ingredients, missing factors and dated citations. Download a source-attributed dossier.
- Museum filters multi-anchor cohorts by year/horizon/sector and 5×/10×/20×/100× maximum-hit threshold.
  Missing outcomes remain in eligible denominators. Dated predictors and later outcomes are separated.
  Artificial cohorts do not estimate population base rates. Maximum hits differ from holding returns.
- Thesis Studio calculates editable bear/base/bull assumptions with dilution/net debt and supports
  hypothesis, catalyst citations, review date, falsification and bear-argument drafts. Save/load locally
  and download Markdown. Defaults are illustrative user assumptions, not company financials.
  Its dated catalyst calendar saves up to 100 events per security, with optional public HTTPS
  citations, falsification conditions and planned/observed/invalidated operator statuses. Filter,
  remove and export events locally; changing a status does not verify an assertion.
- Validation Lab separates the legacy toy from a constrained simulation, with execution rows, costs,
  whole shares, cash, caps, 12–1 momentum/revenue-growth/seeded-random comparators, return/drawdown/
  win-rate/payoff diagnostics, cost sensitivity, purge/embargo and illustrative bootstrap arithmetic.
  Daily close equity includes cash gaps, corporate actions and costs, with close-to-close drawdown,
  volatility, zero-risk-free Sharpe and zero-target Sortino. Window-end metrics remain separately
  labeled. Execution filters and pagination keep the ledger usable. The inspected fixture is not
  an untouched holdout; fixture weekdays are not an exchange calendar. Ratios are undefined where
  variance is zero or equity exhaustion prevents valid sampling.
- Data Quality exposes source/archive-checksum status, limitations and source/report downloads.
- Settings persists display preferences and exports model/portfolio policies for explicit CLI refresh.
  Browser edits never rewrite materialized output or activate provider data.
- Finviz Observations lists local snapshots for explicit selection without restarting the API.
  Selection revalidates original source bytes. Select a saved reference batch separately. Index
  metadata is not source verification. No provider request, new mapping or identity promotion runs.
  Reported sector/country, price availability, volume and positive-P/E filters apply before
  pagination. Click a ticker to write a snapshot-bound research draft with hypothesis, evidence
  questions, falsification, bear case and review date; save/load locally and export a provenance
  dossier. These assertions never become scored predictors or verified security identities.

## Reproducible policies and refresh

Download policies in Settings, then run:

```powershell
uv run baghunter demo --policy discovery-policy.json --portfolio-policy portfolio-policy.json
```

Discovery fields: version, min_dollar_volume, min_price, ignition_relative_volume, max_base_width,
max_ema_stretch, confirmation_sessions and six score weights. Weights sum to one. Absent inputs stay
null; weight is not redistributed. Quality arithmetic requires dated operating and cashflow margins,
so it stays missing in the revenue-only fixture. Annual growth requires comparable 330–400-day ends.

Six deterministic, unvalidated stage rules use a 21-session history initialized at WATCH. Ignition
requires a prior 60-session high, volume, liquidity and base width. Confirmation requires sustained
trend, dated growth, relative strength and breadth. Insufficient peer breadth remains null.
No future outcome label enters discovery. Financial revisions obey publication plus processing lag.

Portfolio fields: capital, max_position, max_sector, participation, min_dollar_volume, min_price,
one_way_cost_bps, selector and seed. Selectors are momentum_63d, momentum_12_1, revenue_growth,
seeded_random. Comparators share constraints. Missing selector inputs are excluded with reasons.
Next-weekday-open entries use 21-session holds and cash gaps. Participation uses prior known dollar
volume, never future execution volume. Exits cannot finance entries at the same earlier open.
Dividends stay cash, splits alter shares, delist proceeds are explicit, missing exits fail closed.
Missing held-session marks also fail closed. Delisted holdings become explicit cash after the
terminal event; terminal daily equity must reconcile to simulated cash. Turnover includes actual
buy notional plus sale/delist proceeds, excluding cash dividends.
Fixed combined costs are assumptions, not calibrated impact. No borrowing, shorting or trading.

Run IDs bind raw bytes, UTC clock, seed, code and both policies. Identical refresh verifies/reuses
all archived output checksums; corruption rejects without repair. Policy changes create a new run.
Comparisons reject a later baseline and disclose policy differences. Legacy archives without an
integrity manifest are labeled. Back up the adjacent raw source archive and runs together.

## Reports and operations

`/runs/<id>/reports/<name>` downloads source_manifest.json, validation.json, portfolio.json,
portfolio_policy.json, discovery_policy.json, cohort_grid.json, toy_backtest.json,
historical_cohorts.csv, baghunter_watchlist.csv, historical_cases.md, discovery_digest.md and
research_limitations.md. `/runs/<id>/dossiers/<security_id>` downloads a fixture dossier. Scenario
memo downloads remain separate user drafts. No generated draft counts as a verified thesis.

`examples/refresh-fixture.ps1` and `examples/refresh-fixture.cron.example` are manual templates;
neither registers a task or requests provider data. CI/review gates remain mandatory. Deployments
require owner confirmation and a commit already on main. On Windows stop dev servers before npm ci
if native binaries are locked. Run `pwsh -NoProfile -File scripts/qa.ps1` for full acceptance.
For an isolated second worktree, set BAGHUNTER_API_PORT=8001 and BAGHUNTER_WEB_PORT=5174 in its
shell before starting its Vite/Playwright commands; both accept only integer ports 1–65535 and
keep loopback binding. Defaults remain 8000/5173. Its Python environment and data stay separate.

## Accession-bound SEC normalization

The [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) expose
submissions and aggregate companyfacts. Use an existing local raw pair:

```powershell
uv run baghunter normalize-sec --submissions data/real/sec/submissions.json --companyfacts data/real/sec/companyfacts.json --security-id local-unverified-id --asof 2022-01-03T23:00:00+00:00
```

The parser never downloads or invents a contact. Both CIKs must match. Each accepted fact requires
its exact accession, aware acceptance timestamp and primary document; acceptance/publication proxy
plus lag must precede as-of. Date-only filed is not used as an acceptance clock. Annual USD revenue,
net/operating income and operating cashflow are supported. Conflicting aliases reject, amendments
remain, and unsupported units/periods/missing old acceptance metadata are counted and excluded.
Quarterly/YTD conversion and custom taxonomies are unsupported. Raw hashes and filing URLs remain.

Output stays in data/real/sec/quarantine. Security-ID assignment is an operator assertion. Current
aggregate facts do not prove original extraction vintage, publisher authenticity or class identity.
Real research still requires original-vintage and licensed PIT universe/action/delisting evidence.
