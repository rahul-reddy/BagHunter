# 04 — Implementation sprints (vertical slice first)

A sprint is a verified milestone, **not necessarily a week**. Do not proceed past broken critical gates. Maintain `SPRINT_STATUS.md` and `NEXT_ACTION.md` after each sprint.

## Sprint 0 — Repo and contract
- [ ] Inspect environment/tools, initialize Python/backend and React frontend workspaces.
- [ ] Create strict lint/type/test/build scripts and CI skeleton.
- [ ] Write research glossary, dataset schemas, provider interfaces, quality and coverage flags.
- [ ] Implement health endpoint and empty state dashboard.
- [ ] Set up `config.example.env` with no live credentials.
**Exit:** clean install, backend and web start, lint/type/tests pass.

## Sprint 1 — First trustworthy data pipeline
- [ ] Ingest small real SEC filing sample with first-public timestamps and citations.
- [ ] Ingest small historical bars/reference sample via legitimately accessible source OR labeled fixtures.
- [ ] Build permanent security IDs, symbol mapping, price adjustment policy and raw provenance manifest.
- [ ] Add data quality tests, as-of query and missing/delisted flags.
- [ ] Demonstrate one company as-of profile, without future filings.
**Exit:** query shows raw source lineage, correct filing cutoff, coverage/freshness.

## Sprint 2 — Historical cohort and feature engine
- [ ] Define dated anchor rules and 1/2/3/5-year outcome labels.
- [ ] Build winner/failure outcome computation and matched nonwinner controls.
- [ ] Build 1D/1W/1M/3M momentum, moving averages, volume, consolidation, relative strength and selected fundamental factors.
- [ ] Implement strict PIT cutoff tests and split/delist unit fixtures.
- [ ] Produce case/control comparison as a reproducible local report.
**Exit:** deterministic cohort/feature generation; tests reject future facts.

## Sprint 3 — End-to-end runnable vertical slice (MANDATORY)
- [ ] Connect ingestion -> cohort -> signals -> trivial walk-forward evaluation -> API -> UI.
- [ ] Render one historical case with matching failed peer and evidence timeline.
- [ ] Render one as-of candidate profile and score breakdown with source links.
- [ ] Show baseline comparison and data-availability caveats; no invented alpha results.
- [ ] Run browser E2E and end-to-end CLI smoke test on real sample or explicitly labeled fixture.
**Exit:** researcher launches stack, runs pipeline, sees traceable history/current profile. COMPLETE THIS BEFORE NICE-TO-HAVE ML/ANIMATIONS.

## Sprint 4 — Historical archaeology at scale
- [ ] Backfill the largest lawful, funded and technically supportable PIT universe including delisted securities.
- [ ] Generate 5x/10x/20x/100x outcome cohorts and controls; audit missing returns.
- [ ] Perform time-aligned case studies and matched peer retrospectives.
- [ ] Quantify base rates, sector/regime cohorts, liquidity and survival distortions.
- [ ] Produce failed-lookalike atlas and case-study exports.
**Exit:** research coverage report and reproducible cohort tables; limitations explicit.

## Sprint 5 — Candidate discovery engine
- [ ] Implement configurable WATCH/IGNITION/EMERGING/CONFIRMED/EXTENDED/INVALIDATED labels.
- [ ] Track multi-horizon momentum, sector breadth and event freshness.
- [ ] Implement explainable scores with explicit missingness adjustments.
- [ ] Compare hand-built score to simple momentum/quality/liquidity baselines.
- [ ] Add incremental refresh and changes-since-last-run diff.
**Exit:** deterministic daily/as-of watchlist; each rank traceable to input.

## Sprint 6 — Rigorous validation and portfolio constraints
- [ ] Chronological train/validation/untouched test partitions.
- [ ] Purge/embargo overlapping outcomes, avoid universe look-ahead.
- [ ] Include transaction costs, execution/position constraints, delistings and benchmark.
- [ ] Report turnover, drawdown, hit rates, base rates, calibration, uncertainty and subgroups.
- [ ] Test sensitivity to signal weights and liquidity thresholds.
**Exit:** reproducible comparisons; no unsupported outperformance claim.

## Sprint 7 — Investment committee reports
- [ ] Build 3–5 (or fewer) evidence-backed deep-dives.
- [ ] Build bear/base/bull scenarios from explicit assumptions, share count and sensitivity.
- [ ] Add catalyst calendar, valuation comps, liquidity/dilution and falsification monitor.
- [ ] Run independent adversarial critique and attach citations.
- [ ] Deliver Markdown/PDF optional; no invented prices/quotes.
**Exit:** every major factual statement source-linked, all assumptions labeled.

## Sprint 8 — Dashboard polish and operationalization
- [ ] Build responsive screeners, cohort explorer, security dossier, backtest explorer and research queue.
- [ ] Build source freshness, missing-data indicators and version displays.
- [ ] Add CLI scheduling templates (not automatically enabled) and cache-aware updates.
- [ ] Add structured logs, secrets handling, CI and recovery runbook.
- [ ] Run browser, accessibility and basic load tests.
**Exit:** repeatable fresh run; user can understand why each stock appears.

## Sprint 9 — Independent audit and release
- [ ] Red-team labels for survivorship, price adjustments, future leakage, amendments and curve fitting.
- [ ] Rerun untouched holdout once using frozen model/config.
- [ ] Save commands, versions, manifests, test and benchmark evidence.
- [ ] Create final PASS/FAIL/BLOCKED matrix and known-issues register.
- [ ] Package deployable repo, docs and sampled research report.
**Exit:** no blocking integrity failures; all unsupported capabilities clearly flagged.

## Stop-early release policy
After Sprint 3, hand off an honest useful local MVP even when broad data entitlements or execution budget block later sprints. Never present synthetic candidate returns as validated results.
