# 02 — Historical archaeology, controls, and discovery methods

## A. Define the universe before choosing winners
Create monthly/quarterly point-in-time US stock universes by listing/exchange, security type, market cap, price, dollar volume and eligibility. Distinguish common shares from ETFs, SPAC shells, preferreds, ADRs and OTC securities. Specify inclusion rules and sensitivity tests; allow microcap illiquidity instead of hiding it. Carry immutable instrument IDs through ticker/CIK/name changes, mergers and delistings.

## B. Define outcomes **prospectively**
At each historical observation date t, calculate future split-adjusted total-return multiples at prespecified horizons (e.g. 1, 2, 3, 5 years), maximum attained multiples and drawdown *separately*. A '10x within five years' max-hit label is not the same as a five-year holding return. Count corporate actions, delist proceeds and unavailable prices honestly. Do not require future survival to be in the base cohort. Study 5x, 10x, 20x, 100x, and failures; 100x may be too rare for robust inference.

## C. Sampling and matched controls
For each case, choose as-of eligible controls matched on date, market-cap bucket, industry, liquidity and price bucket without matching future information. Include randomly drawn peers, false breakouts, late-stage momentum and business failures. Record sampling weights so retrospective case-control comparisons do not get misread as population hit probabilities. Repeat sampling across seeds.

## D. Historical event study
Mark *pre-event* observation anchors, not the first hindsight-visible breakout. Candidate anchors: quarterly rebalance date, predefined consolidation breakout rule, earnings filing publication time, or unusual volume event. Compute signal snapshots at t-120, t-60, t-20, t, and t+20 solely for descriptive paths; never feed later snapshots into predictors at t. For each case: company evolution, revenues/margins/FCF, shares outstanding, capital raises, customers, total addressable market assumptions, sector cycle, valuation and inflection evidence. Create failure counterparts.

## E. Feature catalog (each with formula, availability lag, missingness)
Price/volume: 1D/5D/21D/63D returns, 20/60/120-day breakouts, proximity to highs, MA 8/21/50/200, 20-day dollar volume, relative volume, 20/60-day realized volatility, ATR, volatility contraction, time spent in base, gap behavior.

Relative: stock return versus market and industry, cross-sectional ranks, sector breadth, market regime, participation and dispersion.

Fundamentals: trailing and year-over-year revenue growth, two-quarter acceleration, gross/operating margin change, revenue per share, operating cash flow, FCF conversion, gross debt/cash, working-capital pressure, dilution and SBC, valuation relative to growth and comparables. Use **filing acceptance/publication** timestamps and conservative processing lag.

Qualitative: industry catalyst, customer concentration, product releases, contract quality, management incentives, competitive moat and narrative saturation; require dated primary-source evidence and explicit human/LLM judgment tagging.

## F. Candidate stages — version 0 heuristic only
WATCH: meets universe/quality floor but no ignition.
IGNITION: defined 20/60-day breakout + elevated relative volume + base duration floor + cross-sectional relative strength; apply liquidity floor.
EMERGING: maintains base breakout and improving fundamentals or verifiable catalysts.
CONFIRMED: sustained strength, peer participation and multiple filing-supported inflection signals.
EXTENDED/AGING: materially stretched from defined base or late in trend with declining asymmetry.
INVALIDATED: original trigger invalidated by price/filing/financial evidence.
Use thresholds as config, optimize only inside training windows and keep full signal history.

## G. Research design and hypothesis tests
Pre-register candidate feature families and baseline comparisons; partition history chronologically into exploratory, validation and untouched holdout. If enough data: nested walk-forward tuning; rolling/expanding training, embargo/purge for overlapping future label windows, robust cross-sectional/regime subgroup reporting. Prevent multiple-testing bias by showing every attempted family and false-discovery consideration. Bootstrap by date/cluster rather than treating overlapping stock outcomes as independent. Report confidence intervals and selection sensitivity. Holdout used once per final frozen configuration.

## H. Rank present-day candidates
As-of scoring formula (starting weights, only if validation supports them): 25% fundamental inflection, 20% price/volume, 15% industry breadth, 15% balance-sheet/business quality, 15% valuation/catalyst, 10% liquidity/risk. **These are placeholder weights**, not a validated model. Apply explicit missing-data penalty and report subscore inputs. Compare alternative nonparametric ranks and no-score baselines. Output stage, score, freshness, evidence links and disconfirmations.

## I. Deep-dive memo process
Candidate memo must include: dated catalyst map; source-supported operating model; peer valuation bands; equity dilution; bear/base/bull scenarios with assumptions and sensitivity; competitive threats; time-to-thesis; falsification and monitoring metrics; opportunity cost; counterargument written by a separate critic. Clearly separate observed facts from modeled assumptions and speculation.

## J. Stopping rules
If broad PIT historical data cannot be obtained, perform a rigorously limited case-study MVP with sample-selection caveats and never claim generalizable pattern discovery. If insufficient candidate data, output a monitoring watchlist rather than invented '3–5 winners'.
