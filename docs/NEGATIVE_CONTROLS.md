# Frozen negative controls and numeric boundaries

The fixture pipeline writes `negative_controls.json` for frozen 63-session momentum and
`discovery_negative_controls.json` for configured six-factor discovery under reports/. Both are
embedded in validation under corresponding keys. Validation Lab switches models and shows dated window
inspection, exclusions and a source-bound JSON download. Older archives show an unavailable state.
Reproduce with `uv run baghunter demo`; seed, clock, policy and input hash accompany the report.

## Frozen ledger and availability

The toy evaluator first constructs features using eligible identities and available prices/facts
at each decision clock. It retains the complete eligible candidate count, permanent IDs, identity
first-seen dates, frozen scores and latest predictor publication. Only then are outcomes
attached in the backtest namespace. Discovery ranks are recomputed at each historical decision
using the frozen configured policy, with its own price/liquidity pool and policy checksum. All
stages are retained for cross-sectional rank diagnostics; this is not a stage trading strategy. Nothing from this ledger enters predictor assembly or the gold
feature table. Missing peer outcomes fail rather than shrink the comparison pool.

The diagnostic requires decision < entry <= exit, aware clocks, unique dates/IDs, complete pools
and predictor publication <= signal time. It includes only outcomes available at the diagnostic
clock. Future outcomes are not inspected or fingerprinted. At the default fixture clock,
12 windows with 30 candidate observations are mature; the 2021-12-06 decision's exit is later
than the clock and stays excluded. This differs from the legacy hindsight report's 13 windows.
A single-peer or below-budget pool is explicitly excluded, never filled.

## Controls and interpretation

- Freeze top-k ranks before inspecting labels; default k=1, positive net holding return is the hit
  label. Precision and base rates use equal weight per decision date, not pooled row counts.
- Shuffle the complete outcome vector within each date 500 times with a local seeded RNG. Never
  exchange labels across dates, chronological split boundaries or predictor inputs. Report the
  central 95% range of randomized mean excess/precision, null mean and descriptive upper-tail
  fraction with the finite-sample +1 convention. These are not calibrated p-values, confidence
  statements, a fitted-model comparison or evidence of alpha.
- A separate irrelevant rank hashes seed, prior calendar date and permanent ID without market
  inputs or labels. It is synthetic, not a measured economic feature. Its comparison requires
  every pool identity to have been known on the prior date; otherwise that date is unavailable
  for this control. The frozen-selector comparator is reported on matching dates.
- Identical return pools yield a degenerate-null status; label-variation counts remain visible.
  Empty, immature and thin samples do not become successful tests. Mean holding returns are not
  compounded wealth. Exchangeability, independence, representative data and an untouched holdout
  have not been established. This fixed artificial fixture cannot validate predictive claims.

Bounds: at most 2,000 windows and 20,000 matured candidate records, 20–1,000 permutations and
budget 1–100. The report is deterministic for canonical input order and does not mutate inputs.
The API only downloads materialized reports; it does not launch permutations/provider requests.

## Numeric policy

Finite raw facts can produce unrepresentable ratios. Annual research growth/margins now retain
null with `numeric_limits` and citations when arithmetic overflows; missing score weights stay
missing. Candidate DNA displays affected fields. Snapshot growth also requires USD and adjacent
330–400-day annual periods. Saturating scores clamp finite inputs before multiplication.
The base feature version is `heuristic-v2-unvalidated`.

Unrepresentable price/volume, compounded wealth, daily returns or risk outputs raise explicit
errors before ranking/statistics/JSON publication. Daily skew uses standardized deviations before
cubing, avoiding unnecessary overflow under a change of equity scale. Source facts are not clipped
or replaced by zero. Tests cover finite-input overflow, scale invariance, currency/period
compatibility, future labels/predictors/identities, complete pools, deterministic ranks, degenerate
controls, browser interpretation and report integrity.
