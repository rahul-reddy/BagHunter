# Frozen multibagger classification diagnostics

`frozen-multibagger-classification-v1` evaluates fixed-budget discovery-score, 63-session
momentum and seeded-random ranks against 5x/10x maximum daily-close wealth over 1/2/3/5 years.
This is a closed synthetic-cohort diagnostic, not a current-company probability model.

Annual anchors are the first known session of each year. Rank snapshots use only dated
prices and lagged filing facts, with price/liquidity/warmup exclusions recorded. The common
population retains every as-of listed fixture common share, including unrankable names.
All families use the same population and declared budget; insufficient pools do not silently
reduce it. Ranks and source/policy SHA bindings are frozen before hindsight labels are computed.

The full anniversary horizon must mature at 23:00 UTC, even when one security delisted earlier.
Every required fixture weekday price through the horizon or the day before a known terminal
delist must exist. Missing anchor/interior/terminal prices and unavailable proceeds leave labels
unknown. Known splits, cash dividends and delist proceeds follow the shared wealth arithmetic.
A maximum daily-close multiple differs from an intraday high and from terminal holding return.
The synthetic weekday calendar and action effective-date availability are not real-exchange vintages.

Confusion counts use known labels only. Precision is unavailable when selected outcomes are
missing; population base rate, recall, lift and false-positive rate are unavailable with incomplete
population labels. Zero positives leave recall/lift undefined. Missingness bounds describe possible
unknown outcomes and are not confidence intervals. Aggregate summaries include every mature,
budget-feasible date and retain all excluded attempts separately. No best family is selected.

Illustrative 500-resample cluster intervals require at least five complete nonoverlapping date
cohorts. Undefined bootstrap metrics produce no interval, rather than being discarded. Nonoverlap
does not establish independence or empirical coverage. Default fixture data are insufficient for
these intervals. Rank scores are not probabilities: calibration, reliability bins and Brier score
remain explicitly unavailable. No p-value, FDR or untouched-holdout claim is made.

The pipeline archives `reports/classification.json` and `.md`; the read-only API serves the saved
report without recomputing legacy runs. Validation Lab compares all three families and exposes
horizon/threshold filters, per-anchor missingness, exclusions, provenance and full downloads.
No classification labels enter gold features, predictors or current research observations.

Boundary tests cover hand-calculated confusion counts, missing labels/prices, dates/timezones,
fixed budgets, malformed inputs, future-data invariance, rank/label separation, deterministic
ordering and uncertainty gates. Real browser tests cover filtering, source-bound downloads,
legacy unavailability, keyboard access and desktop/mobile accessibility.
