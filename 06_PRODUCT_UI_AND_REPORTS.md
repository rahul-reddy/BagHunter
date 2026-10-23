# 06 — Product, dashboard and report specifications

## Visual direction
Polished dark research terminal, restrained teal/amber color accents, excellent typography, accessible contrast. Focus on research transparency rather than gamified 'AI confidence'. Responsive desktop and tablet; mobile browse/read support. Fast charts; no fake real-time animations.

## Pages
1. **Command Center:** market regime, theme breadth, new ignition count, emerging/confirmed counts, source freshness, last successful refresh, top research queue.
2. **Alpha Radar:** sortable/filterable cross section by market cap, liquidity, sector, 1D/1W/1M/3M performance, volume burst, consolidation, fundamentals, stage, risk flags, evidence quality and score.
3. **100-Bagger Museum:** historical winners and matched failures side-by-side, earliest eligible date, what was knowable at that time, later outcomes visibly separated, cohorts and sector/regime filters.
4. **Candidate DNA:** chart with base/breakout markers, earnings timeline, financials, dilution, catalysts, peer breadth, score ingredients, links, uncertainty, alternative explanations.
5. **Thesis Studio:** bull/base/bear models, explicit probabilities only if defensible, catalyst checklist, falsification, independent bear reviewer and valuation sensitivity.
6. **Validation Lab:** benchmark charts, out-of-sample settings, equity curves, drawdown, trades, costs, sample-size panels, incomplete history notices.
7. **Data Quality:** providers, PIT eligibility, missing/unlicensed slices, delisted coverage, last ingestion, amendments and data audits.
8. **Settings:** watchlist preferences, universe thresholds, data-provider state, cache, version, safe local job controls.

## Report templates
### Historical case study
Instrument permanent ID; dates; eligibility and survivorship coverage; return metric; hypothetical anchor; dated knowable price/fundamentals; catalysts with citation; matched controls; why controls failed or diverged; lessons and caveats.

### Candidate memo
As-of date/time and data age; central thesis (1 paragraph); evidence table (metric, value, source, first known, caveat); industry map; financial model; valuation with per-share dilution assumptions; bull/base/bear assumptions and scenario outputs; disconfirming evidence; catalysts; downside and liquidity risks; invalidation checklist; alternative hypothesis; conflict/missing-source disclosure; model version.

### Weekly discovery digest
New ignitions, advancing/deteriorating themes, watchlist changes, fresh filings, thesis breakers, data-quality alerts, candidates requiring investigation, no forced pick count.

## Exportable files
`reports/historical_cohorts.csv`, `reports/failed_lookalikes.md`, `reports/model_validation.md`, `reports/alpha_watchlist.csv`, `reports/theses/<permanent-id>.md`, `reports/source_manifest.json`, `reports/research_limitations.md`. Additional PDF permitted only if document pipeline is available.

## Interaction requirements
Every score opens factor breakdown; every sourced financial value links to dated source; every chart labels as-of clock and adjustment basis; every backtest shows validation split and execution assumption; every missing datum is missing rather than zero. Provide search by ticker and persistent ID, visible reasons for inclusion/exclusion and an explicit 'research only' banner.
